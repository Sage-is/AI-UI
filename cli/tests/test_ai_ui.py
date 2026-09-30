"""ai-ui's container runtime on macOS (Colima by default, Docker Desktop or OrbStack on request), and nuke across them."""

import os
import pty
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

AI_UI = Path(__file__).resolve().parent.parent / "ai-ui"

# Stand-ins log each call; `docker info` answers once the runtime's context is marked running.
STUBS = {
    "docker": """echo "docker ${DOCKER_CONTEXT:-} $*" >> "$STATE/calls"
case "$1" in
  info)    [[ -e "$STATE/running-${DOCKER_CONTEXT:-default}" ]] ;;
  context) cat "$STATE/current-context" 2>/dev/null || echo default ;;
esac""",
    "colima": """echo "colima $*" >> "$STATE/calls"
case "$1" in
  list)  if [[ -e "$STATE/colima-vm" ]]; then echo '{"name":"default","status":"Stopped"}'; fi ;;
  start) touch "$STATE/colima-vm" "$STATE/running-colima" ;;
esac""",
    "open": """echo "open $*" >> "$STATE/calls"
case "${@: -1}" in
  Docker)   touch "$STATE/running-desktop-linux" ;;
  OrbStack) touch "$STATE/running-orbstack" ;;
esac""",
}


@unittest.skipUnless(sys.platform == "darwin", "the runtime choice is macOS-only")
class Mac(unittest.TestCase):
    """A fake Mac: its own home, apps folder and stand-in commands."""

    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        root = Path(scratch.name)
        self.home, self.apps, self.state = root / "home", root / "Applications", root / "state"
        for folder in (self.home, self.apps, self.state, root / "bin"):
            folder.mkdir()
        for name, body in STUBS.items():
            stub = root / "bin" / name
            stub.write_text("#!/bin/bash\n" + body + "\n")
            stub.chmod(0o755)
        self.env = {"HOME": str(self.home), "PATH": f"{root}/bin:/usr/bin:/bin",
                    "STATE": str(self.state), "APPLICATIONS_DIR": str(self.apps)}

    def install(self, app):
        (self.apps / f"{app}.app").mkdir()

    def run_ai_ui(self, *args, answer=None, cli=None):
        """Run ai-ui; with `answer`, stdin is a terminal that types it."""
        cli = cli or AI_UI
        if answer is None:
            return subprocess.run([cli, *args], env=self.env, capture_output=True, text=True,
                                  stdin=subprocess.DEVNULL, timeout=30)
        terminal, typist = pty.openpty()
        os.write(terminal, answer.encode())
        try:
            return subprocess.run([cli, *args], env=self.env, capture_output=True, text=True,
                                  stdin=typist, timeout=30)
        finally:
            os.close(terminal)
            os.close(typist)

    def calls(self):
        return (self.state / "calls").read_text().splitlines()

    def saved_runtime(self):
        saved = self.home / ".sage-is" / "runtime"
        return saved.read_text().strip() if saved.exists() else None


class FirstStart(Mac):
    def test_a_mac_with_no_runtime_gets_colima_and_a_vm_sized_for_sage(self):
        result = self.run_ai_ui("start")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("colima start --vm-type vz --memory 4", self.calls())
        self.assertIn("docker colima run", " ".join(self.calls()))
        self.assertEqual(self.saved_runtime(), "colima")

    def test_an_existing_colima_vm_keeps_its_own_settings(self):
        (self.state / "colima-vm").touch()
        self.run_ai_ui("start")
        self.assertIn("colima start", self.calls())
        self.assertNotIn("colima start --vm-type vz --memory 4", self.calls())

    def test_the_question_lists_each_runtime_and_defaults_to_the_last_one_used(self):
        self.install("Docker")
        (self.state / "current-context").write_text("desktop-linux\n")
        result = self.run_ai_ui("start", answer="\n")
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


class RuntimeFlag(Mac):
    DOCKER_SETTINGS = "Library/Group Containers/group.com.docker/settings-store.json"

    def test_docker_desktop_that_ran_before_starts_hidden_in_the_background(self):
        self.install("Docker")
        (self.home / self.DOCKER_SETTINGS).parent.mkdir(parents=True)
        (self.home / self.DOCKER_SETTINGS).touch()
        result = self.run_ai_ui("start", "--runtime", "docker-desktop", "--port", "9090")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("open -g -j -a Docker", self.calls())
        self.assertIn("docker desktop-linux run -d -p 9090:8080", " ".join(self.calls()))
        self.assertEqual(self.saved_runtime(), "docker-desktop")

    def test_docker_desktops_first_start_stays_in_view(self):
        self.install("Docker")
        result = self.run_ai_ui("start", "--runtime", "docker-desktop")
        self.assertIn("open -a Docker", self.calls())
        self.assertIn("setup screens", result.stdout)

    def test_a_runtime_that_is_not_installed_says_how_to_get_it(self):
        result = self.run_ai_ui("start", "--runtime", "orbstack")
        self.assertEqual(result.returncode, 1)
        self.assertIn("brew install --cask orbstack", result.stdout)
        self.assertNotIn("run", " ".join(self.calls()))

    def test_an_unknown_runtime_is_refused(self):
        result = self.run_ai_ui("start", "--runtime", "podman")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Use one of: colima docker-desktop orbstack", result.stdout)
        self.assertIsNone(self.saved_runtime())


class OtherCommands(Mac):
    def test_they_follow_the_last_runtime_used_without_saving_or_starting_it(self):
        (self.state / "current-context").write_text("desktop-linux\n")
        self.run_ai_ui("status")
        container_calls = [call for call in self.calls() if call != "docker  context show"]
        self.assertTrue(container_calls)
        self.assertTrue(all(call.startswith("docker desktop-linux ") for call in container_calls), container_calls)
        self.assertIsNone(self.saved_runtime())

    def test_update_starts_the_runtime_before_it_pulls(self):
        self.run_ai_ui("update")
        calls = self.calls()
        self.assertLess(calls.index("colima start --vm-type vz --memory 4"),
                        next(i for i, call in enumerate(calls) if " pull " in call))


class Nuke(Mac):
    def test_a_brew_install_finds_nuke_sage_and_passes_its_flags(self):
        libexec = self.home / "keg" / "libexec"  # the formula installs all three side by side
        libexec.mkdir(parents=True)
        for source in (AI_UI, AI_UI.parent / "nuke-sage", AI_UI.parent.parent / "distribution.env"):
            shutil.copy2(source, libexec / source.name)
        result = self.run_ai_ui("nuke", "--all", "--dry-run", cli=libexec / "ai-ui")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
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
        (self.home / ".sage-is").mkdir()
        (self.home / ".sage-is" / "runtime").write_text("docker-desktop\n")
        (self.state / "running-desktop-linux").touch()
        self.run_ai_ui("nuke", "--dry-run")
        self.assertIn("docker desktop-linux inspect sage-ai", self.calls())


class CredentialHelper(Mac):
    """Docker Desktop leaves "credsStore": "desktop" behind; without its helper, every pull fails."""

    def write_docker_config(self):
        config = self.home / ".docker" / "config.json"
        config.parent.mkdir()
        config.write_text('{"auths": {}, "credsStore": "desktop", "currentContext": "colima"}\n')
        return config

    def test_a_missing_helper_is_dropped_before_the_pull_with_a_backup(self):
        config = self.write_docker_config()
        result = self.run_ai_ui("start")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("credsStore", config.read_text())
        self.assertIn('"currentContext":"colima"', config.read_text())
        backups = list(config.parent.glob("config.json.*.bak"))
        self.assertEqual(len(backups), 1)
        self.assertIn('"credsStore": "desktop"', backups[0].read_text())
        self.assertIn("docker-credential-desktop is not installed", result.stdout)

    def test_an_installed_helper_is_left_alone(self):
        config = self.write_docker_config()
        helper = Path(self.env["PATH"].split(":")[0]) / "docker-credential-desktop"
        helper.write_text("#!/bin/bash\n")
        helper.chmod(0o755)
        self.run_ai_ui("start")
        self.assertIn('"credsStore": "desktop"', config.read_text())
