"""The in-container HTTP client for shell scripts. Replaced curl and jq in 3.2.1.

The runtime image no longer ships curl or jq: they served only the HEALTHCHECK,
start.sh and dev.sh, and both are handy tools for anyone who gets a shell in the
container. This does the four things those scripts need, with the standard
library only:

    python3 -m sage_is_ai.utils.localhttp [-X METHOD] [--json BODY|@-]
        [--bearer TOKEN] [--cookie-token TOKEN] [--field KEY]
        [--require-true KEY] [--wait-seconds N] URL

- ``--json @-`` reads the body from stdin, so a password never sits in argv.
- ``--field KEY`` prints one top-level JSON value (was ``sed``/``jq``).
- ``--require-true KEY`` exits 1 unless that value is ``true`` (HEALTHCHECK).
- ``--wait-seconds N`` retries a refused connection for up to N seconds.

Exit codes follow ``curl -f``: 0 for 2xx, 22 for an HTTP error status, 7 when
the server cannot be reached, 1 for a URL that is not http or https (curl's
unsupported protocol). Pinned by ``test_localhttp.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

EXIT_HTTP_ERROR = 22
EXIT_UNREACHABLE = 7
EXIT_UNSUPPORTED = 1


class _Unreachable(Exception):
    pass


def _parse(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="localhttp")
    p.add_argument("url")
    p.add_argument("-X", dest="method", default=None)
    p.add_argument("--json", dest="body", default=None)
    p.add_argument("--bearer", default=None)
    p.add_argument("--cookie-token", default=None)
    p.add_argument("--field", default=None)
    p.add_argument("--require-true", default=None)
    p.add_argument("--wait-seconds", type=float, default=0.0)
    p.add_argument("--timeout", type=float, default=30.0)
    return p.parse_args(argv)


def _request(a: argparse.Namespace) -> urllib.request.Request:
    data = None
    headers = {"Accept": "application/json"}
    if a.body is not None:
        data = (sys.stdin.read() if a.body == "@-" else a.body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if a.bearer:
        headers["Authorization"] = f"Bearer {a.bearer}"
    if a.cookie_token:
        headers["Cookie"] = f"token={a.cookie_token}"
    method = a.method or ("POST" if data is not None else "GET")
    return urllib.request.Request(a.url, data=data, headers=headers, method=method)


def _fetch(req: urllib.request.Request, timeout: float, wait_seconds: float) -> bytes:
    """The body, retrying a refused connection; HTTPError propagates at once."""
    deadline = time.monotonic() + wait_seconds
    while True:
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310 — main() admits only http and https URLs
                return r.read()
        except urllib.error.HTTPError:
            raise
        except (urllib.error.URLError, OSError) as e:
            if time.monotonic() >= deadline:
                raise _Unreachable(str(e)) from e
            time.sleep(1)


def _emit(a: argparse.Namespace, raw: bytes) -> int:
    if a.field is None and a.require_true is None:
        sys.stdout.write(raw.decode("utf-8", "replace"))
        return 0
    try:
        doc = json.loads(raw or b"null")
    except ValueError:
        doc = None
    if not isinstance(doc, dict):
        print("localhttp: response is not a JSON object", file=sys.stderr)
        return 1
    if a.require_true is not None and doc.get(a.require_true) is not True:
        return 1
    if a.field is None:
        return 0
    value = doc.get(a.field)
    if value is None:
        return 1
    print(value if isinstance(value, str) else json.dumps(value))
    return 0


def main(argv: list[str] | None = None) -> int:
    a = _parse(argv)
    if urllib.parse.urlsplit(a.url).scheme not in ("http", "https"):
        print(f"localhttp: only http and https URLs, not {a.url!r}", file=sys.stderr)
        return EXIT_UNSUPPORTED
    req = _request(a)
    try:
        raw = _fetch(req, a.timeout, a.wait_seconds)
    except urllib.error.HTTPError as e:
        print(
            f"localhttp: {req.get_method()} {a.url} -> HTTP {e.code}", file=sys.stderr
        )
        return EXIT_HTTP_ERROR
    except _Unreachable as e:
        print(f"localhttp: {a.url} unreachable: {e}", file=sys.stderr)
        return EXIT_UNREACHABLE
    return _emit(a, raw)


if __name__ == "__main__":
    sys.exit(main())
