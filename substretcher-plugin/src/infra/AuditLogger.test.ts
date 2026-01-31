import { describe, it, expect, afterAll } from 'vitest';
import { AuditLogger } from './AuditLogger.js';
import { readFile, rm, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';

// Use a single test directory for all tests to avoid race conditions
const testDir = join(tmpdir(), `substretcher-test-${process.pid}`);

describe('AuditLogger', () => {
  afterAll(async () => {
    // Clean up after all tests
    if (existsSync(testDir)) {
      await rm(testDir, { recursive: true });
    }
  });

  describe('log', () => {
    it('should write JSONL entries to log file', async () => {
      const logDir = join(testDir, 'log-test-1');
      await mkdir(logDir, { recursive: true });
      const logger = new AuditLogger(logDir);

      await logger.log('scan_start', 'netflix', 'Starting scan', true);
      await logger.log('scan_complete', 'netflix', 'Completed scan', true);

      const content = await readFile(logger.getLogPath(), 'utf-8');
      const lines = content.trim().split('\n');

      expect(lines).toHaveLength(2);

      const entry1 = JSON.parse(lines[0]);
      expect(entry1.action).toBe('scan_start');
      expect(entry1.serviceId).toBe('netflix');
      expect(entry1.success).toBe(true);

      const entry2 = JSON.parse(lines[1]);
      expect(entry2.action).toBe('scan_complete');
    });

    it('should include metadata when provided', async () => {
      const logDir = join(testDir, 'log-test-2');
      await mkdir(logDir, { recursive: true });
      const logger = new AuditLogger(logDir);

      await logger.log('cancel_complete', 'spotify', 'Cancelled', true, {
        endDate: '2024-02-01',
      });

      const content = await readFile(logger.getLogPath(), 'utf-8');
      const entry = JSON.parse(content.trim());

      expect(entry.metadata).toEqual({ endDate: '2024-02-01' });
    });
  });

  describe('sanitize', () => {
    it('should mask credit card numbers', async () => {
      const logDir = join(testDir, 'sanitize-test-1');
      await mkdir(logDir, { recursive: true });
      const logger = new AuditLogger(logDir);

      await logger.log(
        'scan_complete',
        'netflix',
        'Found card: 4111 1111 1111 1234',
        true
      );

      const content = await readFile(logger.getLogPath(), 'utf-8');
      const entry = JSON.parse(content.trim());

      expect(entry.details).toContain('****1234');
      expect(entry.details).not.toContain('4111');
    });

    it('should mask email addresses', async () => {
      const logDir = join(testDir, 'sanitize-test-2');
      await mkdir(logDir, { recursive: true });
      const logger = new AuditLogger(logDir);

      await logger.log(
        'scan_complete',
        'netflix',
        'Account: user@example.com',
        true
      );

      const content = await readFile(logger.getLogPath(), 'utf-8');
      const entry = JSON.parse(content.trim());

      expect(entry.details).toContain('[email]');
      expect(entry.details).not.toContain('user@example.com');
    });

    it('should strip full URLs, keep domain only', async () => {
      const logDir = join(testDir, 'sanitize-test-3');
      await mkdir(logDir, { recursive: true });
      const logger = new AuditLogger(logDir);

      await logger.log(
        'scan_start',
        'netflix',
        'Navigating to https://netflix.com/account/billing?token=secret',
        true
      );

      const content = await readFile(logger.getLogPath(), 'utf-8');
      const entry = JSON.parse(content.trim());

      expect(entry.details).toContain('netflix.com');
      expect(entry.details).not.toContain('token=secret');
    });
  });

  describe('getLogPath', () => {
    it('should return the audit log path', () => {
      const logDir = join(testDir, 'path-test');
      const logger = new AuditLogger(logDir);
      expect(logger.getLogPath()).toBe(join(logDir, 'audit.log'));
    });
  });
});
