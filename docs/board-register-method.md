# The board register pass

Weekly, per project (Alexander, 2026-08-15). The bar: **no open `- [ ]` line over 350 characters**. One short claim line per card; everything else a tight sub-checklist. Proven here twice on 2026-08-15: pass 1 cut 40 blocks 143.5k → 87.8k chars (−39%); pass 2 split 117 long lines to zero over the bar.

## The shape

```markdown
- [ ] **Short title**: one sentence — what and why it matters. #tags
  - Fact the claim rests on (plain bullet: context, not work).
  - [ ] One action, with its numbers and paths.
    - [ ] A step under a step (depth 3 max).
```

Actions get checkboxes; plain facts get plain bullets — the kanban checklist then holds only real work.

## The pass

1. **Scout.** Open `- [ ]` lines >350 chars, python regex `^\s*- \[ \]`    BSD awk's `\s` is not whitespace and lies. Carve the containing top-level card    blocks (`^- \[`; note `####` headings ride inside blocks).
2. **Rewrite** each block (fan out if many; ~6 blocks per agent):
   - Parent line ≤ ~320 chars: one claim, shortened title, tags kept.
   - Every long line splits into subtasks ≤ ~220 chars, one action or fact each.
   - Reuse the original's words — split and trimmed, never re-narrated. Invent nothing.
   - Keep verbatim: paths, env vars, flags, make targets, versions, dates, measured
     numbers, citations, hashtags, attributions, [MANUALLY]/[WE], `<!-- inline: -->`
     lines, ~~strikethrough~~, dossier links, ALL checkbox states.
   - Checked children >300 chars become one-line `- [x] _gist + earned numbers.
     Archived → docs/completed-todos.md._` stubs; originals move to that file.
   - Bugs ledger: claim = symptom + root cause + worst consequence (with citation);
     repro detail, traps, and fix steps become subtasks.
3. **Dossier.** Full original text of every compressed block goes verbatim to
   `docs/board-dossiers.md` under a title heading — zero information loss; the board
   wins on conflict. Skip blocks already dossiered.
4. **Verify**, deterministically, before calling it done:
   - Hard tokens (paths, `UPPER_CASE` in backticks, make-target **invocations**,
     versions, dates) from each original still appear in its rewrite.
   - Zero open lines >350 remain (python, not awk).
   - Splice with a drift assert: the block on disk must byte-match the carve.
5. **Re-point** every file citing `TODO.md:NNN` in the same sitting — charts, ledgers, decision records. These rot on every pass; re-derive from bold titles.
6. **Un-mix** while there: a `- [x]` parent hiding open children gets its open children extracted to real cards and the parent archived.

## Traps

- The carve's trailing-blank handling: recompute each splice span from the stored text's line count, never from a separately tracked `end`.
- Markdown headings inside carved blocks need a blank line before them after splice.
- Agents may shorten titles — grep the dossier by old title when a card seems gone.
- KANBAN.canvas regenerates itself; never hand-edit it.

## Follow-ups

Tracked as **Optimize the board register pass** in TODO.md Backlog: a commit-time length gate, tooling extraction into `scripts/`, a TodoScope upstream flag, and the automation decision.
