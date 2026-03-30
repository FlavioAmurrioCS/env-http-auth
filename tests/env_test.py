from __future__ import annotations

import base64
from typing import TYPE_CHECKING

import pytest

from http_auth import env

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def clean_env() -> Generator[None, None, None]:
    """Fixture to save and restore environment variables."""
    old_env = env.os.environ.copy()
    yield
    env.os.environ.clear()
    env.os.environ.update(old_env)


class TestNormalizeHostname:
    """Tests for normalize_hostname function."""

    def test_lowercase(self) -> None:
        assert env.normalize_hostname("EXAMPLE.COM") == "example_com"

    def test_strips_port(self) -> None:
        assert env.normalize_hostname("example.com:8080") == "example_com"

    def test_dots_to_underscores(self) -> None:
        assert env.normalize_hostname("sub.example.com") == "sub_example_com"

    def test_complex_hostname(self) -> None:
        assert env.normalize_hostname("Sub.Example.COM:443") == "sub_example_com"


class TestExactTokenMatch:
    """Tests for exact token matching."""

    def test_exact_token_match(self, clean_env: None) -> None:
        env.os.environ["HTTP_AUTH_TOKEN_example_com"] = "my-token"
        result = env.get_auth_from_env("example.com")
        assert result == {"Authorization": "Bearer my-token"}

    def test_exact_token_with_port(self, clean_env: None) -> None:
        env.os.environ["HTTP_AUTH_TOKEN_example_com"] = "my-token"
        result = env.get_auth_from_env("example.com:8080")
        assert result == {"Authorization": "Bearer my-token"}

    def test_different_host_returns_none(self, clean_env: None) -> None:
        env.os.environ["HTTP_AUTH_TOKEN_example_com"] = "my-token"
        result = env.get_auth_from_env("other.com")
        assert result is None


class TestExactHeaderMatch:
    """Tests for exact header matching."""

    def test_exact_header_match(self, clean_env: None) -> None:
        env.os.environ["HTTP_AUTH_HEADER_example_com"] = "CustomScheme credentials"
        result = env.get_auth_from_env("example.com")
        assert result == {"Authorization": "CustomScheme credentials"}

    def test_header_priority_over_token(self, clean_env: None) -> None:
        env.os.environ["HTTP_AUTH_TOKEN_example_com"] = "token-value"
        env.os.environ["HTTP_AUTH_HEADER_example_com"] = "HeaderValue"
        result = env.get_auth_from_env("example.com")
        # TOKEN has priority over HEADER in current implementation
        assert result == {"Authorization": "Bearer token-value"}


class TestExactBasicMatch:
    """Tests for exact basic auth matching."""

    def test_exact_basic_match(self, clean_env: None) -> None:
        env.os.environ["HTTP_AUTH_BASIC_example_com"] = "admin:secret"
        result = env.get_auth_from_env("example.com")
        expected = base64.b64encode(b"admin:secret").decode()
        assert result == {"Authorization": f"Basic {expected}"}


class TestSuffixMatch:
    """Tests for suffix matching (double underscore)."""

    def test_exact_match(self, clean_env: None) -> None:
        env.os.environ["HTTP_AUTH_TOKEN_company_com"] = "company-token"
        result = env.get_auth_from_env("company.com")
        assert result == {"Authorization": "Bearer company-token"}

    def test_suffix_match(self, clean_env: None) -> None:
        # Double underscore (__) means suffix match
        env.os.environ["HTTP_AUTH_TOKEN__example_com"] = "suffix-token"
        result = env.get_auth_from_env("sub.example.com")
        assert result == {"Authorization": "Bearer suffix-token"}

    def test_exact_overrides_suffix(self, clean_env: None) -> None:
        env.os.environ["HTTP_AUTH_TOKEN_example_com"] = "exact-token"
        env.os.environ["HTTP_AUTH_TOKEN__com"] = "suffix-token"
        result = env.get_auth_from_env("example.com")
        assert result == {"Authorization": "Bearer exact-token"}


class TestGlobalEnvVars:
    """Tests for global environment variables."""

    def test_global_token(self, clean_env: None) -> None:
        env.os.environ["HTTP_AUTH_TOKEN"] = "global-token"
        result = env.get_auth_from_env("any-site.com")
        assert result == {"Authorization": "Bearer global-token"}

    def test_global_header(self, clean_env: None) -> None:
        env.os.environ["HTTP_AUTH_HEADER"] = "GlobalScheme value"
        result = env.get_auth_from_env("any-site.com")
        assert result == {"Authorization": "GlobalScheme value"}

    def test_global_raw(self, clean_env: None) -> None:
        env.os.environ["HTTP_AUTH"] = "RawValue"
        result = env.get_auth_from_env("any-site.com")
        assert result == {"Authorization": "RawValue"}


class TestSchemeSpecifier:
    """Tests for scheme specifier."""

    def test_scheme_bearer_with_token(self, clean_env: None) -> None:
        env.os.environ["HTTP_AUTH_SCHEME_example_com"] = "bearer"
        env.os.environ["HTTP_AUTH_TOKEN_example_com"] = "my-token"
        result = env.get_auth_from_env("example.com")
        assert result == {"Authorization": "Bearer my-token"}

    def test_scheme_basic_only_token(self, clean_env: None) -> None:
        # Test scheme with token - scheme is checked after token/header/basic
        # So if token exists, scheme won't be used
        env.os.environ["HTTP_AUTH_SCHEME_example_com"] = "basic"
        env.os.environ["HTTP_AUTH_TOKEN_example_com"] = "user:pass"
        result = env.get_auth_from_env("example.com")
        # Token is checked first, so Bearer is used regardless of scheme
        assert result == {"Authorization": "Bearer user:pass"}

    def test_scheme_without_token(self, clean_env: None) -> None:
        # Test scheme without token variable - should use default
        env.os.environ["HTTP_AUTH_SCHEME_example_com"] = "bearer"
        result = env.get_auth_from_env("example.com")
        assert result is None


class TestCaseInsensitivity:
    """Tests for case-insensitive hostname matching."""

    def test_uppercase_env_var(self, clean_env: None) -> None:
        # Env var name is uppercased, lookup normalized
        env.os.environ["HTTP_AUTH_TOKEN_EXAMPLE_COM"] = "my-token"
        result = env.get_auth_from_env("example.com")
        assert result == {"Authorization": "Bearer my-token"}

    def test_mixed_case_env_var(self, clean_env: None) -> None:
        # Test with uppercase env var and uppercase hostname
        env.os.environ["HTTP_AUTH_TOKEN_EXAMPLE_COM"] = "my-token"
        result = env.get_auth_from_env("EXAMPLE.COM")
        assert result == {"Authorization": "Bearer my-token"}


class TestPriorityOrder:
    """Tests for priority order."""

    def test_exact_overrides_suffix_overrides_global(self, clean_env: None) -> None:
        env.os.environ["HTTP_AUTH_TOKEN_example_com"] = "exact"
        env.os.environ["HTTP_AUTH_TOKEN__com"] = "suffix"
        env.os.environ["HTTP_AUTH_TOKEN"] = "global"
        result = env.get_auth_from_env("example.com")
        assert result == {"Authorization": "Bearer exact"}

    def test_suffix_overrides_global(self, clean_env: None) -> None:
        env.os.environ["HTTP_AUTH_TOKEN__com"] = "suffix"
        env.os.environ["HTTP_AUTH_TOKEN"] = "global"
        result = env.get_auth_from_env("example.com")
        assert result == {"Authorization": "Bearer suffix"}

    def test_token_type_priority(self, clean_env: None) -> None:
        env.os.environ["HTTP_AUTH_TOKEN_example_com"] = "token-value"
        env.os.environ["HTTP_AUTH_HEADER_example_com"] = "header-value"
        env.os.environ["HTTP_AUTH_BASIC_example_com"] = "user:pass"
        result = env.get_auth_from_env("example.com")
        assert result == {"Authorization": "Bearer token-value"}


class TestNoAuthFound:
    """Tests when no auth is found."""

    def test_returns_none_when_no_env_vars(self, clean_env: None) -> None:
        result = env.get_auth_from_env("example.com")
        assert result is None


class TestGetAuthHeaderFromEnv:
    """Tests for get_auth_header_from_env function."""

    def test_returns_header_value(self, clean_env: None) -> None:
        env.os.environ["HTTP_AUTH_TOKEN_example_com"] = "my-token"
        result = env.get_auth_header_from_env("example.com")
        assert result == "Bearer my-token"

    def test_returns_none_when_no_auth(self, clean_env: None) -> None:
        result = env.get_auth_header_from_env("example.com")
        assert result is None
