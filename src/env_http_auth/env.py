from __future__ import annotations

import base64
import os


def normalize_hostname(hostname: str) -> str:
    """Normalize hostname for env var matching.

    - Remove port number
    - Convert to lowercase
    - Replace dots with underscores for env var compatibility
    """
    host_part = hostname.split(":", maxsplit=1)[0].lower()
    return host_part.replace(".", "_")


def get_auth_from_env(hostname: str, env_prefix: str = "HTTP_AUTH") -> dict[str, str] | None:
    """Get auth from environment variables for given hostname.

    Priority order:
    1. Exact host match (HTTP_AUTH_TOKEN_example_com)
    2. Glob/prefix match (HTTP_AUTH_TOKEN_*.example_com)
    3. Global env vars (HTTP_AUTH_TOKEN, HTTP_AUTH_HEADER, HTTP_AUTH)

    Args:
        hostname: The hostname to look up auth for.
        env_prefix: Prefix for environment variables. Default: "HTTP_AUTH"

    Returns:
        Dict with Authorization header or None if not found.
    """
    normalized = normalize_hostname(hostname)

    result = _try_exact_host(normalized, env_prefix)
    if result:
        return result

    result = _try_suffix_match(hostname, env_prefix)
    if result:
        return result

    result = _try_global_env(env_prefix)
    if result:
        return result

    return None


def _try_exact_host(normalized: str, env_prefix: str = "HTTP_AUTH") -> dict[str, str] | None:
    """Try exact host matching for env vars."""
    prefix_upper = f"{env_prefix.upper()}_"
    auth_env_vars = {
        k.upper(): v for k, v in os.environ.items() if k.upper().startswith(prefix_upper)
    }

    for var_type in ("TOKEN", "HEADER", "BASIC"):
        pattern = f"{env_prefix.upper()}_{var_type}_{normalized}"
        value = auth_env_vars.get(pattern.upper())
        if value:
            return _build_auth_header(var_type, value)

    scheme_pattern = f"{env_prefix.upper()}_SCHEME_{normalized}"
    scheme = auth_env_vars.get(scheme_pattern.upper())
    if scheme:
        return _try_scheme_auth(scheme, normalized, env_prefix)

    return None


def _try_suffix_match(hostname: str, env_prefix: str = "HTTP_AUTH") -> dict[str, str] | None:
    """Try suffix matching for environment variables.

    Double underscore (__) indicates suffix matching:
    - HTTP_AUTH_TOKEN__example_com matches example.com, sub.example.com, api.example.com
    """
    normalized = normalize_hostname(hostname)

    for var_type in ("TOKEN", "HEADER", "BASIC"):
        suffix_prefix = f"{env_prefix}_{var_type}__"

        for env_name, env_value in os.environ.items():
            if not env_name.startswith(suffix_prefix):
                continue

            pattern = env_name[len(suffix_prefix) :]
            if _matches_suffix(normalized, hostname, pattern):
                return _build_auth_header(var_type, env_value)

    return None


def _matches_suffix(normalized: str, hostname: str, pattern: str) -> bool:
    """Check if hostname ends with the pattern (suffix match).

    The pattern comes from the env var name after HTTP_AUTH_TOKEN__ or similar.
    """
    suffix = pattern.lower()
    return normalized.endswith(suffix) or hostname.lower().endswith(suffix.replace("_", "."))


def _try_global_env(env_prefix: str = "HTTP_AUTH") -> dict[str, str] | None:
    """Try global environment variables."""
    for var in (f"{env_prefix}_TOKEN", f"{env_prefix}_HEADER", env_prefix):
        if value := os.environ.get(var):
            if "TOKEN" in var:
                return {"Authorization": f"Bearer {value}"}
            return {"Authorization": value}
    return None


def _try_scheme_auth(
    scheme: str, normalized: str, env_prefix: str = "HTTP_AUTH"
) -> dict[str, str] | None:
    """Try to get auth using scheme specifier. Expects normalized hostname."""
    token_var = f"{env_prefix}_TOKEN_{normalized}"
    token = os.environ.get(token_var)

    if token:
        scheme_lower = scheme.lower()
        if scheme_lower == "bearer":
            return {"Authorization": f"Bearer {token}"}
        if scheme_lower == "basic":
            encoded = base64.b64encode(token.encode()).decode()
            return {"Authorization": f"Basic {encoded}"}
        return {"Authorization": token}

    basic_user_var = f"{env_prefix}_BASIC_{normalized}_USER"
    basic_pass_var = f"{env_prefix}_BASIC_{normalized}_PASS"
    user = os.environ.get(basic_user_var)
    password = os.environ.get(basic_pass_var)

    if user and password:
        credentials = f"{user}:{password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    return None


def _build_auth_header(var_type: str, value: str) -> dict[str, str]:
    """Build Authorization header based on variable type."""
    if var_type == "TOKEN":
        return {"Authorization": f"Bearer {value}"}
    if var_type == "BASIC":
        encoded = base64.b64encode(value.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}
    return {"Authorization": value}


def get_auth_header_from_env(hostname: str, env_prefix: str = "HTTP_AUTH") -> str | None:
    """Get just the Authorization header value from environment variables.

    Args:
        hostname: The hostname to look up auth for.
        env_prefix: Prefix for environment variables. Default: "HTTP_AUTH"

    Returns:
        Authorization header value or None if not found.
    """
    auth = get_auth_from_env(hostname, env_prefix)
    if auth:
        return auth.get("Authorization")
    return None
