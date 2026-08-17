# Working with files: field rules

Practical rules for agents and people changing files in this repo. Rules comes from something that went wrong or nearly did,  none of it is general advice. Where a rule cites an incident, the date points at our board or our archive.

The theme: **verify before you trust.** Most of the costly problems looked fine at a glance.

## Before changing a file

Read the region you will touch, not just a grep.

Always check whether anyone else is working in the repo. Run `git status` before and after your edits. If a anyone has staged work in flight, never `git add -A` — name your files explicitly.

For any file that might be hardlinked — Makefiles especially — check first:

```bash
stat -f "%l %N" Makefile   # macOS: prints link count
```

Any count above 1 means Edit/Write replaces the inode and this silently breaks the hardlink chain. Use `sed -i ''` in place instead.

## Before you trust a file

A file existing is not evidence that it is current.

- **Build artifacts go stale.** An artifact may be months old. Verify the version it reports, not its filename. (A DMG named for the right version was once three months old and matched an old release's checksum.)
- **Processes go stale.** A running app may be a previous build holding the port you are about to test. A smoke test once returned a clean health reporting the *previous* version, because an app from an earlier session
  answered first. Check `pgrep` before believing a local endpoint.
- **Checkouts go stale.** A locally installed tap or vendored repo may lag the
  remote. Confirm the checkout contains the commit you just pushed.

## When renaming across a codebase

Census first, rename second.

```bash
grep -rc 'oldname' --include='*.py' --include='*.html' .
```

Record the count. After the rename, verify the new count matches and the old one is zero. Rename code and templates yourself; docs can be delegated.

If the rename *corrects* an old mistake, check when it entered:

```bash
git log --oneline -S 'oldname' --reverse | head -3
```

That history shapes the decision. A typo dating to the founding commit with no external consumers justifies a clean break; a widely-used public name does not.

Prove the old paths are dead. Do not assume.

## When a config claims to protect something

**Ignore files are not transitive.** `.gitignore` does not protect against `COPY . /app/` — Docker reads `.dockerignore`, and when that file is absent, everything goes in.

A secret can be correctly gitignored and still ship inside a public image. That is exactly what happened on 2026-08-16: `scanner/access_keys.csv` was gitignored, never committed, and present in every published container tag.

Check each packaging boundary separately — git, Docker, the installer bundle, the release archive. Then test the claim rather than reading it: pull the published artifact and `cat` the file you believe is excluded.

## Verifying build artifacts

Open the box. Mount the image, run the embedded binary, hit the endpoints. Check the version the *artifact* reports, not the version the build log claimed. Confirm that what should be absent is absent.

For anything installed through a package manager, rehearse the real install path end to end: download from the published URL, verify the checksum against what the manifest declares, apply the platform's quarantine or permission behaviour, then launch it. That rehearsal is worth more than a syntax check on the manifest.

## Deleting published artifacts

**Deleting a tag does not delete content.** A container tag is a pointer; the manifest underneath stays pullable by digest.

After removing tagged versions, enumerate the untagged ones and test each by digest. On 2026-08-16 one untagged digest still served a leaked credential after every tagged version had been deleted.

```bash
gh api /orgs/<org>/packages/container/<pkg>/versions \
  --jq '.[] | {id, tags: .metadata.container.tags}'
```

## Editing machine-parsed files

If code parses the file — a board, a manifest, a lockfile — treat every character as load-bearing.

Prefer surgical edits over whole-file rewrites; a targeted replacement cannot silently drop a field. After editing, run the parser and compare counts before and after. For `TODO.md` that means `scanner/kanban.py`, plus `make sync_todos` to keep the README section honest.

**Never patch code after cutting a release tag.** If you find a bug post-tag, file it. The artifact and the tag must describe the same tree.

## Delegating file work

State outcomes and constraints. Point at reference files. Do not transcribe the target content into the brief — if you are typing the answer, you have already done the work and added a handoff risk for nothing.

A good brief names the file, the goal, what must not change, and where the ground truth lives. A bad brief is the finished text in quotes.

Always read the resulting diff. A delegated edit does exactly what you said, including faithfully preserving a line that went stale between writing the brief and running it.

Delegation does not fit when the content already exists and has been approved: that is transcription, not generation, and the brief would have to carry the whole text.

## Restructuring TODOs

Move TODOS **verbatim** — every number, path, date, flag, and checkbox state. Summarise in the new location, never in the moved copy. Leave a pointer from the trimmed file back to the archive.

In this repo: shipped work goes to `docs/completed-todos.md`; narration cut from open cards goes to `docs/board-dossiers.md`.

## Look at the rendered output

Screenshots and rendered pages are a test surface, not decoration.

Two real bugs surfaced on 2026-08-16 only because rendered pages got looked at rather than asserted on as strings: inline `#` comment markers were parsed as markdown headings, so every inline TODO painted as an `<h1>`; and a lookup keyed on the display name instead of the directory name reported "never" for a whole class of records.

If the work has a visual surface, look at it before calling it done.
