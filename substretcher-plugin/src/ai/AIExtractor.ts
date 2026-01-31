import type { BillingInfo, ServiceConfig } from '../types/index.js';

/**
 * Result of an authentication check
 */
export interface AuthCheckResult {
  loggedIn: boolean;
  confidence: number; // 0-1
  reason: string; // Explanation for debugging
}

/**
 * Location of an element found by AI
 */
export interface ElementLocation {
  x: number; // Pixel X coordinate
  y: number; // Pixel Y coordinate
  width?: number; // Element width (if determinable)
  height?: number; // Element height (if determinable)
  confidence: number; // 0-1
}

/**
 * Interface for AI-powered extraction
 */
export interface AIExtractor {
  /**
   * Extract billing information from screenshot
   * @param screenshot - PNG image buffer
   * @param config - Service configuration with hints
   * @returns Extracted billing info with confidence score
   */
  extractBillingInfo(
    screenshot: Buffer,
    config: ServiceConfig
  ): Promise<BillingInfo>;

  /**
   * Check if user is logged in
   * @param screenshot - PNG image buffer
   * @param serviceName - Human-readable service name
   */
  isLoggedIn(screenshot: Buffer, serviceName: string): Promise<AuthCheckResult>;

  /**
   * Find clickable element by description
   * Used for AI-guided cancellation when no selector available
   * @param screenshot - PNG image buffer
   * @param description - Human description of element
   * @returns Coordinates or null if not found
   */
  findElement(
    screenshot: Buffer,
    description: string
  ): Promise<ElementLocation | null>;
}
