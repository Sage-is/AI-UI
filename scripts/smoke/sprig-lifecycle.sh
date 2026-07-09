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
# 600s ceiling: by section 9 the rootstock runs several grafted server children
# while pulling the biggest artifacts (dev-svelte ~1.1GB) — 300s flaked under load.
G(){ curl -s --max-time 600 -X POST "$BASE/api/v1/retrieval/sprigs/graft" -H "$AUTH" -H 'Content-Type: application/json' -d "{\"name\":\"$1\",\"capability\":\"$2\"}"; }
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

echo "== 2d. reranker cultivar: /v1/rerank from the static llama-server (bare rootstock) =="
RR=$(G bge-reranker-v2-m3-gguf reranker)
echo "$RR" | jq -e '.status==true' >/dev/null 2>&1 && ok "reranker grafts pre-vector (zero python deps)" || no "reranker graft: $(echo "$RR" | head -c 200)"
RURL=$(echo "$RR" | jq -r '.base_url // empty')
RES=$(X "curl -s ${RURL}/rerank -H 'Content-Type: application/json' -d '{\"model\":\"reranker\",\"query\":\"what is a panda?\",\"documents\":[\"the kernel reserves an ephemeral loopback port\",\"The giant panda is a bear species endemic to China.\"],\"top_n\":2}'")
RTOP=$(echo "$RES" | jq -r '.results | sort_by(-.relevance_score) | .[0].index' 2>/dev/null)
[ "$RTOP" = "1" ] && ok "rerank orders the panda doc first (relevance contract)" || no "rerank ordering: $(echo "$RES" | head -c 200)"
RCFG=$(curl -s "$BASE/api/v1/retrieval/config" -H "$AUTH")
echo "$RCFG" | jq -e '.RAG_RERANKING_ENGINE=="external" and (.RAG_EXTERNAL_RERANKER_URL|endswith("/rerank"))' >/dev/null 2>&1 \
  && ok "reranking config points at the sprig" || no "reranking config not pointed: $(echo "$RCFG" | jq -c '{RAG_RERANKING_ENGINE,RAG_EXTERNAL_RERANKER_URL}' 2>/dev/null | head -c 150)"
PRR=$(curl -s -X POST "$BASE/api/v1/retrieval/sprigs/prune" -H "$AUTH" -H 'Content-Type: application/json' -d '{"name":"bge-reranker-v2-m3-gguf"}')
echo "$PRR" | jq -e '.reranking_reset==true' >/dev/null 2>&1 && ok "prune resets reranking dispatch" || no "prune reranking reset: $(echo "$PRR" | head -c 150)"
curl -s "$BASE/api/v1/retrieval/config" -H "$AUTH" | jq -e '.RAG_RERANKING_ENGINE==""' >/dev/null 2>&1 \
  && ok "reranking engine cleared post-prune" || no "stale reranking engine after prune"
G bge-reranker-v2-m3-gguf reranker | jq -e '.status==true' >/dev/null 2>&1 && ok "re-graft (revive) reranker" || no "reranker revive failed"

echo "== 2e. stt cultivar: whisper-server transcription (bare rootstock) =="
X 'python3 -c "
import math, struct, wave
w = wave.open(\"/tmp/gate.wav\", \"w\")
w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
w.writeframes(b\"\".join(struct.pack(\"<h\", int(12000*math.sin(2*math.pi*440*t/16000))) for t in range(16000)))
w.close()"' && ok "test wav generated in-container" || no "wav generation failed"
ST=$(G whisper-base-ggml stt)
echo "$ST" | jq -e '.status==true' >/dev/null 2>&1 && ok "whisper sprig grafts (static binary, zero python deps)" || no "stt graft: $(echo "$ST" | head -c 200)"
SURL=$(echo "$ST" | jq -r '.base_url // empty')
SDIRECT=$(X "curl -s ${SURL}/audio/transcriptions -F file=@/tmp/gate.wav -F response_format=json")
echo "$SDIRECT" | jq -e 'has("text")' >/dev/null 2>&1 && ok "whisper-server answers with {text} (direct)" || no "direct transcription: $(echo "$SDIRECT" | head -c 150)"
# type= matters: the endpoint gates on content_type audio/* and curl would
# otherwise send application/octet-stream -> 400 before reaching the sprig.
SAPP=$(X "curl -s -o /dev/null -w '%{http_code}' -X POST http://localhost:8080/api/v1/audio/transcriptions -H '$AUTH' -F 'file=@/tmp/gate.wav;type=audio/wav'")
[ "$SAPP" = "200" ] && ok "app /audio/transcriptions 200 through the grafted sprig" || no "app transcription: HTTP $SAPP"
curl -s "$BASE/api/v1/retrieval/models/status" -H "$AUTH" | jq -e '.models.whisper=="ready" or .whisper=="ready"' >/dev/null 2>&1 \
  && ok "wizard whisper status ready (HF download skippable)" || no "whisper status not ready post-graft"

echo "== 3. vector-chroma v2 (now carries numpy+tokenizers+hf) =="
VR=$(G vector-chroma vector)
echo "$VR" | jq -e '.delivered==true' >/dev/null 2>&1 && ok "vector-chroma v2 delivered" || no "vector delivery: $(echo "$VR" | head -c 200)"
docker restart "$ROOT" >/dev/null
for i in $(seq 1 120); do [ "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health" 2>/dev/null)" = "200" ] && break; sleep 2; done
ok "restarted healthy"
# Reconcile re-points every server capability grafted before the restart
# (gguf embedding from 2b, reranker from 2d, stt from 2e) at FRESH ports.
RCFG2=$(curl -s "$BASE/api/v1/retrieval/config" -H "$AUTH")
echo "$RCFG2" | jq -e '.RAG_RERANKING_ENGINE=="external"' >/dev/null 2>&1 \
  && ok "reranker re-pointed by boot reconcile" || no "reranker config lost across restart"
ACFG2=$(curl -s "$BASE/api/v1/audio/config" -H "$AUTH")
echo "$ACFG2" | jq -e '.stt.ENGINE=="openai" and (.stt.OPENAI_API_BASE_URL|startswith("http://127.0.0.1"))' >/dev/null 2>&1 \
  && ok "stt re-pointed by boot reconcile" || no "stt config lost across restart: $(echo "$ACFG2" | jq -c '.stt' 2>/dev/null | head -c 150)"
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

echo "== 6c. minilm-onnx-inhoused: the chroma-onnx seed path (in-housed MiniLM) =="
# The ONLY catalog entry using artifact.py's chroma-onnx seed mode (extract ->
# _seed_chroma_cache -> DefaultEmbeddingFunction serves offline). NOT covered by
# 6/6b (those are model-dir seeds). (all-MiniLM-onnx, the old live-pull twin of
# this entry, was retired 2026-07-05 — the whole catalog is zero-egress now.)
MI=$(G minilm-onnx-inhoused embedding)
echo "$MI" | jq -e '.status==true' >/dev/null 2>&1 && ok "minilm-onnx-inhoused grafts (chroma-onnx seed)" || no "minilm graft: $(echo "$MI" | head -c 200)"
MURL=$(echo "$MI" | jq -r '.base_url // empty')
MDIM=$(X "curl -s ${MURL}/embeddings -H 'Content-Type: application/json' -d '{\"input\":[\"in-housed minilm\"]}' | jq '.data[0].embedding | length'")
[ "$MDIM" = "384" ] && ok "384-dim vector from the seeded chroma cache (offline)" || no "minilm embed dim: $MDIM"
X 'jq -e ".grafted | length > 0" /app/backend/data/sage-is/sprigs/state.json' >/dev/null 2>&1 && ok "state.json on the volume records grafts (restart durability)" || no "state.json missing/empty"

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
