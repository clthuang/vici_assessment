/**
 * Interface for browser automation
 */
export interface BrowserAdapter {
  /**
   * Connect to Chrome via CDP
   * @param port - Debug port (default: 9222)
   * @throws ChromeNotRunningError if Chrome not available
   */
  connect(port?: number): Promise<void>;

  /**
   * Gracefully disconnect from Chrome
   */
  disconnect(): Promise<void>;

  /**
   * Check if currently connected
   */
  isConnected(): boolean;

  /**
   * Navigate to URL and wait for load
   * @param url - URL to navigate to
   * @param timeout - Timeout in milliseconds
   * @throws NavigationTimeoutError if timeout exceeded
   */
  navigateTo(url: string, timeout?: number): Promise<void>;

  /**
   * Get the current page URL
   */
  getCurrentUrl(): Promise<string>;

  /**
   * Capture visible viewport as PNG
   * @returns Buffer containing PNG image data
   */
  takeScreenshot(): Promise<Buffer>;

  /**
   * Click element by CSS selector
   * @param selector - CSS selector
   * @throws ElementNotFoundError if selector not found
   */
  click(selector: string): Promise<void>;

  /**
   * Click at specific coordinates
   * @param x - X coordinate
   * @param y - Y coordinate
   */
  clickAt(x: number, y: number): Promise<void>;

  /**
   * Type text into focused element
   * @param text - Text to type
   */
  type(text: string): Promise<void>;

  /**
   * Wait for element to appear
   * @param selector - CSS selector
   * @param timeout - Timeout in milliseconds
   * @throws ElementNotFoundError if timeout exceeded
   */
  waitForSelector(selector: string, timeout?: number): Promise<void>;

  /**
   * Wait for text to appear on page
   * @param text - Text to wait for
   * @param timeout - Timeout in milliseconds
   * @returns true if found, false if timeout
   */
  waitForText(text: string, timeout?: number): Promise<boolean>;
}
