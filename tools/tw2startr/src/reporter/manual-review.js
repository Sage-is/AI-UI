/**
 * Collects and reports items that need human attention.
 */
export class ManualReviewCollector {
  constructor() {
    this.items = [];
  }

  add(filePath, line, className, reason) {
    this.items.push({ filePath, line, className, reason });
  }

  addFromReviews(filePath, reviews) {
    for (const review of reviews) {
      this.items.push({ filePath, line: null, className: null, reason: review });
    }
  }

  getReport() {
    if (this.items.length === 0) return '';

    let report = '\n' + '='.repeat(60) + '\n';
    report += 'MANUAL REVIEW NEEDED\n';
    report += '='.repeat(60) + '\n\n';
    report += `${this.items.length} item(s) need manual attention:\n\n`;

    // Group by file
    const byFile = new Map();
    for (const item of this.items) {
      if (!byFile.has(item.filePath)) byFile.set(item.filePath, []);
      byFile.get(item.filePath).push(item);
    }

    for (const [file, items] of byFile) {
      report += `${file}:\n`;
      for (const item of items) {
        const lineInfo = item.line ? `:${item.line}` : '';
        const classInfo = item.className ? ` [${item.className}]` : '';
        report += `  ${lineInfo}${classInfo} — ${item.reason}\n`;
      }
      report += '\n';
    }

    return report;
  }
}
