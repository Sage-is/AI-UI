#!/usr/bin/env bash
# The structure ratchet for the chat path.
#
# Asserts that middleware.py — and the package the restructure will split it
# into — is at or under every ceiling in baseline.json, and that no line link in
# the charts or the bug ledger has rotted.
#
# Runs on the host. It reads source and markdown and imports nothing from the
# application, so it needs no image and no container. That matters: a gate that
# requires a 20-minute build is a gate that gets skipped locally and only ever
# fails in CI, long after the commit that broke it.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../../.."

exec python3 scripts/gates/chat-path-structure/measure.py "$@"
