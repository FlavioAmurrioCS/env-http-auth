from __future__ import annotations

import subprocess

import pytest

from env_http_auth import __main__


class TestCLI:
    """Tests for CLI."""

    def test_cli_with_auth(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_AUTH_TOKEN_example_com", "cli-token")
        result = __main__.main(["https://example.com"])
        assert result == 0

    def test_cli_no_auth(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HTTP_AUTH_TOKEN", raising=False)
        monkeypatch.delenv("HTTP_AUTH_HEADER", raising=False)
        monkeypatch.delenv("HTTP_AUTH", raising=False)
        # Function returns 1 when no auth found, doesn't raise
        result = __main__.main(["https://example.com"])
        assert result == 1

    def test_cli_no_args(self) -> None:
        with pytest.raises(SystemExit) as exc_info:
            __main__.main([])
        # argparse exits with 2 when required args missing
        assert exc_info.value.code == 2


class TestCLIHeaderOnly:
    """Tests for --header-only flag."""

    def test_header_only(
        self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
    ) -> None:
        monkeypatch.setenv("HTTP_AUTH_TOKEN_example_com", "token-value")
        result = __main__.main(["--header-only", "https://example.com"])
        captured = capsys.readouterr()
        assert "token-value" in captured.out
        assert result == 0


class TestCLIIntegration:
    """Integration tests for CLI entry point."""

    def test_entry_point(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("HTTP_AUTH_TOKEN_example_com", "entry-token")
        result = subprocess.run(
            ["python", "-m", "env_http_auth", "https://example.com"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Bearer entry-token" in result.stdout

    def test_entry_point_no_auth(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("HTTP_AUTH_TOKEN", raising=False)
        result = subprocess.run(
            ["python", "-m", "env_http_auth", "https://example.com"],
            check=False,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
