from __future__ import annotations

import base64
import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from http_auth import config

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture
def temp_config() -> Generator[Path, None, None]:
    """Create a temporary config file."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".ini", delete=False, prefix=".http-auth"
    ) as f:
        yield Path(f.name)
    os.unlink(f.name)


@pytest.fixture
def valid_config(temp_config: Path) -> Path:
    """Create a valid config file."""
    with open(temp_config, "w") as f:
        f.write("[example.com]\n")
        f.write("token = my-token\n")
        f.write("scheme = bearer\n")
        f.write("\n")
        f.write("[other.company.com]\n")
        f.write("basic_user = admin\n")
        f.write("basic_pass = secret\n")
        f.write("scheme = basic\n")
    return temp_config


class TestValidConfig:
    """Tests for valid config files."""

    def test_token_auth(self, valid_config: Path) -> None:
        result = config.get_auth_from_config("example.com", config_path=valid_config)
        assert result == {"Authorization": "Bearer my-token"}

    def test_basic_auth(self, valid_config: Path) -> None:
        result = config.get_auth_from_config("other.company.com", config_path=valid_config)
        expected = base64.b64encode(b"admin:secret").decode()
        assert result == {"Authorization": f"Basic {expected}"}

    def test_missing_host(self, valid_config: Path) -> None:
        result = config.get_auth_from_config("missing.com", config_path=valid_config)
        assert result is None


class TestConfigUnderscoreMatch:
    """Tests for underscore matching in config."""

    def test_underscore_match(self, valid_config: Path) -> None:
        result = config.get_auth_from_config("example.com", config_path=valid_config)
        assert result == {"Authorization": "Bearer my-token"}


class TestConfigMissingFile:
    """Tests for missing config file."""

    def test_missing_config(self) -> None:
        result = config.get_auth_from_config("example.com", config_path=Path("/nonexistent"))
        assert result is None


class TestConfigGlobPattern:
    """Tests for glob patterns in config."""

    @pytest.fixture
    def glob_config(self, temp_config: Path) -> Path:
        with open(temp_config, "w") as f:
            f.write("[*.example.com]\n")
            f.write("token = wildcard-token\n")
            f.write("scheme = bearer\n")
        return temp_config

    def test_glob_pattern(self, glob_config: Path) -> None:
        result = config.get_auth_from_config("sub.example.com", config_path=glob_config)
        assert result == {"Authorization": "Bearer wildcard-token"}


class TestConfigHeader:
    """Tests for custom header in config."""

    @pytest.fixture
    def header_config(self, temp_config: Path) -> Path:
        with open(temp_config, "w") as f:
            f.write("[example.com]\n")
            f.write("header = CustomScheme credentials\n")
        return temp_config

    def test_custom_header(self, header_config: Path) -> None:
        result = config.get_auth_from_config("example.com", config_path=header_config)
        assert result == {"Authorization": "CustomScheme credentials"}


class TestConfigIntegration:
    """Integration tests for config with resolver."""

    def test_resolver_uses_config(self, valid_config: Path) -> None:
        from http_auth import resolver

        res = resolver.AuthResolver(sources={"config"})
        with mock.patch.object(config, "DEFAULT_CONFIG_PATH", valid_config):
            result = res.for_hostname("example.com")
        assert result == {"Authorization": "Bearer my-token"}
