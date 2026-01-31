/**
 * Billing information extracted from a subscription service
 */
export interface BillingInfo {
  serviceId: string;
  serviceName: string;
  status: 'active' | 'cancelled' | 'paused' | 'trial' | 'unknown';
  renewalDate: string | null; // ISO 8601 date
  cost: {
    amount: number;
    currency: string; // ISO 4217 code (USD, EUR, etc.)
    cycle: 'weekly' | 'monthly' | 'annual' | 'unknown';
  } | null;
  paymentMethod: string | null; // Masked, e.g., "Visa ****1234"
  confidence: number; // 0-1
  extractedAt: string; // ISO 8601 timestamp
  errors: string[]; // Any extraction warnings/errors
}

/**
 * Result of a multi-service scan operation
 */
export interface ScanResult {
  scannedAt: string; // ISO 8601 timestamp
  services: BillingInfo[];
  summary: {
    total: number;
    successful: number;
    failed: number;
    skipped: number;
    totalMonthlyCost: number; // Normalized to monthly
    currency: string;
  };
}

/**
 * Result of a cancellation operation
 */
export interface CancelResult {
  serviceId: string;
  serviceName: string;
  success: boolean;
  message: string;
  endDate: string | null; // When access ends
  cancelledAt: string; // ISO 8601 timestamp
}

/**
 * Options for scan operations
 */
export interface ScanOptions {
  output?: string;
  all?: boolean;
  verbose?: boolean;
  timeout?: number;
  fresh?: boolean;
}

/**
 * Options for cancel operations
 */
export interface CancelOptions {
  confirm?: boolean;
  verbose?: boolean;
  timeout?: number;
}
