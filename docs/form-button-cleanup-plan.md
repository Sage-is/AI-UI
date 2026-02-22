---
title: "Form Button Cleanup Plan"
description: "Plan to remove redundant type='button' attributes from forms using preventDefault in Svelte components."
date: 2026-01-23
tags:
  - cleanup
  - svelte
  - frontend
  - forms
---

# Form Button Cleanup Plan

## Current Situation

Throughout the application, we have a mixed pattern:

1. **Good**: Forms use `on:submit|preventDefault` to override default submit behavior
2. **Redundant**: Many buttons inside these forms have `type="button"` which is unnecessary

## The Problem

When a form has `on:submit|preventDefault`, ALL buttons inside that form will NOT trigger default form submission behavior, regardless of their `type` attribute. This is because:

```svelte
<form on:submit|preventDefault={() => submitHandler()}>
  <!-- This button will NOT submit the form by default -->
  <button on:click={doSomething}>Click Me</button>

  <!-- This type="button" is REDUNDANT -->
  <button type="button" on:click={doSomething}>Click Me</button>

  <!-- Only THIS will trigger the submit handler -->
  <button type="submit">Submit</button>
</form>
```

The `preventDefault` modifier stops the default form submission event, so we don't need defensive `type="button"` attributes everywhere.

## Established Convention

**In forms with `on:submit|preventDefault`:**
- **DO**: Use `type="submit"` for the actual submit button
- **DO**: Omit `type` attribute for all other buttons (cleaner, less verbose)
- **DON'T**: Use `type="button"` (it's redundant)

**Exception - Auth Forms:**
Auth forms (`app/src/routes/auth/+page.svelte` and submodules equivalent) may use traditional patterns. Review these separately.

## What Needs to Change

### Pattern to Find:
1. Forms with `on:submit|preventDefault` (or `on:submit={(e) => { e.preventDefault(); ...`)
2. Buttons inside those forms with `type="button"`
3. Remove the `type="button"` attribute

### Files to Process:
- `app/src/**/*.svelte`
- Potentially `submodules/open-webui/src/**/*.svelte` (if we maintain that code)

## Implementation Strategy

### Phase 1: Automated Cleanup
Run a script to:
1. Parse Svelte files
2. Identify forms with preventDefault pattern
3. Find buttons with `type="button"` inside those forms
4. Remove the redundant `type="button"` attribute

### Phase 2: Manual Review
1. Review auth forms separately
2. Check edge cases where preventDefault might not be present
3. Verify no unintended side effects

### Phase 3: Documentation
1. Add to `CONVENTION.instructions.md`
2. Update any development guidelines
3. Consider adding an ESLint rule or pre-commit hook

## Expected Benefits

1. **Cleaner Code**: Less verbose, easier to read
2. **Consistency**: Single pattern across the entire app
3. **Maintainability**: Developers don't need to remember to add `type="button"`
4. **Reduced Bundle Size**: Minor, but every byte counts

## Files Affected (Sample)

Based on initial scan, affected files include:
- `app/src/lib/components/ImportModal.svelte`
- `app/src/lib/components/AddServerModal.svelte`
- `app/src/lib/components/AddConnectionModal.svelte`
- `app/src/lib/components/layout/Sidebar/ChannelModal.svelte`
- `app/src/lib/components/admin/Functions/FunctionEditor.svelte`
- Many more (estimated 50+ files)

## Risks & Mitigation

### Risk: Breaking Functionality
**Mitigation**:
- Thorough testing after changes
- Only remove `type="button"` from forms with confirmed preventDefault
- Keep git history for easy rollback

### Risk: Auth Forms Behaving Differently
**Mitigation**:
- Exclude auth forms from automated cleanup
- Manual review of authentication flows

### Risk: Third-party Components
**Mitigation**:
- Only modify files in `app/src/` initially
- Be cautious with submodules

## Tool Implementation

See `tools/cleanup-form-buttons.js` for the automated cleanup script.

The script will:
1. Use regex to find forms with preventDefault
2. Parse button elements within form scope
3. Remove `type="button"` attributes
4. Generate a report of changes
5. Create backup of modified files

## Execution Plan

1. **Review this document**
2. Run the cleanup tool with `--dry-run` flag
3. Review the proposed changes
4. Execute the actual cleanup
5. Test affected forms manually
6. Commit changes with clear documentation
7. Update conventions document

## Success Criteria

- [ ] All forms with `on:submit|preventDefault` have buttons without redundant `type="button"`
- [ ] All actual submit buttons have explicit `type="submit"`
- [ ] All forms still function correctly
- [ ] Convention documented in `CONVENTION.instructions.md`
- [ ] No regression in tests or manual testing
