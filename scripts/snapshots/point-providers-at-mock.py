#!/usr/bin/env python3
"""Point every OpenAI-compatible connection in a webui.db COPY at a mock provider.

The surface-budget gate measures bytes. With the snapshot's real provider URLs,
`/api/models` fetched the live catalogs on every run, so the floor grew with the
calendar, not the code, and the snapshot's production keys left on every run
(card "The SPA floor crept 539 kB unnoticed"). After this, connection K reads
`<base>/cK/v1`, whose catalog is fixed, and carries no real key.

Runs inside the ai-ui image on the copy's volume, as inject-test-admin.py does.
Only ever point this at a copy.

Usage: point-providers-at-mock.py <webui.db> <base-url>
"""

import json
import sqlite3
import sys


def main(db_path: str, base: str) -> None:
    con = sqlite3.connect(db_path)
    row = con.execute("SELECT id, data FROM config ORDER BY id DESC LIMIT 1").fetchone()
    if row is None:
        sys.exit("no saved config in the copy")
    config_id, raw = row
    data = json.loads(raw)
    openai = data.setdefault("openai", {})
    count = len(openai.get("api_base_urls") or [])
    openai["api_base_urls"] = [f"{base}/c{i}/v1" for i in range(count)]
    openai["api_keys"] = ["mock-key"] * count
    con.execute("UPDATE config SET data = ? WHERE id = ?", (json.dumps(data), config_id))
    con.commit()
    print(f"{count} connection(s) now read {base}/cK/v1")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2].rstrip("/"))
