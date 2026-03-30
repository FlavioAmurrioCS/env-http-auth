# HTTP Auth Convention

A standard for HTTP authentication via environment variables.

## Motivation

Environment variables are the standard way to pass configuration to applications and tools. HTTP authentication should be no different. This convention provides a portable, shell-compatible approach that any tool can implement without dependencies.

## Design Principles

1. **Shell-compatible** - Uses only valid characters in environment variable names
2. **Case-insensitive** - Hostname matching works regardless of case
3. **Clear priority** - Explicit per-host config takes precedence over fallbacks
4. **Zero dependencies** - Can be implemented in any language with just env var access

## Variable Syntax

### Exact Match

```
HTTP_AUTH_TOKEN_<hostname>
```

| Component | Description |
|-----------|-------------|
| `HTTP_AUTH` | Prefix (can be customized) |
| `TOKEN` | Auth type |
| `<hostname>` | Normalized hostname |

**Example:**
```bash
# Matches exactly: example.com
HTTP_AUTH_TOKEN_example_com=my-secret-token
```

### Suffix Match (Double Underscore)

```
HTTP_AUTH_TOKEN__<suffix>
```

Double underscore (`__`) indicates suffix matching.

**Example:**
```bash
# Matches: example.com, sub.example.com, api.example.com
HTTP_AUTH_TOKEN__example_com=my-secret-token
```

### Global Fallback

```
HTTP_AUTH_TOKEN
HTTP_AUTH_HEADER
HTTP_AUTH
```

Applies to any host when no host-specific match is found.

### Type Suffixes

| Type Suffix | Output | Example Value |
|------------|--------|----------------|
| `TOKEN` | `Bearer <value>` | `mytoken` |
| `HEADER` | Raw header value | `Bearer mytoken` |
| `BASIC` | `Basic <base64>` | `user:pass` |

### Scheme Specifier

Override the auth scheme per host:

```bash
HTTP_AUTH_SCHEME_example_com=bearer  # Default for TOKEN
HTTP_AUTH_SCHEME_example_com=basic  # Treat TOKEN value as user:pass
```

## Hostname Normalization

Hostnames are normalized before matching:

1. **Lowercase** - `EXAMPLE.COM` → `example.com`
2. **Dots to underscores** - `example.com` → `example_com`
3. **Port stripped** - `example.com:8080` → `example.com`

**Why underscores?**
- Periods (`.`) are not valid in Unix shell environment variable names
- Using underscores maintains shell compatibility

## Priority Order

When resolving authentication, sources are checked in this order:

1. **Exact host** - `HTTP_AUTH_TOKEN_example_com`
2. **Suffix match** - `HTTP_AUTH_TOKEN__example_com`
3. **Global** - `HTTP_AUTH_TOKEN`

## Examples

### Basic Usage

```bash
# Set token for specific host
export HTTP_AUTH_TOKEN_example_com=my-secret-token

# Result: Authorization: Bearer my-secret-token
```

### Suffix Matching

```bash
# Match any subdomain of example.com
export HTTP_AUTH_TOKEN__example_com=wildcard-token

# Matches: api.example.com, sub.example.com, example.com
```

### Multiple Hosts

```bash
export HTTP_AUTH_TOKEN_github_com=ghp_xxx
export HTTP_AUTH_TOKEN_gitlab_com=glpat-xxx
export HTTP_AUTH_TOKEN_awsamazonaws_com=AKIA_xxx
```

### Global Fallback

```bash
# Fallback for any host without specific config
export HTTP_AUTH_TOKEN=my-default-token
```

### Basic Authentication

```bash
# Basic auth with user:pass
export HTTP_AUTH_BASIC_example_com=admin:secret

# Result: Authorization: Basic YWRtaW46c2VjcmV0
```

### Custom Header

```bash
# Raw header value (used as-is)
export HTTP_AUTH_HEADER_example_com=CustomScheme credentials

# Result: Authorization: CustomScheme credentials
```

## Comparison to Alternatives

| Approach | Pros | Cons |
|----------|------|------|
| This convention | Portable, no deps, shell-compatible | Requires env var support |
| `.netrc` | Built into curl/ftp | Not shell-compatible, less secure |
| Config file | Structured, supports complex setups | File management required |
| Keyring | Secure | Requires setup, not portable |

## Adoption

This convention can be adopted by any tool that needs HTTP authentication. Implementations:

- **http-auth** (Python) - Full implementation with optional config/netrc/keyring
- BuildKit (Go) - Partial implementation
- Others are welcome to adopt

### Minimal Implementation Example (Python)

```python
import os

def get_auth(hostname: str) -> dict | None:
    # Normalize hostname
    host = hostname.lower().replace(".", "_").split(":")[0]

    # 1. Try exact match
    for var_type in ("TOKEN", "HEADER", "BASIC"):
        key = f"HTTP_AUTH_{var_type}_{host}"
        if value := os.environ.get(key):
            if var_type == "TOKEN":
                return {"Authorization": f"Bearer {value}"}
            elif var_type == "BASIC":
                import base64
                encoded = base64.b64encode(value.encode()).decode()
                return {"Authorization": f"Basic {encoded}"}
            return {"Authorization": value}

    # 2. Try suffix match
    for var_type in ("TOKEN", "HEADER", "BASIC"):
        key = f"HTTP_AUTH_{var_type}__{host.rsplit('_', 1)[0]}"
        if value := os.environ.get(key):
            # ... handle as above

    # 3. Try global
    if token := os.environ.get("HTTP_AUTH_TOKEN"):
        return {"Authorization": f"Bearer {token}"}

    return None
```

## Rationale

### Why Double Underscore for Suffix?

Single underscore (`_`) is a valid shell character used in exact matching. Double underscore (`__`) was chosen because:
- It's a valid shell character
- It's unambiguous (clearly different from single underscore)
- No escaping required in shell

### Why This Priority Order?

1. **Exact before suffix** - Most specific takes precedence
2. **Suffix before global** - Catch-all should be last resort

### Why No Wildcard Characters?

Traditional glob patterns (`*`, `?`) don't work in shell variable names. The suffix match (`__`) provides similar functionality while remaining shell-compatible.

## License

This specification is released into the public domain. Adopt freely.
