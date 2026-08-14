# Release runbook

One command publishes a release: `make ship`. Everything below explains what it does, what it refuses, and how to recover when a step fails halfway.

Hotfixes use the same command. `release_smoke` accepts `release/*` and `hotfix/*` alike, and `finish_flow` works out which branch it is on.

## Why there is only one command

There used to be three ways to publish, and the one the README documented skipped `sprig_publish`. A Sprig shipped internal-only and nobody could pull it. The fix was not another check placed near the wrong door; it was removing the door.

The steps underneath `ship` now start with an underscore. They carry no `##` comment, so `make help` cannot list them, and reaching one means typing it on purpose.

## The sequence

| # | Step | Label | What it does |
| --- | --- | --- | --- |
| 1 | `release_preflight` | [WE] | Four checks against the outside world. See below |
| 2 | `release_smoke` | [WE] | Branch, version and clean-tree checks, then builds and smokes native plus amd64 |
| 3 | `release_finish` | [WE] | Merges to master and develop, cuts the annotated tag, pushes all three |
| 4 | `_it_build_multi_arch_push_GHCR` | [WE] | Multi-arch buildx push of `:X.Y.Z` and `:latest` |
| 5 | `verify_ghcr_manifest` | [WE] | Asserts the pushed image is present and a real amd64 plus arm64 index |
| 6 | `_pin_server_tag` | [WE] | Writes `SERVER_TAG` into `distribution.env`, preserving the inode |
| 7 | `sprig_publish` | [WE] | Pushes every local Sprig tag and gates on anonymous pullability |

Step 3 is the first irreversible one. Everything before it can be re-run freely.

## Before you run it

1. [WE] `make minor_release` (or `patch_release` / `major_release`) to cut the branch.
2. [WE] `make bump_release_version` to write the version into `app/package.json`. This is the only file it touches. The README version is a shields badge that reads origin's tags, so nothing keeps it in step by hand.
3. [MANUALLY] Write the `## [X.Y.Z]` section in `CHANGELOG.md`, then commit. Preflight refuses without it.
4. [WE] `make ship`.

## What preflight refuses

Four checks, and each is a fact about the world outside this repo. Everything else that used to live here has been designed away rather than checked.

| Check | Why it cannot be designed away |
| --- | --- |
| `gh auth status` succeeds | Credential state lives outside the repo. A stale login fails *after* the tag is cut |
| Docker reachable with at least 8 GiB | 2.3.0 died of buildx OOM with the tag already on origin. Override with `RELEASE_MIN_DOCKER_GIB=<n>` |
| `v<X.Y.Z>` is not already on origin | Origin is shared mutable state. This single check catches both the 2.3.0 and the 3.1.0 failures |
| `CHANGELOG.md` has a `## [X.Y.Z]` section | Prose. There is nothing to derive it from |

Preflight runs before `release_smoke`, not after. A preflight that fires at the end of a twenty-minute build has already wasted the twenty minutes.

## Recovery

**Preflight or smoke failed.** Nothing has happened yet. Fix and re-run `make ship`.

**The build or push failed after `release_finish`.** The merges and the tag are already on origin and the release branch is gone, so `make ship` will fail at `release_smoke`. Run the publishing half on its own:

```bash
make _it_build_multi_arch_push_GHCR
make verify_ghcr_manifest
make _pin_server_tag IMAGE_TAG=<X.Y.Z>
make sprig_publish
```

The underscores are the point. These are reachable when you mean them and invisible when you do not.

**`verify_ghcr_manifest` failed.** The push produced no image, or a single-arch one. Do not pin `SERVER_TAG`. Re-run the push step; the verify is what stands between a bad push and a CapRover deploy that says `manifest unknown`.

**`distribution_verify` failed inside `release_finish`.** A sibling repo's `distribution.env` differs from this one's. Read the diff before doing anything: the gate does not pick a winner, because homebrew-apps legitimately owns `CLI_VERSION` while this repo owns `SERVER_TAG`, and a rule that chose automatically would silently discard whichever field it did not favour. Fold the sibling's change into this repo's copy by hand, then `make distribution_sync` to publish, then re-run. If the difference is only ours to push, `make distribution_sync` alone is enough.

Note the ordering inside `_pin_server_tag`: it verifies *before* it rewrites `SERVER_TAG`, so a divergent sibling stops the release while everything is still untouched, rather than after a sync has already overwritten what that sibling was holding.

## Tags

`finish_flow` cuts tags with `git tag -a`. Do not cut one by hand. A hand-typed `git tag -f` produced this repo's only lightweight tag, and a lightweight tag is a bare pointer with no author, date or message, so `git describe` and every provenance question answer differently depending on which kind you got.

The pre-push hook refuses to publish a lightweight `v*` tag. It only judges tags that are not yet on origin, so an already-published one does not block every push. Run it by hand with `make tags_annotated`, and prove it still works with `make tags_annotated_teeth`.

## Deploying what you shipped

[MANUALLY] CapRover deploys by image name (Deployment tab, Method 6). Paste a digest-pinned reference rather than a tag:

```
ghcr.io/sage-is/ai-ui@sha256:<index-digest>
```

Swarm can serve a stale image after a same-tag redeploy, which bit 3.0.0. A digest cannot be stale. Get it from the output of `verify_ghcr_manifest`.

[MANUALLY] Then check the running version:

```bash
curl -s https://try.sage.is/api/config | python3 -m json.tool | grep -i version
```

A verified image is not a running image. Only that curl proves the deploy landed.
