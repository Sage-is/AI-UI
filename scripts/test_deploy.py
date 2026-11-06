"""The deploy backup lands encrypted and verified, never as plaintext (scripts/deploy.py).

Host-only, seconds: a stand-in `sage-secret` on PATH resolves the vault reference to a
test passphrase, so the real openssl and gzip run and nothing reaches the vault.
    cd scripts && python3 -B -m unittest -q test_deploy
"""

import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import deploy

FAKE_SAGE_SECRET = """#!/bin/sh
# sage-secret run -- CMD...: swap the one reference the deploy uses for a test passphrase.
[ "$1" = run ] && [ "$2" = -- ] || exit 2
shift 2
[ "$BACKUP_PASS" = "bw:ai-ui-deploy-db-backup" ] || exit 3
BACKUP_PASS=test-only-passphrase exec "$@"
"""
DB = b"SQLite format 3\x00" + os.urandom(4096)


class DeployBackup(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "bin").mkdir()
        fake = self.tmp / "bin" / "sage-secret"
        fake.write_text(FAKE_SAGE_SECRET)
        fake.chmod(0o755)
        self.path = mock.patch.dict(os.environ, {"PATH": f"{self.tmp / 'bin'}:{os.environ['PATH']}"})
        self.path.start()
        self.addCleanup(self.path.stop)

    def test_the_backup_is_encrypted_verified_and_never_plaintext(self):
        target = self.tmp / "app" / "2026-11-03-0000-3.2.2.db.gz.enc"
        target.parent.mkdir()
        deploy.store_encrypted(DB, target)
        self.assertEqual(sorted(p.name for p in target.parent.iterdir()), [target.name, "2026-11-03-0000-3.2.2.db.sha256"])
        self.assertNotIn(DB[:16], target.read_bytes())
        plain = subprocess.run(
            ["sh", "-c", f'{deploy.ENC} -d -pass pass:test-only-passphrase -in "$1" | gunzip -c', "sh", str(target)],
            check=True, capture_output=True,
        ).stdout
        self.assertEqual(plain, DB)
        self.assertEqual((target.parent / "2026-11-03-0000-3.2.2.db.sha256").read_text().split()[0],
                         hashlib.sha256(DB).hexdigest())

    def test_no_mounted_drive_means_no_download_and_no_deploy(self):
        instance = {"app": "sage-startr-cloud", "url": "https://example.invalid", "admin_key_env": "KEY"}
        with (
            mock.patch.object(deploy, "BACKUPS", self.tmp / "not-mounted" / "ai-ui"),
            mock.patch.dict(os.environ, {"KEY": "k"}),
            mock.patch.object(deploy.urllib.request, "urlopen") as urlopen,
        ):
            with self.assertRaises(SystemExit) as stop:
                deploy.back_up(instance)
        self.assertIn("is not mounted", str(stop.exception))
        urlopen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
