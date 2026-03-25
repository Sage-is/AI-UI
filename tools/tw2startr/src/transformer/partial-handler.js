import { extractClassSegments } from '../parser/class-extractor.js';
import { convertClasses } from './class-converter.js';
import { mergeStyles } from './style-merger.js';

/**
 * Process a single HTML element's class and style attributes.
 *
 * @param {object} element - Parsed element from svelte-parser
 *   { classAttr: { value, ... }, styleAttr: { value, ... }, fullTag, ... }
 * @returns {object} - { newTag, stats }
 */
export function processElement(element) {
  const stats = {
    classesConverted: 0,
    classesUnconverted: 0,
    reviews: [],
  };

  if (!element.classAttr) {
    return { newTag: element.fullTag, stats };
  }

  const classValue = element.classAttr.value;

  // Handle class={expression} — entire class is a Svelte expression, skip
  if (element.classAttr.isSvelteExpression) {
    return { newTag: element.fullTag, stats };
  }

  // Extract static classes and dynamic segments
  const segments = extractClassSegments(classValue);

  // Collect all static classes for conversion
  const allStaticClasses = segments
    .filter(s => s.type === 'static')
    .flatMap(s => s.classes);

  if (allStaticClasses.length === 0) {
    return { newTag: element.fullTag, stats };
  }

  // Convert static classes
  const { converted, unconverted, reviews } = convertClasses(allStaticClasses);

  stats.classesConverted = converted.length;
  stats.classesUnconverted = unconverted.length;
  stats.reviews = reviews;

  if (converted.length === 0) {
    return { newTag: element.fullTag, stats };
  }

  // Build new style attribute value
  const existingStyle = element.styleAttr ? element.styleAttr.value : null;
  const newStyleValue = mergeStyles(existingStyle, converted);

  // Build new class attribute value
  // Replace converted classes in segments, keep unconverted and dynamic
  const unconvertedSet = new Set(unconverted);
  const newClassSegments = [];

  for (const seg of segments) {
    if (seg.type === 'dynamic') {
      newClassSegments.push(seg.expression);
    } else {
      // Filter to only unconverted classes
      const remaining = seg.classes.filter(c => unconvertedSet.has(c));
      if (remaining.length > 0) {
        newClassSegments.push(remaining.join(' '));
      }
    }
  }

  const newClassValue = newClassSegments.join(' ').trim();

  // Rebuild the tag
  let newTag = element.fullTag;

  // Replace or add style attribute
  if (element.styleAttr) {
    // Replace existing style value — attrStart/attrEnd are relative to fullTag
    newTag = newTag.substring(0, element.styleAttr.attrStart) +
      `style="${newStyleValue}"` +
      newTag.substring(element.styleAttr.attrEnd);
  } else {
    // Insert style attribute before the class attribute
    const insertPos = element.classAttr.attrStart;
    newTag = newTag.substring(0, insertPos) +
      `style="${newStyleValue}"\n\t` +
      newTag.substring(insertPos);
  }

  // Now update/remove class attribute in the modified tag
  // Re-find class attribute position in the modified tag since positions shifted
  if (newClassValue) {
    // Replace class value
    newTag = replaceAttributeValue(newTag, 'class', newClassValue, element.classAttr.quote);
  } else {
    // Remove class attribute entirely
    newTag = removeAttribute(newTag, 'class');
  }

  return { newTag, stats };
}

/**
 * Replace an attribute's value in a tag string.
 */
function replaceAttributeValue(tagStr, attrName, newValue, quote) {
  const q = quote === '{' ? '"' : (quote || '"');
  // Find the attribute
  const pattern = new RegExp(`(\\s)${attrName}\\s*=\\s*(?:"[^"]*"|'[^']*'|\\{[^}]*\\})`, 's');
  const match = tagStr.match(pattern);
  if (!match) return tagStr;
  return tagStr.replace(match[0], `${match[1]}${attrName}=${q}${newValue}${q}`);
}

/**
 * Remove an attribute entirely from a tag string.
 */
function removeAttribute(tagStr, attrName) {
  // Match the attribute including leading whitespace
  const pattern = new RegExp(`\\s+${attrName}\\s*=\\s*(?:"[^"]*"|'[^']*'|\\{[^}]*\\})`, 's');
  return tagStr.replace(pattern, '');
}

/**
 * Process an entire Svelte file content.
 * Returns { newContent, stats }
 */
export function processContent(content, parseElements, replaceTag) {
  const elements = parseElements(content);

  const totalStats = {
    elementsProcessed: 0,
    classesConverted: 0,
    classesUnconverted: 0,
    reviews: [],
  };

  if (elements.length === 0) {
    return { newContent: content, stats: totalStats };
  }

  // Process elements in reverse order to maintain correct positions
  let newContent = content;

  for (let i = elements.length - 1; i >= 0; i--) {
    const element = elements[i];
    const { newTag, stats } = processElement(element);

    if (newTag !== element.fullTag) {
      newContent = newContent.substring(0, element.tagStart) +
        newTag +
        newContent.substring(element.tagEnd);

      totalStats.elementsProcessed++;
      totalStats.classesConverted += stats.classesConverted;
      totalStats.classesUnconverted += stats.classesUnconverted;
      totalStats.reviews.push(...stats.reviews);
    }
  }

  return { newContent, stats: totalStats };
}
