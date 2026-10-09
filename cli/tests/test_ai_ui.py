"""ai-ui's container runtime on macOS (Colima by default, Docker Desktop or OrbStack on request), Colima's VM and its data disk, the move to Colima, and nuke across them."""

import filecmp
import io
import json
import os
import pty
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import unittest
from pathlib import Path

AI_UI = Path(__file__).resolve().parent.parent / "ai-ui"
# ai-ui sources the runtime code it shares with sage-runtime and trellis-crm from lib/ beside it: a copy of the
# homebrew-apps tap's, in a checkout beside this one.
LIB = AI_UI.parent / "lib" / "sage-runtime.sh"
TAP = AI_UI.parents[2] / "homebrew-apps"
# krunkit's dependencies come from its tap too, and Homebrew 7 refuses each one from an untrusted tap.
KRUNKIT_INSTALL = "brew tap libkrun/krun && brew trust libkrun/krun && brew install krunkit"
# What a krunkit VM needs in Lima's override file, byte for byte as sage-runtime writes it (its own tests hold
# its output to these): virtiofs (abiosoft/colima#1607), and a boot step that mounts the data disk (abiosoft/colima#1614).
VIRTIOFS = ("# Colima 0.10.3 hands Lima 9p for krunkit, and Lima 2.2 refuses it: abiosoft/colima#1607\n"
            "mountType: virtiofs\n")
DATA_DISK_STEP = """\
  - mode: dependency
    script: |
      #!/bin/sh
      for link in /dev/disk/by-label/lima-*; do
        [ -e "$link" ] || continue
        dir="/mnt/${link##*/}"
        mountpoint -q "$dir" || { mkdir -p "$dir" && mount "$link" "$dir"; }
      done
"""
DATA_DISK = ("# krunkit puts the data disk on vdc, where Lima 2.2 looks for vdb; mount it by label: abiosoft/colima#1614\n"
             "provision:\n" + DATA_DISK_STEP)
OWN_PROVISION = "provision:\n  - mode: system\n    script: echo hi\n"
# Lima's override as a krunkit VM's first start finds it (None: no file yet), and as it leaves it.
FIRST_STARTS = (
    (None, VIRTIOFS + DATA_DISK),
    ("", VIRTIOFS + DATA_DISK),
    ("cpuType: host\n", "cpuType: host\n" + VIRTIOFS + DATA_DISK),
    ("cpuType: host", "cpuType: host\n" + VIRTIOFS + DATA_DISK),  # an editor may leave off the last newline
    ("mountType: 9p\n", "mountType: 9p\n" + DATA_DISK),
    ("mountType: virtiofs", "mountType: virtiofs\n" + DATA_DISK),
    (VIRTIOFS + DATA_DISK, VIRTIOFS + DATA_DISK),  # each fix lands once
    (OWN_PROVISION, OWN_PROVISION + VIRTIOFS),  # a second provision key would break the file
)
HOST_ENTRY = "--add-host=host.docker.internal:host-gateway"
MOVE_QUESTION = "Move Sage to Colima now?"
KRUNKIT_QUESTION = "Make the VM krunkit now, keeping every image and volume?"

# Stand-ins log each call. Each docker context answers once its $STATE/running-<context> marker is there, and keeps
# a folder per volume under $STATE/vol-<context>/. $STATE/run-<context>/<name> is a running container (the volumes it
# mounts, between commas), and $STATE/app-<context> the image and port sage-ai has there. A copy's alpine runs read
# and write those folders as tar, find and du would.
# `colima start` makes colima docker's context unless told --activate=false, keeps the Lima override it found where
# Colima 0.10.3 looks (config/files.go), and writes
# a new VM's type where Lima keeps it, with a data disk in Lima's _disks. A krunkit VM comes back with Docker on its
# root disk ($STATE/root-disk) on any boot after its first, unless the override mounts its disk by label
# (abiosoft/colima#1614). delete keeps the data disk and Docker's data on it. `colima ssh` runs the command as if
# inside the VM, and reads stdin to pass it on, as ssh does. There findmnt names the disk under Docker's folder,
# which is no mount at all on a VM made before Colima had a data disk ($STATE/one-disk). A hang ($STATE/hang-ssh,
# $STATE/hang-inspect) leaves a child holding the output, as colima ssh's limactl and ssh do: ending the stand-in
# alone ends no $(...). uname and sysctl describe the Mac; df gives 100 GiB free.
STUBS = {
    "docker": r"""ctx="$(cat "$STATE/current-context" 2>/dev/null || echo default)"
[[ -z "${DOCKER_CONTEXT:-}" ]] || ctx="$DOCKER_CONTEXT"
if [[ "${1:-}" == --context ]]; then ctx="$2"; shift 2; fi
echo "docker $ctx $*" >> "$STATE/calls"
vols="$STATE/vol-$ctx"
case "$1 ${2:-}" in
  "info "*)          [[ -e "$STATE/running-$ctx" ]] || exit 1
                     [[ "${2:-}" != --format ]] || echo /var/lib/docker ;;
  "context show")    echo "$ctx" ;;
  "context inspect") [[ -e "$STATE/running-$3" ]] ;;
  "context use")     echo "$3" > "$STATE/current-context" ;;
  "volume ls")       ls "$vols" 2>/dev/null || true ;;
  "ps "*)            for f in "$STATE/run-$ctx"/*; do [[ ! -e "$f" ]] || printf '%s\t%s\n' "${f##*/}" "$(cat "$f")"; done ;;
  "inspect --format") [[ ! -e "$STATE/hang-inspect" ]] || { sleep 60; exit 1; }
                     [[ -e "$STATE/run-$ctx/${@: -1}" || -e "$STATE/stopped-$ctx/${@: -1}" ]] || exit 1
                     cat "$STATE/app-$ctx" ;;
  "stop "*)          shift
                     for name in "$@"; do
                       [[ -e "$STATE/run-$ctx/$name" ]] || continue
                       mkdir -p "$STATE/stopped-$ctx"; mv "$STATE/run-$ctx/$name" "$STATE/stopped-$ctx/"
                     done ;;
  "start "*)         shift
                     for name in "$@"; do
                       [[ ! -e "$STATE/stopped-$ctx/$name" ]] || mv "$STATE/stopped-$ctx/$name" "$STATE/run-$ctx/"
                     done ;;
  "run "*)
    # -v NAME:... names a volume, which docker makes; -v /PATH:/stage is the staging folder.
    vol="" stage="" prev=""
    for a in "$@"; do
      if [[ "$prev" == -v ]]; then
        if [[ "$a" == /* ]]; then stage="${a%%:*}"; else vol="${a%%:*}"; fi
      fi
      prev="$a"
    done
    dir="$vols/$vol" last="${*: -1}"
    [[ -z "$vol" ]] || mkdir -p "$dir"
    if [[ "$*" == *" df -Pk /v" ]]; then
      printf 'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/vdb1 209715200 0 104857600 0%% /v\n'
    elif [[ "$*" == *" -cf /stage/"* ]]; then
      all="$*"; f="${all##* -cf /stage/}"; tar -C "$dir" -cf "$stage/${f%% *}" .
    elif [[ "$*" == *" -xf /stage/"* ]]; then
      tar -C "$dir" -xf "$stage/${last#/stage/}"
    elif [[ "$*" == *" find /v -mindepth 1 -delete"* ]]; then
      find "$dir" -mindepth 1 -delete
    elif [[ "$*" == *" sh -c "* ]]; then
      sh -c "${last//\/v/$dir}"
    fi ;;
esac""",
    "colima": r"""echo "colima $*" >> "$STATE/calls"
home="$HOME/.colima"
if [[ ! -e "$home" && -n "${XDG_CONFIG_HOME:-}" ]]; then home="$XDG_CONFIG_HOME/colima"; fi
if [[ -d "${COLIMA_HOME:-}" ]]; then home="$COLIMA_HOME"; fi
lima="${LIMA_HOME:-$home/_lima}"
case "$1" in
  list)   if [[ -e "$STATE/colima-vm" ]]; then
            status=Stopped; [[ ! -e "$STATE/running-colima" ]] || status=Running
            printf '{"name":"default","status":"%s","arch":"aarch64","cpus":5,"memory":8589934592,"disk":107374182400,"runtime":"docker"}\n' "$status"
          fi ;;
  start)  cp "$lima/_config/override.yaml" "$STATE/override-at-start" 2>/dev/null
          rm -f "$STATE/root-disk"
          if [[ -e "$STATE/colima-vm" ]] && grep -q '^vmType: krunkit' "$lima/colima/lima.yaml" 2>/dev/null \
             && ! grep -q 'by-label/lima-' "$lima/_config/override.yaml" 2>/dev/null; then
            touch "$STATE/root-disk"
          fi
          if [[ " $* " == *" --vm-type "* ]]; then
            all="$*"; type="${all##*--vm-type }"
            mkdir -p "$lima/colima"; echo "vmType: ${type%% *}" > "$lima/colima/lima.yaml"
          fi
          if [[ ! -e "$STATE/one-disk" ]]; then mkdir -p "$lima/_disks/colima"; touch "$lima/_disks/colima/datadisk"; fi
          [[ " $* " == *" --activate=false "* ]] || echo colima > "$STATE/current-context"
          touch "$STATE/colima-vm" "$STATE/running-colima" ;;
  stop)   rm -f "$STATE/running-colima" ;;
  delete) rm -rf "$STATE/colima-vm" "$STATE/running-colima" "${lima:?}/colima" ;;
  ssh)    cat > /dev/null
          [[ ! -e "$STATE/fail-ssh" ]] || exit 255
          [[ ! -e "$STATE/hang-ssh" ]] || { sleep 60; exit 255; }
          while [[ $# -gt 0 && "$1" != -- ]]; do shift; done
          shift; DOCKER_CONTEXT=colima "$@" ;;
esac""",
    "findmnt": r"""[[ ! -e "$STATE/no-findmnt" ]] || exit 127
case "${@: -1}" in
  /)  echo /dev/vda1 ;;
  /var/lib/docker|/var/lib/containerd)
      if [[ -e "$STATE/one-disk" ]]; then
        [[ " $* " == *" -T "* ]] || exit 1
        echo /dev/vda1
      elif [[ -e "$STATE/root-disk" ]]; then echo "/dev/vda1[/mnt/lima-colima/docker]"
      else echo "/dev/vdc1[/docker]"; fi ;;
esac""",
    "open": r"""echo "open $*" >> "$STATE/calls"
case "${@: -1}" in
  Docker)   touch "$STATE/running-desktop-linux" ;;
  OrbStack) touch "$STATE/running-orbstack" ;;
esac""",
    "osascript": r"""case "$*" in
  *'application "Docker" is running'*)   if [[ -e "$STATE/running-desktop-linux" ]]; then echo true; else echo false; fi ;;
  *'application "OrbStack" is running'*) if [[ -e "$STATE/running-orbstack" ]]; then echo true; else echo false; fi ;;
esac""",
    "df": r"""[[ -e "${@: -1}" ]] || exit 1
printf 'Filesystem 1024-blocks Used Available Capacity Mounted on\n/dev/disk1 209715200 0 104857600 1%% /\n'""",
    "uname": r"""case "${1:-}" in
  -m) cat "$STATE/arch" ;;
  *)  echo Darwin ;;
esac""",
    "sysctl": r"""case "${@: -1}" in
  hw.memsize) echo $(( $(cat "$STATE/memory-gib") * 1073741824 )) ;;
  hw.ncpu)    cat "$STATE/cores" ;;
esac""",
}


def write_command(path, body=""):
    path.write_text("#!/bin/bash\n" + body + "\n")
    path.chmod(0o755)


def setUpModule():
    # macOS checks each new executable on its first run, about 0.3 s, so the stand-ins are written once.
    shared = tempfile.TemporaryDirectory()
    unittest.addModuleCleanup(shared.cleanup)
    Mac.stand_ins = Path(shared.name)
    for name, body in STUBS.items():
        write_command(Mac.stand_ins / name, body)


@unittest.skipUnless(sys.platform == "darwin", "the runtime choice is macOS-only")
class Mac(unittest.TestCase):
    """A fake Mac with Apple Silicon, 32 GiB and 10 cores, and no krunkit.

    Its own home, apps folder and commands come first; the shared stand-ins follow on its PATH.
    """

    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        root = Path(scratch.name).resolve()  # /var is a link to /private/var, where a command run there finds itself
        self.home, self.apps, self.state, self.bin = root / "home", root / "Applications", root / "state", root / "bin"
        for folder in (self.home, self.apps, self.state, self.bin):
            folder.mkdir()
        self.hardware()
        self.env = {"HOME": str(self.home), "PATH": f"{self.bin}:{self.stand_ins}:/usr/bin:/bin",
                    "STATE": str(self.state), "APPLICATIONS_DIR": str(self.apps)}
        self.override = self.home / ".colima" / "_lima" / "_config" / "override.yaml"

    def add_command(self, name, body=""):
        write_command(self.bin / name, body)

    def colima(self, *args):
        """Colima, run by hand."""
        subprocess.run([self.stand_ins / "colima", *args], env=self.env, check=True, stdin=subprocess.DEVNULL)

    def write_override(self, text):
        self.override.parent.mkdir(parents=True, exist_ok=True)
        self.override.write_text(text)

    def hardware(self, arch="arm64", memory_gib=32, cores=10):
        """What uname -m and sysctl report."""
        for name, value in (("arch", arch), ("memory-gib", memory_gib), ("cores", cores)):
            (self.state / name).write_text(f"{value}\n")

    def install(self, app):
        (self.apps / f"{app}.app").mkdir()

    def running(self, context):
        (self.state / f"running-{context}").touch()
        if context == "colima":  # a VM that runs is one Colima lists
            (self.state / "colima-vm").touch()

    def volume(self, context, name, files):
        folder = self.state / f"vol-{context}" / name
        folder.mkdir(parents=True)
        for rel, text in files.items():
            (folder / rel).parent.mkdir(parents=True, exist_ok=True)
            (folder / rel).write_text(text)
        return folder

    def app(self, context, image, port):
        """sage-ai, running in CONTEXT on IMAGE and PORT with its volume."""
        (self.state / f"app-{context}").write_text(f"{image} {port}\n")
        (self.state / f"run-{context}").mkdir(exist_ok=True)
        (self.state / f"run-{context}" / "sage-ai").write_text("sage-ai-data")

    def save_runtime(self, runtime):
        (self.home / ".sage-is").mkdir(exist_ok=True)
        (self.home / ".sage-is" / "runtime").write_text(runtime + "\n")

    def run_ai_ui(self, *args, answer=None, cli=None, cwd=None):
        """Run ai-ui; with `answer`, stdin is a terminal that types it."""
        cli = cli or AI_UI
        if answer is None:
            return subprocess.run([cli, *args], env=self.env, capture_output=True, text=True,
                                  stdin=subprocess.DEVNULL, timeout=30, cwd=cwd)
        terminal, typist = pty.openpty()
        os.write(terminal, answer.encode())
        try:
            return subprocess.run([cli, *args], env=self.env, capture_output=True, text=True,
                                  stdin=typist, timeout=30, cwd=cwd)
        finally:
            os.close(terminal)
            os.close(typist)

    def ok(self, *args, **kwargs):
        result = self.run_ai_ui(*args, **kwargs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def calls(self):
        path = self.state / "calls"
        return path.read_text().splitlines() if path.exists() else []

    def runs(self, context):
        """The containers ai-ui ran in CONTEXT: every docker run but a copy's."""
        return [call for call in self.calls() if call.startswith(f"docker {context} run ") and "alpine:3" not in call]

    def saved_runtime(self):
        saved = self.home / ".sage-is" / "runtime"
        return saved.read_text().strip() if saved.exists() else None

    def offers(self):
        offers = self.home / ".sage-is" / "offers"
        return offers.read_text() if offers.exists() else None

    def docker_context(self):
        """docker's saved context, the one new shells use."""
        saved = self.state / "current-context"
        return saved.read_text().strip() if saved.exists() else "default"


class FirstStart(Mac):
    def test_a_mac_with_no_runtime_gets_colima_and_a_vm_sized_for_sage(self):
        self.add_command("krunkit")
        result = self.ok("start")
        self.assertIn("colima start --profile default --vm-type krunkit --mount-type virtiofs --mount-inotify"
                      " --memory 12 --cpu 5 --disk 100", self.calls())
        self.assertNotIn(KRUNKIT_INSTALL, result.stdout)
        self.assertTrue(self.runs("colima"))
        self.assertEqual(self.saved_runtime(), "colima")

    def test_an_existing_colima_vm_keeps_its_own_settings(self):
        (self.state / "colima-vm").touch()
        self.add_command("krunkit")
        self.run_ai_ui("start")
        self.assertEqual([call for call in self.calls() if call.startswith("colima start")], ["colima start"])
        self.assertFalse(self.override.exists())

    def test_the_question_lists_each_runtime_and_defaults_to_the_last_one_used(self):
        self.install("Docker")
        (self.state / "current-context").write_text("desktop-linux\n")
        result = self.run_ai_ui("start", answer="\nn\n")  # then no to the move
        self.assertIn("1) colima", result.stderr)
        self.assertIn("2) docker-desktop", result.stderr)
        self.assertIn("Runtime [docker-desktop]:", result.stderr)
        self.assertEqual(self.saved_runtime(), "docker-desktop")

    def test_a_number_picks_from_the_list(self):
        self.install("Docker")
        (self.state / "current-context").write_text("desktop-linux\n")
        self.run_ai_ui("start", answer="1\n")
        self.assertEqual(self.saved_runtime(), "colima")

    def test_no_question_without_a_terminal(self):
        self.install("Docker")
        result = self.run_ai_ui("start")
        self.assertNotIn("Runtime [", result.stderr)
        self.assertEqual(self.saved_runtime(), "colima")


class ColimaVM(Mac):
    """The first start creates Colima's VM: krunkit on Apple Silicon when it is installed, else vz."""

    def new_vm(self):
        """Start without a VM; return the `colima start` that made one, and what ai-ui said."""
        for leftover in ("colima-vm", "running-colima", "calls"):
            (self.state / leftover).unlink(missing_ok=True)
        result = self.ok("start")
        return next(call for call in self.calls() if call.startswith("colima start")), result.stdout

    def test_apple_silicon_without_krunkit_says_how_to_get_it_and_uses_vz_with_rosetta(self):
        command, said = self.new_vm()
        self.assertEqual(command, "colima start --profile default --vm-type vz --vz-rosetta --mount-type virtiofs"
                                  " --mount-inotify --memory 8 --cpu 5 --disk 100")
        warnings = [line for line in said.splitlines() if "krunkit" in line]
        self.assertEqual(len(warnings), 1, said)
        self.assertTrue(warnings[0].startswith("Warning: "), warnings[0])
        self.assertIn(KRUNKIT_INSTALL, warnings[0])
        self.assertFalse(self.override.exists())

    def test_intel_gets_vz_without_rosetta_even_with_krunkit_on_the_path(self):
        self.hardware(arch="x86_64")
        self.add_command("krunkit")
        command, said = self.new_vm()
        self.assertEqual(command, "colima start --profile default --vm-type vz --mount-type virtiofs --mount-inotify"
                                  " --memory 8 --cpu 5 --disk 100")
        self.assertNotIn("krunkit", said)
        self.assertFalse(self.override.exists())

    def test_krunkit_takes_half_the_memory_from_4_to_12_gib_and_half_the_cores_from_2_to_8(self):
        self.add_command("krunkit")
        self.hardware(memory_gib=4, cores=2)
        self.assertRegex(self.new_vm()[0], " --memory 4 --cpu 2 --disk 100$")
        self.hardware(memory_gib=16, cores=20)
        self.assertRegex(self.new_vm()[0], " --memory 8 --cpu 8 --disk 100$")

    def test_vz_takes_a_third_of_the_memory_from_4_to_8_gib(self):
        self.hardware(memory_gib=8, cores=2)
        self.assertRegex(self.new_vm()[0], " --memory 4 --cpu 2 --disk 100$")
        self.hardware(memory_gib=16, cores=20)
        self.assertRegex(self.new_vm()[0], " --memory 5 --cpu 8 --disk 100$")

    def test_a_mac_whose_sysctl_fails_gets_the_smallest_vm(self):
        self.add_command("sysctl", "exit 1")  # sysctl lives in /usr/sbin, which some PATHs leave out
        self.assertRegex(self.new_vm()[0], " --memory 4 --cpu 2 --disk 100$")

    def test_help_says_to_install_krunkit_before_the_first_start(self):
        self.assertIn(KRUNKIT_INSTALL, self.run_ai_ui("--help").stdout)


class LimaOverride(Mac):
    """Lima's override file mends two krunkit faults before ai-ui makes a krunkit VM.

    Colima 0.10.3 hands Lima 9p, which Lima 2.2 refuses (abiosoft/colima#1607), and krunkit leaves the
    data disk unmounted after the VM's first boot (abiosoft/colima#1614).
    """

    def setUp(self):
        super().setUp()
        self.add_command("krunkit")

    def first_start(self, held=None):
        """Start Sage with no VM yet and Lima's override holding `held` (None: no file); return the result."""
        for leftover in ("colima-vm", "running-colima"):
            (self.state / leftover).unlink(missing_ok=True)
        self.override.unlink(missing_ok=True)
        if held is not None:
            self.write_override(held)
        return self.ok("start")

    def test_each_override_ends_byte_for_byte_as_sage_runtime_leaves_it(self):
        for held, left in FIRST_STARTS:
            with self.subTest(held=held):
                self.first_start(held)
                self.assertEqual(self.override.read_bytes(), left.encode())

    def test_a_new_krunkit_vm_starts_with_both_mends_in_place(self):
        self.first_start()
        self.assertEqual((self.state / "override-at-start").read_text(), VIRTIOFS + DATA_DISK)

    def test_each_mend_says_so_and_a_file_that_has_both_hears_nothing(self):
        said = self.first_start().stdout
        lines = [line for line in said.splitlines() if str(self.override) in line]
        self.assertEqual(len(lines), 2, said)
        self.assertIn("A QEMU Colima profile will not start while that line is there.", lines[0])
        self.assertIn("mounts the VM's data disk (abiosoft/colima#1614)", lines[1])
        result = self.first_start(VIRTIOFS + DATA_DISK)
        self.assertNotIn(str(self.override), result.stdout + result.stderr)

    def test_an_override_with_its_own_provision_list_gets_the_step_to_add_by_hand(self):
        result = self.first_start(OWN_PROVISION)
        self.assertIn(f"Warning: {self.override} has its own provision list. Add this step to it", result.stderr)
        self.assertIn(DATA_DISK_STEP, result.stderr)

    def test_colima_home_moves_it(self):
        self.env["COLIMA_HOME"] = str(self.home / "colima")
        self.first_start()
        self.assertEqual((self.home / "colima/_lima/_config/override.yaml").read_text(), VIRTIOFS + DATA_DISK)
        self.assertFalse(self.override.exists())

    def test_lima_home_moves_it(self):
        self.env["LIMA_HOME"] = str(self.home / "lima")
        self.first_start()
        self.assertEqual((self.home / "lima/_config/override.yaml").read_text(), VIRTIOFS + DATA_DISK)
        self.assertFalse((self.home / ".colima").exists())

    def test_xdg_config_home_moves_it_without_making_a_colima_folder(self):
        # Colima ignores $XDG_CONFIG_HOME, and the profiles kept there, once ~/.colima exists.
        self.env["XDG_CONFIG_HOME"] = str(self.home / ".config")
        self.first_start()
        self.assertEqual((self.home / ".config/colima/_lima/_config/override.yaml").read_text(), VIRTIOFS + DATA_DISK)
        self.assertFalse((self.home / ".colima").exists())

    def test_an_existing_colima_folder_beats_xdg_config_home(self):
        self.env["XDG_CONFIG_HOME"] = str(self.home / ".config")
        (self.home / ".colima").mkdir()
        self.first_start()
        self.assertEqual(self.override.read_text(), VIRTIOFS + DATA_DISK)

    def test_help_names_the_file_and_what_each_mend_does(self):
        said = self.run_ai_ui("--help").stdout
        for fact in (str(self.override), "abiosoft/colima#1607", "QEMU", "abiosoft/colima#1614",
                     "colima ssh -- findmnt /var/lib/docker", "colima restart"):
            self.assertIn(fact, said)


class DataDisk(Mac):
    """Docker keeps its images and volumes, Sage's data among them, on the Colima VM's data disk."""

    def setUp(self):
        super().setUp()
        self.add_command("krunkit")

    def test_a_krunkit_vm_ai_ui_made_keeps_docker_on_its_data_disk_after_a_restart(self):
        self.run_ai_ui("start")
        for step in ("stop", "start"):  # colima restart
            self.colima(step)
        self.ok("start")
        self.assertFalse((self.state / "root-disk").exists())

    def test_docker_on_the_root_disk_stops_ai_ui_before_it_pulls_and_a_restart_mends_it(self):
        # A krunkit VM made without the boot step, by hand or by an older ai-ui, after its first boot.
        self.write_override(VIRTIOFS)
        self.colima("start", "--vm-type", "krunkit")
        self.colima("stop")
        result = self.run_ai_ui("start")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Error: Docker in the colima VM runs on the VM's root disk, not its data disk", result.stderr)
        self.assertIn("then run this again: colima restart", result.stderr)
        self.assertNotIn(" pull ", " ".join(self.calls()))
        self.assertEqual(self.override.read_text(), VIRTIOFS + DATA_DISK)
        for step in ("stop", "start"):  # colima restart
            self.colima(step)
        self.ok("start")
        self.assertTrue(self.runs("colima"))

    def test_a_vm_that_is_not_krunkit_keeps_its_override_when_docker_runs_on_its_root_disk(self):
        # The boot step mends krunkit only, and virtiofs stops a QEMU VM from starting.
        self.colima("start", "--vm-type", "qemu")
        (self.state / "root-disk").touch()
        result = self.run_ai_ui("start")
        self.assertEqual(result.returncode, 1)
        self.assertIn("colima restart", result.stderr)
        self.assertFalse(self.override.exists())

    def test_a_vm_without_a_data_disk_passes_and_a_question_with_no_answer_only_warns(self):
        # Colima kept Docker on the root disk by design before it had a data disk.
        (self.state / "one-disk").touch()
        result = self.ok("start")
        self.assertNotIn("Warning", result.stderr)
        for fault in ("fail-ssh", "no-findmnt"):
            with self.subTest(fault):
                (self.state / fault).touch()
                result = self.ok("start")
                self.assertIn("Warning: could not ask the colima VM which disk Docker uses", result.stderr)
                (self.state / fault).unlink()

    def test_a_probe_that_hangs_only_warns(self):
        # colima ssh runs limactl shell, which runs ssh; each holds the probe's output until it ends.
        (self.state / "colima-vm").touch()
        (self.state / "hang-ssh").touch()
        began = time.monotonic()
        result = self.ok("start")
        self.assertLess(time.monotonic() - began, 25)
        self.assertIn("Warning: could not ask the colima VM which disk Docker uses", result.stderr)
        self.assertTrue(self.runs("colima"))


def functions(script):
    """The names of a script's top-level shell functions."""
    return set(re.findall(r"^([a-z_]+)\(\) \{", script.read_text(), re.M))


class RuntimeLib(unittest.TestCase):
    """ai-ui sources lib/sage-runtime.sh, the tap's copy, so sage-runtime, trellis-crm and ai-ui share one runtime code."""

    def test_ai_ui_defines_none_of_the_shared_functions_again(self):
        self.assertTrue(functions(LIB))
        self.assertEqual(functions(AI_UI) & functions(LIB), set())

    @unittest.skipUnless((TAP / "lib" / "sage-runtime.sh").exists(), "needs the homebrew-apps checkout beside AI-UI")
    def test_the_copy_is_the_taps_byte_for_byte(self):
        self.assertTrue(filecmp.cmp(LIB, TAP / "lib" / "sage-runtime.sh", shallow=False),
                        "cli/lib/sage-runtime.sh differs from the tap's lib/sage-runtime.sh. Edit the tap's, then: make runtime_sync")


class RuntimeFlag(Mac):
    DOCKER_SETTINGS = "Library/Group Containers/group.com.docker/settings-store.json"

    def test_docker_desktop_that_ran_before_starts_hidden_in_the_background(self):
        self.install("Docker")
        (self.home / self.DOCKER_SETTINGS).parent.mkdir(parents=True)
        (self.home / self.DOCKER_SETTINGS).touch()
        self.ok("start", "--runtime", "docker-desktop", "--port", "9090")
        self.assertIn("open -g -j -a Docker", self.calls())
        self.assertIn("docker desktop-linux run -d -p 9090:8080", " ".join(self.calls()))
        self.assertFalse([call for call in self.calls() if call.startswith("colima")])  # no data-disk question
        self.assertEqual(self.saved_runtime(), "docker-desktop")

    def test_docker_desktops_first_start_stays_in_view(self):
        self.install("Docker")
        result = self.run_ai_ui("start", "--runtime", "docker-desktop")
        self.assertIn("open -a Docker", self.calls())
        self.assertIn("setup screens", result.stdout)

    def test_orbstack_that_ran_before_starts_hidden_and_runs_sage(self):
        self.install("OrbStack")
        (self.home / ".orbstack").mkdir()
        self.ok("start", "--runtime", "orbstack")
        self.assertIn("open -g -j -a OrbStack", self.calls())
        self.assertTrue(self.runs("orbstack"))
        self.assertEqual(self.saved_runtime(), "orbstack")

    def test_a_runtime_that_is_not_installed_says_how_to_get_it_or_to_use_colima(self):
        # Docker Desktop, saved by an older start, may since have gone from the Mac.
        self.save_runtime("docker-desktop")
        for args, install in (((), "brew install --cask docker-desktop"),
                              (("--runtime", "orbstack"), "brew install --cask orbstack")):
            with self.subTest(args):
                result = self.run_ai_ui("start", *args)
                self.assertEqual(result.returncode, 1)
                self.assertIn("Run Sage in Colima: ai-ui start --runtime colima", result.stderr)
                self.assertIn(install, result.stderr)
                self.assertNotIn("run", " ".join(self.calls()))

    def test_an_unknown_runtime_is_refused(self):
        result = self.run_ai_ui("start", "--runtime", "podman")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Use one of: colima docker-desktop orbstack", result.stderr)
        self.assertIsNone(self.saved_runtime())


class OtherCommands(Mac):
    def test_they_follow_the_last_runtime_used_without_saving_or_starting_it(self):
        (self.state / "current-context").write_text("desktop-linux\n")
        self.run_ai_ui("status")
        self.assertTrue(self.calls())
        self.assertTrue(all(call.startswith("docker desktop-linux ") for call in self.calls()), self.calls())
        self.assertIsNone(self.saved_runtime())

    def test_update_starts_the_runtime_before_it_pulls(self):
        self.run_ai_ui("update")
        calls = self.calls()
        self.assertLess(next(i for i, call in enumerate(calls) if call.startswith("colima start")),
                        next(i for i, call in enumerate(calls) if " pull " in call))


class DataVolume(Mac):
    def test_sage_ai_volume_picks_where_the_data_lives(self):
        self.env["SAGE_AI_VOLUME"] = str(self.home / "SageData" / "ai-ui")
        self.ok("start")
        self.assertIn(f"-v {self.home}/SageData/ai-ui:/app/backend/data", " ".join(self.calls()))


class ReachTheMac(Mac):
    """Sage reaches Ollama on the Mac as host.docker.internal, which Linux resolves only when docker run names it."""

    def test_start_dev_and_try_name_the_mac_for_the_container(self):
        self.add_command("curl", "echo '[]'")  # try's personas: none, at once
        self.save_runtime("colima")
        (self.home / ".sage-is" / "try.env").write_text("TRY_SAGE_LLM_API_URL=http://llm\nTRY_SAGE_LLM_API_KEY=k\n")
        source = self.home / "src" / "ai-ui"
        source.mkdir(parents=True)
        for command in (("start",), ("dev", "--dir", str(source)), ("try",)):
            with self.subTest(command[0]):
                (self.state / "calls").unlink(missing_ok=True)
                self.ok(*command)
                runs = self.runs("colima")
                self.assertEqual(len(runs), 1, self.calls())
                self.assertIn(f" {HOST_ENTRY} ", runs[0])


class DevMode(Mac):
    """dev mounts a checkout into the container. Colima shares only the home folder; Docker Desktop shares more."""

    def setUp(self):
        super().setUp()
        self.source = self.home / "src" / "ai-ui"
        self.source.mkdir(parents=True)
        self.elsewhere = self.home.parent / "elsewhere"
        self.elsewhere.mkdir()

    def test_the_reloader_polls_for_edits_made_on_the_mac(self):
        self.ok("dev", "--dir", str(self.source))
        run = self.runs("colima")[0]
        self.assertIn(f" -v {self.source}/app/backend:/app/backend ", run)
        self.assertIn(" -e WATCHFILES_FORCE_POLLING=true ", run)

    def test_on_colima_a_checkout_outside_the_home_folder_is_refused_before_anything_starts(self):
        result = self.run_ai_ui("dev", "--dir", str(self.elsewhere))
        self.assertEqual(result.returncode, 1)
        self.assertIn(f"Error: {self.elsewhere} is outside your home folder, the only one Colima shares with containers.",
                      result.stderr)
        self.assertEqual(self.calls(), ["docker default context show"])  # ask_runtime's look at docker's context
        self.assertFalse((self.home / ".sage-is" / "projects").exists())

    def test_a_relative_dir_counts_from_where_you_are(self):
        self.ok("dev", "--dir", "src/ai-ui", cwd=self.home)
        self.assertIn(f" -v {self.source}/app/src:/app/src ", self.runs("colima")[0])
        self.assertEqual((self.home / ".sage-is" / "projects").read_text(), f"ai-ui={self.source}\n")

    def test_docker_desktop_still_runs_a_checkout_outside_the_home_folder(self):
        self.install("Docker")
        self.ok("dev", "--dir", str(self.elsewhere), "--runtime", "docker-desktop")
        self.assertIn(f" -v {self.elsewhere}/app/src:/app/src ", self.runs("desktop-linux")[0])


class Migrate(Mac):
    """ai-ui migrate moves Sage's own data from Docker Desktop or OrbStack to Colima, and starts Sage there."""

    def setUp(self):
        super().setUp()
        self.add_command("krunkit")
        self.install("Docker")
        self.running("desktop-linux")
        self.save_runtime("docker-desktop")
        self.volume("desktop-linux", "sage-ai-data", {"webui.db": "db", "uploads/a.txt": "a"})
        self.app("desktop-linux", "ghcr.io/sage-is/ai-ui:3.1.0", 9090)

    def test_it_stops_sage_copies_its_data_and_starts_it_in_colima_with_the_same_tag_and_port(self):
        result = self.ok("migrate")
        calls = self.calls()
        stop = calls.index("docker desktop-linux stop sage-ai sage-try")
        self.assertLess(stop, next(i for i, call in enumerate(calls) if "-cf /stage/sage-ai-data.tar" in call))
        self.assertEqual((self.state / "vol-colima" / "sage-ai-data" / "uploads" / "a.txt").read_text(), "a")
        self.assertTrue((self.state / "vol-desktop-linux" / "sage-ai-data" / "webui.db").exists())  # its own copy stays
        self.assertFalse((self.state / "vol-colima" / "sage-try-data").exists())  # no trial to move
        self.assertRegex((self.home / ".sage-is" / "migrated").read_text(), r"^sage-ai-data docker-desktop colima 4 \d+\n$")
        self.assertEqual(list((self.home / ".sage-is" / "staging").iterdir()), [])
        self.assertEqual(self.saved_runtime(), "colima")
        self.assertEqual(self.docker_context(), "colima")  # new shells follow Sage, as sage-runtime use leaves them
        runs = self.runs("colima")
        self.assertEqual(len(runs), 1)
        self.assertTrue(runs[0].startswith("docker colima run -d -p 9090:8080 "), runs[0])
        self.assertTrue(runs[0].endswith(" ghcr.io/sage-is/ai-ui:3.1.0"), runs[0])
        self.assertFalse(self.runs("desktop-linux"))
        self.assertIn("docker-desktop keeps its own copy of Sage's data. Go back any time: ai-ui start --runtime docker-desktop",
                      result.stdout)
        self.assertEqual(result.stdout.splitlines()[-1],
                         "Other apps' data stays in docker-desktop. sage-runtime migrate --from docker-desktop moves it all"
                         " (brew tap sage-is/apps && brew tap libkrun/krun && brew trust --tap sage-is/apps libkrun/krun && brew install sage-runtime).")

    def test_orbstack_moves_too_with_the_trial_volume(self):
        self.install("OrbStack")
        self.running("orbstack")
        self.save_runtime("orbstack")
        self.volume("orbstack", "sage-ai-data", {"webui.db": "db"})
        self.volume("orbstack", "sage-try-data", {"webui.db": "trial"})
        self.ok("migrate")
        self.assertIn("docker orbstack stop sage-ai sage-try", self.calls())
        for name, text in (("sage-ai-data", "db"), ("sage-try-data", "trial")):
            self.assertEqual((self.state / "vol-colima" / name / "webui.db").read_text(), text)
        self.assertEqual(self.saved_runtime(), "colima")

    def test_a_dry_run_lists_sages_volumes_and_changes_nothing(self):
        self.volume("desktop-linux", "sage-try-data", {"webui.db": "trial"})
        result = self.ok("migrate", "--dry-run")
        for line in ("Would copy volume sage-ai-data from docker-desktop to colima.",
                     "Would copy volume sage-try-data from docker-desktop to colima.",
                     "Would stop Sage in docker-desktop, make colima ai-ui's runtime and start ghcr.io/sage-is/ai-ui:3.1.0"
                     " there on port 9090. docker-desktop keeps its copy.",
                     "Dry run: nothing changed. Move: ai-ui migrate"):
            self.assertIn(line + "\n", result.stdout)
        self.assertFalse([call for call in self.calls()
                          if call.startswith("colima start") or " stop " in call or " run " in call])
        self.assertEqual(self.saved_runtime(), "docker-desktop")
        self.assertFalse((self.state / "vol-colima").exists())

    def test_an_engine_that_never_answers_about_sage_leaves_the_pinned_tag_and_port(self):
        (self.state / "hang-inspect").touch()
        began = time.monotonic()
        result = self.ok("migrate", "--dry-run")
        self.assertLess(time.monotonic() - began, 25)
        self.assertIn("start ghcr.io/sage-is/ai-ui:3.2.0 there on port 8080.", result.stdout)

    def test_data_in_colima_that_no_copy_vouches_for_stops_the_move_before_sage_stops(self):
        self.running("colima")
        self.volume("colima", "sage-ai-data", {"webui.db": "other"})
        result = self.run_ai_ui("migrate")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Error: colima already has a volume sage-ai-data with data that no copy from docker-desktop"
                      " vouches for, so nothing was copied.", result.stderr)
        self.assertIn("sage-runtime copy-volume sage-ai-data --from docker-desktop --to colima --force", result.stderr)
        self.assertNotIn(" stop ", " ".join(self.calls()))
        self.assertEqual((self.state / "vol-colima" / "sage-ai-data" / "webui.db").read_text(), "other")
        self.assertEqual(self.saved_runtime(), "docker-desktop")

    def test_a_refusal_after_sage_stops_leaves_sage_and_dockers_context_where_they_were(self):
        # The copy checks the source only once Sage is stopped; here a backup job holds Sage's volume.
        (self.state / "current-context").write_text("desktop-linux\n")
        (self.state / "run-desktop-linux" / "backup").write_text("sage-ai-data")
        result = self.run_ai_ui("migrate")
        self.assertEqual(result.returncode, 1)
        self.assertIn("running containers use these volumes, so nothing was copied", result.stderr)
        self.assertIn("docker desktop-linux stop sage-ai sage-try", self.calls())
        self.assertTrue((self.state / "run-desktop-linux" / "sage-ai").exists(), self.calls())
        self.assertIn("Started Sage again in docker-desktop.\n", result.stderr)
        self.assertEqual(self.saved_runtime(), "docker-desktop")
        self.assertEqual(self.docker_context(), "desktop-linux")  # colima start took it; the refusal gives it back

    def test_a_login_helper_that_left_with_docker_desktop_is_dropped_before_the_copy_pulls(self):
        # OrbStack is in use and Docker Desktop has gone, leaving "credsStore": "desktop": each pull fails until it goes.
        config = self.home / ".docker" / "config.json"
        config.parent.mkdir()
        config.write_text('{"auths": {}, "credsStore": "desktop"}\n')
        self.add_command("docker", f'store="$(plutil -extract credsStore raw -o - "{config}" 2>/dev/null)" || store=""\n'
                                   'if [[ -n "$store" && ( " $* " == *" run "* || " $* " == *" pull "* ) ]] \\\n'
                                   '   && ! command -v "docker-credential-$store" >/dev/null; then\n'
                                   '  echo "error getting credentials: no docker-credential-$store" >&2; exit 1\n'
                                   'fi\n'
                                   f'exec "{self.stand_ins}/docker" "$@"')
        self.install("OrbStack")
        self.running("orbstack")
        self.save_runtime("orbstack")
        self.volume("orbstack", "sage-ai-data", {"webui.db": "db"})
        result = self.ok("migrate")
        self.assertIn("credsStore: removed desktop, which has no helper here", result.stdout)
        self.assertNotIn("credsStore", config.read_text())
        self.assertEqual((self.state / "vol-colima" / "sage-ai-data" / "webui.db").read_text(), "db")
        self.assertEqual(self.saved_runtime(), "colima")

    def test_a_rerun_after_a_stop_partway_goes_on(self):
        self.ok("migrate")
        self.save_runtime("docker-desktop")  # as if the move stopped once the copy was recorded
        result = self.ok("migrate")
        self.assertIn("Skipping volume sage-ai-data: copied from docker-desktop before, and unchanged there since.",
                      result.stdout)
        self.assertEqual(self.saved_runtime(), "colima")

    def test_data_in_a_folder_of_the_home_folder_needs_no_copy_and_one_elsewhere_is_refused(self):
        folder = self.home / "SageData" / "ai-ui"
        self.env["SAGE_AI_VOLUME"] = str(folder)
        result = self.ok("migrate")
        self.assertIn(f"Sage's data is in {folder} on this Mac, so it needs no copy.", result.stdout)
        self.assertFalse([call for call in self.calls() if "/stage/" in call])
        self.assertIn(f" -v {folder}:/app/backend/data ", self.runs("colima")[0])
        self.save_runtime("docker-desktop")
        (self.state / "calls").unlink()
        self.env["SAGE_AI_VOLUME"] = str(self.home.parent / "SageData")
        result = self.run_ai_ui("migrate")
        self.assertEqual(result.returncode, 1)
        self.assertIn("outside your home folder, the only one Colima shares with containers", result.stderr)
        self.assertNotIn(" stop ", " ".join(self.calls()))

    def test_without_krunkit_it_moves_to_a_vz_vm_and_says_how_to_get_krunkit(self):
        (self.bin / "krunkit").unlink()
        result = self.ok("migrate")
        self.assertIn("colima start --profile default --vm-type vz --vz-rosetta --mount-type virtiofs --mount-inotify"
                      " --memory 8 --cpu 5 --disk 100", self.calls())
        self.assertIn("krunkit is not installed, so Colima runs Sage on a vz VM. Get it, then make the VM krunkit with"
                      f" ai-ui migrate: {KRUNKIT_INSTALL}\n", result.stdout)
        self.assertEqual((self.state / "vol-colima" / "sage-ai-data" / "webui.db").read_text(), "db")

    def test_on_a_vz_colima_vm_it_makes_the_vm_krunkit_instead(self):
        self.save_runtime("colima")
        self.colima("start", "--vm-type", "vz")
        self.colima("stop")
        result = self.ok("migrate", "--dry-run")
        self.assertIn("The Colima VM default is vz: 8 GiB memory, 5 CPUs, 100 GiB disk.", result.stdout)
        self.assertIn("Dry run: nothing changed. Convert: ai-ui migrate --yes", result.stdout)
        self.assertNotIn("colima delete --force", self.calls())
        result = self.ok("migrate")
        self.assertIn("colima delete --force", self.calls())
        self.assertIn("The Colima VM default is krunkit now", result.stdout)
        self.assertEqual((self.home / ".colima/_lima/colima/lima.yaml").read_text(), "vmType: krunkit\n")


class Offer(Mac):
    """start and update offer once to move Sage to Colima, or a vz VM to krunkit, and remember the answer."""

    def setUp(self):
        super().setUp()
        self.add_command("krunkit")
        self.install("Docker")
        self.save_runtime("docker-desktop")  # as a Mac that ran AI-UI 3.2.0 on Docker Desktop
        self.volume("desktop-linux", "sage-ai-data", {"webui.db": "db"})

    def test_no_keeps_docker_desktop_and_a_second_start_does_not_ask(self):
        result = self.ok("start", answer="n\n")
        self.assertIn("Sage runs in docker-desktop. Colima is free, and its krunkit VM on Apple Silicon gives memory back"
                      " to macOS. docker-desktop keeps its copy of Sage's data.\n", result.stderr)
        self.assertIn(MOVE_QUESTION, result.stderr)
        self.assertEqual(self.offers(), "ai-ui colima no\n")
        self.assertTrue(self.runs("desktop-linux"))
        self.assertFalse([call for call in self.calls() if call.startswith("colima")])
        result = self.ok("start", answer="y\n")  # it would move, were it asked
        self.assertNotIn(MOVE_QUESTION, result.stderr)
        self.assertEqual(self.saved_runtime(), "docker-desktop")
        self.assertFalse([call for call in self.calls() if call.startswith("colima")])

    def test_yes_moves_sage_and_starts_it_in_colima(self):
        result = self.ok("start", "--port", "9191", answer="y\n")
        self.assertEqual(self.offers(), "ai-ui colima yes\n")
        self.assertEqual(self.saved_runtime(), "colima")
        self.assertEqual((self.state / "vol-colima" / "sage-ai-data" / "webui.db").read_text(), "db")
        self.assertTrue(self.runs("colima")[0].startswith("docker colima run -d -p 9191:8080 "))
        self.assertFalse(self.runs("desktop-linux"))
        self.assertTrue(result.stdout.splitlines()[-1].startswith("Other apps' data stays in docker-desktop."))

    def test_update_asks_before_it_pulls_into_the_runtime_it_leaves(self):
        result = self.ok("update", answer="y\n")
        self.assertIn(MOVE_QUESTION, result.stderr)
        self.assertEqual(self.offers(), "ai-ui colima yes\n")
        self.assertFalse([call for call in self.calls() if call.startswith("docker desktop-linux pull ")])
        self.assertTrue(self.runs("colima"))

    def test_a_first_start_that_picks_docker_desktop_is_offered_the_move(self):
        (self.home / ".sage-is" / "runtime").unlink()
        (self.state / "current-context").write_text("desktop-linux\n")
        result = self.ok("start", answer="\nn\n")
        self.assertIn("Runtime [docker-desktop]:", result.stderr)
        self.assertIn(MOVE_QUESTION, result.stderr)
        self.assertEqual(self.offers(), "ai-ui colima no\n")

    def test_a_yes_whose_move_stops_partway_asks_again(self):
        # Its error says to run this again, which must not start Sage where it was without a word.
        (self.state / "run-desktop-linux").mkdir()
        (self.state / "run-desktop-linux" / "backup").write_text("sage-ai-data")
        result = self.run_ai_ui("start", answer="y\n")
        self.assertEqual(result.returncode, 1)
        self.assertIn("running containers use these volumes, so nothing was copied", result.stderr)
        self.assertIsNone(self.offers())
        (self.state / "run-desktop-linux" / "backup").unlink()
        result = self.ok("start", answer="y\n")
        self.assertIn(MOVE_QUESTION, result.stderr)
        self.assertEqual(self.offers(), "ai-ui colima yes\n")
        self.assertEqual(self.saved_runtime(), "colima")

    def test_without_a_terminal_one_line_says_how_and_nothing_is_remembered(self):
        result = self.ok("start")
        hints = [line for line in result.stdout.splitlines() if "ai-ui migrate" in line]
        self.assertEqual(hints, ["Sage runs in docker-desktop. Colima is free, and its krunkit VM on Apple Silicon gives"
                                 " memory back to macOS. Move Sage there: ai-ui migrate"])
        self.assertIsNone(self.offers())
        self.assertTrue(self.runs("desktop-linux"))

    def test_a_runtime_named_on_the_command_line_is_not_questioned(self):
        result = self.ok("start", "--runtime", "docker-desktop", answer="y\n")
        self.assertNotIn(MOVE_QUESTION, result.stderr)
        self.assertNotIn("ai-ui migrate", result.stdout)
        self.assertIsNone(self.offers())
        self.assertTrue(self.runs("desktop-linux"))

    def vz_vm(self):
        self.save_runtime("colima")
        self.colima("start", "--vm-type", "vz")
        self.colima("stop")

    def test_a_vz_vm_on_apple_silicon_is_offered_krunkit_and_yes_converts_it(self):
        self.vz_vm()
        result = self.ok("start", answer="y\n")
        self.assertIn(KRUNKIT_QUESTION, result.stderr)
        self.assertEqual(self.offers(), "ai-ui krunkit yes\n")
        self.assertIn("colima delete --force", self.calls())
        self.assertEqual((self.home / ".colima/_lima/colima/lima.yaml").read_text(), "vmType: krunkit\n")
        self.assertTrue(self.runs("colima"))

    def test_a_vz_vm_without_krunkit_hears_how_to_get_it_once_and_is_asked_once_it_is_there(self):
        # ai-ui 3.2.0 made vz VMs, and its formula cannot depend on krunkit's tap.
        (self.bin / "krunkit").unlink()
        self.vz_vm()
        result = self.ok("start", answer="y\n")
        self.assertIn(f"A krunkit VM gives it back to macOS. Get krunkit, then run ai-ui migrate: {KRUNKIT_INSTALL}\n",
                      result.stdout)
        self.assertNotIn(KRUNKIT_QUESTION, result.stderr)
        self.assertEqual(self.offers(), "ai-ui krunkit-install shown\n")
        result = self.ok("start", answer="y\n")
        self.assertNotIn(KRUNKIT_INSTALL, result.stdout)
        self.assertEqual(self.offers(), "ai-ui krunkit-install shown\n")
        self.assertNotIn("colima delete --force", self.calls())
        self.add_command("krunkit")
        result = self.ok("start", answer="n\n")
        self.assertIn(KRUNKIT_QUESTION, result.stderr)
        self.assertEqual(self.offers(), "ai-ui krunkit-install shown\nai-ui krunkit no\n")
        self.assertNotIn("colima delete --force", self.calls())

    def test_intel_and_a_krunkit_vm_are_not_asked(self):
        self.vz_vm()
        self.hardware(arch="x86_64")
        result = self.ok("start", answer="y\n")
        self.assertNotIn(KRUNKIT_QUESTION, result.stderr)
        self.hardware(arch="arm64")
        (self.home / ".colima/_lima/colima/lima.yaml").write_text("vmType: krunkit\n")
        self.write_override(VIRTIOFS + DATA_DISK)
        result = self.ok("start", answer="y\n")
        self.assertNotIn(KRUNKIT_QUESTION, result.stderr)
        self.assertIsNone(self.offers())


class Install(Mac):
    """ai-ui finds lib/, nuke-sage and distribution.env beside itself, where the formula installs them."""

    def libexec(self, *names):
        """A brew install's libexec, with these of ai-ui's files: ai-ui itself, and lib/ unless left out."""
        libexec = self.home / "keg" / "libexec"
        libexec.mkdir(parents=True)
        for source in (AI_UI, AI_UI.parent / "nuke-sage", AI_UI.parent.parent / "distribution.env"):
            if source.name in names or source == AI_UI:
                shutil.copy2(source, libexec / source.name)
        if "lib" in names:
            shutil.copytree(LIB.parent, libexec / "lib")
        return libexec

    def test_a_link_to_ai_ui_finds_the_files_beside_it(self):
        link = self.bin / "ai-ui"
        link.symlink_to(self.libexec("lib", "distribution.env") / "ai-ui")
        result = self.ok("version", cli=link)
        self.assertNotIn("(server latest)", result.stdout)  # distribution.env's pin, not the fallback

    def test_without_its_lib_ai_ui_says_how_to_put_it_back(self):
        result = self.run_ai_ui("version", cli=self.libexec() / "ai-ui")
        self.assertEqual(result.returncode, 1)
        self.assertIn("lib/sage-runtime.sh is missing. Reinstall ai-ui (brew reinstall ai-ui), or in an AI-UI checkout"
                      " run: make runtime_sync", result.stderr)


class Nuke(Install):
    def test_a_brew_install_finds_nuke_sage_and_passes_its_flags(self):
        libexec = self.libexec("lib", "nuke-sage", "distribution.env")  # the formula installs them side by side
        result = self.ok("nuke", "--all", "--dry-run", cli=libexec / "ai-ui")
        self.assertIn("Mode: --all (keep config vaults)", result.stdout)

    def test_genesis_lists_every_runtime_on_the_mac(self):
        self.install("Docker")
        self.install("OrbStack")
        result = self.run_ai_ui("nuke", "--genesis", "--dry-run")
        for provider in ("Docker Desktop", "OrbStack", "Colima"):
            self.assertIn(f"Docker:      {provider}", result.stdout)
        self.assertIn("uninstall your Docker providers: desktop orbstack colima", result.stdout)
        self.assertIn("[dry-run] Nothing was removed.", result.stdout)

    def test_nuke_works_in_the_runtime_this_mac_chose(self):
        self.save_runtime("docker-desktop")
        (self.state / "running-desktop-linux").touch()
        self.run_ai_ui("nuke", "--dry-run")
        self.assertIn("docker desktop-linux inspect sage-ai", self.calls())


class CredentialHelper(Mac):
    """Docker Desktop leaves "credsStore": "desktop" behind. Its helper only wraps the Keychain's, and leaves with the app."""

    def write_docker_config(self):
        config = self.home / ".docker" / "config.json"
        config.parent.mkdir()
        config.write_text('{"auths": {}, "credsStore": "desktop", "currentContext": "colima"}\n')
        return config

    def backups(self, config):
        return [backup.read_text() for backup in config.parent.glob("config.json.*.bak")]

    def test_with_colima_in_use_docker_keeps_its_logins_with_the_keychain_helper(self):
        config = self.write_docker_config()
        for helper in ("desktop", "osxkeychain"):
            self.add_command(f"docker-credential-{helper}")
        result = self.ok("start")
        self.assertEqual(json.loads(config.read_text())["credsStore"], "osxkeychain")
        self.assertEqual(len(self.backups(config)), 1)
        self.assertIn("credsStore: desktop goes through Docker Desktop; now osxkeychain", result.stdout)

    def test_docker_desktop_in_use_keeps_its_own_helper(self):
        config = self.write_docker_config()
        for helper in ("desktop", "osxkeychain"):
            self.add_command(f"docker-credential-{helper}")
        self.install("Docker")
        self.ok("start", "--runtime", "docker-desktop")
        self.assertEqual(json.loads(config.read_text())["credsStore"], "desktop")
        self.assertEqual(self.backups(config), [])

    def test_a_missing_helper_is_dropped_before_the_pull_with_a_backup(self):
        config = self.write_docker_config()
        result = self.ok("start")
        self.assertNotIn("credsStore", config.read_text())
        self.assertIn('"currentContext":"colima"', config.read_text())
        backups = self.backups(config)
        self.assertEqual(len(backups), 1)
        self.assertIn('"credsStore": "desktop"', backups[0])
        self.assertIn("credsStore: removed desktop, which has no helper here", result.stdout)


FORMULA_SCRIPT = TAP / "scripts" / "ai-ui-formula.sh"
CAVEAT = "      On a Mac using Docker Desktop or OrbStack? `ai-ui migrate` moves Sage to Colima.\n"


@unittest.skipUnless(FORMULA_SCRIPT.exists(), "needs the homebrew-apps checkout beside AI-UI")
class Formula(unittest.TestCase):
    """The tap's formula script installs cli/lib beside ai-ui and names ai-ui migrate in the caveats, once."""

    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        root = Path(scratch.name)
        self.tap, self.bin = root / "tap", root / "bin"
        for folder in (self.tap / "Formula", self.tap / "scripts", self.bin):
            folder.mkdir(parents=True)
        shutil.copy2(TAP / "Formula" / "ai-ui.rb", self.tap / "Formula")
        shutil.copy2(FORMULA_SCRIPT, self.tap / "scripts")
        self.formula = self.tap / "Formula" / "ai-ui.rb"
        self.tarball = root / "release.tar.gz"
        write_command(self.bin / "curl", 'while [[ $# -gt 0 ]]; do [[ "$1" != -o ]] || cp "$TARBALL" "$2"; shift; done')

    def release(self, *paths):
        """An AI-UI 3.9.9 release tarball holding these paths."""
        with tarfile.open(self.tarball, "w:gz") as tar:
            for path in paths:
                data = b"SERVER_TAG=3.9.9\n" if path == "distribution.env" else b"#!/bin/bash\n"
                info = tarfile.TarInfo(f"AI-UI-3.9.9/{path}")
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))

    def run_script(self):
        return subprocess.run(["bash", "scripts/ai-ui-formula.sh", "3.9.9"], cwd=self.tap, capture_output=True, text=True,
                              env={"PATH": f"{self.bin}:/usr/bin:/bin", "TARBALL": str(self.tarball)}, timeout=30)

    def test_the_formula_installs_cli_lib_and_names_migrate_once(self):
        self.release("cli/ai-ui", "cli/nuke-sage", "cli/lib/sage-runtime.sh", "distribution.env")
        for _ in range(2):
            result = self.run_script()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            text = self.formula.read_text()
            self.assertEqual(text.count('    libexec.install "cli/ai-ui", "cli/nuke-sage", "cli/lib"\n'), 1, text)
            self.assertEqual(text.count(CAVEAT), 1, text)
            self.assertIn(CAVEAT + "\n      Pin a specific server version:\n", text)

    def test_a_release_without_cli_lib_is_refused(self):
        before = self.formula.read_text()
        self.release("cli/ai-ui", "cli/nuke-sage", "distribution.env")
        result = self.run_script()
        self.assertEqual(result.returncode, 1)
        self.assertIn("AI-UI v3.9.9 has no cli/lib/sage-runtime.sh", result.stderr)
        self.assertEqual(self.formula.read_text(), before)


if __name__ == "__main__":
    unittest.main()
