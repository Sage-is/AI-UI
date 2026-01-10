---
applyTo: "*"
---
# Startr Development Workflow

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



## See the [DEVELOPMENT_WORKFLOW.md](docs/DEVELOPMENT_WORKFLOW.md) for more details.