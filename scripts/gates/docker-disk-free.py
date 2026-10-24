#!/usr/bin/env python3
"""Room on the HOST disk that holds the disk of the docker runtime in use.

    docker-disk-free.py NEED_GIB    # ok, or FAIL with this runtime's fix (exit 1)

3.2.0's build died with "input/output error": Docker.raw is sparse, and the
drive holding it had 373 MiB left. Docker cannot see that; only the host can.
Colima, OrbStack and Docker Desktop each keep their disk somewhere else, and
the socket of docker's context says which one a build writes to. Docker
Desktop's drive tells nothing about a build on Colima.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

GIB = 1 << 30
ORBSTACK_DATA = "Library/Group Containers/HUAQ24HBR6.dev.orbstack/data"
DESKTOP_DATA = "Library/Containers/com.docker.docker/Data/vms/0/data"
DESKTOP_SETTINGS = "Library/Group Containers/group.com.docker/settings-store.json"

# What the disk holds, what grows, and how else to make room.
RUNTIMES = {
    "colima": (
        "Colima's VM disks",
        "Colima's VM disk",
        "move that folder to a larger drive with Colima stopped, and link it back",
    ),
    "orbstack": (
        "OrbStack's data",
        None,
        "pick a larger drive in OrbStack, Settings, Storage (OrbStack starts empty there)",
    ),
    "docker-desktop": (
        "Docker Desktop's Docker.raw",
        "Docker.raw",
        "move the disk image (Docker Desktop, Settings, Resources)",
    ),
    "docker": ("Docker's data", None, None),
}


def ask(*args: str) -> str:
    try:
        return subprocess.run(
            ["docker", *args], capture_output=True, text=True, timeout=20, check=False
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def unwritten(image: Path, size: int = 0) -> int:
    """How far a sparse disk image may still grow: its size less the blocks it holds; -1 when unknown."""
    try:
        st = image.stat()
    except OSError:
        return size or -1
    return max(0, (size or st.st_size) - st.st_blocks * 512)


def colima(sock: Path):
    """A Colima socket sits in its profile's folder, beside colima.yaml; the
    legacy ~/.colima/docker.sock serves the default profile. The profile's disk
    is in _disks under the Lima home: $LIMA_HOME, else _lima beside the profiles."""
    profile = sock.parent
    if not (profile / "colima.yaml").is_file():
        profile = profile / "default"
    if not (profile / "colima.yaml").is_file():
        return None
    lima = Path(os.environ.get("LIMA_HOME") or profile.parent / "_lima")
    disks = lima / "_disks"
    vm = "colima" if profile.name == "default" else f"colima-{profile.name}"
    folder = next(d for d in (disks, lima, profile) if d.is_dir())
    return folder, unwritten(disks / vm / "datadisk")


def orbstack(sock: Path):
    if ".orbstack" not in sock.parts:
        return None
    home = Path.home()
    settings = home / ".orbstack/vmconfig.json"
    try:
        folder = json.loads(settings.read_text()).get("data_dir")
    except (OSError, ValueError):
        folder = None
    folder = Path(folder or home / ORBSTACK_DATA)
    return (folder, -1) if folder.is_dir() else None


def desktop(sock: Path):
    home = Path.home()
    run = (home / ".docker/run").resolve()
    if sock.parent != run and "com.docker.docker" not in sock.parts:
        return None
    try:
        s = json.loads((home / DESKTOP_SETTINGS).read_text())
    except (OSError, ValueError):
        return None
    folder = Path(s.get("DataFolder") or home / DESKTOP_DATA)
    if not folder.is_dir():
        return None
    cap = int(s.get("DiskSizeMiB") or 0) << 20
    return folder, unwritten(folder / "Docker.raw", cap)


def daemon_root() -> Path:
    out = ask("info", "--format", "{{.DockerRootDir}}")
    return Path(out) if out and Path(out).exists() else Path("/")


def find():
    """(runtime, folder, growth) for the runtime docker's context uses."""
    out = ask("context", "inspect", "-f", "{{.Endpoints.docker.Host}}")
    if out.startswith("unix://"):
        sock = Path(out[len("unix://") :]).resolve()
        for runtime, probe in (
            ("colima", colima),
            ("orbstack", orbstack),
            ("docker-desktop", desktop),
        ):
            found = probe(sock)
            if found:
                return (runtime, *found)
    return "docker", daemon_root(), -1


def main(argv: list[str]) -> int:
    if len(argv) != 2 or not argv[1].isdigit():
        print(f"usage: {argv[0]} NEED_GIB", file=sys.stderr)
        return 2
    need = int(argv[1])
    runtime, folder, growth = find()
    holds, grows, fix = RUNTIMES[runtime]
    free = shutil.disk_usage(folder).free
    if free >= need * GIB:
        print(f"  ok    {free // GIB}GiB free on the host disk that holds {holds}")
        return 0
    more = (
        f" {grows} may still grow {growth // GIB}GiB." if grows and growth >= 0 else ""
    )
    print(
        f"  FAIL  the host disk that holds {holds} has {free >> 20}MiB free: {folder.resolve()}"
    )
    print(f"        The multi-arch build wants {need}GiB there.{more}")
    print(
        "        3.2.0 died here: the drive filled, buildkit said input/output error, the tag was on origin."
    )
    print(
        f"        Fix: free space on that volume, {fix + ', ' if fix else ''}or override RELEASE_MIN_BUILD_DISK_GIB=<n>."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
