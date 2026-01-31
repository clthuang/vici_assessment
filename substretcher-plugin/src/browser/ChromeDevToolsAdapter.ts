import CDP from 'chrome-remote-interface';
import type { BrowserAdapter } from './BrowserAdapter.js';
import {
  ChromeNotRunningError,
  ConnectionLostError,
  NavigationTimeoutError,
  ElementNotFoundError,
} from './errors.js';

type CDPClient = Awaited<ReturnType<typeof CDP>>;

/**
 * Browser adapter using Chrome DevTools Protocol
 */
export class ChromeDevToolsAdapter implements BrowserAdapter {
  private client: CDPClient | null = null;
  private port: number = 9222;

  /**
   * Connect to Chrome via CDP
   */
  async connect(port: number = 9222): Promise<void> {
    this.port = port;

    try {
      this.client = await CDP({ port });

      // Enable required domains
      const { Page, Runtime, DOM, Network } = this.client;
      await Promise.all([
        Page.enable(),
        Runtime.enable(),
        DOM.enable(),
        Network.enable(),
      ]);

      // Handle disconnection
      this.client.on('disconnect', () => {
        this.client = null;
      });
    } catch (err) {
      if (
        err instanceof Error &&
        (err.message.includes('ECONNREFUSED') ||
          err.message.includes('connect'))
      ) {
        throw new ChromeNotRunningError(port);
      }
      throw err;
    }
  }

  /**
   * Disconnect from Chrome
   */
  async disconnect(): Promise<void> {
    if (this.client) {
      await this.client.close();
      this.client = null;
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.client !== null;
  }

  /**
   * Navigate to URL
   */
  async navigateTo(url: string, timeout: number = 30000): Promise<void> {
    this.ensureConnected();

    const { Page } = this.client!;

    const navigationPromise = new Promise<void>((resolve, reject) => {
      const timer = setTimeout(() => {
        reject(new NavigationTimeoutError(url, timeout));
      }, timeout);

      Page.loadEventFired().then(() => {
        clearTimeout(timer);
        resolve();
      });
    });

    await Page.navigate({ url });
    await navigationPromise;
  }

  /**
   * Get current URL
   */
  async getCurrentUrl(): Promise<string> {
    this.ensureConnected();

    const { Runtime } = this.client!;
    const result = await Runtime.evaluate({
      expression: 'window.location.href',
    });

    return result.result.value as string;
  }

  /**
   * Take screenshot
   */
  async takeScreenshot(): Promise<Buffer> {
    this.ensureConnected();

    const { Page } = this.client!;
    const { data } = await Page.captureScreenshot({ format: 'png' });

    return Buffer.from(data, 'base64');
  }

  /**
   * Click element by selector
   */
  async click(selector: string): Promise<void> {
    this.ensureConnected();

    const { DOM } = this.client!;

    // Get document
    const { root } = await DOM.getDocument();

    // Find element
    const { nodeId } = await DOM.querySelector({
      nodeId: root.nodeId,
      selector,
    });

    if (!nodeId) {
      throw new ElementNotFoundError(selector);
    }

    // Get element position
    const { model } = await DOM.getBoxModel({ nodeId });
    if (!model) {
      throw new ElementNotFoundError(selector);
    }

    // Calculate center point
    const x = (model.content[0] + model.content[2]) / 2;
    const y = (model.content[1] + model.content[5]) / 2;

    // Click at center
    await this.clickAt(x, y);
  }

  /**
   * Click at coordinates
   */
  async clickAt(x: number, y: number): Promise<void> {
    this.ensureConnected();

    const { Input } = this.client!;

    await Input.dispatchMouseEvent({
      type: 'mousePressed',
      x,
      y,
      button: 'left',
      clickCount: 1,
    });

    await Input.dispatchMouseEvent({
      type: 'mouseReleased',
      x,
      y,
      button: 'left',
      clickCount: 1,
    });
  }

  /**
   * Type text
   */
  async type(text: string): Promise<void> {
    this.ensureConnected();

    const { Input } = this.client!;

    for (const char of text) {
      await Input.dispatchKeyEvent({
        type: 'keyDown',
        text: char,
      });
      await Input.dispatchKeyEvent({
        type: 'keyUp',
        text: char,
      });
    }
  }

  /**
   * Wait for selector
   */
  async waitForSelector(
    selector: string,
    timeout: number = 10000
  ): Promise<void> {
    this.ensureConnected();

    const startTime = Date.now();
    const { DOM } = this.client!;

    while (Date.now() - startTime < timeout) {
      const { root } = await DOM.getDocument();
      const { nodeId } = await DOM.querySelector({
        nodeId: root.nodeId,
        selector,
      });

      if (nodeId) {
        return;
      }

      await this.sleep(100);
    }

    throw new ElementNotFoundError(selector);
  }

  /**
   * Wait for text on page
   */
  async waitForText(text: string, timeout: number = 10000): Promise<boolean> {
    this.ensureConnected();

    const startTime = Date.now();
    const { Runtime } = this.client!;

    while (Date.now() - startTime < timeout) {
      const result = await Runtime.evaluate({
        expression: `document.body.innerText.includes(${JSON.stringify(text)})`,
      });

      if (result.result.value === true) {
        return true;
      }

      await this.sleep(100);
    }

    return false;
  }

  /**
   * Ensure client is connected
   */
  private ensureConnected(): void {
    if (!this.client) {
      throw new ConnectionLostError();
    }
  }

  /**
   * Sleep for given milliseconds
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
