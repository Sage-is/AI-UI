/**
 * Aggregate and display conversion statistics.
 */
export class SummaryReporter {
  constructor() {
    this.files = [];
    this.totalClassesConverted = 0;
    this.totalClassesUnconverted = 0;
    this.totalElementsProcessed = 0;
    this.totalFilesModified = 0;
    this.totalFilesScanned = 0;
    this.errors = [];
    this.allReviews = [];
    this.unconvertedTally = new Map(); // class → count
  }

  addFile(filePath, stats) {
    this.totalFilesScanned++;
    if (stats.elementsProcessed > 0) {
      this.totalFilesModified++;
    }
    this.totalClassesConverted += stats.classesConverted;
    this.totalClassesUnconverted += stats.classesUnconverted;
    this.totalElementsProcessed += stats.elementsProcessed;
    this.allReviews.push(...stats.reviews.map(r => ({ file: filePath, review: r })));

    this.files.push({ path: filePath, ...stats });
  }

  addUnconvertedClass(cls) {
    this.unconvertedTally.set(cls, (this.unconvertedTally.get(cls) || 0) + 1);
  }

  addError(filePath, error) {
    this.errors.push({ file: filePath, error: error.message || error });
  }

  getReport() {
    const totalClasses = this.totalClassesConverted + this.totalClassesUnconverted;
    const conversionRate = totalClasses > 0
      ? ((this.totalClassesConverted / totalClasses) * 100).toFixed(1)
      : '0';

    let report = '\n' + '='.repeat(60) + '\n';
    report += 'CONVERSION SUMMARY\n';
    report += '='.repeat(60) + '\n\n';
    report += `Files scanned:      ${this.totalFilesScanned}\n`;
    report += `Files modified:     ${this.totalFilesModified}\n`;
    report += `Elements processed: ${this.totalElementsProcessed}\n`;
    report += `Classes converted:  ${this.totalClassesConverted}\n`;
    report += `Classes remaining:  ${this.totalClassesUnconverted}\n`;
    report += `Conversion rate:    ${conversionRate}%\n`;

    if (this.errors.length > 0) {
      report += `\nErrors: ${this.errors.length}\n`;
      for (const { file, error } of this.errors) {
        report += `  - ${file}: ${error}\n`;
      }
    }

    if (this.unconvertedTally.size > 0) {
      report += '\nTop unconverted classes:\n';
      const sorted = [...this.unconvertedTally.entries()]
        .sort((a, b) => b[1] - a[1])
        .slice(0, 30);
      for (const [cls, count] of sorted) {
        report += `  ${cls}: ${count}\n`;
      }
    }

    return report;
  }

  getReviewReport() {
    if (this.allReviews.length === 0) return '';

    let report = '\n' + '='.repeat(60) + '\n';
    report += 'ITEMS NEEDING REVIEW\n';
    report += '='.repeat(60) + '\n\n';

    // Group by review text
    const grouped = new Map();
    for (const { file, review } of this.allReviews) {
      if (!grouped.has(review)) grouped.set(review, []);
      grouped.get(review).push(file);
    }

    for (const [review, files] of grouped) {
      const uniqueFiles = [...new Set(files)];
      report += `${review}\n`;
      report += `  (${uniqueFiles.length} file(s))\n\n`;
    }

    return report;
  }
}
