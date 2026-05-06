import allRules from '../mappings/index.js';

let customClassMap = new Map();

/**
 * Configure project-specific class mappings.
 *
 * Input shape:
 * {
 *   "class-name": { "--prop": "value", "plain-css-prop": "value" },
 *   "another-class": [
 *     { "prop": "--w", "value": "100%" },
 *     { "prop": "--mx", "value": "auto" }
 *   ]
 * }
 */
export function setCustomClassMap(mapObject = {}) {
  const next = new Map();

  for (const [className, mapping] of Object.entries(mapObject)) {
    if (!className || typeof className !== 'string') continue;

    if (Array.isArray(mapping)) {
      const normalized = mapping
        .filter((entry) => entry && typeof entry.prop === 'string' && typeof entry.value === 'string')
        .map((entry) => ({ prop: entry.prop, value: entry.value }));
      if (normalized.length > 0) next.set(className, normalized);
      continue;
    }

    if (mapping && typeof mapping === 'object') {
      const normalized = Object.entries(mapping)
        .filter(([prop, value]) => typeof prop === 'string' && typeof value === 'string')
        .map(([prop, value]) => ({ prop, value }));
      if (normalized.length > 0) next.set(className, normalized);
    }
  }

  customClassMap = next;
}

/**
 * Reset project-specific class mappings.
 */
export function resetCustomClassMap() {
  customClassMap = new Map();
}

/**
 * Responsive prefix → startr.style suffix mapping
 */
const RESPONSIVE_SUFFIXES = {
  sm: '-sm',
  md: '-md',
  lg: '-lg',
  xl: '-xl',
  '2xl': '-xl',  // startr.style doesn't have -2xl, map to -xl
  print: '-pt',
};

/**
 * State prefixes that map to startr.style property prefixes
 */
const STATE_PREFIX_MAP = {
  hover: 'hvr',
  dark: 'dark',
};

/**
 * State prefixes that CANNOT be converted to inline styles.
 * These stay in the class attribute.
 */
const UNCONVERTIBLE_PREFIXES = new Set([
  'focus', 'focus-within', 'focus-visible',
  'active', 'visited', 'target',
  'first', 'last', 'only', 'odd', 'even',
  'first-of-type', 'last-of-type',
  'empty', 'disabled', 'enabled', 'checked', 'indeterminate', 'default',
  'required', 'valid', 'invalid', 'in-range', 'out-of-range',
  'placeholder-shown', 'autofill', 'read-only',
  'group-hover', 'group-focus', 'group-active', 'group-first', 'group-last',
  'peer-hover', 'peer-focus', 'peer-checked', 'peer-disabled',
  'has', 'group-has', 'peer-has',
  'before', 'after', 'first-line', 'first-letter',
  'marker', 'selection', 'file', 'placeholder',
  'backdrop', 'supports', 'motion-safe', 'motion-reduce',
  'contrast-more', 'contrast-less',
  'portrait', 'landscape',
  'ltr', 'rtl', 'open',
]);

/**
 * Data attribute prefixes that can't be inlined
 */
const DATA_PREFIX_RE = /^data-\[.+\]$/;

/**
 * Parse prefixes from a Tailwind class.
 * Returns { prefixes: string[], baseClass: string, isNegative: boolean }
 *
 * Examples:
 *   'sm:hover:bg-gray-100' → { prefixes: ['sm', 'hover'], baseClass: 'bg-gray-100', isNegative: false }
 *   'dark:hover:text-white' → { prefixes: ['dark', 'hover'], baseClass: 'text-white', isNegative: false }
 *   '-translate-x-4' → { prefixes: [], baseClass: 'translate-x-4', isNegative: true }
 *   'sm:-mt-4' → { prefixes: ['sm'], baseClass: 'mt-4', isNegative: true }
 */
export function parsePrefixes(twClass) {
  const parts = twClass.split(':');
  const prefixes = parts.slice(0, -1);
  let baseClass = parts[parts.length - 1];
  let isNegative = false;

  // Handle negative values (leading -)
  if (baseClass.startsWith('-')) {
    isNegative = true;
    baseClass = baseClass.substring(1);
  }

  return { prefixes, baseClass, isNegative };
}

/**
 * Check if any prefix makes this class unconvertible.
 * Returns the first unconvertible prefix found, or null.
 */
export function findUnconvertiblePrefix(prefixes) {
  for (const prefix of prefixes) {
    if (UNCONVERTIBLE_PREFIXES.has(prefix)) return prefix;
    if (DATA_PREFIX_RE.test(prefix)) return prefix;
    // Check compound: group-hover, peer-focus, etc.
    if (prefix.startsWith('group-') || prefix.startsWith('peer-')) return prefix;
  }
  return null;
}

/**
 * Classify prefixes into responsive, state, and unconvertible.
 */
function classifyPrefixes(prefixes) {
  const responsive = [];
  const states = [];
  const unconvertible = [];

  for (const prefix of prefixes) {
    if (RESPONSIVE_SUFFIXES[prefix]) {
      responsive.push(prefix);
    } else if (STATE_PREFIX_MAP[prefix]) {
      states.push(prefix);
    } else if (UNCONVERTIBLE_PREFIXES.has(prefix) || DATA_PREFIX_RE.test(prefix) ||
               prefix.startsWith('group-') || prefix.startsWith('peer-')) {
      unconvertible.push(prefix);
    } else {
      // Unknown prefix — treat as unconvertible to be safe
      unconvertible.push(prefix);
    }
  }

  return { responsive, states, unconvertible };
}

/**
 * Apply a responsive suffix to a startr.style property name.
 * '--d' + 'sm' → '--d-sm'
 * '--bgc' + 'md' → '--bgc-md'
 */
function applyResponsiveSuffix(prop, responsivePrefix) {
  const suffix = RESPONSIVE_SUFFIXES[responsivePrefix];
  if (!suffix) return prop;
  // Only apply to startr.style custom properties (starting with --)
  if (prop.startsWith('--')) return `${prop}${suffix}`;
  // For plain CSS properties, can't add responsive suffix — flag for review
  return prop;
}

/**
 * Apply state prefix to a startr.style property.
 * '--bgc' + 'hover' → '--hvr-bgc'  (extracts the short name after --)
 * '--c' + 'hover' → '--hvr-c'
 * '--bgc' + 'dark' → '--dark-bgc'
 *
 * For hover, only certain properties have startr.style support:
 * --hvr-bg, --hvr-bgc, --hvr-c, --hvr-b, --hvr-bc
 * Others are converted but may need review.
 *
 * For dark, use --dark-{shortname} pattern.
 */
function applyStatePrefix(prop, statePrefix) {
  const stateKey = STATE_PREFIX_MAP[statePrefix];
  if (!stateKey || !prop.startsWith('--')) return prop;

  // Extract the short name: '--bgc' → 'bgc', '--shadow' → 'shadow'
  const shortName = prop.substring(2);
  return `--${stateKey}-${shortName}`;
}

/**
 * Convert a single Tailwind class to startr.style property/value pair(s).
 *
 * Returns:
 *   { converted: true, properties: [{prop, value}], review?: string }
 *   { converted: false, reason: string }
 */
export function convertClass(twClass) {
  // Parse prefixes
  const { prefixes, baseClass, isNegative } = parsePrefixes(twClass);
  const { responsive, states, unconvertible } = classifyPrefixes(prefixes);

  // If any unconvertible prefix, can't convert
  if (unconvertible.length > 0) {
    return {
      converted: false,
      reason: `unconvertible prefix: ${unconvertible.join(', ')}`,
      originalClass: twClass
    };
  }

  // First try project-specific class map for direct class-name matches.
  let matchResult = null;
  if (customClassMap.has(baseClass)) {
    const mapped = customClassMap.get(baseClass) || [];
    matchResult = mapped.map((entry) => ({ prop: entry.prop, value: entry.value }));
  }

  // Fall back to built-in rules.
  if (!matchResult) {
    for (const rule of allRules) {
      const match = baseClass.match(rule.pattern);
      if (match) {
        matchResult = rule.convert(match);
        if (matchResult !== null) break;
      }
    }
  }

  if (!matchResult) {
    return {
      converted: false,
      reason: 'no matching rule',
      originalClass: twClass
    };
  }

  // Normalize to array
  let properties = Array.isArray(matchResult) ? matchResult : [matchResult];

  // Check for review flags
  let review = null;
  properties = properties.map(p => {
    if (p.review) {
      review = p.review;
      const { review: _, ...rest } = p;
      return rest;
    }
    return p;
  });

  // Apply negative if needed
  if (isNegative) {
    properties = properties.map(p => ({
      ...p,
      value: p.value.startsWith('-') ? p.value : `-${p.value}`
    }));
  }

  // Apply state prefixes (dark:, hover:)
  // Order matters: dark:hover:bg-gray-100 → --dark-hvr-bgc
  for (const statePrefix of states) {
    properties = properties.map(p => ({
      ...p,
      prop: applyStatePrefix(p.prop, statePrefix)
    }));
  }

  // Apply responsive suffixes
  // sm:hover:flex → --hvr-d-sm
  for (const respPrefix of responsive) {
    let hasPlainCSS = false;
    properties = properties.map(p => {
      if (p.prop.startsWith('--')) {
        return { ...p, prop: applyResponsiveSuffix(p.prop, respPrefix) };
      } else {
        hasPlainCSS = true;
        return p;
      }
    });
    if (hasPlainCSS) {
      review = (review ? review + '; ' : '') + `responsive prefix ${respPrefix}: on plain CSS property — no responsive support`;
    }
  }

  return {
    converted: true,
    properties,
    review: review || undefined,
    originalClass: twClass
  };
}

/**
 * Merge legacy opacity modifier classes into their base color class.
 * e.g. ['bg-green-700', 'bg-opacity-40'] → ['bg-green-700/40']
 * Handles: bg-opacity, text-opacity, border-opacity, ring-opacity
 */
function combineOpacityModifiers(classes) {
  const result = [...classes];
  for (const prefix of ['bg', 'text', 'border', 'ring', 'fill', 'stroke']) {
    const opIdx = result.findIndex(c => new RegExp(`^${prefix}-opacity-(\\d+)$`).test(c));
    if (opIdx === -1) continue;
    const opVal = result[opIdx].match(/-(\d+)$/)[1];
    // Find the matching color class (not the opacity class itself, not other opacity classes)
    const colorIdx = result.findIndex((c, i) => {
      if (i === opIdx) return false;
      if (!c.startsWith(`${prefix}-`)) return false;
      if (/^(bg|text|border|ring|fill|stroke)-opacity-/.test(c)) return false;
      return true;
    });
    if (colorIdx === -1) continue;
    result[colorIdx] = result[colorIdx] + '/' + opVal;
    result.splice(opIdx, 1);
  }
  return result;
}

/**
 * Guard against outputting values that look like unresolved Tailwind tokens.
 * Throws an error so the caller can treat the class as unconverted rather than
 * silently writing garbage like --bgc:opacity-50 or --bgc:green-700.
 */
function assertValidCssValue(prop, value, originalClass) {
  if (/^opacity-\d+$/.test(value)) {
    throw new Error(
      `unresolved opacity modifier "${value}" for ${prop} (class: "${originalClass}") — pair bg-opacity-* with a bg-{color} class`
    );
  }
  if (/^[a-z]+-\d{3}$/.test(value)) {
    throw new Error(
      `unresolved color token "${value}" for ${prop} (class: "${originalClass}")`
    );
  }
}

/**
 * Convert multiple Tailwind classes.
 * Returns { converted: [{prop, value, originalClass, review?}], unconverted: [string], reviews: [string] }
 */
export function convertClasses(classes) {
  const converted = [];
  const unconverted = [];
  const reviews = [];

  // Merge legacy opacity modifiers (bg-opacity-40 etc.) into their color class
  // before individual conversion so we never emit half-resolved values.
  const mergedClasses = combineOpacityModifiers(classes);

  for (const cls of mergedClasses) {
    const result = convertClass(cls);
    if (result.converted) {
      let guardFailed = false;
      for (const prop of result.properties) {
        try {
          assertValidCssValue(prop.prop, prop.value, result.originalClass);
        } catch (err) {
          reviews.push(err.message);
          unconverted.push(result.originalClass);
          guardFailed = true;
          break;
        }
        converted.push({ ...prop, originalClass: result.originalClass });
      }
      if (guardFailed) continue;
      if (result.review) {
        reviews.push(`${result.originalClass}: ${result.review}`);
      }
    } else {
      unconverted.push(result.originalClass);
      if (result.reason !== 'no matching rule') {
        reviews.push(`${result.originalClass}: ${result.reason}`);
      }
    }
  }

  return { converted, unconverted, reviews };
}
