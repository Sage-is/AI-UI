#!/usr/bin/env bash
# The cognitive-complexity ratchet for the Python backend.
#
# Asserts that no function in app/backend/sage_is_ai got harder to read than the
# value recorded in baseline.json, and that no new function walks in over the
# watch floor unmeasured.
#
# Runs on the host. It reads source and imports nothing from the application, so
# it needs no image and no container.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/../../.."

exec python3 scripts/gates/cognitive-complexity/measure.py "$@"
