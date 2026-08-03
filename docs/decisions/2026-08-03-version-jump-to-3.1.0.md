# try.sage.is moves to 3.1.0 before Friday

Resolves the **The version jump** card on [charts/friday-demo/TODO.md](../../charts/friday-demo/TODO.md).
Decided 2026-08-03 by Alexander, on the live readings in
[the screen inventory](2026-08-03-try-sage-screen-inventory.md).

## Decision

**Cut 3.1.0 off develop through the normal git-flow release, and run Friday's demo on it.**

## Why, in one line each

- try.sage.is runs a tag cut 2026-07-16 and is **71 commits behind develop**.
- Reviewer T's mobile cutoff is unfixed on the instance, and there is a phone in the room.
- Nothing under `/pages/` is registered on the running image, so no server-rendered
  surface exists to demo.
- The social preview work has to land somewhere, and the surface it belongs on — the
  server-rendered welcome page — does not exist on 3.0.0.

## Rejected, and why

**3.0.1 as a patch.** The 71 commits carry twelve server-rendered panels, a rebuilt
welcome page, the ui-Sprig contract, and the cookie bridge. Calling that a patch misreads
the content, and the Makefile's two version tracks treat minor and patch differently.

**Deploying develop untagged.** It breaks the rule that `IMAGE_TAG` is the last official
git tag, and it leaves the demo host running something with no tag to roll back to. Four
days before a customer demo is the wrong week to have no rollback.

## What ships by itself, without anyone choosing it

`ENABLE_TRY_SAGE` is `true` on the instance — confirmed in `/api/config`. On develop,
`main.py` registers `GET /` under that flag and serves the server-rendered welcome page
to any caller without an auth cookie, falling through to the SPA index for a signed-in
reader. Explicit routes resolve before the SPA mount, so **the anonymous landing page
changes the moment 3.1.0 boots**. Three consequences:

1. Reviewer T's cutoff is fixed on the surface that a phone in the room will hit first.
2. `TrySageWelcome.svelte` is gone, so there is no toggle back. The server-rendered page
   is the landing page.
3. A shared try.sage.is link previews **that document**, which is why the social tags
   belong on it and not on the SPA shell.

## Scope riding this release

Decided alongside the version, same session:

- **Social graph tags on the server-rendered pages only.** `try-sage.html` currently
  declares charset, viewport, title and one stylesheet, and nothing else — no
  description, no Open Graph, no Twitter card, no canonical. The SPA shell
  (`app/src/app.html`) has no OG tags either, but it is one file serving every
  deployment, so branding it as Sage.is would brand self-hosted instances too. The
  welcome page is per-deployment and is what a pasted link actually resolves to.
- **An Open Graph preview image.** No share-preview asset exists anywhere in the repo.
  What it shows is still open — see the **Social preview** card.
- **`web-app-manifest-512x512.png`** — still 170,761 bytes. Develop's icon cut took
  favicon, logo, splash and both dark twins to 45,710 and missed this one. The PWA
  manifest references it.
- **`favicon.svg`** — still 202,944 bytes on develop: two byte-identical 2036×2040 PNGs
  base64-wrapped in an SVG. The `image/svg+xml` link is already gone from `app.html`, so
  nothing fetches it; it is dead weight in the image. Live 3.0.0 still links it and still
  serves 198.2 kB of it.

Checked and **not** an issue: `app/static/icons/sage.2025-08-01.xcf` is 5.77 MB and
tracked in git, but `.dockerignore:26` excludes `**/*.xcf`, and the live host returns 404
for it. It never reaches the image.

## Consequence for the chart

**The cut line is dissolved, not deferred.** It asked which no-build surfaces flip before
the deploy. Cutting a tag off develop ships all of them, so the only question left is
which ones appear in the demo — and that is **Tour route list**. The card is removed
rather than parked; a scope boundary is not a step on the route.

**Ship and prove** now blocks on this record instead.

## Release runbook

Labels follow the house convention: **[MANUALLY]** is Alexander's, **[WE]** runs from a
CLI session.

1. **[MANUALLY]** Start the release branch: `make release` (git-flow-next, `require_gitflow_next`).
2. **[WE]** Land the scope above on the release branch: social tags, OG image, two icon fixes.
3. **[WE]** Gates: `make it_build`, `make e2e`, `make sprig_smoke`, `make ui_sprig_gate`,
   `make upgrade_gate`. Measure the welcome page before and after rather than asserting it.
4. **[MANUALLY]** `make release_and_push_GHCR` — runs `release_smoke`, then
   `release_finish` (which runs `distribution_verify`), tags, and pushes the multi-arch
   image to GHCR. try.sage.is is an amd64 host.
5. **[MANUALLY]** Pin `SERVER_TAG=3.1.0` in `distribution.env` and commit.
6. **[MANUALLY]** Deploy on CapRover **by index digest**, not by tag. Swarm has served a
   stale image after a same-tag redeploy.
7. **[WE]** Prove the running image, not the built one.

## Execution status, 2026-08-03

Landed on the working tree, unstaged, not yet on a release branch:

- **Social graph tags** — `try-sage.html` gains description, canonical, eleven `og:*` and
  five `twitter:*` tags; `try_sage_panel.py` supplies `base_url`, `site_name`,
  `social_image` and a `social_description` written for a reader who does **not** have
  the link yet. Rendered standalone in both config branches: with `WEBUI_URL` set, every
  URL comes out absolute (`https://try.sage.is/static/assets/images/og-image.jpg`); with
  it unset, the block is omitted entirely and the description survives. The magic-link
  minter's `localhost:8080` fallback is deliberately **not** reused — a clickable link
  needs a host, a share card pointing at localhost is worse than no card.
- **Share image** — `app/static/assets/images/og-image.jpg`, 1200×630, **55,147 bytes**,
  built from `tools/og-card/card.html` by headless Chrome and encoded with ImageMagick.
  **This is a rough card to react to, not final art**: the mark is `favicon.png` scaled
  up and the type is Georgia.

  Two earlier attempts are worth recording, because the first was wrong in a way that
  only showed up on inspection. Padding `favicon.png` onto black with `sips` produced a
  **white plate floating on a black field** — the icon is not transparent, and nothing
  in the byte count says so. Padding onto white fixed the seam and produced a card with
  no relationship to the page it previews. The third attempt takes the look from
  `try-sage.html` itself: same backdrop image, same two-layer dim, same circular mark,
  same serif heading. Rebuild instructions and the reasoning live in
  `tools/og-card/README.md`.

  JPEG rather than PNG or WebP: the same card as PNG is 271 kB against 55 kB, and the
  static mount serves `.webp` as `text/plain` (see below), which a crawler would reject.
- **`favicon.svg` deleted** — 202,944 bytes, referenced by nothing since the
  2026-08-02 icon cut. The comment in `app/src/app.html` that recorded the earlier
  decision to keep it on disk is corrected rather than left contradicting the tree.
- **Guard-rail** — `try-sage-welcome.cy.ts` gains two tests. The first asserts an
  invariant that holds in both config branches: either no social tags, or every URL
  absolute **and** `og:image` fetched and confirmed to return 200 with an `image/*`
  content type. The second asserts the SPA shell stays unbranded, which is the scope
  decision made executable. **Neither has been run** — that needs `make it_build` plus
  `ENABLE_TRY_SAGE=true SPEC=try-sage-welcome.cy.ts make e2e`.

### Not done, and why

**`web-app-manifest-512x512.png` stays at 170,761 bytes.** It is genuinely 512×512, so
the fix is recompression rather than resizing, and `sips` cannot quantize — re-encoding
produced **178,934 bytes**, larger than the original. Doing it properly needs `pngquant`
or `oxipng`, which is a brew install and therefore Alexander's call, or a step in the
Docker build. It is fetched on PWA install and not on any page load, so it is not on the
demo path.

### Found while verifying, unrelated to the release

`/static/assets/images/library.webp` is served with `Content-Type: text/plain`. `.jpg`
and `.png` get `image/jpeg` and `image/png` correctly, so it is a `.webp` gap in the
static mount's type map. Browsers sniff it and the slideshow renders, so nothing is
visibly broken — but a `.webp` share image would have failed the crawler. Choosing JPEG
avoided it by accident.

## What counts as proof

A 200 proves nothing here: the SPA catch-all answers 200 with the same 6,532-byte shell
for every unregistered path, including `/pages/*` and outright nonsense URLs. Three checks
that can actually fail:

- `GET /` **without** a cookie returns the welcome document, not the SvelteKit shell —
  grep the body for the absence of `_app/immutable`.
- `GET /pages/admin/sprigs` returns a real panel, not the 6,532-byte shell.
- `GET /api/config` reports `version 3.1.0`.
