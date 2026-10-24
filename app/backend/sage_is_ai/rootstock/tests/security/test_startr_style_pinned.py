"""Every page loads the vendored startr.style 1.5.0 with an integrity hash, never the rolling URL
(TODO.md, "Pages load startr.style from a rolling URL").

Static: the vendored sheet is byte-for-byte the Startr/Style v1.5.0 release; none of the three
pages names https://startr.style/style.css; each links the vendored path once, with a sha384
integrity value that matches the file.
"""

from __future__ import annotations

import base64
import hashlib
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[6]
VENDORED = REPO / "app" / "static" / "vendor" / "startr.style" / "1.5.0" / "style.css"
HREF = "/static/vendor/startr.style/1.5.0/style.css"
ROLLING = "https://startr.style/style.css"
# Startr/Style tag v1.5.0 (2026-10-18), src/static/v1.5.0/style.css.
RELEASE_SHA256 = "0d8693035254943b0f2d4517e6cbfb5bc104c5cb7712d191bdacecf787b8efe4"
PAGES = (
    REPO / "app" / "src" / "app.html",
    REPO / "app" / "backend" / "sage_is_ai" / "pages" / "templates" / "try-sage.html",
    REPO / "app" / "backend" / "sage_is_ai" / "pages" / "shell.py",
)
LINK = re.compile(r"<link\b[^>]*>", re.S)
ATTR = re.compile(r'([a-z-]+)="([^"]*)"')


def links(text: str) -> list[dict]:
    return [dict(ATTR.findall(tag)) for tag in LINK.findall(text)]


def integrity(path: Path) -> str:
    return "sha384-" + base64.b64encode(hashlib.sha384(path.read_bytes()).digest()).decode()


class StartrStyleIsPinned(unittest.TestCase):
    def test_the_vendored_sheet_is_the_1_5_0_release(self):
        self.assertEqual(hashlib.sha256(VENDORED.read_bytes()).hexdigest(), RELEASE_SHA256)

    def test_no_page_names_the_rolling_url(self):
        for page in PAGES:
            with self.subTest(page=page.name):
                self.assertFalse(ROLLING in page.read_text(), f"{page.name} still names {ROLLING}")

    def test_each_page_loads_the_vendored_sheet_with_its_hash(self):
        expected = integrity(VENDORED)
        for page in PAGES:
            with self.subTest(page=page.name):
                tags = [t for t in links(page.read_text()) if t.get("href") == HREF]
                self.assertEqual(len(tags), 1, f"{page.name} links {HREF} {len(tags)} times")
                self.assertEqual(tags[0].get("rel"), "stylesheet")
                self.assertEqual(tags[0].get("integrity"), expected)
