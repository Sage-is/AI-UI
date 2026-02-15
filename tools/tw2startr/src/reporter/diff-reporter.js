/**
 * Generate a unified diff between two strings.
 * Simple implementation — shows changed lines with context.
 */
export function generateDiff(filePath, original, modified, contextLines = 3) {
  if (original === modified) return null;

  const origLines = original.split('\n');
  const modLines = modified.split('\n');

  const hunks = [];
  let i = 0;
  let j = 0;

  while (i < origLines.length || j < modLines.length) {
    if (i < origLines.length && j < modLines.length && origLines[i] === modLines[j]) {
      i++;
      j++;
      continue;
    }

    // Found a difference — collect the hunk
    const hunkStartOrig = Math.max(0, i - contextLines);
    const hunkStartMod = Math.max(0, j - contextLines);

    // Find how many lines differ
    let diffEndOrig = i;
    let diffEndMod = j;

    // Simple approach: advance both until we find matching lines again
    while (diffEndOrig < origLines.length || diffEndMod < modLines.length) {
      if (diffEndOrig < origLines.length && diffEndMod < modLines.length &&
          origLines[diffEndOrig] === modLines[diffEndMod]) {
        // Check if we have enough matching context to end the hunk
        let matchCount = 0;
        while (diffEndOrig + matchCount < origLines.length &&
               diffEndMod + matchCount < modLines.length &&
               origLines[diffEndOrig + matchCount] === modLines[diffEndMod + matchCount]) {
          matchCount++;
          if (matchCount >= contextLines * 2) break;
        }
        if (matchCount >= contextLines) break;
      }
      if (diffEndOrig < origLines.length) diffEndOrig++;
      if (diffEndMod < modLines.length) diffEndMod++;
    }

    const hunkEndOrig = Math.min(origLines.length, diffEndOrig + contextLines);
    const hunkEndMod = Math.min(modLines.length, diffEndMod + contextLines);

    const hunk = {
      origStart: hunkStartOrig + 1,
      origCount: hunkEndOrig - hunkStartOrig,
      modStart: hunkStartMod + 1,
      modCount: hunkEndMod - hunkStartMod,
      lines: []
    };

    // Add context before
    for (let k = hunkStartOrig; k < i; k++) {
      hunk.lines.push(` ${origLines[k]}`);
    }

    // Add removed lines
    for (let k = i; k < diffEndOrig; k++) {
      hunk.lines.push(`-${origLines[k]}`);
    }

    // Add added lines
    for (let k = j; k < diffEndMod; k++) {
      hunk.lines.push(`+${modLines[k]}`);
    }

    // Add context after
    for (let k = diffEndOrig; k < hunkEndOrig; k++) {
      hunk.lines.push(` ${origLines[k]}`);
    }

    hunks.push(hunk);

    i = hunkEndOrig;
    j = hunkEndMod;
  }

  if (hunks.length === 0) return null;

  // Format as unified diff
  let diff = `--- a/${filePath}\n+++ b/${filePath}\n`;
  for (const hunk of hunks) {
    diff += `@@ -${hunk.origStart},${hunk.origCount} +${hunk.modStart},${hunk.modCount} @@\n`;
    diff += hunk.lines.join('\n') + '\n';
  }

  return diff;
}
