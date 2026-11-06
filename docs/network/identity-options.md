# Identity options

Each person holds passkeys as the one credential, and an OIDC provider per box turns them into service logins. GUN's SEA and decentralized IDs travel across boxes, but none of our services speaks them, and SEA has no recovery.

## What our services speak

- OIDC: Nextcloud ([user_oidc](https://apps.nextcloud.com/apps/user_oidc)), Gitea, AI-UI, Vaultwarden [1.35+](https://github.com/dani-garcia/vaultwarden/releases/tag/1.35.0) (master password still unlocks), [Stalwart](https://stalw.art/docs/auth/backend/oidc/) (checks tokens; mail clients keep app passwords; mailboxes must exist first).
- Passkey login: Nextcloud; Gitea [1.23+](https://github.com/go-gitea/gitea/pull/31504).
- CapRover apps: none; a forward-auth proxy goes in front.

## Compared

| Option | Sign-in | Across boxes | Lost device | Record | Licence |
| --- | --- | --- | --- | --- | --- |
| AI-UI as IdP ([DOT](https://github.com/django-oauth/django-oauth-toolkit)) | ours to build | an IdP per box | ours to build | none yet | AGPL |
| [Kanidm](https://kanidm.github.io/kanidm/stable/) | passkey first; OIDC, LDAP | 2-node replicas | reset token, e-mail | active; one lead; no public audit | MPL-2.0 |
| Authentik | password, passkey; OIDC, SAML, LDAP, forward auth | one instance | e-mail flow | [Cure53 2023, Cobalt 2024](https://docs.goauthentik.io/security/audits-and-certs/); company | MIT core |
| Zitadel | password, passkey; OIDC, SAML | an org per host | e-mail, admin | [pentests](https://help.zitadel.com/do-you-do-regular-penetration-testing); company | AGPL-3.0 since 2025 |
| Pocket ID | passkey only; OIDC | one instance | [admin code](https://pocket-id.org/docs/troubleshooting/account-recovery) | one lead; certified | BSD-2 |
| LLDAP + Authelia | password, 2FA; LDAP, OIDC | one directory | e-mail reset | LLDAP one maintainer; Authelia [certified](https://www.authelia.com/blog/we-are-now-openid-certified/) | GPL-3, Apache-2 |
| GUN SEA | password or keypair | yes, key is the ID | none | alpha, no audit | MIT, Zlib, Apache |
| Passkeys | device unlock | one domain, [5 related](https://web.dev/articles/webauthn-related-origin-requests) | synced copy, second key | phishing-proof | standard |
| DIDs + VCs | wallet ([OpenID4VP](https://openid.net/specs/openid-4-verifiable-presentations-1_0-final.html)) | yes, any box verifies | reissue | [VC 2.0](https://www.w3.org/TR/vc-data-model-2.0/) 2025; tools young | royalty-free |

## GUN, judged

GUN's author still offers SEA. Login runs the password through PBKDF2 at 100,000 rounds to open a keypair kept in the shared graph ([sea.js](https://github.com/amark/gun/blob/master/sea.js)). Anyone can copy that blob and guess offline. OWASP asks [600,000](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html). The file calls itself "only an alpha release". The repo's 2026 commits add a UI kit.

## Recommendation

1. The credential is a passkey, synced in each person's password manager. Admins keep a second key.
2. Kanidm is the team box's OIDC bridge: passkey first, OIDC and LDAP in one binary. Authentik is the fallback, for public audits and built-in forward auth.
3. Across boxes, each host keeps its own IdP, later AI-UI, and hosts trust each other through [OpenID Federation](https://openid.net/specs/openid-federation-1_0.html), final in 2026. Trust marks can carry the Guarantee. E-mail stays with the host.
4. GUN stays out of sign-in.

## Questions for Alexander

1. Kanidm now and AI-UI as IdP later, or wait for Rootstock?
2. One network IdP at the steward, or one per host with federation?
3. Does GUN's author propose SEA as the login, or GUN as a sync layer?

Unverified: CapRover forward-auth wiring; Kanidm's audit (a maintainer's word, no report); OpenID Federation support in any candidate.
