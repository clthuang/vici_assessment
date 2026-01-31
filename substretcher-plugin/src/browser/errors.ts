/**
 * Error thrown when Chrome is not running with debugging enabled
 */
export class ChromeNotRunningError extends Error {
  constructor(port: number = 9222) {
    super(
      `Chrome is not running with debugging enabled on port ${port}.\n` +
        `Start Chrome with: /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=${port}`
    );
    this.name = 'ChromeNotRunningError';
  }
}

/**
 * Error thrown when the CDP connection is lost
 */
export class ConnectionLostError extends Error {
  constructor(message?: string) {
    super(message ?? 'Lost connection to Chrome. Please reconnect.');
    this.name = 'ConnectionLostError';
  }
}

/**
 * Error thrown when page navigation times out
 */
export class NavigationTimeoutError extends Error {
  constructor(url: string, timeout: number) {
    super(`Navigation to ${url} timed out after ${timeout}ms`);
    this.name = 'NavigationTimeoutError';
  }
}

/**
 * Error thrown when an element is not found on the page
 */
export class ElementNotFoundError extends Error {
  constructor(selector: string) {
    super(`Element not found: ${selector}`);
    this.name = 'ElementNotFoundError';
  }
}
