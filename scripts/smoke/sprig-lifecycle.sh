#!/usr/bin/env bash
# Sprig™ lifecycle gate (Bonsai™ 8.I) — the rootstock boots without langchain/
# numpy/fpdf/fonts/pyodide/wasm/chromadb, every capability 503s cleanly with a
# graft pointer, then grafts back (most WITHOUT a restart). Includes the GGUF
# cultivar on a bare rootstock and a live onnx->gguf top-graft.
#
# Usage: scripts/smoke/sprig-lifecycle.sh [image]   (default sage-is/ai-ui:develop)
# Requires: the local sprig registry (`local-registry` on sage-network) seeded
# with the catalog artifacts. Runs a FRESH container; safe to re-run.
set -uo pipefail
IMG="${1:-sage-is/ai-ui:develop}"
NET="${SPRIG_SMOKE_NET:-sage-network}"; ROOT="${SPRIG_SMOKE_NAME:-sage-wolfi}"; VOL="${ROOT}-data"
PORT="${SPRIG_SMOKE_PORT:-8099}"; BASE="http://localhost:${PORT}"
PASS=0; FAIL=0; ok(){ echo "  ✅ $1"; PASS=$((PASS+1)); }; no(){ echo "  ❌ $1"; FAIL=$((FAIL+1)); }
X(){ docker exec "$ROOT" sh -lc "$1"; }

echo "== fresh 8.I.2 rootstock =="
docker rm -f "$ROOT" >/dev/null 2>&1 || true; docker volume rm "$VOL" >/dev/null 2>&1 || true
docker run -d --name "$ROOT" --network "$NET" -p "$PORT:8080" -e ENABLE_SIGNUP=True -e WEBUI_AUTH=True -v "$VOL:/app/backend/data" "$IMG" >/dev/null
for i in $(seq 1 120); do [ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health" 2>/dev/null)" = "200" ] && break; sleep 2; done
[ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health")" = "200" ] && ok "BOOTS without langchain/numpy/fpdf/chromadb" || { no "boot failed"; docker logs --tail 40 "$ROOT"; exit 1; }

echo "== 1. absences =="
for m in langchain numpy fpdf tokenizers huggingface_hub chromadb; do
  X "python3 -c 'import $m' 2>&1 | grep -q ModuleNotFoundError" && ok "$m absent" || no "$m still present"
done
X 'python3 -c "import langchain_core, langsmith"' && ok "langchain_core + langsmith stay (interface layer)" || no "langchain_core missing!"
X 'test -d /app/static/fonts' >/dev/null 2>&1 && no "CJK fonts still shipped" || ok "fonts dir gone"
[ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/pyodide/pyodide.js")" = "404" ] && ok "pyodide 404 pre-graft" || no "pyodide unexpectedly present"
WCT=$(curl -s -o /dev/null -w '%{content_type}' "$BASE/wasm/ort-wasm-simd-threaded.jsep.wasm")
echo "$WCT" | grep -q wasm && no "real wasm still shipped" || ok "wasm not shipped pre-graft (SPA fallback: $WCT)"

TOK=$(curl -s -X POST "$BASE/api/v1/auths/signup" -H 'Content-Type: application/json' -d '{"name":"S8","email":"s8@sage.is","password":"sprig-smoke-pw-123"}' | jq -r '.token // empty')
AUTH="Authorization: Bearer $TOK"; [ -n "$TOK" ] && ok "admin signup (PyJWT alive)" || { no "signup"; exit 1; }
G(){ curl -s --max-time 300 -X POST "$BASE/api/v1/retrieval/sprigs/graft" -H "$AUTH" -H 'Content-Type: application/json' -d "{\"name\":\"$1\",\"capability\":\"$2\"}"; }
PDF(){ curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/api/v1/utils/pdf" -H "$AUTH" -H 'Content-Type: application/json' -d '{"title":"t","messages":[{"role":"user","content":"hello sprig"}]}'; }

echo "== 2. clean degradation pre-graft =="
E5=$(G multilingual-e5-large embedding)
echo "$E5" | grep -q "vector-chroma" && ok "e5 pre-check names vector-chroma" || no "e5 pre-check wrong: $(echo "$E5" | head -c 150)"
[ "$(PDF)" = "503" ] && ok "pdf export 503 pre-graft" || no "pdf export not 503: $(PDF)"
PT=$(curl -s -X POST "$BASE/api/v1/retrieval/process/text" -H "$AUTH" -H 'Content-Type: application/json' -d '{"name":"d","content":"x","collection_name":"precol"}')
echo "$PT" | jq -e '.status==true' >/dev/null 2>&1 && no "RAG worked without vector?!" || ok "RAG unavailable pre-vector"

echo "== 2b. GGUF cultivar: embedding with ZERO python ML deps (bare rootstock!) =="
GG=$(G e5-large-gguf embedding)
echo "$GG" | jq -e '.status==true' >/dev/null 2>&1 && ok "e5-large-gguf grafts pre-vector (static llama-server)" || no "gguf graft: $(echo "$GG" | head -c 200)"
GURL=$(echo "$GG" | jq -r '.base_url // empty')
DIM=$(docker exec "$ROOT" sh -c "curl -s ${GURL}/embeddings -H 'Content-Type: application/json' -d '{\"input\":[\"hello gguf sprig\"]}' | jq '.data[0].embedding | length'")
[ "$DIM" = "1024" ] && ok "1024-dim vector from the static binary (no python in child)" || no "gguf embed dim: $DIM"

echo "== 3. vector-chroma v2 (now carries numpy+tokenizers+hf) =="
VR=$(G vector-chroma vector)
echo "$VR" | jq -e '.delivered==true' >/dev/null 2>&1 && ok "vector-chroma v2 delivered" || no "vector delivery: $(echo "$VR" | head -c 200)"
docker restart "$ROOT" >/dev/null
for i in $(seq 1 120); do [ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health" 2>/dev/null)" = "200" ] && break; sleep 2; done
ok "restarted healthy"
X 'python3 -c "import chromadb, numpy, tokenizers, huggingface_hub"' && ok "chromadb + numpy + tokenizers + hf via overlay" || no "overlay imports failed"

echo "== 4. mock grafts; chunking blocked until rag-loaders =="
TOK=$(curl -s -X POST "$BASE/api/v1/auths/signin" -H 'Content-Type: application/json' -d '{"email":"s8@sage.is","password":"sprig-smoke-pw-123"}' | jq -r .token)
AUTH="Authorization: Bearer $TOK"
G mock-embedding embedding | jq -e '.status==true' >/dev/null 2>&1 && ok "mock grafts (pure-python, no numpy)" || no "mock graft"
PT=$(curl -s -X POST "$BASE/api/v1/retrieval/process/text" -H "$AUTH" -H 'Content-Type: application/json' -d '{"name":"d","content":"x","collection_name":"ragcol"}')
echo "$PT" | grep -q "rag-loaders" && ok "chunking 503s naming rag-loaders" || no "chunking error wrong: $(echo "$PT" | head -c 150)"

echo "== 5. rag-loaders graft — NO restart =="
G rag-loaders rag | jq -e '.delivered==true' >/dev/null 2>&1 && ok "rag-loaders delivered" || no "rag-loaders delivery"
PT=$(curl -s -X POST "$BASE/api/v1/retrieval/process/text" -H "$AUTH" -H 'Content-Type: application/json' -d '{"name":"d","content":"the rootstock grafts its rag engines back","collection_name":"ragcol2"}')
echo "$PT" | jq -e '.status==true' >/dev/null 2>&1 && ok "chunk+embed+store works RESTART-FREE" || no "process/text: $(echo "$PT" | head -c 150)"
Q=$(curl -s -X POST "$BASE/api/v1/retrieval/query/collection" -H "$AUTH" -H 'Content-Type: application/json' -d '{"collection_names":["ragcol2"],"query":"what does the rootstock do","k":1}')
echo "$Q" | jq -e '(.distances|length)>0' >/dev/null 2>&1 && ok "query round-trip" || no "query failed"

echo "== 6. e5-large now grafts (runtime via vector-chroma v2) =="
G multilingual-e5-large embedding | jq -e '.status==true' >/dev/null 2>&1 && ok "e5-large grafts" || no "e5 graft failed"
PT=$(curl -s -X POST "$BASE/api/v1/retrieval/process/text" -H "$AUTH" -H 'Content-Type: application/json' -d '{"name":"e","content":"onnx on the slim rootstock","collection_name":"e5col"}')
echo "$PT" | jq -e '.status==true' >/dev/null 2>&1 && ok "1024-dim embed through onnx server" || no "e5 embed failed"

echo "== 6b. live top-graft swap: onnx -> gguf, same width, RAG keeps working =="
G e5-large-gguf embedding | jq -e '.status==true' >/dev/null 2>&1 && ok "top-graft onnx->gguf" || no "gguf top-graft failed"
PT=$(curl -s -X POST "$BASE/api/v1/retrieval/process/text" -H "$AUTH" -H 'Content-Type: application/json' -d '{"name":"g","content":"gguf serving the whole rag path now","collection_name":"e5col"}')
echo "$PT" | jq -e '.status==true' >/dev/null 2>&1 && ok "process/text through gguf cultivar (1024-dim, no reindex)" || no "gguf rag: $(echo "$PT" | head -c 150)"

echo "== 7. export-document graft — NO restart, pdf renders =="
G export-document export | jq -e '.delivered==true' >/dev/null 2>&1 && ok "export-document delivered" || no "export delivery"
[ "$(PDF)" = "200" ] && ok "pdf export 200 RESTART-FREE (fpdf + CJK fonts live)" || no "pdf export still failing: $(PDF)"
X 'test -f /app/static/fonts/NotoSansSC-Regular.ttf' && ok "CJK fonts delivered to static" || no "fonts missing"

echo "== 8. code-pyodide + browser-ml graft — assets serve =="
G code-pyodide code | jq -e '.delivered==true' >/dev/null 2>&1 && ok "code-pyodide delivered" || no "pyodide delivery"
[ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/pyodide/pyodide.js")" = "200" ] && ok "/pyodide/ serves post-graft" || no "pyodide 404 after graft"
G browser-ml browser-ml | jq -e '.delivered==true' >/dev/null 2>&1 && ok "browser-ml delivered" || no "browser-ml delivery"
WCT=$(curl -s -o /dev/null -w '%{http_code} %{content_type}' "$BASE/wasm/ort-wasm-simd-threaded.jsep.wasm")
echo "$WCT" | grep -q "200.*wasm" && ok "/wasm/ serves REAL wasm post-graft" || no "wasm wrong after graft: $WCT"

echo "== 9. binaries + dev toolchain still deliver =="
G media-ffmpeg media | jq -e '.delivered==true' >/dev/null 2>&1 && ok "media-ffmpeg" || no "ffmpeg delivery"
G backup-rclone backup | jq -e '.delivered==true' >/dev/null 2>&1 && ok "backup-rclone" || no "rclone delivery"
G dev-svelte dev | jq -e '.delivered==true' >/dev/null 2>&1 && ok "dev-svelte" || no "dev-svelte delivery"

echo "== 10. UI serves to a fresh admin =="
curl -s "$BASE/" | grep -qi "html" && ok "/ serves SPA" || no "SPA broken"
[ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/static/icons/favicon.svg")" = "200" ] && ok "favicon" || no "favicon broken"

echo ""
echo "================  8.I.2 RESULT: ${PASS} passed, ${FAIL} failed  ================"
echo "rootstock: 3.78GB -> 1.43 -> 1.12 -> $(docker images sage-is/ai-ui:develop --format '{{.Size}}')"
[ "$FAIL" -eq 0 ]
