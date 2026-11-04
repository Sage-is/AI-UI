---
title: "The box network"
description: "A proposal for interoperable boxes, shared invites, vetted hosts, and a network pool."
date: 2026-11-03
tags:
  - federation
  - network
  - growth
---

# The box network

Proposal, 2026-11-03, written be Alexander and Izzy's for team review.

AI-UI side: Alexander decides. Tinker.Click side: a proposal until the Tinker.Click team agrees. Nothing here is built.

## The idea

AI-UI boxes and Tinker.Click library servers ("nodes") form one network and work together. Boxes differ in capacity. Invite codes let people try a box, and the network encourages them to move up to a managed box. Hosts who run boxes in the network can earn from them, and they add invites to one shared pool.

Alexander has answered two questions. A self-hoster's box may join as a host once the team vets it. The network sets a minimum seat price, and hosts price at or above it, plus allow n free seats.

## What others call these things

| Who | Place | Invite | Money |
| --- | --- | --- | --- |
| Discord | "server" | invite link: expiry from 30 minutes to never, a use limit; a server-wide vanity link at Boost Level 3 | Many Options: [Boosts unlock server perks and pay the owner nothing; Server Subscriptions range $2.99 to $199.99 a month, up to three tiers, owner keeps about 90% (launch coverage and guides; US creators only)](https://memberful.com/blog/how-to-monetize-a-discord-server) |
| Minecraft | "server" or "network"; Realms is Mojang's own small managed tier | (not researched) > #TODO | hosts sell plans by RAM and player slots: Shockbyte from $4 (1 GB, 8 slots) to $64 (16 GB); usage guidelines allow cosmetic sales only, no pay-to-win; a breaking server can be blacklisted |
| Mastodon | "server" or "instance" | three sign-up modes: open, approval, invite-only; invite links limited by time and number of sign-ups, and they work while sign-up is closed | managed hosting such as Masto.host from about $6 a month |
| Bluesky (AT Protocol) | PDS, Personal Data Server; an account can move from one PDS to another | in the beta: codes per account on a schedule (about one every two weeks), bonus codes when invitees posted well | codes were resold for $10 to $50; outsiders cracked the generator; invites later ended |
| Lobsters | — | a public invite tree: who invited whom; the inviter answers for invitees | — |
| Nextcloud | "provider" | Simple Signup: email and password, a free account of 2 to 5 GB at a vetted provider; the email goes to the provider, not to Nextcloud | paid upgrades fund the free accounts |
| PikaPods | "pod", managed open-source hosting | — | app maintainers can get 10 to 15% of what their app earns |
| Matrix | "homeserver"; matrix.org lists hosts without endorsing them | — | Element Server Suite: free Community edition (AGPL), Pro priced per seat from 100 users |
| Storj | "node operator" | — | paid monthly in USDC per use (storage per TB-month, egress); a payout minimum; new nodes once had part of their pay held back (older terms, unconfirmed today) |
| Vast.ai | "host" | — | hosts set their own prices; verified hosts cost more (H100 about $1.50-1.87/h vs $0.90 unverified, third-party reviews); verification is automated, a "Secure Cloud" filter shows ISO 27001 hosts |
| Akash | "provider", "tenant", "lease" | — | auditors sign provider attributes; tenants pick audited providers; take rate reported between 4% and 20% (sources conflict) |
| Home Assistant | Nabu Casa runs the paid cloud | — | most subscription profit funds the nonprofit Open Home Foundation, which owns the code |
| Web hosting | "reseller", "white label" | — | a reseller sells a provider's hosting under its own brand |

## Our words

- **Box:** any running AI-UI or Tinker.Click server. Already the word in both federation docs (`docs/federation.md`, Tinker's `docs/FEDERATION.md`). Keep it.
- **Network:** the boxes that share one directory, one sign-in and one pool.
- **Seat:** one person's place on a box. A box's capacity is seats times model budget, plus storage. Model calls cost money, unlike Minecraft RAM.
- **Host:** the person or team that runs a box in the network.
- **Steward:** the network's operator (Sage.is and the team): directory, vetting, pool, the floor price.

Industry words include self-hosted, managed, hosted; instance, node, operator, provider, host. "Fully managed" means updates, backups and migrations are handled for you. Plans are sold by capacity: RAM and slots (Minecraft), seats (Element), storage (Nextcloud).

## Roles

The two axes stay apart: the network axis says who you are to the network; the box axis says what you may do inside one box. AI-UI already has these box roles: admin, facilitator, user, temporary. Magic links already create `temporary` accounts.

Three shapes for the network axis:

- A. Three roles: guest, member, host. Simple; fits a ladder.
- B. Four: guest, member, host, steward. Names the network's own job, which governance needs.
- C. Hosts in two kinds: managed host (the steward runs the box; the host owns the members and the relationship) and vetted host (the host runs the box; the team vetted it). Vast.ai shows verified and unverified hosts side by side, priced apart; Akash lets tenants pick audited providers.

Recommendation: B for the people, with the two host kinds of C.

- **Guest:** a trial seat with an end date and a model budget. On the box axis: `temporary`.
- **Member:** a seat that stays, paid or sponsored. Box axis: `user`.
- **Host:** runs a box in the network. Box axis: `admin`. Managed host or vetted host.
- **Steward:** runs the directory, vetting, the pool and the floor price.
- **Independent:** anyone may run the AGPL software outside the network. No listing, no pool. Vetting turns an independent box into a vetted host.

Why: the box axis exists and works today, so the network adds only one word per step. "Host" pairs with "guest". A Tinker.Click maker is a member of a box, so the same words serve both products.

The ladder: guest, then member, then own box (managed), then host. An independent box joins at host through vetting.

## Code names

Today's draft names: "trial seat" (a code) and "pilot request" (a code). Research:

- "Invite code" signals gated access: launches, betas, waitlists; often time-bound.
- "Referral code" signals an ongoing reward to the person who referred.
- "Guest pass" signals a single-use grant a member hands to someone; fitness studios use it, and a third-party blog describes a seven-day guest pass on a paid AI plan.
- Discord and Mastodon say "invite link".
- B2B says "pilot" for a trial of a managed service.

Recommendation: neither draft name.

- **Guest pass:** opens a guest seat on a box for a set time. Handed out by a member, a host, or the pool. Pairs with host and guest.
- **Referral code:** opens nothing. It credits whoever sent a person, on the pilot form or at sign-up.
- "Pilot" stays as the word for the sales path to a managed box. It is a form, not a code.
- "Invite" stays the plain umbrella word in copy ("invite a friend").

One mechanism under both: AI-UI magic links already carry `max_uses`, `expires_at`, `account_duration`, `role`, `group_ids`, `meta` and `webhook_url`. A guest pass is a magic link with a `temporary` role. A referral code is a link or code whose `meta` names the sender and opens no seat.

The pass records who issued it. That builds an invite tree like Lobsters', so a guest who later books a pilot carries the referral by default.

Tinker.Click option for the team: the planned one-wave opening after the waitlist videos could go out as guest passes.

## Vetting: a host Guarantee

The Mastodon Server Guarantee lists servers on joinmastodon.org only when they commit to four things: active moderation against racism, sexism, homophobia and transphobia; daily backups; at least one other person with emergency access; at least 3 months' warning before shutting down, so people can export and move.

Nextcloud's Simple Signup sends people only to vetted providers.

Draft host Sage.is/Guarantee (proposal, every item open to change):

1. A supported AI-UI or Tinker.Click release, updated within the network's window after a security release.
2. The privacy filter on for every external connection. Never off for guests.
3. Daily encrypted backups, with a tested restore.
4. A second person with emergency access.
5. At least 3 months' notice before shutdown, with an export for every member.
6. AI model budget per seat with clear spend caps that paid users can adjust.
7. Data stays in the box (federation rule 1). Only capacity numbers and shared artifacts (#todo better word needed for apps, prompts etc) leave, with consent (rule 3).
8. A named operator people can reach, and the network's code of conduct.
9. An hourly health and capacity report the network can read.

Process: apply; automated checks (version, health endpoint, privacy filter state, TLS); a human review by the team; probation (first payouts held back, as Storj once did); listing. Checks keep running. A host that breaks the Guarantee is delisted, and its members get the notice and the export.

Open: must vetted hosts sit behind Cloudflare too? Every Sage.is public service is behind Cloudflare by policy (2026-10-22).

#todo review and possibly allow for other protection eg other cdn or even TOR.

## Price

- Precedent: Discord sets the range ($2.99 to $199.99 a month) and owners pick inside it; Vast.ai lets hosts set any price, and verified hosts charge more.
- Proposal: the steward sets a floor per seat per month. Hosts price at or above it.
- The floor covers the model budget a seat includes, plus the network fee. A floor stops a race to the bottom that would starve model budgets.
- The steward also sets the guest/sponsored seat's length and model budget, tool access etc.
- Network fee benchmarks: Discord about 10% of subscriptions; PikaPods 10 to 15% to maintainers; Akash 4 to 20% (conflicting reports). Proposal: decide a band, between 10% and 20%.
- Where the fee goes: the core and the directory. How any Tinker.Click share is split is the Tinker.Click team's call (their decisions note proposes one shared ledger with equal splits).
- Managed-box plans by capacity: seats, model budget and storage. Benchmarks only, no prices proposed: Masto.host from about $6 a month; a small Bluesky PDS server about EUR 9 a month (2 vCPU, 2 GB); Element Pro per seat from 100 users.

## The pool

- A guest pass is a promise of someone's capacity. Mint passes from committed spare seats, not from popularity.
- A host commits spare seats. The steward mints guest passes against them. A redeemed pass puts the guest on a box with a free seat that fits their language and region.
- Like Nextcloud's Simple Signup, the guest can pick a host, or let the network pick. Their email goes to the host, not to the steward.
- When a guest stays as a member, the host earns and the seat leaves the pool.
- Members and hosts also get passes of their own on a schedule, as in Bluesky's beta. A pass whose guest stays earns more passes.
- Every pass records its issuer: the invite tree.
- Abuse controls: random codes (Bluesky's generator was cracked); one use, or a small number; a short expiry; bound to one person at redemption; rate limits; revocation. Bluesky codes were resold for $10 to $50, and the tree makes resale traceable.

## Interop

The four seams in Tinker.Click's `docs/notes/2026-10-31-integration-decisions.md` are the network's spine:

- AI-UI as a possible sign-in provider: one identity across boxes.
- The model gateway (Rootstock F2): every model call goes through the box, so the privacy filter applies.
- The Tinker.Click library server as a Sprig (F5): a Tinker library inside an AI-UI box.
- A shared bridge contract for apps in the Workshop.

The network adds three pieces:

- A directory: each box's region, languages, version, free seats, and its Guarantee status. No member data in it. A candidate home: the community hub at community.sage.is, due this winter.
- A pass service: mints, checks and revokes passes; keeps the invite tree.
- Export and move: a member takes their work to another box. Bluesky accounts already move between PDSs, and the Mastodon Guarantee's notice rule assumes an export.

The three federation rules hold (`docs/federation.md`): data stays home; definitions travel; numbers travel with consent. Seat counts, conversions and payout totals are numbers, so they travel only with the host's consent.

## Payments

- With Stripe Connect, each seller is usually the merchant of record for its own sales and carries the tax work.
- With a merchant-of-record provider, that provider collects sales tax and VAT and takes chargebacks and audit risk.
- US marketplace-facilitator laws may make the marketplace collect sales tax either way. #todo Not researched yet; ask accounting and look at tax friendly regions. Already we have Wyoming.
- Discord pays creators in the US only, which shows how much this work weighs.
- Proposal: no payouts at first. Hosts bill their own members, and the steward invoices hosts the network fee. Decide Connect or merchant of record before any payout.

## Who funds the core

Home Assistant's model: Nabu Casa sells the cloud service and hardware, and most subscription profit funds the nonprofit Open Home Foundation that owns the code. Managed boxes could fund the AI-UI core the same way. Tinker.Click's split is the Tinker.Click team's call.

#todo could this alternatively be done with a token and a blockchain. EG we mint our own tinker.token that corresponds to stuff.

## Phases

1. Our boxes only. Guest passes are magic links per channel, each with an expiry, a use limit and an account length. Referral codes ride the pilot form, and leads land in Trellis. The directory is one page.
2. Vetted hosts: managed hosts first, then independent boxes that pass vetting. The Guarantee, the floor price and capacity-backed passes start. Hosts bill their own members.
3. Payouts and the fee split; sign-in across boxes; export and move between boxes; Tinker.Click boxes join, once the Tinker.Click team agrees.

## Parked ideas

- IPFS mirrors (Alexander, 2026-11-03): member boxes pin each other's public files that never change, such as Sprig images and the catalog, release files and published Tinker apps. Anyone can mirror them and check a copy by its content ID, without trusting the server it came from. Never private data: IPFS is public by design, and a file lives only while someone pins it. Video served through a gateway behind Cloudflare stays under Cloudflare's video rule.

## Risks

- Model cost: a guest seat spends someone's API budget. Per-seat budgets and provider spend caps are required, not optional.
- A member's data on a stranger's box: the privacy brand rides on every host, so vetting and delisting must work from day one.
- Payouts make the steward a marketplace: tax forms and identity checks.
- Abuse: see the pool's controls. #TODO outline a Sage.is auto-watchdog that uses heuristics to Mitigate abuses.

## Decisions for to be made

1. Roles: guest, member, host and steward, with managed and vetted hosts?
2. Code names: guest pass and referral code?
3. The floor per seat, and the fee band.
4. The guest seat's length and model budget.
5. The Guarantee's items, and who on the team vets.
6. The directory's home: community.sage.is?
7. Payments: no payouts in phases 1 and 2?
8. Must vetted hosts sit behind Cloudflare?
9. Tinker.Click boxes in the network: the Tinker.Click team decides.

## Sources

### Discord

- <https://www.shacknews.com/article/133327/discord-server-subscription-revenue>
- <https://discord.com/creators/server-subs-102-to-tier-or-not-to-tier>
- <https://blog.communityone.io/discord-monetization-guide-2026/>
- <https://www.unilink.us/blog/how-to-add-link-discord-server>

### Minecraft

- <https://www.gameserverkings.com/knowledge-base/minecraft/monetising-your-server/>
- <https://pcgamesn.com/minecraft/mojang-clarify-new-server-rules-prevent-minecraft-servers-becoming-pay-win>
- <https://www.techradar.com/reviews/shockbyte>

### Fediverse and Matrix

- <https://joinmastodon.org/Guarantee>
- <https://docs.joinmastodon.org/user/signup/>
- <https://connect.fediforum.org/open-social-web-platform-managed-hosting/masto.host/>
- <https://matrix.org/hosting>
- <https://element.io/blog/simpler-plans-for-element-on-premise-and-cloud/>

### Bluesky

- <https://bsky.social/about/blog/6-02-2023-beta-update>
- <https://videogamer.com/news/bluesky-invite-codes-selling-for-50>
- <https://sliplane.io/blog/self-hosting-bluesky-pds-the-easy-way>

### Invite trees and code names

- <https://tildes.net/~tildes/1sc/brainstorming_trust_system_ideas>
- <https://jcs.org/notes/955524103454605404>
- <https://growsurf.com/glossary/invite-program/>
- <https://growsurf.com/glossary/referral-code/>
- <https://guide.fitdegree.com/support/solutions/articles/151000231351-what-is-a-guest-pass->

### Managed hosting and revenue share

- <https://nextcloud.com/sign-up/>
- <https://lowendbox.com/blog/the-pikapods-interview-super-easy-hosted-apps-from-people-who-care-about-privacy-plus-a-darn-cute-mascot>
- <https://linkding.link/acknowledgements/>
- <https://home-assistant.io/blog/2026/10/02/big-tech-ruined-the-cloud-so-were-renaming-ours/>
- <https://www.cnx-software.com/2024/04/23/open-home-foundation-manage-home-assistant-esphome-zigpy-over-240-open-source-smart-home-projects/>
- <https://verpex.com/blog/reseller-hosting/what-is-white-label-hosting>

### Node operators and compute markets

- <https://storj.dev/node/payouts>
- <https://docs.vast.ai/guides/instances/pricing>
- <https://www.fast.io/resources/vast-ai-review-2026/>
- <https://akash.network/docs/learn/core-concepts/providers-leases/>

### Payments

- <https://stripe.com/gb/resources/more/merchant-of-record-vs-payment-facilitator>
- <https://hokodo.co/resources/what-is-a-merchant-of-record-marketplace>

Many figures come from third-party guides and vendor pages, not the companies' own terms; check the primary page before any number goes into a price or a contract.
