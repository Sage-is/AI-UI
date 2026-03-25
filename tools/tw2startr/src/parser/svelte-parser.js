/**
 * Find regions in the content that are inside <script> or <style> blocks.
 * Returns an array of { start, end } ranges to skip.
 */
function findSkipRegions(content) {
  const regions = [];
  const blockPattern = /<(script|style)[\s>][^]*?<\/\1>/gi;
  let match;
  while ((match = blockPattern.exec(content)) !== null) {
    regions.push({ start: match.index, end: match.index + match[0].length });
  }
  return regions;
}

/**
 * Check if a position is inside a skip region.
 */
function isInSkipRegion(pos, regions) {
  return regions.some(r => pos >= r.start && pos < r.end);
}

/**
 * Extract a complete opening tag starting at a given position.
 * Handles multi-line tags and nested braces (Svelte expressions in attributes).
 * Returns { tag: string, endIdx: number } or null.
 */
function extractOpenTag(content, startIdx) {
  let i = startIdx;
  let depth = 0;  // brace depth for Svelte expressions
  let inString = false;
  let stringChar = '';
  let tag = '';

  while (i < content.length) {
    const ch = content[i];
    tag += ch;

    // Handle strings
    if ((ch === '"' || ch === "'" || ch === '`') && (i === 0 || content[i - 1] !== '\\')) {
      if (!inString) {
        inString = true;
        stringChar = ch;
      } else if (ch === stringChar) {
        inString = false;
      }
    }

    if (!inString) {
      if (ch === '{') depth++;
      if (ch === '}') depth--;

      // Self-closing tag
      if (ch === '>' && depth === 0) {
        return { tag, endIdx: i, selfClosing: tag.endsWith('/>') };
      }
    }

    i++;
  }

  return null;
}

/**
 * Parse a tag string to extract attributes.
 * Returns { tagName, attributes: Map<string, { value, quote, start, end }>, raw }
 *
 * We specifically need class and style attributes.
 */
function parseTagAttributes(tagStr) {
  // Extract tag name
  const tagNameMatch = tagStr.match(/^<(\/?[\w.-]+)/);
  if (!tagNameMatch) return null;
  const tagName = tagNameMatch[1];

  // Find class and style attributes specifically
  // These can be complex with multi-line values and Svelte expressions
  const attrs = {};

  // Match class attribute: class="..." or class='...' or class={...}
  // Handle the value which may contain { } Svelte expressions
  const classMatch = findAttribute(tagStr, 'class');
  if (classMatch) attrs.class = classMatch;

  const styleMatch = findAttribute(tagStr, 'style');
  if (styleMatch) attrs.style = styleMatch;

  return { tagName, attrs, raw: tagStr };
}

/**
 * Find a specific attribute in a tag string.
 * Returns { value, startIdx, endIdx, quote } or null.
 *
 * Handles:
 *   class="value here"
 *   class='value here'
 *   class={expression}
 *   class="value with {expression} inside"
 */
function findAttribute(tagStr, attrName) {
  // Look for attrName= followed by a quoted value or Svelte expression
  // Use a state machine approach for robustness
  const searchStr = attrName + '=';
  let searchIdx = 0;

  while (true) {
    const idx = tagStr.indexOf(searchStr, searchIdx);
    if (idx === -1) return null;

    // Make sure it's actually the attribute (preceded by whitespace or tag start)
    if (idx > 0) {
      const prevChar = tagStr[idx - 1];
      if (prevChar !== ' ' && prevChar !== '\t' && prevChar !== '\n' && prevChar !== '\r') {
        searchIdx = idx + 1;
        continue;
      }
    }

    const valueStart = idx + searchStr.length;
    if (valueStart >= tagStr.length) return null;

    const firstChar = tagStr[valueStart];

    if (firstChar === '"' || firstChar === "'") {
      // Quoted value — find matching closing quote
      // But must handle nested { } Svelte expressions
      let i = valueStart + 1;
      let braceDepth = 0;

      while (i < tagStr.length) {
        const ch = tagStr[i];
        if (ch === '{') braceDepth++;
        else if (ch === '}') braceDepth--;
        else if (ch === firstChar && braceDepth === 0) {
          // Found closing quote
          return {
            value: tagStr.substring(valueStart + 1, i),
            fullMatch: tagStr.substring(idx, i + 1),
            attrStart: idx,
            attrEnd: i + 1,
            quote: firstChar
          };
        }
        i++;
      }
      return null;
    } else if (firstChar === '{') {
      // Svelte expression as entire attribute value: class={expr}
      let i = valueStart;
      let depth = 0;
      let inStr = false;
      let strCh = '';

      while (i < tagStr.length) {
        const ch = tagStr[i];
        if (inStr) {
          if (ch === strCh && tagStr[i-1] !== '\\') inStr = false;
        } else {
          if (ch === '"' || ch === "'" || ch === '`') { inStr = true; strCh = ch; }
          else if (ch === '{') depth++;
          else if (ch === '}') { depth--; if (depth === 0) {
            return {
              value: tagStr.substring(valueStart, i + 1),
              fullMatch: tagStr.substring(idx, i + 1),
              attrStart: idx,
              attrEnd: i + 1,
              quote: '{',
              isSvelteExpression: true
            };
          }}
        }
        i++;
      }
      return null;
    }

    searchIdx = idx + 1;
  }
}

/**
 * Parse a Svelte file and find all elements with class and/or style attributes.
 *
 * Returns an array of:
 * {
 *   tagStart: number,      // position in content where the tag starts
 *   tagEnd: number,        // position where the tag ends
 *   tagName: string,       // element name
 *   classAttr: { value, attrStart, attrEnd, quote } | null,
 *   styleAttr: { value, attrStart, attrEnd, quote } | null,
 *   fullTag: string,       // the entire opening tag string
 * }
 */
export function parseElements(content) {
  const skipRegions = findSkipRegions(content);
  const elements = [];

  // Find all opening tags: < followed by a letter or uppercase (components)
  const tagStartPattern = /<(?=[A-Za-z])/g;
  let match;

  while ((match = tagStartPattern.exec(content)) !== null) {
    if (isInSkipRegion(match.index, skipRegions)) continue;

    const tagInfo = extractOpenTag(content, match.index);
    if (!tagInfo) continue;

    const parsed = parseTagAttributes(tagInfo.tag);
    if (!parsed) continue;

    // Skip closing tags, comments, etc.
    if (parsed.tagName.startsWith('/')) continue;

    // Only include elements that have class or style attributes
    if (parsed.attrs.class || parsed.attrs.style) {
      elements.push({
        tagStart: match.index,
        tagEnd: tagInfo.endIdx + 1,
        tagName: parsed.tagName,
        classAttr: parsed.attrs.class || null,
        styleAttr: parsed.attrs.style || null,
        fullTag: tagInfo.tag,
      });
    }
  }

  return elements;
}

/**
 * Replace a tag in the content with a new tag string.
 * Returns the new content.
 */
export function replaceTag(content, element, newTag) {
  return content.substring(0, element.tagStart) + newTag + content.substring(element.tagEnd);
}

export { findAttribute, extractOpenTag, parseTagAttributes };
