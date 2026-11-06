"""Teeth for the loop-lag watchdog: it names the blocking frame, never a value."""

import asyncio
import json
import os
import tempfile
import time
import unittest
from pathlib import Path

try:
    from .loop_watch import LoopWatch, log, start_loop_watch
except ImportError:  # run as a script from this folder
    from loop_watch import LoopWatch, log, start_loop_watch

CANARY = "sk-canary-never-logged"


def _block_for_test(seconds):
    secret = CANARY  # a local the watchdog must never read
    time.sleep(seconds)
    return secret


async def _run(stalls, **kwargs):
    loop = asyncio.get_running_loop()
    watch = LoopWatch(loop, interval=0.02, threshold=0.06, **kwargs).start()
    await asyncio.sleep(0.1)
    for seconds in stalls:
        _block_for_test(seconds)
        await asyncio.sleep(0.1)
    watch.stop()
    return watch


class LoopWatchTest(unittest.TestCase):
    def test_names_the_blocking_frame_and_counts_the_lag(self):
        watch = asyncio.run(_run([0.3], dedupe=0))
        self.assertTrue(any("_block_for_test" in k for k in watch.stacks), watch.stacks)
        self.assertGreaterEqual(watch.histogram[">=250ms"], 1, watch.histogram)

    def test_never_reads_values(self):
        with tempfile.TemporaryDirectory() as d, self.assertLogs(log, "WARNING") as logs:
            watch = asyncio.run(_run([0.2], dedupe=0, out_dir=d))
            day = Path(d, f"loop-lag-{time.strftime('%Y-%m-%d')}.json").read_text()
        everything = day + json.dumps(watch.stacks) + "\n".join(logs.output)
        self.assertIn("_block_for_test", everything)
        self.assertNotIn(CANARY, everything)

    def test_logs_one_stack_once_per_window(self):
        with self.assertLogs(log, "WARNING") as logs:
            watch = asyncio.run(_run([0.15, 0.15], dedupe=600))
        hits = sum(n for k, n in watch.stacks.items() if "_block_for_test" in k)
        self.assertEqual(hits, 2, watch.stacks)
        self.assertEqual(sum("_block_for_test" in line for line in logs.output), 1)

    def test_off_switch(self):
        loop = asyncio.new_event_loop()
        os.environ["RS_LAG_WATCH"] = "off"
        try:
            self.assertIsNone(start_loop_watch(loop))
        finally:
            del os.environ["RS_LAG_WATCH"]
            loop.close()


if __name__ == "__main__":
    unittest.main()
