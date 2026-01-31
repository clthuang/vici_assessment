/**
 * Type declarations for chrome-remote-interface
 * Minimal types for our CDP usage
 */
declare module 'chrome-remote-interface' {
  interface CDPOptions {
    host?: string;
    port?: number;
    target?: string;
  }

  interface CDPClient {
    Page: {
      enable(): Promise<void>;
      navigate(params: { url: string }): Promise<{ frameId: string }>;
      captureScreenshot(params?: { format?: string }): Promise<{ data: string }>;
      loadEventFired(): Promise<void>;
    };
    Runtime: {
      enable(): Promise<void>;
      evaluate(params: {
        expression: string;
        returnByValue?: boolean;
      }): Promise<{ result: { value?: unknown } }>;
    };
    Input: {
      dispatchMouseEvent(params: {
        type: string;
        x: number;
        y: number;
        button?: string;
        clickCount?: number;
      }): Promise<void>;
      insertText(params: { text: string }): Promise<void>;
      dispatchKeyEvent(params: {
        type: string;
        key?: string;
        code?: string;
        text?: string;
      }): Promise<void>;
    };
    DOM: {
      enable(): Promise<void>;
      getDocument(): Promise<{ root: { nodeId: number } }>;
      querySelector(params: { nodeId: number; selector: string }): Promise<{ nodeId: number }>;
      getBoxModel(params: { nodeId: number }): Promise<{
        model: {
          content: number[];
          padding: number[];
          border: number[];
          margin: number[];
          width: number;
          height: number;
        };
      }>;
    };
    Network: {
      enable(): Promise<void>;
    };
    close(): Promise<void>;
    on(event: string, handler: (...args: unknown[]) => void): void;
  }

  function CDP(options?: CDPOptions): Promise<CDPClient>;
  export = CDP;
}
