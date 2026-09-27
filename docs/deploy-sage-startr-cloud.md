# Deploying to sage.startr.cloud — upgrade runbook

Target: **sage.startr.cloud**, amd64, the team's real data (32 users, 1982 chats as of the v2.3.2 audit, not current). Not pinned to a node.

## What it is
A CapRover app named `sage-startr-cloud`. Runs on any cluster node; the store is replicated, not anchored.

## Where the data lives
A Service Update Override bind-mounts `/root/Sync/sage-ai-data/` onto `/app/backend/data/`. Syncthing replicates that folder across all three nodes, so the app can start on any of them and find the same `webui.db`. Syncthing is **replication, not backup**: a live SQLite file can sync torn. Backups come from the deploy step.

## Upgrade
Run `make deploy`.
The procedure, the automatic database download and the canary order are in [release-runbook.md](release-runbook.md#deploying-what-you-shipped).

## Check after deploy
[WE] `captain apps sage-startr-cloud` shows the bind mount under Service Update Override.
[WE] `curl https://sage.startr.cloud/api/config` reports the new version.
[MANUALLY] Open a few chats and Spaces by hand to confirm the data.
Re-index knowledge bases if the embedding engine changed (the catalog store records zero collections on prior versions, so this is required regardless).

## Restore from backup
[MANUALLY] In the CapRover dashboard set the app's Instance Count to 0 and save.
[MANUALLY] Pick one node and pause Syncthing there, so no other replica overwrites the file while you copy.
[MANUALLY] Copy the backup `.db` from `~/Backups/ai-ui/sage-startr-cloud/<date>-<old version>.db` over `/root/Sync/sage-ai-data/webui.db` on that node.
[MANUALLY] Remove any `webui.db-wal` and `webui.db-shm` files next to `webui.db` so SQLite does not replay a newer log over the restored file.
[MANUALLY] Resume Syncthing and wait for `sage-ai-data` to show Up to Date on all three nodes: it carries the restored file to the others.
[MANUALLY] In the CapRover dashboard set the app's Instance Count back to 1 and save.

## Rollback
[WE] `make deploy_rollback APP=sage-startr-cloud` — `captain rollback` runs the image version before the current one.
[MANUALLY] If a schema migration ran on the upgrade, restore the pre-upgrade backup via the Restore steps above; otherwise the rolled-back image still reads the current schema.

## Sprig registry
`SPRIG_REGISTRY` defaults to `ghcr.io/sage-is` (secure). Point it at the in-cluster registry or a GHCR pull-through proxy; sha256 pins guarantee the same bytes. `SPRIG_REGISTRY_INSECURE` gates plain-HTTP (auto-on only for loopback/local hosts).
