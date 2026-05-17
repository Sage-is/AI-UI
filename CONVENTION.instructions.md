---
applyTo: "*"
---
# Sage.is AI-UI Development Workflow

## Core Principles

Every development task follows the **Plan-Document-Execute-Verify** cycle:

0. Zeroth Principle: **Follow the Standards**
  - **SOLID** - Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, Dependency Inversion
  - **YAGNI** - You Aren't Gonna Need It (don't add features until needed)
  - **KISS** - Keep It Simple, Stupid
  - **DRY** - Don't Repeat Yourself (ever in Code)
  - **KISS** - Keep It Simple, Stupid
1. **Plan** - Add to TODO.md before doing any work
2. **Document** - Update docs and README as needed
3. **Execute** - Implement changes following standards
4. **Verify** - Test, commit, and check off completed items

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



## See the [development-workflow.md](docs/development-workflow.md) for more details.

## FastAPI Dependency Ordering for Env-Gated Routes

When a route is gated by both an env flag (e.g. `ENABLE_TRY_SAGE`) and an auth
dependency (e.g. `get_admin_user`), the env gate **must** appear earlier in the
handler's parameter list than the auth dependency. FastAPI evaluates `Depends`
left to right; the first one to raise wins.

```python
# CORRECT — env gate fires first, returns 404 when feature disabled.
async def get_llm_status(
    request: Request,
    _gate: None = Depends(_require_try_sage_enabled),
    user=Depends(get_admin_user),
):
    ...
```

```python
# WRONG — auth fires first, returns 403 when feature disabled.
async def get_llm_status(
    request: Request,
    user=Depends(get_admin_user),
):
    _require_try_sage_enabled()  # too late: auth already 403'd unauth'd callers
```

**Why it matters:** A disabled feature must look like it doesn't exist (404),
not like the caller is unauthorized (403). The latter signals "the path is
real, try harder" — wrong information and a small surface-area leak. The gate
must fire before auth so unauthenticated callers also see 404.

**Reference fix:** 2.3.1 / 2026-05-12 — `app/backend/sage_is_ai/routers/sage_runtime.py`
lifted `_require_try_sage_enabled` into a `_gate` Depends parameter ahead of
`get_admin_user` for `/llm-status`, `/extend`, `/reset`.