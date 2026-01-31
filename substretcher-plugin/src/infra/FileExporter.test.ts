import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { FileExporter } from './FileExporter.js';
import { readFile, rm, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import type { ScanResult } from '../types/index.js';

describe('FileExporter', () => {
  let testDir: string;
  let exporter: FileExporter;

  const sampleResult: ScanResult = {
    scannedAt: '2024-01-15T10:00:00Z',
    services: [
      {
        serviceId: 'netflix',
        serviceName: 'Netflix',
        status: 'active',
        renewalDate: '2024-02-15',
        cost: { amount: 15.99, currency: 'USD', cycle: 'monthly' },
        paymentMethod: 'Visa ****1234',
        confidence: 0.95,
        extractedAt: '2024-01-15T10:00:00Z',
        errors: [],
      },
      {
        serviceId: 'spotify',
        serviceName: 'Spotify',
        status: 'active',
        renewalDate: '2024-02-01',
        cost: { amount: 10.99, currency: 'USD', cycle: 'monthly' },
        paymentMethod: 'Mastercard ****5678',
        confidence: 0.88,
        extractedAt: '2024-01-15T10:01:00Z',
        errors: [],
      },
    ],
    summary: {
      total: 2,
      successful: 2,
      failed: 0,
      skipped: 0,
      totalMonthlyCost: 26.98,
      currency: 'USD',
    },
  };

  beforeEach(async () => {
    testDir = join(tmpdir(), `substretcher-test-${Date.now()}`);
    await mkdir(testDir, { recursive: true });
    exporter = new FileExporter();
  });

  afterEach(async () => {
    if (existsSync(testDir)) {
      await rm(testDir, { recursive: true });
    }
  });

  describe('exportJSON', () => {
    it('should export scan results as JSON', async () => {
      const filePath = join(testDir, 'results.json');
      await exporter.exportJSON(sampleResult, filePath);

      const content = await readFile(filePath, 'utf-8');
      const parsed = JSON.parse(content);

      expect(parsed.scannedAt).toBe(sampleResult.scannedAt);
      expect(parsed.services).toHaveLength(2);
      expect(parsed.summary.totalMonthlyCost).toBe(26.98);
    });

    it('should format JSON with indentation', async () => {
      const filePath = join(testDir, 'results.json');
      await exporter.exportJSON(sampleResult, filePath);

      const content = await readFile(filePath, 'utf-8');

      // Should be pretty-printed
      expect(content).toContain('\n');
      expect(content.split('\n').length).toBeGreaterThan(5);
    });
  });

  describe('exportCSV', () => {
    it('should export scan results as CSV', async () => {
      const filePath = join(testDir, 'results.csv');
      await exporter.exportCSV(sampleResult, filePath);

      const content = await readFile(filePath, 'utf-8');
      const lines = content.trim().split('\n');

      // Header + 2 data rows
      expect(lines).toHaveLength(3);

      // Check header
      expect(lines[0]).toContain('serviceId');
      expect(lines[0]).toContain('serviceName');
      expect(lines[0]).toContain('status');

      // Check data
      expect(lines[1]).toContain('netflix');
      expect(lines[1]).toContain('Netflix');
      expect(lines[2]).toContain('spotify');
    });

    it('should properly escape CSV values with commas', async () => {
      const resultWithComma: ScanResult = {
        ...sampleResult,
        services: [
          {
            ...sampleResult.services[0],
            serviceName: 'Netflix, Inc.',
          },
        ],
      };

      const filePath = join(testDir, 'results.csv');
      await exporter.exportCSV(resultWithComma, filePath);

      const content = await readFile(filePath, 'utf-8');

      // Should be quoted
      expect(content).toContain('"Netflix, Inc."');
    });
  });
});
