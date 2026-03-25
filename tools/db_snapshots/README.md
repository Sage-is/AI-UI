# DB Snapshots

Database snapshots for upgrade testing. These files are **gitignored** — only this README is committed.

## Purpose

Before each release, run `make test_db_upgrade` to verify that migrations apply cleanly against a prior-version database. The test copies the snapshot to a temp directory (original is never mutated), boots the app in Docker, and checks that all Peewee + Alembic migrations succeed.

## Files

Place `.sqlite` snapshots here. Naming convention: `webui.<version>.db.sqlite`

```
webui.2.0.0.db.sqlite   # current release snapshot
webui_dev.db.sqlite      # small dev DB for quick iteration
```

## Rotation Policy

Keep **current version + one prior version**. Max 2-3 files total.

When releasing vN:
1. Run `make test_db_upgrade` against v(N-1) snapshot
2. After test passes, create vN snapshot from the migrated DB
3. Delete v(N-1) snapshot — it served its purpose

Never accumulate more than 3 snapshots.

## Backup & Storage

These files are too large for git. They're covered by the existing three-tier backup stack:

1. **SyncThing** — syncs between dev machines automatically (already running). Snapshots live in a SyncThing-shared directory.
2. **Time Machine** — local versioned backups cover the SyncThing dirs.
3. **Backblaze Computer Backup** — offsite versioned backup of the whole machine.

All three layers have versioning. No separate B2 bucket or git-annex needed.

## Onboarding New Developers

**Primary: SyncThing**
1. New dev installs SyncThing (`brew install syncthing`)
2. Exchange device IDs with an existing team member
3. Share the project folder — snapshots sync automatically
4. That's it. Ongoing sync is automatic.

**Ad-hoc: Magic Wormhole**
For one-time sharing with occasional contributors who don't need ongoing sync:
```bash
# Sender
brew install magic-wormhole
wormhole send tools/db_snapshots/webui.2.0.0.db.sqlite

# Receiver
wormhole receive <code>
```
End-to-end encrypted, no account needed, link expires after transfer.

## Usage

```bash
make it_build            # Build image first if needed
make test_db_upgrade     # Run migration smoke test against snapshots
```
