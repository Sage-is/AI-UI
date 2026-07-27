#!/usr/bin/env bash
# ui-Sprig™ contract gate — proves what validate_ui_bundle REFUSES.
#
# The Cypress spec (cypress/e2e/ui-sprig-contract.cy.ts) walks the happy path
# against a real artifact: graft, serve, render, prune, revoke. This gate walks
# the other side, which is the side that matters for a marketplace — a
# fail-closed contract is worth exactly what it refuses.
#
# Refusals are proved here rather than through graft on purpose. Doing it that
# way would mean publishing deliberately malicious artifacts and listing them in
# the shipped catalog, where the catalog IS the allowlist. So the bundles are
# written straight onto the volume layout the validator reads, inside the real
# image, against the real function.
#
# Usage: scripts/smoke/ui-sprig-validator.sh [image]  (default sage-is/ai-ui:develop)
set -uo pipefail
IMG="${1:-sage-is/ai-ui:develop}"

# `-i` is load-bearing. Without it docker attaches no stdin, python3 reads an
# empty program, and the gate exits 0 having checked nothing — which is how this
# script passed the first time it was run. The tee + sentinel below is the
# belt-and-braces: a gate whose silence looks identical to success is worse than
# no gate, so this one has to SAY it ran.
# WEBUI_SECRET_KEY is required at import or env.py refuses to load. Any value
# does: nothing here signs or verifies a token, and a throwaway container is
# gone before the value could matter.
OUT="$(docker run --rm -i \
  -e WEBUI_SECRET_KEY=ui-sprig-gate-not-a-real-key \
  --entrypoint python3 "$IMG" - <<'PY'
import sys, tempfile, pathlib, os

# The validator reads from DATA_DIR, so point it at a scratch tree before the
# module is imported and its DATA_DIR constant is bound.
tmp = tempfile.mkdtemp()
os.environ["DATA_DIR"] = tmp
sys.path.insert(0, "/app/backend")

from sage_is_ai.sprigs.ui_dispatch import (  # noqa: E402
    UiValidationError,
    validate_ui_bundle,
    ui_bundle_dir,
)

FAILURES = []
COUNT = 0


def bundle(name, html, css=None):
    d = ui_bundle_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    (d / "fragment.html").write_text(html, encoding="utf-8")
    if css is not None:
        (d / "fragment.css").write_text(css, encoding="utf-8")
    return name


def check(label, name, *, granted=False, expect_refused=True, expect_in=""):
    """Assert on the OUTCOME and, when refused, on the reason.

    Matching the reason matters: a validator that refuses everything for the
    wrong cause passes a refusal test while telling operators nothing useful.
    """
    global COUNT
    COUNT += 1
    try:
        validate_ui_bundle(name, scripting_granted=granted)
    except UiValidationError as e:
        if not expect_refused:
            FAILURES.append(f"{label}: refused but should have passed — {e}")
            print(f"FAIL  {label}  — unexpectedly refused: {e}")
            return
        if expect_in and expect_in.lower() not in str(e).lower():
            FAILURES.append(f"{label}: refused for the wrong reason — {e}")
            print(f"FAIL  {label}  — wrong reason: {e}")
            return
        print(f"PASS  {label}  — refused: {str(e)[:78]}")
        return
    if expect_refused:
        FAILURES.append(f"{label}: ACCEPTED a bundle that must be refused")
        print(f"FAIL  {label}  — ACCEPTED")
    else:
        print(f"PASS  {label}  — accepted")


CLEAN = '<div class="ok"><h2>Welcome</h2><p>Plain markup.</p></div>'

# --- the contract's happy path, so the refusals below mean something ---------
check("a plain hypermedia fragment is accepted",
      bundle("ok-plain", CLEAN), expect_refused=False)
check("a fragment with a self-contained stylesheet is accepted",
      bundle("ok-css", CLEAN, ".ok { color: red; }"), expect_refused=False)

# --- missing / oversized ------------------------------------------------------
check("a bundle with no fragment.html is refused",
      "never-delivered", expect_in="missing")
check("an oversized fragment is refused",
      bundle("too-big", "<p>" + ("x" * 300_000) + "</p>"), expect_in="caps fragments")

# --- zero egress --------------------------------------------------------------
check("an external script source is refused",
      bundle("ext-script", '<script src="https://cdn.example.com/svelte.js"></script>'),
      granted=True, expect_in="off this origin")
check("an external stylesheet is refused",
      bundle("ext-css", '<link rel="stylesheet" href="https://cdn.example.com/a.css">'),
      expect_in="off this origin")
check("a protocol-relative reference is refused",
      bundle("proto-rel", '<img src="//tracker.example.com/pixel.gif">'),
      expect_in="off this origin")
check("an off-origin form action is refused",
      bundle("ext-form", '<form action="https://evil.example.com/collect"><input name="q"></form>'),
      expect_in="off this origin")

# --- framing and executable URLs ---------------------------------------------
check("an iframe is refused",
      bundle("framed", '<iframe src="/somewhere"></iframe>'), expect_in="frame")
check("a javascript: URL is refused",
      bundle("js-url", '<a href="javascript:alert(1)">x</a>'), expect_in="frame or execute")
check("an <object> is refused",
      bundle("obj", '<object data="/x.swf"></object>'), expect_in="frame or execute")

# --- interpreted attributes: invisible to a CSP, so never allowed ------------
check("a hyperscript _ attribute is refused even WITH a grant",
      bundle("hs-underscore", '<button _="on click toggle .x">go</button>'),
      granted=True, expect_in="interpreted script attribute")
check("a data-script attribute is refused even WITH a grant",
      bundle("hs-data", '<div data-script="on load fetch /x"></div>'),
      granted=True, expect_in="interpreted script attribute")

# --- scripting: off by default, widened only by the admin's grant ------------
check("script is refused without a grant",
      bundle("script-nogrant", '<div>hi</div><script>console.log(1)</script>'),
      expect_in="hypermedia by default")
check("an inline event handler is refused without a grant",
      bundle("onclick-nogrant", '<button onclick="go()">go</button>'),
      expect_in="inline event handler")
check("inline script IS accepted once the grant is on",
      bundle("script-granted", '<div id="x"></div><script>document.getElementById("x").textContent="hi"</script>'),
      granted=True, expect_refused=False)

# --- no framework sprigs ------------------------------------------------------
# The rule no regex can decide in general, carried by a size ceiling instead:
# an independently-built Svelte biome inlines ~18 kB of runtime at minimum
# (measured, tools/spikes/biomes), so a 16 kB cap makes bundling one
# structurally impossible while leaving an island room to work.
framework = "var Svelte=(function(){" + ("var pad='" + "z" * 20_000 + "';") + "})();"
check("a framework-sized script is refused even WITH a grant",
      bundle("framework", f"<div></div><script>{framework}</script>"),
      granted=True, expect_in="bring its own framework")
check("a script sourced from a FILE is refused even WITH a grant",
      bundle("script-file", '<div></div><script src="/pages/_assets/x.js"></script>'),
      granted=True, expect_in="sources script from a file")

# --- the stylesheet follows the theme rules, via the theme validator ---------
check("a fragment stylesheet that @imports is refused",
      bundle("css-import", CLEAN, '@import url("/other.css"); .ok{color:red}'),
      expect_in="fragment.css rejected")
check("a fragment stylesheet with an external url() is refused",
      bundle("css-ext", CLEAN, '.ok{background:url(https://cdn.example.com/b.png)}'),
      expect_in="fragment.css rejected")
# The escape-smuggling case the theme validator was hardened against. It is
# reachable from here too, and it is inherited rather than reimplemented —
# which is the reason ui_dispatch calls validate_theme_css instead of restating
# its rules.
check("a stylesheet hiding an external url() behind CSS escapes is refused",
      bundle("css-escape", CLEAN, r'.ok{background:url(\68ttps://cdn.example.com/b.png)}'),
      expect_in="fragment.css rejected")

# --- documentation must not trip its own rules -------------------------------
check("a fragment may DOCUMENT the forbidden syntax in a comment",
      bundle("commented", '<!-- never do <script> or href="https://cdn" -->' + CLEAN),
      expect_refused=False)

print()
if FAILURES:
    print(f"{len(FAILURES)} of {COUNT} checks FAILED")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print(f"{COUNT}/{COUNT} ui-Sprig contract checks passed")
PY
)"
RC=$?
echo "$OUT"

# The sentinel: a real run ends with a count. Anything else — an empty stdin, a
# crashed interpreter, an image without the module — is a failure that would
# otherwise read as a pass.
if [ "$RC" -ne 0 ]; then
  echo "ui-Sprig contract gate FAILED (exit $RC)"
  exit "$RC"
fi
if ! printf '%s' "$OUT" | grep -Eq '^[0-9]+/[0-9]+ ui-Sprig contract checks passed$'; then
  echo "ui-Sprig contract gate produced no verdict — it did not run. NOT a pass."
  exit 1
fi
