import type { BillingInfo } from './billing.js';

/**
 * State for resuming interrupted scans
 */
export interface ResumeState {
  scanId: string; // UUID for this scan session
  startedAt: string; // ISO 8601 timestamp
  services: string[]; // Services requested
  completed: string[]; // Services already processed
  results: BillingInfo[]; // Partial results collected
  lastUpdated: string; // ISO 8601 timestamp
}

/**
 * Types of audit log actions
 */
export type AuditAction =
  | 'scan_start'
  | 'scan_complete'
  | 'cancel_start'
  | 'cancel_step'
  | 'cancel_complete'
  | 'cancel_failed'
  | 'login_prompt'
  | 'user_skip';

/**
 * An entry in the audit log
 */
export interface AuditLogEntry {
  timestamp: string; // ISO 8601 timestamp
  action: AuditAction;
  serviceId: string;
  details: string; // Human-readable description (no sensitive data)
  success: boolean;
  metadata?: Record<string, string>; // Additional context (e.g., step number)
}
