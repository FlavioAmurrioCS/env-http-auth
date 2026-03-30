# http-auth

[![PyPI - Version](https://img.shields.io/pypi/v/http-auth.svg)](https://pypi.org/project/http-auth)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/http-auth.svg)](https://pypi.org/project/http-auth)

Lightweight HTTP authentication via environment variables for httpx, requests, and raw HTTP clients.

## Features

- **Zero dependencies** by default (stdlib only)
- **Universal**: Works with `requests`, `httpx`, and any HTTP client
- **Multiple auth sources**: Environment variables, netrc, keyring, config files
- **Per-host authentication** with suffix patterns
- **Type safe**: Full type hints for better development experience

## Table of Contents

- [http-auth](#http-auth)
  - [Features](#features)
  - [Table of Contents](#table-of-contents)
  - [Installation](#installation)
  - [Quick Start](#quick-start)
  - [Environment Variables](#environment-variables)
    - [Variable Naming](#variable-naming)
    - [Notes](#notes)
    - [Suffix Matching](#suffix-matching)
    - [Scheme Specifier](#scheme-specifier)
  - [Usage Examples](#usage-examples)
    - [Basic usage](#basic-usage)
    - [Using requests](#using-requests)
    - [Using httpx](#using-httpx)
    - [AuthResolver class](#authresolver-class)
  - [Priority Chain](#priority-chain)
  - [Configuration Sources](#configuration-sources)
    - [Environment Variables](#environment-variables-1)
    - [netrc](#netrc)
    - [System Keyring](#system-keyring)
    - [Config File](#config-file)
  - [CLI](#cli)
    - [CLI Options](#cli-options)
  - [Contributing](#contributing)
  - [License](#license)

## Installation

```console
pip install http-auth
```

## Quick Start

```python
import os
from http_auth import get_auth

# Set environment variable
os.environ["HTTP_AUTH_TOKEN_example_com"] = "my-token"

# Get auth dict for URL
auth = get_auth("https://example.com/path")
# Returns: {'Authorization': 'Bearer my-token'}
```

## Environment Variables

Environment variables are the primary way to configure authentication. Hostnames are normalized (lowercase, dots become underscores).

### Variable Naming

| Priority | Variable | Example Value | Output |
|----------|----------|---------------|--------|
| 1 | `HTTP_AUTH_TOKEN_example_com` | `mytoken` | `Bearer mytoken` |
| 2 | `HTTP_AUTH_TOKEN__example_com` | `mytoken` | `Bearer mytoken` (suffix) |
| 3 | `HTTP_AUTH_HEADER_example_com` | `Bearer token` | `Bearer token` |
| 4 | `HTTP_AUTH_BASIC_example_com` | `user:pass` | `Basic dXNlcjpwYXNz` |
| 5 | `HTTP_AUTH_TOKEN` | `token` | `Bearer token` |
| 6 | `HTTP_AUTH_HEADER` | `Bearer token` | `Bearer token` |
| 7 | `HTTP_AUTH` | `Custom creds` | `Custom creds` |

### Notes

- Periods (`.`) in hostnames become underscores (`_`) in env var names
  - `example.com` → `HTTP_AUTH_TOKEN_example_com`
  - `artifactory.company.com` → `HTTP_AUTH_TOKEN_artifactory_company_com`
- Matching is case-insensitive
- Use config file for hosts with many periods

### Suffix Matching

Double underscore (`__`) indicates suffix matching:

```bash
export HTTP_AUTH_TOKEN__example_com=my-token
# Matches: example.com, sub.example.com, api.example.com
```

### Scheme Specifier

Override the auth scheme per host:

```bash
export HTTP_AUTH_SCHEME_example_com=bearer
export HTTP_AUTH_TOKEN_example_com=my-token
# Output: Bearer my-token

export HTTP_AUTH_SCHEME_example_com=basic
export HTTP_AUTH_TOKEN_example_com=user:pass
# Output: Basic dXNlcjpwYXNz
```

## Usage Examples

### Basic usage

```python
from http_auth import get_auth, get_auth_header

# Get full auth dict
auth = get_auth("https://example.com/path")
# {'Authorization': 'Bearer my-token'}

# Get just the header value
header = get_auth_header("https://example.com/path")
# 'Bearer my-token'
```

### Using requests

```python
from http_auth import HTTPEnvAuth
import requests

# Set environment variable
# HTTP_AUTH_TOKEN_example_com=my-token

# Use with requests
response = requests.get(
    "https://example.com/api/data",
    auth=HTTPEnvAuth()
)
```

### Using httpx

```python
from http_auth import HTTPEnvAuth
import httpx

# Set environment variable
# HTTP_AUTH_TOKEN_example_com=my-token

# Use with httpx
client = httpx.Client(auth=HTTPEnvAuth())
response = client.get("https://example.com/api/data")
```

### AuthResolver class

For more control over authentication sources:

```python
from http_auth import AuthResolver

# Use only specific sources
resolver = AuthResolver(sources={"env", "netrc"})

# Query by URL or hostname
auth = resolver.for_url("https://example.com/path")
auth = resolver.for_hostname("example.com")

# Custom source order
resolver = AuthResolver(sources={"config", "env", "keyring"})
```

## Priority Chain

When resolving authentication, sources are tried in this order:

1. **Exact host match** - `HTTP_AUTH_TOKEN_example_com`
2. **Suffix match** - `HTTP_AUTH_TOKEN__example_com` (double underscore)
3. **Global env vars** - `HTTP_AUTH_TOKEN`
4. **Config file** - `~/.http-auth.ini`
5. **netrc** - `~/.netrc`
6. **keyring** - System keyring

## Configuration Sources

### Environment Variables

Primary source. Supports per-host and global variables. See [Environment Variables](#environment-variables) for details.

### netrc

Falls back to `~/.netrc` for Basic authentication:

```netrc
machine example.com
login admin
password secret123
```

### System Keyring

Stores credentials in the system keyring:

```python
import keyring

# Store token
keyring.set_password("http-auth:example.com", "token", "my-secret")

# Store Basic auth
keyring.set_password("http-auth:example.com", "username", "admin")
keyring.set_password("http-auth:example.com", "password", "secret")
```

### Config File

INI format at `~/.http-auth.ini`:

```ini
[example.com]
token = my-token
scheme = bearer

[other.company.com]
basic_user = admin
basic_pass = secret
scheme = basic
```

## CLI

Get authentication headers from the command line:

```bash
# Basic usage
$ export HTTP_AUTH_TOKEN_example_com=my-token
$ http-auth https://example.com
Authorization: Bearer my-token

# Header only (value only)
$ http-auth --header-only https://example.com
Bearer my-token

# No auth found
$ http-auth https://unknown.com
No authentication found for https://unknown.com
```

### CLI Options

```
http-auth [-h] [--header-only] url

Get HTTP authentication header for a URL

positional arguments:
  url                  URL to get authentication header for

options:
  -h, --help           show this help message and exit
  --header-only        Output only the header value
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

http-auth is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
