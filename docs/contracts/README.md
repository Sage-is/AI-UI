# Contracts: how AI-UI, Trellis and Tinker.Click fit together

This page is the charter. Trellis and Tinker.Click link here and keep no copy. It is Alexander's position, 2026-11-12. For AI-UI and Trellis it is decided. Tinker.Click's side is a proposal until agreed by the team. Nothing on this page runs yet; the board card "Platform alignment" in `TODO.md` tracks the work.

## Roles on a box

| Product | Role | Owns | Never owns |
| --- | --- | --- | --- |
| AI-UI | The door, and the node | Sign-in, the privacy filter, model calls, credits, Spaces | Customer records, a second app builder |
| Trellis | The record | The append-only record with proof, scopes, the loop, verification | A user list, a provider key |
| Tinker.Click | The workshop | The app format, the bridge, the builder, the library, the gallery | Customer records, provider keys, identity |

A box serves four addresses: AI-UI, Trellis, Tinker's interface, and a domain for built apps. The first three share one site, so a frame still carries Tinker's `SameSite=Lax` session cookie. Built apps get a registrable domain of their own, as Tinker's `docs/WEB-DESIGN.md` asks.

Off a box, Tinker.Click runs as it does today, with its own sign-in, keys and node types.

## Decisions

1. **Sibling apps, one sign-in.** Each product keeps its own repo, image, database and address. Trellis does not become a Sprig.
2. **Each thing is built once.** One user list and one model route, in AI-UI. One record, in Trellis. One builder, library, app format and bridge, in Tinker.Click. No shared runtime code. On a box AI-UI's credits count, and Tinker's metering is off.
3. **One charter, here.** A contract moves to a BONSAI spec once a second consumer conforms.
4. **Fit is checked live, both ways.** AI-UI lists its contract versions in `/api/version`, and Tinker's server lists its `node` and `bridge` versions. Each side checks the other's and shows the result.
5. **Web Tinker is a second client, at the phone's capability set.** Tinker's own server serves the same interface, engine and library in a browser tab, minus desktop tools. It opens at its own address. A Trellis page and AI-UI's Workshop tab can frame it, on the same site. The Workshop tab is decided after 2026-11-17; until then web Tinker opens in its own tab. AI-UI builds no builder of its own. The desktop app and every node type stay.
6. **AI-UI is the node; Tinker stores.** Tinker's server holds the library and runs the engine. Every model call web Tinker makes goes through AI-UI, and no model key reaches the browser. Calls made as each person wait on the `sign-in` credential; until then one node account carries every web user's calls. A desktop client may keep its own keys.
7. **Sign-in stays small.** A sibling sends the person to AI-UI, gets a one-time code back, and asks AI-UI server to server who that is. No JWT verification by siblings, no shared signing key, no separate identity server.
8. **The node work lands upstream.** Tinker.Click already ships a "Sage.is AI-UI account" node type. The work that makes it answer goes to Tinker's repo by pull request, never to a fork.
9. **It just works, and a remix never breaks it.** Stock screens need no setup. A remixed screen sits beside the stock one, which stays one click away. A broken remix cannot erase or rewrite the record: its writes are claims, and the record is append-only.

## The four contracts

| Contract | Owner | Promise | Written where |
| --- | --- | --- | --- |
| `sign-in` | AI-UI | A sibling learns who a person is by asking AI-UI, and gets a credential for calls made as that person. Its guards: a secret per sibling when it redeems a code, a redirect allow-list, a `state` value, codes that work once, sign-out that reaches every sibling, and a path for desktop and phone clients. | `sign-in.md` in this folder, not yet written |
| `gateway` | AI-UI | Every model call goes through `/api/chat/completions`, never the raw routes. | [federation.md](../federation.md) |
| `node` | Tinker.Click | The server a Tinker client signs in to. On a box, AI-UI answers `/v1/auth/*` and `/v1/model-login` itself, and forwards `/v1/rpc/*` to Tinker's server. `/v1/model-login` answers since 2026-11-17, behind `ENABLE_TINKER_NODE` ([federation.md](../federation.md)); the rest is not built. | Tinker's `docs/SERVER.md` |
| `bridge` | Tinker.Click | A built app runs in a sandboxed frame with no network of its own, but its scripts, styles and fonts may load from public CDNs. It holds no key. Everything else crosses `window.tinker`: `ask`, `storage`, `connector`, `tinker.fetch` to any address once the person allows it, and on the desktop files and `run`. On a box, an app that uses a connector gets no `tinker.fetch` and no CDN. | Tinker's `core/prompts/blocks/tinker-bridge.md` |

## Security rules

1. The app holds no key. Only the bridge crosses the frame.
2. Any call into Trellis made for a person runs as that person, never with a shared bearer. That holds for the bridge and for AI-UI's own tool server. Trellis's scopes decide what that person sees. Today AI-UI's tool server breaks this rule: Trellis's `scripts/aiui_register.py` registers it with one shared key.
3. A write from an app is a claim. Only Trellis's own pages verify it.
4. Definitions travel; data stays. An app is scanned before it leaves the box. Open: a connector's results copied into Tinker's `storage` or into a chat leave Trellis's scopes.
