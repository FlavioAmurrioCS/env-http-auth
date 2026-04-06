from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from urllib.parse import urlparse

if TYPE_CHECKING:
    from typing import ClassVar
    from typing import Literal

    AuthSource = Literal["env", "config", "netrc", "keyring"]

logger = logging.getLogger(__name__)

SOURCE_PRIORITY: list[AuthSource] = ["env", "config", "netrc", "keyring"]


class AuthResolver:
    """Resolves HTTP authentication from multiple sources.

    The resolver tries sources in priority order until auth is found.

    Priority:
        1. Environment variables (exact host, suffix, global)
        2. Config file (~/.env-http-auth.ini)
        3. netrc (~/.netrc)
        4. System keyring

    Args:
        sources: Set of sources to enable. Default: all sources enabled.
        env_prefix: Prefix for environment variables. Default: "HTTP_AUTH"

    Example:
        >>> resolver = AuthResolver()
        >>> auth = resolver.for_url("https://example.com/path")
        >>> # Returns {'Authorization': 'Bearer ...'} or {}

        >>> # Enable specific sources
        >>> resolver = AuthResolver(sources={"env", "netrc"})
    """

    DEFAULT_SOURCES: ClassVar[set[AuthSource]] = {"env", "config", "netrc", "keyring"}

    def __init__(
        self,
        sources: set[AuthSource] | None = None,
        env_prefix: str = "HTTP_AUTH",
    ) -> None:
        self.sources = sources or self.DEFAULT_SOURCES.copy()
        self.env_prefix = env_prefix

    def for_url(self, url: str) -> dict[str, str]:
        """Get auth for a full URL.

        Args:
            url: The URL to get auth for.

        Returns:
            Dict with Authorization header or empty dict if not found.
        """
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return self.for_hostname(hostname)

    def for_hostname(self, hostname: str) -> dict[str, str]:
        """Get auth for a hostname.

        Args:
            hostname: The hostname to get auth for.

        Returns:
            Dict with Authorization header or empty dict if not found.
        """
        for source in SOURCE_PRIORITY:
            if source not in self.sources:
                continue
            result = self._try_source(source, hostname)
            if result:
                logger.debug(
                    "Found auth for %s from source: %s",
                    hostname,
                    source,
                )
                return result

        logger.debug("No auth found for %s", hostname)
        return {}

    def _try_source(self, source: str, hostname: str) -> dict[str, str] | None:
        """Try to get auth from a specific source."""
        if source == "env":
            from env_http_auth.env import get_auth_from_env

            return get_auth_from_env(hostname, self.env_prefix)
        if source == "netrc":
            from env_http_auth.netrc_ import get_auth_from_netrc

            return get_auth_from_netrc(hostname)
        if source == "keyring":
            from env_http_auth.keyring_ import get_auth_from_keyring

            return get_auth_from_keyring(hostname)
        if source == "config":
            from env_http_auth.config import get_auth_from_config

            return get_auth_from_config(hostname)
        logger.warning("Unknown auth source: %s", source)
        return None


def get_auth(url: str) -> dict[str, str]:
    """Get auth dict for a URL.

    This is a convenience function that uses the default AuthResolver.

    Args:
        url: The URL to get auth for.

    Returns:
        Dict with Authorization header or empty dict if not found.

    Example:
        >>> auth = get_auth("https://example.com/path")
        >>> # Returns {'Authorization': 'Bearer ...'} or {}
    """
    resolver = AuthResolver()
    return resolver.for_url(url)


def get_auth_header(url: str) -> str | None:
    """Get just the Authorization header value for a URL.

    Args:
        url: The URL to get auth for.

    Returns:
        Authorization header value or None if not found.

    Example:
        >>> header = get_auth_header("https://example.com/path")
        >>> # Returns 'Bearer ...' or None
    """
    auth = get_auth(url)
    if auth:
        return auth.get("Authorization")
    return None
