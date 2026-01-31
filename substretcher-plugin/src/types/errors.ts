/**
 * Types of errors that can occur during operation
 */
export enum ErrorType {
  CHROME_NOT_RUNNING = 'chrome_not_running',
  CONNECTION_LOST = 'connection_lost',
  NAVIGATION_TIMEOUT = 'navigation_timeout',
  AUTH_REQUIRED = 'auth_required',
  RATE_LIMITED = 'rate_limited',
  CONFIG_INVALID = 'config_invalid',
  SERVICE_NOT_FOUND = 'service_not_found',
  UNKNOWN = 'unknown',
}

/**
 * A classified error with recovery information
 */
export interface ClassifiedError {
  type: ErrorType;
  message: string;
  recoverable: boolean;
  userAction?: string;
  originalError?: Error;
}
