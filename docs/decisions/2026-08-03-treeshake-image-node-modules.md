# Decision record: does the runtime image carry node_modules, or only the built bundle?

**Date:** 2026-08-03 · **Card:** What the image actually installs · **Type:** research · **Chart:** `app/TODO.md`

## Answer

Only the built bundle. The runtime image contains no `node_modules`, no `node`, no `npm`, no `bun`. `bun install` runs in the `frontend` builder stage and dies there; the runtime stage copies `/app/build` (31.1 MB) and `/app/static` (11.8 MB) out of it and nothing else. The build installs `dependencies` and `devDependencies` together — `NODE_ENV` is never set and no `--production` flag is passed — so moving an entry between the two lists changes nothing that is installed or shipped.

## Evidence

Three stages: `frontend` → `python-build` → `runtime` (`Dockerfile:1-7`). Stage 1 is `node:22-bookworm` (`Dockerfile:23`), runs the only dependency install (`Dockerfile:34`, `bun install --frozen-lockfile`), and builds to `/app/build` (`Dockerfile:54`). Stage 3 starts from a fresh Wolfi base (`Dockerfile:111`), so nothing is inherited — everything arrives by explicit `COPY --from`.

Of the nine `COPY` instructions into the runtime stage, exactly two come from the frontend stage: `/app/build/` (`Dockerfile:208`) and `/app/static-runtime/` (`Dockerfile:214`). Both are compiled output. There is no `COPY --from=frontend /app/node_modules`.

The Dockerfile states the intent at lines 201-204: the dev toolchain (bun ~92 MB plus node_modules ~1.1 GB) is deliberately not baked in, and the `dev-svelte` Sprig delivers both on demand. Corroborated at `app/backend/sage_is_ai/sprigs/supervisor.py:282-299` — "dev mode grafts it; production never carries it."

Verified against the real image (`sage-is/ai-ui:develop`, built the same day): `/app/node_modules` does not exist, `find / -name node_modules` returns nothing, and `node`/`npm`/`bun`/`npx` are all absent from PATH. `/usr/local/bin/bun` is a dangling symlink to `/app/bun`, which the sprig fills in.

Size: 622 MB on disk. The largest layer is 267 MB of Python `site-packages` (`Dockerfile:154`); the entire frontend contribution is 43 MB, about 7%.

devDependencies are installed at build time: `NODE_ENV`, `--omit=dev`, `--production` and `npm ci` appear nowhere in the Dockerfile, and `node:22-bookworm` leaves `NODE_ENV` empty, so bun's production shortcut never fires. `npx vite build` resolves `vite` out of that install, which proves devDependencies are present. Local `app/node_modules` measures 1.0 GB.

The bundle is served by Python: `FRONTEND_BUILD_DIR` resolves to `/app/build` (`env.py:321`) and FastAPI mounts it (`main.py:2496-2500`). No Node process runs at runtime.

## What this means for the effort

**1. Image size is off the table.** Any claim that pruning dependencies shrinks the shipped image is void. Image-size work lives in the 267 MB Python layer, which is a different effort.

**2. `dependencies` → `devDependencies` reclassification is cosmetic.** Both lists install in full. Zero bytes move, in the builder or the image. Keep it as manifest hygiene if at all, and label it that way rather than filing it under size or supply chain.

**3. Pruning still pays — bill it correctly.** The real returns are builder install time, CI layer-cache size, the ~1.0 GB `dev-svelte` sprig artifact that must be built, signed, pushed and pulled, and every developer's local `node_modules`.

**4. Bundle-byte claims need per-package proof.** Vite bundles only what source imports, so an unimported entry already contributes zero bytes to `/app/build`. Measure `/app/build` before and after; never infer bundle savings from `node_modules` savings.

**5. Runtime CVE surface does not move.** No npm package reaches the shipped image, so a Trivy scan never saw these packages. A devDependency remains a build-time supply-chain surface either way.

**Uncertainty, stated:** verified against the locally built `develop` image, not a published GHCR tag. The local `ghcr.io/sage-is/ai-ui:3.0.0` is a larger, older image predating the Wolfi rootstock and was not inspected. Conclusions hold for images built from the Dockerfile at HEAD.
