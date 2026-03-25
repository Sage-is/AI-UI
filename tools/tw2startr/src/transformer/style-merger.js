/**
 * Parse an existing style attribute value into ordered segments.
 * Handles:
 *   "--d:flex; --ai:center; --p:1rem"
 *   "color: red; --d: flex"
 *   Mixed with Svelte expressions: "--d:flex; {isActive ? '--bg:red' : ''}"
 *   Expressions embedded in CSS values: "opacity: {expr}; background-image: url('{expr}')"
 *
 * Returns { staticProps: Map<string, string>, segments: [{type, ...}] }
 */
export function parseStyleValue(styleValue) {
  if (!styleValue) return { staticProps: new Map(), segments: [] };

  const segments = [];
  let current = '';
  let i = 0;

  while (i < styleValue.length) {
    if (styleValue[i] === '{') {
      // Check if this brace is inside a CSS string context (e.g., url('...'))
      if (isInsideCssString(current)) {
        current += styleValue[i];
        i++;
        continue;
      }

      // Flush current static text
      if (current) {
        segments.push({ type: 'static', text: current });
      }
      current = '';

      // Find matching closing brace (Svelte expression)
      let depth = 0;
      let start = i;
      let inStr = false;
      let strCh = '';

      while (i < styleValue.length) {
        const ch = styleValue[i];
        if (inStr) {
          if (ch === strCh && styleValue[i-1] !== '\\') inStr = false;
        } else {
          if (ch === '"' || ch === "'" || ch === '`') { inStr = true; strCh = ch; }
          else if (ch === '{') depth++;
          else if (ch === '}') { depth--; if (depth === 0) { i++; break; } }
        }
        i++;
      }

      segments.push({ type: 'dynamic', expression: styleValue.substring(start, i) });
    } else {
      current += styleValue[i];
      i++;
    }
  }

  if (current) {
    segments.push({ type: 'static', text: current });
  }

  // Parse static segments into property map
  const staticProps = new Map();
  for (const seg of segments) {
    if (seg.type === 'static') {
      const decls = seg.text.split(';').map(d => d.trim()).filter(Boolean);
      for (const decl of decls) {
        const colonIdx = decl.indexOf(':');
        if (colonIdx !== -1) {
          const prop = decl.substring(0, colonIdx).trim();
          const value = decl.substring(colonIdx + 1).trim();
          if (value) {
            staticProps.set(prop, value);
          }
        }
      }
    }
  }

  return { staticProps, segments };
}

/**
 * Check if the current position is inside a CSS string context
 * (e.g., inside url('...') or similar constructs where { is not a Svelte expression)
 */
function isInsideCssString(text) {
  let singleQuotes = 0;
  let doubleQuotes = 0;

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (ch === "'" && (i === 0 || text[i-1] !== '\\')) singleQuotes++;
    if (ch === '"' && (i === 0 || text[i-1] !== '\\')) doubleQuotes++;
  }

  let parenDepth = 0;
  for (let i = 0; i < text.length; i++) {
    if (text[i] === '(') parenDepth++;
    if (text[i] === ')') parenDepth--;
  }

  return (singleQuotes % 2 !== 0) || (doubleQuotes % 2 !== 0) || parenDepth > 0;
}

/**
 * Merge new properties into an existing style value.
 * New properties override existing ones with the same name.
 * Preserves dynamic Svelte expressions in their original positions.
 *
 * Strategy:
 * - If no property conflicts: prepend new props, keep existing style verbatim
 * - If conflicts: remove overridden declarations from existing, then prepend new
 *
 * @param {string|null} existingStyle - Current style attribute value (may be null)
 * @param {Array<{prop: string, value: string}>} newProps - Properties to add
 * @returns {string} - The merged style attribute value
 */
export function mergeStyles(existingStyle, newProps) {
  if (!newProps || newProps.length === 0) return existingStyle || '';

  const newDecls = newProps.map(({ prop, value }) => `${prop}:${value}`).join('; ');

  if (!existingStyle) return newDecls;

  const { staticProps } = parseStyleValue(existingStyle);
  const newPropNames = new Set(newProps.map(p => p.prop));

  // Check if any new props conflict with existing static props
  let hasConflicts = false;
  for (const propName of newPropNames) {
    if (staticProps.has(propName)) {
      hasConflicts = true;
      break;
    }
  }

  if (!hasConflicts) {
    // No conflicts — simply prepend new props, keep existing verbatim
    return `${newDecls}; ${existingStyle}`;
  }

  // Has conflicts — remove overridden property declarations from existing style
  // while preserving everything else (dynamic expressions, formatting) verbatim
  const cleaned = removePropsFromStyle(existingStyle, newPropNames);

  if (cleaned) {
    return `${newDecls}; ${cleaned}`;
  }
  return newDecls;
}

/**
 * Remove specific property declarations from a style string while preserving
 * dynamic Svelte expressions and the overall structure.
 *
 * Works by scanning character-by-character, tracking brace depth to avoid
 * modifying content inside { } expressions.
 */
function removePropsFromStyle(styleStr, propsToRemove) {
  // Split into segments (static text and dynamic expressions)
  const { segments } = parseStyleValue(styleStr);

  // Process only static segments: remove conflicting declarations
  // but keep the text structure (semicolons, whitespace) intact
  const result = [];
  for (const seg of segments) {
    if (seg.type === 'dynamic') {
      result.push(seg.expression);
    } else {
      // Split by semicolons, keeping the semicolons as separators
      const parts = seg.text.split(';');
      const kept = [];
      for (const part of parts) {
        const trimmed = part.trim();
        if (!trimmed) {
          kept.push(part);
          continue;
        }
        const colonIdx = trimmed.indexOf(':');
        if (colonIdx !== -1) {
          const propName = trimmed.substring(0, colonIdx).trim();
          if (propsToRemove.has(propName)) {
            // Skip this declaration
            continue;
          }
        }
        kept.push(part);
      }
      result.push(kept.join(';'));
    }
  }

  // Join and clean up
  let cleaned = result.join('').trim();
  // Remove double/triple semicolons and leading/trailing semicolons
  cleaned = cleaned.replace(/;\s*;+/g, ';').replace(/^\s*;+\s*/, '').replace(/\s*;+\s*$/, '');
  return cleaned;
}
