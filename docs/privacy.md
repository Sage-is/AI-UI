# Privacy rules: the key, and rotating it

The privacy filter pseudonymizes what leaves for a hosted model and puts the real values back in what returns. Admins set it at `/pages/admin/privacy`. The design record is [decisions/2026-09-16-privacy-rules.md](decisions/2026-09-16-privacy-rules.md).

## Which connections it covers

- Every connection has a switch in the panel. The admin's switch wins, for a local connection as for an external one.
- A connection left on "instance default" is filtered when it is external and "Filter every external connection" is on, the default since 3.2.0.
- Local or external is the connection's own setting in Admin → Connections. OpenAI-style connections default to external and Ollama connections to local, so mark an Ollama on a hosted box as external.
- People's own direct connections share one switch, apart from the admin's connections.
- A per-model override beats any connection switch.
- The filter covers answers, reasoning and tool-call arguments, streamed or not.

## The key

- `PRIVACY_KEY` seeds every stand-in: each one is an HMAC of the real value under the key. Empty, it falls back to `WEBUI_SECRET_KEY`. With neither set and the filter on, a request is refused, never sent with guessable stand-ins.
- Give `PRIVACY_KEY` a value of its own and keep it in the vault. Rotating `WEBUI_SECRET_KEY`, which signs sessions, then leaves the stand-ins alone.

## What rotating the key does

- The box keeps a map of every real value it has replaced and the stand-in it used. A value already in the map keeps its old stand-in under a new key. Only values the box has not seen get stand-ins from the new key.
- Replies keep reversing: each request reverses only the stand-ins it sent itself.
- Chats are stored as people see them, with real values, so nothing visible depends on the map.

## When and how to rotate

Rotate when the key may have leaked. Someone who holds the key and a stand-in can test guesses, by computing the stand-in for each candidate value. A new key alone does not help, because the map keeps the old stand-ins, so rotate and purge together:

1. Put a new value in the vault and point `PRIVACY_KEY` at it. Restart the box.
2. In `/pages/admin/privacy`, purge the map with its confirmation. The purge is audited.
3. Check that the map is empty and that the test bench gives back what it was given.

The next request pseudonymizes every value afresh under the new key.
