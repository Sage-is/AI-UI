#!/usr/bin/env python3
"""The Sprig™ capability reference: emitted from the code, gated against it.

WHY THIS EXISTS
---------------
`BONSAI/sprig-spec/IMPLEMENTATION.md` records eleven places where the drafted
spec and the shipped subsystem disagree. Divergence #6 is this one: the draft
reserves `whisper-` for speech-to-text, the code ships `stt`, and six live
capabilities appear nowhere in the draft. The document was written before most
of the code.

One section of that spec matches the implementation exactly — Theme Sprigs™ —
and the note in IMPLEMENTATION.md says why: it "was written FROM the
implementation." That is the whole idea here, mechanised. `CATALOG` already IS
the authority on what a capability is; this reads it and writes the prose, so
the reference cannot drift without a build going red.

WHAT IS DERIVED

  entries          Every CATALOG entry, grouped by capability: server kind,
                   delivery, arch, model, health path.
  on graft         Which config fields each capability's dispatch mutates,
                   read out of the `point_*_at` functions themselves.
  on restart       Whether the capability re-dispatches in `_reconcile`. A
                   capability missing here silently loses its config on every
                   restart, because the respawned child gets a fresh port.
  on prune         Whether the capability reverses its dispatch in
                   `prune_sprig`. A capability missing here leaves config
                   pointing at a released port forever.
  gaps             The capabilities where those three disagree. This is the
                   section that would have caught the tika/docling prune bug
                   on the day it was written.

WHY IT PARSES INSTEAD OF IMPORTS
--------------------------------
Importing `supervisor.py` pulls `sage_is_ai.config`, and `config.py:73` runs
database migrations at import. A gate that needs a database is a gate that
needs the image, and a gate that needs the image is a gate nobody runs locally.
So this reads source with `ast` and imports nothing from the application —
the same discipline as the chat-path structure ratchet.

USAGE
    make sprig_capabilities          # rewrite the reference
    make sprig_capabilities_check    # fail if the reference is stale

Exit 0 when the committed document matches the code, 1 otherwise.
"""

from __future__ import annotations

import argparse
import ast
import difflib
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
BACKEND = ROOT / "app/backend/sage_is_ai"
SUPERVISOR = BACKEND / "sprigs/supervisor.py"
SPRIG_ROUTER = BACKEND / "routers/sprigs.py"
DISPATCH_DIR = BACKEND / "sprigs"
DOC = ROOT / "docs/sprigs/capabilities.md"

BEGIN = "<!-- BEGIN GENERATED — edits here are overwritten by `make sprig_capabilities` -->"
END = "<!-- END GENERATED -->"

# The three fan-outs. Each is a hand-maintained copy of the same table, which
# is precisely why they are worth reading mechanically.
#
# `restart` narrows to the `if handle.process is not None:` block. `_reconcile`
# also compares the capability at its dev-mode skip, and counting that would
# report `dev` as re-dispatching when it does the opposite — it is the branch
# that declines to restore.
REGIONS = {
    "graft": (SPRIG_ROUTER, "graft_sprig", None),
    "restart": (SUPERVISOR, "_reconcile", "handle.process is not None"),
    "prune": (SPRIG_ROUTER, "prune_sprig", None),
}


def parse(path: pathlib.Path) -> ast.Module:
    return ast.parse(path.read_text(), filename=str(path))


def literal(node: ast.AST):
    """Best-effort value. Falls back to source text for non-literals."""
    try:
        return ast.literal_eval(node)
    except (ValueError, SyntaxError):
        return ast.unparse(node)


# --------------------------------------------------------------------------
# The catalog
# --------------------------------------------------------------------------


def find_catalog(tree: ast.Module) -> ast.Dict:
    for node in ast.walk(tree):
        targets = []
        if isinstance(node, ast.AnnAssign) and node.target is not None:
            targets = [node.target]
        elif isinstance(node, ast.Assign):
            targets = node.targets
        for t in targets:
            if isinstance(t, ast.Name) and t.id == "CATALOG":
                if isinstance(node.value, ast.Dict):
                    return node.value
    sys.exit("sprig-capabilities: no CATALOG dict literal found — the parser is stale")


def render_arch(node: ast.AST) -> str:
    """`NEUTRAL` reads as neutral; an arch dict reads as its keys.

    The per-arch values are tag and digest overrides. They belong in the
    catalog, not in a document a human is trying to skim.
    """
    if ast.unparse(node) == "NEUTRAL":
        return "neutral"
    if isinstance(node, ast.Dict):
        keys = [k.value for k in node.keys if isinstance(k, ast.Constant)]
        if keys:
            return ", ".join(sorted(keys))
    return ast.unparse(node)


def read_entries() -> list[dict]:
    """Every catalog entry as a plain dict, plus its arch stamp and line."""
    catalog = find_catalog(parse(SUPERVISOR))
    entries: list[dict] = []

    for key, value in zip(catalog.keys, catalog.values):
        if not isinstance(key, ast.Constant):
            continue
        spec_node, arch_node = value, None

        # The catalog spells entries `_sprig({...}, arch=...)`. Tolerate a bare
        # dict too, so a future entry that skips the helper still documents.
        if isinstance(value, ast.Call) and value.args:
            spec_node = value.args[0]
            for kw in value.keywords:
                if kw.arg == "arch":
                    arch_node = kw.value
        if not isinstance(spec_node, ast.Dict):
            continue

        spec = {}
        for k, v in zip(spec_node.keys, spec_node.values):
            if isinstance(k, ast.Constant):
                spec[k.value] = literal(v)

        if arch_node is not None:
            spec["_arch"] = render_arch(arch_node)
        entries.append({"name": key.value, "line": key.lineno, "spec": spec})

    if not entries:
        sys.exit("sprig-capabilities: catalog parsed to zero entries — the parser is stale")
    return entries


# --------------------------------------------------------------------------
# The fan-outs
# --------------------------------------------------------------------------


def is_capability_expr(node: ast.AST) -> bool:
    """Does this expression name a capability?

    Covers all three shapes in the tree: the bare `cap` in `_reconcile`, the
    `handle.capability` attribute in graft_sprig, and the
    `h.get("capability")` lookup in prune_sprig.
    """
    if isinstance(node, ast.Name) and node.id in {"cap", "capability"}:
        return True
    if isinstance(node, ast.Attribute) and node.attr == "capability":
        return True
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr == "get" and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and first.value == "capability":
                return True
    return False


def find_function(tree: ast.Module, name: str) -> ast.AST:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    sys.exit(f"sprig-capabilities: function {name!r} not found — it was renamed or moved")


def narrow(func: ast.AST, test_src: str) -> ast.AST:
    """The nested `if` whose test reads exactly `test_src`."""
    for node in ast.walk(func):
        if isinstance(node, ast.If) and ast.unparse(node.test) == test_src:
            return node
    sys.exit(f"sprig-capabilities: no `if {test_src}:` inside the target function "
             f"— the guard moved and the reader is stale")


def capabilities_in(path: pathlib.Path, func_name: str, within: str | None = None) -> set[str]:
    """Capability strings compared against inside one function.

    Only `==` counts. `!=` is deliberately ignored: `routers/sprigs.py`'s
    `capability != "embedding"` is the catch-all fallthrough, not a branch that
    handles embedding.
    """
    scope = find_function(parse(path), func_name)
    if within is not None:
        scope = narrow(scope, within)
    found: set[str] = set()
    for node in ast.walk(scope):
        if not isinstance(node, ast.Compare) or len(node.ops) != 1:
            continue
        if not isinstance(node.ops[0], ast.Eq):
            continue
        left, right = node.left, node.comparators[0]
        for a, b in ((left, right), (right, left)):
            if is_capability_expr(a) and isinstance(b, ast.Constant):
                if isinstance(b.value, str):
                    found.add(b.value)
    return found


def read_regions() -> dict[str, set[str]]:
    return {
        label: capabilities_in(path, fn, within)
        for label, (path, fn, within) in REGIONS.items()
    }


# --------------------------------------------------------------------------
# What a graft actually changes
# --------------------------------------------------------------------------


def read_dispatch() -> dict[str, dict]:
    """Config fields each `point_*_at` writes, read from the function body."""
    out: dict[str, dict] = {}
    for path in sorted(DISPATCH_DIR.glob("*_dispatch.py")):
        capability = path.stem[: -len("_dispatch")]
        tree = parse(path)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not (node.name.startswith("point_") and node.name.endswith("_at")):
                continue
            fields: list[str] = []
            for sub in ast.walk(node):
                if not isinstance(sub, ast.Assign):
                    continue
                for target in sub.targets:
                    if not isinstance(target, ast.Attribute):
                        continue
                    base = ast.unparse(target.value)
                    # cfg.X / config.X / app.state.config.X are the config
                    # writes. app.state.X is runtime state, reported apart.
                    if base.endswith("config") or base in {"cfg", "config"}:
                        fields.append(target.attr)
            out[capability] = {
                "module": path.name,
                "function": node.name,
                "line": node.lineno,
                "fields": sorted(set(fields)),
            }
            break
    return out


# --------------------------------------------------------------------------
# The document
# --------------------------------------------------------------------------


def mark(present: bool) -> str:
    return "yes" if present else "**no**"


def runs_no_process(entries: list[dict]) -> bool:
    """Every entry runs no child process.

    Two shapes qualify: `deliver` (pull + extract an artifact, then nothing) and
    `none` (nothing is pulled either — the code already ships in the image, and
    grafting only makes the capability available so it can be wired).
    """
    return all(e["spec"].get("server") in ("deliver", "none") for e in entries)


def render(entries: list[dict], regions: dict[str, set[str]], dispatch: dict[str, dict]) -> str:
    by_cap: dict[str, list[dict]] = {}
    for entry in entries:
        by_cap.setdefault(entry["spec"].get("capability", "?"), []).append(entry)

    caps = sorted(by_cap)
    out: list[str] = []
    w = out.append

    w(BEGIN)
    w("")
    w(f"Derived from `{SUPERVISOR.relative_to(ROOT)}`, "
      f"`{SPRIG_ROUTER.relative_to(ROOT)}`, and `sprigs/*_dispatch.py`.")
    w("")
    w(f"**{len(caps)} capabilities, {len(entries)} catalog entries.**")
    w("")

    # --- the summary table ---
    w("## What each capability does")
    w("")
    w("| Capability | Entries | Changes on graft | Survives restart | Reverses on prune |")
    w("|---|---|---|---|---|")
    for cap in caps:
        d = dispatch.get(cap)
        if d and d["fields"]:
            changed = ", ".join(f"`{f}`" for f in d["fields"])
        elif cap in regions["graft"]:
            changed = "dispatches, no config write found"
        else:
            changed = (
                "nothing — the capability is enabled, then wired"
                if all(e["spec"].get("server") == "none" for e in by_cap[cap])
                else "nothing — delivery only"
            )
        writes_config = bool(d and d["fields"])
        restart = "n/a — no process" if runs_no_process(by_cap[cap]) \
            else mark(cap in regions["restart"])
        prune = mark(cap in regions["prune"]) if writes_config \
            else "n/a — nothing to reverse"
        w(f"| `{cap}` | {len(by_cap[cap])} | {changed} | {restart} | {prune} |")
    w("")
    w("*Survives restart* means the capability re-dispatches in "
      "`SprigSupervisor._reconcile`. Without it a respawned child gets a fresh "
      "loopback port and the config still names the old one. Capabilities that "
      "run no process are marked n/a: `_reconcile` gates its dispatch on "
      "`handle.process is not None`, and they rely on the persisted config "
      "pointer instead, which does not move.")
    w("")
    w("*Reverses on prune* means `prune_sprig` resets what the graft changed. "
      "Without it the config keeps pointing at a released port.")
    w("")

    # --- the gaps ---
    w("## Gaps")
    w("")
    gaps = []
    for cap in caps:
        writes_config = bool(dispatch.get(cap, {}).get("fields"))
        if not writes_config:
            continue
        if cap not in regions["restart"] and not runs_no_process(by_cap[cap]):
            gaps.append(f"- `{cap}` writes config on graft but is absent from `_reconcile`. "
                        f"Its config does not survive a restart.")
        if cap not in regions["prune"]:
            fields = ", ".join(f"`{f}`" for f in dispatch[cap]["fields"])
            gaps.append(f"- `{cap}` writes {fields} on graft and reverses nothing on prune. "
                        f"After pruning, those values point at a released port.")
    if gaps:
        for line in gaps:
            w(line)
    else:
        w("None. Every capability that writes config re-dispatches on restart and "
          "reverses on prune.")
    w("")

    # --- per capability ---
    w("## Capabilities in detail")
    w("")
    for cap in caps:
        w(f"### `{cap}`")
        w("")
        d = dispatch.get(cap)
        if d:
            w(f"Dispatch: `sprigs/{d['module']}` → `{d['function']}()` "
              f"(line {d['line']}).")
            if d["fields"]:
                w("")
                w("Writes on graft:")
                w("")
                for f in d["fields"]:
                    w(f"- `{f}`")
        else:
            # by_cap[cap], NOT `entries` — the latter is every Sprig in the
            # catalog, so this branch could never fire.
            if all(e["spec"].get("server") == "none" for e in by_cap[cap]):
                w("No dispatch module and nothing to deliver. The code ships in "
                  "the image; grafting makes the capability available so it can "
                  "be wired.")
            else:
                w("No dispatch module. Grafting delivers bytes and changes no configuration.")
        w("")
        w("| Entry | Server | Delivery | Arch | Model | Health |")
        w("|---|---|---|---|---|---|")
        for e in sorted(by_cap[cap], key=lambda x: x["name"]):
            s = e["spec"]
            w(f"| `{e['name']}` "
              f"| `{s.get('server', 'mock')}` "
              f"| {s.get('delivery', 'built in')} "
              f"| {s.get('_arch', '?')} "
              f"| `{s.get('model', '—')}` "
              f"| {'n/a — nothing runs' if s.get('server') == 'none' else chr(96) + s.get('health_path', '/health') + chr(96)} |")
        w("")

    w(END)
    return "\n".join(out) + "\n"


def splice(existing: str, block: str) -> str:
    if BEGIN in existing and END in existing:
        head = existing.split(BEGIN)[0]
        tail = existing.split(END, 1)[1]
        return head + block.rstrip("\n") + tail
    return existing.rstrip("\n") + "\n\n" + block


# --------------------------------------------------------------------------
# The spec view
# --------------------------------------------------------------------------

SPEC_BEGIN = "<!-- BEGIN GENERATED — from the reference implementation's catalog. Do not edit by hand. -->"
SPEC_END = "<!-- END GENERATED -->"

RESERVED_HEADING = "Reserved capability prefixes, grouped by family:"
RESERVED_UNTIL = "## Artifact format"
PREFIX_TOKEN = __import__("re").compile(r"`([a-z0-9-]+-)`")


def read_reserved(spec_path: pathlib.Path) -> list[str]:
    """The prefixes the spec reserves, read out of the spec's own prose.

    Both sides of the comparison are derived: add a reservation to v1.md and
    the delta below corrects itself on the next publish.
    """
    text = spec_path.read_text()
    if RESERVED_HEADING not in text:
        sys.exit(f"sprig-capabilities: {spec_path.name} has no "
                 f"{RESERVED_HEADING!r} — the spec was restructured")
    section = text.split(RESERVED_HEADING, 1)[1].split(RESERVED_UNTIL, 1)[0]
    seen: list[str] = []
    for line in section.splitlines():
        if not line.lstrip().startswith("-"):
            continue
        for token in PREFIX_TOKEN.findall(line):
            if token not in seen:
                seen.append(token)
    if not seen:
        sys.exit("sprig-capabilities: parsed zero reserved prefixes — the reader is stale")
    return seen


def matches(capability: str, prefix: str) -> bool:
    return capability == prefix.rstrip("-") or capability.startswith(prefix)


def render_spec(entries: list[dict], reserved: list[str]) -> str:
    shipped = sorted({e["spec"].get("capability", "?") for e in entries})
    counts: dict[str, int] = {}
    for e in entries:
        counts[e["spec"].get("capability", "?")] = \
            counts.get(e["spec"].get("capability", "?"), 0) + 1

    honoured = {c: p for c in shipped for p in reserved if matches(c, p)}
    unreserved = [c for c in shipped if c not in honoured]
    unshipped = [p for p in reserved if not any(matches(c, p) for c in shipped)]

    out: list[str] = []
    w = out.append
    w(SPEC_BEGIN)
    w("")
    w("### What the reference implementation ships")
    w("")
    w(f"`sage-is/AI-UI` carries **{len(shipped)} capabilities across "
      f"{len(entries)} catalog entries**. The three lists below are computed by "
      f"comparing that catalog against the reserved prefixes above, so they "
      f"cannot drift from either side. This is the standing answer to "
      f"divergence #6 in `IMPLEMENTATION.md`.")
    w("")
    w("**Reserved and shipped.**")
    w("")
    w("| Capability | Entries | Honours |")
    w("|---|---|---|")
    for c in sorted(honoured):
        w(f"| `{c}` | {counts[c]} | `{honoured[c]}` |")
    w("")
    w("**Shipped without a reserved prefix.** Each is live vocabulary this "
      "document does not yet reserve.")
    w("")
    if unreserved:
        for c in unreserved:
            w(f"- `{c}` — {counts[c]} "
              f"{'entry' if counts[c] == 1 else 'entries'}")
    else:
        w("- None.")
    w("")
    w("**Reserved and not yet shipped.** Vocabulary held for a later spec "
      "version or a later implementation.")
    w("")
    if unshipped:
        w("- " + ", ".join(f"`{p}`" for p in unshipped))
    else:
        w("- None.")
    w("")
    w("The full implementation reference — what each capability changes on "
      "graft, whether it survives a restart, whether it reverses on prune — "
      "lives in the reference implementation at `docs/sprigs/capabilities.md`, "
      "generated from the same source and gated there.")
    w("")
    w(SPEC_END)
    return "\n".join(out) + "\n"


def splice_spec(existing: str, block: str) -> str:
    if SPEC_BEGIN in existing and SPEC_END in existing:
        head = existing.split(SPEC_BEGIN)[0]
        tail = existing.split(SPEC_END, 1)[1]
        return head + block.rstrip("\n") + tail
    sys.exit("sprig-capabilities: the spec has no generated block. Add the "
             "marker pair to v1.md where the inventory should land:\n"
             f"  {SPEC_BEGIN}\n  {SPEC_END}")


def self_test(block: str) -> int:
    """A gate nobody has watched fail is a gate nobody should trust.

    Perturbs the committed document three ways and asserts the comparison
    notices each one. Touches no file: everything happens on strings.
    """
    if not DOC.exists():
        print("self-test: no document to perturb — run the generator first.")
        return 1

    current = DOC.read_text()
    if splice(current, block) != current:
        print("self-test: the document is already stale, so a failing check "
              "proves nothing. Run `make sprig_capabilities` first.")
        return 1

    cases = {
        "a hand-edit inside the generated block":
            current.replace("| `tika` |", "| `tikka` |", 1),
        "a dropped line":
            "\n".join(l for l in current.splitlines()
                      if not l.startswith("| `stt` |")) + "\n",
        "a silently changed count":
            current.replace("catalog entries.**", "catalog entries (ish).**", 1),
    }

    failures = []
    for label, mutated in cases.items():
        if mutated == current:
            failures.append(f"{label}: the perturbation changed nothing — "
                            f"the self-test is stale, not the gate")
        elif splice(mutated, block) == mutated:
            failures.append(f"{label}: NOT DETECTED")

    if failures:
        for line in failures:
            print(f"self-test FAILED — {line}")
        return 1

    print(f"PASS — the check detected all {len(cases)} perturbations. "
          f"The gate has teeth.")
    return 0


def publish_spec(v1: pathlib.Path) -> int:
    """Fold the vocabulary view into the spec, in place.

    Deliberately NOT the whole reference. The spec states a contract; the prune
    gaps and config field names are implementation status and belong in the
    implementation's own document. What folds here is vocabulary: which
    reserved prefixes ship, which shipped names are unreserved, which
    reservations are still empty.
    """
    if not v1.exists():
        print(f"sprig-capabilities: {v1} not found.")
        return 1
    reserved = read_reserved(v1)
    block = render_spec(read_entries(), reserved)
    current = v1.read_text()
    updated = splice_spec(current, block)
    if updated == current:
        print(f"sprig-capabilities: {v1.name} already current "
              f"({len(reserved)} reserved prefixes).")
        return 0
    v1.write_text(updated)
    print(f"sprig-capabilities: folded the vocabulary view into {v1} "
          f"({len(reserved)} reserved prefixes read from the spec itself).")
    print("Commit it there separately — this repo does not own that tree.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="fail if the committed reference is stale")
    ap.add_argument("--self-test", action="store_true",
                    help="prove the check can fail")
    ap.add_argument("--publish-spec", metavar="V1_MD",
                    help="fold the vocabulary view into the Sprig spec's v1.md")
    args = ap.parse_args()

    if args.publish_spec:
        return publish_spec(pathlib.Path(args.publish_spec))

    block = render(read_entries(), read_regions(), read_dispatch())

    if args.self_test:
        return self_test(block)

    if not DOC.exists():
        if args.check:
            print(f"sprig-capabilities: {DOC.relative_to(ROOT)} does not exist. "
                  f"Run `make sprig_capabilities`.")
            return 1
        DOC.parent.mkdir(parents=True, exist_ok=True)
        DOC.write_text(block)
        print(f"sprig-capabilities: wrote {DOC.relative_to(ROOT)}")
        return 0

    current = DOC.read_text()
    updated = splice(current, block)

    if args.check:
        if current == updated:
            entries = read_entries()
            print(f"PASS — capability reference matches the code "
                  f"({len(entries)} entries).")
            return 0
        diff = difflib.unified_diff(
            current.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"{DOC.relative_to(ROOT)} (committed)",
            tofile=f"{DOC.relative_to(ROOT)} (from the code)",
        )
        sys.stdout.writelines(diff)
        print(f"\nFAIL — the capability reference is stale. "
              f"Run `make sprig_capabilities` and commit the result.")
        return 1

    DOC.write_text(updated)
    print(f"sprig-capabilities: rewrote {DOC.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
