# http-auth Python Library - Implementation Plan

## Project Overview

- **Name**: http-auth
- **Purpose**: Environment-variable-based HTTP authentication library
- **Language**: Python 3.8+
- **Core Interface**: `get_auth(url)` → `{'Authorization': 'Bearer ...'}` or `{}`
- **Key Design**: Zero dependencies by default, optional extras for requests/httpx/keyring

## Project Structure

```
http-auth/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/http_auth/
│   ├── __init__.py          # Main exports
│   ├── _version.py          # Hatch VCS version (auto-generated)
│   ├── resolver.py          # AuthResolver class (core)
│   ├── env.py               # Environment variable parsing
│   ├── netrc_.py            # netrc fallback
│   ├── keyring_.py          # keyring fallback (optional)
│   ├── config.py            # INI config file parsing
│   ├── auth.py              # Auth types (Bearer, Basic)
│   └── http_auth.py         # requests/httpx optional integration
└── tests/
    ├── __init__.py
    ├── test_resolver.py
    ├── test_env.py
    ├── test_netrc.py
    └── test_cli.py
```

## pyproject.toml Configuration

```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.build"

[project]
name = "http-auth"
dynamic = ["version"]
description = "Lightweight HTTP authentication via environment variables for httpx, requests, and raw HTTP clients"
readme = "README.md"
requires-python = ">=3.8"
license = "MIT"
authors = [
  { name = "Your Name", email = "you@example.com" },
]
dependencies = []  # ZERO by default!

[project.optional-dependencies]
requests = ["requests"]
httpx = ["httpx"]
keyring = ["keyring>=23.0.0"]
all = ["requests", "httpx", "keyring>=23.0.0"]
tests = ["pytest", "http-auth[all]"]

[project.scripts]
http-auth = "http_auth.__main__:main"
```

## Environment Variable Naming Convention

> **IMPORTANT**: Periods (`.`) are not valid in environment variable names.
> Therefore, replace periods with underscores (`_`) in hostnames.

| Priority | Variable | Example Value | Output |
|----------|----------|---------------|--------|
| 1 (exact) | `HTTP_AUTH_TOKEN_example_com` | `mytoken` | `Bearer mytoken` |
| 2 (exact) | `HTTP_AUTH_HEADER_example_com` | `Bearer token` | `Bearer token` (as-is) |
| 3 (exact) | `HTTP_AUTH_BASIC_example_com` | `user:pass` | `Basic dXNlcjpwYXNz` |
| 4 (glob) | `HTTP_AUTH_TOKEN_*.example_com` | `token` | `Bearer token` |
| 5 (global) | `HTTP_AUTH_TOKEN` | `token` | `Bearer token` |
| 6 (global) | `HTTP_AUTH_HEADER` | `Bearer token` | `Bearer token` |
| 7 (global) | `HTTP_AUTH` | `Custom creds` | `Custom creds` |

**Hostname Matching Rules:**

- **Case-insensitive**: Hostnames are normalized to lowercase for matching
  - `HTTP_AUTH_TOKEN_EXAMPLE_COM=token` matches `example.com`
  - User can define in any case; library handles normalization
- **Period handling**: Periods (`.`) become underscores (`_`) in env var names
  - `example.com` → `example_com`
  - For complex hosts (many periods), use INI config file instead

**Scheme Specifier** (optional override per host):
- `HTTP_AUTH_SCHEME_example_com=bearer|basic|custom`

**For Hosts with Periods**: Use INI config file (`~/.http-auth.ini`) instead of environment variables. Environment variables cannot contain periods, but INI section names can.

## Priority Chain (Full)

1. **Exact host env vars** → `HTTP_AUTH_TOKEN_host.com`, `HTTP_AUTH_HEADER_host.com`, `HTTP_AUTH_BASIC_host.com`
2. **Glob/prefix env vars** → `HTTP_AUTH_TOKEN_*.host.com` (via fnmatch)
3. **Global env vars** → `HTTP_AUTH_TOKEN`, `HTTP_AUTH_HEADER`, `HTTP_AUTH`
4. **netrc** → `~/.netrc`
5. **keyring** → system keyring (service: `http-auth:{hostname}`) - optional
6. **INI config** → `~/.http-auth.ini`

## Core API

### Main Exports (http_auth/__init__.py)

```python
from http_auth.resolver import AuthResolver
from http_auth.auth import BearerAuth, BasicAuth, HTTPEnvAuth
from http_auth import get_auth, get_auth_header

__version__ = "0.1.0"
__all__ = [
    "AuthResolver",
    "BearerAuth",
    "BasicAuth",
    "HTTPEnvAuth",
    "get_auth",
    "get_auth_header",
]
```

### Resolver Class (http_auth/resolver.py)

```python
from __future__ import annotations

import fnmatch
import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Self

logger = logging.getLogger(__name__)


class AuthResolver:
    """Resolves HTTP authentication from multiple sources."""

    def __init__(
        self,
        sources: list[str] | None = None,
        env_prefix: str = "HTTP_AUTH",
    ) -> None:
        self.sources = sources or ["env", "netrc", "keyring", "config"]
        self.env_prefix = env_prefix

    def for_url(self, url: str) -> dict:
        """Returns {'Authorization': '...'} or {}"""
        from urllib.parse import urlparse

        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return self.for_hostname(hostname)

    def for_hostname(self, hostname: str) -> dict:
        """Returns {'Authorization': '...'} or {}"""
        # Try each source in priority order
        for source in self.sources:
            result = self._try_source(source, hostname)
            if result:
                return result
        return {}

    def _try_source(self, source: str, hostname: str) -> dict | None:
        if source == "env":
            from http_auth.env import get_auth_from_env

            return get_auth_from_env(hostname)
        elif source == "netrc":
            from http_auth.netrc_ import get_auth_from_netrc

            return get_auth_from_netrc(hostname)
        elif source == "keyring":
            from http_auth.keyring_ import get_auth_from_keyring

            return get_auth_from_keyring(hostname)
        elif source == "config":
            from http_auth.config import get_auth_from_config

            return get_auth_from_config(hostname)
        return None
```

### Auth Types (http_auth/auth.py)

```python
from __future__ import annotations

import base64
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import TypeVar

    import httpx
    import requests
    from typing_extensions import TypeIs

    T = TypeVar("T", bound="httpx.Request | requests.PreparedRequest")

try:
    from requests.auth import AuthBase
except ImportError:
    AuthBase = object  # type: ignore[misc,assignment]


class BearerAuth(AuthBase):  # type: ignore[valid-type]
    """Bearer token authentication."""

    def __init__(self, token: str) -> None:
        self.token = token

    def __call__(self, r: T) -> T:
        r.headers["Authorization"] = f"Bearer {self.token}"
        return r


class BasicAuth(AuthBase):  # type: ignore[valid-type]
    """Basic authentication."""

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password

    def __call__(self, r: T) -> T:
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        r.headers["Authorization"] = f"Basic {encoded}"
        return r


class HTTPEnvAuth(AuthBase):  # type: ignore[valid-type]
    """requests-compatible auth that auto-resolves from env.

    Supports: requests library when 'requests' extra is installed.
    """

    def __init__(self, sources: list[str] | None = None) -> None:
        self.resolver = AuthResolver(sources=sources)

    def __call__(self, r: T) -> T:
        from urllib.parse import urlparse

        hostname = urlparse(r.url).hostname or ""
        auth = self.resolver.for_hostname(hostname)
        if auth:
            r.headers["Authorization"] = auth.get("Authorization", "")
        return r
```

### Environment Variable Parsing (http_auth/env.py)

```python
from __future__ import annotations

import fnmatch
import os
import re
from typing import NamedTuple


class AuthResult(NamedTuple):
    """Result of auth lookup."""

    value: str
    scheme: str  # 'bearer', 'basic', 'header', 'raw'


def normalize_hostname(hostname: str) -> str:
    """Normalize hostname for env var matching."""
    # Remove port, convert to lowercase
    host_part = hostname.split(":")[0].lower()
    # Replace dots with underscores for env var compatibility
    return host_part.replace(".", "_")


def get_auth_from_env(hostname: str) -> dict | None:
    """Get auth from environment variables for given hostname."""
    normalized = normalize_hostname(hostname)

    # Priority 1: Exact host match
    # HTTP_AUTH_TOKEN_example_com, HTTP_AUTH_HEADER_example_com, etc.
    for var_type in ["TOKEN", "HEADER", "BASIC"]:
        env_var = f"HTTP_AUTH_{var_type}_{normalized}"
        value = os.environ.get(env_var)
        if value:
            return _build_auth_header(var_type, value)

    # Priority 2: Glob/prefix matching (HTTP_AUTH_TOKEN_*.example_com)
    # Sort by length descending to match longest prefix first
    env_vars = {k: v for k, v in os.environ.items() if k.startswith(f"HTTP_AUTH_")}
    for var_type in ["TOKEN", "HEADER", "BASIC"]:
        prefix = f"HTTP_AUTH_{var_type}_"
        for env_name, env_value in env_vars.items():
            if env_name.startswith(prefix):
                pattern = env_name[len(prefix) :]
                # Check if hostname matches glob pattern
                if fnmatch.fnmatch(normalized, pattern) or fnmatch.fnmatch(
                    hostname.lower(), pattern.replace("_", ".")
                ):
                    return _build_auth_header(var_type, env_value)

    # Priority 3: Global env vars
    # HTTP_AUTH_TOKEN, HTTP_AUTH_HEADER, HTTP_AUTH
    if token := os.environ.get("HTTP_AUTH_TOKEN"):
        return {"Authorization": f"Bearer {token}"}
    if header := os.environ.get("HTTP_AUTH_HEADER"):
        return {"Authorization": header}
    if raw := os.environ.get("HTTP_AUTH"):
        return {"Authorization": raw}

    return None


def _build_auth_header(var_type: str, value: str) -> dict:
    """Build Authorization header based on variable type."""
    if var_type == "TOKEN":
        return {"Authorization": f"Bearer {value}"}
    elif var_type == "BASIC":
        import base64

        encoded = base64.b64encode(value.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}
    else:  # HEADER or raw
        return {"Authorization": value}
```

### netrc Support (http_auth/netrc_.py)

```python
from __future__ import annotations

import netrc
import os
from typing import NamedTuple


class NetrcAuth(NamedTuple):
    """Result from netrc lookup."""

    login: str
    password: str


def get_auth_from_netrc(hostname: str) -> dict | None:
    """Get Basic auth from ~/.netrc for given hostname."""
    try:
        netrc_path = os.environ.get("NETRC") or os.path.expanduser("~/.netrc")
        if not os.path.exists(netrc_path):
            return None

        authenticators = netrc.netrc(netrc_path).authenticators(hostname)
        if authenticators:
            login, _, password = authenticators
            if login and password:
                import base64

                credentials = f"{login}:{password}"
                encoded = base64.b64encode(credentials.encode()).decode()
                return {"Authorization": f"Basic {encoded}"}
    except Exception:
        pass
    return None
```

### Keyring Support (http_auth/keyring_.py)

```python
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import keyring


def get_auth_from_keyring(hostname: str) -> dict | None:
    """Get auth from system keyring."""
    try:
        import keyring

        service = f"http-auth:{hostname}"
        # Try to get token first, then basic auth
        token = keyring.get_password(service, "token")
        if token:
            return {"Authorization": f"Bearer {token}"}

        username = keyring.get_password(service, "username")
        password = keyring.get_password(service, "password")
        if username and password:
            import base64

            credentials = f"{username}:{password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            return {"Authorization": f"Basic {encoded}"}
    except ImportError:
        pass
    except Exception:
        pass
    return None
```

### INI Config Support (http_auth/config.py)

```python
from __future__ import annotations

import configparser
import os
from pathlib import Path


def get_auth_from_config(hostname: str) -> dict | None:
    """Get auth from ~/.http-auth.ini config file."""
    config_path = Path(os.path.expanduser("~/.http-auth.ini"))
    if not config_path.exists():
        return None

    config = configparser.ConfigParser()
    config.read(config_path)

    # Try exact match first
    if hostname in config:
        return _parse_config_section(config[hostname])

    # Try with normalized hostname (dots to underscores)
    normalized = hostname.replace(".", "_")
    if normalized in config:
        return _parse_config_section(config[normalized])

    return None


def _parse_config_section(section: configparser.SectionProxy) -> dict | None:
    """Parse a config section to auth header."""
    if token := section.get("token"):
        scheme = section.get("scheme", "bearer").lower()
        if scheme == "bearer":
            return {"Authorization": f"Bearer {token}"}
        elif scheme == "basic":
            import base64

            encoded = base64.b64encode(token.encode()).decode()
            return {"Authorization": f"Basic {encoded}"}
        else:
            return {"Authorization": token}

    if user := section.get("basic_user"):
        password = section.get("basic_pass", "")
        import base64

        credentials = f"{user}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    return None
```

### CLI Entry Point (http_auth/__main__.py)

```python
from __future__ import annotations

import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx
    import requests


def main() -> int:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: http-auth <url>", file=sys.stderr)
        return 1

    url = sys.argv[1]

    from http_auth import get_auth

    auth = get_auth(url)
    if auth:
        print(auth["Authorization"])
        return 0
    else:
        print("No authentication found", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
```

## CLI Usage

```bash
# Get auth header for URL
$ http-auth https://artifactory.company.com
Authorization: Bearer my-secret-token

# With environment variable
$ export HTTP_AUTH_TOKEN_artifactory_company_com=secret
$ http-auth https://artifactory.company.com
Authorization: Bearer secret
```

## Requests/Httpx Optional Integration Pattern

Following the aws-http-auth pattern (http_auth/http_auth.py):

```python
from __future__ import annotations

import sys

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import httpx
    import requests

try:
    from requests.auth import AuthBase
except ImportError:
    AuthBase = object  # type: ignore[misc,assignment]


class HTTPEnvAuth(AuthBase):  # type: ignore[valid-type]
    """requests-compatible auth that auto-resolves from env.

    Requires 'requests' extra: pip install http-auth[requests]
    """

    def __init__(self, sources: list[str] | None = None) -> None:
        self.resolver = AuthResolver(sources=sources)

    def __call__(self, r: requests.PreparedRequest) -> requests.PreparedRequest:
        from urllib.parse import urlparse

        hostname = urlparse(r.url).hostname or ""
        auth = self.resolver.for_hostname(hostname)
        if auth:
            r.headers["Authorization"] = auth.get("Authorization", "")
        return r
```

## Usage Examples

### Basic Usage (no dependencies)

```python
from http_auth import get_auth

# Get auth dict for URL
auth = get_auth("https://artifactory.company.com/repo")
# Returns: {'Authorization': 'Bearer mytoken'} or {}

# Get just the header value
from http_auth import get_auth_header
header = get_auth_header("https://example.com")
# Returns: 'Bearer token' or None
```

### With requests

```python
import requests
from http_auth.http_auth import HTTPEnvAuth

# Auto-resolves auth from environment variables
requests.get("https://artifactory.company.com/repo", auth=HTTPEnvAuth())
```

### With httpx

```python
import httpx
from http_auth.http_auth import HTTPEnvAuth

client = httpx.Client(auth=HTTPEnvAuth())
response = client.get("https://artifactory.company.com/repo")
```

### With AuthResolver (flexible)

```python
from http_auth import AuthResolver

# Custom source order
resolver = AuthResolver(sources=["env", "config", "netrc"])

# Query by URL or hostname
auth = resolver.for_url("https://example.com/path")
auth = resolver.for_hostname("example.com")
```

## Config File Format (~/.http-auth.ini)

```ini
[example.com]
token = my-token
scheme = bearer

[other.company.com]
basic_user = admin
basic_pass = secret
scheme = basic

[custom.example]
header = CustomScheme credentials
scheme = custom
```

## Dependencies (pyproject.toml)

```toml
[project.optional-dependencies]
requests = ["requests"]
httpx = ["httpx"]
keyring = ["keyring>=23.0.0"]
all = ["requests", "httpx", "keyring>=23.0.0"]
tests = ["pytest", "http-auth[all]"]
```

## Implementation Order

1. **Phase 1**: Core - `env.py` + `get_auth()` function + basic resolver
2. **Phase 2**: Add `AuthResolver` class with netrc support
3. **Phase 3**: Add keyring support (optional dependency)
4. **Phase 4**: Add INI config support
5. **Phase 5**: Add `http_auth.py` with requests/httpx compatibility
6. **Phase 6**: Add CLI helpers + tests

## Testing Notes

- Use `pytest` with `pytest-mock` for mocking environment variables
- Test glob matching with `fnmatch` patterns
- Test netrc with fixture files
- Mock keyring for unit tests
- Use `responses` or `requests-mock` for requests tests

## Type Checking

Use pyright/mypy with strict settings. Key patterns:

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import requests

try:
    from requests.auth import AuthBase
except ImportError:
    AuthBase = object  # type: ignore[misc,assignment]
```

This allows type checking without runtime dependencies.
