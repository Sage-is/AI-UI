# Deploying to sage.startr.cloud — upgrade runbook and go/no-go

Target: **sage.startr.cloud**, amd64, currently v2.3.2 (32 users, 1982 chats,
18 knowledge bases, embedding engine = `openai` / text-embedding-3-small).
Snapshot used for rehearsal: `tools/db_snapshots/2026-07-12/` (read-only).

## Go / no-go: the amd64 capability gap (READ FIRST)

The slim rootstock dropped chromadb, langchain, pypdf/docx2txt, fpdf2, and the
whisper/embedding runtimes from the base image (they were baked into v2.3.2).
Those capabilities now arrive as Sprigs. **Every one of those Sprigs is
arm64-only today** (roadmap 8.J has not shipped amd64 builds). The host-arch
guard correctly refuses them on amd64, which means on this target the upgrade
would leave four production-critical capabilities with no recovery path:

| Capability | Depends on Sprig | amd64 today |
| --- | --- | --- |
| Document search / RAG retrieval | `vector-chroma` | REFUSED (arm64-only) |
| Document ingestion / upload | `rag-loaders` | REFUSED (arm64-only) |
| Chat → PDF export | `export-document` | REFUSED (arm64-only) |
| Local embedding (non-OpenAI) | `e5-large-gguf` etc. | REFUSED (arm64-only) |
| STT (voice notes) | `whisper-base-ggml` | REFUSED (arm64-only) |

`make upgrade_gate` proves this on the real snapshot and prints the gap
explicitly (section 6 + `CAPABILITY GAP` + `DEPLOY NOTE`). What still works on
amd64: chat, auth, all users/chats/knowledge rows, the OpenAI-hosted embedding
config (external API, untouched), and every architecture-neutral Sprig (themes,
code-pyodide, browser-ml).

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

**Remaining (the amd64 artifact builds — a scoped follow-on, roadmap 8.J):**
- The 3 recipe-having binaries need amd64 server builds: `llama-server`
  (e5-gguf, reranker) and `whisper-server` (stt). First attempt hit a real yak
  — llama.cpp b9859's web-UI embed step fails under the static musl config
  when cross-built; that build needs a fix (disable the bundled web UI, or
  vendor a prebuilt asset) before the amd64 binary lands. Once it does,
  `repack-sprig-arch.sh` produces the three amd64 GGUF artifacts.
- The 8 recipe-less artifacts (`vector-chroma`, `rag-loaders`,
  `export-document`, `media-ffmpeg`, `backup-rclone`, and the onnx weight
  cultivars' serving overlay) need their build recipes written first — the
  same #critical recipe-gap that gates reproducibility — then amd64 builds:
  static amd64 ffmpeg/rclone are downloads; the python-wheel closures
  (chromadb/onnxruntime/hnswlib/pillow/fpdf) need amd64 wheels via buildx.
- Move option (an arm64 host) or the deps-baked amd64 variant remain fallbacks
  if the artifact builds slip; the schema + image work above stand regardless.

Until the amd64 artifacts land, deploying to the amd64 target is a **functional
downgrade** for on-box document/embedding/export features. The neutral Sprigs
(themes, code-pyodide, browser-ml) and everything non-Sprig already work on the
amd64 image.

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
   `FORCE=1 make sprig_publish`. The publish gate now derives the repo list from
   the CATALOG and checks anonymous pullability via the ghcr token endpoint —
   it will FAIL loudly on the two theme packages (`sprig-theme-workshop-bio`,
   `sprig-theme-workshop-math`), which are built but not yet pushed/public.
   Push them and flip both to Public in the GitHub package settings.
2. [WE] Pin the `.pub` line as `_DEFAULT_PUBKEY` in `artifact.py`, flip catalog
   entries to `signed: True` if enforcing signatures.

### [WE] Rehearse
3. `make upgrade_gate` — must pass (the amd64 capability-gap note is expected on
   an amd64 target; it is a go/no-go signal, not a failure).
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
