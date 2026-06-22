# Rootstock Spec™ v1 (draft)

> **Status:** Draft. Sibling to [Sprig Spec™ v1](sprig-spec-v1-draft.md). Review, edit, then move to the canonical home at `github.com/sage-is/rootstock-spec`.

This document is the contract a Bonsai™ rootstock implementation honors so it can host conforming Sprigs™. If the Sprig Spec™ tells Sprig™ authors what to build, this tells rootstock implementers what to support. Together the two specs define the Graft Union™.

The reference implementation is `github.com/sage-is/AI-UI`. Third-party rootstocks are welcome; they need to satisfy the requirements below.

## Scope of v1

- HTTP transport (loopback for `delivery: oci-artifact`; TLS over the public network for `delivery: service-endpoint`)
- Both delivery shapes from the Sprig Spec™: `oci-artifact` (pull + supervise locally) and `service-endpoint` (point at a managed HTTPS endpoint with bearer auth)
- Pull, verify, extract, launch, supervise, and dispatch for `oci-artifact`
- Probe, verify, and dispatch (no process supervision) for `service-endpoint`
- Sprig Catalog™ surfacing in an operator UI
- Diagnostics surface keyed by capability
- Graft API endpoints for operator-driven graft / prune / topgraft / revive
- Sigstore verification — on the pulled tar.zst for `oci-artifact`; on the `/sage-is/v1/inspect` manifest for `service-endpoint`
- Sha256 verification of the extracted binary for `oci-artifact`
- Spec-version negotiation between rootstock and Sprig™
- Migration from legacy install paths (rootstocks that previously baked ML capabilities into a fat image)

Out of scope for v1: non-HTTP transports (`unix_socket`, `stdio`, `signal`, `none`), Sprig-to-Sprig direct communication, distributed multi-host supervision of `oci-artifact` Sprigs™ (one rootstock owns one local Sprig™), federated identity at the Sprig™ Hub level.

## Vocabulary

This spec uses the same vocabulary as the Sprig Spec™. The terms most relevant here:

- **Rootstock** — the implementation honoring this spec. The Bonsai™ image.
- **Sprig™** — the unit of capability the rootstock grafts. Can be local (`delivery: oci-artifact`) or remote (`delivery: service-endpoint`).
- **Local Sprig™** — a Sprig™ delivered as a tar.zst the rootstock pulls and runs as a child process under its supervisor. Loopback transport.
- **Remote Sprig™** — a Sprig™ delivered as a managed HTTPS endpoint the rootstock probes and dispatches to. The publisher owns the binary's lifecycle; the rootstock owns the trust and visibility layer.
- **Sprig Catalog™** — the rootstock's view of what Sprigs™ are sprouted, grafted, dormant, wilted, or pruned across both delivery shapes.
- **Sprig Manifest™** — declarative pins in `distribution.env` (or rootstock-equivalent) that name which Sprigs™ the operator wants available. The pin shape differs by delivery; see [Configuration](#configuration).
- **Graft Union™** — the boundary between rootstock and Sprig™. HTTP-based in v1: loopback for local Sprigs™, TLS over the public network for remote Sprigs™.
- **Wilted Sprig™** — a Sprig™ that was grafted and has stopped answering. For local Sprigs™ the artifact stays on disk; for remote Sprigs™ the signed manifest stays in `state.json`. In both cases the rootstock keeps enough state for the operator to click Revive without re-grafting from scratch.

See the Sprig Spec™ for the full vocabulary list.

## License compatibility

The Sage.is Rootstock™ reference implementation (`github.com/sage-is/AI-UI`) is licensed AGPL-3.0. This section clarifies what that means for operators running the Rootstock™, for Sprig™ authors building against it, and for third parties implementing their own conforming rootstock.

### Operators running an unmodified Rootstock™

No AGPL obligation is triggered by grafting Sprigs™ of any license. The Rootstock™ binary stays unmodified; the Sprigs™ are arms-length artifacts communicating via the published Sprig Spec™ contract. Run any mix of proprietary, MIT, Apache-2.0, BSD, GPL, AGPL, or any other Sprigs™ without legal exposure. The mix of licenses inside an operator's catalog is the operator's choice.

### Operators modifying the Rootstock™

AGPL-3.0 Section 13 fires for the Rootstock™ modifications only. The modified Rootstock™ source must be offered to remote users who interact with the modified version. Grafted Sprigs™ are NOT part of the Rootstock™ for this purpose — they sit on the other side of an arms-length process boundary (HTTP over loopback, HTTPS over the public network, or the `none` transport's exit-code contract) and remain unaffected by the operator's Rootstock™ modifications. An operator who modifies the Rootstock™ AND grafts a proprietary Sprig™ owes source for the Rootstock™ modifications; they owe nothing for the Sprig™.

### Sprig™ authors

A Sprig™ is not a derivative work of the Rootstock™ when it communicates via the published Sprig Spec™ contract. Sprig™ authors choose their license freely. The reference Sprigs™ (`sage-is/sprig-embedding`, `sage-is/sprig-whisper`, `sage-is/sprig-dev-svelte`, `sage-is/sprig-build-svelte`) ship under AGPL-3.0 because that is Sage.is's own choice for those artifacts, not because the Spec requires it.

### Third-party rootstock implementations

Anyone may implement the Rootstock Spec™ in any language under any license. The spec itself is implementation-language-agnostic and license-agnostic for conforming rootstocks. A conforming proprietary rootstock can graft AGPL Sprigs™ without inheriting their license, and an AGPL rootstock implementation (the Sage.is reference, or anyone else's) can graft proprietary Sprigs™ without imposing AGPL on them.

This follows the FSF's standard interpretation of inter-process communication via published interfaces — aggregation rather than combined work. Proprietary userspace on a GPL'd Linux kernel and a closed-source database client talking to a GPL'd database server over a socket are the canonical examples.

## Rootstock responsibilities

A conforming rootstock owns six things end-to-end:

1. **Catalog** — read the Sprig Manifest™; expose what's available, what's grafted, and what's wilted.
2. **Pull** — fetch the tar.zst artifact from the Sprig Store™ using `oras` (or an equivalent OCI Artifact client).
3. **Verify** — confirm the sigstore signature and the manifest's `binary_sha256` against the extracted file.
4. **Supervise** — launch the binary under a process supervisor that restarts on crash, backs off on repeated failure, and persists state across rootstock restarts.
5. **Dispatch** — route inbound requests to the right Grafted Sprig™ using the existing engine/URL config so that no per-capability dispatch code needs to change when a new Sprig™ is added.
6. **Surface** — expose status, errors, and operator actions through a Graft API and a diagnostics page.

Each is specified in the sections below.

## Sprig Catalog™

The catalog is the rootstock's source of truth about what Sprigs™ exist, what state each is in, and what the operator can do next.

The catalog reads from two places:

- **Sprig Manifest™** — declarative pins in `distribution.env` (or the equivalent config file the rootstock uses). The pin shape differs by delivery: `oci-artifact` pins carry a repo tag and per-variety SHA256s; `service-endpoint` pins carry the endpoint URL, the env var name for the auth token, and an optional `inspect_interval_s` override. See [Configuration](#configuration).
- **Local runtime state** — `data/sage-is/sprigs/state.json` records the per-Sprig™ lifecycle state. For `oci-artifact` Sprigs™ this includes extraction paths and PIDs. For `service-endpoint` Sprigs™ it records the last `/inspect` response, the last health probe outcome, and the consecutive-failure count for backoff.

A v1 catalog MUST surface every Sprig™ in either source regardless of delivery shape. A Sprig™ in the manifest but never grafted appears as **Sprouted**. A Sprig™ in `state.json` but missing from the manifest appears as **Pruned** (with a note that the operator should re-add to the manifest or run prune to clean up).

The catalog MUST be queryable via `GET /api/v1/retrieval/sprigs` (see Graft API below). The catalog MAY also drive a Wizard UI mode picker so first-run operators can select Sprigs™ before Rootstock startup completes.

## Graft pipeline

Grafting moves a Sprig™ from Sprouted → Grafting → Grafted (or back to Dormant on failure). The pipeline forks by delivery shape. Both forks update `data/sage-is/sprigs/state.json` at every step so a rootstock restart can resume cleanly.

### For `delivery: oci-artifact`

1. **Reserve a port.** The rootstock picks an unused loopback port (typical range 9001-9999, configurable). Loopback only; the port MUST NOT be exposed externally.
2. **Pull.** `oras pull ghcr.io/sage-is/sprig-<name>:<tag>` into a staging directory under `data/sage-is/sprigs/<name>/.staging/`. If the pull fails, the Sprig™ stays Sprouted and the failure lands in the diagnostics registry.
3. **Verify signature.** `cosign verify` against the publisher identity declared in `distribution.env`. A signature failure aborts the graft, deletes the staging directory, and emits a structured error. The rootstock MUST refuse to extract an unsigned or wrong-signer artifact.
4. **Extract.** Decompress the tar.zst into `data/sage-is/sprigs/<name>/` atomically (write to `.staging/`, then rename). Atomic rename guards against half-extracted Sprigs™ after a power loss.
5. **Verify binary checksum.** Compute sha256 of `bin/<process.binary>` and compare against the manifest's `binary_sha256`. Mismatch aborts the graft.
6. **Interpolate process args.** Substitute `${PORT}`, `${SPRIG_ROOT}`, `${SHARE_DIR}`, `${LIB_DIR}`, `${BIN_DIR}` in `process.args`, `process.env`, and `process.working_dir`. Unknown tokens cause the graft to refuse with a structured error.
7. **Launch.** Spawn the binary as a child of the rootstock's supervisor (see Supervisor below). State transitions to Grafting.
8. **Poll readiness.** Hit `GET /health` every 500ms up to `process.ready_timeout_s`. First `200 OK` with `status: "ok"` transitions the row to Grafted and emits a structured success event. If timeout elapses, transition to Wilted and let the supervisor handle restart-with-backoff.

### For `delivery: service-endpoint`

No pull, no extract, no port reservation. Six steps:

1. **Fetch manifest.** `GET ${service.endpoint_url}${service.inspect_path}` (default `/sage-is/v1/inspect`). The response carries the Sprig™'s `sprig.yaml` as JSON. A non-200 response or TLS failure aborts the graft.
2. **Verify manifest signature.** Retrieve the detached sigstore signature (from `${inspect_path}.sig` or the publisher's well-known URL declared in `distribution.env`) and `cosign verify` against the publisher identity. Refuse on signature failure or wrong signer.
3. **Validate spec_version.** Confirm the rootstock supports the manifest's declared `spec_version`. Refuse with `sprig_spec_too_new` if the manifest asks for a newer spec than the rootstock can honor.
4. **Select variety.** If the manifest declares `service.varieties[]` with two or more entries, the rootstock applies the operator's `SAGE_IS_SPRIG_<NAME>_VARIETY` pin per the rules in the Sprig Spec™'s [Variety selection](sprig-spec-v1-draft.md#variety-selection) section: a literal variety name dispatches to that variety's `endpoint_url`; `default` dispatches to the variety marked `default: true`; `auto` runs a `GET /health` probe against every advertised variety (5-second timeout each, run concurrently) and selects the lowest-RTT variety. Refuses with `variety_pin_required`, `variety_unknown`, `variety_no_default`, or `variety_auto_no_probes` per the spec. If the manifest declares `service.endpoint_url` directly (no `varieties:`) or a single-entry `service.varieties:`, the rootstock uses that URL and skips selection. The chosen variety name and the URL it resolved to are persisted in `state.json`.
5. **Resolve auth token.** Read the env var named in `service.auth.env_var`. Refuse the graft if the env var is unset and `service.auth.type != none`. The token MUST NOT land in `state.json` or any API response.
6. **Probe health.** `GET <selected_endpoint_url>${health_path}` with the resolved auth header. Expect `200 OK` with `{"status": "ok", ...}` within a 10-second window. Success transitions to Grafted. Failure transitions to Wilted; the rootstock starts the probe-backoff cycle described in [Remote Sprig™ supervision](#remote-sprig-supervision).

## Supervisor

The supervisor is the per-Sprig™ process minder. The reference implementation uses asyncio subprocess management with `tini` as PID 1 of the rootstock container.

Requirements:

- **Restart-with-backoff.** On unexpected exit, restart after 1s. Double the delay on each consecutive failure: 1s, 2s, 4s, 8s, 16s, 30s ceiling. Reset the delay on a successful ready transition.
- **Failure ceiling.** After 5 consecutive failures within a single backoff cycle, pause automatic restart and leave the row in Wilted. The operator clicks Revive to retry. The ceiling exists so a broken Sprig™ does not keep restarting indefinitely and filling the log.
- **Graceful shutdown.** On graft removal or rootstock shutdown, send `SIGTERM`. Wait `process.shutdown_grace_s` (default 10s). If the binary has not exited, send `SIGKILL`.
- **Crash recovery.** On rootstock startup, the supervisor reads `state.json` and re-grafts every Sprig™ whose last state was Grafted. The operator does not have to remember which Sprigs™ were running before a container restart.
- **State persistence.** Every state transition writes `state.json` atomically (write tmp, rename). State persistence is best-effort; a write failure logs a warning but does not block the transition.
- **Logging.** The supervisor captures Sprig™ stderr (structured logs) and forwards to the rootstock's log stream tagged with the Sprig™ name. stdout is discarded for HTTP transport (reserved for `stdio` transport in later spec versions).

The supervisor MUST NOT exec arbitrary commands. The only binary it executes is `bin/<process.binary>` from a verified extraction.

## One-shot Sprig™ supervision (`transport: none`)

For `transport: none` Sprigs™ the supervisor's job is different. There is no service to keep alive; the Sprig™ runs once, exits, and the Rootstock™ consumes any artifacts it produced before transitioning the row to Grafted (or Wilted on failure). Build tooling like `sprig-build-svelte` is the canonical case.

The supervisor MUST:

- Launch the binary with the interpolated `process.args` and `${SPRIG_ROOT}` / `${OUTPUT_DIR}` env tokens. No `${PORT}` is allocated.
- Wait for the process to exit, bounded by `process.ready_timeout_s`. Exceeding the timeout transitions to Wilted with error class `sprig_build_timeout` after sending SIGTERM and then SIGKILL.
- Treat exit code 0 as success and any non-zero code as failure (Wilted with error class `sprig_build_exit_nonzero` and the exit code in `error.code`).
- When `process.expect_artifacts: true` (the default), refuse to transition to Grafted unless `process.output_dir` contains at least one file after a code-0 exit. The row transitions to Wilted with error class `sprig_build_no_artifacts`.
- Capture stderr into the rootstock log stream tagged with the Sprig™ name. Capture stdout but neither parse nor forward it (build tools may print artifact paths there).
- Send `SIGTERM` if the operator prunes mid-operation and wait `process.shutdown_grace_s` before `SIGKILL`.

The supervisor MUST NOT apply restart-with-backoff to `transport: none` Sprigs™. A failed one-shot stays Wilted until the operator clicks Revive, which re-runs the process from scratch. The "5 consecutive failures pauses automatic restart" ceiling does not apply because there is no automatic restart for one-shot Sprigs™.

### Artifact propagation

After a successful exit, the Rootstock™ consumes the artifacts from `process.output_dir` per the Sprig™'s capability prefix:

- **`build-` Sprigs™** — the Rootstock™ replaces its static-asset surface with the produced artifacts. The reference implementation copies or symlinks the contents into the directory it serves atomically (write a sibling directory, then `rename(2)` it into place) so an in-flight request does not see a torn surface.
- **Future one-shot capabilities** — consumption logic is per-capability and lands as those capabilities are defined.

The consumption operation runs within the lifespan of the graft. State transitions: `Sprouted → Grafting → (process running) → (process exits 0) → (artifact consumption) → Grafted`. A failure during consumption (e.g., the Rootstock™ cannot write into its static-asset directory) transitions to Wilted with error class `sprig_build_consumption_failed` and leaves the artifacts in `output_dir` for operator inspection.

### State persistence for one-shot Sprigs™

For each `transport: none` Sprig™ row in `state.json` the supervisor records:

- `last_exit_code` — the exit code of the most recent run
- `last_run_at` — timestamp the run completed (success or failure)
- `artifact_count` — number of files in `output_dir` after a successful run; null otherwise
- `consumed_at` — timestamp the Rootstock™ finished consuming artifacts (when consumption is per-capability defined)

### Unsupported transports

A Sprig™ that declares a transport other than `http` or `none` MUST be refused at graft time with the structured error class `transport_not_yet_implemented`. The error response names the declared transport and the spec version that will ship it (`shmem` lands in v1.1; `unix_socket`, `stdio`, and `signal` are deferred to a later v1.x). The Rootstock™ does not attempt to launch a Sprig™ with an unsupported transport.

## Remote Sprig™ supervision

For `delivery: service-endpoint` Sprigs™ the rootstock has no process to supervise. SIGTERM, SIGKILL, restart-with-backoff, and `state.json` recovery do not apply because somebody else owns the running binary. The rootstock's job here is narrower: probe the remote often enough to surface honest visibility into whether it is healthy and whether it still matches what was originally signed.

Two probes run on independent intervals:

- **Health probe.** `GET ${endpoint_url}${health_path}` with the resolved auth header. Default interval 30 seconds, configurable per Sprig™. A failure transitions to Wilted; consecutive failures back off using the same 1s → 30s ceiling curve as process supervision, but the unit being delayed is the next probe, not a restart. After 5 consecutive failures the rootstock pauses automatic probing and waits for the operator to click Revive.
- **Inspect probe.** `GET ${endpoint_url}${inspect_path}` with the auth header. Default interval `service.inspect_interval_s` (default 300 seconds). The response MUST match the `spec_version`, `capability`, and (when declared) `cultivar` from the originally-signed manifest. A drift transitions the row to Wilted with error class `sprig_inspect_drift` and the diagnostics row surfaces the diff so the operator can decide whether to Revive or Prune.

Revive on a remote Sprig™ resets the health-probe backoff counter and runs an immediate inspect probe. There is no restart attempt because there is no process.

On rootstock startup, the supervisor reads `state.json` and resumes probing for every previously-Grafted service-endpoint Sprig™. Operators do not have to re-graft remote Sprigs™ after a rootstock restart.

The rootstock SHOULD store the auth token resolution result in memory only. Persisting the token value to `state.json` is a violation of the "no secret material" rule in Security below. Re-resolve from the env var on every restart.

## Dispatch

The Sprig Spec™'s OpenAI-compatible shape exists so the rootstock does not need new dispatch code per capability. A v1 rootstock routes requests using whatever engine/URL config it already has.

Example for the embedding capability:

- The operator grafts `sprig-embedding-e5-large`. The rootstock launches it on `localhost:9001`.
- The rootstock writes `RAG_EMBEDDING_ENGINE=openai` and `RAG_OPENAI_API_BASE_URL=http://localhost:9001/v1` to the persisted config.
- An incoming embedding request hits the existing OpenAI dispatch path and routes to the grafted Sprig™ without any per-capability routing code being added.

The rootstock SHOULD wrap the dispatch in its standard endpoint-health helper (the AI-UI reference uses `with_endpoint_health(url, capability)`) so a Wilted Sprig™ produces the same structured `EndpointUnreachable → 503` response any external endpoint failure would.

Topgrafting (swapping a cultivar without a request gap) follows this sequence:

1. Pull, verify, extract, launch the new Sprig™ on a fresh port.
2. Poll `GET /health` until Grafted.
3. Atomically update the engine config URL to the new port.
4. Wait `topgraft_drain_s` (default 30s) for in-flight requests on the old port to finish.
5. SIGTERM the old Sprig™. Wait `process.shutdown_grace_s`. SIGKILL if needed.
6. Prune the old extraction directory.

A topgraft failure at step 1 or 2 leaves the old Sprig™ grafted. In-flight traffic keeps routing to the old port and the operator sees no interruption.

## Diagnostics surface

The rootstock MUST expose Sprig™ state in its diagnostics surface. The reference implementation reuses the EndpointHealth registry keyed by `capability`, where Sprig™ rows are filtered by `capability.startswith("sprig:")`.

Required diagnostics fields per Sprig™:

- `capability` — full string like `"sprig:embedding"`
- `delivery` — `oci-artifact` | `service-endpoint`
- `cultivar`, `variety`, `sprig_version`, `spec_version` — from the manifest (variety may be null for `service-endpoint`)
- `state` — `sprouted | grafting | grafted | dormant | wilted | pruned`
- `pid` — process id when Grafted under `oci-artifact`; null otherwise
- `port` — loopback port when Grafted under `oci-artifact`; null otherwise
- `endpoint_url` — TLS URL when Grafted under `service-endpoint`; null otherwise
- `selected_variety` — the variety name the rootstock dispatched to (e.g. `hosted-us-east`). For `service-endpoint`, populated whether the pin was a literal, `default`, or `auto`. For `oci-artifact`, mirrors the pinned variety.
- `auto_selection_rtt_ms` — round-trip time of the `/health` probe that won the `auto` selection, when applicable; null otherwise.
- `last_probed_at`, `last_ok_at`, `consecutive_failures` — supervisor or probe tracking
- `last_inspect_at` — last successful `/inspect` probe for `service-endpoint` Sprigs™; null for `oci-artifact`
- `error_class`, `error_message` — last structured failure if Wilted (`sprig_inspect_drift`, `variety_pin_required`, `variety_unknown`, `variety_no_default`, `variety_auto_no_probes`, `variety_reserved_name` are the service-endpoint-specific classes)

The diagnostics surface MUST distinguish Wilted from other failure states so the operator UI can render a Revive action.

The diagnostics surface SHOULD include a per-Sprig™ "Revive" action that triggers a fresh graft attempt. Reviving a Wilted Sprig™ resets the backoff counter and starts a single restart attempt at the lowest backoff window.

The diagnostics surface MUST NOT expose secret material. Sprig™ rows include URLs and PIDs; they do not include API keys, signing keys, or any operator-provided credentials.

## Graft API

The rootstock MUST expose these endpoints. The reference implementation puts them under `/api/v1/retrieval/sprigs/`; other rootstocks MAY choose a different prefix.

**`POST /sprigs/graft`** — body `{capability, cultivar, variety}`. Pull, verify, extract, launch. Returns a SprigHandle with `{name, capability, cultivar, variety, port, state, pid}`. Idempotent: if the Sprig™ is already Grafted, returns the existing handle.

**`POST /sprigs/prune`** — body `{name}`. SIGTERM, SIGKILL fallback, delete extraction directory, mark Pruned in state.json. Idempotent.

**`POST /sprigs/topgraft`** — body `{name, new_cultivar}`. Atomic cultivar swap per the topgraft sequence above. Returns the new handle. The old port stays reachable until the drain window expires.

**`GET /sprigs`** — returns the full catalog: available, grafted, wilted, dormant, and pruned Sprigs™. The diagnostics page and the Wizard mode picker both read from this endpoint.

**`POST /sprigs/revive`** — body `{name}`. Force a single restart attempt on a Wilted Sprig™. Resets the backoff counter. Returns the new state.

All endpoints MUST be gated by admin authentication. All endpoints MUST reject URLs or capability strings not in the active catalog (SSRF defense; mirrors the `_collect_urls(app)` pattern from the diagnostics router).

## Security

- **Sigstore verification is mandatory.** For `oci-artifact` Sprigs™ the rootstock MUST refuse any tar.zst that does not pass `cosign verify` against the publisher identity declared in the Sprig Manifest™. For `service-endpoint` Sprigs™ the rootstock MUST refuse any `/sage-is/v1/inspect` response whose detached signature does not pass `cosign verify` against the same declared identity.
- **Loopback only for `oci-artifact`.** Sprig™ ports under local supervision MUST bind to `127.0.0.1`. The rootstock MUST refuse a Sprig™ that tries to bind a routable interface (validated at supervisor launch time via the port-allocation contract).
- **TLS only for `service-endpoint`.** Remote Sprig™ endpoints MUST use HTTPS. The rootstock MUST refuse to graft an endpoint URL with `http://` scheme. Certificate validation MUST use the system trust store unless the operator has explicitly pinned a CA (operator override, not a Sprig™-author decision).
- **No exec arbitrary.** The supervisor only executes `bin/<process.binary>` from a verified, extracted Sprig™. The operator cannot supply a command string and the supervisor does not invoke a shell.
- **SSRF guard.** The graft API rejects any URL or capability string not in the active Sprig Manifest™. This mirrors the same defense used by the diagnostics probe endpoint.
- **Auth tokens are env-only.** The bearer token for a `service-endpoint` Sprig™ MUST be resolved from the env var named in `service.auth.env_var` at probe time. The token value MUST NOT be persisted to `state.json`, `distribution.env`, the SQLite config table, or any API response. The hardlinked `distribution.env` is shared across sibling repos; storing a token there would leak it to every linked workspace.
- **No secret material in API responses.** Sprig™ rows in `GET /sprigs` include URLs, PIDs, and lifecycle state. They do not include API keys, bearer tokens, signing keys, or any operator-provided credentials.
- **Spec-version refuse.** The rootstock MUST refuse a Sprig™ whose `spec_version` is newer than the rootstock supports. Error: `sprig_spec_too_new` with the supported and requested versions in the structured body.
- **Inspect-drift refuse.** For `service-endpoint` Sprigs™, an `/inspect` response whose `spec_version`, `capability`, or (when declared) `cultivar` differs from the originally-signed manifest MUST transition the row to Wilted with error class `sprig_inspect_drift`. The operator decides whether to Revive (accept the drift after review) or Prune.

## Configuration

A v1 rootstock reads Sprig pins from a configuration file. The reference implementation uses the hardlinked `distribution.env` pattern; other rootstocks MAY use any equivalent declarative source. The pin shape differs by delivery.

### Pin shape for `delivery: oci-artifact`

```env
SAGE_IS_SPRIG_<NAME>_DELIVERY=oci-artifact
SAGE_IS_SPRIG_<NAME>_REPO_TAG=v1.0
SAGE_IS_SPRIG_<NAME>_<CULTIVAR>_<VARIETY>_SHA256=<sha256>
SAGE_IS_SPRIG_<NAME>_<CULTIVAR>_<VARIETY>_SHA256=<sha256>
# repeat for each (cultivar, variety) the rootstock wants available
```

Example:

```env
SAGE_IS_SPRIG_EMBEDDING_DELIVERY=oci-artifact
SAGE_IS_SPRIG_EMBEDDING_REPO_TAG=v1.0
SAGE_IS_SPRIG_EMBEDDING_E5_LARGE_LINUX_AMD64_CPU_SHA256=9a4f3e...
SAGE_IS_SPRIG_EMBEDDING_E5_LARGE_LINUX_ARM64_CPU_SHA256=b8c2f1...
```

When `_DELIVERY` is omitted the rootstock defaults to `oci-artifact` for backward compatibility with manifests written before this section existed.

The rootstock MUST treat the pinned SHA256 as authoritative; if the pulled artifact's SHA256 does not match the pin, the graft refuses.

Operators who want to track a moving tag (uncommon, mostly for development) can omit the per-variety SHA256s; the rootstock SHOULD then log a warning at every graft because the supply chain guarantee is downgraded to whatever sigstore alone provides.

### Pin shape for `delivery: service-endpoint`

```env
SAGE_IS_SPRIG_<NAME>_DELIVERY=service-endpoint
SAGE_IS_SPRIG_<NAME>_ENDPOINT_URL=https://<host>[/<base-path>]    # discovery URL where /sage-is/v1/inspect lives
SAGE_IS_SPRIG_<NAME>_VARIETY=<value>                              # required when publisher advertises multiple varieties; optional otherwise
SAGE_IS_SPRIG_<NAME>_AUTH_ENV=<env-var-name-holding-the-token>
SAGE_IS_SPRIG_<NAME>_PUBLISHER_IDENTITY=<cosign-identity-or-well-known-URL>
SAGE_IS_SPRIG_<NAME>_INSPECT_INTERVAL_S=300       # optional; default 300
SAGE_IS_SPRIG_<NAME>_HEALTH_INTERVAL_S=30         # optional; default 30
```

Example (single-variety publisher; `_VARIETY` omitted because only one variety is advertised):

```env
SAGE_IS_SPRIG_TTS_DELIVERY=service-endpoint
SAGE_IS_SPRIG_TTS_ENDPOINT_URL=https://api.elevenlabs.io
SAGE_IS_SPRIG_TTS_AUTH_ENV=ELEVENLABS_API_KEY
SAGE_IS_SPRIG_TTS_PUBLISHER_IDENTITY=https://elevenlabs.io/.well-known/sage-is-publisher
SAGE_IS_SPRIG_TTS_INSPECT_INTERVAL_S=600
```

Example (multi-variety publisher; `_VARIETY` is required because the manifest advertises `hosted-us-east`, `hosted-eu-west`, `hosted-asia-pacific`):

```env
SAGE_IS_SPRIG_EMBEDDING_DELIVERY=service-endpoint
SAGE_IS_SPRIG_EMBEDDING_ENDPOINT_URL=https://embedding.example.com
SAGE_IS_SPRIG_EMBEDDING_VARIETY=hosted-eu-west       # pin to a specific region
SAGE_IS_SPRIG_EMBEDDING_AUTH_ENV=EMBEDDING_API_KEY
SAGE_IS_SPRIG_EMBEDDING_PUBLISHER_IDENTITY=https://embedding.example.com/.well-known/sage-is-publisher
```

`_VARIETY` accepts three forms:

- A literal advertised variety name (`hosted-us-east`, `hosted-premium`, etc.) — the rootstock dispatches to that variety's `endpoint_url` from the manifest.
- `auto` — the rootstock probes `GET /health` against every advertised variety at graft time and picks the one with the lowest round-trip time. The selected variety is persisted in `state.json` and shown in the diagnostics row.
- `default` — the rootstock uses the variety the publisher marked `default: true` in the manifest. Refuses the graft if no default is declared.

If the publisher advertises only one variety and `_VARIETY` is unset, the rootstock uses the only available variety silently. If the publisher advertises multiple varieties and `_VARIETY` is unset or empty, the graft refuses with structured error `variety_pin_required` and lists the advertised varieties so the operator can pick one.

Critical: `_AUTH_ENV` holds the NAME of the env var, not the token itself. The actual token (e.g. `ELEVENLABS_API_KEY`) MUST be supplied at runtime through a different channel — the operator's own env file, a secrets manager, or the container orchestrator. Storing the token value in `distribution.env` is a security violation because that file hardlinks across three sibling repos.

The rootstock MUST treat `_PUBLISHER_IDENTITY` as the cosign verification identity at graft time and at every subsequent `/inspect` probe. A change to this value invalidates the existing graft and requires the operator to re-graft from a fresh manifest fetch.

## Migration

A v1 rootstock MUST handle the case of an operator upgrading from a fat-image install that baked ML deps into the rootstock layer.

Detection: at lifespan startup, look for `data/ml_packages/` (or the rootstock-equivalent legacy install path). If present and the operator's engine config is the legacy default (no localhost URL), surface a migration banner in the admin UI.

The banner offers a one-click flow:

1. Pull and graft the matching Sprig™ (e.g. `sprig-embedding-e5-large`).
2. Verify Grafted.
3. Top-graft the engine config from legacy to `openai`+localhost URL.
4. Run a smoke check (one embedding request) to confirm the new path works.
5. Offer to delete `data/ml_packages/` on operator confirm.

The legacy install path stays functional through v1 of the rootstock spec. Removal of the legacy branch happens in a later rootstock release; the migration banner persists for at least one major version.

## Conformance

Conformance is split by delivery shape so a minimal embedded rootstock can claim `oci-artifact`-only support and still be conforming for that subset. A rootstock that advertises `service-endpoint` support has to satisfy the universal MUSTs plus both subsets below.

### Universal MUSTs (apply to both delivery shapes)

1. Read the Sprig Manifest™ from configuration and populate the catalog.
2. Verify sigstore signatures before activating any Sprig™ — the tar.zst for `oci-artifact`, the `/inspect` manifest for `service-endpoint`.
3. Refuse Sprigs™ with `spec_version` newer than the rootstock supports.
4. Refuse Sprigs™ that declare a transport other than `http` or `none` in v1, with the structured error class `transport_not_yet_implemented` and the declared transport name in the error body.
5. Refuse graft requests for capabilities not in the active manifest (SSRF defense).
6. Implement the Graft API endpoints (`/graft`, `/prune`, `/topgraft`, `/sprigs`, `/revive`) gated by admin authentication.
7. Pause automatic retries after 5 consecutive failures and surface a Revive action.
8. Persist runtime state to disk so a rootstock restart can resume Sprigs™ that were Grafted at shutdown.
9. Surface Sprig™ state in the diagnostics page with the fields listed in Diagnostics surface.
10. Surface a migration banner when a legacy install path is detected and an engine config is still set to the legacy default.

### Additional MUSTs for `delivery: oci-artifact` (`transport: http`)

1. Verify `binary_sha256` against the extracted binary.
2. Bind Sprig™ ports to the loopback interface only.
3. Restart Wilted Sprigs™ with exponential backoff up to a 30-second ceiling.
4. Send SIGTERM before SIGKILL on Sprig™ shutdown, honoring `process.shutdown_grace_s`.
5. NOT exec arbitrary commands; only run `bin/<process.binary>` from a verified, extracted Sprig™.

### Additional MUSTs for `transport: none` (typically with `delivery: oci-artifact`)

1. Launch the binary once per graft and wait for it to exit (bounded by `process.ready_timeout_s`).
2. Treat exit code 0 as success and any non-zero code as failure (Wilted with `sprig_build_exit_nonzero`, exit code in `error.code`).
3. When `process.expect_artifacts: true` (the default), refuse to transition to Grafted unless `process.output_dir` contains at least one file after a code-0 exit (Wilted with `sprig_build_no_artifacts`).
4. Refuse to allocate `${PORT}` for `transport: none` Sprigs™; the supervisor MUST NOT open a loopback port for them.
5. Apply the per-capability artifact consumption operation atomically (write a sibling target, then `rename(2)` into place) so in-flight requests do not see a torn surface.
6. NOT apply restart-with-backoff to one-shot Sprigs™. A failed run stays Wilted until the operator clicks Revive; Revive re-runs the process from scratch.
7. Persist `last_exit_code`, `last_run_at`, `artifact_count`, and `consumed_at` (when applicable) in `state.json` for each `transport: none` row.

### Additional MUSTs for `delivery: service-endpoint`

1. Refuse endpoint URLs with `http://` scheme; require HTTPS with a system-trusted (or operator-pinned) certificate chain.
2. Resolve the auth token from the env var named in `service.auth.env_var` at probe time, never persist the token value to `state.json` or any other on-disk file, and never include it in API responses.
3. Probe `/health` and `/inspect` on the configured intervals (defaults 30s and 300s); back off on consecutive failures using the same 1s → 30s curve as process supervision, but applied to the next probe delay rather than a process restart.
4. Transition to Wilted with error class `sprig_inspect_drift` when an `/inspect` response shows a different `spec_version`, `capability`, or (when declared) `cultivar` than the originally-signed manifest.
5. Re-verify the manifest's sigstore signature on every `/inspect` response, not just at graft time.
6. Apply the variety selection rules from the Sprig Spec™ when the manifest declares `service.varieties[]` with two or more entries: refuse the graft with `variety_pin_required` if `SAGE_IS_SPRIG_<NAME>_VARIETY` is unset or empty; refuse with `variety_unknown` if the pin does not match an advertised variety; refuse with `variety_no_default` if the pin is `default` but no variety carries `default: true`; refuse with `variety_auto_no_probes` if the pin is `auto` and every advertised variety fails its initial `/health` probe.
7. For `auto` variety selection, run the per-variety `GET /health` probes concurrently with a 5-second per-probe timeout and select the variety with the lowest measured round-trip time among the probes that returned `200 OK`. Persist the selected variety name and the measured RTT in `state.json`; surface both in the diagnostics row so the operator can see what `auto` resolved to.
8. Treat the variety selection as fixed for the lifetime of the graft. The rootstock MUST NOT silently re-select a different variety mid-flight even if a different one becomes faster. Switching varieties is the operator's job via topgraft.
9. Refuse a manifest whose `service.varieties[]` block contains an entry whose `name` is one of the reserved tokens `auto` or `default`. Error: `variety_reserved_name`.

### Universal SHOULDs

1. Wrap dispatched HTTP calls in a structured endpoint-health helper so Wilted Sprigs™ produce the same boundary error shape any external endpoint failure would.
2. Persist endpoint health and supervisor state to separate files so debugging is easier.
3. Expose a `POST /sprigs/revive` that resets the backoff counter and triggers a single graft retry.
4. Implement topgrafting with a drain window so cultivar swaps do not interrupt in-flight requests.
5. Log structured events on every state transition.

The conformance test suite lives at `github.com/sage-is/rootstock-spec/conformance/`. Run against a candidate rootstock:

```bash
rootstock-conformance check http://localhost:8080
```

The test suite runs against a live rootstock that has been pointed at a published mock Sprig™ catalog. It exercises every required behavior and produces a JSON report with PASS/FAIL per requirement.

## Reference implementation

The reference rootstock is `github.com/sage-is/AI-UI`. Files of note for implementers studying the reference:

- `app/backend/sage_is_ai/sprigs/` — the Grafter subsystem (protocol, artifact, supervised, registry, catalog).
- `app/backend/sage_is_ai/diagnostics/health_registry.py` — the EndpointHealth registry; Sprig™ rows reuse the same shape.
- `app/backend/sage_is_ai/routers/diagnostics.py` — the diagnostics JSON API.
- `app/backend/sage_is_ai/routers/retrieval.py` — the Graft API endpoints.
- `distribution.env` — the Sprig Manifest™ pins.

Read these as worked examples. The reference is licensed AGPL-3.0; other rootstocks may relicense their own code but the spec itself is intentionally implementation-language-agnostic.

## Changelog

- **v1 (draft)** — initial publication. Defines the rootstock side of the Graft Union™. Transports: `http` (loopback for oci-artifact, TLS for service-endpoint) and `none` (one-shot fire-and-forget with exit-code health, build-tooling focus). Refuses Sprigs™ declaring any other transport with `transport_not_yet_implemented`. Mirrors Sprig Spec™ v1's vocabulary and lifecycle states. Supports both delivery shapes from the Sprig Spec™: `oci-artifact` (process supervision, loopback) and `service-endpoint` (probe-based monitoring, TLS). Handles single-variety and multi-variety service-endpoint Sprigs™, including `auto` latency-based variety selection at graft time. Reserves dev/build tooling capability prefixes (`dev-`, `build-`) alongside ML and infrastructure. Conformance is split so a rootstock can claim `oci-artifact`-only support if it does not want to handle remote Sprigs™. License compatibility: operator running unmodified Rootstock™ owes no AGPL obligation regardless of grafted Sprig™ licenses; arms-length process boundary applies to all transports.
- **v1.1 (planned)** — `shmem` transport handler ships in the supervisor (shared-memory orphan cleanup at lifespan startup, control-channel watchdog, region-size verification). First reference shmem Sprig™ is `sage-is/sprig-embedding-batch-shmem`. The v1.1 Rootstock™ stops refusing `transport: shmem` Sprigs™ with `transport_not_yet_implemented` and accepts them.
