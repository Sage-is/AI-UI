# federation survey: boxes, the privacy edge and single sign-on

Pinned: aa25d9b + pending 3.2.1 paths

Backend paths start at `app/backend/sage_is_ai/`. Other repos are named: the tap (`homebrew-apps`), Trellis (`WEB-AI-Sage-Trellis`) and the Tinker repo (`AI--Tinker.Click`). Board cards are cited by title because `TODO.md` lines move. `(unverified)` marks what the host could not run or find: FastAPI and Authlib are not installed on it, and no Caddyfile for a box exists in the repos read.

## Surface

**What federation means today.** A rule set in `docs/federation.md` (144 lines, dated 2026-10-15), enforced in code at one place.

- Three rules (`docs/federation.md:15-19`): data stays home, definitions travel, numbers travel with consent.
- A box is one team's or one client's install: its AI-UI, its CRM and its Tinker library, on hardware it controls (`:21`). Each team gets its own Trellis and its own AI-UI (Trellis `crm/docs/federation.md:40`).
- The map shows three kinds of line and says none carries a record about a person (`:25-50`).
- Rule 1 is built for model calls only: the privacy filter on `/api/chat/completions` (`:84-93`).
- Rule 2 is manual: exports of agents, prompts and functions, Sprigs pinned by digest, theme tokens. Nothing scans a definition for data (`:64-74`).
- Rule 3 is built on the Trellis side only: scoped keys that fail closed, `aggregates` over 7, 30 or 90 days, synthetic data only until signed reports exist (Trellis `crm/docs/federation.md:62,68-90`). AI-UI has no totals-only endpoint and cannot issue a scoped key (`docs/federation.md:79-80`).
- Not built: the community hub, a shared library server, and identity across boxes (`:116-144`; board card "AI-UI as the single sign-on for our other projects").

**Box tooling.**

- Makefile: `box_check`, `box_up`, `box_update`, `box_status` and `box_read` (`Makefile:276-304`). `BOX` has no default, and `APPLY` and `REBOOT` count only at `1`, so a missing name never reaches a client's Mac.
- `sage-box` lives in the tap: 1,631 lines of bash, a 406-line man page, `docs/boxes/access.md` (96) and `docs/boxes/example.env` (47). One file per box in `~/.sage-is/boxes/` names the host and holds secrets only as `bw:` references. Modes: `source`, `image`, `peer`.
- Verbs: a dry-run plan, `--apply`, `--reboot`, `update`, `backup`, `mailbox`, `status`, `read VERB`, `unlock`, `lock`, `local`, `version` (`sage-box:111-155`).
- Four doors (`docs/boxes/access.md:5-12`): a read key held to five verbs (`probe`, `backup`, `power`, `containers`, `version`; `sage-box:86`), a window certificate of 1 to 4 hours signed by a FIDO CA, a person's own key, and a legacy admin key that new boxes never get.
- A box runs Colima, started at power-on by a LaunchDaemon, `trellis-crm` in server mode, and `ai-ui start` (Trellis `crm/docs/runbooks/pilot.md`, "What the box runs"). AI-UI is container `sage-ai` on network `sage-network`. Trellis calls it at `http://sage-ai:8080` (`sage-box:57-60`). `probe` asks `http://127.0.0.1:8080/health` (`sage-box:527`).
- The team box keeps AI-UI on :8080, loopback only (board heading "Dedicated instance — after the demo"). The decided door is a Cloudflare Tunnel on a codename host behind Cloudflare Access. It is not built: the address stays on the tailnet until then (Trellis `pilot.md`, "Not yet"). Five team logins come at the kickoff. The brief puts Caddy in front of the apps; no Caddyfile for a box is in the three repos (unverified).

**The privacy filter.**

- `privacy/` holds 805 lines (`engine.py` 199, `hooks.py` 214, `mapper.py` 38, `rules.py` 153, `shapes.py` 193, `__init__.py` 8) and 306 lines of tests. Tables `privacy_map` and `privacy_audit` sit in `models/privacy.py` (166 lines). The panel is `/pages/admin/privacy` (`pages/privacy_panel.py`, 222).
- The hook sits in `generate_chat_completion` (`utils/chat.py:174-221`). `active_for` picks by model, then by connection (`privacy/hooks.py:66-76`).
- Not covered: the raw `/openai` and `/ollama` routes (`routers/openai.py` 1,272 lines with 8 routes, `routers/ollama.py` 1,888 lines with 40), embeddings, images and speech (`docs/federation.md:91-93`).

**Identity edges.**

- Trellis to AI-UI: the `sk-` key of a user named Trellis with role `user`, made by `scripts/aiui_setup.py:80-101` in the Trellis repo. Calls: `GET /api/version`, `GET /api/v1/auths/`, `GET /api/v1/spaces/{id}` and `POST /api/v1/spaces/{id}/messages/post` (`crm/loop/aiui.py:47-64`; `crm/loop/notify.py:66-77`). A `/api/chat/completions` call is planned (`crm/docs/plans/loop.md`).
- AI-UI to Trellis: an OpenAPI tool server with a static bearer key, registered through an admin sign-in (`scripts/aiui_register.py`, 119 lines). Trellis answers 503 for a bad key table, 401 for a wrong key and 403 outside the key's scope (`crm/api/auth.py:127-149`).
- Tool servers take `auth_type` `bearer` (the stored key) or `session` (the caller's own AI-UI bearer; `utils/tools.py:75-80`).
- Outbound identity: `ENABLE_FORWARD_USER_INFO_HEADERS` (off) adds `X-Sage-User-Name`, `-Id`, `-Email` and `-Role` to model-provider calls (`routers/openai.py:758-769`; `env.py:282`).
- `sk-` keys act as their owner. One allowlist covers every key on the instance (`docs/federation.md:80,95-99`).

**Consumers measured in the SSO comparison.**

- Trellis signs people in with Django's stock auth: `LoginRequiredMiddleware` and `LOGIN_URL = "/admin/login/"` (`config/settings.py:154,162`). Its `crm/identity/` is alias linking for captured mail, not sign-in (`crm/identity/models.py:1-5`). It has seven dependencies, none for OIDC (Trellis `requirements.txt:3-11`). Roles are `is_staff` and `crm.review_task` (`config/settings.py:191-199`). Sessions use Django's two-week default. It sits behind a TLS-ending proxy (`config/settings.py:73-74`).
- The Tinker library server (`server/src/auth.rs`, 2,176 lines) is an OAuth client for Google and GitHub. The desktop app never sees a client secret. It starts a sign-in, shows a short code, polls with a secret key, and receives a session once the person confirms the code (`auth.rs:3-18,737-870`). Sessions are stored hashed and last 90 days (`:43,1241-1250`). Passwords are Argon2id (`:19-25`).
- The team box is the Mac mini described above.

## What really runs

**1. A model call through the edge** (`utils/chat.py:174-221`).

1. A caller posts to `/api/chat/completions` with a session token or an `sk-` key. `get_current_user` resolves the user (`../identity/README.md`).
2. `_generate_chat_completion` finds the model and asks `privacy.active_for(request, model)` (`utils/chat.py:207-209`). That is true unless the privacy config is off, the model is local, Ollama, a pipe or an arena model, or an override says no (`privacy/hooks.py:52-76`).
3. `outbound` pseudonymizes the text of every message part (`:83-113`). It does not touch tool arguments or a system prompt added later (board card "Privacy: tool arguments leak on the follow-up").
4. The provider answers. `reverse_completion` or the SSE reverser puts real values back (`:116-214`).
5. The mapper is one instance-wide table keyed by `PRIVACY_KEY` or, when that is unset, `WEBUI_SECRET_KEY` (`privacy/hooks.py:38-49`; `models/privacy.py:83-87`).

**2. A Trellis nudge into a Space.**

1. An admin runs Trellis's `scripts/aiui_setup.py`. It signs in by password, makes the Trellis user through `/api/v1/auths/add`, signs in as that user, reads or makes its `sk-` key, and creates a Space whose `access_control` names the user (`:80-122`).
2. The key goes into Trellis's environment as `AI_UI_API_KEY`. The tick loop posts one message per new event to `/api/v1/spaces/{id}/messages/post` with `Authorization: Bearer sk-…` (`crm/loop/notify.py:65-77`).
3. AI-UI resolves the key (`utils/auth.py:170-204`), applies the allowlist when it is on, then checks read access to the Space. Posting needs only read access (`routers/spaces.py:543-557`).
4. With restrictions on, the allowlist must name `/api/v1/spaces`, `/api/v1/auths` and `/api/version`, or the nudge and the status page break (`crm/loop/aiui.py:47-64`).

**3. The Tinker library server signs a person in** (`server/src/auth.rs`).

1. The desktop app asks `start` for a provider. The server returns the provider's address, an eight-digit code to show and a secret `poll_key` (`:737-780`). The address carries `client_id`, `redirect_uri`, `response_type=code`, `scope` and `state`. It carries no PKCE challenge and no nonce (`:748-760`).
2. The browser returns to `/v1/auth/callback/<provider>`. The server trades the code for a token with the client secret in the form body, then reads the profile (`:784-820,884-910`). It branches on the provider's name: `google` reads OIDC-style `sub`, `email` and `email_verified`, and anything else is treated as GitHub (`:911-950`).
3. `account()` needs a verified e-mail, checks the allow list (`*`, an address, `@domain` or `github:login`), links by `(provider, subject)` and then by e-mail, and never merges a password account with a provider account (`:1150-1239`). The first account administers (`:201,690`).
4. The person confirms the code in the browser. The app polls and receives a `tk_` session token once (`:828-870,1241-1250`).
5. A model login is a named, server-wide credential: provider, key, base URL, model. People are assigned to one, or get the default, and the app keeps it in memory (`:366-381,1111-1127`). It is not a per-person key.

**4. A box update** (`make box_update BOX=<name>`).

1. `box_check` refuses an empty `BOX` and a missing `sage-box` (`Makefile:282-285`). `sage-box <box> update` takes the first open door: a valid window, then `--as-me`, then the legacy key (`docs/boxes/access.md:14`).
2. On the box it runs `brew upgrade` for our tools, `git pull` in source mode, `trellis-crm update`, then `ai-ui start`. `ai-ui start` makes a new `sage-ai`, so the run joins it to `sage-network` again (`sage-box:1163-1166,1322-1332`).
3. A last check reads both apps and the network (`sage-box:1222-1240`).

**5. Reading a box** (`make box_read BOX=<name> WHAT=<verb>`).

1. `BOX` and `WHAT` reach the shell as environment variables, never as command text, and `$` is refused (`Makefile:294-304`).
2. `sage-box` resolves only the read key from the vault and calls ssh with `-F none` and one identity. The box's sshd sends that key to a root-owned dispatcher that matches the request against the five verbs (`docs/boxes/access.md:32,36`).
3. The plan adds a sixth verb, `census`. A new verb changes root's files on every box, which takes a window and the box's login password (`docs/boxes/access.md:60-63`).

**6. Team totals** (Trellis `crm/api/`).

1. A key lists `ops` such as `about`, `aggregates` and `areas`. A call outside the list answers 403 and names what the key may call (Trellis `crm/docs/federation.md:68-90`).
2. `aggregates` answers 403 on real data for every key until signed reports exist. Rows count as synthetic only when fixtures loaded (Trellis `config/settings.py:109-114`; `crm/docs/federation.md:62`).
3. Even with fixed windows, a key that polls daily can subtract one day from the next, and nothing records the calls (Trellis `crm/docs/federation.md:66`). Signed reports are the stated fix (Trellis `TODO.md:125`).

## Edge cases worth keeping

Tags: **K** carry over, **F** fix as a logged intended diff, **D** dies with a cut.

1. [K] **The filter is the only rule enforced in code.** Rule 1 reaches the model call and nothing else. No scan runs on exports and no totals-only endpoint exists (`docs/federation.md:74,79-80`). The Rootstock keeps one filtered door and no raw route.
2. [F] **Raw routes skip the filter.** `/openai/chat/completions`, the `/openai/{path}` catch-all and the three Ollama chat routes send real values (`docs/federation.md:93`; `routers/openai.py:901-908,1178`). They are 48 routes in 3,160 lines. The plan retires the Ollama proxy and offers no raw route.
3. [F] **The filter rewrites message text only.** A system prompt added after the filter and the arguments of a tool call reach the provider unmasked (`privacy/hooks.py:97-113`; `routers/openai.py:929`). Board card: "Privacy: tool arguments leak on the follow-up".
4. [K] **One pseudonym table serves the whole box.** `privacy_map` has no user or chat column, and `pairs()` returns every row, so a stand-in learned in one chat reverses in any other (`models/privacy.py:83-87`; `privacy/mapper.py:29-34`). The key is `PRIVACY_KEY` or, when that is unset, the session secret, so rotating either orphans every stand-in (`privacy/hooks.py:38-49`; `env.py:397-399`). Set `PRIVACY_KEY` before any rotation.
5. [F] **`/api/usage` returns user ids and the models in use**, not a total (`docs/federation.md:79`; `main.py:2140-2146`). Rule 3 needs a counts-only op.
6. [F] **The `sk-` allowlist fails open on an empty entry** (`utils/auth.py:176-192`; identity note, edge case 8). The recipe at `docs/federation.md:95-99` needs "no trailing comma, and test it".
7. [F] **`auth_type=session` hands the user's AI-UI bearer to the tool server** (`utils/tools.py:77-80`; `routers/configs.py:132-135`). The token has no `exp` by default and works at AI-UI. The board parks "forward the chatting user's identity to tool servers" (card "Paused 2026-10-01: Trellis first"). An audience-bound, short-lived token from the SSO provider replaces it.
8. [F] **The tool-server list is replaced whole on save, and `GET` returns every key in clear to admins** (`routers/configs.py:97-120`). Registration scripts read first and keep other entries (`scripts/aiui_register.py:1-12`). Two writers still race.
9. [F] **`ENABLE_FORWARD_USER_INFO_HEADERS` sends name, id, e-mail and role to the model provider**, outside the filter (`routers/openai.py:758-769`; `env.py:282`). Off by default. Keep it off on any box with an external connection.
10. [K] **Trellis fails closed.** No key, a short key, a placeholder or a bad client table answers 503 and names the client, never the key. `compare_digest` runs against every key, so timing does not say which one matched (`crm/api/auth.py:1-15,127-149`). `rs_api_key` copies this. AI-UI compares keys by database equality (`models/users.py:159-165`).
11. [K] **A key is consent.** A team gives a key and revokes it by deleting the entry, and the next call answers 401 (Trellis `crm/docs/federation.md:92-98`). In AI-UI a key is a user (`docs/federation.md:80`). The plan's `rs_api_key.ops` closes the gap.
12. [K] **A new `sage-ai` drops off `sage-network`.** `ai-ui start` makes a new container each time. `sage-box` joins it again after every start, and `verify` fails if it is not on the network (`sage-box:57-60,1163-1166,1222-1240`). Keep `ai-ui start` as it is, or move the join into the CLI.
13. [F] **`ai-ui start` publishes the port with `-p "$port:8080"`** (`cli/ai-ui:320`), which Docker Engine binds on every interface. The team box reports loopback only (board heading "Dedicated instance — after the demo"). Whether Colima's forwarding or a flag causes that is unrecorded (unverified). Server mode should bind loopback by default.
14. [K] **`BOX` has no default, and only `1` turns `APPLY`, `REBOOT` or `NIGHTLY` on** (`Makefile:276-281,286-287`; Trellis `crm/docs/runbooks/pilot.md`, end of "Once per box"). A default would send an update to a client's Mac.
15. [K] **The read key does five things, and the box enforces them.** Any other request gets `refused` and exit 2, and the box logs the caller's address (`docs/boxes/access.md:9,24-34`). `/api/v2/doctor` must be reachable through `probe`, which asks `/health` today. `/health` always answers true (`sage-box:527`; `main.py:2285-2287`).
16. [K] **Two instances on one host share a cookie jar**, because cookies ignore ports. Trellis tags its cookie names with `CRM_INSTANCE_LABEL` (Trellis `config/settings.py:102-108`; `crm/docs/federation.md:42`). AI-UI's `token` cookie carries no tag (`routers/auths.py:660-667`). The Rootstock sets `SESSION_COOKIE_NAME` from the box label.
17. [F] **The Tinker server sends no PKCE challenge and no nonce**, reads the profile with the access token and never checks an ID token (`auth.rs:748-760,884-910`). That is fine against Google. A provider we run should require PKCE, which costs the server about 12 lines.
18. [F] **A third provider needs a new match arm.** `fetch_profile` matches on `p.name`, and anything that is not `google` is parsed as GitHub (`auth.rs:911-950`). `main.rs:66-82` builds providers from two-argument constructors, so a provider with a per-box issuer URL needs a third argument.
19. [K] **Tinker keeps password accounts and provider accounts apart.** An unverified-e-mail account is never merged, and `@domain` allow entries need a verified e-mail (`auth.rs:19-25,1170-1197`). An AI-UI account must say whether its e-mail is verified (identity note, decisions).
20. [K] **The confirm code defeats a forged sign-in.** Without it, an attacker starts a sign-in and talks a victim into approving it (`auth.rs:9-15`). Any new provider keeps the step.
21. [F] **Upstream state is read at sign-in only.** Tinker's own `disabled` flag ends a session at once (`auth.rs:1503-1517`). A person disabled in AI-UI keeps a Tinker session for up to 90 days (`:43`).
22. [K] **The Tinker server holds model keys for its people.** A model login stores a sealed key per named login and hands it to the app (`auth.rs:288-296,365-381`). With AI-UI as the gateway, the key becomes an AI-UI credential and the call passes the filter. Per person means one login row per person, or a new column.
23. [F] **A saved value outranks a new default.** The code default for `ENABLE_COMMUNITY_SHARING` is off, because one share handler points at a public request bin (`config.py:1484-1492`). `docs/federation.md:144` says keep it off. Both snapshots hold the saved value `true`, and a saved value beats the default (`config.py:168-172`). The board card "Community-share leak + dead wiring" dates the decision 2026-08-15, before the September backup. Check the live setting before any federation claim, and have the settings registry flag a saved value that differs from a changed default.

## Ceremony to drop

- Raw proxy routes: `routers/openai.py`'s catch-all and chat route and all 40 routes of `routers/ollama.py` (1,888 lines) leave the core. The plan turns an Ollama URL into an OpenAI-compatible connection.
- `ENABLE_FORWARD_USER_INFO_HEADERS` and its 88 `X-Sage-User` mentions: replace with an explicit, per-connection opt-in or drop. Off by default.
- `auth_type=session` on tool servers (`utils/tools.py:79-80`; `routers/configs.py:132-135`, about 6 lines): the SSO provider mints a short audience-bound token instead.
- The `sk-` instance-wide allowlist (`utils/auth.py:176-192`, 17 lines, 2 settings): `rs_api_key.ops` replaces it.
- `/api/usage` as a federation surface (`main.py:2140-2146`): replace with a counts-only op.
- Nothing in `privacy/`: `engine.py`, `rules.py` and `shapes.py` are adapted unchanged; `hooks.py` (214 lines) becomes `walk.py`; the DB mapper (38 lines) keeps its cache fix.

## Rootstock equivalent

**Modules.** `federation/` has a 230-line cap. Rule 1 lives in `privacy/`, and the sign-in provider lives in `identity/sso/` (`../identity/README.md`). Line counts are estimates, counted the budget way.

| Where | Holds | Lines |
| --- | --- | --- |
| `federation/box.py` | the box's name, its public URL (the issuer), key ids, an `about` op, doctor lines for issuer, JWKS and clients | 50 |
| `federation/reports.py` | counts-only `aggregates` from Receipts over 7, 30 and 90 days, signed with a report key kept apart from the sign-in key | 90 |
| `federation/policy.py` | what each client may see: claims by client kind (inside or outside the box) and the ops a key may call | 60 |
| Total | | 200 |

- `privacy/` (300 cap): `walk.py` and the mapper keep Rule 1. `providers/call.py` takes only a privacy policy, so no raw route exists.
- `compat/` (220 cap): the OpenAI-compatible door for Trellis and Tinker. It accepts an `rs_api_key` or an SSO access token, and every call writes a Receipt with `caller=key:` or `client:`. Receipts feed `reports.py` and per-key budgets.
- Tool servers get a short, audience-bound token from the SSO provider instead of the session bearer.
- Box identity is the issuer URL plus two public keys: the sign-in JWKS and the report key. A team hands an umbrella the report key with the consent key, which answers the board's open question "how a box proves who it is".
- Outside the repo: the tap's read dispatcher must learn `/api/v2/doctor` and `census`, which takes a window on every box (`docs/boxes/access.md:60-63`). `ai-ui start` should bind loopback in server mode (`cli/ai-ui:320`).
- Rule 2's scan has no budget line. `docs/federation.md:18,74` promises it and nothing builds it. Either a Sprig takes it or the promise softens.

### SSO comparison

**The decision is Alexander's. It is due before F2's commit A** (plan, Cutover table, F2 row; board card "Rootstock: a clean-room Django core at one tenth the lines…"). Three options, each measured against Trellis, the Tinker library server and the team box. Line counts are estimates from the parts listed.

**Option (a): AI-UI as an OIDC provider. Authorization code with PKCE, RS256 ID tokens, JWKS.**

- Libraries: `PyJWT[crypto]==2.15.1` and `authlib==1.9.1` are pinned (`app/backend/requirements.txt:107,111`). `cryptography` is present and unpinned (`:19`).
- Authlib's source is not on this host. Typeshed stubs of an earlier release, bundled with Jedi in Homebrew's IPython 9.16.1 (`jedi/third_party/typeshed/stubs/Authlib/`), list a Django OAuth2 provider integration: `AuthorizationServer`, `ResourceProtector`, `RevocationEndpoint` and Django request adapters. They also list OIDC grants, PKCE and RFC 8414 metadata. The integration brings no models, views, consent page, discovery document or JWKS. That 1.9.1 keeps all of it is unverified.
- The pins sit under two critical Authlib advisories from 2026, one for a JWK-header bypass and one for signature verification (`app/backend/requirements.txt:106-110`).
- Trellis changes about 90 lines: login and callback views marked `@login_not_required`, a user mapper keyed on `sub`, role to `is_staff` and `crm.review_task`, and settings for the issuer, the internal URL and the secret. The admin login stays for break-glass. It adds one dependency.
- The Tinker library server changes about 55 Rust lines: `Provider::sage(issuer, id, secret)` 14, a `fetch_profile` arm for OIDC userinfo 15, `main.rs` wiring 12, S256 PKCE 12 (`auth.rs:86-125,911-950`; `main.rs:66-82`). `Allow` and `account()` stay.
- The team box needs two client rows and `WEBUI_URL` set (empty in both snapshots). Browsers use the public or tailnet name, while Trellis's server calls use `http://sage-ai:8080`. Authlib refusing a non-https token endpoint is from memory (unverified), and that hop is plain http.
- The Rootstock owns about 500 counted lines in `identity/sso/`: models 60 (client, code, token, key), grants 70 (code with PKCE, the OpenID extension, refresh), key handling 55 (RS256 pair at mode 600, `kid`, rotation, JWKS), claims 35, views 150 (discovery, JWKS, authorize with consent, token, userinfo, revoke, end-session), consent template 25, client ops 60, bearer validator for `compat/` 30. If 1.9.1 lacks the Django integration, add about 100.

Security of (a):

- Blast radius: one private key per box. A thief mints ID tokens for any user at every client of that box until it rotates. Today anyone who holds `WEBUI_SECRET_KEY` can mint an AI-UI session for any user (`utils/auth.py:114-122`), and Trellis's card plans to hand that key to Trellis (Trellis `TODO.md`, card "AI-UI is the identity provider"). Option (a) keeps signing power in one process. A stolen client secret alone mints nothing: the attacker also needs a user's browser to obtain a code.
- Rotation: add a key, publish both in the JWKS, sign with the new one, drop the old after the longest ID-token life plus the consumers' JWKS cache. No client edits. A client holds two secret hashes during a swap. The report key rotates apart from the sign-in key.
- Public clients: PKCE S256 and a loopback redirect on any port (RFC 8252), no secret. This is needed only if the desktop app talks to AI-UI itself. Today it does not: the library server is the OAuth client (`auth.rs:3-18`).
- Claims: `sub` is `user.id`, a stable uuid. Then `email`, `email_verified`, `name`, `role` and group names. A client flagged outside the box gets `sub` alone, which holds Rule 1.
- `/authorize` refuses `pending` and expired `temporary` users, through the same gate as `get_verified_user`, and it reads the session through `session.py`, so the try.sage cutoff applies.

Failure modes of (a):

1. AI-UI down: no new sign-in. Sessions already open run on, two weeks in Trellis (Django default) and 90 days in Tinker (`auth.rs:43`).
2. Revocation lag: a person disabled in AI-UI keeps both sessions until they end. Close it with short consumer sessions and a periodic userinfo check, about 25 lines each, or with back-channel logout.
3. Issuer drift: `iss` sits in every token and every client config. `WEBUI_URL` is empty in both snapshots, and the team box moves from a tailnet name to a tunnel host. Fix the public name first.
4. A JWKS cache outlasts an emergency rotation by its lifetime.
5. Clock skew: allow a minute of leeway on `iat` and `exp`.
6. Library risk: the two Authlib advisories sit on the verification path. Trellis can verify with PyJWT alone (`algorithms=["RS256"]`, `aud`, `iss`, `nonce`) and leave Authlib to AI-UI. Whether PyJWT's JWK client suits Trellis is unverified.
7. `email_verified` has no source: AI-UI never verifies an address (`routers/auths.py:693-811`), and Tinker's `@domain` entries trust the claim (`auth.rs:19-25`). Policy decides it.
8. `user.email` has no unique index, so consumers key on `sub`, as Tinker keys on `(provider, subject)` (`auth.rs:1150-1239`).

**Option (b): OIDC with HS256 ID tokens, each signed with that client's secret.**

- Trellis changes the same 90 lines and verifies with `jwt.decode(token, secret, algorithms=["HS256"], audience=…)`. Authlib's own support for HS256 ID tokens is unverified. The Tinker server changes the same 55 lines. It reads userinfo and never checks a signature (`auth.rs:884-910`), so the algorithm does not touch it. The team box changes as in (a).
- The Rootstock owns about 450 lines: (a) minus key handling (55) and the JWKS view (8), plus 25 for reversible secret storage and per-client signing.
- Blast radius: one secret per client. A client can mint tokens valid at itself only, which it could do anyway. AI-UI must keep each secret recoverable, because it signs with it. A database read leaks every client secret at once.
- Rotation: per client, with a two-secret overlap. The plan's phrase "no rotation without re-issuing every secret" does not hold for per-client secrets.
- No public clients, because there is no secret to hold. A tool server can check a user token only by holding the secret that signs it, so each tool server needs a secret of its own.
- Failure modes: those of (a) minus the JWKS items, plus algorithm confusion if any consumer accepts both HS256 and RS256, and secrets sitting in each consumer's env file. Standard libraries default to RS256 and JWKS, so each consumer gets a non-default setup.
- It saves about 60 lines against (a) and buys a weaker model. It is dominated.

**Option (c): forward-auth headers from the box's proxy.**

- Form: the proxy asks AI-UI "who is this?" and passes `X-Sage-User-*` to the app. AI-UI already emits those names outward (`routers/openai.py:758-769`). Caddy's `forward_auth` does the asking (from Caddy's documentation, unverified here). The legacy trusted-header sign-in runs the other way: the proxy tells AI-UI who the user is (`routers/auths.py:595-620`).
- Trellis changes about 40 lines and adds no dependency: a `RemoteUserMiddleware` subclass reading `HTTP_X_SAGE_USER_ID`, a backend mapping role to `is_staff` and `crm.review_task`, and settings.
- The Tinker library server cannot use a proxy for the desktop or iOS apps. As a service Sprig, it can sit behind AI-UI's own service proxy, which injects the header on loopback. That needs a header mode in `auth.rs` of about 40 lines and cannot serve a library server outside the box.
- The team box needs two `forward_auth` blocks, header stripping on every route and closed ports.
- The Rootstock owns about 50 lines: a verifier answering 204 with headers or 401, plus about 20 in the service proxy.
- Blast radius: no key. Trust is network position. Anything that reaches an app port can name any user, admin included, because `signin` accepts the header with no secret (`routers/auths.py:595-612`). On the team box AI-UI is loopback-only, but the Trellis container reaches `sage-ai:8080` by name on `sage-network` (`sage-box:57-60`), so a compromised Trellis could forge an AI-UI admin. `ai-ui start` publishes on every interface elsewhere (`cli/ai-ui:320`).
- The `token` cookie has no `Domain` (`routers/auths.py:660-667`), so forward-auth reaches only apps on the same hostname.

Failure modes of (c):

1. AI-UI down means Trellis down on every request, not only at sign-in.
2. A missing `forward_auth` on one route opens it. A header the proxy does not strip lets a client forge it. How Caddy treats a client-sent header of the same name is unverified, so strip by hand.
3. Logout and expiry are per app. A disabled user loses access on the next request, which is a strength.
4. No federation across boxes, no desktop or iOS app, no service-to-service call: none of them passes the proxy.
5. The team box's decided door is Cloudflare Access (board heading "Dedicated instance — after the demo"). A person would sign in at Access, again at AI-UI and again at Trellis unless a mechanism links them. A signed Access assertion verified by AI-UI is a fourth shape, with Cloudflare as the provider. It does not reach the school box or an offline box (header names and key location unverified here).

**Side by side.**

| | (a) RS256 + JWKS | (b) HS256 per client | (c) forward-auth |
| --- | --- | --- | --- |
| Rootstock code | about 500 | about 450 | about 50 |
| Trellis change | about 90 | about 90 | about 40 |
| Tinker server change | about 55 Rust | about 55 Rust | about 40 Rust, service Sprig only |
| Team box change | 2 clients, `WEBUI_URL`, split URLs | same | 2 proxy blocks, stripping, closed ports |
| Signing secret held by consumers | none | one each, signs for itself | none |
| Signing secret held by AI-UI | one private key | every client secret, recoverable | none |
| Public clients | yes | no | no |
| Rotation | JWKS overlap | per client, two-secret overlap | none to rotate |
| Revocation | at session end | at session end | next request |
| Availability coupling | sign-in and JWKS fetch | sign-in | every request |
| Reaches another box | yes | yes | no |
| Tool-server tokens | yes, audience-bound, public key | one secret per tool server | no |

**Recommendation: build (a), skip (b), and keep (c) for one narrow case.** The choice is Alexander's.

- (a) is the only option that cuts signing power to one process, reaches the Tinker library server wherever it runs, and gives tool servers a safe token. It costs about 500 lines inside `identity/`.
- (b) saves about 60 lines and gives up the one-way key, which is what makes (a) safe.
- (c) fits one case: a service Sprig that listens on loopback behind AI-UI's own service proxy. The proxy injects `X-Sage-User-*`, nothing else can reach the port, and no keys exist. That is about 20 lines. Do not put Caddy between Trellis and AI-UI: it ties every request to AI-UI, and any container on `sage-network` can forge the header.
- Authlib stays on the AI-UI side. Trellis may verify with PyJWT.

**Decide together with it.**

1. The public issuer name of each box. `WEBUI_URL` is empty in both snapshots, and `iss` cannot change once clients register.
2. The `email_verified` rule. Proposed: true for admin-added and provider-verified users, false for invite and sign-up users.
3. Consent. Proposed: skip it for first-party clients (Trellis, the Tinker library server) and show it for any other.
4. Outside clients. Proposed: a library server outside every box gets `sub` and nothing else.
5. Session length at each consumer, which sets revocation lag.

**Where the plan's SSO paragraph needs correcting.**

- "Tinker's server already models any OAuth2 provider" holds for the struct (`auth.rs:86-97`) and fails in `fetch_profile`, which knows two names (`:911-950`). `main.rs:66-82` builds two-argument providers. There is no PKCE (`:748-760`).
- "Public clients with PKCE for Tinker desktop": the desktop never speaks OAuth to a provider. The library server does (`auth.rs:3-18`). A public client waits for a design that removes the server.
- "`model_logins` … with a per-user key": a model login is a named, server-wide credential (`auth.rs:288-296,365-381,1111-1127`). A per-person key needs one row per person or a new column.
- "(b) … no rotation without re-issuing every secret": per-client secrets rotate one client at a time.
- Pointers: the shared-key risk now sits at `TODO.md:367`, not `:357`, under the card "AI-UI as the single sign-on for our other projects". "Signed reports" is Trellis `TODO.md:125` and `config/settings.py:109-114`, not AI-UI `TODO.md:361`.

**Census:** facts from `census/census-2026-10-23.json` (two databases: a 2026-07-12 production snapshot and a 2026-09-27 backup, both 3.1.0-era). Counts only. Both databases hold 32 users, 5 `admin` and 27 `user`. OpenAI-compatible connections: 6 in July and 7 in September, each with a key slot. Ollama is off with 1 base URL. There are 2 tool-server connections and direct connections are on. `ui.enable_community_sharing` is saved true. `ui.enable_user_webhooks` is true and `webhook_url` is empty. No OAuth provider is configured. API keys are on with no endpoint restriction and an empty allowlist. `webui.url` is empty and sign-up is off. Alembic head `b1c2d3e4f5a6` predates the privacy tables, so neither database says how many pseudonyms exist.
