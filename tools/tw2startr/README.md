# tw2startr

Convert Tailwind CSS utility classes to [startr.style](https://startr.style) responsive inline CSS custom properties in Svelte and HTML files.

Given a Svelte component like this:

```svelte
<div class="flex items-center gap-4 p-6 bg-gray-100 hover:bg-gray-200 rounded-lg shadow-md">
```

tw2startr rewrites it to:

```svelte
<div style="--d:flex; --ai:center; --g:1rem; --p:1.5rem; --bgc:#f3f4f6; --hvr-bgc:#e5e7eb; --radius:0.5rem; --shadow:3">
```

Responsive and hover prefixes are preserved through the startr.style property naming convention (`sm:flex` becomes `--d-sm:flex`, `hover:bg-gray-200` becomes `--hvr-bgc:#e5e7eb`).

## Why startr.style?

Tailwind popularized utility-first CSS, but it comes with trade-offs: a build step, a config file, a plugin ecosystem, thousands of generated class names, and an abstraction layer between you and actual CSS. [startr.style](https://startr.style) takes a different approach.

**No build step.** startr.style is a single stylesheet under 8kb gzipped. Add one `<link>` tag and start building. No compiler, no PostCSS, no purging unused classes.

**You write real CSS values.** Tailwind invents its own vocabulary (`p-4`, `text-sm`, `rounded-lg`) that you have to memorize and that maps to hidden values. startr.style utilities are just CSS custom properties, you set the actual values yourself. `--p:1rem` means `padding: 1rem`. There's nothing to decode.

**Browser inspector is your best friend.** This is big! Because startr.style properties live in the `style` attribute, you can edit them directly in your browser's dev tools and see changes instantly. Tweak `--g:1rem` to `--g:2rem`, change `--bgc:#f3f4f6` to any color, adjust `--radius` -- alllive, no rebuild, no hot reload delay! With Tailwind, the inspector shows you computed styles but you can't easily iterate on utility classes from there. With startr.style, the inspector becomes your design tool.

**Utility complete, not utility first.** Tailwind generates a rule for every common property/value combination. startr.style defines the property and lets you set any valid CSS value, giving you full access to the CSS spec while keeping the stylesheet a fraction of the size.

**Responsive built in.** Four breakpoints (`-sm`, `-md`, `-lg`, `-xl`) plus print, applied as suffixes: `--d-md:none` hides an element at medium breakpoints. No `@media` queries to write, no responsive config to maintain.

## Quick Start

```bash
cd tools/tw2startr
npm install

# Preview what would change (no files modified)
npx tw2startr --dry-run --diff "src/**/*.svelte"

# Apply conversions
npx tw2startr "src/**/*.svelte"
```

## CLI Usage

```
tw2startr [options] [glob]
```

| Flag | Short | Description |
|------|-------|-------------|
| `--dry-run` | `-n` | Preview changes without modifying any files |
| `--diff` | `-d` | Show a unified diff of each changed file |
| `--report` | `-r` | Print conversion stats and manual-review items |
| `--verbose` | `-v` | Detailed per-file processing output |
| `--backup` | | Create `.backup` files before overwriting (default) |
| `--no-backup` | | Skip creating backup files |
| `--path <dir>` | | Base directory to search (defaults to cwd) |
| `--exclude <pattern>` | | Exclude paths matching this substring (repeatable) |
| `--help` | `-h` | Show help text |

The positional argument is a glob pattern or a direct file path. If omitted, all `.svelte` and `.html` files under the base directory are processed.

### Examples

```bash
# Dry run with diff on all Svelte files in src/
npx tw2startr --dry-run --diff "src/**/*.svelte"

# Convert a single file
npx tw2startr src/lib/components/common/Switch.svelte

# Convert with a full report, excluding test fixtures
npx tw2startr --report --exclude test "src/lib/**/*.svelte"

# Convert everything under a specific directory, no backups
npx tw2startr --no-backup --path src/lib/components

# Convert HTML files
npx tw2startr --dry-run --diff "**/*.html"
```

## Mapping Coverage

### Core Property Conversions

| Category | Tailwind Class | startr.style Property | Example |
|----------|---------------|----------------------|---------|
| **Display** | `flex`, `block`, `grid`, `hidden`, ... | `--d` | `flex` -> `--d:flex` |
| **Position** | `relative`, `absolute`, `fixed`, `sticky` | `--pos` | `absolute` -> `--pos:absolute` |
| **Flex Direction** | `flex-col`, `flex-row-reverse` | `--fd` | `flex-col` -> `--fd:column` |
| **Flex Wrap** | `flex-wrap`, `flex-nowrap` | `--fw` | `flex-wrap` -> `--fw:wrap` |
| **Flex Shorthand** | `flex-1`, `flex-auto`, `flex-none` | `--fx` | `flex-1` -> `--fx:1 1 0%` |
| **Grow / Shrink** | `grow`, `grow-0`, `shrink`, `shrink-0` | `--fg`, `--fs` | `grow` -> `--fg:1` |
| **Align Items** | `items-center`, `items-start` | `--ai` | `items-center` -> `--ai:center` |
| **Justify Content** | `justify-between`, `justify-center` | `--jc` | `justify-between` -> `--jc:space-between` |
| **Align Self** | `self-start`, `self-center` | `--as` | `self-center` -> `--as:center` |
| **Gap** | `gap-4`, `gap-x-2`, `gap-y-8` | `--g`, `column-gap`, `row-gap` | `gap-4` -> `--g:1rem` |
| **Grid Columns** | `grid-cols-3`, `col-span-2` | `--gtc`, `--gc` | `grid-cols-3` -> `--gtc:repeat(3, minmax(0, 1fr))` |
| **Z-Index** | `z-10`, `z-50`, `z-auto` | `--z` | `z-10` -> `--z:10` |
| **Inset** | `top-0`, `left-4`, `inset-0` | `--top`, `--left`, `--inset` | `top-0` -> `--top:0` |
| **Padding** | `p-4`, `px-2`, `pt-8` | `--p`, `--px`, `--pt` | `p-4` -> `--p:1rem` |
| **Margin** | `m-4`, `mx-auto`, `-mt-2` | `--m`, `--mx`, `--mt` | `mx-auto` -> `--mx:auto` |
| **Width** | `w-full`, `w-64`, `w-1/2` | `--w` | `w-full` -> `--w:100%` |
| **Height** | `h-screen`, `h-16` | `--h` | `h-screen` -> `--h:100vh` |
| **Min/Max Width** | `min-w-0`, `max-w-lg` | `--minw`, `--maxw` | `max-w-lg` -> `--maxw:32rem` |
| **Min/Max Height** | `min-h-screen`, `max-h-full` | `--minh`, `--maxh` | `min-h-screen` -> `--minh:100vh` |
| **Font Size** | `text-sm`, `text-xl`, `text-2xl` | `--size` | `text-sm` -> `--size:0.875rem` |
| **Font Weight** | `font-bold`, `font-semibold` | `--weight` | `font-bold` -> `--weight:700` |
| **Font Family** | `font-sans`, `font-mono` | `--ff` | `font-mono` -> `--ff:ui-monospace, ...` |
| **Text Align** | `text-center`, `text-left` | `--ta` | `text-center` -> `--ta:center` |
| **Text Transform** | `uppercase`, `lowercase`, `capitalize` | `--tt` | `uppercase` -> `--tt:uppercase` |
| **Text Decoration** | `underline`, `line-through` | `--td` | `underline` -> `--td:underline` |
| **Line Height** | `leading-tight`, `leading-6` | `--lh` | `leading-tight` -> `--lh:1.25` |
| **Letter Spacing** | `tracking-wide`, `tracking-tight` | `--ls` | `tracking-wide` -> `--ls:0.025em` |
| **Whitespace** | `whitespace-nowrap`, `whitespace-pre` | `--ws` | `whitespace-nowrap` -> `--ws:nowrap` |
| **Text Color** | `text-gray-500`, `text-white` | `--c` | `text-white` -> `--c:#ffffff` |
| **Background Color** | `bg-blue-600`, `bg-white` | `--bgc` | `bg-blue-600` -> `--bgc:#2563eb` |
| **Border Color** | `border-gray-300` | `--bc` | `border-gray-300` -> `--bc:#d1d5db` |
| **Border Width** | `border`, `border-2`, `border-t` | `--b`, `--bw`, `--bt` | `border` -> `--b:1px solid` |
| **Border Style** | `border-dashed`, `border-dotted` | `--bs` | `border-dashed` -> `--bs:dashed` |
| **Border Radius** | `rounded`, `rounded-lg`, `rounded-full` | `--radius` | `rounded-lg` -> `--radius:0.5rem` |
| **Shadow** | `shadow`, `shadow-md`, `shadow-lg` | `--shadow` | `shadow-md` -> `--shadow:3` |
| **Opacity** | `opacity-50`, `opacity-0` | `--op` | `opacity-50` -> `--op:0.5` |
| **Cursor** | `cursor-pointer`, `cursor-not-allowed` | `--cur` | `cursor-pointer` -> `--cur:pointer` |
| **Pointer Events** | `pointer-events-none` | `--pe` | `pointer-events-none` -> `--pe:none` |
| **User Select** | `select-none`, `select-all` | `--us` | `select-none` -> `--us:none` |
| **Overflow** | `overflow-hidden`, `overflow-auto` | `--of`, `--ofx`, `--ofy` | `overflow-hidden` -> `--of:hidden` |
| **Object Fit** | `object-cover`, `object-contain` | `--objf` | `object-cover` -> `--objf:cover` |
| **Visibility** | `visible`, `invisible` | `--v` | `invisible` -> `--v:hidden` |
| **Scale** | `scale-50`, `scale-150` | `--scale` | `scale-50` -> `--scale:0.5` |
| **Rotate** | `rotate-45`, `-rotate-90` | `--rotate` | `rotate-45` -> `--rotate:45deg` |
| **Translate** | `translate-x-4`, `-translate-y-1/2` | `--translatex`, `--translatey` | `translate-x-4` -> `--translatex:1rem` |
| **Transform Origin** | `origin-center`, `origin-top-right` | `--to` | `origin-center` -> `--to:center` |
| **Transition** | `transition`, `transition-colors` | `--tn` | `transition` -> `--tn:color, background-color, ...` |
| **Duration** | `duration-300`, `duration-150` | `--tdn` | `duration-300` -> `--tdn:300ms` |
| **Easing** | `ease-in-out`, `ease-linear` | `--ttf` | `ease-in-out` -> `--ttf:cubic-bezier(0.4, 0, 0.2, 1)` |

### Responsive Prefix Mapping

Tailwind responsive prefixes are converted to startr.style suffixes on the custom property name:

| Tailwind Prefix | startr.style Suffix | Example |
|----------------|---------------------|---------|
| `sm:` | `-sm` | `sm:flex` -> `--d-sm:flex` |
| `md:` | `-md` | `md:grid-cols-2` -> `--gtc-md:repeat(2, minmax(0, 1fr))` |
| `lg:` | `-lg` | `lg:p-8` -> `--p-lg:2rem` |
| `xl:` | `-xl` | `xl:text-xl` -> `--size-xl:1.25rem` |
| `2xl:` | `-xl` | `2xl:hidden` -> `--d-xl:none` (mapped to -xl) |
| `print:` | `-pt` | `print:hidden` -> `--d-pt:none` |

### Hover and Dark Mode

| Tailwind Prefix | startr.style Pattern | Example |
|----------------|---------------------|---------|
| `hover:` | `--hvr-{prop}` | `hover:bg-gray-200` -> `--hvr-bgc:#e5e7eb` |
| `dark:` | `--dark-{prop}` | `dark:bg-gray-800` -> `--dark-bgc:#1f2937` |

Prefixes compose. `sm:hover:bg-blue-500` becomes `--hvr-bgc-sm:#3b82f6`.

## What Cannot Be Auto-Converted

The following patterns are flagged for manual review and left in the `class` attribute:

| Pattern | Reason |
|---------|--------|
| `focus:*`, `focus-within:*`, `focus-visible:*` | Pseudo-class states cannot be expressed as inline styles |
| `active:*`, `visited:*`, `target:*` | Pseudo-class states |
| `first:*`, `last:*`, `odd:*`, `even:*` | Structural pseudo-classes |
| `group-hover:*`, `group-focus:*` | Requires parent `.group` selector context |
| `peer-hover:*`, `peer-focus:*`, `peer-checked:*` | Requires sibling `.peer` selector context |
| `before:*`, `after:*` | Pseudo-elements |
| `placeholder:*`, `file:*`, `marker:*` | Pseudo-element selectors |
| `disabled:*`, `checked:*`, `required:*`, `invalid:*` | Form state pseudo-classes |
| `motion-safe:*`, `motion-reduce:*` | Prefers-reduced-motion media queries |
| `portrait:*`, `landscape:*` | Orientation media queries |
| `ltr:*`, `rtl:*` | Direction selectors |
| `data-[...]:*` | Data attribute selectors |
| `has:*`, `group-has:*`, `peer-has:*` | :has() relational pseudo-class |
| `contrast-more:*`, `contrast-less:*` | Prefers-contrast media queries |
| `supports:*` | @supports queries |
| `open:*` | Details/dialog open state |
| `animate-spin`, `animate-bounce`, ... | Require `@keyframes` definitions (converted but flagged) |
| `ring-*` | Box-shadow approximation (converted but flagged for review) |
| `space-x-*`, `space-y-*` | Uses `> * + *` combinator; converted to `gap` with review flag |
| `divide-*` | Uses `> * + *` combinator; flagged for review |
| Gradient stops (`from-*`, `via-*`, `to-*`) | Converted but require manual gradient setup verification |
| Multiple filters (`blur-*` + `brightness-*`) | Each filter overwrites `--fr`; must be combined manually |

Classes with no matching mapping rule (e.g., project-specific utilities) are left in `class` unchanged.

## Architecture

```
tw2startr/
  bin/
    tw2startr.js          # CLI entry point
  src/
    cli.js                # Argument parsing, file discovery, orchestration
    index.js              # Public API exports
    mappings/
      index.js            # Combines all rule modules (order matters)
      layout.js           # display, position, flex, grid, alignment, z-index, gap
      spacing.js          # padding, margin, space-x/y
      sizing.js           # width, height, min/max variants, size shorthand
      typography.js       # font-size, weight, family, alignment, decoration, line-height
      colors.js           # bg, text, border, divide, ring, outline, accent, caret colors
      borders.js          # border width/style/radius, shadow, outline, ring, divide
      effects.js          # opacity, cursor, overflow, filters, blur, scroll, aspect-ratio
      transforms.js       # scale, rotate, translate, skew, transitions, animation
    parser/
      svelte-parser.js    # Finds HTML elements with class attributes in Svelte/HTML markup
      class-extractor.js  # Splits class strings into static tokens and dynamic expressions
    transformer/
      class-converter.js  # Matches Tailwind classes to mapping rules, handles prefixes
      partial-handler.js  # Processes elements: converts classes, merges styles, rebuilds tags
      style-merger.js     # Merges new CSS custom properties into existing style attributes
    reporter/
      diff-reporter.js    # Generates unified diffs between original and converted content
      summary-reporter.js # Aggregates per-file and overall conversion statistics
      manual-review.js    # Collects items that need human attention after conversion
    utils/
      css-value-resolver.js  # Resolves spacing scale, arbitrary values, fractions, colors
      tailwind-values.js     # Tailwind default value tables (font sizes, weights, radii, etc.)
  test/
    mappings.test.js      # Unit tests for mapping rules
    parser.test.js        # Unit tests for Svelte parsing and class extraction
    transformer.test.js   # Unit tests for the conversion pipeline
    integration.test.js   # End-to-end tests against fixture files
    fixtures/             # Sample Svelte files for integration tests
```

### Processing Pipeline

1. **Parse** -- `svelte-parser` scans the file for HTML opening tags containing `class` attributes.
2. **Extract** -- `class-extractor` splits the class value into static class tokens and dynamic Svelte expressions (ternaries, template literals).
3. **Convert** -- `class-converter` matches each static class against mapping rules, handling responsive/state prefixes and negative values.
4. **Merge** -- `style-merger` combines newly generated CSS custom properties with any existing `style` attribute.
5. **Rebuild** -- `partial-handler` reconstructs each tag with the updated `style` and reduced `class` attributes, then splices the result back into the file content.

## Extending Mappings

Each mapping module exports an array of rule objects. A rule has a `pattern` (regex) and a `convert` function:

```js
// Example: adding a custom utility
{
  pattern: /^my-utility-(.+)$/,
  convert: (match) => {
    return { prop: '--my-prop', value: match[1] };
  }
}
```

The `convert` function receives the regex match array and returns one of:

- `{ prop, value }` -- a single CSS property/value pair
- `[{ prop, value }, ...]` -- multiple properties (e.g., `inset-x` sets both `--left` and `--right`)
- `{ prop, value, review: 'message' }` -- a conversion that needs human verification
- `null` -- no match for this particular input (the engine tries the next rule)

To add a new rule:

1. Add it to the appropriate module in `src/mappings/` (or create a new one).
2. If creating a new module, import and spread it into `src/mappings/index.js`. Order matters: more specific rules should come before general ones.
3. Add tests in `test/mappings.test.js`.

## Testing

Tests use [Vitest](https://vitest.dev/).

```bash
# Run the full test suite
npm test

# Watch mode for development
npm run test:watch
```

Test files:

- `test/mappings.test.js` -- verifies individual class-to-property conversions
- `test/parser.test.js` -- verifies Svelte tag parsing and class extraction
- `test/transformer.test.js` -- verifies the end-to-end element transformation
- `test/integration.test.js` -- runs against fixture `.svelte` files in `test/fixtures/`

## Standalone Use

tw2startr is structured as a self-contained npm package with its own `package.json`, `bin` entry, and public API exports. It has no runtime dependencies beyond Node.js (Vitest is a dev dependency only).

To use it outside this repository:

```bash
# From another project
npm install --save-dev /path/to/tools/tw2startr

# Or after publishing to npm
npm install --save-dev tw2startr
```

The programmatic API is available via the main export:

```js
import { convertClass, convertClasses, parsePrefixes, allRules } from 'tw2startr';

const result = convertClass('sm:hover:bg-gray-100');
// { converted: true, properties: [{ prop: '--hvr-bgc-sm', value: '#f3f4f6' }], ... }
```
