"""Every community share and install path goes through app/src/lib/utils/community.ts
(TODO.md, "Community-share leak + dead wiring", 2026-11-03).

Static. No source names the public request bin a model share used to reach. No window
or tab posts to '*'. No handler or install allowlist hardcodes a hub address: the one
address is COMMUNITY_HUB_URL. Every component that shares imports the helper. And no
function crosses in either direction, since a function is code the server runs
unsandboxed. ROOTSTOCK_REPO points the checks at another tree, for a teeth run.
"""

from __future__ import annotations

import os
import re
import unittest
from pathlib import Path

REPO = Path(os.environ.get("ROOTSTOCK_REPO") or Path(__file__).resolve().parents[6])
APP = REPO / "app"
HELPER = APP / "src" / "lib" / "utils" / "community.ts"
FUNCTION_CREATE = (
    APP / "src" / "routes" / "(app)" / "admin" / "functions" / "create" / "+page.svelte"
)
ROOTS = (APP / "src", APP / "backend" / "sage_is_ai" / "pages")
SUFFIXES = {".svelte", ".ts", ".js", ".py", ".html"}
# A window or tab takes a target origin; workers and message ports do not.
POST_TO_ANY = re.compile(
    r"\b(?:tab|opener|window|parent)\.postMessage\([^;]*?,\s*['\"]\*['\"]\s*\)", re.S
)
# The old literals: a share or browse path on sage.is, or a bare quoted sage.is in code.
HUB_LITERAL = re.compile(
    r"https://(?:www\.)?sage\.is/(?:community|prompts/create|models/create|functions/create|chats/upload|leaderboard)"
    r"|'https://(?:www\.)?sage\.is'"
)


def sources() -> dict[Path, str]:
    return {
        path: path.read_text(encoding="utf-8", errors="replace")
        for root in ROOTS
        for path in root.rglob("*")
        if path.suffix in SUFFIXES and "vendor" not in path.parts and path.is_file()
    }


class CommunitySharePaths(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = sources()

    def offenders(self, test) -> list[str]:
        return sorted(
            str(p.relative_to(REPO)) for p, text in self.files.items() if test(text)
        )

    def test_no_source_names_the_request_bin(self):
        self.assertEqual(self.offenders(lambda t: "webhook.site" in t), [])

    def test_no_window_posts_to_any_origin(self):
        self.assertEqual(self.offenders(POST_TO_ANY.search), [])

    def test_no_handler_hardcodes_a_hub_address(self):
        self.assertEqual(self.offenders(HUB_LITERAL.search), [])

    def test_every_share_goes_through_the_helper(self):
        # The toast every share shows marks a sharing component.
        sharers = self.offenders(lambda t: "Redirecting you to" in t)
        self.assertTrue(
            sharers, "no sharing component found; did the toast text change?"
        )
        self.assertEqual(
            [p for p in sharers if "$lib/utils/community" not in self.files[REPO / p]],
            [],
        )

    def test_no_function_crosses_to_or_from_the_hub(self):
        self.assertEqual(self.offenders(lambda t: "shareToHub('/functions" in t), [])
        page = self.files[FUNCTION_CREATE]
        self.assertNotIn("receiveFromHub", page)
        self.assertNotIn("addEventListener('message'", page)

    def test_the_helper_holds_one_handshake_word(self):
        self.assertIn("HUB_HANDSHAKE = 'loaded'", self.files.get(HELPER, ""))


if __name__ == "__main__":
    unittest.main()
