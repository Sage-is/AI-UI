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
# Requirements: docker, gh (authed, write:packages), jq, the local registry on
# sage-network. oras runs DOCKERIZED (no host install) — the same shape as the
# future in-cluster publisher: an oras container with creds mounted read-only.
# Idempotent; safe to re-run.
# FORCE=1 re-pushes tags that already exist remotely — required after
# scripts/sign-sprigs.sh, because signing changes each manifest digest.
set -uo pipefail

SRC="${SRC:-localhost:5000}"                 # host-published local registry
SRC_INTERNAL="${SRC_INTERNAL:-local-registry:5000}"  # name inside sage-network (dockerized oras)
DEST="${DEST:-ghcr.io/sage-is}"
ORG="${ORG:-sage-is}"

command -v docker >/dev/null || { echo "ERROR: docker not on PATH"; exit 1; }
command -v gh     >/dev/null || { echo "ERROR: gh not on PATH"; exit 1; }
command -v jq     >/dev/null || { echo "ERROR: jq not on PATH"; exit 1; }

# Dockerized oras: no host oras, no login state. A throwaway docker-config is
# minted from gh's token and mounted read-only (oras honors DOCKER_CONFIG).
ORAS_IMG="${ORAS_IMG:-ghcr.io/oras-project/oras:v1.2.0}"
NETWORK="${NETWORK:-sage-network}"
AUTH_DIR="$(mktemp -d)"
trap 'rm -rf "$AUTH_DIR"' EXIT
printf '{"auths":{"%s":{"auth":"%s"}}}' "${DEST%%/*}" \
  "$(printf '%s:%s' "$(gh api user -q .login)" "$(gh auth token)" | base64 | tr -d '\n')" \
  > "$AUTH_DIR/config.json"
oras() {
  docker run --rm --network "$NETWORK" -v "$AUTH_DIR:/auth:ro" \
    -e DOCKER_CONFIG=/auth "$ORAS_IMG" "$@"
}

FAIL=0
NON_PUBLIC=()
NOT_PULLABLE=()

# The pull CONTRACT is the supervisor CATALOG, not whatever happens to be in the
# local registry (a fresh named volume can be missing a just-built artifact and
# skip it silently). Derive the required repo list from the catalog's repo pins
# and fail loudly if any is absent locally — this is exactly the gap that let
# the theme sprigs ship unpublished.
SUP="$(cd "$(dirname "$0")/.." && pwd)/app/backend/sage_is_ai/sprigs/supervisor.py"
REQUIRED=$(grep -oE 'sprig-[a-z0-9-]+"' "$SUP" | tr -d '"' | sort -u)
LOCAL=$(curl -fsS "http://$SRC/v2/_catalog" | jq -r '.repositories[]' | sort -u)
MISSING=$(comm -23 <(echo "$REQUIRED") <(echo "$LOCAL"))
if [ -n "$MISSING" ]; then
  echo "ERROR: catalog pins these repos but they are ABSENT from $SRC:"
  echo "$MISSING" | sed 's/^/  - /'
  echo "Build them (scripts/build-sprig-*.sh) before publishing, or the live"
  echo "server will 503 on graft. Refusing to publish a partial catalog."
  exit 1
fi

echo "== pushing every local tag to $DEST =="
for r in $LOCAL; do
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

# The real contract is ANONYMOUS pullability, which is what a fresh live server
# (no oras login) actually needs. Verify it directly via the ghcr token
# endpoint instead of trusting gh-api visibility alone — a package can read
# 'public' in one view and still deny anonymous pulls.
echo "== pullability gate: every package must be ANONYMOUSLY pullable =="
for r in $LOCAL; do
  vis=$(gh api "/orgs/$ORG/packages/container/$r" -q .visibility 2>/dev/null || echo "unknown")
  code=$(curl -s -o /dev/null -w '%{http_code}' \
    "https://ghcr.io/token?service=ghcr.io&scope=repository:$ORG/$r:pull")
  if [ "$code" = "200" ]; then
    echo "  ✅ $r anonymously pullable (visibility: $vis)"
  else
    echo "  ❌ $r NOT anonymously pullable (token endpoint $code, visibility: $vis)"
    NON_PUBLIC+=("$r")
    NOT_PULLABLE+=("$r")
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
