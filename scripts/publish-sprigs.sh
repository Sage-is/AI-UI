#!/usr/bin/env bash
# publish-sprigs.sh — publish the local sprig catalog to the public registry.
#
# Copies EVERY tag of EVERY repo in the local registry to $DEST (default
# ghcr.io/sage-is) registry-to-registry via oras, then VERIFIES each package
# is public and fails loudly with the exact fix URL for any that isn't.
# GitHub has NO API for container-package visibility, so new packages are
# born private/internal and need one manual flip in the web UI — this gate
# makes it impossible to *silently* ship a package the world can't pull.
# (Once flipped, a package name stays public across future pushes.)
#
# One-time org check ([MANUALLY], reduces future flips):
#   https://github.com/organizations/sage-is/settings/packages
#   — ensure members may create PUBLIC packages so the flip is available.
#
# Requirements: oras (or the dockerized shim), gh (authed, write:packages),
# jq, the local registry on sage-network. Idempotent; safe to re-run.
# FORCE=1 re-pushes tags that already exist remotely — required after
# scripts/sign-sprigs.sh, because signing changes each manifest digest.
set -uo pipefail

SRC="${SRC:-localhost:5000}"                 # host-published local registry
SRC_INTERNAL="${SRC_INTERNAL:-local-registry:5000}"  # name inside sage-network (dockerized oras)
DEST="${DEST:-ghcr.io/sage-is}"
ORG="${ORG:-sage-is}"

command -v oras >/dev/null || { echo "ERROR: oras not on PATH (use the dockerized shim or ask to brew install)"; exit 1; }
command -v gh   >/dev/null || { echo "ERROR: gh not on PATH"; exit 1; }
command -v jq   >/dev/null || { echo "ERROR: jq not on PATH"; exit 1; }

# Login (idempotent) — same gh-token pattern as `make ghcr_login`.
gh auth token | oras login "${DEST%%/*}" -u "$(gh api user -q .login)" --password-stdin >/dev/null || {
  echo "ERROR: oras login to ${DEST%%/*} failed"; exit 1; }

FAIL=0
NON_PUBLIC=()

echo "== pushing every local tag to $DEST =="
for r in $(curl -fsS "http://$SRC/v2/_catalog" | jq -r '.repositories[]'); do
  for t in $(curl -fsS "http://$SRC/v2/$r/tags/list" | jq -r '.tags[]'); do
    if [ -z "${FORCE:-}" ] && oras manifest fetch "$DEST/$r:$t" >/dev/null 2>&1; then
      echo "  = $r:$t already published"
    else
      printf "  ↑ %s:%s ... " "$r" "$t"
      if oras cp --from-plain-http "$SRC_INTERNAL/$r:$t" "$DEST/$r:$t" >/dev/null 2>&1; then
        echo "pushed"
      else
        echo "PUSH FAILED"; FAIL=1
      fi
    fi
  done
done

echo "== visibility gate: every package must be PUBLIC =="
for r in $(curl -fsS "http://$SRC/v2/_catalog" | jq -r '.repositories[]'); do
  vis=$(gh api "/orgs/$ORG/packages/container/$r" -q .visibility 2>/dev/null || echo "unknown")
  if [ "$vis" = "public" ]; then
    echo "  ✅ $r public"
  else
    echo "  ❌ $r is '$vis'"
    NON_PUBLIC+=("$r")
    FAIL=1
  fi
done

if [ "${#NON_PUBLIC[@]}" -gt 0 ]; then
  echo
  echo "MANUAL STEP REQUIRED — GitHub only allows visibility changes in the web UI."
  echo "Flip these to Public (Package settings → Danger Zone → Change visibility):"
  for r in "${NON_PUBLIC[@]}"; do
    echo "  https://github.com/orgs/$ORG/packages/container/$r/settings"
  done
  echo "Then re-run: make sprig_publish   (verifies + confirms)"
fi

[ "$FAIL" -eq 0 ] && echo "== PUBLISH COMPLETE: all packages pushed and public =="
exit "$FAIL"
