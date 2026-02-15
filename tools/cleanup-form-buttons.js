#!/usr/bin/env node

/**
 * Form Button Cleanup Tool
 * 
 * This tool removes redundant type="button" attributes from buttons inside forms
 * that use on:submit|preventDefault pattern.
 * 
 * The key insight: when a form uses on:submit|preventDefault, the default submit
 * behavior is already prevented, so type="button" on buttons is redundant.
 * 
 * Usage:
 *   node tools/cleanup-form-buttons.js --dry-run    # Preview changes
 *   node tools/cleanup-form-buttons.js              # Apply changes
 *   node tools/cleanup-form-buttons.js --path app/src/lib/components  # Specific path
 *   node tools/cleanup-form-buttons.js --verbose    # Show all files processed
 */

const fs = require('fs');
const path = require('path');

// Configuration
const config = {
  dryRun: process.argv.includes('--dry-run'),
  verbose: process.argv.includes('--verbose'),
  targetPath: process.argv.includes('--path') 
    ? process.argv[process.argv.indexOf('--path') + 1]
    : 'app/src',
  excludePatterns: [
    '/routes/auth/', // Exclude auth forms - may have different patterns
    '/node_modules/',
    '/.git/'
  ],
  backupDir: '.cleanup-backups'
};

// Stats tracking
const stats = {
  filesScanned: 0,
  filesModified: 0,
  buttonsFixed: 0,
  errors: [],
  details: []
};

/**
 * Find all Svelte files in directory
 */
function findSvelteFiles(dir) {
  let results = [];
  
  try {
    const files = fs.readdirSync(dir);
    
    for (const file of files) {
      const filePath = path.join(dir, file);
      
      // Check if should exclude
      if (config.excludePatterns.some(pattern => filePath.includes(pattern))) {
        continue;
      }
      
      const stat = fs.statSync(filePath);
      
      if (stat.isDirectory()) {
        results = results.concat(findSvelteFiles(filePath));
      } else if (file.endsWith('.svelte')) {
        results.push(filePath);
      }
    }
  } catch (err) {
    console.error(`Error scanning directory ${dir}:`, err.message);
  }
  
  return results;
}

/**
 * Check if a form tag has preventDefault
 * Handles multi-line form tags
 */
function formHasPreventDefault(formTag) {
  return /on:submit\|preventDefault/.test(formTag) || 
         /on:submit\s*=\s*\{[^}]*\.preventDefault\s*\(\)/.test(formTag) ||
         /on:submit\s*=\s*\{[^}]*preventDefault/.test(formTag);
}

/**
 * Extract the complete form opening tag (may span multiple lines)
 */
function extractFormOpenTag(content, startIdx) {
  let depth = 0;
  let inString = false;
  let stringChar = '';
  let tag = '';
  
  for (let i = startIdx; i < content.length; i++) {
    const char = content[i];
    tag += char;
    
    // Handle strings
    if ((char === '"' || char === "'" || char === '`') && content[i-1] !== '\\') {
      if (!inString) {
        inString = true;
        stringChar = char;
      } else if (char === stringChar) {
        inString = false;
      }
    }
    
    if (!inString) {
      if (char === '{') depth++;
      if (char === '}') depth--;
      if (char === '>' && depth === 0) {
        return { tag, endIdx: i };
      }
    }
  }
  
  return null;
}

/**
 * Find matching closing form tag
 */
function findFormEnd(content, startIdx) {
  let depth = 1;
  let i = startIdx;
  
  while (i < content.length && depth > 0) {
    if (content.substring(i, i + 6) === '<form ') {
      depth++;
      i += 6;
    } else if (content.substring(i, i + 7) === '</form>') {
      depth--;
      if (depth === 0) {
        return i + 7;
      }
      i += 7;
    } else {
      i++;
    }
  }
  
  return -1;
}

/**
 * Remove type="button" from a button tag (handles multi-line)
 * Returns { modified, changed }
 */
function cleanButtonTag(buttonContent) {
  // Match type="button" or type='button' with preceding whitespace
  // Handle both same-line and newline + tabs/spaces
  const patterns = [
    /(\s+)type="button"/g,
    /(\s+)type='button'/g,
    /\n\s*type="button"/g,
    /\n\s*type='button'/g
  ];
  
  let modified = buttonContent;
  let changed = false;
  
  for (const pattern of patterns) {
    if (pattern.test(modified)) {
      modified = modified.replace(pattern, '');
      changed = true;
    }
  }
  
  return { modified, changed };
}

/**
 * Process buttons inside a form block
 */
function processFormContent(formContent) {
  let modified = formContent;
  let changeCount = 0;
  
  // Find all button tags (including multi-line)
  // We need to find <button ... > and check for type="button"
  const buttonRegex = /<button\s[^>]*type=["']button["'][^>]*>/gs;
  
  let match;
  const replacements = [];
  
  // Reset regex
  buttonRegex.lastIndex = 0;
  
  while ((match = buttonRegex.exec(formContent)) !== null) {
    const original = match[0];
    const { modified: cleaned, changed } = cleanButtonTag(original);
    
    if (changed) {
      replacements.push({ original, cleaned });
      changeCount++;
    }
  }
  
  // Apply replacements
  for (const { original, cleaned } of replacements) {
    modified = modified.replace(original, cleaned);
  }
  
  return { modified, changeCount };
}

/**
 * Process a single file
 */
function processFile(filePath) {
  stats.filesScanned++;
  
  try {
    let content = fs.readFileSync(filePath, 'utf8');
    const originalContent = content;
    let totalChanges = 0;
    
    // Find all form tags
    const formStartRegex = /<form\s/g;
    let formMatch;
    
    // Collect all forms with preventDefault
    const formsToProcess = [];
    
    while ((formMatch = formStartRegex.exec(content)) !== null) {
      const formStartIdx = formMatch.index;
      const formTagInfo = extractFormOpenTag(content, formStartIdx);
      
      if (!formTagInfo) continue;
      
      if (formHasPreventDefault(formTagInfo.tag)) {
        const formEndIdx = findFormEnd(content, formTagInfo.endIdx + 1);
        
        if (formEndIdx !== -1) {
          const formContent = content.substring(formStartIdx, formEndIdx);
          formsToProcess.push({
            startIdx: formStartIdx,
            endIdx: formEndIdx,
            content: formContent
          });
        }
      }
    }
    
    if (formsToProcess.length === 0) {
      if (config.verbose) {
        console.log(`  ⊘ ${filePath} - No preventDefault forms`);
      }
      return;
    }
    
    // Process forms in reverse order to maintain indices
    for (let i = formsToProcess.length - 1; i >= 0; i--) {
      const form = formsToProcess[i];
      const { modified, changeCount } = processFormContent(form.content);
      
      if (changeCount > 0) {
        content = content.substring(0, form.startIdx) + modified + content.substring(form.endIdx);
        totalChanges += changeCount;
      }
    }
    
    if (totalChanges > 0) {
      console.log(`  ✓ ${filePath} - ${totalChanges} button(s) cleaned`);
      stats.filesModified++;
      stats.buttonsFixed += totalChanges;
      stats.details.push({ file: filePath, count: totalChanges });
      
      if (!config.dryRun) {
        // Create backup
        const backupPath = path.join(config.backupDir, filePath);
        const backupDir = path.dirname(backupPath);
        
        if (!fs.existsSync(backupDir)) {
          fs.mkdirSync(backupDir, { recursive: true });
        }
        
        fs.writeFileSync(backupPath, originalContent);
        
        // Write modified content
        fs.writeFileSync(filePath, content);
      }
    } else if (config.verbose) {
      console.log(`  − ${filePath} - Has preventDefault forms but no type="button"`);
    }
    
  } catch (err) {
    console.error(`  ✗ Error processing ${filePath}:`, err.message);
    stats.errors.push({ file: filePath, error: err.message });
  }
}

/**
 * Main execution
 */
function main() {
  console.log('🔍 Form Button Cleanup Tool\n');
  console.log(`Mode: ${config.dryRun ? 'DRY RUN (no changes)' : 'APPLY CHANGES'}`);
  console.log(`Path: ${config.targetPath}`);
  console.log(`Excluded: ${config.excludePatterns.join(', ')}\n`);
  
  // Find all Svelte files
  console.log('Scanning for Svelte files...\n');
  const files = findSvelteFiles(config.targetPath);
  console.log(`Found ${files.length} Svelte files\n`);
  
  // Process each file
  console.log('Processing files...\n');
  files.forEach(processFile);
  
  // Print summary
  console.log('\n' + '='.repeat(60));
  console.log('SUMMARY');
  console.log('='.repeat(60));
  console.log(`Files scanned:  ${stats.filesScanned}`);
  console.log(`Files modified: ${stats.filesModified}`);
  console.log(`Buttons fixed:  ${stats.buttonsFixed}`);
  console.log(`Errors:         ${stats.errors.length}`);
  
  if (stats.errors.length > 0) {
    console.log('\nErrors:');
    stats.errors.forEach(({ file, error }) => {
      console.log(`  - ${file}: ${error}`);
    });
  }
  
  if (config.dryRun && stats.buttonsFixed > 0) {
    console.log('\n⚠️  This was a DRY RUN - no files were modified');
    console.log('Run without --dry-run to apply changes');
  } else if (stats.buttonsFixed > 0) {
    console.log(`\n✓ Backups saved to: ${config.backupDir}/`);
    console.log('✓ Changes applied successfully');
  } else {
    console.log('\n✓ No changes needed');
  }
}

// Run the tool
main();
