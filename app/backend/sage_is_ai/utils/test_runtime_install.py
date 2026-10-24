"""uv command building: python -m unittest sage_is_ai.utils.test_runtime_install"""

import sys
import unittest

from sage_is_ai.utils.runtime_install import (
    PIP_ONLY_FLAGS,
    system_install_cmd,
    target_install_cmd,
    uv_compatible,
)


class UvCompatible(unittest.TestCase):
    def test_the_four_flags_uv_rejected_are_dropped(self):
        # What uv 0.12.24 answered "unexpected argument" to (2026-10-15). If uv
        # starts rejecting another pip flag, add it here and to PIP_ONLY_FLAGS.
        self.assertEqual(
            PIP_ONLY_FLAGS,
            {
                "--root-user-action",
                "--prefer-binary",
                "--no-warn-script-location",
                "--user",
            },
        )
        opts = [
            "--root-user-action=ignore",
            "--prefer-binary",
            "--no-warn-script-location",
            "--user",
        ]
        with self.assertLogs("sage_is_ai.utils.runtime_install", "WARNING"):
            self.assertEqual(uv_compatible(opts), [])

    def test_a_separate_value_goes_with_its_flag(self):
        self.assertEqual(
            uv_compatible(["--root-user-action", "ignore", "--pre"]), ["--pre"]
        )

    def test_flags_uv_accepts_pass_through_in_order(self):
        opts = [
            "--pre",
            "--no-cache-dir",
            "--trusted-host=pypi.org",
            "-i",
            "https://x/simple",
        ]
        self.assertEqual(uv_compatible(opts), opts)


class Commands(unittest.TestCase):
    def test_system_install_targets_this_interpreter_through_uv(self):
        cmd = system_install_cmd(
            ["six==1.17.0"], ["--user", "--pre"], ["-i", "https://x/simple"]
        )
        self.assertEqual(cmd[:3], ["uv", "pip", "install"])
        self.assertEqual(cmd[cmd.index("--python") + 1], sys.executable)
        self.assertIn("--system", cmd)
        self.assertNotIn("--user", cmd)
        self.assertEqual(cmd[-3:], ["six==1.17.0", "-i", "https://x/simple"])

    def test_target_install_keeps_extra_flags(self):
        cmd = target_install_cmd(["chromadb==0.6.3"], "/data/ml", "--reinstall")
        self.assertEqual(cmd[cmd.index("--target") + 1], "/data/ml")
        self.assertIn("--reinstall", cmd)
        self.assertEqual(cmd[-1], "chromadb==0.6.3")


if __name__ == "__main__":
    unittest.main()
