import fs from 'fs';
import path from 'path';
import { parseElements, replaceTag } from './parser/svelte-parser.js';
import { processContent } from './transformer/partial-handler.js';
import { setCustomClassMap, resetCustomClassMap } from './transformer/class-converter.js';
import { generateDiff } from './reporter/diff-reporter.js';
import { SummaryReporter } from './reporter/summary-reporter.js';
import { ManualReviewCollector } from './reporter/manual-review.js';

/**
 * Parse command-line arguments.
 */
export function parseArgs(argv) {
  const args = {
    dryRun: false,
    diff: false,
    report: false,
    verbose: false,
    backup: true,
    basePath: process.cwd(),
    exclude: [],
    glob: null,
    classMapPath: null,
    help: false,
    files: [],
  };

  const rawArgs = argv.slice(2);
  let i = 0;

  while (i < rawArgs.length) {
    const arg = rawArgs[i];

    switch (arg) {
      case '--dry-run':
      case '-n':
        args.dryRun = true;
        break;
      case '--diff':
      case '-d':
        args.diff = true;
        break;
      case '--report':
      case '-r':
        args.report = true;
        break;
      case '--verbose':
      case '-v':
        args.verbose = true;
        break;
      case '--backup':
        args.backup = true;
        break;
      case '--no-backup':
        args.backup = false;
        break;
      case '--path':
        i++;
        args.basePath = rawArgs[i] || args.basePath;
        break;
      case '--exclude':
        i++;
        if (rawArgs[i]) args.exclude.push(rawArgs[i]);
        break;
      case '--class-map':
        i++;
        args.classMapPath = rawArgs[i] || null;
        break;
      case '--help':
      case '-h':
        args.help = true;
        break;
      default:
        if (!arg.startsWith('-')) {
          args.glob = arg;
        }
        break;
    }
    i++;
  }

  return args;
}

/**
 * Show help text.
 */
export function showHelp() {
  console.log(`
tw2startr — Tailwind CSS to startr.style converter

Usage: tw2startr [options] [glob]

Supports Svelte (.svelte) and HTML (.html) files.

Options:
  --dry-run, -n        Preview changes, don't modify files
  --diff, -d           Show unified diff of changes
  --report, -r         Stats: what converts, what doesn't
  --verbose, -v        Detailed processing output
  --backup             Create .backup files (default: true)
  --no-backup          Skip backups
  --path <dir>         Base directory (default: cwd)
  --exclude <pattern>  Exclude glob patterns
  --class-map <file>   JSON class map for project-specific utility classes
  --help, -h           Show help

Examples:
  tw2startr --dry-run "src/**/*.svelte"
  tw2startr --report "src/lib/components/**/*.svelte"
  tw2startr --diff src/lib/components/common/Switch.svelte
  tw2startr --dry-run --diff "app/src/**/*.svelte"
  tw2startr --dry-run "**/*.html"
`);
}

/**
 * Find Svelte files matching a glob pattern.
 * Simple recursive implementation (no external deps).
 */
export function findFiles(dir, pattern, excludes = []) {
  const results = [];

  function walk(currentDir) {
    let entries;
    try {
      entries = fs.readdirSync(currentDir);
    } catch {
      return;
    }

    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry);

      // Check exclusions
      if (excludes.some(ex => fullPath.includes(ex))) continue;
      if (entry === 'node_modules' || entry === '.git' || entry === '.svelte-kit') continue;

      let stat;
      try {
        stat = fs.statSync(fullPath);
      } catch {
        continue;
      }

      if (stat.isDirectory()) {
        walk(fullPath);
      } else if (entry.endsWith('.svelte') || entry.endsWith('.html')) {
        // Simple glob matching: if pattern is provided, check if path matches
        if (!pattern || matchGlob(fullPath, pattern)) {
          results.push(fullPath);
        }
      }
    }
  }

  walk(dir);
  return results.sort();
}

/**
 * Simple glob matching (supports ** and *).
 */
function matchGlob(filePath, pattern) {
  // Convert glob pattern to regex
  let regexStr = pattern
    .replace(/\\/g, '/')
    .replace(/\*\*/g, '<<<GLOBSTAR>>>')
    .replace(/\*/g, '[^/]*')
    .replace(/<<<GLOBSTAR>>>/g, '.*')
    .replace(/\?/g, '.');

  // Make it match the end of the path
  const normalizedPath = filePath.replace(/\\/g, '/');
  const regex = new RegExp(regexStr + '$');
  return regex.test(normalizedPath);
}

function loadClassMap(classMapPath, basePath) {
  if (!classMapPath) return {};

  const resolvedPath = path.isAbsolute(classMapPath)
    ? classMapPath
    : path.resolve(basePath, classMapPath);

  const raw = fs.readFileSync(resolvedPath, 'utf8');
  const parsed = JSON.parse(raw);

  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error(`class map must be a JSON object: ${resolvedPath}`);
  }

  return parsed;
}

/**
 * Main CLI execution.
 */
export async function run(argv) {
  const args = parseArgs(argv);

  if (args.help) {
    showHelp();
    return;
  }

  const mode = args.dryRun ? 'DRY RUN' : 'APPLY';
  console.log(`tw2startr — Tailwind to startr.style converter\n`);
  console.log(`Mode: ${mode}`);
  console.log(`Path: ${args.basePath}`);
  if (args.glob) console.log(`Pattern: ${args.glob}`);
  console.log();

  // Find files
  const files = args.glob
    ? findFiles(args.basePath, args.glob, args.exclude)
    : findFiles(args.basePath, null, args.exclude);

  if (files.length === 0) {
    // If glob was given as a direct file path, try it
    if (args.glob && fs.existsSync(args.glob)) {
      files.push(args.glob);
    } else if (args.glob) {
      // Try relative to basePath
      const resolved = path.resolve(args.basePath, args.glob);
      if (fs.existsSync(resolved) && (resolved.endsWith('.svelte') || resolved.endsWith('.html'))) {
        files.push(resolved);
      }
    }
  }

  console.log(`Found ${files.length} file(s)\n`);

  if (files.length === 0) {
    console.log('No files to process.');
    return;
  }

  // Reset map each run to avoid stale mappings across repeated CLI invocations.
  resetCustomClassMap();
  if (args.classMapPath) {
    try {
      const classMap = loadClassMap(args.classMapPath, args.basePath);
      setCustomClassMap(classMap);
      if (args.verbose) {
        const resolvedPath = path.isAbsolute(args.classMapPath)
          ? args.classMapPath
          : path.resolve(args.basePath, args.classMapPath);
        console.log(`Loaded class map: ${resolvedPath}\n`);
      }
    } catch (error) {
      console.error(`Error loading class map: ${error.message}`);
      process.exit(1);
    }
  }

  const reporter = new SummaryReporter();
  const reviewer = new ManualReviewCollector();

  // Process each file
  for (const filePath of files) {
    try {
      const content = fs.readFileSync(filePath, 'utf8');
      const { newContent, stats } = processContent(content, parseElements, replaceTag);

      reporter.addFile(filePath, stats);

      if (stats.reviews.length > 0) {
        reviewer.addFromReviews(filePath, stats.reviews);
      }

      if (newContent !== content) {
        if (args.diff) {
          const relativePath = path.relative(args.basePath, filePath);
          const diffOutput = generateDiff(relativePath, content, newContent);
          if (diffOutput) {
            console.log(diffOutput);
          }
        }

        if (args.verbose) {
          console.log(`  ✓ ${filePath} — ${stats.classesConverted} class(es) converted, ${stats.classesUnconverted} remaining`);
        }

        if (!args.dryRun) {
          // Create backup
          if (args.backup) {
            const backupPath = filePath + '.backup';
            fs.writeFileSync(backupPath, content);
          }

          // Write modified file
          fs.writeFileSync(filePath, newContent);
        }
      } else if (args.verbose) {
        console.log(`  - ${filePath} — no changes`);
      }
    } catch (error) {
      console.error(`  ✗ Error processing ${filePath}: ${error.message}`);
      reporter.addError(filePath, error);
    }
  }

  // Print reports
  if (args.report || args.verbose) {
    console.log(reporter.getReport());

    const reviewReport = reviewer.getReport();
    if (reviewReport) {
      console.log(reviewReport);
    }
  } else {
    // Always show a brief summary
    console.log(`\nDone: ${reporter.totalClassesConverted} class(es) converted across ${reporter.totalFilesModified} file(s).`);
    if (reporter.totalClassesUnconverted > 0) {
      console.log(`${reporter.totalClassesUnconverted} class(es) could not be converted (use --report for details).`);
    }
  }

  if (args.dryRun) {
    console.log('\nThis was a DRY RUN — no files were modified.');
    console.log('Run without --dry-run to apply changes.');
  }
}
