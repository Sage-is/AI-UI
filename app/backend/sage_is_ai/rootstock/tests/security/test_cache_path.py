"""/cache/{path}: the served file must sit under the cache root, siblings included.

A unit test lifts `cache_path_for` out of main.py (importing main.py boots the whole
app) and tries a sibling directory whose name starts with the root's name, which a
string-prefix check lets through. An HTTP test asks the box for `../webui.db` and for
`../cache-evil/secret.txt`; both must be 404 whether or not the files exist.

    cd app/backend && RS_BASE_URL=http://localhost:8184 \\
        python3 -m unittest -v sage_is_ai.rootstock.tests.security.test_cache_path
"""

from __future__ import annotations

import ast
import os
import tempfile
import unittest
from pathlib import Path

from ._http import admin

MAIN = Path(__file__).resolve().parents[3] / "main.py"


def lift_cache_path_for():
    """The `cache_path_for` function from main.py, compiled on its own: main.py's imports start the app."""
    tree = ast.parse(MAIN.read_text(), filename=str(MAIN))
    node = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "cache_path_for"), None)
    if node is None:
        raise AssertionError(f"{MAIN} defines no cache_path_for")
    namespace = {"Path": Path, "CACHE_DIR": Path("/nonexistent-cache-root")}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(MAIN), "exec"), namespace)  # nosec B102 — one pure function lifted from our own source, no app import
    return namespace["cache_path_for"]


class CachePathForTest(unittest.TestCase):
    def setUp(self):
        self.cache_path_for = lift_cache_path_for()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.root = base / "cache"
        self.root.mkdir()
        (self.root / "ok.txt").write_text("fine")
        (base / "cache-evil").mkdir()
        (base / "cache-evil" / "secret.txt").write_text("secret")
        (base / "outside.txt").write_text("outside")

    def test_a_file_under_the_root_is_served(self):
        self.assertEqual(self.cache_path_for("ok.txt", self.root), (self.root / "ok.txt").resolve())

    def test_a_sibling_sharing_the_prefix_is_refused(self):
        self.assertIsNone(self.cache_path_for("../cache-evil/secret.txt", self.root))

    def test_a_parent_path_is_refused(self):
        self.assertIsNone(self.cache_path_for("../outside.txt", self.root))
        self.assertIsNone(self.cache_path_for("/etc/hostname", self.root))

    def test_a_symlink_out_of_the_root_is_refused(self):
        os.symlink(Path(self.tmp.name) / "cache-evil", self.root / "link")
        self.assertIsNone(self.cache_path_for("link/secret.txt", self.root))


class CacheRouteTest(unittest.TestCase):
    """Against the box: the route never answers 200 for a path outside the cache root."""

    @classmethod
    def setUpClass(cls):
        cls.user = admin()

    def test_traversal_paths_answer_404(self):
        for path in ("/cache/../webui.db", "/cache/%2e%2e/webui.db", "/cache/../cache-evil/secret.txt",
                     "/cache/..%2fcache-evil%2fsecret.txt"):
            with self.subTest(path=path):
                r = self.user.get(path)
                self.assertEqual(r.status, 404, f"{path}: HTTP {r.status} {r.text[:80]!r}")


if __name__ == "__main__":
    unittest.main()
