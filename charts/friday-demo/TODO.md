# Friday demo — Chart

Charted 2026-08-03. Destination date 2026-08-07.

## Destination

Realtor R's kickoff runs on try.sage.is on Friday 2026-08-07 over screen share, with a phone in the room. It is a kickoff conversation and a product tour at once. Everything on screen has to be fast, and none of it can be School B's. At least one deploy ships before it.

## Notes

Codenames only in this file. It is tracked. Real names, commercial terms, and dates live in the untracked `.clients.md` at the repo root, which is a dead link in a fresh clone by design. Never write a client name here, in a commit message, or on any pushed branch.

try.sage.is is the `try-sage-is` app on the production CapRover host (its address lives in the deployment docs, not on this chart — `sage-internal-hostname` is a gitleaks rule and it fired on the first draft of this line), image `ghcr.io/sage-is/ai-ui:<tag>`. It runs **3.0.0, a tag cut 2026-07-16 and 71 commits behind develop** — read live on 2026-08-03, see the Screen inventory record. Treat "live on 3.0.0" as a statement about the tag rather than about the work: none of the no-build surfaces are on it. CapRover has served a stale image after a same-tag redeploy, so deploy pinned to `@sha256:<index-digest>` and verify the image that is running rather than the one that was built.

**Decided 2026-08-03: the instance moves to 3.1.0, cut off develop, before Friday.** Runbook and proof checks in the [version-jump record](../../docs/decisions/2026-08-03-version-jump-to-3.1.0.md).

The SPA catch-all returns 200 with the 6,532-byte shell for **any** unregistered path, including `/pages/*` and nonsense URLs. A 200 proves nothing. Check the body.

Consult the repo [TODO.md](../../TODO.md) for the no-build strangler state (Phases 3–4, the payload survey, the floor), plus `docs/no-build-surface-convention.md` and `docs/try-sage-deployment.md`. The route-payload numbers this chart leans on come from `cypress/e2e/upgrade/route-payload.cy.ts` and `workshop-payload.cy.ts`.

Git writes are Alexander's; sessions edit and stage nothing. Measure before and after; never assert a payload win. Decision records go in `docs/decisions/` as `YYYY-MM-DD-<slug>.md`.

The repo TODO.md rules that the four customer-blocking items run in sequence rather than in parallel ([TODO.md:86](../../TODO.md#L86)). This chart does not overturn that. It only decides which no-build work sits on the demo path.

## In Progress

<!-- claimed cards: exactly the ones a session is resolving right now -->

## TODO

<!-- charted open cards. A blocked card carries a Blocked-by line. -->

- [ ] **Social preview**: **the artifact is built and waiting for a reaction — that is all this card needs now.** Tags, image and guard-rail are on the working tree (see the version-jump record's execution status). Two things to judge, and neither is a code question. **The image**: 1200×630, 55 kB, rebuilt from the landing page's own look — library backdrop, the same two-layer dim, circular mark, serif heading — via `tools/og-card/card.html`. Rough, not final art: the mark is `favicon.png` scaled up and the type is Georgia. **The copy**: the card currently reads _"A hosted trial of Sage.is AI, the open-source AI platform for workshops and teams. By invitation only."_ — deliberately not the on-page tagline, because a share card is read by someone who does not have the link yet. Say whether both hold. #prototype

- [ ] **Four broken agents**: four of the five agents on try.sage.is answer `Model not found`. The connection serves one base model, `openai/gpt-oss-120b`; the other four point at `qwen/qwen3-32b` and `meta-llama/llama-4-scout-17b-16e-instruct`. Delete them, repoint them at the model that works, or extend the connection? `DEFAULT_MODEL_SELECTOR_FILTER` is `agents`, so the selector puts the broken four in front of the visitor. #interview

- [ ] **Tour route list**: which surfaces are on screen Friday, in what order? This is the sorting key for every other card. It decides which surfaces have to be fast, which have to be clean, and which get judged on a phone. Name routes rather than features. **It absorbed the old cut line**: 3.1.0 ships every server-rendered surface at once, so the only remaining question is which of them a visitor sees. #interview

- [ ] **Browser baseline**: what does the demo path actually cost on try.sage.is, measured in a browser? `curl` reached 226.5 kB wire / 330.6 kB decoded across the shell's 11 referenced assets, and that is a floor rather than a page cost — SvelteKit pulls route chunks by dynamic import and none of them appear in the HTML. Every payload number on the board came from Cypress against a restored production snapshot in a container, which is a different instance with 51 agents. Point `route-payload.cy.ts` at the live host. #research

- [ ] **Kickoff agenda**: which of the five open questions in `.clients.md` get asked Friday, and in what order? "Which task comes off his plate first" has no first rung until this session happens. #interview

- [ ] **Trial model set**: which models does the demo run on, and who pays for those tokens? One base model is served today. Time-to-first-token measured 1.62 s direct and 1.15 s through the one working agent, 16 SSE frames each — inside the destination's tolerance, on an instance with no other load. #interview

- [ ] **School B's residue**: delete it, or keep some of it? The premise was wrong and the cleanup is cheaper than the card assumed. Three knowledge bases carry school-flavoured names — "American Revolution", "Guess who", "Housing in Ottawa" — and **all three hold zero files**. Total stored content on the whole instance is 15.1 kB in two markdown files, both belonging to the `try_sage_kb_*` built-ins. All five accounts are `@try.sage.is` seeds. There is no personal data and nothing to export, so "ask them first" has little left to protect. Still a call for a person: one Space (`the-steam-room`) and one note remain unattributed. #interview

- [ ] **The `/api/models` cut**: does anything ship before Friday? **Demoted on live readings.** `/api/models` measures **11.9 kB decoded / 4.3 kB wire** on try.sage.is, not the 2,304 kB on the board — that figure came from the production snapshot with 324 model rows and base64 avatars. The defect is real and it is not on this instance. It returns the moment content is seeded with avatars uploaded through `ModelEditor.svelte`, which is the path any real-estate seeding takes. Decide whether that makes it a Friday card or a post-demo one. #prototype
  Blocked by [What replaces it on screen].

- [ ] **What replaces it on screen**: the instance is already close to empty, so this is the bigger half of the cleanup rather than an afterthought. Five agents, four of them broken; five knowledge bases, three of them empty; zero prompts, zero chats, zero functions, one note. What does the tour actually show — seeded real-estate sample material, Realtor R's own documents, or an empty product we narrate? Nothing belonging to Realtor R can go on this host; see the tenancy note below. #interview
  Blocked by [School B's residue].

- [ ] **Phone-width pass**: walk the tour surfaces on a real phone and record what breaks. **The welcome page is no longer the one surface that has been judged — on the live instance it is unfixed.** The server-rendered replacement is on develop, so try.sage.is still serves the Svelte `TrySageWelcome` that produced Reviewer T's bottom-of-page cutoff. Phase S established that a green suite is the weakest evidence on an interactive surface, so a person has to walk these surfaces and a viewport assertion will not stand in. #task
  Blocked by [Tour route list].

- [ ] **Ship and prove**: the tag is decided; what remains is who cuts it, when, and what evidence closes it. The release runbook and the three falsifiable checks are written into the version-jump record. **A 200 proves nothing** — the SPA catch-all answers 200 with the 6,532-byte shell for any unregistered path. Name the cut-off time for landing scope on the release branch, given Friday. #interview
  Blocked by [Social preview], [Four broken agents], [School B's residue].

## Backlog

<!-- the fog: in-scope questions you cannot phrase sharply yet -->

- Whether Spaces appears in the tour at all. The assistant and the VA are not confirmed in the room, and Spaces is the surface that answers "three humans, one workspace", so it may be the strongest thing to show or a distraction from a one-operator screen share.
- Whether any admin surface should be hidden from a first-time operator during the tour, and whether that is a demo choice or a product one.
- Messaging bridges. `.clients.md` flags WhatsApp as unresolved: going client-facing on his business number carries ban risk on the number his livelihood runs through, and Spaces may cover the internal case entirely. Too early to card, and probably not Friday.
- What the demo will expose that we cannot fix by Friday, and how it gets said out loud instead of steered around.
- Whether the engagement eventually needs its own tenant rather than the shared try.sage.is instance. **Sharpened by a live reading, and no longer really fog: `GET /api/v1/sage/runtime/personas` returns 200 to an anonymous caller with a working admin magic link.** That is deliberate — the endpoint is documented public when try-mode is on, and stable pre-workshop URLs are the point — but it means anyone who finds the host gets admin. Nothing belonging to Realtor R can live there. What is still unsharp is when the separate tenant has to exist and who provisions it.
- Whether the demo instance should be reset before Friday at all. `TRY_SAGE_RESET_AT` and `TRY_SAGE_RESET_INTERVAL_HOURS` already drive a scheduled wipe, and a reset landing mid-demo would be worse than any stale content.

## Out of scope

<!-- work ruled beyond the destination -->

- The mid-November FFPF benefit dinner. Sponsorship signage and materials only, no live software demo. It is a marketing deadline rather than a ship-by date, and it must not manufacture engineering urgency here.
- The "4-month milestone" from the original B2B notes. It is Realtor R's own arbitrary soon-ish with nothing anchoring it, and it gets replaced at kickoff rather than before.
- No-build Phases 3–4 beyond the surfaces on the tour path. The migration continues on the repo board; this chart only decides what rides the Friday deploy.
- Packaging the engagement as autoconfig Sprigs. That is the beachhead work, and it starts after the kickoff tells us what to package.

## Done

<!-- the index: one line per resolved card, gist plus link to the record -->

- [x] **The version jump**: cut **3.1.0** off develop through the normal git-flow release and run Friday on it; 3.0.1 and an untagged develop deploy both rejected. Anonymous `/` flips to the server-rendered welcome page by itself when it boots, which is where the social tags go and where Reviewer T's fix lands. Riding the release: OG tags on the server-rendered pages only, a new share image, `web-app-manifest-512x512.png` (170,761 B), `favicon.svg` (202,944 B). **The cut line is dissolved** — a tag off develop ships every surface, so the question collapsed into [Tour route list] — [decision](../../docs/decisions/2026-08-03-version-jump-to-3.1.0.md)

- [x] **Screen inventory**: read live 2026-08-03. The instance runs v3.0.0 and is 71 commits behind develop, so no server-rendered surface is live and Reviewer T's mobile fix is not deployed; four of five agents answer `Model not found`; the School B residue is three empty knowledge bases and 15.1 kB of stored content in total; `/api/models` is 11.9 kB here rather than the board's 2,304 kB — [decision](../../docs/decisions/2026-08-03-try-sage-screen-inventory.md)
