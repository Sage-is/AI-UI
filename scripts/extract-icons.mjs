#!/usr/bin/env node
/**
 * extract-icons.mjs
 *
 * Reads all Svelte icon components from app/src/lib/components/icons/,
 * extracts their SVG data, and generates:
 *   1. app/static/sprites/icons.svg  — SVG sprite sheet with visual grid
 *   2. app/src/lib/components/icons.ts — name map + TypeScript types
 */

import { readFileSync, writeFileSync, readdirSync } from 'fs';
import { join, basename } from 'path';

const ICONS_DIR = 'app/src/lib/components/icons';
const SPRITE_OUT = 'app/static/sprites/icons.svg';
const TYPES_OUT = 'app/src/lib/components/icons.ts';

// Icons confirmed unused — skip these
const SKIP = new Set([
  'BookOpen', 'CalendarSolid', 'CheckCircle', 'Cog6Solid',
  'DocumentArrowDown', 'DocumentCheck', 'FloppyDisk', 'Lifebuoy', 'QueueList'
]);

// Icons with intentionally hardcoded stroke-width on <path> — preserve as inline style
const HARDCODED_STROKE_WIDTH = new Set(['Photo', 'CheckBox']);

// Grid layout
const COLS = 12;
const CELL_W = 48;
const CELL_H = 56;
const ICON_SIZE = 24;
const ICON_OFFSET_X = (CELL_W - ICON_SIZE) / 2;
const ICON_OFFSET_Y = 8;

function pascalToKebab(str) {
  return str
    .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
    .replace(/([A-Z])([A-Z][a-z])/g, '$1-$2')
    .toLowerCase();
}

function parseIcon(filePath, fileName) {
  const content = readFileSync(filePath, 'utf-8');
  const name = fileName.replace('.svelte', '');

  // Extract script props
  const classMatch = content.match(/export let className\s*=\s*['"]([^'"]+)['"]/);
  const strokeMatch = content.match(/export let strokeWidth\s*=\s*['"]([^'"]+)['"]/);
  const defaultClass = classMatch ? classMatch[1] : 'size-4';
  const defaultStroke = strokeMatch ? strokeMatch[1] : null;

  // Extract SVG element attributes
  const svgMatch = content.match(/<svg[\s\S]*?>/);
  if (!svgMatch) return null;
  const svgTag = svgMatch[0];

  // viewBox
  const vbMatch = svgTag.match(/viewBox="([^"]+)"/);
  const viewBox = vbMatch ? vbMatch[1] : '0 0 24 24';

  // fill on <svg>
  const fillMatch = svgTag.match(/\bfill="([^{"]+)"/);
  const svgFill = fillMatch ? fillMatch[1] : null;

  // stroke on <svg>
  const strokeAttrMatch = svgTag.match(/\bstroke="([^{"]+)"/);
  const svgStroke = strokeAttrMatch ? strokeAttrMatch[1] : null;

  // Determine rendering type
  let renderType = 'stroke'; // default
  if (svgFill === 'currentColor' && !svgStroke) {
    renderType = 'fill';
  } else if (svgFill === 'currentColor' && svgStroke === 'currentColor') {
    renderType = 'mixed';
  } else if (svgFill === 'none' || svgFill === null) {
    renderType = 'stroke';
  }

  // Extract all path/element content between <svg> and </svg>
  // Get everything after the <svg...> opening tag and before </svg>
  const svgContentMatch = content.match(/<svg[\s\S]*?>([\s\S]*?)<\/svg\s*>/);
  if (!svgContentMatch) return null;
  let innerContent = svgContentMatch[1];

  // Remove <slot /> if present
  innerContent = innerContent.replace(/<slot\s*\/?>(\s*<\/slot>)?/g, '');

  // For icons with hardcoded stroke-width on paths, convert attribute to inline style
  if (HARDCODED_STROKE_WIDTH.has(name)) {
    innerContent = innerContent.replace(
      /stroke-width="([^"]+)"/g,
      'style="stroke-width: $1"'
    );
  }

  // Clean up: remove stroke="currentColor" from paths (it will inherit from symbol)
  innerContent = innerContent.replace(/\s+stroke="currentColor"/g, '');

  // Clean up: remove fill="currentColor" from paths (it will inherit from symbol)
  // But preserve fill="none" if present on a path
  innerContent = innerContent.replace(/\s+fill="currentColor"/g, '');

  // Trim whitespace
  innerContent = innerContent.trim();

  return {
    name,
    id: pascalToKebab(name),
    viewBox,
    renderType,
    svgFill,
    svgStroke,
    defaultClass,
    defaultStroke,
    innerContent,
  };
}

function buildSymbol(icon) {
  const attrs = [`id="${icon.id}"`, `viewBox="${icon.viewBox}"`];

  if (icon.renderType === 'stroke') {
    attrs.push('fill="none"', 'stroke="currentColor"');
  } else if (icon.renderType === 'fill') {
    attrs.push('fill="currentColor"');
  } else if (icon.renderType === 'mixed') {
    attrs.push('fill="currentColor"', 'stroke="currentColor"');
  }

  return `  <symbol ${attrs.join(' ')}>\n    ${icon.innerContent}\n  </symbol>`;
}

function buildGrid(icons) {
  const rows = Math.ceil(icons.length / COLS);
  const gridW = COLS * CELL_W;
  const gridH = rows * CELL_H;
  let gridContent = '';

  // Light grid lines
  for (let r = 0; r <= rows; r++) {
    gridContent += `  <line x1="0" y1="${r * CELL_H}" x2="${gridW}" y2="${r * CELL_H}" stroke="#eee" stroke-width="0.5"/>\n`;
  }
  for (let c = 0; c <= COLS; c++) {
    gridContent += `  <line x1="${c * CELL_W}" y1="0" x2="${c * CELL_W}" y2="${gridH}" stroke="#eee" stroke-width="0.5"/>\n`;
  }

  // Icons + labels
  icons.forEach((icon, i) => {
    const col = i % COLS;
    const row = Math.floor(i / COLS);
    const x = col * CELL_W + ICON_OFFSET_X;
    const y = row * CELL_H + ICON_OFFSET_Y;
    const labelX = col * CELL_W + CELL_W / 2;
    const labelY = row * CELL_H + ICON_OFFSET_Y + ICON_SIZE + 12;

    // Determine stroke-width for the grid preview
    const previewStroke = icon.defaultStroke || '1.5';

    gridContent += `  <use href="#${icon.id}" x="${x}" y="${y}" width="${ICON_SIZE}" height="${ICON_SIZE}"`;
    if (icon.renderType === 'stroke' || icon.renderType === 'mixed') {
      gridContent += ` stroke-width="${previewStroke}"`;
    }
    gridContent += ` color="#333"/>\n`;
    gridContent += `  <text x="${labelX}" y="${labelY}">${icon.id}</text>\n`;
  });

  return { gridContent, gridW, gridH };
}

function buildSpriteSVG(icons) {
  const symbols = icons.map(buildSymbol).join('\n\n');
  const { gridContent, gridW, gridH } = buildGrid(icons);

  // Scale up for comfortable zoom in editors
  const displayW = gridW * 4;
  const displayH = gridH * 4;

  return `<?xml version="1.0" encoding="UTF-8"?>
<!--
  Icon Sprite Sheet — auto-generated by scripts/extract-icons.mjs
  ${icons.length} icons in a ${COLS}-column grid.
  Open in Figma or Inkscape to edit. Runtime use via <use href="/sprites/icons.svg#icon-id"/>.
-->
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     viewBox="0 0 ${gridW} ${gridH}" width="${displayW}" height="${displayH}"
     style="background:#fff">

<defs>
${symbols}
</defs>

<style>
  text { font: 5px sans-serif; fill: #999; text-anchor: middle; }
</style>

<!-- Visual Grid -->
${gridContent}
</svg>
`;
}

function buildTypesTS(icons) {
  const entries = icons.map(icon => `  ${icon.name}: '${icon.id}'`).join(',\n');
  const defaultClassMap = icons
    .filter(i => i.defaultClass !== 'size-4' && i.defaultClass !== 'w-4 h-4')
    .map(i => `  '${i.id}': '${i.defaultClass}'`)
    .join(',\n');
  const defaultStrokeMap = icons
    .filter(i => i.defaultStroke && i.defaultStroke !== '1.5')
    .map(i => `  '${i.id}': '${i.defaultStroke}'`)
    .join(',\n');
  const fillOnlyList = icons
    .filter(i => i.renderType === 'fill')
    .map(i => `  '${i.id}'`)
    .join(',\n');

  return `// Auto-generated by scripts/extract-icons.mjs — do not edit manually

export const ICON_NAMES = {
${entries}
} as const;

export type IconName = typeof ICON_NAMES[keyof typeof ICON_NAMES];

/** Icons whose original default className differs from 'size-4' */
export const ICON_DEFAULT_CLASS: Partial<Record<IconName, string>> = {
${defaultClassMap}
};

/** Icons whose original default strokeWidth differs from '1.5' */
export const ICON_DEFAULT_STROKE: Partial<Record<IconName, string>> = {
${defaultStrokeMap}
};

/** Fill-only icons (no meaningful strokeWidth) */
export const FILL_ONLY_ICONS: Set<IconName> = new Set([
${fillOnlyList}
]);
`;
}

// ─── Main ───────────────────────────────────────────────────────────────

const files = readdirSync(ICONS_DIR)
  .filter(f => f.endsWith('.svelte'))
  .sort();

const icons = [];
const skipped = [];

for (const file of files) {
  const name = file.replace('.svelte', '');
  if (SKIP.has(name)) {
    skipped.push(name);
    continue;
  }
  const icon = parseIcon(join(ICONS_DIR, file), file);
  if (icon) {
    icons.push(icon);
  } else {
    console.warn(`  WARN: Could not parse ${file}`);
  }
}

console.log(`Parsed ${icons.length} icons, skipped ${skipped.length} unused: ${skipped.join(', ')}`);

// Group summary
const stroke = icons.filter(i => i.renderType === 'stroke').length;
const fill = icons.filter(i => i.renderType === 'fill').length;
const mixed = icons.filter(i => i.renderType === 'mixed').length;
console.log(`  Stroke: ${stroke}, Fill: ${fill}, Mixed: ${mixed}`);

const viewBoxes = {};
icons.forEach(i => { viewBoxes[i.viewBox] = (viewBoxes[i.viewBox] || 0) + 1; });
console.log(`  viewBox distribution:`, viewBoxes);

// Write outputs
const spriteSVG = buildSpriteSVG(icons);
writeFileSync(SPRITE_OUT, spriteSVG);
console.log(`\nWrote ${SPRITE_OUT} (${(spriteSVG.length / 1024).toFixed(1)} KB)`);

const typesTS = buildTypesTS(icons);
writeFileSync(TYPES_OUT, typesTS);
console.log(`Wrote ${TYPES_OUT} (${(typesTS.length / 1024).toFixed(1)} KB)`);

console.log('\nDone!');
