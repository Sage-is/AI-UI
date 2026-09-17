"""Pseudonymize outbound text, reverse inbound text, streamed or whole.

``pseudonymize`` runs every rule, keeps the earliest and then longest match
where matches overlap, and asks the mapper for each value's fake. ``reverse``
puts the real values back by exact, longest-first replacement of known fakes.
``StreamReverser`` does the same on a stream by holding back as many
characters as the longest known fake, so a fake split across two chunks is
still caught.
"""

from __future__ import annotations

import re
from typing import Protocol

from sage_is_ai.privacy import shapes
from sage_is_ai.privacy.rules import Hit, Rule, hint_rules


class Mapper(Protocol):
    def fake(self, category: str, real: str, strategy: str, replacement: str = "") -> str: ...

    def owner(self, fake: str) -> tuple[str, str] | None: ...

    def reverse_table(self) -> dict[str, str]: ...


class MemoryMapper:
    """In memory: the test bench, and the base the database mapper builds on."""

    def __init__(self, key: str):
        self.key = key
        self.by_real: dict[tuple[str, str], str] = {}
        self.by_fake: dict[str, tuple[str, str]] = {}

    def _real_key(self, category: str, real: str) -> tuple[str, str]:
        return category, real.strip()

    def lookup(self, category: str, real: str) -> str | None:
        return self.by_real.get(self._real_key(category, real))

    def owner(self, fake: str) -> tuple[str, str] | None:
        return self.by_fake.get(fake)

    def store(self, category: str, real: str, fake: str) -> None:
        self.by_real[self._real_key(category, real)] = fake
        self.by_fake[fake] = self._real_key(category, real)

    def fake(self, category: str, real: str, strategy: str, replacement: str = "") -> str:
        if strategy == "redact":
            return f"[{category}]"
        known = self.lookup(category, real)
        if known is not None:
            return known
        if strategy == "literal":
            owner = self.owner(replacement)
            if owner is None:
                self.store(category, real, replacement)
            return replacement  # a shared literal still replaces; it just cannot reverse
        salt = 0
        while True:
            candidate = shapes.fake_for(category, real, self.key, salt)
            if salt < 64 and shapes.too_close(candidate, real, category):
                salt += 1  # a fake that repeats the real value is not a fake
                continue
            owner = self.owner(candidate)
            if owner is None:
                self.store(category, real, candidate)
                return candidate
            if owner == self._real_key(category, real):
                return candidate
            salt += 1  # a collision: another real value already wears this fake

    def reverse_table(self) -> dict[str, str]:
        return {fake: real for fake, (_, real) in self.by_fake.items()}


def pseudonymize(text: str, rules: list[Rule], mapper: Mapper, hints=None) -> tuple[str, list[Hit]]:
    if not text:
        return text, []
    active = hint_rules(hints) + [r for r in rules if r.enabled]
    active.sort(key=lambda r: r.order)
    candidates = []
    for rank, rule in enumerate(active):
        for match in rule.compiled().finditer(text):
            if match.end() > match.start():
                candidates.append((match.start(), -(match.end() - match.start()), rank, match.end(), rule))
    candidates.sort()
    out, cursor, hits = [], 0, {}
    for start, _, _, end, rule in candidates:
        if start < cursor:
            continue  # overlaps an earlier, longer or higher-ranked match
        real = text[start:end]
        out.append(text[cursor:start])
        if mapper.owner(real) is not None:
            out.append(real)  # already a fake: a message sent twice stays stable
        else:
            out.append(mapper.fake(rule.category, real, rule.strategy, rule.replacement))
        cursor = end
        hit = hits.setdefault(rule.name, Hit(rule.name, rule.category))
        hit.count += 1
    out.append(text[cursor:])
    return "".join(out), list(hits.values())


_PATTERNS: dict[int, tuple[re.Pattern, int]] = {}


def _pattern(table: dict[str, str]) -> tuple[re.Pattern | None, int]:
    if not table:
        return None, 0
    cached = _PATTERNS.get(id(table))
    if cached is not None:
        return cached
    fakes = sorted(table, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(f) for f in fakes))
    _PATTERNS.clear()  # one live table at a time is plenty
    _PATTERNS[id(table)] = (pattern, len(fakes[0]))
    return pattern, len(fakes[0])


def reverse(text: str, table: dict[str, str]) -> str:
    pattern, _ = _pattern(table)
    if pattern is None or not text:
        return text
    return pattern.sub(lambda m: table.get(m.group(0), m.group(0)), text)


class StreamReverser:
    def __init__(self, table: dict[str, str]):
        self.table = table
        self.pattern, self.hold = _pattern(table)
        self.buffer = ""

    def feed(self, chunk: str) -> str:
        if not chunk:
            return ""
        if self.pattern is None:
            return chunk
        self.buffer += chunk
        safe = max(len(self.buffer) - self.hold + 1, 0)
        for match in self.pattern.finditer(self.buffer):
            if match.start() < safe < match.end():
                safe = match.start()  # a fake straddles the cut: hold it back whole
                break
        out, self.buffer = self.buffer[:safe], self.buffer[safe:]
        return reverse(out, self.table)

    def flush(self) -> str:
        out, self.buffer = self.buffer, ""
        return reverse(out, self.table)
