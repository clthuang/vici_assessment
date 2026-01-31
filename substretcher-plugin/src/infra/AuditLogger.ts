import { appendFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';
import type { AuditLogEntry, AuditAction } from '../types/index.js';

/**
 * Append-only audit trail for actions
 */
export class AuditLogger {
  private readonly baseDir: string;
  private readonly logPath: string;

  constructor(baseDir?: string) {
    this.baseDir = baseDir ?? join(homedir(), '.substretcher');
    this.logPath = join(this.baseDir, 'audit.log');
  }

  /**
   * Ensure the base directory exists
   */
  private async ensureDir(): Promise<void> {
    if (!existsSync(this.baseDir)) {
      await mkdir(this.baseDir, { recursive: true });
    }
  }

  /**
   * Log an audit entry
   */
  async log(
    action: AuditAction,
    serviceId: string,
    details: string,
    success: boolean,
    metadata?: Record<string, string>
  ): Promise<void> {
    await this.ensureDir();

    const entry: AuditLogEntry = {
      timestamp: new Date().toISOString(),
      action,
      serviceId,
      details: this.sanitize(details),
      success,
      metadata,
    };

    const line = JSON.stringify(entry) + '\n';
    await appendFile(this.logPath, line, 'utf-8');
  }

  /**
   * Sanitize sensitive data from log entries
   */
  private sanitize(text: string): string {
    let sanitized = text;

    // Strip full URLs, keep domain only
    sanitized = sanitized.replace(
      /https?:\/\/([^/\s]+)[^\s]*/g,
      'https://$1/...'
    );

    // Mask card numbers (keep last 4)
    sanitized = sanitized.replace(
      /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?(\d{4})\b/g,
      '****$1'
    );

    // Mask shorter card patterns
    sanitized = sanitized.replace(
      /\b(\d{2})\d{10,14}(\d{4})\b/g,
      '$1****$2'
    );

    // Remove email addresses
    sanitized = sanitized.replace(
      /[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g,
      '[email]'
    );

    // Truncate long strings
    if (sanitized.length > 500) {
      sanitized = sanitized.substring(0, 500) + '...';
    }

    return sanitized;
  }

  /**
   * Get the log file path
   */
  getLogPath(): string {
    return this.logPath;
  }
}
