#!/usr/bin/env bash
# Upgrade gate — boot THIS image on a COPY of a production data snapshot and prove the upgrade path holds: migrations run, users/chats survive, the legacy RAG config degrades cleanly on the slim rootstock, the pinned chromadb opens the production vector store after a vector-chroma graft, and the new surfaces (themes, arch guard, registry resolution) behave.
#
# The snapshot is READ-ONLY here: every run copies it into a fresh docker volume and injects a throwaway admin into the COPY.
#
# Usage: scripts/smoke/upgrade-gate.sh [image] [snapshot-dir]
#   defaults: sage-is/ai-ui:develop  tools/db_snapshots/<newest>
# Reusable against ANY snapshot dir with the standard data layout
# (webui.db, vector_db/, cache/, uploads/). Safe to re-run.
set -uo pipefail
HERE="$(cd "$(dirname "$0")/../.." && pwd)"
IMG="${1:-sage-is/ai-ui:develop}"
SNAP="${2:-$(ls -d "$HERE"/tools/db_snapshots/*/ 2>/dev/null | sort | tail -1)}"
[ -d "$SNAP" ] || { echo "ERROR: no snapshot dir at '$SNAP'"; exit 1; }
NET="${SPRIG_SMOKE_NET:-sage-network}"; ROOT="sage-upgrade"; VOL="${ROOT}-data"
PORT="${UPGRADE_GATE_PORT:-8096}"; BASE="http://localhost:${PORT}"
ADMIN_EMAIL="upgrade-gate@sage.is"; ADMIN_PW="upgrade-gate-pw-1234"
. "$(dirname "${BASH_SOURCE[0]}")/../lib/gate.sh"   # PASS/FAIL + ok/no/require
X(){ docker exec "$ROOT" sh -lc "$1"; }

# KEEP=1 leaves the booted container + volume up after the gate (for the Cypress half, cypress/e2e/upgrade/, or manual inspection at $BASE).
cleanup(){
  [ -n "${KEEP:-}" ] && { echo "KEEP=1: leaving $ROOT up at $BASE (admin: $ADMIN_EMAIL)"; return; }
  docker rm -f "$ROOT" >/dev/null 2>&1 || true
  docker volume rm "$VOL" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo ""
echo "==============================================================="
echo "== 0. copy snapshot -> fresh volume (pristine source: $SNAP) =="
docker rm -f "$ROOT" >/dev/null 2>&1 || true
docker volume rm "$VOL" >/dev/null 2>&1 || true
docker volume create "$VOL" >/dev/null
# Skip the ~2.4GB cache/ dir (HF embedding-model download cache from the fat image). The gate grafts sprigs that carry their own models and asserts on the DB + vector store, never the old cache — copying it just doubles the disk
# footprint (this + the target-arch volume) and is what exhausted the VM.
docker run --rm -v "$SNAP:/src:ro" -v "$VOL:/dst" alpine:3.20 \
  sh -c "tar -C /src --exclude=./cache -cf - . | tar -C /dst -xf - && rm -f /dst/readme.txt && du -sm /dst | cut -f1" \
  | { read MB; echo "  copied ${MB}MB (cache/ excluded)"; }
docker run --rm -v "$VOL:/data" -v "$HERE/scripts/snapshots/inject-test-admin.py:/inject.py:ro" \
  -e WEBUI_SECRET_KEY=upgrade-gate --entrypoint python3 "$IMG" /inject.py /data/webui.db "$ADMIN_EMAIL" "$ADMIN_PW" \
  && ok "test admin injected into the COPY" || { no "admin injection failed"; exit 1; }

echo "== 1. boot the NEW image on the production data =="
docker run -d --name "$ROOT" --network "$NET" -p "${PORT}:8080" \
  -e SPRIG_REGISTRY=local-registry:5000 -e WEBUI_AUTH=True \
  -e WEBUI_SECRET_KEY=upgrade-gate-secret \
  -v "$VOL:/app/backend/data" "$IMG" >/dev/null
BOOTED=0
for i in $(seq 1 150); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health" 2>/dev/null)" = "200" ] && BOOTED=1 && break; sleep 2
done
[ "$BOOTED" = "1" ] && ok "boots + migrates a real 176MB production DB" \
  || { no "boot failed on production data"; docker logs --tail 40 "$ROOT"; exit 1; }
docker logs "$ROOT" 2>&1 | grep -qiE "traceback|migration.*(fail|error)" \
  && no "boot log shows tracebacks/migration errors" || ok "no tracebacks in boot log"

echo "== 2. auth + data survival =="
TOK=$(curl -s -X POST "$BASE/api/v1/auths/signin" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PW\"}" | jq -r '.token // empty')
AUTH="Authorization: Bearer $TOK"
[ -n "$TOK" ] && ok "injected admin signs in (bcrypt path intact)" || { no "signin failed"; exit 1; }
# jq path picks a NUMBER key explicitly, and we reject an error body (an object
# like {"detail":"..."} would make `length` return a key count and pass wrongly).
URESP=$(curl -s "$BASE/api/v1/users/?limit=50" -H "$AUTH")
NUSERS=$(echo "$URESP" | jq -r 'if type=="object" and has("total") then .total elif type=="object" and has("users") then (.users|length) elif type=="array" then length else -1 end' 2>/dev/null)
[ "${NUSERS:-0}" -ge 30 ] 2>/dev/null && ok "all production users survive ($NUSERS)" \
  || no "user count off: $NUSERS ($(echo "$URESP" | head -c 120))"
KRESP=$(curl -s "$BASE/api/v1/knowledge/list" -H "$AUTH")
# Must be a JSON ARRAY (the real shape); an error object must NOT satisfy this.
NKNOW=$(echo "$KRESP" | jq -r 'if type=="array" then length else -1 end' 2>/dev/null)
[ "${NKNOW:-0}" -ge 0 ] 2>/dev/null && [ "${NKNOW}" != "-1" ] \
  && ok "knowledge list returns an array ($NKNOW visible to gate admin)" \
  || no "knowledge list not an array: $(echo "$KRESP" | head -c 120)"

echo "== 3. legacy RAG config on the slim rootstock =="
# Engine lives on /embedding (not /config — that response has no embedding keys).
ECFG=$(curl -s "$BASE/api/v1/retrieval/embedding" -H "$AUTH")
ENGINE=$(echo "$ECFG" | jq -r '.embedding_engine // empty' 2>/dev/null)
[ "$ENGINE" = "openai" ] && ok "openai embedding engine survives untouched (external API, no reset)" \
  || no "embedding engine drifted: '$ENGINE' (expected openai from snapshot)"
echo "$ECFG" | jq -e '.openai_config.url | length > 0' >/dev/null 2>&1 \
  && ok "openai embedding base URL intact" || no "openai embedding URL emptied by boot guards"
# Assert the CODE, not just body shape: a clean degrade is a 4xx/503, NOT a
# 500 (an unhandled traceback would also lack .status==true and pass wrongly).
PCODE=$(curl -s -o /tmp/pt-body -w '%{http_code}' -X POST "$BASE/api/v1/retrieval/process/text" \
  -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name":"gate","content":"upgrade gate probe","collection_name":"upgrade-gate-col"}')
if jq -e '.status==true' /tmp/pt-body >/dev/null 2>&1; then
  no "RAG ingestion worked without chromadb?!"
elif [ "$PCODE" = "500" ]; then
  no "RAG ingestion 500'd (unhandled crash, not a clean degrade): $(head -c 120 /tmp/pt-body)"
else
  ok "RAG degrades cleanly pre-graft: HTTP $PCODE, no 500 crash"
fi
rm -f /tmp/pt-body

echo "== 4. vector-chroma graft opens the PRODUCTION vector store =="
G=$(curl -s --max-time 600 -X POST "$BASE/api/v1/retrieval/sprigs/graft" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name":"vector-chroma","capability":"vector"}')
echo "$G" | jq -e '.delivered==true' >/dev/null 2>&1 && ok "vector-chroma grafts on production data" \
  || no "vector-chroma graft: $(echo "$G" | head -c 200)"
# Parity, not a magic number: the pinned chromadb must see exactly what the
# snapshot's own sqlite records. (Discovered 2026-07-12: this production
# store records ZERO collections — a historic chroma upgrade on the server
# orphaned the HNSW dirs. Post-upgrade, knowledge bases need a re-index;
# the parity assertion still proves OUR chromadb reads the store faithfully.)
EXPECT=$(python3 - "$SNAP" <<'PY'
import shutil, sqlite3, sys, tempfile
src = f"{sys.argv[1].rstrip('/')}/vector_db/chroma.sqlite3"
with tempfile.NamedTemporaryFile(suffix=".sqlite3") as tmp:
    shutil.copyfile(src, tmp.name)  # never open the pristine file directly
    print(sqlite3.connect(tmp.name).execute("SELECT count(*) FROM collections").fetchone()[0])
PY
)
NCOLL=$(X 'python3 -c "
import chromadb
c = chromadb.PersistentClient(\"/app/backend/data/vector_db\")
print(len(c.list_collections()))" 2>/dev/null' | grep -E '^[0-9]+$' | tail -1)
[ "${NCOLL:-x}" = "${EXPECT:-y}" ] \
  && ok "pinned chromadb reads the store with collection PARITY ($NCOLL == snapshot's $EXPECT)" \
  || no "collection parity broken: container sees '$NCOLL', snapshot records '$EXPECT'"
NDIRS=$(ls -d "$SNAP"/vector_db/*/ 2>/dev/null | wc -l | tr -d ' ')
if [ "${NDIRS:-0}" -gt "${EXPECT:-0}" ]; then
  echo "  ⚠️  $NDIRS HNSW index dirs vs $EXPECT registered collections: orphaned"
  echo "     vector data (historic chroma upgrade residue). Knowledge bases need"
  echo "     a re-index after the upgrade; the orphan dirs are reclaimable disk."
fi

echo "== 5. theme surface on legacy data =="
curl -s "$BASE/themes/active.css" | grep -q 'no theme grafted' \
  && ok "themes route serves the empty default (legacy config has no theme)" || no "themes route wrong"
TG=$(curl -s --max-time 300 -X POST "$BASE/api/v1/retrieval/sprigs/graft" -H "$AUTH" -H 'Content-Type: application/json' \
  -d '{"name":"theme-workshop-bio","capability":"theme"}')
echo "$TG" | jq -e '.delivered==true' >/dev/null 2>&1 && curl -s "$BASE/themes/active.css" | grep -q 'workshop-bio' \
  && ok "theme grafts + serves on production data" || no "theme graft on legacy data failed"

echo "== 6. TARGET-ARCH capability reality on the production data =="
# The load-bearing rehearsal: boot the SAME production volume as the real
# deployment arch (default amd64 = sage.startr.cloud) and assert, capability by
# capability, whether the data's dependencies actually restore.
#
# PREFER a REAL target-arch container: boot the ${IMG}-<arch> image under
# --platform (QEMU) so executable cultivars — the onnx embedding server, the
# GGUF binaries — genuinely RUN, not just deliver. SPRIG_ARCH env-faking on the
# native image is a fallback that ONLY validates the arch guard + delivery: it
# runs native binaries, so a cross-arch executable cultivar can't load its .so
# and would false-fail. In that fallback we assert delivery-only and skip the
# executable embedding cultivar (with a loud note to build the real image).
TARGET_ARCH="${TARGET_ARCH:-amd64}"
HOST_ARCH_REAL=$(docker run --rm --entrypoint uname "$IMG" -m 2>/dev/null)
case "$HOST_ARCH_REAL" in aarch64) HOST_ARCH_REAL=arm64;; x86_64) HOST_ARCH_REAL=amd64;; esac
TGT_IMG="$IMG"; TGT_PLAT=(); TGT_ARCHENV=(-e SPRIG_ARCH="$TARGET_ARCH"); REAL_TARGET=0
if [ "$TARGET_ARCH" = "$HOST_ARCH_REAL" ]; then
  REAL_TARGET=1; TGT_ARCHENV=()                                   # native — already the target
elif docker image inspect "${IMG}-${TARGET_ARCH}" >/dev/null 2>&1; then
  TGT_IMG="${IMG}-${TARGET_ARCH}"; TGT_PLAT=(--platform "linux/${TARGET_ARCH}"); TGT_ARCHENV=(); REAL_TARGET=1
  echo "  (real ${TARGET_ARCH} container via QEMU — executable cultivars run for real)"
else
  echo "  ⚠️  no ${IMG}-${TARGET_ARCH} image — env-faking arch for GUARD+DELIVERY only;"
  echo "     executable cultivars can't run cross-arch this way. Build it"
  echo "     (make it_build_amd64 / cross_smoke) for a full amd64 execution proof."
fi
docker rm -f "${ROOT}-tgt" >/dev/null 2>&1 || true
docker volume rm "${VOL}-tgt" >/dev/null 2>&1 || true
docker volume create "${VOL}-tgt" >/dev/null
docker run --rm -v "$SNAP:/src:ro" -v "${VOL}-tgt:/dst" alpine:3.20 \
  sh -c "tar -C /src --exclude=./cache -cf - . | tar -C /dst -xf - && rm -f /dst/readme.txt" >/dev/null
docker run --rm -v "${VOL}-tgt:/data" -v "$HERE/scripts/snapshots/inject-test-admin.py:/inject.py:ro" \
  -e WEBUI_SECRET_KEY=upgrade-gate --entrypoint python3 "$IMG" /inject.py /data/webui.db "$ADMIN_EMAIL" "$ADMIN_PW" >/dev/null
docker run -d --name "${ROOT}-tgt" ${TGT_PLAT[@]+"${TGT_PLAT[@]}"} --network "$NET" -p "$((PORT+1)):8080" \
  -e SPRIG_REGISTRY=local-registry:5000 ${TGT_ARCHENV[@]+"${TGT_ARCHENV[@]}"} \
  -e WEBUI_AUTH=True -e WEBUI_SECRET_KEY=upgrade-gate-secret \
  -v "${VOL}-tgt:/app/backend/data" "$TGT_IMG" >/dev/null
for i in $(seq 1 150); do
  [ "$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:$((PORT+1))/health" 2>/dev/null)" = "200" ] && break; sleep 2
done
T2=$(curl -s -X POST "http://localhost:$((PORT+1))/api/v1/auths/signin" -H 'Content-Type: application/json' \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PW\"}" | jq -r '.token // empty')
A2="Authorization: Bearer $T2"
[ -n "$T2" ] && ok "target-arch ($TARGET_ARCH) boots the production volume" || no "target-arch boot failed"
docker logs "${ROOT}-tgt" 2>&1 | grep -q "Sprig™ host architecture: $TARGET_ARCH" \
  && ok "boot logs the detected host arch ($TARGET_ARCH)" || no "arch not logged at boot"

# The four capabilities the production data actually depends on. Since the
# 8.J amd64 artifacts shipped (vector-chroma/rag-loaders/export-document
# overlays + the arch-neutral ONNX embedding weights), every one MUST graft on
# the target arch — a refusal is now a capability gap and FAILS the gate.
# Embedding asserts the ONNX cultivar (the canonical amd64 path); the GGUF
# cultivars (e5-large-gguf, reranker) also graft on amd64 now but are optional,
# so they stay out of this deploy-critical assertion set.
GAPPED=0; BROKEN=0
# Deliver cultivars (extract-only) are validated in either mode. The embedding
# cultivar SPAWNS an onnx server child, so it only proves anything in a REAL
# target-arch container — under env-faking it can't load its cross-arch .so.
PAIRS=("vector-chroma:vector" "rag-loaders:rag" "export-document:export")
if [ "$REAL_TARGET" = "1" ]; then
  PAIRS+=("multilingual-e5-large:embedding")
else
  echo "  … skipping the embedding server cultivar (needs a real $TARGET_ARCH image to execute)"
fi
for pair in "${PAIRS[@]}"; do
  nm="${pair%%:*}"; cap="${pair##*:}"
  R=$(curl -s --max-time 60 -X POST "http://localhost:$((PORT+1))/api/v1/retrieval/sprigs/graft" \
    -H "$A2" -H 'Content-Type: application/json' -d "{\"name\":\"$nm\",\"capability\":\"$cap\"}")
  if echo "$R" | jq -e '.delivered==true or .status==true' >/dev/null 2>&1; then
    ok "$nm grafts on $TARGET_ARCH (capability available)"
  elif echo "$R" | grep -q "requires .* and this host is $TARGET_ARCH"; then
    echo "  ⛔ $nm REFUSED on $TARGET_ARCH — capability unavailable until an $TARGET_ARCH build ships (8.J)"
    GAPPED=$((GAPPED+1))
  else
    # A non-arch failure (disk, registry, extraction) — NOT a capability gap,
    # but the capability is still not graftable, so it must fail the summary.
    no "$nm: unexpected graft result: $(echo "$R" | head -c 160)"
    BROKEN=$((BROKEN+1))
  fi
done
# Neutral sprigs MUST still work on the target arch (the escape hatch).
TG2=$(curl -s --max-time 300 -X POST "http://localhost:$((PORT+1))/api/v1/retrieval/sprigs/graft" \
  -H "$A2" -H 'Content-Type: application/json' -d '{"name":"theme-workshop-math","capability":"theme"}')
echo "$TG2" | jq -e '.delivered==true' >/dev/null 2>&1 \
  && ok "architecture-neutral sprig still grafts on $TARGET_ARCH" || no "neutral graft on $TARGET_ARCH failed"
if [ "$GAPPED" -eq 0 ] && [ "$BROKEN" -eq 0 ]; then
  ok "no capability gap on $TARGET_ARCH — every production dependency is graftable"
elif [ "$GAPPED" -gt 0 ]; then
  no "CAPABILITY GAP: $GAPPED production-critical capabilities are NOT graftable on $TARGET_ARCH"
else
  no "$BROKEN production-critical graft(s) FAILED on $TARGET_ARCH for a non-arch reason (see above — disk/registry/extraction), NOT a capability gap"
fi
docker rm -f "${ROOT}-tgt" >/dev/null 2>&1 || true
docker volume rm "${VOL}-tgt" >/dev/null 2>&1 || true

echo ""
echo "================  UPGRADE GATE: ${PASS} passed, ${FAIL} failed  ================"
if [ "${GAPPED:-0}" -gt 0 ]; then
  echo "  DEPLOY BLOCKER: on ${TARGET_ARCH}, $GAPPED capabilities the production data"
  echo "  depends on (document search / ingestion / export / embedding) cannot be"
  echo "  restored by grafting. The ${TARGET_ARCH} artifacts shipped with 8.J, so a"
  echo "  refusal here means a missing/mismatched CATALOG pin or an unpublished"
  echo "  tag — the gate FAILS until every production dependency grafts."
fi
[ "$FAIL" -eq 0 ]
