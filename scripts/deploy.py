#!/usr/bin/env python3
"""Roll an AI-UI release out to our CapRover apps, one at a time, canary first.

The apps, their order and which need a backup live in deploy/instances.toml.
"""

import argparse
import datetime
import hashlib
import json
import os
import subprocess
import sys
import tomllib
import urllib.request
from pathlib import Path

INSTANCES = Path(__file__).resolve().parents[1] / "deploy" / "instances.toml"
# Backups land on Somma 02, which Backblaze syncs as it is, so they land
# encrypted and no plaintext copy touches any disk (card "Production data
# reaches Backblaze in plaintext", 2026-11-03). The passphrase stays in the vault.
BACKUPS = Path(os.environ.get("AI_UI_DEPLOY_BACKUPS", "/Volumes/Somma 02 14TB/Backups/ai-ui"))
BACKUP_KEY = "bw:ai-ui-deploy-db-backup"
# The recipe every encrypted backup on Somma 02 uses; decrypt with the same line plus -d.
ENC = "openssl enc -aes-256-cbc -pbkdf2 -iter 600000"
SQLITE_HEADER = b"SQLite format 3\x00"
# Cloudflare answers 403 to urllib's default User-Agent.
HEADERS = {"User-Agent": "sage-ai-ui-deploy"}


def run(*cmd: str) -> str:
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout


def digest_of(image: str, tag: str) -> str:
    """The multi-arch index digest behind a tag: what `cr-deploy deploy-image` needs."""
    manifest = run("docker", "buildx", "imagetools", "inspect", f"{image}:{tag}", "--format", "{{json .Manifest}}")
    return json.loads(manifest)["digest"]


def live_app(app: str) -> dict:
    return json.loads(run("cr-deploy", "apps", app, "--json"))[0]


def version_at(url: str) -> str:
    """The version an app reports, or "" when it does not answer."""
    try:
        with urllib.request.urlopen(urllib.request.Request(f"{url}/api/config", headers=HEADERS), timeout=15) as r:
            return json.load(r).get("version", "")
    except (OSError, ValueError):
        return ""


def sealed(script: str, *args: str, data: bytes | None = None) -> bytes:
    """`sh -c script` with BACKUP_PASS resolved by sage-secret: the passphrase
    reaches only that shell, never this process or a file."""
    command = ["sage-secret", "run", "--", "sh", "-c", script, "sh", *args]
    env = os.environ | {"BACKUP_PASS": BACKUP_KEY}
    return subprocess.run(command, input=data, env=env, check=True, capture_output=True).stdout


def store_encrypted(data: bytes, target: Path) -> None:
    """Write `data` gzipped and encrypted to `target`, keep it only if it decrypts
    back to the same bytes, and leave its sha256 beside it."""
    sealed(f'gzip -c | {ENC} -salt -pass env:BACKUP_PASS -out "$1"', str(target), data=data)
    digest = hashlib.sha256(data).hexdigest()
    if hashlib.sha256(sealed(f'{ENC} -d -pass env:BACKUP_PASS -in "$1" | gunzip -c', str(target))).hexdigest() != digest:
        target.unlink()
        sys.exit(f"{target.name}: the encrypted copy did not decrypt to the download; no deploy")
    plain_name = target.name.removesuffix(".gz.enc")
    target.with_name(f"{plain_name}.sha256").write_text(f"{digest}  {plain_name}\n")


def back_up(instance: dict) -> Path:
    """Download the app's database and store it encrypted on Somma 02; stop the rollout if that fails."""
    app, url, key_env = instance["app"], instance["url"], instance["admin_key_env"]
    key = os.environ.get(key_env)
    if not key:
        sys.exit(f"{app}: {key_env} is empty; run this through `make deploy`; no backup, no deploy")
    if not BACKUPS.parent.is_dir():
        sys.exit(f"{app}: {BACKUPS.parent} is not mounted; no backup, no deploy")
    request = urllib.request.Request(f"{url}/api/v1/utils/db/download", headers=HEADERS | {"Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(request, timeout=600) as r:
        data = r.read()
    if not data.startswith(SQLITE_HEADER):
        sys.exit(f"{app}: the download is not a SQLite database; no deploy")
    target = BACKUPS / app / f"{datetime.datetime.now():%Y-%m-%d-%H%M}-{version_at(url)}.db.gz.enc"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        store_encrypted(data, target)
    except subprocess.CalledProcessError as e:
        target.unlink(missing_ok=True)
        sys.exit(f"{app}: encrypting the backup failed: {e.stderr.decode(errors='replace').strip()[:300]}; no deploy")
    return target


def roll_out(instance: dict, tag: str, image: str) -> bool:
    app, url = instance["app"], instance["url"]
    now = live_app(app)
    if now["image"] == image:
        print(f"{app}: already runs {tag}; checking it answers")
        return version_at(url) == tag
    if not now["keeps_data"] and not instance.get("throwaway"):
        sys.exit(f"{app}: no volume and no bind mount; a deploy would start it empty. Refusing.")
    if instance.get("backup"):
        print(f"{app}: database saved to {back_up(instance)}")
    deploy = ["cr-deploy", "deploy-image", app, image, "--verify", f"{url}/api/config",
              "--expect", f"version={tag}", "--health", f"{url}/health"]
    return subprocess.run(deploy).returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="e.g. ghcr.io/sage-is/ai-ui")
    parser.add_argument("--tag", required=True, help="the release, e.g. 3.2.0")
    parser.add_argument("apps", nargs="*", help="only these apps (default: all, in order)")
    args = parser.parse_args()

    image = f"{args.image}@{digest_of(args.image, args.tag)}"
    instances = tomllib.loads(INSTANCES.read_text())["instance"]
    unknown = set(args.apps) - {i["app"] for i in instances}
    if unknown:
        sys.exit(f"not in {INSTANCES.name}: {', '.join(sorted(unknown))}")
    for instance in instances:
        if args.apps and instance["app"] not in args.apps:
            continue
        if not roll_out(instance, args.tag, image):
            print(f"{instance['app']}: stopped; apps after it were not touched. "
                  f"Undo with: make deploy_rollback APP={instance['app']}")
            return 1
    print(f"{args.tag} is live on every app")
    return 0


if __name__ == "__main__":
    sys.exit(main())
