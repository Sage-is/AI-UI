# oras.sh — the one ORAS image every host-side Sprig script runs.
#
# Build, sign, repack and publish all push through it, and `sprig_publish`
# reaches GHCR with it, so it is pinned by index digest: a moved tag cannot
# change what signs or ships a Sprig. Bump it here and nowhere else (it was
# copied into eight scripts at v1.2.0 until 2026-11-03). A caller's own
# ORAS_IMG still wins, for trying a newer release.
#
#   . "$(dirname "${BASH_SOURCE[0]}")/lib/oras.sh"

: "${ORAS_IMG:=ghcr.io/oras-project/oras:v1.3.4@sha256:f7bc056d54d97baa399414ed5048ecc67c3371b750d4bbce1d871827a5758179}"
