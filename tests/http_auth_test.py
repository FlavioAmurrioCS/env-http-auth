from __future__ import annotations

from typing import TYPE_CHECKING
from unittest import mock

from http_auth import http_auth

if TYPE_CHECKING:
    import pytest


class TestHTTPEnvAuthRequests:
    """Tests for HTTPEnvAuth with requests library."""

    def test_requests_integration_with_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_AUTH_TOKEN_example_com", "requests-token")
        http_env = http_auth.HTTPEnvAuth()

        mock_prepared = mock.MagicMock()
        mock_prepared.url = "https://example.com/api/v1"
        mock_prepared.headers.get.return_value = None
        result = http_env(mock_prepared)

        mock_prepared.headers.__setitem__.assert_called_once_with(
            "Authorization", "Bearer requests-token"
        )

    def test_requests_integration_no_match(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HTTP_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("HTTP_AUTH_HEADER", raising=False)
        monkeypatch.delenv("HTTP_AUTH", raising=False)
        http_env = http_auth.HTTPEnvAuth(sources=set())

        mock_prepared = mock.MagicMock()
        mock_prepared.url = "https://example.com/path"
        http_env(mock_prepared)

        mock_prepared.headers.__setitem__.assert_not_called()

    def test_requests_integration_returns_request(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_AUTH_TOKEN_example_com", "token")
        http_env = http_auth.HTTPEnvAuth()

        mock_prepared = mock.MagicMock()
        mock_prepared.url = "https://example.com/path"
        result = http_env(mock_prepared)

        assert result is mock_prepared


class TestHTTPEnvAuthHttpx:
    """Tests for HTTPEnvAuth with httpx library."""

    def test_httpx_integration_with_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_AUTH_TOKEN_example_com", "httpx-token")
        http_env = http_auth.HTTPEnvAuth()

        mock_request = mock.MagicMock()
        mock_request.url.host = "example.com"
        mock_request.headers.get.return_value = None
        http_env(mock_request)

        mock_request.headers.__setitem__.assert_called_once_with(
            "Authorization", "Bearer httpx-token"
        )

    def test_httpx_integration_no_match(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HTTP_AUTH_TOKEN", raising=False)
        http_env = http_auth.HTTPEnvAuth(sources=set())

        mock_request = mock.MagicMock()
        mock_request.url.host = "example.com"
        http_env(mock_request)

        mock_request.headers.__setitem__.assert_not_called()

    def test_httpx_integration_returns_request(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_AUTH_TOKEN_example_com", "token")
        http_env = http_auth.HTTPEnvAuth()

        mock_request = mock.MagicMock()
        mock_request.url.host = "example.com"
        result = http_env(mock_request)

        assert result is mock_request


class TestHTTPEnvAuthIntegration:
    """Integration tests for HTTPEnvAuth."""

    def test_custom_sources(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_AUTH_TOKEN_example_com", "custom-token")
        http_env = http_auth.HTTPEnvAuth(sources={"env"})

        mock_prepared = mock.MagicMock()
        mock_prepared.url = "https://example.com/path"
        mock_prepared.headers.get.return_value = None
        http_env(mock_prepared)

        mock_prepared.headers.__setitem__.assert_called_once()

    def test_preserves_user_set_authorization(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """If user explicitly set Authorization header, preserve it."""
        monkeypatch.setenv("HTTP_AUTH_TOKEN_example_com", "env-token")
        http_env = http_auth.HTTPEnvAuth()

        mock_prepared = mock.MagicMock()
        mock_prepared.url = "https://example.com/path"
        mock_prepared.headers.get.return_value = "User-Token"
        http_env(mock_prepared)

        mock_prepared.headers.__setitem__.assert_not_called()
