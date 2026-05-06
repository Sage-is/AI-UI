export {
  convertClass,
  convertClasses,
  parsePrefixes,
  setCustomClassMap,
  resetCustomClassMap,
} from './transformer/class-converter.js';
export { extractClassSegments, getStaticClasses } from './parser/class-extractor.js';
export { parseElements } from './parser/svelte-parser.js';
export { mergeStyles, parseStyleValue } from './transformer/style-merger.js';
export { processElement, processContent } from './transformer/partial-handler.js';
export { generateDiff } from './reporter/diff-reporter.js';
export { SummaryReporter } from './reporter/summary-reporter.js';
export { ManualReviewCollector } from './reporter/manual-review.js';
export { run, parseArgs } from './cli.js';

import allRules from './mappings/index.js';
export { allRules };
