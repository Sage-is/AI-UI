#!/usr/bin/env python3
"""Insert (or reset) a throwaway admin account in a webui.db COPY.

Runs INSIDE the ai-ui image (passlib/bcrypt ship there):

  docker run --rm -v /path/to/COPY-of-data:/data \
    --entrypoint python3 sage-is/ai-ui:develop \
    /app/backend/sage_is_ai/../../../scripts/... (or mount this file)

Only ever point this at a copy. The upgrade gate does; nothing here should
touch a production database or the pristine snapshot.

Usage: inject-test-admin.py <webui.db> <email> <password>
"""

import sqlite3
import sys
import time
import uuid

# passlib 1.7.4 (final, unmaintained) reads bcrypt.__about__.__version__, which
# bcrypt removed in 4.1+. On its own that logs a noisy "(trapped) error reading
# bcrypt version" traceback (harmless — hashing still works). Restore the
# attribute so passlib reads the real version and stays quiet. The app does the
# equivalent in utils/auth.py; this standalone helper needs its own.
import bcrypt as _bcrypt_mod

if not hasattr(_bcrypt_mod, "__about__"):
    _bcrypt_mod.__about__ = type("about", (), {"__version__": _bcrypt_mod.__version__})

from passlib.hash import bcrypt


def main() -> None:
    db_path, email, password = sys.argv[1], sys.argv[2].lower(), sys.argv[3]
    pw_hash = bcrypt.using(rounds=12).hash(password)
    now = int(time.time())
    uid = f"upgrade-gate-{uuid.uuid4()}"

    con = sqlite3.connect(db_path)
    cur = con.cursor()
    row = cur.execute("SELECT id FROM auth WHERE email = ?", (email,)).fetchone()
    if row:
        uid = row[0]
        cur.execute(
            "UPDATE auth SET password = ?, active = 1 WHERE id = ?", (pw_hash, uid)
        )
        cur.execute("UPDATE user SET role = 'admin' WHERE id = ?", (uid,))
        print(f"reset existing account {email} ({uid}) to admin")
    else:
        cur.execute(
            "INSERT INTO auth (id, email, password, active) VALUES (?, ?, ?, 1)",
            (uid, email, pw_hash),
        )
        cur.execute(
            "INSERT INTO user (id, name, email, role, profile_image_url, api_key, "
            "created_at, updated_at, last_active_at, settings, info, oauth_sub) "
            "VALUES (?, 'Upgrade Gate', ?, 'admin', '/user.png', NULL, ?, ?, ?, "
            "NULL, NULL, NULL)",
            (uid, email, now, now, now),
        )
        print(f"injected admin {email} ({uid})")
    con.commit()
    con.close()


if __name__ == "__main__":
    main()
