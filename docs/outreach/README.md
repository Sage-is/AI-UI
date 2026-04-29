# Outreach drafts

Working drafts of outbound communication to schools, partners, and prospective
clients. Pre-send material lives here while we shape it.

## What's tracked, what's not

This `README.md` is the only file in this folder that git tracks. Everything
else is gitignored. Drafts often name people, schools, and pricing. None of
that belongs in a public repo.

The gitignore rule is in the project root `.gitignore`:

```
docs/outreach/*
!docs/outreach/README.md
```

## Where the sent versions live

Sent emails are not archived here. Other systems handle that:

- The mail accounts that send the message keep the canonical record.
- Archival and sync run outside this repo.

If you need a sent message, go to the mailbox, not this folder.

## How to use this folder

- Draft new outreach as `kebab-case.md` files (e.g., `bialik-trial-emails.md`).
- Keep one file per campaign or recipient thread, not one per email.
- When the campaign ships, the drafts can stay here for reference or be
  deleted — either way, nothing here is the source of truth.

## Mistake-proofing

Three barriers stop drafts leaking into the public repo:

1. **`.gitignore`** — ignores everything here except this README. Plain
   `git add` does nothing on a draft.
2. **`pre-commit` hook `block-outreach-drafts`** — refuses any commit that
   stages a file in this folder other than `README.md`. Catches
   `git add -f`, which would otherwise bypass `.gitignore`.
3. **This README** — tells future-you why the folder exists. Do not strip
   the rules without a reason.

What still bites:

- `git commit --no-verify` skips the hook. Don't use it here.
- Editing `.gitignore` or `.pre-commit-config.yaml` to remove the rules
  defeats them. Review changes to those files carefully.
- Cloud sync (Dropbox, iCloud, SyncThing) of the parent folder will copy
  drafts wherever the sync runs. Repo privacy is not cloud privacy.
