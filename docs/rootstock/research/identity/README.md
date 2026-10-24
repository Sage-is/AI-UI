# identity survey: sessions, sign-in, roles, access

Pinned: aa25d9b + pending 3.2.1 paths

Backend paths start at `app/backend/sage_is_ai/`; other repos are named in full. Counted lines drop blanks and `#` comments, as the Rootstock budget test counts them. `(unverified)` marks what the host could not run: FastAPI, SQLAlchemy and Authlib are not installed on it. Board cards are cited by title because `TODO.md` lines move.

## Surface

**Routes: 58 across five files, plus 2 open helpers and 4 socket events.**

- `/api/v1/auths` has 23 routes in `routers/auths.py` (1,439 lines): session read, profile and password update, claim, LDAP, sign-in, sign-up, sign-out, add user, admin details, four admin-config pairs (settings, OAuth, LDAP server, LDAP switch), e-mail magic link send and verify, API key create, read and delete.
- `/api/v1/users` has 16 routes (`routers/users.py`, 567 lines), `/api/v1/groups` 10 (`routers/groups.py`, 310), `/api/v1/magic-links` 7 (`routers/magic_links.py`, 397).
- `/oauth/{provider}/login` and `/callback` sit in `main.py:2169-2182`.
- `GET /api/config` (`main.py:1909`) carries the sign-in flags and the `onboarding` hint. `GET /api/v1/sage/runtime/personas` is public while try.sage is on (`routers/sage_runtime.py:230`).
- Socket.IO authenticates in `connect`, `user-join`, `join-spaces` and `join-note` (`socket/main.py:249,281,310,331`).
- Guards: 176 `get_verified_user` in 25 files, 122 `get_admin_user` in 22, 17 `get_admin_or_facilitator_user` in 5, 10 bare `get_current_user` in 2.
- The pages layer has three guards of its own in `pages/auth.py` (136 lines): 38 routes admin-only, 9 workshop readers, 7 any signed-in user (`pages/router.py`).

**Tables: 4 own, 6 carry `access_control`.**

- `user` (12 columns), `auth` (4), `group` (10), `magic_link` (14). `user.email` and `auth.email` have no unique index. Only `api_key` and `oauth_sub` do. Production files carry the peewee shape, where `email`, `name`, `role`, `password` and `active` are NOT NULL (`internal/legacy_schema.sql:14-15,24-26,35`). The Alembic init migration builds the same columns nullable (`migrations/versions/7e5b5dc7342b_init.py:33,173,184-185`). `user.id` and `auth.id` share one uuid with no foreign key.
- `config` holds `auth.*`, `oauth.*`, `ldap.*`, `magic_link_login.*`, `ui.*`, `user.permissions` and `try_sage.reset.sessions_invalidated_at`.
- `access_control` JSON sits on `file` (no reader in `routers/files.py`), `knowledge`, `model`, `note`, `prompt` and `channel` (Spaces). It also sits inside each tool-server connection in `config` (`routers/tools.py:53-57`).

**Settings: 13 core, 62 per provider, 26 permission defaults, 13 env-only.**

- Core `PersistentConfig`: `JWT_EXPIRES_IN`, three API-key settings, `ENABLE_SIGNUP`, `ENABLE_LOGIN_FORM`, `DEFAULT_USER_ROLE`, `SHOW_ADMIN_DETAILS`, `ADMIN_EMAIL`, two pending-overlay texts, `USER_PERMISSIONS`, `TRY_SAGE_SESSIONS_INVALIDATED_AT`.
- Provider settings: 39 for OAuth (`config.py:297-678`), 17 for LDAP (`config.py:3118-3218`), 6 for e-mail magic link (`config.py:683-724`).
- 26 `USER_PERMISSIONS_*` env names feed one dict (`config.py:1266-1439`).
- Env-only: `WEBUI_AUTH`, three `WEBUI_AUTH_TRUSTED_*_HEADER`, `WEBUI_AUTH_SIGNOUT_REDIRECT_URL`, two auth-cookie and two session-cookie flags, `WEBUI_SECRET_KEY` with its deprecated alias, `TRUSTED_SIGNATURE_KEY`, `BYPASS_MODEL_ACCESS_CONTROL` (`env.py:112,368-417`).

**Credentials: four token kinds, three cookies.**

- Session JWT: HS256 on `WEBUI_SECRET_KEY`, claims `id`, optional `iat`, optional `exp` (`utils/auth.py:37-38,114-122`). It travels as `Authorization: Bearer` or the `token` cookie.
- Magic-link JWT: same key, claims `sub`, `type=magic_link`, `jti`, `exp`. E-mail links last 15 minutes (`routers/auths.py:1183-1186`). Persona links last 7 days by default (`utils/try_sage_seed.py:718-727`; `config.py:3286-3290`).
- Invite token: 43 random characters in `magic_link.token` (`models/magic_links.py:122`).
- API key: `sk-` plus 32 hex characters, one per user, plain text in `user.api_key` (`utils/auth.py:137-139`).
- Cookies: `token` (httponly, SameSite `lax`, Secure off by default, `env.py:401-417`), `oui-session` (Starlette session for OAuth state, `main.py:2160-2166`) and `oauth_id_token` (`utils/oauth.py:532-540`). The SPA also writes `localStorage.token`: 459 lines in `app/src` touch it, set at `app/src/routes/auth/+page.svelte:75,231`.

**Size today.**

- 14 backend files hold 5,275 lines, 4,041 counted: `routers/auths.py` 1,439, `utils/oauth.py` 548, `routers/users.py` 567, `models/users.py` 443, `models/groups.py` 406, `routers/magic_links.py` 397, `utils/auth.py` 346, `routers/groups.py` 310, `models/magic_links.py` 212, `models/auths.py` 210, `utils/access_control.py` 174, `pages/auth.py` 136, `utils/passwords.py` 49, `utils/facilitator.py` 38.
- try.sage persona seeding adds 970 lines (`utils/try_sage_seed.py`) and 330 (`routers/sage_runtime.py`). It stays legacy until F7.
- The SPA side is about 5,440 lines: `routes/auth` 980, `routes/join` 117, `components/admin/Users` 2,999, Settings Account 722, overlays 153, onboarding 148, API wrappers 321.

## What really runs

**1. A signed-in API call** (`utils/auth.py:152-346`).

1. The `check_url` middleware copies `ENABLE_API_KEY` onto `request.state` and parses the Authorization header a second time (`main.py:1469-1480`). Only the tool-server code reads that second parse (`utils/tools.py:80`; `routers/configs.py:135`).
2. `get_current_user` takes the Bearer credential, else the `token` cookie. No credential gives 403 "Not authenticated" (`utils/auth.py:158-167`).
3. A value that starts `sk-` takes the key path. Keys must be enabled (`:171`). The optional allowlist applies (`:176-192`). One lookup finds the user and one write stamps `last_active_at` (`:194,286-305`). Keys skip the cutoff.
4. Anything else is decoded as HS256. Every failure becomes `None`, then 401 (`:125-130,207-213,279-283`). A payload without `id` is refused (`:215`).
5. The try.sage cutoff compares `iat` with `TRY_SAGE_SESSIONS_INVALIDATED_AT`. A token with no `iat` counts as 0 and dies once a cutoff exists. The refusal deletes the cookie (`:222-242`).
6. `Users.get_user_by_id` loads the user. "Not found" and "database error" both return `None`, so both answer 401 (`:244-249`; `models/users.py:151-157`).
7. If a trusted e-mail header is configured and present, it must equal the user's e-mail. A mismatch deletes the cookies and fails 401 (`:251-264`).
8. A background task writes `last_active_at` (`:274-277`).
9. Route guards add the role test. `get_verified_user` accepts `user`, `admin`, `facilitator` and `temporary`, and answers 403 for an expired temporary account (`:308-328`). `get_admin_user` wants `admin`. `get_admin_or_facilitator_user` wants either (`:331-346`). A refused role answers 401.

**2. Password sign-in** (`routers/auths.py:593-685`).

1. With a trusted e-mail header configured, the e-mail comes from the header and the password is never read. An unknown address is created through `signup()` (`:595-620`). With `WEBUI_AUTH=False` the route signs in a fixed `admin@localhost` account (`:622-638`).
2. Otherwise `Auths.authenticate_user` finds the user by e-mail, loads the `auth` row with `active=True` and runs bcrypt (`models/auths.py:130-148`; `utils/passwords.py:34-49`). An unknown e-mail returns before any hash runs.
3. The route mints `{id, iat}` with an `exp` from `JWT_EXPIRES_IN`, sets the cookie, and returns token, `expires_at`, profile and merged permissions (`:642-683`). The default is `"-1"`: no `exp` and a session cookie (`config.py:288-290`; `utils/misc.py:355-356`).

**3. Sign-up and the first admin** (`routers/auths.py:693-811`).

1. Sign-up needs `ENABLE_SIGNUP` and `ENABLE_LOGIN_FORM` (`:696-703`). `ENABLE_SIGNUP` defaults on and `DEFAULT_USER_ROLE` defaults to `pending` (`config.py:1050-1064,1133-1137`).
2. The route counts users, lower-cases the e-mail, checks format, the 8-character minimum and the 72-byte maximum, hashes, then writes the `auth` and `user` rows in two separate transactions (`:710-747`; `models/auths.py:98-128`).
3. The first user gets `admin`. After that insert, the route sets `ENABLE_SIGNUP` false, which rewrites the whole config blob (`:720-722,792-794`; `config.py:198-208,230-235`). Both snapshots show sign-up off.

**4. OAuth** (`utils/oauth.py:338-548`).

1. Authlib's Starlette client runs the code flow and keeps state in the signed `oui-session` cookie (`main.py:2156-2182`). Four providers register from settings: Google, Microsoft, GitHub and a generic OIDC (`config.py:550-678`).
2. The callback reads `userinfo`, builds `provider@sub`, lower-cases the e-mail and applies `OAUTH_ALLOWED_DOMAINS` (`:359-421`).
3. It finds the user by `oauth_sub`, else by e-mail when `OAUTH_MERGE_ACCOUNTS_BY_EMAIL` is on, and then rewrites `oauth_sub` (`:424-433`). With OAuth sign-up on it creates the user. The first user, or the only user, becomes admin (`:95-103,456-493`).
4. It mints `{id}` with no `iat`, sets `token` as a session cookie, and redirects to `/auth#token=<jwt>`. The SPA copies that token into `localStorage` (`:511-548`; `app/src/routes/auth/+page.svelte:218-231`).

**5. Invites and temporary accounts** (`routers/magic_links.py`).

1. An admin or facilitator creates a `magic_link` row: random token, group ids, `max_uses`, `expires_at`, `account_duration`. A facilitator may name only groups it facilitates and only role `temporary` (`:48-75`; `models/magic_links.py:113-140`).
2. `POST /redeem` is public. It checks active, expiry and `use_count`, then creates a user with a synthetic `temp_<hex>@magic.local` e-mail and role `temporary`. It stores `info.temporary.expires_at`, adds the user to the listed groups, counts the use, may call a webhook, and returns a token with no `iat` and no `exp` (`:273-388`).
3. `get_verified_user` refuses the account once `expires_at` passes. A sweep every 5 minutes sets expired accounts to role `pending` (`utils/auth.py:315-326`; `main.py:532-545`).
4. `POST /claim` lets a temporary user attach a real e-mail and password. The role stays `temporary` until an admin approves (`routers/auths.py:213-308`).

**6. E-mail login links and try.sage personas.**

1. `POST /magic-link/send` signs a 15-minute JWT for an existing user and mails it over SMTP (`routers/auths.py:1165-1225`). The SPA reads `#magic_token=` and posts it to `/magic-link/verify`, which mints a normal session token with `iat` (`:1228-1292`; `app/src/routes/auth/+page.svelte:199-210`).
2. try.sage mints the same JWT at boot for five personas (admin, facilitator, three users) and lists the links publicly, by design (`utils/try_sage_seed.py:693-727`; `routers/sage_runtime.py:230-245`; `config.py:3346-3349`). A reset writes the cutoff (`utils/try_sage_seed.py:932`).

**7. Pages, sockets, `/api/config`.**

1. `pages/auth.py` calls `get_current_user` with the bearer slot empty, so pages read the cookie only (`:55-65`). A failure becomes a 307 to `/auth?next=<path>`. `require_admin_page` adds `role == "admin"`. `require_agents_reader` adds `workshop.models` from the saved permissions (`:105-136`).
2. Each socket event decodes the token itself and loads the user (`socket/main.py:253-277,283-299,312-327,333-342`). `/api/config` does the same with the cookie (`main.py:1912-1923`).

**8. Access checks.**

1. `get_permissions` starts from the saved `USER_PERMISSIONS`, ORs in every group the user belongs to, and fills gaps from the code defaults (`utils/access_control.py:28-76`). `has_permission` asks the groups first, then the defaults (`:79-114`). Groups grant. They never deny.
2. `has_access(user, "read"|"write", access_control)` is true when the user id or one of the user's groups is listed. `None` means public read and no write (`:137-153`). Callers add the admin and owner tests: 48 call sites in 18 files.
3. A facilitator gains access through `group.meta.facilitator_ids` (`:117-134`; `models/groups.py:192-268`).

## Edge cases worth keeping

Tags: **K** carry over, **F** fix as a logged intended diff, **D** dies with a cut. The shared harvest in `../edge-cases.md` holds the same traps under the same tags.

1. [F] **Three header parsers disagree.** `HTTPBearer` ignores a scheme that is not `Bearer`, so the cookie wins (`utils/auth.py:156-164`; unverified, FastAPI is not installed here). `get_session_user`, `check_url` and the audit middleware take any scheme (`routers/auths.py:102-108`; `main.py:1472`; `utils/audit.py:198`). With `Authorization: Basic …` plus a cookie, two layers hold two tokens.
2. [F] **Status codes run backwards.** No credential answers 403. A refused role answers 401 (`utils/auth.py:166-167,311-313,333-336`). The SPA and scripts may lean on both. Carry them through the parity run, then change them as a logged intended diff.
3. [F] **Tokens never expire by default.** `JWT_EXPIRES_IN` is `"-1"`, so no `exp` (`config.py:288-290`; `utils/misc.py:355-356`). Sign-out only deletes the cookie (`routers/auths.py:815-817`). A leaked token lives until the key rotates. March audit M5 (`docs/archive/audits/codebase-audit-2026-03.md:56`) found it. A search of the board finds no card.
4. [F] **The reset cutoff guards 1 of 7 session decode sites.** Sockets decode four times (`socket/main.py:267,287,315,336`), `/api/config` once (`main.py:1915`), `get_session_user` once (`routers/auths.py:109`). After a try.sage reset an old token still opens a socket and unlocks the signed-in `/api/config`. Keys skip the cutoff on purpose (`docs/try-sage-deployment.md:117`). Its `type != "magic_link"` clause is dead: a magic-link JWT has no `id` and fails first (`utils/auth.py:215,235`).
5. [F] **Five of eight session mints omit `iat`.** OAuth (`utils/oauth.py:511`), invite redeem (`routers/magic_links.py:369`), claim (`routers/auths.py:272`), LDAP (`:527`) and add user (`:904`). Redeem and add user omit `exp` too. Sign-in, sign-up and link verify keep `iat` (`:648,755,1260`). The plan names two of the five.
6. [F] **A busy database reads as a bad token.** `get_user_by_id` swallows every exception (`models/users.py:151-157`), so 401. The file has 16 such handlers; the lookups by key, name, e-mail and `oauth_sub` share the flaw (`:164-188`). Sign-in turns a lock into "invalid credentials" (`models/auths.py:133-148`). Board card: "A busy database reads as 'session expired'".
7. [F] **Every call writes `last_active_at`.** A JWT call schedules the write; a key call writes inline (`utils/auth.py:274-277,303`). Under one SQLite writer, reads cost writes. Throttle it to once a minute.
8. [F] **The `sk-` allowlist fails open.** With restrictions on, an empty list or a trailing comma yields an empty entry, and `path.startswith("" + "/")` is true for every path (`utils/auth.py:176-192`). The same expression run on plain strings on 2026-10-23: `""`, `" "` and `"/api/models,"` all allow `/api/v1/users/`. `docs/federation.md:95-99` recommends this setting. No card.
9. [K] **Keys act as their owner.** The `sk-` branch returns the user at once and guards stack on top (`utils/auth.py:194-204`). One key per user, 122 bits, plain text in `user.api_key`, readable again by `GET /api/v1/auths/api_key` (`utils/auth.py:137-139`; `routers/auths.py:1404-1439`). One of 32 census users holds one. Keep the `sk-` prefix and the owner rule. Store a hash for new keys.
10. [F] **The signing key has a public default.** `WEBUI_SECRET_KEY` falls back to `t0p-s3cr3t`, and the guard tests only for empty (`env.py:390-395,419-420`). `start.sh` makes and persists a real key first (`app/backend/start.sh:120-185`), so only runs outside it fall back. The same key signs sessions, the `oui-session` cookie and, while `PRIVACY_KEY` is unset, the privacy pseudonyms (`main.py:2160-2162`; `privacy/hooks.py:41-43`). March audit C1 (`docs/archive/audits/codebase-audit-2026-03.md:23`).
11. [K] **Sign-up closes after the first admin, and the count is racy.** `ENABLE_SIGNUP` goes false when `user_count == 0` (`routers/auths.py:710,720-722,792-794`). The count and the insert are separate steps, so two first sign-ups can both become admin (read, not run). OAuth and LDAP carry their own copies of the rule (`utils/oauth.py:95-103`; `routers/auths.py:491-497`), and `/api/config` a fourth hint (`main.py:1925-1930`). Keep the rule. Make the insert conditional and put it in one place.
12. [F] **Bad sign-up input answers 500.** The 400s for a short or long password sit inside a `try` that ends in `except Exception`, which rewrites them as "An internal error occurred during signup." (`routers/auths.py:719-738,809-811`; read, not run). The password spec tests only `/update/password` (`app/cypress/e2e/auth-password-policy.cy.ts:20-50`).
13. [F] **The password rules hold in three of five places.** Sign-up, change and claim enforce 8 characters and 72 bytes (`routers/auths.py:191-194,239-242,727-738`). Add user and the admin user update enforce neither (`:893-901`; `routers/users.py:500-503`). bcrypt cuts at 72 bytes (`utils/passwords.py:25`), so a longer password accepts any tail.
14. [K] **Password hashes.** bcrypt at 12 rounds. `$2a$` and `$2y$` verify. A stored value that is not bcrypt fails the check and does not raise (`utils/passwords.py:16-49`; `utils/test_passwords.py`). The census does not record the prefix mix (unverified).
15. [F] **No throttle, and a timing tell.** No rate or lockout code exists in the auth files (searched `routers/auths.py`, `utils/auth.py`, `models/auths.py`, `main.py`). An unknown e-mail returns before any hash runs, so response time shows which addresses exist (`models/auths.py:133-135`).
16. [F] **E-mail is unique by habit.** Every entry point lower-cases and looks up before it inserts. The database has no unique index in either schema shape (`internal/legacy_schema.sql:14-15,24-26`; `migrations/versions/7e5b5dc7342b_init.py:33,173`). `validate_email_format` accepts `a@b.c d@e.f` and a trailing newline (`utils/misc.py:310-314`; run 2026-10-23).
17. [D] **`auth.active` is read and never written.** Sign-in filters on it (`models/auths.py:139,166`). Nothing sets it false and the session path never reads it. All 32 census rows hold 1.
18. [K] **Trusted-header sign-in.** `WEBUI_AUTH_TRUSTED_EMAIL_HEADER` makes `/signin` trust any request that carries the header, with no secret. A new address goes through `signup()`, so closed sign-up blocks every header user after the first. Groups sync only for a non-empty header and a non-admin. Password change is refused (`routers/auths.py:185-186,595-620`; `utils/auth.py:251-264`). The federation note decides its fate.
19. [K] **Five roles in one free-form string.** `admin`, `user`, `pending`, `temporary`, `facilitator`. The column is a plain `String` (`models/users.py:27`). `get_verified_user` admits four and answers `pending` with 401 (`utils/auth.py:309`). The admin config takes `pending`, `user`, `admin` or `facilitator` as the default role and ignores anything else without an error (`routers/auths.py:1019-1020`). The plan counts four roles.
20. [F] **`role == "user"` guards 11 model-access sites.** `/api/models`, `check_model_access`, the chat and embedding paths and the OpenAI and Ollama routes test it, so facilitator and temporary accounts see and call every registered agent (`main.py:1673,1742`; `utils/chat.py:219`; `utils/embeddings.py:66`; `routers/openai.py:731,932`; `routers/ollama.py:544,1375,1481,1564,1659`). `routers/chats.py:68,353` do the same for two chat rules. The tests date from when only `user` and `admin` existed (inferred). The trial box has both newer roles.
21. [F] **Any facilitator can edit or delete any Space, and a Space's `write` list is never read.** Both routes take `get_admin_or_facilitator_user` and call no access check (`routers/spaces.py:136-153,161-174`). Reads do check (`:62-74`), and posting needs only read access (`:543-557`). All 3 census Spaces carry a `write` list.
22. [F] **A facilitator can promote to facilitator.** The comment says it cannot. The code blocks only `admin` (`routers/users.py:450-461`).
23. [F] **Temporary accounts expire in one place and not in `/add`.** The expiry test sits in `get_verified_user` only (`utils/auth.py:315-326`). Invites set `info.temporary.expires_at` (`routers/magic_links.py:323-334`). `/add` does not, so a facilitator's temporary account never expires (`routers/auths.py:895-901`). `/add` also returns a token with no `iat` and no `exp` for the new account (`:904-913`). A claim keeps the role `temporary`, so the sweep demotes it unless an admin upgrades it first (`:249-264`; `main.py:532-545`).
24. [K] **The permission tree has 26 keys and the server enforces 7.** `workshop` 4, `sharing` 4, `chat` 13, `features` 5 (`config.py:1398-1433`). Server checks exist for `features.notes` (6 calls), `chat.delete` (3), `workshop.models` (2), `workshop.prompts`, `workshop.knowledge`, `features.direct_tool_servers` and `chat.share`: 15 calls in 8 files. Only the SPA reads the four `sharing.public_*` keys. The panel advertises 19 policies the server never applies. The board names the pattern in "The direct-connections admin toggle is advisory, not enforcing".
25. [D] **Retired `workspace.*` keys sit in saved config.** Both snapshots hold `workshop.*` (all false) beside `workspace.*` (models and knowledge true). Group permissions hold 8 `workspace.*` leaves and no `workshop.*`. Nothing reads `workspace` (`app/cypress/e2e/permissions-drift.cy.ts:47-50`). `POST /users/default/permissions` replaces the dict and drops them (`routers/users.py:274-279`). Do not migrate them: that would grant access nobody has today.
26. [K] **`access_control` semantics.** `None`: everyone reads, only the owner writes. `{}` or a missing key: the owner only. Lists of user ids and group ids grant. A facilitator reads through the groups it facilitates (`utils/access_control.py:117-153`). Callers test owner and admin themselves, so 48 call sites in 18 files repeat the triple.
27. [F] **Group membership is a JSON list matched by `LIKE`.** `get_groups_by_member_id` casts the list to text (`models/groups.py:126-139`). `add_users_to_group` appends in place to a plain `JSON` column (`:357-376`). SQLAlchemy does not track that (unverified, not installed here), so a non-empty group may keep its old members only. Invite redeem relies on it (`routers/magic_links.py:336-339`). No Cypress spec calls the group or magic-link routes (searched `app/cypress/e2e` and `support`).
28. [F] **Deleting a user removes chats and group membership only.** Every other table with a user column keeps its rows: files, folders, functions, knowledge, memories, messages, models, notes, prompts, Spaces, tags, feedback, shares, invites, bridges, privacy (`models/users.py:375-392`; the `user_id`, `created_by` and `shared_by` columns in `models/`). The oldest user by `created_at` can be neither deleted nor demoted (`routers/users.py:463-487,537-550`).
29. [F] **OAuth merges by e-mail and never reads `email_verified`.** With `OAUTH_MERGE_ACCOUNTS_BY_EMAIL` (default True, on in both snapshots) a matching e-mail links the identity and rewrites `oauth_sub` (`utils/oauth.py:424-433`; `config.py:304-308`). One column holds one provider (`utils/oauth.py:370`; `models/users.py:38`). Board card: "OAuth identity linking v1".
30. [K] **OAuth first-user and only-user rules.** The first user becomes admin, and a sole user is re-promoted on every login. With role mapping on, a login whose claims match nothing resets the role to the default, admin included (`utils/oauth.py:95-150`). Role and group mapping are off in both snapshots.
31. [F] **OAuth leaves secrets in logs and URLs.** It logs the whole token response and the user info (`utils/oauth.py:363,368,411,419`). The JWT rides the URL fragment into `localStorage` (`:546`). The `oauth_id_token` cookie has no expiry and can pass the 4 KB cookie limit (`:532-540`). Board card: "Secrets in logs: an OAuth token response, and a dead API-key method".
32. [F] **Open redirect after sign-in.** `?redirect=` goes straight into `window.location.href` (`app/src/routes/auth/+page.svelte:80,106`). `redirect=javascript:…` runs script and `redirect=https://…` leaves the site. March audit H1 (`docs/archive/audits/codebase-audit-2026-03.md:34`). No card. The pages bridge sends `?next=`, unencoded, and the SPA reads only `redirect` for the destination (`pages/auth.py:58-63`; `app/src/routes/auth/+page.svelte:80,300`).
33. [F] **Invites race, and two columns do nothing.** The `use_count >= max_uses` test and the increment are separate steps, and the increment is read-then-write (`routers/magic_links.py:297,342-346`; `models/magic_links.py:177-189`). `magic_link.role` and `.meta` have no reader: redeem hard-codes `temporary` (`routers/magic_links.py:314`). The webhook posts to a URL a facilitator typed (`:349-367`). March audit M4 and H3 (`docs/archive/audits/codebase-audit-2026-03.md:55,36`).
34. [K] **E-mail and persona links are stateless.** The JWT holds `type=magic_link`, `sub` and a `jti` that nothing records, so it works until it expires. `verify` never checks `ENABLE_MAGIC_LINK_LOGIN`, and the try.sage persona links depend on that (`routers/auths.py:1183-1186,1228-1245`; `utils/try_sage_seed.py:693-727`). The mailed link is relative while `WEBUI_URL` is empty, as it is in both snapshots (`routers/auths.py:1188-1189`; `config.py:1047`).
35. [F] **Admin reads return stored secrets.** `GET /admin/config/oauth` returns the client secrets and the SMTP password in clear (`routers/auths.py:1088-1107`).
36. [K] **Config precedence.** A saved value beats the env default, but a saved empty string counts as unset. Clearing a secret in the admin form revives the env value at the next boot (`config.py:168-172`).
37. [D] **Dead and broken code.** `verify_signature` hands a `str` key to `hmac.new`, so it always returns False (run 2026-10-23), and nothing calls it (`utils/auth.py:45-58`). `extract_token_from_auth_header` has no caller (`:133-134`).
38. [F] **The audit middleware miscalls `get_current_user`.** It passes the credential into the `background_tasks` slot, so the call reads the `Depends` default, raises, and the audit logs no user (`utils/audit.py:193-203`; `utils/auth.py:152-157`; stand-in run). The default level is `NONE` (`env.py:596`), so it hides.
39. [F] **The pages guards drift.** `require_page_user` serves 7 routes, not the one its docstring names. It admits `pending` users and expired temporary accounts, because it skips `get_verified_user` (`pages/auth.py:68-84`; `pages/router.py:160,908,940,969,998,1015,1033`).
40. [K] **Onboarding doors stay open until the first user.** `/api/config` reports `onboarding` while the user table is empty (`main.py:1925-1930`). `POST /api/v1/utils/db/restore` takes no auth in that state (`routers/utils.py:206-221`). CORS reflects any origin with credentials by default, and only SameSite `lax` shields the cookie (`config.py:1538`; `main.py:1502-1508`; `env.py:401`). Secure is off unless `WEBUI_AUTH_COOKIE_SECURE` is set (`env.py:411-417`; audit M7, `docs/archive/audits/codebase-audit-2026-03.md:58`).

41. [F] **Every second copy of a check, in one list.** Session decode: 7 sites (`utils/auth.py:208`, `routers/auths.py:109`, `main.py:1915`, `socket/main.py:267,287,315,336`). Header parse: 3 (`utils/auth.py:152-164`, `routers/auths.py:103`, `main.py:1472`) plus the audit call. Cookie write: 9. First-admin rule: 3 and a hint. Password rules: 3 of 5 places. Access triple: 48 `has_access` sites and 13 `role == "user"` tests. Permission tree: the config table, the Pydantic panel models (`routers/users.py:197-253`) and two readers that differ, `get_permissions` and `has_permission` (`utils/access_control.py:28-114`). Page guards: 3. One module each replaces them, and the parity corpus below pins the result.

## Ceremony to drop

Counts are raw lines from `wc -l` or the ranges named.

- LDAP: `routers/auths.py:314-585` (272) and `:1295-1395` (101), `config.py:3118-3218` (101), 17 settings, `LdapForm` (`models/auths.py:67-69`), the `ldap3` pin (`app/backend/requirements.txt:127`) and the SPA's LDAP mode. Both snapshots show LDAP off. About 475 Python lines.
- `WEBUI_AUTH=False`: `routers/auths.py:622-638` and `:704-708`, `config.py:1053-1057`, `main.py:1945`, `env.py:368,419-420`, and the SPA's `features.auth === false` branches. No script, gate or CLI sets it (searched `scripts/`, `Makefile`, `cli/`). About 30 lines.
- Dead code: `verify_signature` with `TRUSTED_SIGNATURE_KEY` (15), `extract_token_from_auth_header` (2), `Auths.authenticate_user_by_api_key` (`models/auths.py:150-160`, 11, logs the key), the licence fetch (`utils/auth.py:61-108`, 48, already left out by the plan) with `LICENSE_KEY` (`main.py:630-631`), the unreachable `except` around `decode_token` (`utils/auth.py:207-213`; `main.py:1914-1921`) and the repeated expiry test (`routers/auths.py:116-120`).
- Provider code: `load_oauth_providers` with its Microsoft and GitHub blocks (`config.py:550-678`, 129 lines), role and group mapping (`utils/oauth.py:95-291`, 197 lines, 8 settings) and the profile-picture fetch (`:293-336`, 44 lines). Neither snapshot configures a provider. The trial instance does sign in through SSO (board card "Security fixes, AI-UI woken for them"), provider unrecorded: confirm it before the cut.
- E-mail login mail: `send`, its form and the SMTP block (`routers/auths.py:1157-1225`, 69 lines; `config.py:683-724`, 42 lines; 6 settings). Keep `verify`, because persona links need it. The invite `send` through bridges (`routers/magic_links.py:143-232`, 90 lines) leaves with the bridges Sprig.
- Admin forms: the settings and OAuth config pairs (`routers/auths.py:959-1147`, 189 lines) give way to the generated settings form. The Pydantic copy of the permission tree (`routers/users.py:197-253`, 57 lines) is generated from the table. The 26 `USER_PERMISSIONS_*` env names go (`config.py:1266-1395`).
- Second copies: `get_session_user`'s parse, the `/api/config` parse, four socket parses, `check_url`'s parse, the pages guards and the audit call. One function replaces them.

## Rootstock equivalent

**Modules in `identity/`, against the 1,750-line cap.** Legacy is 4,041 counted backend lines plus about 5,440 SPA lines. Estimates, counted the budget way.

| Module | Replaces | Lines |
| --- | --- | --- |
| `session.py` | `utils/auth.py:114-346`, the 7 decode sites, `pages/auth.py`, 9 cookie writes | 150 |
| `access.py` | `utils/access_control.py`, `utils/facilitator.py`, 48 `has_access` sites, 15 permission calls | 140 |
| `signin/password.py` | sign-in, sign-up, add, claim, change (adapted `passwords.py` sits outside the budget) | 130 |
| `signin/links.py` | invites, e-mail login and personas in one table | 150 |
| `signin/oauth.py` | `utils/oauth.py` and the four provider blocks: one OIDC client, Google as a preset | 150 |
| `users.py` | user, group, facilitator and key ops | 270 |
| `sso/` | option (a) of `../federation/README.md` | 500 |
| Logic total | | 1,490 |

The screens have no owner in the plan's table: sign-in, join, account, users, groups, invites, consent. Legacy spends about 4,500 SPA lines on them (`routes/auth` 980, `routes/join` 117, `components/admin/Users` 2,999, Settings Account 722). At 30 to 100 lines a Jinja2 page, seven pages add about 450. The total is near 1,940 with (a) and 1,490 with (c), which swaps `sso/` for a 50-line verifier. `design.md` should raise `identity/` to about 1,950 out of the 860 lines by which the caps exceed the 13,000 total, or move the screens to `shell/`.

**Tables.** Legacy `user`, `auth`, `group`, `magic_link` and `config` become unmanaged models. New `rs_*` tables:

- `rs_identity(user_id, provider, subject)`, unique on the pair. It lifts the one-provider limit. `user.oauth_sub` stays readable as a fallback and is never written.
- `rs_signin_link(kind, token_hash, created_by, role, group_ids, max_uses, uses, expires_at, account_seconds, active)`. The census holds 0 invite rows, so nothing moves. A use is `UPDATE … SET uses = uses + 1 WHERE uses < max_uses`.
- `rs_api_key(user_id, hash, prefix, ops, label, last_used_at, revoked_at)`. The one legacy `user.api_key` stays valid until its owner rotates it.
- `rs_user_state(user_id, email_verified, expires_at, password_changed_at, last_active_at)`. A side table, so the core never alters `user`. Temporary expiry leaves `user.info.temporary`. `last_active_at` is written once a minute.
- `rs_oauth_client`, `rs_oauth_code`, `rs_oauth_token`, `rs_signing_key` for options (a) and (b) only.
- Sessions move to Django's `django_session` at F2. A try.sage reset then deletes sessions, and the `iat` cutoff dies with the HS256 cookie.

**Ops.** About 26 of the plan's 95: `whoami`, `sign_in`, `sign_out`, `sign_up`, `claim`, `password_change`, `user_add`, `user_get`, `user_list`, `user_update`, `user_delete`, `key_make`, `key_list`, `key_revoke`, `group_list`, `group_save`, `group_delete`, `group_members`, `link_make`, `link_list`, `link_revoke`, `link_redeem`, `providers`, `sso_client_save`, `sso_client_list`, `sso_client_delete`. Seven of the plan's 15 fixed-contract routes go here under (a) or (b): `/oauth/<provider>/login` and `/callback`, which providers hold, and the five OIDC endpoints.

**Routes that keep their legacy JSON.** Callers outside the SPA use them today. `POST /api/v1/auths/signin` and its body (`docs/API-examples.md:24-45`), `GET /api/v1/auths/` (Trellis link check, `crm/loop/aiui.py:54` in the Trellis repo), `POST /api/v1/auths/add` and `GET|POST /api/v1/auths/api_key` (Trellis `scripts/aiui_setup.py:80-101`), `POST /api/v1/auths/signup`. Each becomes an alias of an op that returns the same JSON.

**Identity parity corpus (F0).** Each row runs through `utils/auth.py` and `session.py`. Both must agree on status and user.

1. No credential: 403.
2. A valid Bearer, a valid cookie, and both with different users: Bearer wins.
3. `Authorization: Basic x` plus a valid cookie: the guard reads the cookie and `get_session_user` reads the header (unverified, `HTTPBearer` not run). One rule after.
4. Wrong signature, `alg: none`, expired `exp`, no `id`, unknown user id: 401.
5. Cutoff set, `iat` older, equal, missing: 401, accepted, 401.
6. `sk-` unknown: 401. Keys off: 403. Restrictions on with a listed path, a path under it, another path, an empty list.
7. `pending` on a verified route: 401. `temporary` live: accepted. `temporary` expired: 403. `facilitator` on an admin route: 401.
8. Trusted header equal, different, absent.
9. A magic-link JWT sent as a session: 401. A token signed with the previous key: 401.
10. Database locked at the user lookup: 401 today, 503 intended.

The access corpus crosses `access_control` of `None`, `{}`, a user list, a group list and both, with six callers: owner, listed user, group member, facilitator of a listed group, admin, stranger, for `read` and `write`. `has_access` and `can()` must agree, except where `intended-diffs.toml` says otherwise.

**Order of work against the cutover table.**

- `session.py` and `access.py` land in F0 and F1, not F2. F1's `/workshop/*` and `/api/v1/{models,prompts}` already need `workshop.models`, `access_control` and facilitator scope (`routers/models.py:30-44,68-70`; `pages/auth.py:105-118`). Group reads land with them.
- The four socket decodes call the shared parser from F0, so the cutoff and the role tests reach them (`socket/main.py:267,287,315,336`). F4 moves the events later.
- F2 reads and writes the same `config` row for the cutoff and accepts the legacy persona JWT, because the try.sage seed stays legacy until F7 (`utils/try_sage_seed.py:693-727,932`).
- Legacy routers keep importing `utils/auth.py` until F8. The corpus runs on every release until then.

**Decisions for `design.md`.** Alexander's SSO choice is separate (`../federation/README.md`).

- Cut LDAP and `WEBUI_AUTH=False`.
- Keep five roles. Write `can()` against capabilities, not `role == "user"`.
- Enforce all 26 permission keys or prune the 19 the server ignores.
- Give new sessions an `exp` and pick the default. Existing `"-1"` tokens keep working until F2.
- Show an API key once, at creation. That changes Settings, Account.
- Set `email_verified` by policy: false for `@magic.local` addresses and for sign-up without proof, true for admin-added users. Merge-by-e-mail and option (a) both need it.
- Keep or drop SMTP login.

**Census:** facts from `census/census-2026-10-23.json` (two databases: a 2026-07-12 production snapshot and a 2026-09-27 backup, both 3.1.0-era). Counts only. Both databases hold 32 users: 5 `admin` and 27 `user`, no `pending`, `temporary` or `facilitator`. `user.api_key` is set on 1 of 32 and `oauth_sub` on 0 of 32. `auth.active` is 1 on 32 of 32. `magic_link` has 0 rows. There are 3 groups and 3 Spaces, each Space with an `access_control` dict holding `read` and `write`. `channel_member` and `chat_share` have 0 rows. Users active in 7, 30 and 90 days: 3, 7, 8 in July and 3, 5, 5 in September. Saved config: sign-up off in `ui` and `oauth`; `merge_accounts_by_email` on; Google and GitHub ids and secrets empty; LDAP off; e-mail magic link off; API keys on, endpoint restrictions off, allowlist empty; `webui.url` empty; `auth.jwt_expiry` saved, value not recorded. Saved `user.permissions` holds `workshop.*` all false and `workspace.*` with models and knowledge true. Group permissions hold 8 `workspace.*` leaves and no `workshop.*`. Both snapshots sit at Alembic head `b1c2d3e4f5a6`, before the privacy tables.
