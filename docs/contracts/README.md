# Contracts: how AI-UI, Trellis and Tinker.Click fit together

This page is the charter. Trellis and Tinker.Click link here and keep no copy. Decided by Alexander, 2026-11-12. Nothing on this page runs yet; the board card "Platform alignment" in `TODO.md` tracks the work.

## Roles on a box

| Product | Role | Owns | Never owns |
| --- | --- | --- | --- |
| AI-UI | The door, and the node | Sign-in, the privacy filter, model calls, credits, Spaces | Customer records, a second app builder |
| Trellis | The record | The append-only record with proof, scopes, the loop, verification | A user list, a provider key |
| Tinker.Click | The workshop | The app format, the bridge, the builder, the library, the gallery | Customer records, provider keys, identity |

Off a box, Tinker.Click runs as it does today, with its own sign-in, keys and node types.

## Decisions

1. **Sibling apps, one sign-in.** Each product keeps its own repo, image, database and address. Trellis does not become a Sprig.
2. **Each thing is built once.** One user list and one model route, in AI-UI. One record, in Trellis. One builder, library, app format and bridge, in Tinker.Click. No shared runtime code.
3. **One charter, here.** A contract moves to a BONSAI spec once a second consumer conforms.
4. **Fit is checked live.** AI-UI lists its contract versions in `/api/version`. Each sibling checks them and shows the result.
5. **Web Tinker is the real Tinker, minus desktop tools.** Tinker's own server runs the same interface, engine and library in a browser tab. It opens at its own address, linked from AI-UI and Trellis. AI-UI builds no builder of its own. The desktop app and every node type stay.
6. **AI-UI is the node; Tinker stores.** The person signs in to AI-UI. Tinker's server holds the library and runs the engine. Every model call goes through AI-UI as that person. No model key reaches the browser.
7. **Sign-in stays small.** A sibling sends the person to AI-UI, gets a one-time code back, and asks AI-UI server to server who that is. No JWT verification by siblings, no shared signing key, no separate identity server.
8. **The node work lands upstream.** Tinker.Click already ships a "Sage.is AI-UI account" node type. The work that makes it answer goes to Tinker's repo by pull request, never to a fork.
9. **It just works, and a remix never breaks it.** Stock screens need no setup. A remixed screen sits beside the stock one, which stays one click away. A broken remix harms nothing.

## The four contracts

| Contract | Owner | Promise | Written where |
| --- | --- | --- | --- |
| `sign-in` | AI-UI | A sibling learns who a person is by asking AI-UI, and gets a credential for calls made as that person. | `sign-in.md` in this folder, not yet written |
| `gateway` | AI-UI | Every model call goes through `/api/chat/completions`, never the raw routes. | [federation.md](../federation.md) |
| `node` | Tinker.Click | The server a Tinker client signs in to. On a box, AI-UI's address answers it by forwarding to Tinker's server. | Tinker's `docs/SERVER.md` |
| `bridge` | Tinker.Click | A built app in a sandboxed frame reaches only `ask`, `storage` and `connector`. It holds no key and has no network. | Tinker's repo |

## Security rules

1. The app holds no key. Only the bridge crosses the frame.
2. The bridge calls Trellis as the signed-in person, never with a shared bearer. Trellis's scopes decide what that person sees.
3. A write from an app is a claim. Only Trellis's own pages verify it.
4. Definitions travel; data stays. An app is scanned before it leaves the box.
