"""The sign-in page follows `?redirect=` only to a path on its own origin (2026-10-23).

This test is static. The redirect runs in the browser, which the standard library cannot
drive, so it reads `app/src/routes/auth/+page.svelte` and checks that every redirect read
passes through one guard, and what that guard does. When node is on the host it also runs
the guard's own source against the attack strings; without node that part skips.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

PAGE = Path(__file__).resolve().parents[5] / "src" / "routes" / "auth" / "+page.svelte"
GUARD = "safeRedirectPath"
GUARD_SOURCE = re.compile(r"\n\tconst safeRedirectPath = \(value\) => \{\n.*?\n\t\};\n", re.S)

# What the browser would do with each value, and where the guard must send it instead.
CASES = [
    ("javascript:alert(1)", "/"),  # runs script in the app's origin
    ("//evil.example/", "/"),  # protocol-relative: another host
    ("https://evil.example/x", "/"),  # another origin
    ("/\\evil.example", "/"),  # browsers fold the backslash into //evil.example
    ("/\t/evil.example", "/"),  # browsers drop the tab, leaving //evil.example
    (" //evil.example", "/"),  # browsers strip the leading space
    ("https://app.example/chat", "/"),  # absolute, even to this origin: a path is what a link may name
    ("/chat?x=1#y", "/chat?x=1#y"),
    ("", "/"),
    (None, "/"),
]


class LoginRedirectSameOrigin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.src = PAGE.read_text()

    def test_every_redirect_read_passes_through_the_guard(self):
        reads = re.findall(r"redirectPath = (.+);", self.src)
        self.assertGreaterEqual(len(reads), 2, "the page reads ?redirect= for its href and for goto")
        for read in reads:
            self.assertTrue(read.startswith(f"{GUARD}("), f"a redirect read skips the guard: {read}")
        self.assertNotRegex(self.src, r"location\.href = querystringValue", "a raw ?redirect= reaches location.href")

    def test_the_guard_keeps_to_this_origin(self):
        m = GUARD_SOURCE.search(self.src)
        self.assertIsNotNone(m, f"{GUARD} is not defined in {PAGE.name}")
        body = m.group(0)
        self.assertIn("new URL(value, window.location.origin)", body, "the guard must parse as the browser will")
        self.assertIn("url.origin === window.location.origin", body, "the guard must compare origins")
        self.assertIn("value.startsWith('/')", body, "the guard must take a path, never an absolute URL")

    @unittest.skipUnless(shutil.which("node"), "node is not on this host")
    def test_the_guard_itself_sends_every_attack_string_home(self):
        m = GUARD_SOURCE.search(self.src)
        self.assertIsNotNone(m, f"{GUARD} is not defined in {PAGE.name}")
        script = ("globalThis.window = { location: { origin: 'https://app.example' } };\n" + m.group(0)
                  + f"\nconsole.log(JSON.stringify(JSON.parse(process.argv[1]).map(([v]) => {GUARD}(v))));")
        run = subprocess.run(["node", "-e", script, json.dumps([[value] for value, _ in CASES])],
                             capture_output=True, text=True, check=True)
        got = json.loads(run.stdout)
        for (value, want), result in zip(CASES, got):
            self.assertEqual(result, want, f"{value!r} -> {result!r}, wanted {want!r}")


if __name__ == "__main__":
    unittest.main()
