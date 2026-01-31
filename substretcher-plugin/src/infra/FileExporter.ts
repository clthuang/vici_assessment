import { writeFile } from 'node:fs/promises';
import type { ScanResult, BillingInfo } from '../types/index.js';

/**
 * Export scan results to JSON or CSV files
 */
export class FileExporter {
  /**
   * Export results to JSON file (pretty-printed)
   */
  async exportJSON(result: ScanResult, path: string): Promise<void> {
    const json = JSON.stringify(result, null, 2);
    await writeFile(path, json, 'utf-8');
  }

  /**
   * Export results to CSV file
   * CSV field order (from spec 4.6):
   * serviceId,serviceName,status,renewalDate,amount,currency,cycle,paymentMethod,confidence,extractedAt
   */
  async exportCSV(result: ScanResult, path: string): Promise<void> {
    const header =
      'serviceId,serviceName,status,renewalDate,amount,currency,cycle,paymentMethod,confidence,extractedAt';

    const rows = result.services.map((b) => this.formatForCSV(b));
    const csv = [header, ...rows].join('\n');

    await writeFile(path, csv, 'utf-8');
  }

  /**
   * Format a BillingInfo as CSV row
   * Field mapping: cost.amount→amount, cost.currency→currency, cost.cycle→cycle
   * Null values: empty strings
   */
  private formatForCSV(billing: BillingInfo): string {
    const fields = [
      billing.serviceId,
      billing.serviceName,
      billing.status,
      billing.renewalDate ?? '',
      billing.cost?.amount?.toString() ?? '',
      billing.cost?.currency ?? '',
      billing.cost?.cycle ?? '',
      billing.paymentMethod ?? '',
      billing.confidence.toString(),
      billing.extractedAt,
    ];

    return fields.map((f) => this.escapeCSV(f)).join(',');
  }

  /**
   * Escape a CSV field value
   * Handles commas, quotes, and newlines
   */
  private escapeCSV(value: string): string {
    if (value === '') {
      return '';
    }

    // Check if escaping is needed
    const needsEscape =
      value.includes(',') ||
      value.includes('"') ||
      value.includes('\n') ||
      value.includes('\r');

    if (!needsEscape) {
      return value;
    }

    // Escape double quotes by doubling them
    const escaped = value.replace(/"/g, '""');

    // Wrap in double quotes
    return `"${escaped}"`;
  }
}
