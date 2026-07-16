#!/usr/bin/env bash
# build-sprig-tika.sh — package the tika Sprig™: Apache Tika Server (fat jar)
# + a jlink'd minimal JRE, per host arch.
#
# The tar carries {jre/, tika-server-standard.jar} at its root. The supervisor
# runs `{artifact_dir}/jre/bin/java -jar {artifact_dir}/tika-server-standard.jar`
# on a loopback port (server: tika-jar); tika_dispatch points TIKA_SERVER_URL at
# it and selects CONTENT_EXTRACTION_ENGINE=tika. Replaces the http://tika:9998
# sidecar. Health = GET /tika (Tika has no /health).
#
# The jar is arch-neutral Java bytecode; the JRE is per-arch, so the artifact is
# per-arch (arm64 = $TAG, amd64 = $TAG-amd64). jlink runs INSIDE the target-arch
# JDK container (amd64 under QEMU on Apple Silicon), so the JRE matches $ARCH.
#
# Local dev (default): pushes to localhost:5000 via a DOCKERIZED oras (no host
# install). Production publishing goes through publish-sprigs.sh (local -> ghcr).
set -euo pipefail

REGISTRY="${REGISTRY:-localhost:5000}"
NAME="${NAME:-sprig-tika}"
TAG="${TAG:-v1}"
INSECURE="${INSECURE:-1}"
MANAGE_REGISTRY="${MANAGE_REGISTRY:-0}"
NETWORK="${NETWORK:-sage-network}"
ARTIFACT_TYPE="application/vnd.sage-is.sprig.v1"
LAYER_TYPE="application/vnd.sage-is.sprig.tar+zstd"
ORAS_IMG="${ORAS_IMG:-ghcr.io/oras-project/oras:v1.2.0}"

# Tika 2.9.x is the last Java-11 line; 3.x needs Java 17+. JDK 21 LTS covers
# either — bump TIKA_VERSION as needed. Source: Maven Central.
TIKA_VERSION="${TIKA_VERSION:-2.9.2}"
JDK_IMAGE="${JDK_IMAGE:-eclipse-temurin:21-jdk}"
TIKA_JAR="tika-server-standard-${TIKA_VERSION}.jar"
TIKA_URL="https://repo1.maven.org/maven2/org/apache/tika/tika-server-standard/${TIKA_VERSION}/${TIKA_JAR}"

_RAW_ARCH="$(uname -m)"
case "${ARCH:-$_RAW_ARCH}" in
  arm64|aarch64) ARCH=arm64 ;;
  amd64|x86_64)  ARCH=amd64 ;;
  *) echo "ERROR: unsupported ARCH='${ARCH:-$_RAW_ARCH}' (want arm64|amd64)" >&2; exit 1 ;;
esac
PLATFORM="${PLATFORM:-linux/$ARCH}"
ARCHTAG="$TAG"; [ "$ARCH" = "amd64" ] && ARCHTAG="$TAG-amd64"

WORK="${WORK:-/tmp/sprig-build/tika-$ARCH}"
OUT_DIR="$WORK/out"
OUT="$OUT_DIR/${NAME}-${ARCHTAG}.tar.zst"
rm -rf "$WORK"; mkdir -p "$WORK/stage" "$OUT_DIR"

sha256() { shasum -a 256 "$1" | awk '{print $1}'; }

# --- 1. jlink a minimal JRE + fetch the Tika jar, on the TARGET arch -----------
# jdeps computes the modules the jar references; we add the ones loaded
# reflectively (crypto, charsets, localedata, naming, sql, management) that
# jdeps can't see. jlink then builds just those into a compact JRE.
echo "== jlink JRE + fetch Tika $TIKA_VERSION on $PLATFORM =="
docker run --rm --platform "$PLATFORM" -v "$WORK/stage:/w" "$JDK_IMAGE" bash -ec '
  cd /w
  curl -fsSL -o "'"$TIKA_JAR"'" "'"$TIKA_URL"'"
  MODS="$(jdeps --print-module-deps --ignore-missing-deps --multi-release 21 "'"$TIKA_JAR"'" 2>/dev/null || echo java.base)"
  MODS="$MODS,java.desktop,java.naming,java.management,java.sql,java.security.jgss,jdk.crypto.ec,jdk.crypto.cryptoki,jdk.localedata,jdk.charsets,jdk.unsupported,java.logging,java.xml,java.scripting"
  jlink --no-header-files --no-man-pages --strip-debug --compress=2 \
        --include-locales=en --add-modules "$MODS" --output jre
  mv "'"$TIKA_JAR"'" tika-server-standard.jar
  ./jre/bin/java -version
  du -sh jre tika-server-standard.jar
'

# --- 2. SANITY GATE: start Tika on the TARGET arch, extract a doc ---------------
echo "== sanity gate: Tika server responds + extracts on $PLATFORM =="
docker run --rm --platform "$PLATFORM" -v "$WORK/stage:/s:ro" "$JDK_IMAGE" bash -ec '
  cp -r /s/jre /tmp/jre && cp /s/tika-server-standard.jar /tmp/
  /tmp/jre/bin/java -jar /tmp/tika-server-standard.jar --host 127.0.0.1 --port 9998 >/tmp/tika.log 2>&1 &
  PID=$!
  for i in $(seq 1 60); do curl -fsS http://127.0.0.1:9998/tika >/dev/null 2>&1 && break; sleep 1; done
  curl -fsS http://127.0.0.1:9998/tika | grep -qi "Tika" && echo "  GET /tika OK"
  printf "hello sprig extraction" > /tmp/t.txt
  curl -fsS -T /tmp/t.txt http://127.0.0.1:9998/tika | grep -qi "hello sprig extraction" && echo "  text extraction OK"
  kill "$PID" 2>/dev/null || true
' || { echo "SANITY GATE FAILED — Tika broken on $ARCH (see log)" >&2; exit 1; }

# --- 3. reproducible pack {jre/, tika-server-standard.jar} ----------------------
docker run --rm -v "$WORK/stage:/stage:ro" -v "$OUT_DIR:/out" alpine sh -c \
  "apk add --no-cache tar zstd >/dev/null && \
   tar --sort=name --owner=0 --group=0 --numeric-owner --mtime='UTC 2020-01-01' \
       --use-compress-program='zstd -19 -T0' \
       -cf /out/$(basename "$OUT") -C /stage jre tika-server-standard.jar"
TAR_SHA="$(sha256 "$OUT")"

echo
echo "=================================================================="
echo "  artifact : $OUT   (arch: $ARCH, Tika $TIKA_VERSION)"
echo "  tar.zst sha256 (PIN in CATALOG 'tika'):"
echo "    $TAR_SHA"
if [ "$ARCH" = "amd64" ]; then
  echo "  -> arches[\"amd64\"] = {\"tag\": \"$ARCHTAG\", \"binary_sha256\": \"$TAR_SHA\"}"
else
  echo "  -> arm64 pin (TAG=$TAG): \"$TAR_SHA\""
fi
echo "=================================================================="

# --- 4. optional local registry ------------------------------------------------
if [ "$MANAGE_REGISTRY" = "1" ]; then
  docker network inspect "$NETWORK" >/dev/null 2>&1 || docker network create "$NETWORK"
  if ! docker ps --format '{{.Names}}' | grep -qx local-registry; then
    docker rm -f local-registry >/dev/null 2>&1 || true
    docker run -d --name local-registry --network "$NETWORK" -p 5000:5000 -v sprig-registry-data:/var/lib/registry registry:2 >/dev/null
  fi
  for _ in $(seq 1 30); do curl -fsS "http://localhost:5000/v2/" >/dev/null 2>&1 && break; sleep 0.5; done
fi

# --- 5. push (dockerized oras; no host install) --------------------------------
PUSH_REG="$REGISTRY"; ORAS_NET=()
case "$REGISTRY" in localhost:*|127.0.0.1:*)
  PUSH_REG="local-registry:${REGISTRY##*:}"; ORAS_NET=(--network "$NETWORK");;
esac
PUSH=(push "$PUSH_REG/$NAME:$ARCHTAG" --artifact-type "$ARTIFACT_TYPE")
[ "$INSECURE" = "1" ] && PUSH+=(--plain-http)
docker run --rm ${ORAS_NET[@]+"${ORAS_NET[@]}"} -v "$OUT_DIR:/w" -w /w "$ORAS_IMG" \
  "${PUSH[@]}" "$(basename "$OUT"):$LAYER_TYPE"

echo
echo "pushed: $REGISTRY/$NAME:$ARCHTAG"
