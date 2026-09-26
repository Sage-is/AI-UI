#!/usr/bin/env python3
"""Standalone Sprig™ graft — ``python3 -m sage_is_ai.sprigs.graft_cli <name>``.

A thin CLI over ``SprigSupervisor.graft`` for launch scripts that need a
capability delivered BEFORE the app's own reconcile runs. Today that is dev.sh:
Vite's dev server needs the ``dev-svelte`` toolchain (node_modules) that ships
OUTSIDE the slim rootstock, and it must be on disk before ``bun run vite dev``.

It reuses the supervisor's graft path deliberately — one implementation carries
the architecture guard, the sha256 pin, the signature policy, and the volume
tar cache. Re-implementing "pull + extract" here would let those drift.

The graft is idempotent: ``artifact.ensure`` short-circuits when the delivery
target sentinel is already present at the catalog tag, so this is cheap on a
warm container and only pulls/extracts on first run or a catalog tag bump.

Not for the production boot path — the supervisor reconciles grafted state
there. This is for launch scripts that must guarantee a delivery synchronously.

Exit status: 0 on success or already-on-hand, 1 on failure — so a boot script
can warn and carry on rather than abort.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from types import SimpleNamespace


async def _graft(name: str, capability: str | None) -> int:
    # A "deliver" sprig (e.g. dev-svelte) needs a supervisor instance but not a
    # live FastAPI app: graft()/_deliver() never touch self.app, and
    # _persist_state writes to the data volume and degrades gracefully. A stub
    # satisfies the constructor.
    from sage_is_ai.sprigs.supervisor import SprigSupervisor

    supervisor = SprigSupervisor(SimpleNamespace(state=SimpleNamespace()))

    spec = supervisor.CATALOG.get(name)
    if spec is None:
        print(f"[graft] unknown sprig '{name}'", file=sys.stderr)
        return 1
    capability = capability or spec["capability"]

    try:
        handle = await supervisor.graft(name, capability)
    except Exception as exc:  # noqa: BLE001 — any failure is the caller's to handle
        print(f"[graft] '{name}' failed: {exc}", file=sys.stderr)
        return 1
    print(f"[graft] '{name}' {handle.state} ({handle.model or capability})")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Graft a Sprig™ by catalog name (standalone; reuses SprigSupervisor.graft).",
    )
    parser.add_argument("name", help="catalog name, e.g. dev-svelte")
    parser.add_argument(
        "capability",
        nargs="?",
        default=None,
        help="declared capability (default: looked up from the catalog)",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_graft(args.name, args.capability)))


if __name__ == "__main__":
    main()
