#!/usr/bin/env python3
"""Free space on the HOST disk Docker writes to: <free_bytes> <growth_bytes> <path>.

3.2.0's build died with "input/output error": Docker.raw is sparse, and the
drive holding it had 373 MiB left. Docker cannot see that; only the host can.
growth_bytes is how far Docker.raw may still grow, or -1 when unknown.
"""

import json
import shutil
import subprocess
from pathlib import Path

SETTINGS = Path.home() / "Library/Group Containers/group.com.docker/settings-store.json"
DEFAULT = Path.home() / "Library/Containers/com.docker.docker/Data/vms/0/data"


def desktop():
    try:
        s = json.loads(SETTINGS.read_text())
    except (OSError, ValueError):
        return None
    folder = Path(s.get("DataFolder") or DEFAULT)
    if not folder.is_dir():
        return None
    image, cap = folder / "Docker.raw", int(s.get("DiskSizeMiB") or 0) << 20
    used = image.stat().st_blocks * 512 if image.exists() else 0  # sparse: blocks, not size
    return folder, max(0, cap - used) if cap else -1


def daemon_root():
    try:
        out = subprocess.run(["docker", "info", "--format", "{{.DockerRootDir}}"],
                             capture_output=True, text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        out = ""
    return Path(out) if out and Path(out).exists() else Path("/")


path, growth = desktop() or (daemon_root(), -1)
print(shutil.disk_usage(path).free, growth, path)
