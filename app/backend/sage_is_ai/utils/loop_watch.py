"""Loop-lag watchdog: record where the event loop stalls, never what it holds.

A loop callback ticks every `interval`; a daemon thread watches the last tick.
When the loop runs `threshold` late, the thread reads the loop thread's frame
(sys._current_frames) and records file:line of the innermost `depth` frames.
It reads no local variables. Each stack is logged once per `dedupe` seconds;
lag counts and stacks go to a daily JSON file under `out_dir`.
RS_LAG_WATCH=off disables it.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import time
from pathlib import Path

log = logging.getLogger(__name__)
BUCKETS_MS = (100, 250, 500, 1000, 2500, 5000, 10000)


def _where(frame) -> str:
    path = frame.f_code.co_filename
    for mark in ("sage_is_ai/", "site-packages/", "python3."):
        if mark in path:
            path = path[path.index(mark) :]
            break
    return f"{path}:{frame.f_lineno} {frame.f_code.co_name}"


class LoopWatch:
    def __init__(self, loop, *, interval=0.1, threshold=0.25, depth=12,
                 dedupe=600.0, out_dir=None, flush_every=60.0):
        self.loop, self.interval, self.threshold = loop, interval, threshold
        self.depth, self.dedupe, self.flush_every = depth, dedupe, flush_every
        self.out_dir = Path(out_dir) if out_dir else None
        self.histogram = {f">={b}ms": 0 for b in BUCKETS_MS}
        self.max_ms = 0.0
        self.stacks: dict[str, int] = {}
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._stalled = False
        self._day = time.strftime("%Y-%m-%d")
        self._flushed = time.monotonic()

    def start(self) -> "LoopWatch":
        """Call from the loop's own thread."""
        self._tid = threading.get_ident()
        self._last = time.monotonic()
        self._arm()
        self._thread = threading.Thread(target=self._watch, name="loop-watch", daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        self._handle.cancel()
        self._thread.join(1.0)
        self.flush()

    def _arm(self) -> None:
        self._due = time.monotonic() + self.interval
        self._handle = self.loop.call_later(self.interval, self._tick)

    def _tick(self) -> None:
        now = time.monotonic()
        late_ms = (now - self._due) * 1000
        with self._lock:
            self.max_ms = max(self.max_ms, late_ms)
            for b in reversed(BUCKETS_MS):
                if late_ms >= b:
                    self.histogram[f">={b}ms"] += 1
                    break
        self._last = now
        if not self._stop.is_set():
            self._arm()

    def _watch(self) -> None:
        while not self._stop.wait(self.interval / 2):
            late = time.monotonic() - self._last - self.interval
            if late >= self.threshold and not self._stalled:
                self._stalled = True
                self._sample(late)
            elif late < self.threshold:
                self._stalled = False
            if self.out_dir and time.monotonic() - self._flushed >= self.flush_every:
                self.flush()

    def _sample(self, late: float) -> None:
        frame = sys._current_frames().get(self._tid)
        stack = []
        while frame is not None and len(stack) < self.depth:
            stack.append(_where(frame))
            frame = frame.f_back
        label = " < ".join(stack)
        now = time.monotonic()
        with self._lock:
            self.stacks[label] = self.stacks.get(label, 0) + 1
            if now - self._seen.get(label, -1e9) < self.dedupe:
                return
            self._seen[label] = now
        # Logged at detection, so the stall lasts at least this long; its full
        # length lands in the histogram when the loop ticks again.
        log.warning("event loop blocked for at least %d ms at %s", late * 1000, label)

    def flush(self) -> None:
        if not self.out_dir:
            return
        with self._lock:
            top = sorted(self.stacks.items(), key=lambda kv: -kv[1])[:50]
            data = {"day": self._day, "max_ms": round(self.max_ms),
                    "histogram": dict(self.histogram), "stacks": dict(top)}
            today = time.strftime("%Y-%m-%d")
            if today != self._day:  # a new day starts empty
                self.histogram = {k: 0 for k in self.histogram}
                self.stacks, self.max_ms, self._day = {}, 0.0, today
        self.out_dir.mkdir(parents=True, exist_ok=True)
        path = self.out_dir / f"loop-lag-{data['day']}.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1))
        os.replace(tmp, path)
        self._flushed = time.monotonic()


def start_loop_watch(loop, data_dir=None) -> LoopWatch | None:
    if os.environ.get("RS_LAG_WATCH", "on").lower() in ("off", "0", "false"):
        return None
    out = Path(data_dir) / "rootstock" if data_dir else None
    return LoopWatch(loop, out_dir=out).start()
