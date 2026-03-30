from __future__ import annotations

import base64
import logging
import netrc
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def get_auth_from_netrc(hostname: str) -> dict[str, str] | None:
    """Get Basic auth from ~/.netrc for given hostname.

    Args:
        hostname: The hostname to look up auth for.

    Returns:
        Dict with Authorization header or None if not found.
    """
    try:
        netrc_path = os.environ.get("NETRC") or os.path.expanduser("~/.netrc")
        if not Path(netrc_path).exists():
            return None

        authenticators = netrc.netrc(netrc_path).authenticators(hostname)
        if authenticators:
            login, _, password = authenticators
            if login and password:
                credentials = f"{login}:{password}"
                encoded = base64.b64encode(credentials.encode()).decode()
                return {"Authorization": f"Basic {encoded}"}
    except netrc.NetrcParseError:
        logger.debug("Failed to parse netrc for %s", hostname)
    except OSError:
        logger.debug("Failed to read netrc for %s", hostname)
    return None
