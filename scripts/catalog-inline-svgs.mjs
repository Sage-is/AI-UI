#!/usr/bin/env node
/**
 * catalog-inline-svgs.mjs
 *
 * Scans all .svelte files for inline <svg> elements that aren't part of the
 * Icon component system. Extracts path data, deduplicates, and outputs a
 * manifest of unique icons that need sprite sheet entries.
 */

import { readFileSync, writeFileSync } from 'fs';
import { execSync } from 'child_process';
import { createHash } from 'crypto';

const SRC_DIR = 'app/src';

// Find all svelte files with inline <svg> tags
const files = execSync(
  `grep -rl '<svg' ${SRC_DIR} --include="*.svelte"`,
  { encoding: 'utf-8' }
).trim().split('\n').filter(Boolean);

// Skip the sprite test page and the Icon wrapper itself
const SKIP_FILES = new Set([
  'app/src/routes/dev/icons/+page.svelte',
  'app/src/lib/components/Icon.svelte',
]);

// Known brand logos — multi-color, can't use currentColor
const BRAND_COLORS = ['#EA4335', '#4285F4', '#FBBC05', '#34A853', '#f25022', '#00a4ef', '#7fba00', '#ffb900'];

function hashPath(d) {
  return createHash('md5').update(d.trim()).digest('hex').slice(0, 12);
}

const allInlineSvgs = [];
const uniquePaths = new Map(); // hash -> { paths, viewBox, type, files }

for (const file of files) {
  if (SKIP_FILES.has(file)) continue;

  const content = readFileSync(file, 'utf-8');

  // Find all inline <svg> blocks (not <use> references from our Icon component)
  const svgRegex = /<svg\b[^>]*>[\s\S]*?<\/svg\s*>/g;
  let match;

  while ((match = svgRegex.exec(content)) !== null) {
    const svgBlock = match[0];

    // Skip if it's our Icon wrapper (contains <use href)
    if (svgBlock.includes('<use href=')) continue;

    // Get line number
    const lineNum = content.slice(0, match.index).split('\n').length;

    // Extract viewBox
    const vbMatch = svgBlock.match(/viewBox="([^"]+)"/);
    const viewBox = vbMatch ? vbMatch[1] : 'unknown';

    // Extract all path d attributes
    const pathDs = [];
    const pathRegex = /d="([^"]+)"/g;
    let pm;
    while ((pm = pathRegex.exec(svgBlock)) !== null) {
      pathDs.push(pm[1]);
    }

    // Detect brand logo (has hardcoded colors)
    const isBrand = BRAND_COLORS.some(c => svgBlock.includes(c));

    // Detect fill vs stroke
    const hasFill = svgBlock.includes('fill="currentColor"');
    const hasStroke = svgBlock.includes('stroke="currentColor"');
    const hasFillNone = svgBlock.includes('fill="none"');
    let type = 'unknown';
    if (isBrand) type = 'brand';
    else if (hasFillNone && hasStroke) type = 'stroke';
    else if (hasFill && !hasStroke) type = 'fill';
    else if (hasFill && hasStroke) type = 'mixed';
    else if (hasStroke) type = 'stroke';
    else type = 'fill';

    // Extract all inner elements (paths, rects, circles, etc.)
    const innerMatch = svgBlock.match(/<svg[^>]*>([\s\S]*?)<\/svg\s*>/);
    const innerContent = innerMatch ? innerMatch[1].trim() : '';

    // Hash based on path data for deduplication
    const pathHash = pathDs.length > 0 ? hashPath(pathDs.join('|')) : hashPath(innerContent);

    const entry = {
      file,
      line: lineNum,
      viewBox,
      type,
      pathHash,
      pathPreview: pathDs[0] ? pathDs[0].slice(0, 50) : '(no paths)',
      pathCount: pathDs.length,
      innerContent,
      svgBlock,
    };

    allInlineSvgs.push(entry);

    if (!uniquePaths.has(pathHash)) {
      uniquePaths.set(pathHash, {
        viewBox,
        type,
        pathPreview: entry.pathPreview,
        pathCount: pathDs.length,
        innerContent,
        files: [],
      });
    }
    uniquePaths.get(pathHash).files.push(`${file}:${lineNum}`);
  }
}

// Report
console.log(`\n=== INLINE SVG CATALOG ===\n`);
console.log(`Total inline SVGs found: ${allInlineSvgs.length}`);
console.log(`Unique icons (by path hash): ${uniquePaths.size}`);

const brands = [...uniquePaths.entries()].filter(([, v]) => v.type === 'brand');
const icons = [...uniquePaths.entries()].filter(([, v]) => v.type !== 'brand');

console.log(`  Brand logos: ${brands.length}`);
console.log(`  UI icons: ${icons.length}`);

console.log(`\n--- BRAND LOGOS (for oauth.svg) ---`);
for (const [hash, info] of brands) {
  console.log(`  [${hash}] viewBox="${info.viewBox}" used in ${info.files.length} place(s):`);
  info.files.forEach(f => console.log(`    ${f}`));
}

console.log(`\n--- UI ICONS (for icons.svg) ---`);
for (const [hash, info] of icons) {
  console.log(`  [${hash}] viewBox="${info.viewBox}" type=${info.type} paths=${info.pathCount} used=${info.files.length}`);
  console.log(`    path: ${info.pathPreview}...`);
  info.files.forEach(f => console.log(`    ${f}`));
}

// Write manifest for the next script to consume
const manifest = {
  brands: brands.map(([hash, info]) => ({ hash, ...info })),
  icons: icons.map(([hash, info]) => ({ hash, ...info })),
};
writeFileSync('scripts/inline-svg-manifest.json', JSON.stringify(manifest, null, 2));
console.log(`\nWrote manifest to scripts/inline-svg-manifest.json`);
