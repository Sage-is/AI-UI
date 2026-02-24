---
title: "Convention Instructions"
description: "Development conventions and coding standards applied to all files in the project."
date: 2025-11-28
tags:
  - conventions
  - standards
  - meta
---

---
applyTo: "*"
---
# Sage.is AI-UI Development Workflow

## Core Principles

Every development task follows the **Plan-Document-Execute-Verify** cycle:

0. **DRY** - Don't Repeat Yourself Code
1. **KISS** - Keep It Simple, Stupid
2. **Plan** - Add to TODO before doing work
3. **Document** - Update docs and README as needed
4. **Execute** - Implement changes following standards
5. **Verify** - Test, commit, and check off completed items

## Styling

Use [Startr.Style](https://startr.style) for all component styling. Inline CSS custom properties (`style="--d:flex; --ai:center"`) — never Tailwind utility classes or standalone CSS classes. See the [Development Workflow](DEVELOPMENT_WORKFLOW.md#styling-with-startrstyle) for the full reference.

## Standard Operating Procedure

### Before Starting Any Work

**ALWAYS add to TODO.md first:**

```markdown
## [Category] TODOs
- [ ] **[Task Name]**: Brief description
  - [ ] Subtask 1
  - [ ] Subtask 2
  - [ ] Test/verify step
  - [ ] Documentation update
```

**NEVER start work without:**
- Adding the task to TODO.md
- Getting approval for significant changes
- Understanding the complete scope

### Planning Requirements

For each task, define:
- **Scope** - What exactly needs to be done
- **Dependencies** - What must be completed first
- **Testing** - How to verify it works
- **Documentation** - What docs need updates



## See the [DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md) for more details.
