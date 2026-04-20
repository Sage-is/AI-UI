#!/usr/bin/env node
/**
 * fix-remaining-icon-tags.mjs
 *
 * Finds and replaces any remaining PascalCase icon tags with <Icon name="..." />.
 * Also ensures the Icon import is present and correct.
 */

import { readFileSync, writeFileSync, readdirSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';

const DRY_RUN = !process.argv.includes('--write');
const ICONS_DIR = 'app/src/lib/components/icons';
const SRC_DIR = 'app/src';

const SKIP = new Set([
  'BookOpen', 'CalendarSolid', 'CheckCircle', 'Cog6Solid',
  'DocumentArrowDown', 'DocumentCheck', 'FloppyDisk', 'Lifebuoy', 'QueueList'
]);

function pascalToKebab(str) {
  return str
    .replace(/([a-z0-9])([A-Z])/g, '$1-$2')
    .replace(/([A-Z])([A-Z][a-z])/g, '$1-$2')
    .toLowerCase();
}

// Build icon metadata from original files (or use the generated icons.ts)
const iconMeta = {};
try {
  const files = readdirSync(ICONS_DIR).filter(f => f.endsWith('.svelte'));
  for (const file of files) {
    const name = file.replace('.svelte', '');
    if (SKIP.has(name)) continue;
    const content = readFileSync(join(ICONS_DIR, file), 'utf-8');
    const classMatch = content.match(/export let className\s*=\s*['"]([^'"]+)['"]/);
    const strokeMatch = content.match(/export let strokeWidth\s*=\s*['"]([^'"]+)['"]/);
    iconMeta[name] = {
      kebab: pascalToKebab(name),
      defaultClass: classMatch ? classMatch[1] : 'size-4',
      defaultStroke: strokeMatch ? strokeMatch[1] : null,
      hasStroke: !!strokeMatch,
    };
  }
} catch {
  // Icons dir deleted — build from icons.ts
  const iconsTs = readFileSync('app/src/lib/components/icons.ts', 'utf-8');
  const nameRegex = /(\w+):\s*'([^']+)'/g;
  let m;
  while ((m = nameRegex.exec(iconsTs)) !== null) {
    iconMeta[m[1]] = {
      kebab: m[2],
      defaultClass: 'size-4',
      defaultStroke: '1.5',
      hasStroke: true,
    };
  }
}

console.log(`Loaded ${Object.keys(iconMeta).length} icon definitions`);

// Build a regex that matches any PascalCase icon tag
const iconNames = Object.keys(iconMeta);
const tagPattern = iconNames.join('|');

// Find all svelte files
const allSvelteFiles = execSync(
  `find ${SRC_DIR} -name '*.svelte' -type f`,
  { encoding: 'utf-8' }
).trim().split('\n').filter(Boolean);

let totalChanged = 0;
let totalTags = 0;

for (const filePath of allSvelteFiles) {
  let content = readFileSync(filePath, 'utf-8');
  const original = content;

  // Replace self-closing tags: <IconName ... />
  const selfCloseRegex = new RegExp(
    `<(${tagPattern})(\\s[^>]*?)?\\s*/>`,
    'g'
  );

  content = content.replace(selfCloseRegex, (fullMatch, iconName, attrs) => {
    const info = iconMeta[iconName];
    if (!info) return fullMatch;

    // Make sure this isn't inside a string or comment
    totalTags++;
    attrs = attrs || '';
    let newAttrs = `name="${info.kebab}"`;
    const cleanAttrs = attrs.trim();
    if (cleanAttrs) {
      newAttrs += ' ' + cleanAttrs;
    }
    return `<Icon ${newAttrs} />`;
  });

  // Replace explicit close tags: <IconName ...>...</IconName>
  const explicitCloseRegex = new RegExp(
    `<(${tagPattern})(\\s[^>]*?)?>([\\s\\S]*?)</(${tagPattern})\\s*>`,
    'g'
  );

  content = content.replace(explicitCloseRegex, (fullMatch, iconName, attrs, children, closeName) => {
    if (iconName !== closeName) return fullMatch;
    const info = iconMeta[iconName];
    if (!info) return fullMatch;
    totalTags++;
    attrs = attrs || '';
    let newAttrs = `name="${info.kebab}"`;
    const cleanAttrs = attrs.trim();
    if (cleanAttrs) {
      newAttrs += ' ' + cleanAttrs;
    }
    return `<Icon ${newAttrs} />`;
  });

  // Remove any remaining old icon imports (relative or $lib)
  content = content.replace(/\timport\s+\w+\s+from\s+['"](?:\$lib\/components\/icons|\.\.?\/icons)\/\w+\.svelte['"];?\n?/g, '');

  // Ensure Icon import is present if <Icon is used
  if (content.includes('<Icon ') && !content.includes("import Icon from '$lib/components/Icon.svelte'")) {
    const lines = content.split('\n');
    let lastImportLine = -1;
    let inMultiLineImport = false;
    for (let i = 0; i < lines.length; i++) {
      const trimmed = lines[i].trim();
      if (trimmed.startsWith('import ') && !inMultiLineImport) {
        if (trimmed.includes('{') && !trimmed.includes('}')) {
          inMultiLineImport = true;
        }
        lastImportLine = i;
      } else if (inMultiLineImport) {
        lastImportLine = i;
        if (trimmed.includes('}')) {
          inMultiLineImport = false;
        }
      }
    }
    if (lastImportLine >= 0) {
      lines.splice(lastImportLine + 1, 0, "\timport Icon from '$lib/components/Icon.svelte';");
      content = lines.join('\n');
    }
  }

  if (content !== original) {
    totalChanged++;
    if (DRY_RUN) {
      console.log(`  Would fix: ${filePath}`);
    } else {
      writeFileSync(filePath, content);
      console.log(`  Fixed: ${filePath}`);
    }
  }
}

console.log(`\n${DRY_RUN ? 'Would fix' : 'Fixed'} ${totalChanged} files, ${totalTags} tags replaced`);
if (DRY_RUN) console.log('Run with --write to apply.');
