#!/usr/bin/env node
/**
 * migrate-icon-imports.mjs
 *
 * Rewrites all files that import from $lib/components/icons/ to use
 * the new <Icon name="..." /> component instead.
 *
 * Usage:
 *   node scripts/migrate-icon-imports.mjs          # dry run (shows diff)
 *   node scripts/migrate-icon-imports.mjs --write  # actually write files
 */

import { readFileSync, writeFileSync, readdirSync } from 'fs';
import { join } from 'path';
import { execSync } from 'child_process';

const DRY_RUN = !process.argv.includes('--write');
const SRC_DIR = 'app/src';

// ─── Build icon metadata from the original .svelte files ─────────────

const ICONS_DIR = 'app/src/lib/components/icons';

// Icons we dropped (unused)
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

// Read original defaults from each icon .svelte file
const iconMeta = {};
for (const file of readdirSync(ICONS_DIR).filter(f => f.endsWith('.svelte'))) {
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

// New universal defaults
const NEW_DEFAULT_CLASS = 'size-4';
const NEW_DEFAULT_STROKE = '1.5';

// Tailwind equivalents: 'w-4 h-4' === 'size-4', so treat as same
function classEquivalent(cls) {
  if (cls === 'w-4 h-4' || cls === 'size-4') return 'size-4';
  if (cls === 'w-5 h-5') return 'size-5';
  return cls;
}

// ─── Find all files that import from icons/ ──────────────────────────

// Find files with either $lib or relative icon imports, plus any still using old PascalCase tags
const allFiles = execSync(
  `grep -rl "from '\\$lib/components/icons/\\|from '\\./icons/\\|from '\\.\\./icons/" ${SRC_DIR} --include="*.svelte" --include="*.ts" 2>/dev/null || true`,
  { encoding: 'utf-8' }
).trim().split('\n').filter(Boolean);

console.log(`${DRY_RUN ? 'DRY RUN — ' : ''}Found ${allFiles.length} files to migrate\n`);

let totalChanged = 0;
let totalImports = 0;
let totalTags = 0;

for (const filePath of allFiles) {
  let content = readFileSync(filePath, 'utf-8');
  const original = content;

  // Collect all icon imports in this file ($lib paths AND relative paths)
  const importRegex = /import\s+(\w+)\s+from\s+['"](?:\$lib\/components\/icons|\.\.?\/icons)\/(\w+)\.svelte['"];?\n?/g;
  const localIcons = {}; // localName -> iconMeta entry
  let match;

  while ((match = importRegex.exec(content)) !== null) {
    const localName = match[1];
    const iconName = match[2];
    if (iconMeta[iconName]) {
      localIcons[localName] = { ...iconMeta[iconName], importMatch: match[0] };
      totalImports++;
    }
  }

  if (Object.keys(localIcons).length === 0) continue;

  // Remove all old icon imports
  for (const info of Object.values(localIcons)) {
    content = content.replace(info.importMatch, '');
  }

  // Add the new Icon import (if not already present)
  if (!content.includes("import Icon from '$lib/components/Icon.svelte'")) {
    // Find all import lines and insert after the last one
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

  // Replace tag usages for each icon
  for (const [localName, info] of Object.entries(localIcons)) {
    // Match self-closing: <IconName ... />
    // Match explicit close: <IconName ...></IconName> or <IconName ...>...</IconName>
    const tagRegex = new RegExp(
      `<${localName}(\\s[^>]*?)?\\s*\\/>|<${localName}(\\s[^>]*?)?>([\\s\\S]*?)<\\/${localName}\\s*>`,
      'g'
    );

    content = content.replace(tagRegex, (fullMatch, selfAttrs, openAttrs, children) => {
      totalTags++;
      const attrs = selfAttrs || openAttrs || '';

      let newAttrs = `name="${info.kebab}"`;

      // Check if className is already specified
      const hasClassName = /className\s*[={]/.test(attrs);
      // Check if strokeWidth is already specified
      const hasStrokeWidth = /strokeWidth\s*[={]/.test(attrs);

      // Inject default className if original default differs from new default
      if (!hasClassName && classEquivalent(info.defaultClass) !== classEquivalent(NEW_DEFAULT_CLASS)) {
        newAttrs += ` className="${info.defaultClass}"`;
      }

      // Inject default strokeWidth if original default differs from new default
      if (!hasStrokeWidth && info.hasStroke && info.defaultStroke !== NEW_DEFAULT_STROKE) {
        newAttrs += ` strokeWidth="${info.defaultStroke}"`;
      }

      // Append existing attrs (strip leading whitespace)
      const cleanAttrs = attrs.trim();
      if (cleanAttrs) {
        newAttrs += ' ' + cleanAttrs;
      }

      return `<Icon ${newAttrs} />`;
    });
  }

  // Handle svelte:component patterns
  // Replace: <svelte:component this={X} .../>  where X was an icon
  for (const [localName, info] of Object.entries(localIcons)) {
    // This handles cases like: <svelte:component this={button.icon} />
    // where button.icon was set to the component. We can't auto-migrate
    // the data structure, but we flag it.
    const dynamicRegex = new RegExp(`\\bthis\\s*=\\s*\\{\\s*${localName}\\s*\\}`, 'g');
    if (dynamicRegex.test(content)) {
      console.log(`  MANUAL: ${filePath} uses dynamic component ref to ${localName}`);
    }
  }

  if (content !== original) {
    totalChanged++;
    if (DRY_RUN) {
      console.log(`  Would change: ${filePath} (${Object.keys(localIcons).length} icons)`);
    } else {
      writeFileSync(filePath, content);
      console.log(`  Changed: ${filePath} (${Object.keys(localIcons).length} icons)`);
    }
  }
}

console.log(`\n${DRY_RUN ? 'Would change' : 'Changed'} ${totalChanged} files`);
console.log(`  ${totalImports} import statements replaced`);
console.log(`  ${totalTags} tag usages rewritten`);

if (DRY_RUN) {
  console.log('\nRun with --write to apply changes.');
}
