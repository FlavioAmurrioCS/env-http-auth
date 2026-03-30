from __future__ import annotations

import base64
import os
import tempfile
from typing import TYPE_CHECKING

import pytest

from env_http_auth import netrc_

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def temp_netrc() -> Generator[str, None, None]:
    """Create a temporary netrc file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".netrc", delete=False) as f:
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def valid_netrc(temp_netrc: str) -> str:
    """Create a valid netrc file."""
    with open(temp_netrc, "w") as f:
        f.write("machine example.com\n")
        f.write("login admin\n")
        f.write("password secret123\n")
    os.chmod(temp_netrc, 0o600)
    return temp_netrc


@pytest.fixture
def no_credentials_netrc(temp_netrc: str) -> str:
    """Create a netrc file without credentials for the host."""
    with open(temp_netrc, "w") as f:
        f.write("machine other.com\n")
        f.write("login otheruser\n")
        f.write("password otherpass\n")
    os.chmod(temp_netrc, 0o600)
    return temp_netrc


class TestValidNetrc:
    """Tests for valid netrc files."""

    def test_valid_netrc(self, valid_netrc: str, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("NETRC", valid_netrc)
        result = netrc_.get_auth_from_netrc("example.com")
        expected = base64.b64encode(b"admin:secret123").decode()
        assert result == {"Authorization": f"Basic {expected}"}

    def test_different_host_returns_none(
        self, valid_netrc: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("NETRC", valid_netrc)
        result = netrc_.get_auth_from_netrc("other.com")
        assert result is None


class TestMissingNetrc:
    """Tests for missing netrc file."""

    def test_missing_netrc(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("NETRC", raising=False)
        monkeypatch.setenv("HOME", "/nonexistent")
        result = netrc_.get_auth_from_netrc("example.com")
        assert result is None


class TestNoCredentials:
    """Tests for netrc without credentials for host."""

    def test_no_credentials_for_host(
        self, no_credentials_netrc: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("NETRC", no_credentials_netrc)
        result = netrc_.get_auth_from_netrc("example.com")
        assert result is None


class TestDefaultNetrcPath:
    """Tests for default netrc path."""

    def test_default_path(self, valid_netrc: str, monkeypatch: pytest.MonkeyPatch) -> None:
        # The netrc module looks for ~/.netrc, so we need to set HOME
        # to the directory containing the temp netrc file
        import os

        home_dir = os.path.dirname(valid_netrc)
        # Create a symlink or copy to ~/.netrc in that home
        import shutil

        netrc_path = os.path.join(home_dir, ".netrc")
        shutil.copy(valid_netrc, netrc_path)
        os.chmod(netrc_path, 0o600)
        monkeypatch.setenv("HOME", home_dir)
        monkeypatch.delenv("NETRC", raising=False)
        result = netrc_.get_auth_from_netrc("example.com")
        expected = base64.b64encode(b"admin:secret123").decode()
        assert result == {"Authorization": f"Basic {expected}"}


class TestNetrcIntegration:
    """Integration tests for netrc with resolver."""

    def test_resolver_uses_netrc(self, valid_netrc: str, monkeypatch: pytest.MonkeyPatch) -> None:
        from env_http_auth import resolver

        monkeypatch.setenv("NETRC", valid_netrc)
        res = resolver.AuthResolver(sources={"netrc"})
        result = res.for_hostname("example.com")
        expected = base64.b64encode(b"admin:secret123").decode()
        assert result == {"Authorization": f"Basic {expected}"}
