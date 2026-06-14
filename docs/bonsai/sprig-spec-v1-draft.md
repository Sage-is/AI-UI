# Sprig Spec™ v1 (draft)

> **Status:** Draft. This document is the contract Sprig™ authors and Bonsai™ rootstocks will hold each other to. Review, edit, and then move to the canonical home at `github.com/sage-is/sprig-spec`.

This document is the contract between a Sprig™ and a Bonsai™ rootstock. If you are building either side, the requirements below are what you sign up for.

A Sprig™ is a versioned binary artifact an operator grafts onto a Bonsai™ rootstock at runtime. Grafting adds a capability — an embedding model, a transcription engine, a tunnel client, whatever the operator needs. Pruning removes one. The rootstock owns the web framework, auth, storage, and the supervisor. Each Sprig™ owns one capability and nothing more.

v1 covers HTTP transport only. Most AI capabilities already speak HTTP, so this is the path of least resistance for the first round of Sprigs™ and the easiest contract to test against. The naming convention and Sprig Manifest™ schema reserve vocabulary for `unix_socket`, `stdio`, `signal`, and `none`, but their full contracts get written in later spec versions. A v1 rootstock rejects Sprigs™ that declare any other transport.

A conforming Sprig™ satisfies the requirements in [Conformance](#conformance). A conforming rootstock refuses Sprigs™ targeting a spec version it cannot honor.

## Scope of v1

- HTTP transport — loopback for `delivery: oci-artifact`, TLS over the public network for `delivery: service-endpoint`
- OpenAI-compatible request shape on `/v1/*` endpoints
- `sage-is/v1/` extension namespace for capabilities OpenAI's spec does not cover
- tar.zst artifact format published as OCI Artifacts
- Sigstore signing
- SemVer + Cultivar™ + Variety™ naming
- Grafted, Dormant, Wilted, Pruned lifecycle states

Out of scope for v1: non-HTTP transports, multi-Sprig™ composition, on-the-fly cultivar swapping mid-request.

## Vocabulary

- **Bonsai™** — the rootstock image. Small (~120 MB). Owns the framework, auth, storage, and the Graft Union™.
- **Sprig™** — a separable capability artifact. Tar.zst with a manifest, a binary, and per-Cultivar™ assets.
- **Cultivar™** — the model variant inside a Sprig™ (e.g. `e5-large`, `bge-large-en`).
- **Variety™** — the platform build inside a Sprig™ (e.g. `linux-amd64-cpu`, `linux-arm64-cpu`).
- **Graft Union™** — the boundary between rootstock and Sprig™. v1: HTTP. Loopback for `delivery: oci-artifact`; TLS over the public network for `delivery: service-endpoint`.
- **Graft / Prune / Topgraft** — operator actions. Graft attaches a Sprig™; prune removes one; topgraft swaps the grafted Cultivar™.
- **Sprig Catalog™** — the rootstock's view of available + grafted Sprigs™.
- **Sprig Manifest™** — `sprig.yaml` inside the tar.zst. Declares Cultivar™, Variety™, capability, transport, and process args.
- **Sprig Spec™** — this document.

## License compatibility

The `license:` field in `sprig.yaml` declares the Sprig™ artifact's own license. Any SPDX identifier or the literal `proprietary` is valid. Sprig™ authors are explicitly free to ship under any license — proprietary, MIT, Apache-2.0, BSD, GPL, AGPL, or anything else.

The Sage.is Rootstock™ reference implementation is licensed AGPL-3.0. A Sprig™ is not a derivative work of the Rootstock™. A Sprig™ communicates with the Rootstock™ across an arms-length process boundary using the contract defined in this spec — HTTP over loopback for `delivery: oci-artifact`, HTTPS over the public network for `delivery: service-endpoint`, the `none` transport for one-shot build tooling. Every transport in v1 crosses a real process boundary; nothing about a Sprig™ links into the Rootstock™'s address space, embeds Rootstock™ source code, or constitutes modification of the AGPL'd program.

This is the same arrangement the FSF treats as aggregation rather than combined work. Proprietary userspace running on a GPL'd Linux kernel does not inherit the kernel's license. A closed-source database client talking to a GPL'd database server over a socket does not inherit the server's license. A Sprig™ talking to the Rootstock™ over the published Sprig Spec™ contract follows the same pattern.

AGPL-3.0 Section 13's network clause fires only when an entity (a) modifies the AGPL'd program and (b) exposes the modified version to remote users. An operator running an unmodified Sage.is Rootstock™ with grafted proprietary Sprigs™ triggers zero AGPL obligation, regardless of how many proprietary Sprigs™ they graft.

### Edge cases

A Sprig™ that bundles or statically links Rootstock™ source code (for example, imports `routers/openai.py` to reuse a helper) IS a derivative work and must respect AGPL-3.0. Build against the published Sprig Spec™ contract instead.

An operator who modifies the Rootstock™ source triggers AGPL Section 13 for the Rootstock™ part. Their grafted Sprigs™ remain on the other side of the arms-length boundary and are unaffected by the operator's Rootstock™ modifications.

The eventual `sage-is-sprig-sdk-py` developer SDK ships under MIT (or an equivalent permissive license) so it does not propagate AGPL into Sprig™ authors' own codebases. Sprig™ authors who depend on the SDK keep their own licensing freedom intact.

Third-party rootstock implementations of the published Rootstock Spec™ may be licensed under anything — proprietary, BSD, Apache-2.0, GPL, AGPL. The spec itself is implementation-language-agnostic and license-agnostic for conforming rootstocks.

## Lifecycle states

A Sprig™ moves through six states. The rootstock surfaces all of them in `/admin/sprigs` and `/admin/diagnostics`.

- **Sprouted** — known to the catalog, not yet pulled. The operator has selected it but `oras pull` has not run.
- **Grafting** — the tar.zst is pulling and extracting; the binary will start after.
- **Grafted** — the binary runs and `GET /health` returns 200. The steady state.
- **Dormant** — extracted to disk but not running. The operator paused it, or the rootstock saw it was unhealthy and stopped restart attempts.
- **Wilted** — was grafted, has stopped answering. Maybe the binary crashed. Maybe the port went silent. Maybe the supervisor exhausted backoff. The row stays in the registry, the artifact stays on disk, and the operator gets a "Revive" action. We do not call this "Failed" because failed implies terminal, and most causes here are recoverable with a restart.
- **Pruned** — the operator removed the Sprig™ and the artifact is gone from disk. Reverse with a fresh graft.

Transitions:

```text
sprouted → grafting → grafted
grafted ↔ wilted (supervisor restart-with-backoff)
grafted | wilted → pruned (operator action)
pruned → sprouted (re-add to catalog)
```

The operator UI uses "Wilted" rather than "Failed" everywhere a Sprig™ stops responding.

For `delivery: service-endpoint` Sprigs™ the same state vocabulary applies but the semantics compress. Grafting is the TLS handshake, auth validation, and the first `/sage-is/v1/inspect` probe that confirms the remote reports the declared `spec_version`. There is no Dormant in v1 for service-endpoint Sprigs™; the rootstock either dispatches to the remote or it does not. Wilted means the endpoint stopped answering or a periodic `/inspect` returned a mismatch. Pruned means the operator removed the manifest entry. The rootstock cannot delete somebody else's artifact, so Pruned is purely a local state change. Revive re-probes the endpoint instead of restarting a process.

## Naming convention

Sprig™ artifacts follow this template:

```text
ghcr.io/sage-is/sprig-<capability>-<cultivar>:v<X.Y>-<variety>
```

Examples:

```text
ghcr.io/sage-is/sprig-embedding-e5-large:v1.0-linux-amd64-cpu
ghcr.io/sage-is/sprig-embedding-bge-large-en:v1.0-linux-arm64-cpu
ghcr.io/sage-is/sprig-whisper-medium:v1.0-linux-amd64-cpu
ghcr.io/sage-is/sprig-tunnel-cloudflared:v1.0-linux-amd64
```

Rules:

- `<capability>` — kebab-case capability namespace. Examples: `embedding`, `whisper`, `tts-kokoro`, `parse-docs`, `tunnel-cloudflared`. The rootstock dispatches by this string.
- `<cultivar>` — kebab-case model identifier within the capability. Examples: `e5-large`, `bge-large-en`, `medium`. For capabilities without a model (tunnels, monitors), omit the cultivar suffix; the artifact name reads `sprig-<capability>` only.
- `v<X.Y>` — SemVer MAJOR.MINOR pinning. PATCH versions float within a MAJOR.MINOR window. A breaking API change to the Sprig™ binary bumps MAJOR; backward-compatible feature adds bump MINOR; bug fixes bump PATCH.
- `<variety>` — kebab-case descriptor whose shape depends on delivery. For `delivery: oci-artifact`, variety is a platform descriptor: `linux-<arch>-<accel>`. Architectures: `amd64`, `arm64`. Accelerators: `cpu`, `cuda12`, `cuda13`, `metal`. Pick the narrowest match. For `delivery: service-endpoint`, variety starts with the sentinel prefix `hosted-` followed by a publisher-defined descriptor: `hosted-default`, `hosted-us-east`, `hosted-eu-west`, `hosted-premium`, `hosted-edge`, etc. The `hosted-` prefix marks the variety as a runtime topology rather than a build target. A `delivery: service-endpoint` Sprig™ MAY advertise multiple varieties under one capability name (regions, performance tiers, residency zones); see [Variety selection](#variety-selection) below.

Reserved capability prefixes, grouped by family:

**ML capabilities** (OpenAI-compatible HTTP shapes by default):

- `embedding-` — text embedding (OpenAI `/v1/embeddings` shape)
- `whisper-` — speech transcription (OpenAI `/v1/audio/transcriptions` shape)
- `tts-` — text to speech (OpenAI `/v1/audio/speech` shape)
- `imagegen-` — image generation (OpenAI `/v1/images/generations` shape)
- `parse-`, `ocr-`, `tokenize-`, `diarize-`, `rag-` — `sage-is/v1/` extension namespace

**Infrastructure capabilities** (typically non-HTTP transports in later spec versions):

- `tunnel-`, `monitor-`, `backup-`, `fetcher-` — operator-side infrastructure Sprigs™ (cloudflared, prometheus exporter, rclone backup, playwright fetcher)

**Dev/build tooling** (added in v1 alongside the `none` transport — see Transport: none below):

- `dev-` — continuously-running development tooling. Reference: `sage-is/sprig-dev-svelte` (vite dev server + HMR over HTTP transport). Live during development only; the Rootstock™ proxies frontend requests to the grafted Sprig™ when present, and never grafts dev tooling in a production deployment.
- `build-` — one-shot build operations using the `none` transport. Reference: `sage-is/sprig-build-svelte`. Runs, produces artifacts in the extraction directory under `${SPRIG_ROOT}/output/` (or a path declared in the manifest's `process.output_dir`), exits with code 0 on success. The Rootstock™ consumes the artifacts (e.g., copies them to its static-asset surface) after a successful exit.

## Artifact format

A Sprig™ ships as a Zstandard-compressed tarball published as an OCI Artifact.

```text
sage-is-sprig-embedding-e5-large-v1.0-linux-amd64-cpu.tar.zst
```

Layout inside the tar:

```text
sprig.yaml            # required: Sprig Manifest™ (schema below)
bin/                  # required: the binary the rootstock executes
  embed-server        # name from sprig.yaml.process.binary
lib/                  # optional: shared libraries co-located with binary
share/                # optional: model files, vocab, weights
LICENSE               # required: artifact license (typically AGPL-3.0)
NOTICE                # optional: third-party notices
```

Publishing:

```bash
oras push ghcr.io/sage-is/sprig-embedding-e5-large:v1.0-linux-amd64-cpu \
  --artifact-type application/vnd.sage-is.sprig.v1 \
  sage-is-sprig-embedding-e5-large-v1.0-linux-amd64-cpu.tar.zst:application/vnd.sage-is.sprig.tar+zstd
```

Sigstore signing:

```bash
cosign sign ghcr.io/sage-is/sprig-embedding-e5-large:v1.0-linux-amd64-cpu
```

The rootstock MUST verify the sigstore signature before extracting. A signature failure aborts the graft and emits a structured error to `/api/v1/diagnostics/health`.

Each Sprig™ artifact SHOULD be reproducible: same source + same inputs produce a byte-identical tar.zst. Reproducibility lets the rootstock's `binary_sha256` field guard against substitution.

## Delivery shapes

A Sprig™ can reach an operator in two ways. The wire contract (HTTP transport, OpenAI-compatible endpoints, error shape, conformance requirements) is the same in both cases. What differs is who runs the binary and who owns its lifecycle.

- **`oci-artifact`** — the publisher ships a tar.zst on GHCR. The operator's rootstock pulls, verifies, extracts, and supervises the binary as a local child process. Lifecycle is the rootstock's responsibility. This is the default delivery in v1.
- **`service-endpoint`** — the publisher ships a managed HTTPS endpoint. The operator points the rootstock at it with an auth token. The rootstock health-polls but does not supervise. Lifecycle is the publisher's responsibility.
- **`both`** — the publisher ships both. The operator chooses per deployment based on cost, latency, compliance, or trust posture.

An `oci-artifact` Sprig™ on a beefy single host fits a private deployment with sensitive data. A `service-endpoint` Sprig™ fits a fleet of light rootstocks sharing one expensive capability — workshops where a teacher's GPU box serves a room of laptops, compliance deployments where data is pinned to a specific host, or managed-API capabilities (ElevenLabs, OpenAI, Stability) that don't ship binaries at all. The `both` shape lets a publisher cover all of these without forcing an early choice, and lets an operator switch as their deployment grows.

A Sprig™ declares its delivery shape in `sprig.yaml`. The fields required for each shape are spelled out in the manifest schema below.

## The Sprig Manifest™ (sprig.yaml)

Every Sprig™ artifact MUST include `sprig.yaml` at the tar root. Schema:

```yaml
spec_version: v1                                    # required
delivery: oci-artifact                               # required: oci-artifact | service-endpoint | both
capability: embedding                                # required: see Reserved capability prefixes
cultivar: e5-large                                   # required (omit for capability-only Sprigs™)
variety: linux-amd64-cpu                             # required for oci-artifact/both; omitted for service-endpoint
sprig_version: v1.0.0                                # required: SemVer of THIS artifact
binary_sha256: 9a4f3e...                             # required for oci-artifact/both: sha256 of bin/<process.binary>
license: AGPL-3.0                                    # required: SPDX identifier

transport: http                                       # required: v1 accepts "http" or "none"; future v1.1+ adds "shmem" first, then unix_socket/stdio/signal

process:                                              # required for oci-artifact/both
  binary: embed-server                                # required: filename in bin/
  args: ["--port", "${PORT}", "--model-dir", "${SHARE_DIR}/e5-large"]
                                                      # required: argv after binary. Env interpolation supported.
  env:                                                # optional: env vars to set
    LOG_LEVEL: info
  working_dir: ${SPRIG_ROOT}                          # optional: defaults to artifact root
  ready_timeout_s: 60                                 # optional: max time from start to first /health 200; default 60
  shutdown_grace_s: 10                                # optional: SIGTERM-to-SIGKILL window; default 10

service:                                              # required for service-endpoint/both
  # Use endpoint_url for the single-variety shortcut.
  endpoint_url: https://embedding.example.com         # required when varieties: is absent. TLS only; HTTP refused.
  # OR use varieties[] to advertise multiple regions/tiers under the same Sprig™ name.
  # When varieties: is present, the rootstock ignores endpoint_url at the top level.
  varieties:                                          # optional: multi-variety publishers
    - name: hosted-us-east                            # required: must start with "hosted-" for service-endpoint
      endpoint_url: https://us.embedding.example.com  # required per variety
      default: true                                   # optional: at most one variety can be default
    - name: hosted-eu-west
      endpoint_url: https://eu.embedding.example.com
    - name: hosted-asia-pacific
      endpoint_url: https://asia.embedding.example.com
  auth:                                               # required when the endpoint authenticates
    type: bearer                                      # bearer | none
    env_var: SAGE_IS_SPRIG_EMBEDDING_TOKEN            # required when type=bearer: operator supplies via env
  inspect_path: /sage-is/v1/inspect                   # optional: default /sage-is/v1/inspect
  inspect_interval_s: 300                             # optional: how often to re-probe spec_version; default 300

http:                                                 # required when transport == "http"
  health_path: /health                                # optional: default /health
  endpoints:                                          # required: capability endpoints
    - method: POST
      path: /v1/embeddings
      shape: openai/v1/embeddings                     # see Transport: HTTP
    - method: POST
      path: /sage-is/v1/inspect                       # optional: see Transport: HTTP
      shape: sage-is/v1/inspect

description: |                                        # optional: free text shown in Sprig Catalog™
  e5-large embedding model. 1024-dim vectors.
  Runs CPU-only; pin SHARE_DIR for offline use.

resources:                                            # optional: advisory hints for catalog UI
  ram_mb: 2048
  disk_mb: 2200
  startup_seconds: 15

requires:                                             # optional: rootstock features the Sprig™ depends on
  - bonsai_version: ">=2.4.0"
  - oras_version: ">=1.1"
```

A compact `delivery: service-endpoint` example (a managed-API capability, no binary, no extraction):

```yaml
spec_version: v1
delivery: service-endpoint
capability: tts
cultivar: elevenlabs-managed
sprig_version: v1.0.0
license: proprietary

transport: http

service:
  endpoint_url: https://api.elevenlabs.io
  auth:
    type: bearer
    env_var: ELEVENLABS_API_KEY
  inspect_path: /sage-is/v1/inspect
  inspect_interval_s: 600

http:
  health_path: /v1/user
  endpoints:
    - method: POST
      path: /v1/text-to-speech/{voice_id}
      shape: openai/v1/audio/speech

description: |
  ElevenLabs hosted TTS. The rootstock health-polls the user endpoint; the operator
  supplies their ElevenLabs API key as ELEVENLABS_API_KEY.
```

Interpolation tokens valid in `process.args`, `process.env`, `process.working_dir`:

- `${PORT}` — port the rootstock assigned (loopback only).
- `${SPRIG_ROOT}` — extraction directory: `data/sage-is/sprigs/<artifact-name>/`.
- `${SHARE_DIR}` — `${SPRIG_ROOT}/share/`.
- `${LIB_DIR}` — `${SPRIG_ROOT}/lib/`.
- `${BIN_DIR}` — `${SPRIG_ROOT}/bin/`.

Unknown tokens MUST cause the rootstock to refuse the graft with a structured error.

## Variety selection

For `delivery: oci-artifact`, variety is a property of the artifact: the operator picks the artifact whose variety matches their host. No selection logic is needed beyond "use the pinned variety."

For `delivery: service-endpoint`, variety describes a runtime topology and a publisher may advertise more than one. The selection rules below cover both shapes:

- **Single-variety publisher.** Manifest declares `service.endpoint_url` (no `service.varieties:` block) or a `service.varieties:` array with exactly one entry. The operator MAY omit the variety pin in `distribution.env`. The rootstock uses the only advertised variety.
- **Multi-variety publisher.** Manifest declares `service.varieties:` with two or more entries. The operator MUST set `SAGE_IS_SPRIG_<NAME>_VARIETY=<value>` in `distribution.env`. If the pin is missing or empty, the rootstock refuses the graft with structured error `variety_pin_required` listing the advertised variety names.

The variety pin value MUST be one of:

- **A literal advertised variety name** — e.g. `hosted-us-east`. The rootstock dispatches to that variety's `endpoint_url`. Refuses with `variety_unknown` if the literal does not match an advertised variety.
- **`default`** — the rootstock dispatches to the variety the publisher marked `default: true`. Refuses with `variety_no_default` if the manifest declares no default and the pin is `default`.
- **`auto`** — the rootstock runs `GET /health` against every advertised variety's endpoint at graft time, measures the round-trip time, and dispatches to the variety with the lowest RTT. Refuses with `variety_auto_no_probes` if every probe fails. The selected variety is recorded in `state.json` and the diagnostics row surfaces both the selected variety and the measured RTT for transparency.

`auto` and `default` are reserved tokens — publishers MUST NOT use them as advertised variety names. A manifest that declares a variety literally named `auto` or `default` is malformed; rootstocks refuse with `variety_reserved_name`.

The rootstock re-evaluates `auto` selection only at graft time. Topgrafting a Sprig™ from one variety to another is the explicit way to switch regions or tiers mid-deployment; the rootstock does not silently re-route an `auto`-selected graft when a different variety becomes faster.

## Transport: HTTP (v1 baseline)

A Grafted Sprig™ exposes its endpoints over HTTP. How the rootstock reaches them depends on the delivery shape declared in the Sprig Manifest™:

- For `delivery: oci-artifact` Sprigs™, the binary listens on a loopback port the rootstock assigned. The rootstock MUST NOT expose this port externally; all traffic between rootstock and Sprig™ stays inside the container.
- For `delivery: service-endpoint` Sprigs™, the rootstock dispatches over TLS to the URL declared in `service.endpoint_url`. The endpoint is external by design; the publisher is responsible for hosting, TLS termination, and origin-side rate limiting.

The wire contract that follows (required endpoints, response codes, error shape) applies to both shapes unchanged.

### Required endpoints

**`GET /health`** — liveness + readiness in one call. The rootstock polls on a 5s interval after `process.ready_timeout_s` elapses.

```http
GET /health HTTP/1.1
Host: 127.0.0.1:9001

HTTP/1.1 200 OK
Content-Type: application/json

{"status": "ok", "cultivar": "e5-large", "spec_version": "v1"}
```

Response codes:

- `200` — ready. `status` MUST be `"ok"`.
- `503` — temporarily unavailable (model loading, etc). The rootstock retries.
- Any other code — Wilted. Supervisor begins restart-with-backoff.

**Capability endpoint(s)** — declared in `sprig.yaml.http.endpoints`. Shape MUST follow the `shape:` field:

- `openai/v1/embeddings` — body matches `POST /v1/embeddings`; response is OpenAI's `Embedding` object.
- `openai/v1/audio/transcriptions` — body matches `POST /v1/audio/transcriptions`; response is OpenAI's `Transcription` object.
- `openai/v1/audio/speech` — body matches `POST /v1/audio/speech`; response is the audio binary.
- `openai/v1/images/generations` — body matches `POST /v1/images/generations`; response is OpenAI's `ImagesResponse` object.
- `sage-is/v1/<name>` — a capability OpenAI's spec does not cover. Schema is published at `github.com/sage-is/sprig-spec/schemas/sage-is/v1/<name>.json`.

### Optional endpoint

**`POST /sage-is/v1/inspect`** — returns Sprig™ metadata for the diagnostics page. Reuses the `sprig.yaml` shape with runtime fields appended (`pid`, `uptime_s`, `served_requests`).

### Error shape

All endpoints MUST return errors in OpenAI's shape with a `sage_is` extension:

```json
{
  "error": {
    "message": "human-readable summary",
    "type": "invalid_request_error",
    "code": "missing_field",
    "sage_is": {
      "capability": "embedding",
      "cultivar": "e5-large",
      "spec_version": "v1"
    }
  }
}
```

## Transport: none (v1)

The `none` transport ships fire-and-forget Sprigs™ that complete a single operation and exit. Build tooling is the canonical use case — `sprig-build-svelte` runs `vite build`, writes artifacts into its extraction directory, and exits with code 0. There is no service for the Rootstock™ to dispatch to. The exit code is the health signal.

### Lifecycle

A `delivery: oci-artifact` Sprig™ declaring `transport: none` runs once per graft. The Rootstock™ launches it as a child process under the supervisor, waits for it to exit within `process.ready_timeout_s`, treats the exit code as health, and consumes artifacts from the declared output directory before transitioning to Grafted.

States used:

- **Sprouted** → known, not yet executed
- **Grafting** → process running
- **Grafted** → process exited with code 0; artifacts available in the output directory
- **Wilted** → process exited with non-zero code, OR exceeded `process.ready_timeout_s` without exiting, OR exited with code 0 but produced no artifacts when `expect_artifacts: true`
- **Dormant** and **Pruned** apply as for other transports

Revive on a Wilted `none` Sprig™ re-runs the process from scratch.

### Manifest schema for `transport: none`

```yaml
transport: none
process:
  binary: vite                                       # required: filename in bin/
  args: ["build", "--outDir", "${SPRIG_ROOT}/output"]
  output_dir: ${SPRIG_ROOT}/output                   # optional: where the Sprig™ writes artifacts; default ${SPRIG_ROOT}/output
  ready_timeout_s: 300                               # required for transport: none — maximum wall-clock for the operation
  shutdown_grace_s: 10                               # optional: SIGTERM-to-SIGKILL window if the operator prunes mid-build
  expect_artifacts: true                             # optional, default true: Rootstock™ refuses Grafted unless output_dir contains at least one file
```

The `http:` block is not declared (the `none` transport carries no HTTP endpoints).

### Artifact propagation

After a successful exit, the Rootstock™ consumes the artifacts from `output_dir`. The consumption is per-capability:

- `build-` Sprigs™ (e.g., `sprig-build-svelte`) — the Rootstock™ replaces its static-asset surface with the produced artifacts. The reference implementation copies or symlinks the contents into the directory it serves.
- Future one-shot capabilities (warmup, pre-fetchers, schema migrators) — consumption is per-capability and out of scope for v1.

### Required behavior

A `transport: none` Sprig™ MUST:

- Write structured logs to stderr.
- Exit with code 0 on success and non-zero on failure.
- Write any produced artifacts to `output_dir` before exiting with code 0.
- Honor `SIGTERM` if the operator prunes mid-operation; exit within `process.shutdown_grace_s`.
- Not bind any network port. The supervisor allocates no `${PORT}` for `transport: none` Sprigs™.

### Error classes

- `sprig_build_exit_nonzero` — process exited with non-zero status; the diagnostics row carries the exit code in `error.code`
- `sprig_build_timeout` — process exceeded `process.ready_timeout_s` without exiting
- `sprig_build_no_artifacts` — process exited with code 0 but `output_dir` is empty when `expect_artifacts: true`

## Future transports (deferred to v1.1+)

v1 specifies `http` (loopback + TLS via the delivery shapes) and `none` (one-shot, exit-code health). The Sprig Manifest™ schema reserves these additional transport tokens for later spec versions. A v1 rootstock refuses any Sprig™ declaring one of them with the structured error class `transport_not_yet_implemented`.

- **`shmem`** — shared-memory transport for high-throughput data Sprigs™ where HTTP's per-message syscall + kernel-buffer copy is the bottleneck (large embedding batches, image generation, tokenization of multi-MB documents). **Ships in v1.1.** Contract sketch below.
- **`unix_socket`** — high-throughput local Sprigs™ that do not need a port (some tokenizers, sandboxed code-runners). Same JSON-RPC-shaped messages as HTTP; socket path declared in `sprig.yaml`.
- **`stdio`** — line-delimited JSON over stdin/stdout with LSP-style frame headers. Useful for stateful per-request workers where keeping a process warm matters.
- **`signal`** — binary runs and stays alive (cloudflared, tailscaled, rclone-mount). Health is `os.kill(pid, 0)` plus an optional sidecar health-check command.

Each future transport gets its own full section in the spec at the spec version that adds it.

### `shmem` contract sketch (ships in v1.1)

Shared memory exists to avoid HTTP's per-message kernel-buffer copy and syscall overhead for high-throughput data flows. Both the Rootstock™ and the Sprig™ map the same physical RAM via POSIX `shm_open` + `mmap` (Linux), so transferring a 4 MB embedding tensor is a pointer hand-off rather than a copy. PyTorch's `torch.Tensor.share_memory_()` and NVIDIA Triton's `shared_memory` mode use exactly this pattern; the spec adopts the same shape so existing ML codebases can wrap with minimal friction.

The transport carries two channels:

- **Control channel** — small wakeup messages via `eventfd` (Linux) or a unix socket declared at `shmem.control_path` in `sprig.yaml`. Carries "process this batch" and "result ready" notifications, on the order of bytes per message. Same JSON shape as `stdio` will use.
- **Data channel** — pre-allocated shared region declared at `shmem.region_size_mb` (e.g. `512` for image generation, `64` for embedding batches). The Rootstock™ creates the region via POSIX `shm_open` + `mmap` and passes its name to the Sprig™ as the `${SHM_NAME}` interpolation token in `process.args` and `process.env`.

Manifest sketch (the v1.1 spec ships the full schema):

```yaml
transport: shmem
shmem:
  control_path: ${SPRIG_ROOT}/control.sock          # required: eventfd or unix socket for wakeup messages
  region_size_mb: 512                                # required: size of the shared region the Rootstock™ allocates
  region_name_template: sage-is.sprig.${SPRIG_NAME}.${PID}   # optional: default pattern shown
```

Lifecycle:

1. **Graft** — Rootstock™ creates the shared region, binds the control channel, passes `${SHM_NAME}` to the Sprig™ via env interpolation.
2. Both processes `mmap` the same region. The Sprig™ signals readiness over the control channel as its `/health` equivalent.
3. **Request flow** — Rootstock™ writes a request payload into the shared region, sends a wakeup on the control channel, waits for the response wakeup, reads the response from the shared region.
4. **Prune** — Rootstock™ closes the control channel, unmaps and `shm_unlink`s the region.
5. **Orphan cleanup** — on Rootstock™ lifespan startup, the supervisor enumerates `/dev/shm` for names matching `sage-is.sprig.*` and `shm_unlink`s any that belong to Sprigs™ no longer in `state.json`.

Error classes the v1.1 spec will define:

- `sprig_shmem_control_lost` — control-channel silence beyond `process.ready_timeout_s` (Wilted)
- `sprig_shmem_protocol_error` — Sprig™ writes a malformed message frame on the control channel (Wilted)
- `sprig_shmem_region_size_mismatch` — region size declared in the manifest does not match the actual `mmap`'d size (graft refuses)

The first reference shmem Sprig™ in v1.1 will be `sage-is/sprig-embedding-batch-shmem` — batched embedding is the highest-volume throughput case in workshop and production deployments alike.

## Process lifecycle

This section applies to `delivery: oci-artifact` Sprigs™ only. For `delivery: service-endpoint` Sprigs™ the publisher runs the binary on their own infrastructure, so this contract is for them to honor, not for the rootstock to enforce.

The rootstock supervises every Grafted local Sprig™ as a child process under `tini` as PID 1.

### Startup

1. The rootstock allocates a loopback port (typically in 9001-9999 range; loopback-only bind).
2. It writes the port into `${PORT}` and interpolates `process.args`.
3. It launches the binary as a child of the rootstock's supervisor.
4. It polls `GET /health` every 500ms up to `process.ready_timeout_s`. First `200 OK` with `status: "ok"` transitions to `grafted`.
5. If timeout elapses before `200`, the Sprig™ enters `wilted`. The supervisor restarts with exponential backoff (1s, 2s, 4s, 8s, 16s, 30s ceiling). 5 consecutive failures pause automatic restart attempts; the row stays Wilted; the operator clicks Revive to retry.

### Shutdown

1. The rootstock sends `SIGTERM` to the child.
2. The child SHOULD finish in-flight requests, close listeners, and exit within `process.shutdown_grace_s`.
3. If the grace window expires, the rootstock sends `SIGKILL`.

### Logging

A Sprig™ MUST write structured logs to stderr. JSON per line is RECOMMENDED. stdout is reserved for transport (when `transport == "stdio"`); for HTTP transport, stdout output is captured but not parsed.

A Sprig™ MUST NOT fork-and-exit (daemonize). The supervisor expects the binary it launched to be the long-lived process.

## Spec versioning

Every Sprig™ artifact declares `spec_version` in `sprig.yaml`. The rootstock declares the highest `spec_version` it can honor.

Rules:

- Rootstock with spec support `vN` MUST honor Sprigs™ with `spec_version` in `[v1, vN]`.
- Rootstock MUST refuse a Sprig™ with `spec_version > vN`. Error: `sprig_spec_too_new`.
- Within a single `spec_version`, additions are backward-compatible. Breaking changes bump the version.
- A Sprig™ author MAY declare the lowest `spec_version` it supports if it intentionally avoids later-version features.

v1 covers HTTP transport only. v2 will add `unix_socket` and `stdio`. v3 will add `signal` and `none`. Each later version preserves v1's HTTP semantics unchanged.

## Conformance

Requirements split by delivery shape and by transport. A `delivery: both` Sprig™ satisfies all requirements from both delivery sections. A `transport: none` Sprig™ satisfies the subset below (and skips the HTTP-shape MUSTs since it has no service surface).

### `delivery: oci-artifact` (`transport: http`)

A conforming Sprig™ MUST:

1. Include a valid `sprig.yaml` at the tar root.
2. Include the binary at `bin/<process.binary>` with sha256 matching `binary_sha256`.
3. Bind to the loopback address on `${PORT}` when launched with the interpolated `process.args`.
4. Respond to `GET /health` with `200 OK` and `{"status": "ok", ...}` within `process.ready_timeout_s` of process start.
5. Implement every endpoint declared in `sprig.yaml.http.endpoints` per its `shape:`.
6. Return errors in the OpenAI-compatible `error` shape with the `sage_is` extension.
7. Honor `SIGTERM` by shutting down within `process.shutdown_grace_s`.
8. Write logs to stderr (not stdout).
9. Be sigstore-signed under `cosign verify` against the publisher's identity.

A conforming Sprig™ SHOULD:

1. Be reproducible: same source + same inputs produce a byte-identical tar.zst.
2. Expose `POST /sage-is/v1/inspect` for diagnostics.
3. Declare advisory `resources:` hints in the manifest.
4. Include a LICENSE file at the tar root.

### `transport: none` (typically with `delivery: oci-artifact`)

A conforming `transport: none` Sprig™ MUST:

1. Include a valid `sprig.yaml` at the tar root with `transport: none`.
2. Include the binary at `bin/<process.binary>` with sha256 matching `binary_sha256`.
3. Exit with code 0 on success and non-zero on failure.
4. Write any produced artifacts to `process.output_dir` (default `${SPRIG_ROOT}/output`) before exiting with code 0.
5. Honor `SIGTERM` if the operator prunes mid-operation; exit within `process.shutdown_grace_s`.
6. Write structured logs to stderr (not stdout).
7. Not bind any network port. The supervisor allocates no `${PORT}` for `transport: none` Sprigs™.
8. Be sigstore-signed under `cosign verify` against the publisher's identity.

A conforming `transport: none` Sprig™ SHOULD:

1. Be reproducible: same source + same inputs produce a byte-identical artifact set in the output directory.
2. Emit a final summary line on stderr naming each artifact written (path + size). The Rootstock™ uses this for its post-graft confirmation log.
3. Declare advisory `resources:` hints in the manifest (RAM, disk for intermediate state, expected wall-clock).
4. Include a LICENSE file at the tar root.

### `delivery: service-endpoint`

A conforming Sprig™ MUST:

1. Publish a valid `sprig.yaml` at `${service.endpoint_url}${service.inspect_path}` (default `/sage-is/v1/inspect`).
2. Serve only over HTTPS. Plain HTTP is refused by the rootstock at graft time.
3. Honor the auth shape declared in `sprig.yaml.service.auth`. For `type: bearer`, accept a Bearer token in the `Authorization` header.
4. Respond to `GET ${endpoint_url}${health_path}` with `200 OK` and `{"status": "ok", ...}` when ready to serve.
5. Implement every endpoint declared in `sprig.yaml.http.endpoints` per its `shape:`.
6. Return errors in the OpenAI-compatible `error` shape with the `sage_is` extension.
7. Sign the manifest content served at `/sage-is/v1/inspect` with sigstore (detached signature available at `${inspect_path}.sig` or via the publisher's well-known URL) so the rootstock can verify provenance without pulling an artifact.
8. Return the same `spec_version` and capability set on every `/inspect` call; a mid-flight change triggers Wilted on the rootstock side.

A conforming Sprig™ SHOULD:

1. Declare advisory `resources:` hints in the manifest so the catalog UI can warn the operator about cost/latency.
2. Publish a status page or uptime endpoint the rootstock can surface alongside its own diagnostics.
3. Document the operator's responsibility for the auth token (rotation cadence, scope, where to obtain it).

The conformance test suite lives at `github.com/sage-is/sprig-spec/conformance/`. Run against a built artifact:

```bash
sprig-conformance check sage-is-sprig-<name>-<cultivar>-v<version>-<variety>.tar.zst
```

The test produces a JSON report with PASS/FAIL per requirement.

## Reference Sprigs™

The following Sprigs™ are the canonical worked examples. Each repo includes a build pipeline, a Sprig™ binary, the manifest, the mock variant, and conformance test fixtures.

- **`github.com/sage-is/sprig-embedding`** — text embedding via OpenAI's `/v1/embeddings` shape. Cultivars: `e5-large`, `bge-large-en`. Mock variant `sprig-embedding-mock` returns deterministic vectors derived from a hash of the input — useful for smoke tests where reproducibility matters more than semantic correctness.
- **`github.com/sage-is/sprig-whisper`** — speech transcription via OpenAI's `/v1/audio/transcriptions` shape. Cultivars: `tiny`, `base`, `small`, `medium`. Mock variant `sprig-whisper-mock` returns canned transcripts.

Read the manifests in either repo as a copy-able starting point for new Sprigs™.

## Changelog

- **v1 (draft)** — initial publication. Transports: `http` (loopback for oci-artifact, TLS for service-endpoint) and `none` (one-shot fire-and-forget, exit-code health, for build tooling). OpenAI-compatible + sage-is/v1 extension namespace. Sprouted / Grafting / Grafted / Dormant / Wilted / Pruned lifecycle. Two delivery shapes: `oci-artifact` (tar.zst over OCI Artifacts, sigstore-signed, locally supervised) and `service-endpoint` (managed HTTPS endpoint, bearer auth via env var, manifest sigstore-signed, probe-monitored). `both` shape lets a publisher ship the same Sprig™ as either at the operator's choice. Variety values carry platform descriptors for `oci-artifact` (`linux-<arch>-<accel>`) and runtime topology descriptors for `service-endpoint` (`hosted-<descriptor>`). Multi-variety publishers can advertise regions or performance tiers under one capability name; operators pin a literal variety, `default`, or `auto` (latency-based selection at graft time). Reserved capability prefixes cover ML (`embedding-`, `whisper-`, `tts-`, `imagegen-`, `parse-`, `ocr-`, `tokenize-`, `diarize-`, `rag-`), infrastructure (`tunnel-`, `monitor-`, `backup-`, `fetcher-`), and dev/build tooling (`dev-`, `build-`). License compatibility: Sprig™ authors choose any license freely; AGPL of the Rootstock™ does not propagate across the published Sprig Spec™ contract (arms-length process boundary).
- **v1.1 (planned)** — `shmem` transport ships with first reference Sprig™ `sage-is/sprig-embedding-batch-shmem`. Contract sketch present in v1 Future transports for forward visibility.
