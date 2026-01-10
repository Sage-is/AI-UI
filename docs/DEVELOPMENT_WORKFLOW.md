# Startr Development Workflow

**Before Starting Any Work ALWAYS add to TODO.md first:**

```markdown
## 🔥 This Week (Current Date)
### 🔥 [Task Category]: [Task Name]
- [ ] **[Task Name]**: Brief description
  - [ ] Subtask 1
  - [ ] Subtask 2
  - [ ] Test/verify step
  - [ ] Documentation update
```

**NEVER start work without:**
- Adding the task to TODO.md at the top (current week section)
- Getting approval for significant changes
- Understanding the complete scope

**TODO Organization Rules:**
- **Current work goes at the top** - Always add new tasks to the current week section
- **Use priority emojis** - 🔥 Critical, 🔶 High, 🔷 Medium, 🔹 Low, ✅ Done
- **Move completed work down** - When tasks are done, move them to "Previous Weeks" section
- **Keep reverse chronological order** - Newest completed work appears first in Previous WeeksCore Principles

Every development task follows the **Plan-Document-Execute-Verify** cycle:


0. **DRY** **KISS** - Don't Repeat Yourself (ever in Code) and Keep It Simple, Stupid
1. **Plan** - Add to TODO before doing any work
2. **Document** - Update docs and README as needed
3. **Execute** - Implement changes following standards
4. **Verify** - Test, commit, and check off completed items

Our Zeroth rule is to keep things **DRY** and **KISS**. This means we avoid code duplication and keep our solutions as simple as possible.

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

### Documentation Standards

**Always update documentation when:**
- Adding new features or processes
- Changing existing functionality
- Creating new files or directories
- Modifying configuration

**Documentation locations:**
- `README.md` - Quick start and overview
- `docs/` - Detailed guides
- `TODO.md` - Current and completed work
- Inline code comments - Complex logic

### Execution Standards

**File Management:**
- Use skip-worktree for config files that need local customization
- Follow naming conventions (kebab-case for files)
- Organize code logically in appropriate directories

**Git Workflow:**
- Descriptive commit messages
- Atomic commits (one logical change per commit)
- Check off TODO items in commit messages when completed

**Code Quality:**
- Follow project conventions
- Test changes before committing
- Use tools appropriately (Makefile targets, npm scripts)

### Verification Process

**Before marking TODO items complete:**
- [ ] Feature/fix works as expected
- [ ] No new errors introduced
- [ ] Documentation updated
- [ ] README links current
- [ ] Committed to version control

**After completion:**
- Mark TODO items with ✅
- Update progress in commit messages
- Note any follow-up tasks needed

## Communication Protocol

### Seeking Approval

**Always check before starting:**
- Significant feature additions
- Process changes
- Large refactoring
- External integrations

**Use clear language:**
- "Ready to proceed with [task] when approved"
- "This will affect [areas] - proceed?"
- "Plan complete, awaiting go-ahead"

### Progress Updates

**Format: [Status] [Task] - [Details]**
- ✅ **Completed** - [Task] with summary
- 🔄 **In Progress** - [Task] current step
- 📋 **Planned** - [Task] ready to start
- ⚠️ **Blocked** - [Task] waiting on [dependency]

## Project-Specific Standards

### Documentation Management

**README.md sections:**
- Quick Start
- Initial Setup  
- Documentation (links to all docs/)
- Environment System
- Troubleshooting
- Technical Details

**Required documentation:**
- All files in `docs/` must be linked in README
- New processes get dedicated documentation
- Configuration changes need setup instructions

### TODO Management

**Organization Principle**: TODOs are organized in **reverse chronological order** (newest first) to keep current work at the top and ensure immediate priorities are visible.

**Structure:**
1. **Current Week** - 🔥 Critical tasks for this week (always at top)
2. **High Priority** - 🔶 Next milestone work  
3. **Medium Priority** - 🔷 Soon
4. **Low Priority** - 🔹 Nice to have
5. **Completed Work** - ✅ Previous weeks in reverse chronological order

**Categories (in order of priority):**
1. **Documentation & Admin Management** - Category for meta-work
2. **Critical Infrastructure & Security** 
3. **High Priority** - User-facing fixes
4. **Medium Priority** - Feature development
5. **Low Priority** - Nice-to-have improvements


**Status tracking:**
- [ ] Planned
- 🔄 In Progress  
- ✅ Completed
- ❌ Cancelled/Won't Do

### Admin Integration Standards

**For data that should be CMS-managed:**
1. Add TODO for admin collection setup
2. Design collection structure matching existing data
3. Plan template integration
4. Test admin interface
5. Document staff process
6. Migrate from static to admin-managed

### Configuration Management

**Files requiring skip-worktree:**
- `src/admin/config.yml` - CMS configuration
- Any file needing local customization

**Setup process:**
- Add to `make setup` target
- Document in README and dedicated guide
- Include in onboarding documentation

## Quality Assurance

### Pre-Commit Checklist

- [ ] TODO updated with progress
- [ ] Documentation reflects changes
- [ ] README links are current
- [ ] No broken links or references
- [ ] Code follows project conventions
- [ ] Changes tested locally

### Review Standards

**Code review focuses on:**
- Adherence to workflow process
- Documentation completeness
- TODO accuracy and progress
- Standard compliance

### Continuous Improvement

**Regular workflow reviews:**
- Monthly TODO cleanup
- Quarterly process refinement
- Document lessons learned
- Update standards as needed

## Tools and Automation

### Makefile Targets

Standard targets for common tasks:
- `make setup` - Configure local environment
- `make help` - Show available commands
- Project-specific build/deploy targets

### Git Integration

**Commit message format:**
```
[Type]: [Summary]

- [Change 1]
- [Change 2] 
- Mark TODO item as complete/in progress
```

**Types:** Add, Update, Fix, Remove, Refactor, Document

### Documentation Tools

- Markdown for all documentation
- Consistent heading structure
- Clear, concise language following Startr Writing Guidelines
- Regular link validation

### Testing Standards

**Test Framework:**
- pytest with pytest-django for Django integration
- pytest-cov for coverage reporting
- All tests in `tests.py` files within app directories

**Test Configuration:**
- `pytest.ini` - Main pytest configuration 
- `conftest.py` - Shared fixtures and Django setup
- Tests run with `--nomigrations` and `--reuse-db` for speed

**Testing Commands:**
```bash
make test                 # Run all tests
make test_verbose         # Run with verbose output
make test_coverage        # Run with coverage report
make test_experiences     # Run only experiences app tests
make test_quick          # Run excluding slow tests
```

**Test Categories (using markers):**
- `@pytest.mark.unit` - Unit tests (isolated, fast)
- `@pytest.mark.integration` - Integration tests  
- `@pytest.mark.slow` - Slow tests (can be excluded)
- `@pytest.mark.django_db` - Tests requiring database

**Writing Tests:**
- One test file per app (`app/tests.py`)
- Test classes for each model/view
- Descriptive test names explaining what is tested
- Use fixtures from `conftest.py` for common setup
- Mock external dependencies

**Test Coverage:**
- Aim for 80%+ coverage on critical paths
- 100% coverage on new models and core business logic
- Coverage reports generated in `htmlcov/` directory

## Success Metrics

**Process adherence:**
- All work starts with TODO entry
- Documentation stays current
- No surprise changes without planning
- Clear approval process followed

**Quality indicators:**
- Accurate TODO progress tracking
- Complete documentation coverage
- Working links and references
- Consistent code standards

**Team efficiency:**
- Reduced context switching
- Clear handoff documentation
- Predictable development cycle
- Minimal rework needed

## Getting Started

**For new team members:**
1. Read this workflow document
2. Run `make setup` 
3. Review current TODO.md
4. Practice the plan-document-execute-verify cycle on small tasks
5. Ask questions before starting significant work

**For existing team members:**
1. Adopt this process for all new work
2. Migrate existing workflows gradually
3. Update TODO.md with current status
4. Help refine and improve the process

---

*This workflow document is living documentation. Update it as the process evolves and improve it based on team feedback and project needs.*
