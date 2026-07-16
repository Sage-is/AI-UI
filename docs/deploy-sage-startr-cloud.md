# Deploying to sage.startr.cloud — upgrade runbook and go/no-go

Target: **sage.startr.cloud**, amd64, currently v2.3.2 (32 users, 1982 chats,
18 knowledge bases, embedding engine = `openai` / text-embedding-3-small).
Snapshot used for rehearsal: `tools/db_snapshots/2026-07-12/` (read-only).

## Go / no-go: the amd64 capability gap (CLOSED 2026-07-15)

The slim rootstock dropped chromadb, langchain, pypdf/docx2txt, fpdf2, and the
whisper/embedding runtimes from the base image (they were baked into v2.3.2).
Those capabilities now arrive as Sprigs. The 8.J amd64 artifacts shipped
2026-07-15: every production-critical capability now grafts on this target.

| Capability | Depends on Sprig | amd64 today |
| --- | --- | --- |
| Document search / RAG retrieval | `vector-chroma` | GRAFTS (`v2-amd64`) |
| Document ingestion / upload | `rag-loaders` | GRAFTS (`v1-amd64`) |
| Chat → PDF export | `export-document` | GRAFTS (`v1-amd64`) |
| Local embedding (non-OpenAI) | ONNX cultivars (e5/bge/minilm) | GRAFTS (arch-neutral weights) |
| STT (voice notes) | `whisper-base-ggml` | GRAFTS (`v1-amd64`) |

Embedding runs the ONNX path on amd64 (weights are arch-neutral; the
onnxruntime rides `vector-chroma`). `media-ffmpeg` and `backup-rclone` amd64
shipped 2026-07-15 too (recipe-built static downloads), so browser voice
notes (webm/opus) transcode as well. The GGUF cultivars (`e5-large-gguf`,
`bge-reranker`) also graft on amd64 now (headless static llama-server,
`LLAMA_BUILD_UI=OFF`+`LLAMA_USE_PREBUILT_UI=OFF`), boot-tested under QEMU —
the whole catalog is both-arch.

`make upgrade_gate` proves all five grafts on the real snapshot (section 6 now
FAILS on any refusal — the gap is a blocker again, not a note). What always
worked on amd64: chat, auth, all users/chats/knowledge rows, the OpenAI-hosted
embedding config (external API, untouched), and every architecture-neutral
Sprig (themes, code-pyodide, browser-ml).

Mitigating fact: this production store's chroma already records **zero
collections** (654 orphaned HNSW dirs from a historic chroma upgrade), so
document search is ALREADY not functioning on v2.3.2 — the upgrade does not
regress a working feature, and the knowledge bases need a re-index regardless.

### Chosen path: build amd64 image + artifacts (2026-07-12, Alexander)

The Docker toolchain here (buildx + QEMU) builds both arches, so the plan is a
real multi-arch release: an amd64 rootstock image plus amd64 Sprig artifacts.

**Done this pass:**
- **amd64 rootstock image** builds green (`make it_build_amd64` → tag
  `-amd64`) and boots natively under QEMU: `uname -m` = x86_64, the boot log
  reports `host architecture: amd64`, the arch guard refuses arm64 artifacts
  with a clear message, the architecture-neutral theme Sprig grafts and serves,
  and `/catalog` reports `host_arch: amd64` with correct per-entry
  `compatible` flags.
- **Multi-arch catalog schema.** `arches` is now a dict `{arch: {tag,
  binary_sha256}}`, so an amd64 build drops in as one override entry per
  artifact — the same repo, an `-amd64`-suffixed tag, its own sha pin. graft()
  overlays the current host's override before pulling. arm64 behavior is
  unchanged (empty override = use the top-level pins).
- **`scripts/repack-sprig-arch.sh`** — since GGUF/ggml/onnx model files are
  architecture-neutral, an amd64 GGUF artifact is the arm64 tar with only its
  server binary swapped. The helper pulls, swaps, verifies the ELF arch,
  repacks reproducibly, signs, and pushes under the `-amd64` tag.

**Shipped 2026-07-15 (closes the gap for this target):**
- amd64 artifact builds for `vector-chroma` (`v2-amd64`), `rag-loaders`
  (`v1-amd64`), `export-document` (`v1-amd64`), `whisper-base-ggml`
  (`v1-amd64`) — new recipes `scripts/build-sprig-{vector-chroma,rag-loaders,
  export-document}.sh` plus the ARCH-parameterized whisper recipe. Each build
  runs its sanity gate on the target arch under QEMU before packing.
- The ONNX weight cultivars flipped to both-arch in the CATALOG (weights are
  arch-neutral bytes; the onnxruntime rides `vector-chroma`). Local embedding
  on amd64 is the ONNX path.
- All recipes and the publish flow run oras DOCKERIZED — no host oras anywhere.

**Still remaining (optional, not deploy-critical):**
- The llama.cpp amd64 yak (`e5-large-gguf`, reranker): b9859's web-UI embed
  step fails under the static musl cross-build — disable the bundled web UI or
  vendor a prebuilt asset, then `repack-sprig-arch.sh` produces the amd64 tags.
- `media-ffmpeg` / `backup-rclone` amd64 (static downloads) and `dev-svelte`.
  Until media-ffmpeg lands, browser voice notes (webm/opus) do not transcode
  on amd64.

Deploying to the amd64 target is no longer a functional downgrade: document
search, ingestion, PDF export, local embedding, and STT all graft.

## What this build fixes and adds (safe on any arch)

- **Registry is env-driven.** `SPRIG_REGISTRY` (default `ghcr.io/sage-is`,
  secure) replaces the hardcoded `local-registry:5000`. Point it at the
  in-cluster registry or a GHCR pull-through proxy; the sha256 pins guarantee
  the same bytes. `SPRIG_REGISTRY_INSECURE` gates plain-HTTP (auto-on only for
  loopback/local hosts).
- **Host-arch guard.** Refuses an incompatible Sprig at graft time with a clear
  message, before any bytes move — no more `Exec format error`. The admin panel
  greys out incompatible cards and shows "Not available on this server (amd64)".
- **Boot reachability + config checks.** The registry is probed at boot
  (unreachable = a loud log, not a per-graft 503 later); malformed
  `SPRIG_REGISTRY`, an unknown arch, and `SPRIG_REQUIRE_SIGNED` with no key are
  each named at boot.
- **Named registry volume.** `sprig-registry-data` replaces the anonymous
  volume that `docker volume prune` could have wiped (recovered 2.7 GB of
  artifacts mid-audit).
- **Upgrade gate.** `make upgrade_gate` boots THIS image on a copy of the
  production snapshot and proves migration, data survival, RAG degradation,
  chromadb store parity, themes, and the amd64 capability gap.

## Deploy steps (once a path above is chosen)

### [MANUALLY] Pre-deploy, one-time
1. Generate the production minisign key (recipe in `scripts/dev-keys/README.md`),
   `SIGN_KEY=~/sage-keys/sprig.key make sprig_sign`, then
   `FORCE=1 make sprig_publish`. The publish gate derives the repo list from
   the CATALOG and checks anonymous pullability via the ghcr token endpoint —
   all 16 packages are published and public as of 2026-07-15 (amd64 tags
   included), so a failure here means a NEW package that needs its one-time
   Public flip in the GitHub package settings.
2. [WE] Pin the `.pub` line as `_DEFAULT_PUBKEY` in `artifact.py`, flip catalog
   entries to `signed: True` if enforcing signatures.

### [WE] Rehearse
3. `make upgrade_gate` — must pass. Section 6 now asserts every
   production-critical capability GRAFTS on the target arch; any refusal fails
   the gate (a missing pin or unpublished tag, not an accepted gap).
4. `KEEP=1 make upgrade_gate` then the Cypress half:
   `TARGET_URL=http://sage-upgrade:8080 CYPRESS_ADMIN_EMAIL=upgrade-gate@sage.is
   CYPRESS_ADMIN_PASSWORD=upgrade-gate-pw-1234 SPEC='cypress/e2e/upgrade/*.cy.ts'
   scripts/e2e/run-cypress.sh`.

### [MANUALLY] Deploy
5. Back up the live server's data volume (already done: the 2026-07-12 snapshot).
6. Pull/deploy the new image with `SPRIG_REGISTRY` set to the production
   registry. Boot; watch the log for the arch line, registry reachability, and
   any config errors.
7. Verify: users sign in, chats load, the OpenAI embedding config is intact.
8. Re-index knowledge bases (they need it regardless — the store records zero
   collections). This requires `vector-chroma` + `rag-loaders`, so it only
   works once the amd64 path (decision above) is in place.
9. Reclaim disk: the 654 orphaned `vector_db/*/` HNSW dirs are safe to remove
   after a successful re-index.

## Rollback
Keep the v2.3.2 image tagged. If the upgrade misbehaves, redeploy v2.3.2 against
the same volume (the snapshot is the safety net) — the new image's migrations
are additive and v2.3.2 tolerates the volume it wrote.
