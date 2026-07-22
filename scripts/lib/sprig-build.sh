#!/usr/bin/env bash
# sprig-build.sh — shared boilerplate for the build-sprig-*.sh recipes.
#
# Every recipe repeated the same OCI-artifact constants, host-arch normalization,
# sha256 helper, optional local-registry bring-up, dockerized-oras push, and build
# timing. This is the one copy. A recipe sources it, sets its own NAME (+ any
# recipe-specific vars), then calls the helpers:
#
#   . "$(dirname "${BASH_SOURCE[0]}")/lib/sprig-build.sh"   # from scripts/*
#   NAME="${NAME:-sprig-foo}"
#   sprig_build_defaults          # REGISTRY/TAG/INSECURE/NETWORK/…/ORAS_IMG
#   sprig_timing_start
#   sprig_arch_normalize          # -> ARCH, PLATFORM, ARCHTAG
#   ...build + pack into $OUT (a .tar.zst under $OUT_DIR)...
#   sprig_ensure_registry         # no-op unless MANAGE_REGISTRY=1
#   sprig_push                    # $REGISTRY/$NAME:$ARCHTAG via dockerized oras
#   sprig_timing_end
#
# IMPORTANT: recipes run under `set -e`. Helpers whose natural last command can
# return non-zero (an arch that is not amd64, a registry poll that times out)
# end with an explicit `return 0` so a benign false does NOT abort the caller —
# matching the inline code these replace. sprig_push is the exception: a failed
# push SHOULD abort, so it returns the docker/oras status.

[ -n "${_SPRIG_BUILD_LIB_LOADED:-}" ] && return 0
_SPRIG_BUILD_LIB_LOADED=1

# Common OCI-artifact constants + local-dev registry defaults. Assign-if-unset,
# so an env override (REGISTRY=ghcr.io/sage-is, INSECURE=0, …) always wins. The
# recipe sets its own NAME before calling this.
sprig_build_defaults(){
  : "${REGISTRY:=localhost:5000}"
  : "${TAG:=v1}"
  : "${INSECURE:=1}"
  : "${MANAGE_REGISTRY:=0}"
  : "${NETWORK:=sage-network}"
  : "${ARTIFACT_TYPE:=application/vnd.sage-is.sprig.v1}"
  : "${LAYER_TYPE:=application/vnd.sage-is.sprig.tar+zstd}"
  : "${ORAS_IMG:=ghcr.io/oras-project/oras:v1.2.0}"
  return 0
}

# Portable sha256 of a file (sha256sum on Linux, shasum on macOS — same digest).
sha256(){
  if command -v sha256sum >/dev/null; then sha256sum "$1" | cut -d' ' -f1
  else shasum -a 256 "$1" | cut -d' ' -f1; fi
}

# Normalize ARCH (arm64|amd64) from ${ARCH:-uname -m}; set PLATFORM and ARCHTAG
# (amd64 carries the -amd64 tag suffix; arm64 keeps the bare $TAG). Exits 1 on an
# unsupported arch. The if/else on ARCHTAG (vs `&& …`) keeps the return status 0
# under `set -e` even on the arm64 branch.
sprig_arch_normalize(){
  local raw; raw="$(uname -m)"
  case "${ARCH:-$raw}" in
    arm64|aarch64) ARCH=arm64 ;;
    amd64|x86_64)  ARCH=amd64 ;;
    *) echo "ERROR: unsupported ARCH='${ARCH:-$raw}' (want arm64|amd64)" >&2; exit 1 ;;
  esac
  PLATFORM="${PLATFORM:-linux/$ARCH}"
  if [ "$ARCH" = "amd64" ]; then ARCHTAG="$TAG-amd64"; else ARCHTAG="$TAG"; fi
  return 0
}

# Bring up the throwaway local registry on $NETWORK — only when MANAGE_REGISTRY=1
# (default 0 = the caller/Makefile already runs it). Idempotent; safe to re-run.
sprig_ensure_registry(){
  [ "${MANAGE_REGISTRY:-0}" = "1" ] || return 0
  docker network inspect "$NETWORK" >/dev/null 2>&1 || docker network create "$NETWORK"
  if ! docker ps --format '{{.Names}}' | grep -qx local-registry; then
    docker rm -f local-registry >/dev/null 2>&1 || true
    docker run -d --name local-registry --network "$NETWORK" -p 5000:5000 -v sprig-registry-data:/var/lib/registry registry:2 >/dev/null
  fi
  for _ in $(seq 1 30); do curl -fsS "http://localhost:5000/v2/" >/dev/null 2>&1 && break; sleep 0.5; done
  return 0
}

# Push $OUT (a .tar.zst under $OUT_DIR) to $REGISTRY/$NAME:$ARCHTAG via a
# dockerized oras (no host install). A localhost registry is rewritten to the
# on-network `local-registry` name. An optional pre-set SIG_LAYER array (signing
# sidecar layer) rides along; unset is fine. Returns the push status so a failed
# push aborts the recipe under `set -e`.
sprig_push(){
  local push_reg="$REGISTRY" oras_net=()
  case "$REGISTRY" in localhost:*|127.0.0.1:*)
    push_reg="local-registry:${REGISTRY##*:}"; oras_net=(--network "$NETWORK");;
  esac
  local push=(push "$push_reg/$NAME:$ARCHTAG" --artifact-type "$ARTIFACT_TYPE")
  [ "${INSECURE:-1}" = "1" ] && push+=(--plain-http)
  docker run --rm ${oras_net[@]+"${oras_net[@]}"} -v "$OUT_DIR:/w" -w /w "$ORAS_IMG" \
    "${push[@]}" "$(basename "$OUT"):$LAYER_TYPE" ${SIG_LAYER[@]+"${SIG_LAYER[@]}"}
}

# Build-timer: sprig_timing_start stamps t0; sprig_timing_end prints the ⏱ line
# (reads NAME, ARCHTAG, OUT). No-ops cleanly if start was never called.
sprig_timing_start(){ SPRIG_BUILD_T0="$(date +%s)"; return 0; }
sprig_timing_end(){
  local el=$(( $(date +%s) - ${SPRIG_BUILD_T0:-$(date +%s)} ))
  printf "⏱  %s %s built in %dm%02ds (artifact %s)\n" \
    "$NAME" "$ARCHTAG" $(( el/60 )) $(( el%60 )) "$(du -h "$OUT" | awk '{print $1}')"
  return 0
}
