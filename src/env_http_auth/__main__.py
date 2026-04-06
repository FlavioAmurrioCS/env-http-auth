from __future__ import annotations

import argparse
import sys

from env_http_auth import get_auth_header


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Get HTTP authentication header for a URL",
    )
    parser.add_argument(
        "url",
        help="URL to get authentication header for",
    )
    parser.add_argument(
        "--header-only",
        action="store_true",
        help="Output only the header value (without 'Authorization: ' prefix)",
    )
    args = parser.parse_args(argv)

    header = get_auth_header(args.url)
    if header is None:
        print(f"No authentication found for {args.url}", file=sys.stderr)
        return 1

    if args.header_only:
        print(header)
    else:
        print(f"Authorization: {header}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
