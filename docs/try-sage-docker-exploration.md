# try.sage Docker Image — Shipping Exploration

This doc explores how to ship try.sage as a single Docker image an operator can `docker run` with one command. It is a recommendation, not a working Dockerfile. Read [try-sage-deployment.md](try-sage-deployment.md) for the runtime contract first. This doc only covers packaging.

## Recommendation summary

- Ship one image — the existing production image. Gate try mode behind `ENABLE_TRY_SAGE=true` at runtime. This is approach 2 below.
- Add a thin `docker-compose.try-sage.yaml` next to the existing `docker-compose.yaml` for operators who prefer compose. This is approach 3, and it composes on top of approach 2 — no conflict.
- Skip the build-time variant (approach 1). It doubles registry footprint and CI cost for zero runtime benefit.
- Add `make try_sage_start` and `make try_sage_stop` as the canonical operator UX. They already exist in the Makefile. This doc explains why those targets are enough and what the next steps look like.
- The hidden LLM secrets stay env-only — never bake `TRY_SAGE_LLM_API_KEY` into an image layer.

## Three approaches considered

### Approach 1 — Build-time variant (`Dockerfile.try-sage`)

Ship a second Dockerfile that bakes `ENV ENABLE_TRY_SAGE=true` into the image. Operators run it without setting that env var. The image still needs `TRY_SAGE_LLM_API_URL`, `TRY_SAGE_LLM_API_KEY`, and `TRY_SAGE_LLM_MODELS` at runtime — those are secrets and must never sit in a layer.

**What changes**

- New `Dockerfile.try-sage`. Likely a one-line `FROM ghcr.io/sage-is/ai-ui:${TAG}` plus `ENV ENABLE_TRY_SAGE=true`.
- New Makefile targets `it_build_try_sage`, `it_build_multi_arch_push_GHCR_try_sage`.
- Second tag stream in GHCR: `ghcr.io/sage-is/ai-ui-try-sage:vX.Y.Z`.
- CHANGELOG and release docs grow a "two image" note.

**Operator UX**

```bash
docker run -d -p 8080:8080 \
  -e WEBUI_URL=https://try.sage.is \
  -e TRY_SAGE_LLM_API_URL=$URL \
  -e TRY_SAGE_LLM_API_KEY=$KEY \
  -e TRY_SAGE_LLM_MODELS='["gpt-4o-mini"]' \
  ghcr.io/sage-is/ai-ui-try-sage:latest
```

One env-var fewer than approach 2. That is the only win.

**Trade-offs**

- Two images to build, scan, sign, and publish. Roughly double the CI minutes and registry storage.
- Two release-note streams. If we ship a security patch, we patch both.
- Drift risk. Someone fixes a bug on the production image and forgets the trial image. The trial then ships a stale build until the next cycle.
- Confuses CapRover. Operators who already know which tag to pull now have to pick a tag flavor too.
- Doesn't simplify the secrets story. The API key still has to come in at runtime.

Net: pays a real cost in CI and surface area to save the operator typing one env var. Skip it.

### Approach 2 — Runtime variant (RECOMMENDED)

One image. The same image production runs. Trial mode is a runtime flag.

```bash
docker run -d -p 8080:8080 \
  -e ENABLE_TRY_SAGE=true \
  -e WEBUI_URL=https://try.sage.is \
  -e TRY_SAGE_LLM_API_URL=$URL \
  -e TRY_SAGE_LLM_API_KEY=$KEY \
  -e TRY_SAGE_LLM_MODELS='["gpt-4o-mini"]' \
  ghcr.io/sage-is/ai-ui:latest
```

**What changes**

- Nothing in the Dockerfile. Trial mode is already env-driven per Phase A1.
- New Makefile targets `try_sage_start` and `try_sage_stop` (already added).
- Documentation says "the same image you already run, with these env vars".

**Operator UX**

Two paths.

1. `make try_sage_start` after putting the trial vars in `.env`. The Makefile target verifies `TRY_SAGE_LLM_API_URL`, `TRY_SAGE_LLM_API_KEY`, and `TRY_SAGE_LLM_MODELS` are set before running `docker run`. Friendly error if any are missing.
2. Raw `docker run` for operators who want it. The five env vars above plus a port and a volume. Same image.

**Trade-offs**

- One env var more than approach 1 — `ENABLE_TRY_SAGE=true`.
- Image size unchanged. Trial code paths sit dormant in the production image. They are small (a few routers, a seed module, a few markdown templates). The cost is bytes, not megabytes.
- One image to ship. One CI pipeline. One signing run. One scan.
- Matches the open-webui pattern. Operators who came from upstream find it familiar.
- Trial wiring is auditable from the production image — security teams can see the same code in both flows.

This is the standard pattern for SaaS-style images. It is the cheapest path to "single image, one `docker run`".

### Approach 3 — Compose wrapper (`docker-compose.try-sage.yaml`)

A second compose file that wraps the existing image with the right env block.

```yaml
services:
  sage-try:
    image: ghcr.io/sage-is/ai-ui:${IMAGE_TAG:-latest}
    container_name: sage-try
    ports:
      - "${PORT_MAPPING:-8080:8080}"
    environment:
      ENABLE_TRY_SAGE: "true"
      WEBUI_URL: ${WEBUI_URL}
      TRY_SAGE_LLM_API_URL: ${TRY_SAGE_LLM_API_URL}
      TRY_SAGE_LLM_API_KEY: ${TRY_SAGE_LLM_API_KEY}
      TRY_SAGE_LLM_MODELS: ${TRY_SAGE_LLM_MODELS}
      TRY_SAGE_USER_SEAT_COUNT: ${TRY_SAGE_USER_SEAT_COUNT:-3}
      TRY_SAGE_RESET_INTERVAL_HOURS: ${TRY_SAGE_RESET_INTERVAL_HOURS:-24}
    env_file:
      - path: .env
        required: false
    volumes:
      - sage-try-data:/app/backend/data
    extra_hosts:
      - host.docker.internal:host-gateway
    restart: unless-stopped

volumes:
  sage-try-data: {}
```

**What changes**

- New file `docker-compose.try-sage.yaml`. About 20 lines.
- Documentation gets a one-liner: `docker compose -f docker-compose.try-sage.yaml up -d`.
- No code changes. No new image.

**Operator UX**

```bash
docker compose -f docker-compose.try-sage.yaml up -d
docker compose -f docker-compose.try-sage.yaml down
```

The `.env` file in the working directory supplies the secrets. Compose loads it automatically.

**Trade-offs**

- Lowest commitment. Add the file, point at the existing image. Done.
- Operators who already use compose get a one-liner. Operators who prefer raw `docker run` ignore the file.
- Composes on top of approach 2 — uses the same runtime contract, no fork.
- Slight duplication with `docker-compose.yaml`. We accept it; the trial deployment differs in env shape, which is exactly what compose files are for.

Ship this alongside approach 2. It is free.

## Concrete next steps

If we go with approach 2 plus the compose wrapper from approach 3, here are the PRs.

1. **PR 1 — Makefile targets.** `try_sage_start` and `try_sage_stop`. Already in this branch. Verifies the three required env vars before running. Defaults `TRY_SAGE_USER_SEAT_COUNT=3` and `TRY_SAGE_RESET_INTERVAL_HOURS=24`. Reuses `DOCKER_RUN_ARGS`.

2. **PR 2 — Compose wrapper.** Add `docker-compose.try-sage.yaml`. Document `docker compose -f docker-compose.try-sage.yaml up -d` in `docs/try-sage-deployment.md` under a new "Compose deployment" subsection.

3. **PR 3 — `.env.example` block.** Append a `# try.sage trial mode` section to `.env.example` listing every `TRY_SAGE_*` and `ANALYTICS_*` variable with empty values and a one-line comment per var. Operators copy the block, fill in secrets, run.

4. **PR 4 — README link.** Add a "Trial mode" callout to the top-level `README.md` pointing at `docs/try-sage-deployment.md` and the new compose file. One paragraph. No marketing.

5. **PR 5 — CapRover one-click.** Update `captain-definition` to include the trial env contract as commented-out defaults, and add a CapRover deployment recipe to `docs/try-sage-deployment.md` (the existing CapRover section already covers env vars — extend it with the one-click button JSON snippet).

6. **PR 6 — CI smoke test.** Add a `make try_sage_smoke` target that boots the image with stub trial vars (`TRY_SAGE_LLM_API_URL=http://localhost:9999`, fake key, empty model list), waits for `/health` to return 200, hits `/api/v1/sage/runtime/status`, expects `enabled: true`. Wire it into the existing GHCR push pipeline as a post-build check. Catches regressions where the trial code path silently breaks.

Optional later: PR 7 — Helm chart values for trial mode. Only if a Kubernetes user asks. CapRover and Compose cover the workshop deployments today.

## Open questions

These need a decision before any of the PRs land. Listed in priority order.

1. **Where should `TRY_SAGE_LLM_API_KEY` live in production?** Three options on the table. (a) Plain env var in CapRover's app config — simple, but keys appear in CapRover's UI to anyone with admin. (b) Docker secret mounted at `/run/secrets/try_sage_llm_api_key` — needs a code change to read from the file path, not the env var. (c) External vault (HashiCorp, 1Password Connect, etc) — overkill for a workshop trial, right cost for try.sage.is itself. Recommend (a) for self-hosted workshops and (c) for try.sage.is. Confirm before docs go out.

2. **Do we want a `latest-try-sage` tag at all?** If we ship approach 2 only, there is no second tag — same image, different env. But CapRover one-click templates pin to a specific tag. If we want a "click this button to spin up a trial" experience on the CapRover marketplace, we may want a tag that signals "this image is meant for try mode" even though the image is identical. Possible compromise: same image bytes, two tags — `:latest` and `:latest-try-sage` — pushed simultaneously from one build. Still one CI pipeline, just two `docker tag` calls.

3. **Should `make try_sage_start` build the image first?** Right now it assumes the image already exists locally. Mirrors `it_run`. Operators new to the project will hit "image not found" the first time. Two options. (a) Document `make it_build && make try_sage_start` as the first-time path. (b) Add a `try_sage_build_n_start` convenience target. Recommend (a) — keeps the trial target focused.

4. **Volume strategy for try.sage.is itself.** The Makefile defaults `VOLUME_DATA=sage-is-ai:/app/backend/data`. The reset routine wipes chats and files but keeps persona accounts and KB collections. So the volume must persist across container restarts but does not need backups in the conventional sense — KB sources live in the image, persona accounts re-seed if missing. Question: do we want a separate named volume for the trial deployment (`sage-try-data`) so a curious operator running both production and trial on the same host doesn't accidentally cross the streams? Recommend yes — bake `VOLUME_DATA=sage-try-data:/app/backend/data` into `make try_sage_start` or the compose file.

5. **Image size impact of trial code paths in production.** Phase A adds five new modules and a `data/try_sage_agents/` folder. The folder ships markdown KBs that production deployments will never use. Estimate is small (under 1 MB) but worth confirming before we ship. If the folder grows past 10 MB, consider a build flag that strips it from production images while keeping the runtime gate intact.

6. **CapRover one-click — single button, single fill-in form?** CapRover supports template apps with predefined env-var prompts. We could ship a CapRover app definition that prompts the operator for `TRY_SAGE_LLM_API_URL`, `TRY_SAGE_LLM_API_KEY`, and `TRY_SAGE_LLM_MODELS`, sets `ENABLE_TRY_SAGE=true` automatically, and spins the container. Worth a separate PR if CapRover is the primary deployment target for workshops.

## Why not ship a try.sage container as a separate repo

Brief note. We considered hosting trial mode in its own repo with its own image. We rejected it.

- The trial backend lives in the same FastAPI app as production. Splitting repos means duplicating the app or building a thin proxy. Both add cost.
- Bug fixes would have to land in two places.
- Frontend Phase B mounts trial-only Svelte components alongside production components. Splitting them means a second frontend build pipeline.

Trial mode is a runtime mode of the same product, not a different product. The packaging should reflect that.

## Acceptance for "shipped"

Trial mode counts as shipped when:

1. `make try_sage_start` boots a container that passes the Phase A verification list in [look-at-our-in-snazzy-gizmo.md](../../.claude/plans/look-at-our-in-snazzy-gizmo.md) sections 1-14.
2. `docker compose -f docker-compose.try-sage.yaml up -d` does the same.
3. `.env.example` has a complete trial block.
4. `docs/try-sage-deployment.md` cross-references this exploration doc and the compose file.
5. The CapRover one-click flow takes an operator from "click button" to "open banner, see five personas, scan QR, sign in" in under five minutes on a fresh CapRover instance.

That is the bar. Anything past that is polish.
