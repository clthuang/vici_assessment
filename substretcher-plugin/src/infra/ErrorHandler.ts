import { ErrorType, type ClassifiedError } from '../types/index.js';

/**
 * Classifies errors and determines recovery actions
 */
export class ErrorHandler {
  /**
   * Classify an error into a known type with recovery information
   */
  classify(error: Error): ClassifiedError {
    const message = error.message.toLowerCase();

    // Chrome not running
    if (
      message.includes('econnrefused') ||
      message.includes('connection refused') ||
      message.includes('cannot connect')
    ) {
      return {
        type: ErrorType.CHROME_NOT_RUNNING,
        message: 'Chrome is not running with debugging enabled',
        recoverable: false,
        userAction:
          'Start Chrome with: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222',
        originalError: error,
      };
    }

    // Connection lost
    if (
      message.includes('connection closed') ||
      message.includes('disconnected') ||
      message.includes('websocket')
    ) {
      return {
        type: ErrorType.CONNECTION_LOST,
        message: 'Lost connection to Chrome',
        recoverable: true,
        userAction: 'Will attempt to reconnect automatically',
        originalError: error,
      };
    }

    // Navigation timeout
    if (message.includes('timeout') || message.includes('timed out')) {
      return {
        type: ErrorType.NAVIGATION_TIMEOUT,
        message: 'Page load timed out',
        recoverable: true,
        userAction: 'Check your network connection and try again',
        originalError: error,
      };
    }

    // Auth required
    if (
      message.includes('login') ||
      message.includes('sign in') ||
      message.includes('auth')
    ) {
      return {
        type: ErrorType.AUTH_REQUIRED,
        message: 'Login required',
        recoverable: true,
        userAction: 'Please log in to the service and try again',
        originalError: error,
      };
    }

    // Rate limited
    if (message.includes('429') || message.includes('rate limit')) {
      return {
        type: ErrorType.RATE_LIMITED,
        message: 'Rate limited by the service',
        recoverable: true,
        userAction: 'Waiting before retrying',
        originalError: error,
      };
    }

    // Config invalid
    if (message.includes('config') || message.includes('validation')) {
      return {
        type: ErrorType.CONFIG_INVALID,
        message: 'Invalid configuration',
        recoverable: false,
        userAction: 'Check the service configuration file',
        originalError: error,
      };
    }

    // Service not found
    if (message.includes('not found') || message.includes('no such')) {
      return {
        type: ErrorType.SERVICE_NOT_FOUND,
        message: 'Service configuration not found',
        recoverable: false,
        userAction: 'Run "substretcher list" to see available services',
        originalError: error,
      };
    }

    // Unknown
    return {
      type: ErrorType.UNKNOWN,
      message: error.message,
      recoverable: false,
      originalError: error,
    };
  }

  /**
   * Format a classified error for user display
   */
  formatForUser(classified: ClassifiedError): string {
    let output = `Error: ${classified.message}`;

    if (classified.userAction) {
      output += `\n  → ${classified.userAction}`;
    }

    return output;
  }

  /**
   * Determine if an error should be retried
   */
  shouldRetry(classified: ClassifiedError): boolean {
    if (!classified.recoverable) {
      return false;
    }

    // Only retry certain error types
    return [
      ErrorType.CONNECTION_LOST,
      ErrorType.NAVIGATION_TIMEOUT,
      ErrorType.RATE_LIMITED,
    ].includes(classified.type);
  }
}
