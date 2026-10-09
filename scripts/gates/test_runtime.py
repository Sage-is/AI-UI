"""The Makefile's docker preflights, disk gate and runtime targets, against stand-ins.

Nothing here reaches a real docker, colima, podman, gh or sage-runtime: each test
puts its own on a PATH that holds nothing else but the system's, with a HOME of its own.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

GATES = Path(__file__).resolve().parent
ROOT = GATES.parents[1]
PREFLIGHT = str(GATES / "docker-preflight.sh")
SYSTEM_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"
BUILD_VM = "sage-runtime build-vm, then DOCKER_CONTEXT=colima-build"
SAGE_RUNTIME_INSTALL = "brew tap sage-is/apps && brew tap libkrun/krun && brew trust --tap sage-is/apps libkrun/krun && brew install sage-runtime"
# The recipes that run linux/$ARCH containers.
SPRIG_RECIPES = [
    "backup-rclone",
    "dev-svelte",
    "docling",
    "export-document",
    "media-ffmpeg",
    "rag-loaders",
    "tika",
    "vector-chroma",
    "whisper",
]

# Stand-ins log each call. docker answers `context inspect` with $STATE/endpoint
# (none: the context is missing), `context show` with $DOCKER_CONTEXT, `ps` with
# $STATE/ps (`--context NAME ps` with $STATE/ps.NAME), `buildx version` once
# $STATE/buildx exists, `info` with $STATE/root, and refuses every `run`. curl never reaches the network: it answers only once
# $STATE/port5000 exists, as a registry in some VM would.
STUBS = {
    "docker": """echo "docker $*" >> "$STATE/calls"
case "$1 $2" in
  "context inspect") cat "$STATE/endpoint" 2>/dev/null || exit 1 ;;
  "context show")    echo "${DOCKER_CONTEXT:-colima}" ;;
  "ps --format")     cat "$STATE/ps" 2>/dev/null ;;
  "--context "*)     [ "$3" = ps ] && cat "$STATE/ps.$2" 2>/dev/null ;;
  "buildx version")  [ -e "$STATE/buildx" ] ;;
  "info --format")   cat "$STATE/root" 2>/dev/null ;;
  "run "*)           exit 1 ;;
esac""",
    "podman": 'echo "podman $*" >> "$STATE/calls"',
    "gh": 'echo "gh $*" >> "$STATE/calls"',
    "sage-runtime": 'echo "sage-runtime $*" >> "$STATE/calls"',
    "curl": 'echo "curl $*" >> "$STATE/calls"; [ -e "$STATE/port5000" ] || exit 7',
}


class Stand(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        # Resolved, as the gates resolve sockets: /var is a link to /private/var.
        self.tmp = Path(tmp.name).resolve()
        self.home, self.state, self.bin = (
            self.tmp / d for d in ("home", "state", "bin")
        )
        for d in (self.home, self.state, self.bin):
            d.mkdir()
        for name, body in STUBS.items():
            self.stub(name, body)
        self.env = {
            "PATH": f"{self.bin}:{SYSTEM_PATH}",
            "HOME": str(self.home),
            "STATE": str(self.state),
        }

    def stub(self, name, body):
        f = self.bin / name
        f.write_text("#!/bin/sh\n" + body + "\n")
        f.chmod(0o755)

    def sh(self, *cmd, cwd=ROOT, **env):
        r = subprocess.run(
            cmd,
            cwd=cwd,
            env={**self.env, **env},
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        return r.returncode, r.stdout + r.stderr

    def make(self, *args, cwd=ROOT, **env):
        return self.sh(
            "make",
            "-s",
            "-f",
            str(ROOT / "Makefile"),
            *args,
            "NOTIFY_DONE=true",
            cwd=cwd,
            **env,
        )

    def calls(self):
        f = self.state / "calls"
        return f.read_text() if f.exists() else ""

    def context(self, sock):
        (self.state / "endpoint").write_text(f"unix://{sock}\n")

    def colima(self, profile="default", vm_type="krunkit"):
        """A Colima profile's folder, as Colima writes it; returns its socket."""
        d = self.home / ".colima" / profile
        d.mkdir(parents=True)
        (d / "colima.yaml").write_text(f"cpu: 4\nvmType: {vm_type}\nrosetta: false\n")
        return d / "docker.sock"

    def docker_config(self, text, folder=None):
        folder = folder or self.home / ".docker"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "config.json").write_text(text)


class Amd64(Stand):
    def test_a_krunkit_vm_stops_amd64_work_with_the_build_vm_route(self):
        self.context(self.colima())
        rc, out = self.sh(PREFLIGHT, "amd64", "make it_build_amd64")
        self.assertEqual(rc, 1)
        self.assertIn(f"{BUILD_VM} make it_build_amd64", out)

    def test_the_build_vm_docker_desktop_and_orbstack_run_it(self):
        build = self.colima("build", "vz")
        for sock in (
            build,
            self.home / ".docker/run/docker.sock",
            self.home / ".orbstack/run/docker.sock",
        ):
            with self.subTest(sock=sock.parent.name):
                self.context(sock)
                self.assertEqual(self.sh(PREFLIGHT, "amd64", "make x"), (0, ""))

    def test_a_missing_context_leaves_the_build_to_say_so(self):
        self.assertEqual(self.sh(PREFLIGHT, "amd64", "make x"), (0, ""))

    def test_the_legacy_socket_and_a_linked_one_reach_the_default_vm(self):
        default = self.colima()
        default.touch()
        legacy = self.home / ".colima/docker.sock"
        legacy.touch()
        link = self.tmp / "docker.sock"
        # Relative, as ln -s writes it.
        link.symlink_to(Path("home/.colima/default/docker.sock"))
        for sock in (legacy, link):
            with self.subTest(sock=str(sock)):
                self.context(sock)
                rc, out = self.sh(PREFLIGHT, "amd64", "make x")
                self.assertEqual(rc, 1)
                self.assertIn(BUILD_VM, out)

    def test_amd64_targets_stop_on_a_krunkit_vm_before_they_build(self):
        self.context(self.colima())
        (self.state / "buildx").touch()
        for target in ("it_build_amd64", "cross_smoke", "catalog_build"):
            with self.subTest(target):
                rc, out = self.make(target)
                self.assertNotEqual(rc, 0)
                self.assertIn(f"{BUILD_VM} make {target}", out)
        # A registry started here would hold port 5000 against the build VM's.
        self.assertNotRegex(self.calls(), r"build --platform|local-registry")

    def test_release_and_multi_arch_targets_check_the_vm_before_anything_else(self):
        for target, then in (
            ("release_smoke", "case "),
            (
                "_it_build_multi_arch_push_GHCR",
                "buildx build --platform linux/amd64,linux/arm64",
            ),
            ("catalog_build", "docker-preflight.sh registry"),
        ):
            with self.subTest(target):
                out = self.make("-n", target)[1]
                at = out.find(f'docker-preflight.sh amd64 "make {target}"')
                self.assertGreaterEqual(at, 0)
                self.assertLess(at, out.find(then))
        self.assertNotIn(
            "docker-preflight.sh amd64",
            self.make("-n", "catalog_build", "ARCHES=arm64")[1],
        )

    def test_amd64_sprig_recipes_stop_on_a_krunkit_vm_before_they_run(self):
        self.context(self.colima())
        for name in SPRIG_RECIPES:
            with self.subTest(name):
                rc, out = self.sh(
                    str(ROOT / f"scripts/build-sprig-{name}.sh"),
                    cwd=self.tmp,
                    ARCH="amd64",
                )
                self.assertEqual(rc, 1)
                self.assertIn(f"{BUILD_VM} ARCH=amd64 ", out)
        self.assertNotRegex(self.calls(), r"docker run|curl")

    def test_arm64_sprig_recipes_build_on_the_krunkit_vm(self):
        self.context(self.colima())
        for name in SPRIG_RECIPES:
            with self.subTest(name):
                # Each may fail further on, against the stand-in docker; any
                # output lands in the temporary folder, not the checkout.
                out = self.sh(
                    str(ROOT / f"scripts/build-sprig-{name}.sh"),
                    cwd=self.tmp,
                    ARCH="arm64",
                )[1]
                self.assertNotIn(BUILD_VM, out)


class Buildx(Stand):
    def test_docker_without_buildx_stops_with_the_install_line(self):
        rc, out = self.sh(PREFLIGHT, "buildx", "docker")
        self.assertEqual(rc, 1)
        self.assertIn("brew install docker-buildx\n", out)
        self.context(self.home / ".orbstack/run/docker.sock")
        out = self.sh(PREFLIGHT, "buildx", "docker")[1]
        self.assertIn(
            "brew install docker-buildx (then: sage-runtime use orbstack)", out
        )

    def test_no_docker_names_podman_not_the_plugin(self):
        (self.bin / "docker").unlink()
        rc, out = self.make("it_build")
        self.assertNotEqual(rc, 0)
        self.assertIn("docker not found", out)
        self.assertIn("CONTAINER_RUNTIME=podman", out)
        self.assertNotIn("buildx not found", out)

    def test_docker_with_buildx_passes(self):
        (self.state / "buildx").touch()
        self.assertEqual(self.sh(PREFLIGHT, "buildx"), (0, ""))

    def test_podman_is_not_asked_about_dockers_plugin(self):
        self.assertEqual(self.sh(PREFLIGHT, "buildx", "podman"), (0, ""))
        self.assertNotIn("buildx", self.calls())

    def test_buildkit_targets_stop_without_buildx_before_they_build(self):
        for target in (
            "it_build",
            "it_build_no_cache",
            "it_build_amd64",
            "ensure_builder",
        ):
            with self.subTest(target):
                rc, out = self.make(target)
                self.assertNotEqual(rc, 0)
                self.assertIn("brew install docker-buildx", out)
        self.assertNotRegex(
            self.calls(), r"docker (buildx )?build |buildx (inspect|create|use)"
        )

    def test_podman_builds_without_dockers_plugin(self):
        rc, _ = self.make("it_build", CONTAINER_RUNTIME="podman")
        self.assertEqual(rc, 0)
        self.assertIn("podman build --load", self.calls())


class Credentials(Stand):
    def test_a_store_without_its_helper_stops_the_login(self):
        self.docker_config('{"auths":{},"credsStore":"fixture"}')
        rc, out = self.sh(PREFLIGHT, "creds")
        self.assertEqual(rc, 1)
        self.assertIn('credsStore "fixture"', out)
        self.assertNotIn("sage-runtime", out)

    def test_the_fix_names_the_runtime_in_use_not_colima(self):
        # sage-runtime use stops every other runtime: the line must not move anyone.
        self.docker_config('{"credsStore":"fixture"}')
        for sock, runtime in (
            (self.colima(), "colima"),
            (self.home / ".orbstack/run/docker.sock", "orbstack"),
            (self.home / ".docker/run/docker.sock", "docker-desktop"),
        ):
            with self.subTest(runtime):
                self.context(sock)
                out = self.sh(PREFLIGHT, "creds")[1]
                self.assertIn(f"Run: sage-runtime use {runtime}\n", out)

    def test_a_store_whose_helper_is_on_the_path_passes(self):
        self.docker_config('{\n  "credsStore": "fixture"\n}\n')
        self.stub("docker-credential-fixture", "true")
        self.assertEqual(self.sh(PREFLIGHT, "creds"), (0, ""))

    def test_no_store_and_no_config_pass(self):
        self.assertEqual(self.sh(PREFLIGHT, "creds"), (0, ""))
        self.docker_config('{"auths":{}}')
        self.assertEqual(self.sh(PREFLIGHT, "creds"), (0, ""))

    def test_docker_config_moves_it(self):
        elsewhere = self.tmp / "elsewhere"
        self.docker_config('{"credsStore":"fixture"}', elsewhere)
        self.assertEqual(self.sh(PREFLIGHT, "creds")[0], 0)
        self.assertEqual(
            self.sh(PREFLIGHT, "creds", DOCKER_CONFIG=str(elsewhere))[0], 1
        )

    def test_ghcr_login_checks_the_helper_before_it_logs_in(self):
        self.docker_config('{"credsStore":"fixture"}')
        rc, out = self.make("ghcr_login")
        self.assertNotEqual(rc, 0)
        self.assertIn('credsStore "fixture"', out)
        self.assertNotRegex(self.calls(), r"gh |docker login")


class Registry(Stand):
    def test_another_vms_registry_stops_a_second_one_on_its_folder(self):
        (self.state / "port5000").touch()
        for ctx, holder in (
            ("colima-build", "colima"),
            ("colima", "colima-build"),
            ("desktop-linux", "colima"),
            ("orbstack", "desktop-linux"),
        ):
            with self.subTest(ctx):
                for f in self.state.glob("ps.*"):
                    f.unlink()
                (self.state / f"ps.{holder}").write_text("sage-ai\nlocal-registry\n")
                rc, out = self.make("sprig_registry", DOCKER_CONTEXT=ctx)
                self.assertNotEqual(rc, 0)
                self.assertIn(f"docker --context {holder} stop local-registry", out)
        self.assertNotIn("docker run", self.calls())

    def test_a_holder_no_context_lists_gets_no_wrong_context(self):
        (self.state / "port5000").touch()
        rc, out = self.sh(PREFLIGHT, "registry")
        self.assertEqual(rc, 1)
        self.assertIn("docker context ls", out)
        self.assertNotIn("docker --context", out)

    def test_this_contexts_registry_or_a_free_port_passes(self):
        self.assertEqual(self.sh(PREFLIGHT, "registry"), (0, ""))
        (self.state / "port5000").touch()
        (self.state / "ps").write_text("sage-ai\nlocal-registry\n")
        self.assertEqual(self.sh(PREFLIGHT, "registry"), (0, ""))
        rc, out = self.make("sprig_registry")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("docker run", self.calls())

    def test_podman_looks_among_its_own_containers(self):
        (self.state / "port5000").touch()
        self.assertEqual(self.sh(PREFLIGHT, "registry", "podman")[0], 1)
        self.assertIn("podman ps --format", self.calls())

    def test_a_release_checks_it_before_the_tag(self):
        out = self.make("-n", "release_preflight", "RELEASE_VERSION=0.0.0")[1]
        at = out.find("docker-preflight.sh registry")
        self.assertGreaterEqual(at, 0)
        self.assertLess(at, out.find("git ls-remote"))


class DiskFree(Stand):
    def gate(self, need, **env):
        return self.sh(
            sys.executable, str(GATES / "docker-disk-free.py"), str(need), **env
        )

    def sparse(self, path, gib):
        """A disk image that holds nothing yet. The half GiB keeps a block or two from changing the GiB it reports."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.truncate(int((gib + 0.5) * (1 << 30)))

    def desktop(self):
        """Docker Desktop, installed, with its Docker.raw on a folder of its own."""
        data = self.tmp / "desktop-data"
        self.sparse(data / "Docker.raw", 0)
        settings = (
            self.home / "Library/Group Containers/group.com.docker/settings-store.json"
        )
        settings.parent.mkdir(parents=True)
        settings.write_text(
            json.dumps({"DataFolder": str(data), "DiskSizeMiB": 64 * 1024 + 512})
        )
        return data

    def test_colima_in_use_measures_its_own_disks_with_docker_desktop_installed(self):
        self.desktop()
        self.context(self.colima())
        disks = self.home / ".colima/_lima/_disks"
        self.assertNotIn("may still grow", self.gate(10**9)[1])  # no disk yet: no guess
        self.sparse(disks / "colima/datadisk", 3)
        rc, out = self.gate(10**9)
        self.assertEqual(rc, 1)
        self.assertIn("the host disk that holds Colima's VM disks has", out)
        self.assertIn(f"free: {disks}\n", out)
        self.assertIn("Colima's VM disk may still grow 3GiB.", out)
        self.assertIn("link it back", out)
        self.assertNotIn("Docker.raw", out)
        rc, out = self.gate(0)
        self.assertEqual(
            (rc, out.split("GiB")[1]),
            (0, " free on the host disk that holds Colima's VM disks\n"),
        )

    def test_the_legacy_socket_and_a_linked_one_measure_the_default_vms_disks(self):
        self.desktop()
        default = self.colima()
        default.touch()
        legacy = self.home / ".colima/docker.sock"
        legacy.touch()
        link = self.tmp / "docker.sock"
        link.symlink_to(default)
        disks = self.home / ".colima/_lima/_disks"
        self.sparse(disks / "colima/datadisk", 3)
        for sock in (legacy, link):
            with self.subTest(sock=str(sock)):
                self.context(sock)
                out = self.gate(10**9)[1]
                self.assertIn(f"free: {disks}\n", out)
                self.assertIn("Colima's VM disk may still grow 3GiB.", out)

    def test_the_build_vm_counts_its_own_disk(self):
        self.context(self.colima("build", "vz"))
        disks = self.home / ".colima/_lima/_disks"
        self.sparse(disks / "colima/datadisk", 3)
        self.sparse(disks / "colima-build/datadisk", 9)
        self.assertIn("Colima's VM disk may still grow 9GiB.", self.gate(10**9)[1])

    def test_lima_home_moves_the_disks(self):
        self.context(self.colima())
        lima = self.tmp / "lima"
        self.sparse(lima / "_disks/colima/datadisk", 5)
        out = self.gate(10**9, LIMA_HOME=str(lima))[1]
        self.assertIn(f"free: {lima / '_disks'}\n", out)
        self.assertIn("may still grow 5GiB.", out)

    def test_orbstack_measures_its_data_wherever_its_settings_put_it(self):
        self.desktop()
        self.context(self.home / ".orbstack/run/docker.sock")
        default = self.home / "Library/Group Containers/HUAQ24HBR6.dev.orbstack/data"
        default.mkdir(parents=True)
        out = self.gate(10**9)[1]
        self.assertIn("the host disk that holds OrbStack's data has", out)
        self.assertIn(f"free: {default}\n", out)
        self.assertIn("OrbStack, Settings, Storage", out)
        self.assertNotIn("may still grow", out)
        moved = self.tmp / "orbstack-data"
        moved.mkdir()
        (self.home / ".orbstack").mkdir()
        (self.home / ".orbstack/vmconfig.json").write_text(
            json.dumps({"data_dir": str(moved)})
        )
        self.assertIn(f"free: {moved}\n", self.gate(10**9)[1])

    def test_docker_desktop_in_use_measures_docker_raw_through_a_linked_socket(self):
        data = self.desktop()
        sock = self.home / ".docker/run/docker.sock"
        sock.parent.mkdir(parents=True)
        sock.touch()
        link = self.tmp / "docker.sock"
        link.symlink_to(sock)
        self.context(link)
        out = self.gate(10**9)[1]
        self.assertIn("the host disk that holds Docker Desktop's Docker.raw has", out)
        self.assertIn(f"free: {data}\n", out)
        self.assertIn("Docker.raw may still grow 64GiB.", out)
        self.assertIn("Docker Desktop, Settings, Resources", out)

    def test_any_other_socket_measures_dockers_own_root(self):
        self.desktop()
        self.context(self.tmp / "remote.sock")
        root = self.tmp / "docker-root"
        root.mkdir()
        (self.state / "root").write_text(f"{root}\n")
        out = self.gate(10**9)[1]
        self.assertIn("the host disk that holds Docker's data has", out)
        self.assertIn(f"free: {root}\n", out)
        self.assertIn(
            "Fix: free space on that volume, or override RELEASE_MIN_BUILD_DISK_GIB=<n>.",
            out,
        )


class Targets(Stand):
    def test_docker_runs_containers_even_with_podman_installed(self):
        self.assertRegex(self.make("-n", "it_stop")[1], r"(?m)^docker rm -f ")
        self.assertRegex(
            self.make("-n", "it_stop", CONTAINER_RUNTIME="podman")[1],
            r"(?m)^podman rm -f ",
        )

    def test_review_picks_its_runtime_the_same_way(self):
        line = next(
            x
            for x in (ROOT / "scripts/manual-check.sh").read_text().splitlines()
            if x.startswith("RUNTIME=")
        )
        self.assertEqual(
            self.sh("bash", "-c", f'{line}; echo "$RUNTIME"'), (0, "docker\n")
        )
        self.assertEqual(
            self.sh(
                "bash", "-c", f'{line}; echo "$RUNTIME"', CONTAINER_RUNTIME="podman"
            ),
            (0, "podman\n"),
        )

    def test_the_reload_gate_container_polls_for_edits(self):
        rc, _ = self.sh(str(GATES / "dev-reload/run-gate.sh"))
        self.assertNotEqual(rc, 0)
        run = next(x for x in self.calls().splitlines() if x.startswith("docker run "))
        self.assertIn("-e WATCHFILES_FORCE_POLLING=true", run)

    def test_convert_to_krunkit_hands_over_to_sage_runtime(self):
        self.assertEqual(self.make("convert_to_krunkit")[0], 0)
        self.assertEqual(self.make("convert_to_krunkit", "YES=1")[0], 0)
        self.assertEqual(self.make("migrate_to_colima", "DRY=1", "IMAGES=1")[0], 0)
        self.assertEqual(
            self.calls().splitlines(),
            [
                "sage-runtime convert",
                "sage-runtime convert --yes",
                "sage-runtime migrate --dry-run --images",
            ],
        )

    def test_only_yes_1_converts(self):
        # Convert deletes the VM and remakes it; YES=0 asks for the plan.
        for yes in ("YES=0", "YES=no", "YES="):
            self.assertEqual(self.make("convert_to_krunkit", yes)[0], 0)
        self.assertEqual(self.calls().splitlines(), ["sage-runtime convert"] * 3)

    def test_only_images_1_brings_images(self):
        # Images can run to tens of GB; IMAGES=0 must not copy them.
        for images in ("IMAGES=0", "IMAGES=no", "IMAGES="):
            self.assertEqual(self.make("migrate_to_colima", images)[0], 0)
        self.assertEqual(self.calls().splitlines(), ["sage-runtime migrate"] * 3)

    def test_without_sage_runtime_each_says_how_to_get_it(self):
        (self.bin / "sage-runtime").unlink()
        for target in ("convert_to_krunkit", "migrate_to_colima"):
            with self.subTest(target):
                rc, out = self.make(target)
                self.assertNotEqual(rc, 0)
                # A line of its own, so it pastes whole.
                self.assertIn(f": {SAGE_RUNTIME_INSTALL}\n", out)

    def test_runtime_sync_copies_the_taps_file(self):
        box, tap = self.tmp / "box", self.tmp / "tap"
        box.mkdir()
        (tap / "lib").mkdir(parents=True)
        (tap / "lib/sage-runtime.sh").write_text("# the tap's runtime file\n")
        rc, out = self.make("runtime_sync", f"SIBLING_HOMEBREW={tap}", cwd=box)
        self.assertEqual(rc, 0, out)
        self.assertEqual(
            (box / "cli/lib/sage-runtime.sh").read_bytes(),
            (tap / "lib/sage-runtime.sh").read_bytes(),
        )
        self.assertIn(
            "already equal",
            self.make("runtime_sync", f"SIBLING_HOMEBREW={tap}", cwd=box)[1],
        )

    def test_runtime_sync_refuses_without_the_tap_or_its_file(self):
        box, tap = self.tmp / "box", self.tmp / "tap"
        box.mkdir()
        rc, out = self.make("runtime_sync", f"SIBLING_HOMEBREW={tap}", cwd=box)
        self.assertNotEqual(rc, 0)
        self.assertIn(
            f"git clone https://github.com/Sage-is/homebrew-apps.git {tap}", out
        )
        tap.mkdir()
        rc, out = self.make("runtime_sync", f"SIBLING_HOMEBREW={tap}", cwd=box)
        self.assertNotEqual(rc, 0)
        self.assertIn(f"MISSING: {tap}/lib/sage-runtime.sh", out)
        self.assertFalse((box / "cli").exists())


if __name__ == "__main__":
    unittest.main()
