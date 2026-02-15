/**
 * Parse an existing style attribute value into individual property declarations.
 * Handles:
 *   "--d:flex; --ai:center; --p:1rem"
 *   "color: red; --d: flex"
 *   Mixed with Svelte expressions: "--d:flex; {isActive ? '--bg:red' : ''}"
 *
 * Returns { staticProps: Map<string, string>, dynamicParts: [{index, expression}] }
 * where staticProps maps property name to value, and dynamicParts are Svelte {expressions}
 * in their original positions.
 */
export function parseStyleValue(styleValue) {
  if (!styleValue) return { staticProps: new Map(), segments: [] };

  const segments = [];
  let current = '';
  let i = 0;

  while (i < styleValue.length) {
    if (styleValue[i] === '{') {
      // Flush current static text
      if (current.trim()) {
        segments.push({ type: 'static', text: current });
      }
      current = '';

      // Find matching closing brace
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

  if (current.trim()) {
    segments.push({ type: 'static', text: current });
  }

  // Parse static segments into property map
  const staticProps = new Map();
  for (const seg of segments) {
    if (seg.type === 'static') {
      // Split by semicolons to get individual declarations
      const decls = seg.text.split(';').map(d => d.trim()).filter(Boolean);
      for (const decl of decls) {
        const colonIdx = decl.indexOf(':');
        if (colonIdx !== -1) {
          const prop = decl.substring(0, colonIdx).trim();
          const value = decl.substring(colonIdx + 1).trim();
          staticProps.set(prop, value);
        }
      }
    }
  }

  return { staticProps, segments };
}

/**
 * Merge new properties into an existing style value.
 * New properties override existing ones with the same name.
 * Preserves dynamic Svelte expressions.
 *
 * @param {string|null} existingStyle - Current style attribute value (may be null)
 * @param {Array<{prop: string, value: string}>} newProps - Properties to add
 * @returns {string} - The merged style attribute value
 */
export function mergeStyles(existingStyle, newProps) {
  if (!newProps || newProps.length === 0) return existingStyle || '';

  const { staticProps, segments } = parseStyleValue(existingStyle);

  // Add/override with new properties
  for (const { prop, value } of newProps) {
    staticProps.set(prop, value);
  }

  // Rebuild: static properties first, then dynamic parts
  const staticDecls = [];
  for (const [prop, value] of staticProps) {
    staticDecls.push(`${prop}:${value}`);
  }

  // Collect dynamic expressions from original segments
  const dynamicParts = segments
    .filter(s => s.type === 'dynamic')
    .map(s => s.expression);

  let result = staticDecls.join('; ');

  if (dynamicParts.length > 0) {
    // Add dynamic parts after static
    const dynamicStr = dynamicParts.join(' ');
    result = result ? `${result}; ${dynamicStr}` : dynamicStr;
  }

  return result;
}
