/**
 * A navigation step to reach a billing page
 */
export interface NavigationStep {
  description: string; // Human-readable description for AI fallback
  selector?: string; // CSS selector (optional - AI can find element)
  action?: 'click' | 'hover' | 'wait'; // Default: 'click'
  waitAfter?: number; // ms to wait after action (default: 1000)
}

/**
 * A step in a cancellation workflow
 */
export interface CancellationStep {
  action: 'click' | 'type' | 'select' | 'wait';
  description: string; // Human-readable for AI guidance
  selector?: string; // CSS selector (optional)
  value?: string; // For 'type' or 'select' actions
  waitAfter?: number; // ms to wait after action
  requiresConfirmation?: boolean; // Pause and ask user before this step
}

/**
 * Configuration for a subscription service
 */
export interface ServiceConfig {
  id: string;
  name: string;
  domain: string;
  billingUrl: string;
  navigation?: {
    steps: NavigationStep[];
  };
  extraction?: {
    status?: { selector: string };
    renewalDate?: { selector: string };
    cost?: { selector: string };
  };
  cancellation?: {
    enabled: boolean;
    steps: CancellationStep[];
    successIndicator: {
      text?: string;
      selector?: string;
    };
  };
}
