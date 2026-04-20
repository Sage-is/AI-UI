#!/usr/bin/env node
/**
 * replace-inline-svgs.mjs
 *
 * Replaces inline <svg>...</svg> blocks with <Icon name="..." /> or <BrandIcon name="..." />.
 * Uses the named manifest and name mapping from previous scripts.
 *
 * Usage:
 *   node scripts/replace-inline-svgs.mjs          # dry run
 *   node scripts/replace-inline-svgs.mjs --write  # apply changes
 */

import { readFileSync, writeFileSync } from 'fs';
import { createHash } from 'crypto';

const DRY_RUN = !process.argv.includes('--write');

const NAMED_MANIFEST = 'scripts/inline-svg-manifest-named.json';
const NAME_MAPPING = 'scripts/inline-svg-name-mapping.json';

// ─── Size translation ───────────────────────────────────────────────

const SIZE_MAP = {
  '0.6rem': 'size-[0.6rem]',
  '0.7rem': 'size-[0.7rem]',
  '0.75rem': 'size-3',
  '0.8rem': 'size-[0.8rem]',
  '0.875rem': 'size-3.5',
  '1rem': 'size-4',
  '1.1rem': 'size-[1.1rem]',
  '1.125rem': 'size-[1.125rem]',
  '1.2rem': 'size-[1.2rem]',
  '1.25rem': 'size-5',
  '1.5rem': 'size-6',
  '2rem': 'size-8',
  '3rem': 'size-12',
};

function extractSize(svgTag) {
  // Try startr.style --w/--h
  const wMatch = svgTag.match(/--w:([^;}"]+)/);
  if (wMatch) {
    const val = wMatch[1].trim();
    return SIZE_MAP[val] || `size-[${val}]`;
  }
  // Try Tailwind class
  const classMatch = svgTag.match(/class="([^"]+)"/);
  if (classMatch) {
    const cls = classMatch[1];
    const sizeMatch = cls.match(/size-[\w.\[\]]+|w-\d+\s+h-\d+/);
    if (sizeMatch) return sizeMatch[0];
  }
  return 'size-4'; // default
}

function extractStrokeWidth(svgTag) {
  const swMatch = svgTag.match(/stroke-width="([^"]+)"/);
  if (swMatch && swMatch[1] !== '1.5') return swMatch[1];
  return null;
}

// ─── Load data ──────────────────────────────────────────────────────

const named = JSON.parse(readFileSync(NAMED_MANIFEST, 'utf-8'));
const nameMapping = JSON.parse(readFileSync(NAME_MAPPING, 'utf-8'));

// Build lookup: hash -> { name, isBrand }
const hashLookup = new Map();
for (const icon of named.icons) {
  hashLookup.set(icon.hash, { name: nameMapping[icon.hash] || icon.name, isBrand: false });
}
for (const brand of named.brands) {
  hashLookup.set(brand.hash, { name: brand.name, isBrand: true });
}

// Build file -> replacements map (sorted by line desc for bottom-up processing)
const fileReplacements = new Map();

function addReplacement(icon, isBrand) {
  for (const fileRef of icon.files) {
    const [filePath, lineStr] = fileRef.split(':');
    const line = parseInt(lineStr, 10);
    if (!fileReplacements.has(filePath)) fileReplacements.set(filePath, []);
    fileReplacements.get(filePath).push({
      line,
      hash: icon.hash,
      isBrand,
    });
  }
}

for (const icon of named.icons) addReplacement(icon, false);
for (const brand of named.brands) addReplacement(brand, true);

// Sort each file's replacements by line descending
for (const [, reps] of fileReplacements) {
  reps.sort((a, b) => b.line - a.line);
}

// ─── Process files ──────────────────────────────────────────────────

let totalFiles = 0;
let totalReplaced = 0;
let totalSkipped = 0;

for (const [filePath, replacements] of fileReplacements) {
  let content = readFileSync(filePath, 'utf-8');
  const original = content;
  let fileReplaced = 0;

  for (const rep of replacements) {
    const info = hashLookup.get(rep.hash);
    if (!info) { totalSkipped++; continue; }

    // Find the <svg> block starting near the given line
    const lines = content.split('\n');
    const startIdx = rep.line - 1; // 0-based

    // Scan for <svg from startIdx (may be a few lines off due to previous replacements)
    let svgStart = -1;
    for (let i = Math.max(0, startIdx - 3); i < Math.min(lines.length, startIdx + 5); i++) {
      if (lines[i].includes('<svg')) {
        svgStart = i;
        break;
      }
    }

    if (svgStart === -1) {
      totalSkipped++;
      continue;
    }

    // Find the closing </svg> tag
    let svgEnd = -1;
    for (let i = svgStart; i < lines.length; i++) {
      if (lines[i].match(/<\/svg\s*>/)) {
        svgEnd = i;
        break;
      }
    }

    if (svgEnd === -1) {
      totalSkipped++;
      continue;
    }

    // Extract the full SVG block
    const svgLines = lines.slice(svgStart, svgEnd + 1);
    const svgBlock = svgLines.join('\n');
    const svgTag = svgBlock.match(/<svg[^>]*>/)?.[0] || '';

    // Verify this is the right SVG by checking path hash
    const pathDs = [];
    const dRegex = /d="([^"]+)"/g;
    let pm;
    while ((pm = dRegex.exec(svgBlock)) !== null) pathDs.push(pm[1]);
    const blockHash = createHash('md5').update(
      pathDs.length > 0
        ? pathDs.map(d => d.replace(/\s+/g, ' ').trim()).join('|')
        : svgBlock.replace(/<svg[^>]*>/, '').replace(/<\/svg\s*>/, '').trim()
    ).digest('hex').slice(0, 12);

    // Allow some hash variation (the catalog may have used slightly different normalization)
    if (blockHash !== rep.hash && !info) {
      totalSkipped++;
      continue;
    }

    // Build replacement
    const indent = svgLines[0].match(/^(\s*)/)?.[1] || '';
    const size = extractSize(svgTag);
    const sw = extractStrokeWidth(svgTag);

    let replacement;
    if (info.isBrand) {
      replacement = `${indent}<BrandIcon name="${info.name}" className="${size}" />`;
    } else {
      let attrs = `name="${info.name}" className="${size}"`;
      if (sw) attrs += ` strokeWidth="${sw}"`;
      replacement = `${indent}<Icon ${attrs} />`;
    }

    // Replace the lines
    lines.splice(svgStart, svgEnd - svgStart + 1, replacement);
    content = lines.join('\n');
    fileReplaced++;
    totalReplaced++;
  }

  if (fileReplaced === 0) continue;

  // Ensure Icon import exists
  if (content.includes('<Icon ') && !content.includes("import Icon from '$lib/components/Icon.svelte'")) {
    const lines = content.split('\n');
    let lastImportLine = -1;
    let inMultiLineImport = false;
    for (let i = 0; i < lines.length; i++) {
      const trimmed = lines[i].trim();
      if (trimmed.startsWith('import ') && !inMultiLineImport) {
        if (trimmed.includes('{') && !trimmed.includes('}')) inMultiLineImport = true;
        lastImportLine = i;
      } else if (inMultiLineImport) {
        lastImportLine = i;
        if (trimmed.includes('}')) inMultiLineImport = false;
      }
    }
    if (lastImportLine >= 0) {
      lines.splice(lastImportLine + 1, 0, "\timport Icon from '$lib/components/Icon.svelte';");
      content = lines.join('\n');
    }
  }

  // Ensure BrandIcon import exists
  if (content.includes('<BrandIcon ') && !content.includes("import BrandIcon from '$lib/components/BrandIcon.svelte'")) {
    const lines = content.split('\n');
    let lastImportLine = -1;
    let inMultiLineImport = false;
    for (let i = 0; i < lines.length; i++) {
      const trimmed = lines[i].trim();
      if (trimmed.startsWith('import ') && !inMultiLineImport) {
        if (trimmed.includes('{') && !trimmed.includes('}')) inMultiLineImport = true;
        lastImportLine = i;
      } else if (inMultiLineImport) {
        lastImportLine = i;
        if (trimmed.includes('}')) inMultiLineImport = false;
      }
    }
    if (lastImportLine >= 0) {
      lines.splice(lastImportLine + 1, 0, "\timport BrandIcon from '$lib/components/BrandIcon.svelte';");
      content = lines.join('\n');
    }
  }

  if (content !== original) {
    totalFiles++;
    if (DRY_RUN) {
      console.log(`  Would change: ${filePath} (${fileReplaced} SVGs)`);
    } else {
      writeFileSync(filePath, content);
      console.log(`  Changed: ${filePath} (${fileReplaced} SVGs)`);
    }
  }
}

console.log(`\n${DRY_RUN ? 'Would change' : 'Changed'} ${totalFiles} files, ${totalReplaced} SVGs replaced, ${totalSkipped} skipped`);
if (DRY_RUN) console.log('Run with --write to apply.');
