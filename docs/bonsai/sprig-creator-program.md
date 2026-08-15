# Sprig Creator Program

For developers who want their app inside Sage.is AI-UI.

This page says what you can build today, what we are still building, and what it costs you. Where
something is not finished, it says so.

## What it costs you: nothing

We do not charge you to list. No listing fee. No submission fee. No annual developer fee. No charge to
be in the catalog.

If your Sprig points at a service you host, you meter that service however you like. Free tier, paid
tier, your call. We take nothing from it and we do not sit between you and your users.

Paid Sprigs sold through the store are a separate thing, and they are not built yet. When they land,
the terms will be written down before anyone is asked to agree to them.

## Four ways in

Pick the rung that matches what you have. Each one costs you more work and gives your users more.

### Rung 0 — Tool server

**Works today.**

Expose an OpenAPI endpoint. An admin adds it by URL. The assistant can then call your API mid-conversation
and work with what comes back.

What you write: an `openapi.json` and a stable HTTPS endpoint.

What to know: the call leaves the instance and reaches your server. Today a tool result renders as a
collapsed JSON block, so this is the assistant *using* your service, not your interface showing up.

### Rung 1 — Function

**Works today, first-party only for now.**

A Python `pipe` or `action` plugin that runs inside the instance. Functions receive an event emitter that
can drive the interface directly, which is powerful and is exactly why we are not taking third-party
Functions until the trust model is settled.

### Rung 2 — Hosted app Sprig

**Specified, not built.**

A real catalog tile backed by an endpoint you run. `delivery: service-endpoint` in the Sprig Spec covers
it, including bearer auth and health probing. The implementation is not finished — see `IMPLEMENTATION.md`
in the spec repo, divergence #9.

### Rung 3 — In-container Sprig

**The pipeline exists. Third-party listings are not open yet.**

Ship a `tar.zst` artifact. The operator's instance pulls it, checks a `sha256` pin, verifies your
signature, extracts it, and runs it on loopback. Nothing leaves the instance.

**You sign with your own key and the operator pins your public key.** That mechanism is already built —
`_signing_policy` resolves a per-entry `pubkey` ahead of our default. You do not sign with our key and we
do not hold yours.

## Where this is going: the app pane

Not built. Stated here because it is the point.

Sage.is already opens generated HTML apps in a side pane next to the chat. What the store should do is
open an *installed* app the same way: your app runs in the pane, the user works in it, and it reports
progress back to the assistant.

There is a technical reason the in-container version is the good one rather than just the private one. A
browser gives service workers, persistent storage, and offline caching only to a real origin. An app
served from inside the instance gets one. An app framed from another domain does not.

**So the version that works offline and the version that integrates properly are the same version.**

## Your code stays yours

Sage.is AI-UI is AGPL-3.0. It does not reach your code.

Every transport in the Sprig Spec crosses a real process boundary. Nothing links into the Rootstock's
address space. An operator running unmodified Sage.is with any number of proprietary Sprigs owes nothing
under section 13. Our Python SDK ships MIT for the same reason — so it cannot pull AGPL into your
codebase.

The one edge: a Sprig that bundles or statically links Rootstock source is a derivative work and must
respect the AGPL. Calling it across the boundary is not that.

Full reasoning: `sprig-spec/v1.md`, "License compatibility."

## What we ask you for

To run a pilot at rung 0:

1. A stable HTTPS endpoint and an `openapi.json`.
2. Your auth model — bearer token, and who issues it.
3. A plain-language note on what your endpoint receives, what it stores, and for how long.
4. Display name, one-line description, licence (an SPDX id or `proprietary`), and homepage.

Item 3 is not paperwork. Schools ask it first, and an answer we can hand to their IT reviewer is worth
more than a feature.

To be listed once third-party submissions open:

1. A publisher key and a stable publisher identity.
2. A `sprig.yaml` that conforms to `sprig-spec/v1.md`.

## What is not ready

Said plainly so nobody builds against it:

- **Third-party submissions are not open.** Admins can load a Sprig by ID. There is no public intake yet.
- **Paid Sprigs do not exist.** No checkout, no entitlements, no licence tokens.
- **`delivery: service-endpoint` is specified but not implemented.**
- **The app pane is not built.**
- **`docs/community-hub.md` describes a Community Hub that is not wired in this fork.** Ignore it.

## Talk to us

The fastest way in is rung 0 and a conversation. We are looking for design partners more than we are
looking for listings, because the store is still being shaped and the first apps in it will decide what
it becomes.
