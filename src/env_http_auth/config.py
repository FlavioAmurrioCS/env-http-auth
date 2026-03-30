from __future__ import annotations

import base64
import configparser
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from configparser import SectionProxy

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path(os.path.expanduser("~/.env-http-auth.ini"))


def get_auth_from_config(
    hostname: str,
    config_path: Path | None = None,
) -> dict[str, str] | None:
    """Get auth from INI config file.

    Config file format (~/.env-http-auth.ini):
        [example.com]
        token = my-token
        scheme = bearer

        [other.company.com]
        basic_user = admin
        basic_pass = secret
        scheme = basic

    Args:
        hostname: The hostname to look up auth for.
        config_path: Path to config file. Default: ~/.env-http-auth.ini

    Returns:
        Dict with Authorization header or None if not found.
    """
    path = config_path or DEFAULT_CONFIG_PATH
    if not path.exists():
        return None

    config = configparser.ConfigParser()
    config.read(path)

    if hostname in config:
        return _parse_config_section(config[hostname])

    normalized = hostname.replace(".", "_")
    if normalized in config:
        return _parse_config_section(config[normalized])

    for section_name in config.sections():
        if _matches_pattern(hostname, section_name):
            return _parse_config_section(config[section_name])

    return None


def _matches_pattern(hostname: str, pattern: str) -> bool:
    """Check if hostname matches a glob pattern in section name."""
    import fnmatch

    return fnmatch.fnmatch(hostname, pattern) or fnmatch.fnmatch(
        hostname, pattern.replace("_", ".")
    )


def _parse_config_section(section: SectionProxy) -> dict[str, str] | None:
    """Parse a config section to auth header."""
    if token := section.get("token"):
        scheme = section.get("scheme", "bearer").lower()
        if scheme == "bearer":
            return {"Authorization": f"Bearer {token}"}
        if scheme == "basic":
            encoded = base64.b64encode(token.encode()).decode()
            return {"Authorization": f"Basic {encoded}"}
        return {"Authorization": token}

    if header := section.get("header"):
        return {"Authorization": header}

    if basic_user := section.get("basic_user"):
        basic_pass = section.get("basic_pass", "")
        credentials = f"{basic_user}:{basic_pass}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {"Authorization": f"Basic {encoded}"}

    return None
