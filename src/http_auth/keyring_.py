from __future__ import annotations

import base64
import logging

logger = logging.getLogger(__name__)


def get_auth_from_keyring(hostname: str) -> dict[str, str] | None:
    """Get auth from system keyring.

    Args:
        hostname: The hostname to look up auth for.

    Returns:
        Dict with Authorization header or None if not found.
    """
    try:
        import keyring

        service = f"http-auth:{hostname}"

        token = keyring.get_password(service, "token")
        if token:
            return {"Authorization": f"Bearer {token}"}

        username = keyring.get_password(service, "username")
        password = keyring.get_password(service, "password")
        if username and password:
            credentials = f"{username}:{password}"
            encoded = base64.b64encode(credentials.encode()).decode()
            return {"Authorization": f"Basic {encoded}"}

    except ImportError:
        logger.debug("keyring not installed, skipping")
    except KeyError:
        logger.debug("Failed to read keyring for %s", hostname)
    except OSError:
        logger.debug("Failed to read keyring for %s", hostname)

    return None
