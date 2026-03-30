from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Any
from urllib.parse import urlparse

from http_auth.resolver import AuthResolver

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from typing import Literal

    AuthSource = Literal["env", "config", "netrc", "keyring"]


class HTTPEnvAuth:
    """Auto-resolving auth for requests and httpx.

    This auth class automatically resolves HTTP authentication from environment
    variables, netrc, keyring, or config file based on the request URL.

    Works with both requests and httpx libraries.

    Optional extras:
        - requests: pip install http-auth[requests]
        - httpx: pip install http-auth[httpx]

    Example:
        >>> # With requests
        >>> import requests
        >>> from http_auth import HTTPEnvAuth
        >>> # Set env var: HTTP_AUTH_TOKEN_example_com=my-token
        >>> requests.get("https://example.com/path", auth=HTTPEnvAuth())

        >>> # With httpx
        >>> import httpx
        >>> client = httpx.Client(auth=HTTPEnvAuth())
        >>> client.get("https://example.com/path")
    """

    def __init__(self, sources: set[AuthSource] | None = None) -> None:
        self.resolver = AuthResolver(sources=sources)

    def __call__(self, request: object) -> Any:
        existing_auth = getattr(request, "headers", {}).get("Authorization")
        if existing_auth:
            return request

        hostname = self._extract_hostname(request)
        auth = self.resolver.for_hostname(hostname)
        auth_header = auth.get("Authorization") if auth else None
        if auth_header:
            headers: dict[str, str] = getattr(request, "headers", {})
            headers["Authorization"] = auth_header
        return request

    def _extract_hostname(self, request: object) -> str:
        url = getattr(request, "url", None)
        if url is not None:
            host = getattr(url, "host", None)
            if host is not None:
                return host

        url_str = str(getattr(request, "url", ""))
        return urlparse(url_str).hostname or ""
