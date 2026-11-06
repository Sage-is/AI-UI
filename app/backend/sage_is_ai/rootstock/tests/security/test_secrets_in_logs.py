"""No secret reaches a log (TODO.md, "Secrets in logs: an OAuth token response, and a dead API-key method").

Static: utils/oauth.py formats neither the token response nor the user info into a log line;
no module carries authenticate_user_by_api_key, which logged a whole key; restore_backup_start.sh,
run with a fake remote, reports the remote's name and never its key.
"""

from __future__ import annotations

import ast
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[4]
PKG = BACKEND / "sage_is_ai"
SENSITIVE = {"token", "user_data"}


def logged_values(tree: ast.AST, names: set[str]) -> list[int]:
    """Lines where a log.<level>(...) call puts one of `names` whole into its message."""
    lines = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "log"):
            continue
        for arg in node.args:
            if isinstance(arg, ast.Name) and arg.id in names:
                lines.append(node.lineno)
            for part in ast.walk(arg):
                if isinstance(part, ast.FormattedValue) and isinstance(part.value, ast.Name) and part.value.id in names:
                    lines.append(node.lineno)
    return sorted(set(lines))


class OAuthLogs(unittest.TestCase):
    def test_no_log_line_carries_the_token_response_or_the_user_info(self):
        tree = ast.parse((PKG / "utils" / "oauth.py").read_text())
        self.assertEqual(logged_values(tree, SENSITIVE), [], "utils/oauth.py logs a whole token or user info at these lines")

    def test_the_check_has_teeth(self):
        flagged = ast.parse('log.warning(f"user data is missing: {token}")\nlog.warning("sub is missing: %s", user_data)\n')
        self.assertEqual(logged_values(flagged, SENSITIVE), [1, 2])
        allowed = ast.parse('log.warning(f"user data is missing; token fields: {sorted(token)}")\n')
        self.assertEqual(logged_values(allowed, SENSITIVE), [])


class DeadApiKeyMethod(unittest.TestCase):
    def test_authenticate_user_by_api_key_is_gone(self):
        carriers = sorted(str(p.relative_to(PKG)) for p in PKG.rglob("*.py")
                          if "authenticate_user_by_api_key" in p.read_text(encoding="utf-8") and p.name != Path(__file__).name)
        self.assertEqual(carriers, [])


class RestoreScript(unittest.TestCase):
    MARKER = "rs-secret-marker-7f3a"

    def test_the_generated_rclone_config_is_not_printed(self):
        script = BACKEND / "restore_backup_start.sh"
        # Only the function under test: the script's tail starts the server.
        command = 'eval "$(sed -n "/^setup_rclone()/,/^}/p" "$1")"; setup_rclone'
        with tempfile.TemporaryDirectory() as home:
            env = {"HOME": home, "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                   "RCLONE_CONFIG_B2_TYPE": "b2", "RCLONE_CONFIG_B2_ACCOUNT": "acct", "RCLONE_CONFIG_B2_KEY": self.MARKER}
            run = subprocess.run(["bash", "-c", command, "bash", str(script)], env=env, capture_output=True, text=True, timeout=30)
            written = (Path(home) / ".config" / "rclone" / "rclone.conf").read_text()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn(f"key = {self.MARKER}", written, "the config file itself must still carry the key")
        self.assertNotIn(self.MARKER, run.stdout + run.stderr, "the key reached the log")
        self.assertIn("B2", run.stdout, "the remote's name is no longer reported")
