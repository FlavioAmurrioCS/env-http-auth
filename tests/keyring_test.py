from __future__ import annotations

import base64
from unittest import mock

from env_http_auth import keyring_


class TestKeyringToken:
    """Tests for keyring token retrieval."""

    @mock.patch("keyring.get_password")
    def test_token_found(self, mock_get_password: mock.MagicMock) -> None:
        mock_get_password.return_value = "my-secret-token"
        result = keyring_.get_auth_from_keyring("example.com")
        mock_get_password.assert_called_with("example.com", "token")
        assert result == {"Authorization": "Bearer my-secret-token"}

    @mock.patch("keyring.get_password")
    def test_token_priority_over_basic(self, mock_get_password: mock.MagicMock) -> None:
        mock_get_password.side_effect = ["token-value", "user", "pass"]
        result = keyring_.get_auth_from_keyring("example.com")
        assert result == {"Authorization": "Bearer token-value"}


class TestKeyringBasic:
    """Tests for keyring basic auth retrieval."""

    @mock.patch("keyring.get_password")
    def test_basic_auth_found(self, mock_get_password: mock.MagicMock) -> None:
        mock_get_password.side_effect = [None, "admin", "secret123"]
        result = keyring_.get_auth_from_keyring("example.com")
        expected = base64.b64encode(b"admin:secret123").decode()
        assert result == {"Authorization": f"Basic {expected}"}

    @mock.patch("keyring.get_password")
    def test_no_credentials(self, mock_get_password: mock.MagicMock) -> None:
        mock_get_password.return_value = None
        result = keyring_.get_auth_from_keyring("example.com")
        assert result is None


class TestKeyringErrors:
    """Tests for keyring error handling."""

    @mock.patch("keyring.get_password")
    def test_keyring_not_installed(self, mock_get_password: mock.MagicMock) -> None:
        mock_get_password.side_effect = ImportError()
        result = keyring_.get_auth_from_keyring("example.com")
        assert result is None

    @mock.patch("keyring.get_password")
    def test_keyring_key_error(self, mock_get_password: mock.MagicMock) -> None:
        mock_get_password.side_effect = KeyError("service")
        result = keyring_.get_auth_from_keyring("example.com")
        assert result is None

    @mock.patch("keyring.get_password")
    def test_keyring_os_error(self, mock_get_password: mock.MagicMock) -> None:
        mock_get_password.side_effect = OSError("No keyring available")
        result = keyring_.get_auth_from_keyring("example.com")
        assert result is None


class TestKeyringIntegration:
    """Integration tests for keyring with resolver."""

    @mock.patch("keyring.get_password")
    def test_resolver_uses_keyring(self, mock_get_password: mock.MagicMock) -> None:
        from env_http_auth import resolver

        mock_get_password.return_value = "resolver-token"
        res = resolver.AuthResolver(sources={"keyring"})
        result = res.for_hostname("example.com")
        assert result == {"Authorization": "Bearer resolver-token"}
