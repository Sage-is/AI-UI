#!/usr/bin/env python3
"""The 3.3.0 look-back: did anyone use the holes F0 closes, in the logs we still have?

    python3 scripts/rootstock/lookback.py AUDIT.log [AUDIT.log ...]

Reads AI-UI audit logs (one JSON object per line: verb, request_uri, user,
response_status_code, request_object) and counts the requests that touched
each closed hole. It prints counts and URIs with their ids masked, never a
user's name, address or request body. Standard library only.
"""

import json
import re
import sys
from collections import Counter

HOLES = {
    "raw /openai proxy by a non-admin": lambda r: r["uri"].startswith("/openai/") and not r["admin"],
    "/api/v1/retrieval/query/* by a non-admin": lambda r: r["uri"].startswith("/api/v1/retrieval/query/") and not r["admin"],
    "bypass_filter= in a query string": lambda r: "bypass_filter=" in r["uri"],
    "internal= in a query string": lambda r: re.search(r"[?&]internal=", r["uri"]) is not None,
    "model_item carrying direct": lambda r: '"direct":true' in r["body"].lower().replace(" ", ""),
    "/cache/ path holding ..": lambda r: r["uri"].startswith("/cache/") and ".." in r["uri"],
}
ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}|\b\d{6,}\b")


def records(path):
    with open(path, errors="replace") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            user = rec.get("user") or {}
            role = user.get("role") if isinstance(user, dict) else None
            body = rec.get("request_object")
            yield {
                "uri": str(rec.get("request_uri") or ""),
                "admin": role == "admin",
                "body": body if isinstance(body, str) else json.dumps(body or {}),
                "ts": rec.get("timestamp"),
            }


def main(paths):
    hits = {name: Counter() for name in HOLES}
    total, first, last = 0, None, None
    for path in paths:
        for r in records(path):
            total += 1
            first = r["ts"] if first is None or (r["ts"] or 0) < first else first
            last = r["ts"] if last is None or (r["ts"] or 0) > last else last
            for name, test in HOLES.items():
                if test(r):
                    hits[name][ID.sub("<id>", r["uri"].split("?")[0])] += 1
    print(f"{total} audited requests" + (f", timestamps {first} to {last}" if total else ""))
    for name, counter in hits.items():
        print(f"- {name}: {sum(counter.values())}" + (": " + ", ".join(f"{u} x{n}" for u, n in counter.most_common(5)) if counter else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]) if sys.argv[1:] else print(__doc__))
