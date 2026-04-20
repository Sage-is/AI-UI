#!/usr/bin/env node
/**
 * build-phase2-sprites.mjs
 *
 * Adds new inline SVG icons to the existing sprite sheet and creates oauth.svg.
 * Updates icons.ts with new entries.
 */

import { readFileSync, writeFileSync } from 'fs';

const NAMED_MANIFEST = 'scripts/inline-svg-manifest-named.json';
const SPRITE = 'app/static/sprites/icons.svg';
const ICONS_TS = 'app/src/lib/components/icons.ts';
const OAUTH_OUT = 'app/static/sprites/oauth.svg';

// Grid layout constants (must match extract-icons.mjs)
const COLS = 12;
const CELL_W = 48;
const CELL_H = 56;
const ICON_SIZE = 24;
const ICON_OFFSET_X = (CELL_W - ICON_SIZE) / 2;
const ICON_OFFSET_Y = 8;

function kebabToPascal(str) {
  return str.split('-').map(s => s.charAt(0).toUpperCase() + s.slice(1)).join('');
}

// ─── Load data ──────────────────────────────────────────────────────

const named = JSON.parse(readFileSync(NAMED_MANIFEST, 'utf-8'));
const spriteContent = readFileSync(SPRITE, 'utf-8');

// Get existing symbol IDs
const existingIds = new Set();
const idRegex = /<symbol\s+id="([^"]+)"/g;
let im;
while ((im = idRegex.exec(spriteContent)) !== null) existingIds.add(im[1]);

console.log(`Existing sprite symbols: ${existingIds.size}`);

// ─── Build new symbols ──────────────────────────────────────────────

const newSymbols = [];
const seenNames = new Set(existingIds);
const nameMap = new Map(); // hash -> name (for icons.ts)

for (const icon of named.icons) {
  if (icon.spriteMatch) {
    // Already in sprite, just record the mapping
    nameMap.set(icon.hash, icon.spriteMatch);
    continue;
  }

  // Deduplicate by name — if we already added this name, skip
  let name = icon.name;
  if (seenNames.has(name)) {
    // Append hash suffix to make unique
    const suffix = icon.hash.slice(0, 4);
    const candidate = `${name}-${suffix}`;
    if (!seenNames.has(candidate)) {
      name = candidate;
    } else {
      // Already have this exact icon, just record the mapping
      nameMap.set(icon.hash, name);
      continue;
    }
  }

  nameMap.set(icon.hash, name);
  seenNames.add(name);

  // Build symbol from innerContent
  let inner = icon.innerContent;

  // Clean: remove stroke="currentColor" and fill="currentColor" from paths (inherit from symbol)
  inner = inner.replace(/\s+stroke="currentColor"/g, '');
  inner = inner.replace(/\s+fill="currentColor"/g, '');

  // Build symbol attributes
  const attrs = [`id="${name}"`, `viewBox="${icon.viewBox}"`];
  if (icon.type === 'stroke') {
    attrs.push('fill="none"', 'stroke="currentColor"');
  } else if (icon.type === 'fill') {
    attrs.push('fill="currentColor"');
  } else if (icon.type === 'mixed') {
    attrs.push('fill="currentColor"', 'stroke="currentColor"');
  }

  newSymbols.push(`  <symbol ${attrs.join(' ')}>\n    ${inner.trim()}\n  </symbol>`);
}

console.log(`New symbols to add: ${newSymbols.length}`);

// ─── Insert new symbols into sprite ─────────────────────────────────

// Insert before </defs>
const defsEnd = spriteContent.indexOf('</defs>');
if (defsEnd === -1) throw new Error('Could not find </defs> in sprite');

const newSymbolBlock = '\n\n<!-- Phase 2: Inline SVG icons -->\n' + newSymbols.join('\n\n') + '\n';
let updatedSprite = spriteContent.slice(0, defsEnd) + newSymbolBlock + spriteContent.slice(defsEnd);

// ─── Rebuild the visual grid ────────────────────────────────────────

// Extract all symbol IDs from the updated sprite
const allIds = [];
const allIdRegex = /<symbol\s+id="([^"]+)"[^>]*viewBox="([^"]+)"/g;
let aim;
while ((aim = allIdRegex.exec(updatedSprite)) !== null) {
  allIds.push({ id: aim[1], viewBox: aim[2] });
}

const rows = Math.ceil(allIds.length / COLS);
const gridW = COLS * CELL_W;
const gridH = rows * CELL_H;

let gridContent = '';
// Grid lines
for (let r = 0; r <= rows; r++) {
  gridContent += `  <line x1="0" y1="${r * CELL_H}" x2="${gridW}" y2="${r * CELL_H}" stroke="#eee" stroke-width="0.5"/>\n`;
}
for (let c = 0; c <= COLS; c++) {
  gridContent += `  <line x1="${c * CELL_W}" y1="0" x2="${c * CELL_W}" y2="${gridH}" stroke="#eee" stroke-width="0.5"/>\n`;
}

// Icons + labels
allIds.forEach((icon, i) => {
  const col = i % COLS;
  const row = Math.floor(i / COLS);
  const x = col * CELL_W + ICON_OFFSET_X;
  const y = row * CELL_H + ICON_OFFSET_Y;
  const labelX = col * CELL_W + CELL_W / 2;
  const labelY = row * CELL_H + ICON_OFFSET_Y + ICON_SIZE + 12;

  gridContent += `  <use href="#${icon.id}" x="${x}" y="${y}" width="${ICON_SIZE}" height="${ICON_SIZE}" stroke-width="1.5" color="#333"/>\n`;
  gridContent += `  <text x="${labelX}" y="${labelY}">${icon.id}</text>\n`;
});

// Replace the visual grid section
const styleEnd = updatedSprite.indexOf('</style>');
const svgClose = updatedSprite.lastIndexOf('</svg>');

// Everything from after </style> to before </svg> is the grid
const beforeGrid = updatedSprite.slice(0, styleEnd + '</style>'.length);
const afterGrid = updatedSprite.slice(svgClose);

// Update viewBox
const displayW = gridW * 4;
const displayH = gridH * 4;
const newHeader = beforeGrid.replace(
  /viewBox="[^"]*"\s+width="\d+"\s+height="\d+"/,
  `viewBox="0 0 ${gridW} ${gridH}" width="${displayW}" height="${displayH}"`
);
// Update icon count in comment
const newHeader2 = newHeader.replace(/\d+ icons in a/, `${allIds.length} icons in a`);

updatedSprite = newHeader2 + '\n\n<!-- Visual Grid -->\n' + gridContent + afterGrid + '\n';

writeFileSync(SPRITE, updatedSprite);
console.log(`Updated ${SPRITE} (${allIds.length} total symbols, ${(updatedSprite.length / 1024).toFixed(1)} KB)`);

// ─── Create oauth.svg ───────────────────────────────────────────────

const brandSymbols = named.brands.map(b => {
  return `  <symbol id="${b.name}" viewBox="${b.viewBox}">\n    ${b.innerContent.trim()}\n  </symbol>`;
}).join('\n\n');

const oauthSvg = `<?xml version="1.0" encoding="UTF-8"?>
<!--
  Brand Logo Sprite Sheet — auto-generated by scripts/build-phase2-sprites.mjs
  ${named.brands.length} brand logos. Multi-color, does not use currentColor.
-->
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     style="display:none">
<defs>
${brandSymbols}
</defs>
</svg>
`;

writeFileSync(OAUTH_OUT, oauthSvg);
console.log(`Created ${OAUTH_OUT} (${named.brands.length} brand logos)`);

// ─── Update icons.ts ────────────────────────────────────────────────

let iconsTs = readFileSync(ICONS_TS, 'utf-8');

// Add new entries to ICON_NAMES
const newEntries = [];
for (const [hash, name] of nameMap) {
  if (existingIds.has(name)) continue; // Already in icons.ts
  const pascal = kebabToPascal(name);
  // Check if this PascalCase key already exists
  if (iconsTs.includes(`${pascal}: '`)) continue;
  newEntries.push(`  ${pascal}: '${name}'`);
}

// Deduplicate entries
const uniqueEntries = [...new Set(newEntries)];

if (uniqueEntries.length > 0) {
  // Insert before the closing } of ICON_NAMES
  const closingBrace = iconsTs.indexOf('} as const;');
  if (closingBrace !== -1) {
    const insertion = ',\n' + uniqueEntries.join(',\n') + '\n';
    iconsTs = iconsTs.slice(0, closingBrace) + insertion + iconsTs.slice(closingBrace);
  }
}

// Add new fill-only entries
const newFillOnly = [];
for (const icon of named.icons) {
  if (icon.spriteMatch) continue;
  if (icon.type === 'fill') {
    const name = nameMap.get(icon.hash);
    if (name && !iconsTs.includes(`'${name}'`)) {
      // It was added to ICON_NAMES above, check if it should be in FILL_ONLY_ICONS
      newFillOnly.push(`  '${name}'`);
    }
  }
}

if (newFillOnly.length > 0) {
  const fillSetClose = iconsTs.indexOf(']);', iconsTs.indexOf('FILL_ONLY_ICONS'));
  if (fillSetClose !== -1) {
    const insertion = ',\n' + [...new Set(newFillOnly)].join(',\n') + '\n';
    iconsTs = iconsTs.slice(0, fillSetClose) + insertion + iconsTs.slice(fillSetClose);
  }
}

writeFileSync(ICONS_TS, iconsTs);
console.log(`Updated ${ICONS_TS}`);

// ─── Write name mapping for Script 3 ───────────────────────────────

const mapping = {};
for (const icon of named.icons) {
  mapping[icon.hash] = nameMap.get(icon.hash) || icon.name;
}
writeFileSync('scripts/inline-svg-name-mapping.json', JSON.stringify(mapping, null, 2));
console.log(`Wrote scripts/inline-svg-name-mapping.json`);

console.log('\nDone!');
