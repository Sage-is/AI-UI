# Startr.Style — Framework & Brand Overview

Startr.Style is a utility-complete, inline-first CSS framework maintained by
Alexander Somma and Izzy Plante (Startr / OpenCo). It is the brand and code
language used alongside Sage.is. Source lives at
[github.com/Startr/Style](https://github.com/Startr/Style); the canonical site
is [startr.style](https://startr.style).

This document is the agent's working reference for generating single-page HTML
artifacts in the Startr.Style language. Sibling files in this `kb/` folder
extend it (helpers, components, patterns) as they are added.

## What makes Startr.Style different

The framework is roughly **45 KB (≈8 KB gzipped)** — about 1/70th the size of
Tailwind. It rejects class-soup and build steps. Instead, every utility is a
**CSS custom property applied inline** via the `style` attribute.

```html
<div style="--bg:#2A2A2A; --c:white; --p:2rem; --radius:8px">
  Inline-first. No build step. Any valid CSS value.
</div>
```

The guiding principle is **Locality of Behaviour (LoB)**: when you read an
element, you should understand its styling without hunting through CSS files.
Style lives next to structure.

### Why this matters for an agent

- Generated HTML is self-contained. One `<link>` tag and a `style` attribute is
  the whole pipeline.
- Any valid CSS value is allowed (gradients, `hsl()`, `clamp()`, `url()`,
  `calc()`). There are no preset palettes to memorize.
- Responsive behavior is encoded inline via suffixed properties — no
  `@media` blocks needed.

## Boilerplate every artifact starts from

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Page title</title>
  <link rel="stylesheet" href="https://startr.style/style.css">
</head>
<body>
  <!-- content -->
</body>
</html>
```

Alternative CDN: `https://unpkg.com/Startr/Style@latest/dist/style.min.css`.
Modular builds also exist (`style-base.min.css`, `style-helpers.min.css`,
`style-utilities.min.css`) for narrower needs.

## The utility model

Every supported CSS property has a short custom-property alias. You set it in
the inline `style` attribute and the framework's stylesheet maps it to the real
property.

```html
<element style="--<prop>:<value>; --<prop>-<bp>:<value>">
```

### Responsive suffixes (mobile-first)

| Suffix | Activates at      | Use for                          |
|--------|-------------------|----------------------------------|
| (none) | All viewports     | Base / mobile                    |
| `-sm`  | ≥ 640px           | Large phones / small tablets     |
| `-md`  | ≥ 768px           | Tablets                          |
| `-lg`  | ≥ 1024px          | Laptops                          |
| `-xl`  | ≥ 1280px          | Desktops                         |
| `-pt`  | Print only        | Print stylesheets                |

```html
<nav style="--d:flex; --fd:column; --fd-md:row; --g:1rem">…</nav>
```

### Core utility map (most-used subset)

The full property table is large; the agent should rely on this lookup for
common cases and reach for the long table below for the rest.

**Layout & box model**
- `--d` display · `--pos` position · `--top` `--right` `--bottom` `--left`
- `--w` width · `--h` height · `--minw` `--minh` `--maxw` `--maxh`
- `--m` margin · `--mt` `--mr` `--mb` `--ml` · `--mx` `--my` (helpers)
- `--p` padding · `--pt` `--pr` `--pb` `--pl` · `--px` `--py` (helpers)
- `--of` overflow · `--ofx` `--ofy` · `--z` z-index

**Flex & grid**
- `--fd` flex-direction · `--fw` flex-wrap · `--fx` flex
- `--ai` align-items · `--ac` align-content · `--as` align-self
- `--jc` justify-content · `--o` order · `--g` gap · `--cg` column-gap
- `--gtc` grid-template-columns · `--gtr` grid-template-rows
- `--gc` grid-column · `--gr` grid-row · `--gac` `--gar`

**Color & background**
- `--c` color · `--bg` background · `--bgc` background-color
- `--bgi` background-image · `--bgp` background-position · `--bgs` size
- `--grad` (helper) linear-gradient shortcut · `--grad-color` overrides default
- `--op` opacity

**Typography**
- `--ff` font-family · `--size` font-size · `--weight` font-weight
- `--lh` line-height · `--ls` letter-spacing · `--ta` text-align
- `--tt` text-transform · `--td` text-decoration · `--ts` text-shadow
- `--line-clamp` (helper) clamp text to N lines
- `--text-3d` (helper) 3D text shadow color, pair with `--c`

**Borders, radii, shadows**
- `--b` border · `--bt` `--br` `--bb` `--bl` · `--bw` width · `--bc` color · `--bs` style
- `--radius` border-radius · `--bblr` `--bbrr` corner radii
- `--shadow:N` integer-intensity soft shadow behind element (see helpers below for variants)

**Transform & motion**
- `--t` transform · `--tn` transition · `--tnd` duration · `--td` delay
- `--ttf` timing-function · `--tp` property

**Misc**
- `--cur` cursor · `--us` user-select · `--pe` pointer-events · `--v` visibility

### Full property reference

Used when a needed property is not in the short list above. All entries are
responsive unless marked **(no-rs)**.

```
align-content --ac · align-items --ai · align-self --as · all --all (no-rs)
background --bg · background-attachment --bga · background-color --bgc
background-image --bgi · background-position --bgp · background-repeat --bgr
background-size --bgs
border --b · border-bottom --bb · border-color --bc · border-left --bl
border-right --br · border-style --bs · border-top --bt · border-width --bw
border-radius --radius · border-bottom-left-radius --bblr · -right --bbrr
bottom --bottom · top --top · left --left · right --right
box-shadow --shadow · box-sizing --bxs (no-rs)
clear --cr · color --c
column-count --cc · column-fill --cf (no-rs) · column-gap --cg
column-rule --cr · column-span --cs
content --ct (no-rs) · cursor --cur (no-rs) · direction --dir (no-rs)
display --d
filter --fr (no-rs)
flex --fx · flex-basis --fb · flex-direction --fd · flex-grow --fg
flex-shrink --fs · flex-wrap --fw · float --ft
font-family --ff (no-rs) · font-size --size · font-style --fs (no-rs)
font-weight --weight (no-rs)
gap --g
grid-auto-columns --gac · grid-auto-rows --gar
grid-column --gc · grid-row --gr
grid-template-columns --gtc · grid-template-rows --gtr
height --h · width --w
justify-content --jc
letter-spacing --ls · line-height --lh
list-style --lis (no-rs) · -position --lisp (no-rs) · -type --list (no-rs)
margin --m · -top --mt · -right --mr · -bottom --mb · -left --ml
max-height --maxh · max-width --maxw · min-height --minh · min-width --minw
object-fit --objf · object-position --objp
opacity --op · order --o
outline --oe (no-rs)
overflow --of (no-rs) · overflow-x --ofx (no-rs) · overflow-y --ofy (no-rs)
padding --p · -top --pt · -right --pr · -bottom --pb · -left --pl
pointer-events --pe (no-rs) · position --pos
scroll-behavior --sb (no-rs)
text-align --ta · text-decoration --td (no-rs) · text-shadow --ts (no-rs)
text-transform --tt (no-rs)
transform --t · transform-origin --ta · transform-style --ts
transition --tn · -delay --td · -duration --tnd · -property --tp
transition-timing-function --ttf
user-select --us (no-rs) · vertical-align --va (no-rs)
visibility --v · white-space --ws · word-break --wb · writing-mode --wm
z-index --z
```

> **Naming collisions to watch.** Some short names map to two CSS properties  depending on context (e.g. `--cr` is both `clear` and `column-rule`; `--td`is both `text-decoration` and `transition-delay`; `--ts` is both  `text-shadow` and `transform-style`; `--fs` is both `flex-shrink` and `font-style`). The framework resolves by element context, but if you need both on one element, fall back to a plain CSS rule.

## Helper utilities (worth knowing by name)

These are sugar on top of the property map.

- `--px` / `--py` — symmetric padding on one axis.
- `--mx` / `--my` — symmetric margin on one axis.
- `--grad` — sets a linear-gradient on `background-image`.

Defaults from black to transparent. Accepts directions (`to top`, `to right`) or angles (`180deg`). Pair with `--grad-color` to swap the dark stop.

- `--line-clamp` — clamp text to N lines.
- `--text-3d` — 3D text-shadow color; pair with `--c` for the foreground.

**Shadow family** — `--shadow` and friends take a single **integer intensity**
(not a raw `box-shadow` value). Higher number = stronger shadow.

- `--shadow:4` — smooth drop shadow at the given intensity.
- `--shadow-soft:N` — softer falloff.
- `--shadow-hard:N` — tighter, harder edge.
- `--shadow-vert:N` — shadow projected only below the element.
- `--shadow-inset:N` — inset shadow.
- `--shadow-hvr:N` — shadow applied only on `:hover`.
- `--levitate:N` — combines vertical translate + shadow for a floating effect.

For an arbitrary `box-shadow` string, write a regular CSS rule — `--shadow`
won't accept it.

## Theme tokens (override these globally)

Defined in `src/variables.css` upstream. Override on `:root` (or any scope) to
re-skin a page without touching markup.

```css
:root {
  --primary:        darkblue;        /* brand primary */
  --secondary:      darkorange;      /* brand secondary */
  --text-main:      darkslategrey;   /* default body text */
  --border-radius:  3pt;             /* default radius */
}
```

When generating a themed page, set these once in a `<style>` block in `<head>`,
then style components inline as usual.

## Base elements (auto-styled, no markup needed)

The framework ships sensible defaults for raw HTML so semantic markup looks
good with zero attributes:

- Headings (`h1`–`h6`), paragraphs, links, lists.
- Buttons and form fields (`input`, `select`, `textarea`).
- Tables (`table`, `thead`, `tbody`, `tfoot`, with `scope` honored).
- Definition lists (`dl`, `dt`, `dd`).
- `<details>` / `<summary>` disclosure.
- Horizontal rules (`<hr>`).

**Rule of thumb:** use the right HTML element first; reach for utilities only
when you need to deviate from the default.

## Pattern library (working snippets)

### Centered hero

```html
<section style="--d:flex; --ai:center; --jc:center; --minh:100vh;
                --bg:#0b0c10; --c:#f5f7fa; --p:2rem; --ta:center">
  <div style="--maxw:42rem">
    <h1 style="--size:clamp(2rem,5vw,3.5rem); --weight:700; --lh:1.1">
      Build pages, not pipelines.
    </h1>
    <p style="--size:1.125rem; --op:.85; --mt:1rem">
      Inline-first CSS that loads in 8 KB.
    </p>
    <a href="#start"
       style="--d:inline-block; --mt:2rem; --px:1.5rem; --py:.75rem;
              --bg:var(--primary); --c:white; --radius:.5rem;
              --td:none; --weight:600">
      Get started
    </a>
  </div>
</section>
```

### Responsive nav (stacks on mobile, row on desktop)

```html
<nav style="--d:flex; --fd:column; --fd-md:row; --ai:center; --jc:space-between;
            --g:1rem; --p:1rem 1.5rem; --bg:white; --shadow:2">
  <a href="/" style="--weight:700; --c:var(--text-main); --td:none">Brand</a>
  <ul style="--d:flex; --fd:column; --fd-md:row; --g:1rem; --m:0; --p:0;
             --list:none">
    <li><a href="/docs">Docs</a></li>
    <li><a href="/blog">Blog</a></li>
    <li><a href="/login">Sign in</a></li>
  </ul>
</nav>
```

### Card grid

```html
<section style="--d:grid; --gtc:1fr; --gtc-md:repeat(2,1fr); --gtc-lg:repeat(3,1fr);
                --g:1.5rem; --p:2rem">
  <article style="--p:1.5rem; --radius:.75rem; --bg:white; --shadow-soft:6">
    <h3 style="--mt:0">Card title</h3>
    <p style="--op:.8; --line-clamp:3">Short summary, clamped to three lines.</p>
    <a href="#" style="--c:var(--primary); --weight:600">Read more →</a>
  </article>
  <!-- repeat -->
</section>
```

### Pricing tier with featured highlight

```html
<div style="--d:grid; --gtc:1fr; --gtc-md:repeat(3,1fr); --g:1.5rem">
  <div style="--p:2rem; --radius:1rem; --b:1px solid #e5e7eb; --bg:white">
    <h3>Starter</h3><p style="--size:2rem; --weight:700">$0</p>
  </div>
  <div style="--p:2rem; --radius:1rem; --bg:var(--primary); --c:white;
              --levitate:8">
    <span style="--d:inline-block; --bg:var(--secondary); --c:white;
                 --px:.5rem; --py:.125rem; --radius:999px;
                 --size:.75rem; --weight:600; --tt:uppercase">Popular</span>
    <h3 style="--mt:.5rem">Pro</h3><p style="--size:2rem; --weight:700">$19</p>
  </div>
  <div style="--p:2rem; --radius:1rem; --b:1px solid #e5e7eb; --bg:white">
    <h3>Team</h3><p style="--size:2rem; --weight:700">$49</p>
  </div>
</div>
```

### Loading spinner (uses inline `@keyframes`)

```html
<style>@keyframes spin { to { transform: rotate(360deg); } }</style>
<div style="--w:2rem; --h:2rem; --radius:50%;
            --b:3px solid rgba(0,0,0,.1); --bt:3px solid var(--primary);
            --t:rotate(0); --tn:transform .8s linear;
            animation: spin .8s linear infinite"></div>
```

## Voice & visual baseline (brand)

The framework is the substrate; the brand is how it's used.

**Voice** — direct, short sentences, active voice. Practical over poetic; show
the work. Optimistic but grounded — name the trade-offs.

**Visual baseline** — calm color, high contrast, generous whitespace. Type
earns its weight: pick fewer sizes, hit them hard. Components ship as small,
composable primitives.

**Aesthetic alignments referenced upstream:** brutalism (raw structure exposed),
modernism (form follows function), minimalism (intentional restraint),
experimentalism (reimagine conventions). Skeuomorphism and neumorphism are
*available* but rarely the default.

**Decision rule.** When two options compete on a brand surface, pick the one
that reads clearly to a tired person on a small screen at low brightness.

## Generation defaults the agent should keep

- Always include the `<link>` to `https://startr.style/style.css` in `<head>`.
- Set `<meta name="viewport">` for responsive behavior to actually work.
- Prefer semantic HTML (`<nav>`, `<article>`, `<section>`, `<button>`) over
  divs — base styles assume it.
- Style inline with custom properties. Reach for a `<style>` block only for
  `@keyframes`, `:root` theme overrides, or pseudo-classes (`:hover`,
  `:focus`) that inline can't express.
- Pass any valid CSS value — there is no preset spacing or color scale to
  conform to.
- For accessibility: hit WCAG AA contrast on text against backgrounds; respect
  `prefers-reduced-motion` when adding animation.
