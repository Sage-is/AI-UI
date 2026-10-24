#!/usr/bin/env python3
"""Insert (or reset) a throwaway admin account in a webui.db COPY.

Runs INSIDE the ai-ui image, and hashes with the app's own utils/passwords.py
(bcrypt only), so the injected admin can never drift from how the app hashes:

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

# The image's backend, for the one module this needs. utils/passwords.py
# imports bcrypt and nothing else from the app. (passlib left in 3.2.1.)
# Images from before 3.2.1 lack that module but ship bcrypt, so the gate can
# still run against them: the fallback applies the same three rules.
sys.path.insert(0, "/app/backend")
try:
    from sage_is_ai.utils.passwords import get_password_hash  # noqa: E402
except ImportError:
    import bcrypt

    def get_password_hash(password: str) -> str:
        cut = password.encode("utf-8")[:72]  # bcrypt reads 72 bytes; passlib cut
        return bcrypt.hashpw(cut, bcrypt.gensalt(rounds=12)).decode("ascii")


def main() -> None:
    db_path, email, password = sys.argv[1], sys.argv[2].lower(), sys.argv[3]
    pw_hash = get_password_hash(password)
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
