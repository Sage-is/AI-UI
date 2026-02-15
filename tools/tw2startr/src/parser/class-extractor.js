/**
 * Split a class attribute value into static tokens and dynamic segments.
 *
 * Returns an array of segments, each either:
 *   { type: 'static', classes: string[] }  — array of individual class names
 *   { type: 'dynamic', expression: string } — verbatim Svelte expression including { }
 *
 * The segments maintain their order so the class attribute can be reconstructed.
 *
 * Examples:
 *   'flex items-center gap-2'
 *   → [{ type: 'static', classes: ['flex', 'items-center', 'gap-2'] }]
 *
 *   'flex {isOpen ? "block" : "hidden"} text-sm'
 *   → [
 *       { type: 'static', classes: ['flex'] },
 *       { type: 'dynamic', expression: '{isOpen ? "block" : "hidden"}' },
 *       { type: 'static', classes: ['text-sm'] }
 *     ]
 *
 *   '{someClass} flex items-center'
 *   → [
 *       { type: 'dynamic', expression: '{someClass}' },
 *       { type: 'static', classes: ['flex', 'items-center'] }
 *     ]
 */
export function extractClassSegments(classValue) {
  const segments = [];
  let i = 0;
  let currentStatic = '';

  while (i < classValue.length) {
    if (classValue[i] === '{') {
      // Flush any accumulated static text
      if (currentStatic.trim()) {
        const classes = currentStatic.trim().split(/\s+/).filter(Boolean);
        if (classes.length > 0) {
          segments.push({ type: 'static', classes });
        }
      }
      currentStatic = '';

      // Find the matching closing brace, accounting for nested braces and strings
      let depth = 0;
      let exprStart = i;
      let inString = false;
      let stringChar = '';

      while (i < classValue.length) {
        const ch = classValue[i];

        if (inString) {
          if (ch === stringChar && classValue[i - 1] !== '\\') {
            inString = false;
          }
        } else {
          if (ch === '"' || ch === "'" || ch === '`') {
            inString = true;
            stringChar = ch;
          } else if (ch === '{') {
            depth++;
          } else if (ch === '}') {
            depth--;
            if (depth === 0) {
              i++; // consume the closing brace
              segments.push({ type: 'dynamic', expression: classValue.substring(exprStart, i) });
              break;
            }
          }
        }
        i++;
      }
    } else {
      currentStatic += classValue[i];
      i++;
    }
  }

  // Flush remaining static text
  if (currentStatic.trim()) {
    const classes = currentStatic.trim().split(/\s+/).filter(Boolean);
    if (classes.length > 0) {
      segments.push({ type: 'static', classes });
    }
  }

  return segments;
}

/**
 * Get all static classes from segments.
 */
export function getStaticClasses(segments) {
  return segments
    .filter(s => s.type === 'static')
    .flatMap(s => s.classes);
}

/**
 * Check if the class value has any dynamic expressions.
 */
export function hasDynamicExpressions(classValue) {
  return classValue.includes('{');
}
