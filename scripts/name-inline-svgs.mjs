#!/usr/bin/env node
/**
 * name-inline-svgs.mjs
 *
 * Enriches the inline SVG manifest with:
 *   - Matches against existing sprite sheet icons
 *   - Auto-generated kebab-case names from file context
 *   - Skip flags for spinners and large illustrations
 */

import { readFileSync, writeFileSync } from 'fs';
import { createHash } from 'crypto';
import { basename } from 'path';

const MANIFEST = 'scripts/inline-svg-manifest.json';
const SPRITE = 'app/static/sprites/icons.svg';
const OUTPUT = 'scripts/inline-svg-manifest-named.json';

// ─── Build sprite path index ────────────────────────────────────────

function normalizePath(d) {
  return d.replace(/\s+/g, ' ').trim().toLowerCase();
}

function hashNormalized(paths) {
  const normalized = paths.map(normalizePath).join('|');
  return createHash('md5').update(normalized).digest('hex').slice(0, 12);
}

const spriteContent = readFileSync(SPRITE, 'utf-8');
const spriteIndex = new Map(); // normalizedHash -> symbolId

const symbolRegex = /<symbol\s+id="([^"]+)"[^>]*>([\s\S]*?)<\/symbol>/g;
let sm;
while ((sm = symbolRegex.exec(spriteContent)) !== null) {
  const id = sm[1];
  const inner = sm[2];
  const pathDs = [];
  const dRegex = /d="([^"]+)"/g;
  let pm;
  while ((pm = dRegex.exec(inner)) !== null) pathDs.push(pm[1]);
  if (pathDs.length > 0) {
    const hash = hashNormalized(pathDs);
    spriteIndex.set(hash, id);
  }
}

console.log(`Sprite index: ${spriteIndex.size} icons`);

// ─── Well-known icon names by path snippet ──────────────────────────
// Maps first ~40 chars of path data to a meaningful name
const KNOWN_ICONS = {
  'm16.862 4.487 1.687-1.688': 'pencil-edit',
  'M16.862 4.487l1.687-1.688': 'pencil-edit',
  'm14.74 9-.346 9m-4.788': 'trash-outline',
  'M6.28 5.22a.75.75 0 00-1.06 1.06L8.94': 'xmark-fill-20',
  'M6.28 5.22a.75.75 0 0 0-1.06 1.06L8.94': 'xmark-fill-20',
  'M15.75 19.5 8.25 12l7.5-7.5': 'chevron-left-24',
  'm8.25 4.5 7.5 7.5-7.5 7.5': 'chevron-right-24',
  'M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5': 'clipboard-import',
  'M16.704 4.153a.75.75 0 01.143 1.052l-8': 'check-fill-20',
  'M16.704 4.153a.75.75 0 0 1 .143 1.052': 'check-fill-20',
  'M17 10a.75.75 0 01-.75.75H5.612': 'arrow-left-fill-20',
  'M17 10a.75.75 0 0 1-.75.75H5.612': 'arrow-left-fill-20',
  'M10.75 4.75a.75.75 0 00-1.5 0v4.5h-4.5': 'plus-fill-20',
  'M10.75 4.75a.75.75 0 0 0-1.5 0v4.5h-4.5': 'plus-fill-20',
  'M8 12h.01M12 12h.01M16 12h.01M21 12c0': 'chat-bubble-dots',
  'M3.98 8.223A10.477': 'eye-slash-outline',
  'M2.036 12.322a1.012 1.012': 'eye-outline',
  'M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75': 'lock-open',
  'M6.115 5.19l.319 1.913': 'rocket',
  'M8.75 3.75a.75.75 0 0 0-1.5 0v3.5h-3.5': 'plus-fill-16',
  'M15.666 3.888A2.25 2.25 0 0013.5 2.25': 'clipboard-doc',
  'M15.666 3.888A2.25 2.25 0 0 0 13.5 2.25': 'clipboard-doc',
  'm11.25 11.25.041-.02a.75.75 0 0 1 1.063': 'info-circle-outline',
  'M11.25 11.25l.041-.02a.75.75 0 011.063': 'info-circle-outline',
  'M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28': 'thumbs-up',
  'M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72': 'thumbs-down',
  'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z': 'play-circle',
  'M16.023 9.348h4.992v-.001': 'refresh-arrows',
  'M3.375 3C2.339 3 1.5 3.84': 'archive-box-fill',
  'M2 3a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1': 'database-fill-16',
  'M4.22 11.78a.75.75 0 0 1 0-1.06L9.44': 'arrow-up-right-fill-16',
  'M4.5 12.75l6 6 9-13.5': 'check-outline',
  'm4.5 12.75 6 6 9-13.5': 'check-outline',
  'M8.75 2.75a.75.75 0 0 0-1.5 0v5.69': 'download-fill-16',
  'M4.22 6.22a.75.75 0 0 1 1.06 0L8 8.94': 'chevron-down-fill-16',
  'M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29': 'github-fill-16',
  'M8.34 1.804A1 1 0 019.32 1h1.36': 'gear-fill-20',
  'M8.34 1.804A1 1 0 0 1 9.32 1h1.36': 'gear-fill-20',
  'M2 4.25A2.25 2.25 0 0 1 4.25 2h7.5': 'monitor-fill-16',
  'M1 9.5A3.5 3.5 0 0 0 4.5 13H12': 'cloud-fill-16',
  'M12 6.75a5.25 5.25 0 0 1 6.775-5.025': 'wrench-fill-24',
  'M7.557 2.066A.5.5 0 0 1 8 2.75v10.5': 'audio-fill-16',
  'M8 2C4.262 2 1 4.57 1 8c0 1.86': 'speech-bubble-fill',
  'M15 8A7 7 0 1 1 1 8a7 7 0 0 1 14': 'info-fill-16',
  'M18 10a8 8 0 11-16 0 8 8 0 0116 0': 'help-circle-fill-20',
  'M4.5 3.75a3 3 0 0 0-3 3v10.5': 'image-fill-24',
  'M2 2.75A.75.75 0 0 1 2.75 2C8.963': 'pipeline-fill-16',
  'M8.914 6.025a.75.75 0 0 1 1.06 0': 'link-fill-16',
  'M8 14a.75.75 0 0 1-.75-.75V4.56L4.03': 'send-up-fill-16',
  'M10 3a.75.75 0 01.75.75v10.638': 'arrow-down-fill-20',
  'M10 3a.75.75 0 0 1 .75.75v10.638': 'arrow-down-fill-20',
  'M9.401 3.003c1.155-2 4.043-2 5.197': 'warning-triangle-fill',
  'M7 4a3 3 0 016 0v6a3 3 0 11-6 0V4': 'mic-fill-20',
  'M7 4a3 3 0 0 1 6 0v6a3 3 0 1 1-6 0V4': 'mic-fill-20',
  'M2.25 12c0-5.385 4.365-9.75 9.75-9.75': 'stop-circle-fill',
  'M6.75 12a.75.75 0 1 1-1.5 0': 'dots-horizontal-outline',
  'M13.19 8.688a4.5 4.5 0 0 1 1.242': 'link-chain-outline',
  'M18 18.72a9.094': 'users-group-outline',
  'M7.487 2.89a.75.75 0 1 0-1.474': 'hashtag-fill-16',
  'M2 8a1.5 1.5 0 1 1 3 0': 'dots-fill-16',
  'M9.594 3.94c.09-.542.56-.94': 'cog-outline-24',
  'M15.75 7.5a1.5 1.5 0 1 1 .412': 'share-nodes-outline',
  'M15.75 4.5a3 3 0 1 1 .825 2.066': 'share-nodes-fill',
  'M3 16.5v2.25A2.25 2.25 0 0 0': 'download-outline-24',
  'M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12': 'menu-partial',
  'M10 3v4a1 1 0 0 1-1 1H5m4 8h6': 'document-text',
  'M13.5 16.875h3.375m0 0h3.375': 'squares-plus',
  'M17.593 3.322c1.1.128 1.907 1.077': 'bookmark-pin',
  'M7.217 10.907a2.25 2.25': 'share-outline',
  'M21.75 6.75v10.5a2.25 2.25 0 0 1-2.25': 'envelope-outline',
  'M2.25 12.75V12A2.25 2.25 0 0 1 4.5 9.75': 'folder-arrow',
  'M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0': 'clock-outline',
  'M19.5 12h-15': 'minus-24',
  'M12 6v12m6-6H6': 'plus-24',
  'm2.695 14.762-1.262 3.155': 'pencil-fill-20',
  'M11.986 3H12a2 2 0 0 1 2 2v6': 'clipboard-copy-16',
  'm19.5 8.25-7.5 7.5-7.5-7.5': 'chevron-down-24',
  'M5.28 4.22a.75.75 0 0 0-1.06 1.06L6.94 8': 'xmark-fill-16',
  'M15.312 11.424a5.5 5.5 0': 'refresh-fill-20',
  'M6.827 6.175A2.31 2.31': 'phone-call-outline',
  'M8 1a7 7 0 1 0 0 14A7 7 0 0 0 8 1Zm0 2.5': 'oidc-fill-16',
  'M2.5 3A1.5 1.5 0 0 0 1 4.5v.793': 'mail-fill-16',
  'M12,1A11,11,0,1,0,23,12': 'spinner-ring',
  'M7.25 10.25a.75.75 0 0 0 1.5 0V4.56': 'upload-fill-16',
  'M5 3.25V4H2.75a.75.75': 'trash-fill-16',
  'M7 1a.75.75 0 0 1 .75.75V6h-1.5': 'power-plug-fill-16',
  'M6.955 1.45A.5.5 0 0 1 7.452 1h1.096': 'settings-gear-fill-16',
  'M8 1a3.5 3.5 0 0 0-3.5 3.5V7A1.5': 'shield-lock-fill-16',
  'M8 0a8 8 0 1 0 0 16A8 8 0 0 0 8 0ZM4.5': 'circle-target-fill-16',
  'M10 1c3.866 0 7 1.79 7 4s-3.134': 'database-fill-20',
  'M11.625 16.5a1.875 1.875 0 1 0 0-3.75': 'search-doc-fill-24',
  'M2 4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v8': 'code-fill-16',
  'M11.644 1.59a.75.75 0 0 1 .712 0l9.75': 'pyramid-fill-24',
  'M8 7c3.314 0 6-1.343 6-3s-2.686': 'data-stack-fill-16',
  'M19.114 5.636a9 9 0 010 12.728': 'volume-outline',
  'm2.25 15.75 5.159-5.159': 'photo-outline',
  'M10 9a3 3 0 100-6 3 3 0 000 6z': 'users-fill-20',
  'M7 8a3 3 0 100-6 3 3 0 000 6z': 'user-group-fill-20',
  'M8.75 1A2.75 2.75 0 006 3.75': 'bell-fill-20',
  'M10.75 2.75a.75.75 0 0 0-1.5 0v8.614': 'download-fill-20',
  'M5.625 1.5c-1.036 0-1.875.84': 'file-doc-fill-24',
  'M3.28 2.22a.75.75 0 0 0-1.06 1.06l10.5': 'eye-slash-fill-16',
  'M8 9.5a1.5 1.5 0 1 0 0-3': 'eye-fill-16',
  'M12.416 3.376a.75.75 0 0 1 .208': 'check-fill-16',
  'M6 18 17.94 6M18 18 6.06 6': 'xmark-mixed-24',
  'M8.5 4.5a2.5 2.5 0 1 1-5 0': 'users-group-fill-16',
  'M8 8a2.5 2.5 0 1 0 0-5': 'user-fill-16',
  'M9 8.25H7.5a2.25 2.25 0 0 0-2.25 2.25': 'copy-outline',
  'M17.25 9.75 19.5 12m0 0 2.25 2.25': 'fork-outline',
  'M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11': 'search-fill-20',
  'm5 12 4.7 4.5 9.3-9': 'checkbox-check',
  'M5 12h14': 'checkbox-minus',
  'M15 12H9m12 0a9 9 0 1 1-18 0': 'minus-circle-outline',
  'M12 0C5.37 0 0 5.37 0 12c0 5.31': 'github-fill-24',
  'M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6': 'key-outline',
  'M4 2a1.5 1.5 0 0 0-1.5 1.5v9A1.5 1.5': 'clipboard-import',
  'M5.25 2A2.25 2.25 0 0 0 3 4.25v9': 'leaderboard-fill-16',
};

// ─── Load manifest ──────────────────────────────────────────────────

const manifest = JSON.parse(readFileSync(MANIFEST, 'utf-8'));

// ─── Process each icon ──────────────────────────────────────────────

const named = { brands: [], icons: [], skipped: [] };

// Skip criteria
const SKIP_VIEWBOXES = new Set(['0 0 87.3 78', '0 0 32 32', '0 0 495 495', '0 0 495 390']);

function shouldSkip(icon) {
  if (SKIP_VIEWBOXES.has(icon.viewBox)) return 'large-viewbox-illustration';
  if (icon.innerContent.includes('<style') || icon.innerContent.includes('animation')) return 'animated-spinner';
  if (icon.innerContent.includes('@keyframes')) return 'animated-spinner';
  return null;
}

function deriveNameFromContext(icon) {
  // Try known icons first
  const preview = icon.pathPreview || '';
  for (const [prefix, name] of Object.entries(KNOWN_ICONS)) {
    if (preview.startsWith(prefix)) return name;
  }

  // Fallback: derive from first file's component name + line context
  const firstFile = icon.files[0] || '';
  const parts = firstFile.split('/');
  const component = parts[parts.length - 1]?.split('.')[0]?.split(':')[0] || 'unknown';
  return `${component.toLowerCase()}-icon-${icon.hash.slice(0, 6)}`;
}

// Process brands
for (const icon of manifest.brands) {
  const skipReason = shouldSkip(icon);
  if (skipReason) {
    named.skipped.push({ ...icon, skipReason });
    continue;
  }

  // Assign brand names based on viewBox
  let name = 'brand-unknown';
  if (icon.viewBox === '0 0 48 48') name = 'google';
  else if (icon.viewBox === '0 0 21 21') name = 'microsoft';
  else if (icon.viewBox === '0 0 24 24') name = 'github-oauth';

  named.brands.push({ ...icon, name, spriteMatch: null });
}

// Process UI icons
let matched = 0;
let newCount = 0;
let skipped = 0;

for (const icon of manifest.icons) {
  const skipReason = shouldSkip(icon);
  if (skipReason) {
    named.skipped.push({ ...icon, skipReason });
    skipped++;
    continue;
  }

  // Try to match against existing sprite
  const pathDs = [];
  const dRegex = /d="([^"]+)"/g;
  let pm;
  while ((pm = dRegex.exec(icon.innerContent)) !== null) pathDs.push(pm[1]);

  let spriteMatch = null;
  if (pathDs.length > 0) {
    const hash = hashNormalized(pathDs);
    if (spriteIndex.has(hash)) {
      spriteMatch = spriteIndex.get(hash);
    }
  }

  const name = spriteMatch || deriveNameFromContext(icon);

  if (spriteMatch) matched++;
  else newCount++;

  named.icons.push({ ...icon, name, spriteMatch });
}

writeFileSync(OUTPUT, JSON.stringify(named, null, 2));

console.log(`\n=== NAMING RESULTS ===`);
console.log(`Matched existing sprite: ${matched}`);
console.log(`New icons to add: ${newCount}`);
console.log(`Skipped (spinners/illustrations): ${skipped}`);
console.log(`Brand logos: ${named.brands.length}`);
console.log(`\nWrote ${OUTPUT}`);

// Print names for review
console.log(`\n--- NEW ICON NAMES (review these) ---`);
const newIcons = named.icons.filter(i => !i.spriteMatch);
for (const icon of newIcons) {
  console.log(`  ${icon.name} (${icon.viewBox}, ${icon.type}, ${icon.files.length}x)`);
}

console.log(`\n--- MATCHED EXISTING SPRITE ---`);
const matchedIcons = named.icons.filter(i => i.spriteMatch);
for (const icon of matchedIcons) {
  console.log(`  → ${icon.spriteMatch} (${icon.files.length}x)`);
}
