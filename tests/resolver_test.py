from __future__ import annotations

from typing import TYPE_CHECKING

from env_http_auth import resolver

if TYPE_CHECKING:
    import pytest


class TestAuthResolver:
    """Tests for AuthResolver class."""

    def test_for_url_basic(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_AUTH_TOKEN_example_com", "test-token")
        res = resolver.AuthResolver()
        result = res.for_url("https://example.com/path")
        assert result == {"Authorization": "Bearer test-token"}

    def test_for_url_extracts_hostname(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_AUTH_TOKEN_example_com", "test-token")
        res = resolver.AuthResolver()
        result = res.for_url("https://example.com:8080/api/v1")
        assert result == {"Authorization": "Bearer test-token"}

    def test_for_url_no_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_AUTH_TOKEN_example_com", "test-token")
        res = resolver.AuthResolver()
        result = res.for_url("https://example.com")
        assert result == {"Authorization": "Bearer test-token"}

    def test_for_hostname(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_AUTH_TOKEN_example_com", "test-token")
        res = resolver.AuthResolver()
        result = res.for_hostname("example.com")
        assert result == {"Authorization": "Bearer test-token"}

    def test_empty_result_no_auth(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HTTP_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("HTTP_AUTH_HEADER", raising=False)
        monkeypatch.delenv("HTTP_AUTH", raising=False)
        res = resolver.AuthResolver(sources=set())
        result = res.for_hostname("example.com")
        assert result == {}

    def test_custom_sources(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_AUTH_TOKEN_example_com", "test-token")
        res = resolver.AuthResolver(sources={"env"})
        result = res.for_hostname("example.com")
        assert result == {"Authorization": "Bearer test-token"}


class TestPriorityChain:
    """Tests for priority chain."""

    def test_env_first_priority(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_AUTH_TOKEN_example_com", "env-token")
        res = resolver.AuthResolver()
        result = res.for_hostname("example.com")
        assert result == {"Authorization": "Bearer env-token"}


class TestGetAuthFunction:
    """Tests for get_auth convenience function."""

    def test_get_auth_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_AUTH_TOKEN_example_com", "test-token")
        result = resolver.get_auth("https://example.com/path")
        assert result == {"Authorization": "Bearer test-token"}

    def test_get_auth_returns_empty_when_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HTTP_AUTH_TOKEN", raising=False)
        result = resolver.get_auth("https://example.com/path")
        assert result == {}


class TestGetAuthHeaderFunction:
    """Tests for get_auth_header convenience function."""

    def test_get_auth_header(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_AUTH_TOKEN_example_com", "test-token")
        result = resolver.get_auth_header("https://example.com/path")
        assert result == "Bearer test-token"

    def test_get_auth_header_returns_none_when_not_found(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("HTTP_AUTH_TOKEN", raising=False)
        result = resolver.get_auth_header("https://example.com/path")
        assert result is None


class TestEnvPrefix:
    """Tests for custom env_prefix."""

    def test_custom_prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MYAUTH_TOKEN_example_com", "custom-token")
        res = resolver.AuthResolver(env_prefix="MYAUTH")
        result = res.for_hostname("example.com")
        assert result == {"Authorization": "Bearer custom-token"}
