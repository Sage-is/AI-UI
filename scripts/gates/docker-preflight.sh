#!/usr/bin/env bash
# The Makefile's docker preflights. Each reads only docker's context, docker's
# config and the PATH, and stops a target before it starts work it cannot finish.
#
#   docker-preflight.sh amd64 "make TARGET"   linux/amd64 work refuses a krunkit VM
#   docker-preflight.sh buildx [RUNTIME]      BuildKit builds need docker's buildx plugin
#   docker-preflight.sh creds                 docker login needs the helper credsStore names
#   docker-preflight.sh registry [RUNTIME]    one local-registry per folder, across VMs
#
# scripts/gates/test_runtime.py runs each one against stand-ins.
set -euo pipefail

# The socket of docker's context, its links followed; nothing without a context.
socket() {
  local sock link
  sock="$(docker context inspect -f '{{.Endpoints.docker.Host}}' 2>/dev/null)" || return 0
  sock="${sock#unix://}"
  # /var/run/docker.sock often links to a runtime's own socket. A bounded loop:
  # older macOS has neither realpath nor readlink -f, and a cycle must not hang.
  for _ in 1 2 3 4 5 6 7 8; do
    [ -L "$sock" ] || break
    link="$(readlink "$sock")"
    case "$link" in /*) sock="$link" ;; *) sock="$(dirname "$sock")/$link" ;; esac
  done
  echo "$sock"
}

# A Colima context's socket sits in its profile's folder, beside colima.yaml;
# the legacy ~/.colima/docker.sock serves the default profile. Prints that
# colima.yaml, or nothing for another runtime's socket.
colima_yaml() {
  local dir
  [ -n "$1" ] || return 0
  dir="$(dirname "$1")"
  [ -f "$dir/colima.yaml" ] || dir="$dir/default"
  [ ! -f "$dir/colima.yaml" ] || echo "$dir/colima.yaml"
}

# The runtime docker's context uses, as sage-runtime names it; nothing for
# another. `sage-runtime use` mends docker's config but also stops every
# other runtime, so a fix names the one in use, never colima by default.
runtime() {
  local sock
  sock="$(socket)"
  if [ -n "$(colima_yaml "$sock")" ]; then echo colima; return 0; fi
  case "$sock" in
    */.orbstack/*) echo orbstack ;;
    */.docker/run/docker.sock | */com.docker.docker/*) echo docker-desktop ;;
  esac
}

# krunkit has no Rosetta, so linux/amd64 runs there only under QEMU: slowly, and
# AI-UI's Vite stage can run out of memory. The build VM is vz with Rosetta.
amd64() {
  grep -qs '^vmType: krunkit' "$(colima_yaml "$(socket)")" || return 0
  echo "$1 needs linux/amd64, which a krunkit VM runs only under QEMU. Use the build VM: sage-runtime build-vm, then DOCKER_CONTEXT=colima-build $1" >&2
  exit 1
}

# Homebrew's docker comes without buildx, and `build --load` needs it. Podman builds on its own.
buildx() {
  local rt
  [ "$(basename "$1")" = docker ] || return 0
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "$1 not found. Install it with Colima: brew install colima docker docker-buildx docker-credential-helper. Or set CONTAINER_RUNTIME=podman to build with Podman." >&2
    exit 1
  fi
  "$1" buildx version >/dev/null 2>&1 && return 0
  rt="$(runtime)"
  echo "docker buildx not found. Install it: brew install docker-buildx${rt:+ (then: sage-runtime use $rt)}" >&2
  exit 1
}

# Docker Desktop writes "credsStore": "desktop", and its helper leaves with the
# app; every login then fails with "error getting credentials".
creds() {
  local config="${DOCKER_CONFIG:-$HOME/.docker}/config.json" store rt fix
  store="$(sed -n 's/.*"credsStore" *: *"\([^"]*\)".*/\1/p' "$config" 2>/dev/null)" || store=""
  if [ -z "$store" ] || command -v "docker-credential-$store" >/dev/null 2>&1; then return 0; fi
  rt="$(runtime)"
  if [ -n "$rt" ]; then fix="Run: sage-runtime use $rt"; else fix="Name a helper this machine has there, or remove the setting."; fi
  echo "credsStore \"$store\" in $config has no helper on this machine, so docker login would fail. $fix" >&2
  exit 1
}

# One local-registry serves $SPRIG_REGISTRY_DATA. Each Colima VM runs its own
# containers, so the build VM's docker does not see the default VM's registry,
# which holds the Mac's port 5000; a second registry would write the same folder.
# The fix names the context that runs the holder: a stopped VM has no context.
registry() {
  local ctx
  "$1" ps --format '{{.Names}}' 2>/dev/null | grep -qx local-registry && return 0
  curl -fsS -o /dev/null -m 5 http://localhost:5000/v2/ 2>/dev/null || return 0
  echo "localhost:5000 already answers, but no local-registry runs in this docker context: another VM or runtime holds the port. A second one would write ${SPRIG_REGISTRY_DATA:-$HOME/SageData/sprig-registry} too." >&2
  for ctx in colima colima-build desktop-linux orbstack; do
    if docker --context "$ctx" ps --format '{{.Names}}' 2>/dev/null | grep -qx local-registry; then
      echo "Stop that one first: docker --context $ctx stop local-registry" >&2
      exit 1
    fi
  done
  echo "Stop the local-registry that holds the port first, in whichever context runs it (docker context ls lists them)." >&2
  exit 1
}

case "${1:-}" in
  amd64)    amd64 "${2:?usage: $0 amd64 \"make TARGET\"}" ;;
  buildx)   buildx "${2:-docker}" ;;
  creds)    creds ;;
  registry) registry "${2:-docker}" ;;
  *)        echo "usage: $0 amd64 \"make TARGET\" | buildx [RUNTIME] | creds | registry [RUNTIME]" >&2; exit 2 ;;
esac
