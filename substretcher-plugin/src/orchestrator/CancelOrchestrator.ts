import * as readline from 'node:readline';
import type { BrowserAdapter } from '../browser/BrowserAdapter.js';
import type { AIExtractor } from '../ai/AIExtractor.js';
import type { ConfigLoader } from '../config/ConfigLoader.js';
import type { AuditLogger } from '../infra/AuditLogger.js';
import { ScanOrchestrator, type ScanOrchestratorDeps } from './ScanOrchestrator.js';
import { ResumeManager } from './ResumeManager.js';
import type {
  BillingInfo,
  CancelResult,
  CancelOptions,
  ServiceConfig,
  CancellationStep,
} from '../types/index.js';

export interface CancelOrchestratorDeps {
  browserAdapter: BrowserAdapter;
  aiExtractor: AIExtractor;
  configLoader: ConfigLoader;
  auditLogger: AuditLogger;
}

/**
 * Orchestrates subscription cancellation workflows
 */
export class CancelOrchestrator {
  private browser: BrowserAdapter;
  private ai: AIExtractor;
  private config: ConfigLoader;
  private audit: AuditLogger;

  constructor(deps: CancelOrchestratorDeps) {
    this.browser = deps.browserAdapter;
    this.ai = deps.aiExtractor;
    this.config = deps.configLoader;
    this.audit = deps.auditLogger;
  }

  /**
   * Cancel a subscription
   */
  async cancel(serviceId: string, options: CancelOptions = {}): Promise<CancelResult> {
    // Load service config
    const config = await this.config.loadService(serviceId);

    if (!config.cancellation?.enabled) {
      return {
        serviceId,
        serviceName: config.name,
        success: false,
        message: `Cancellation not supported for ${config.name}`,
        endDate: null,
        cancelledAt: new Date().toISOString(),
      };
    }

    // First, scan to get current billing info
    const scanDeps: ScanOrchestratorDeps = {
      browserAdapter: this.browser,
      aiExtractor: this.ai,
      configLoader: this.config,
      resumeManager: new ResumeManager(),
      auditLogger: this.audit,
    };

    const scanner = new ScanOrchestrator(scanDeps);
    const scanResult = await scanner.scan([serviceId], { fresh: true });
    const billing = scanResult.services[0];

    if (!billing || billing.status === 'cancelled') {
      return {
        serviceId,
        serviceName: config.name,
        success: false,
        message: billing?.status === 'cancelled'
          ? 'Subscription is already cancelled'
          : 'Could not retrieve billing information',
        endDate: null,
        cancelledAt: new Date().toISOString(),
      };
    }

    // Show pre-cancel summary
    await this.showPreCancelSummary(billing);

    // Confirm cancellation
    if (!options.confirm) {
      const confirmed = await this.confirmCancellation();
      if (!confirmed) {
        return {
          serviceId,
          serviceName: config.name,
          success: false,
          message: 'Cancellation aborted by user',
          endDate: null,
          cancelledAt: new Date().toISOString(),
        };
      }
    }

    // Log cancel start
    await this.audit.log(
      'cancel_start',
      serviceId,
      `Starting cancellation for ${config.name}`,
      true
    );

    // Connect to browser (scanner disconnected)
    await this.browser.connect();

    try {
      // Navigate back to billing page
      await this.browser.navigateTo(config.billingUrl);
      await this.sleep(2000);

      // Execute cancellation steps
      const success = await this.executeCancellationSteps(config);

      if (success) {
        // Verify success
        const verified = await this.verifySuccess(config);

        await this.audit.log(
          verified ? 'cancel_complete' : 'cancel_failed',
          serviceId,
          verified
            ? `Successfully cancelled ${config.name}`
            : `Cancellation completed but could not verify`,
          verified
        );

        return {
          serviceId,
          serviceName: config.name,
          success: verified,
          message: verified
            ? 'Subscription cancelled successfully'
            : 'Cancellation steps completed but could not verify success',
          endDate: billing.renewalDate,
          cancelledAt: new Date().toISOString(),
        };
      } else {
        await this.audit.log(
          'cancel_failed',
          serviceId,
          `Failed to execute cancellation steps for ${config.name}`,
          false
        );

        return {
          serviceId,
          serviceName: config.name,
          success: false,
          message: 'Failed to complete cancellation steps',
          endDate: null,
          cancelledAt: new Date().toISOString(),
        };
      }
    } finally {
      await this.browser.disconnect();
    }
  }

  /**
   * Show pre-cancellation summary
   */
  private async showPreCancelSummary(billing: BillingInfo): Promise<void> {
    console.log('\n╔════════════════════════════════════════╗');
    console.log('║        CANCELLATION SUMMARY            ║');
    console.log('╠════════════════════════════════════════╣');
    console.log(`║ Service: ${billing.serviceName.padEnd(28)} ║`);
    console.log(`║ Status:  ${billing.status.padEnd(28)} ║`);

    if (billing.cost) {
      const costStr = `${billing.cost.currency} ${billing.cost.amount}/${billing.cost.cycle}`;
      console.log(`║ Cost:    ${costStr.padEnd(28)} ║`);
    }

    if (billing.renewalDate) {
      console.log(`║ Ends on: ${billing.renewalDate.padEnd(28)} ║`);
    }

    console.log('╚════════════════════════════════════════╝');
    console.log('\n⚠️  This action cannot be undone!');
  }

  /**
   * Prompt user for cancellation confirmation
   */
  private async confirmCancellation(): Promise<boolean> {
    const input = await this.promptUser(
      '\nType "yes" to confirm cancellation: '
    );
    return input.toLowerCase() === 'yes';
  }

  /**
   * Execute cancellation steps
   */
  private async executeCancellationSteps(config: ServiceConfig): Promise<boolean> {
    const steps = config.cancellation!.steps;

    for (let i = 0; i < steps.length; i++) {
      const step = steps[i];

      // Log step
      await this.audit.log(
        'cancel_step',
        config.id,
        `Executing step ${i + 1}: ${step.description}`,
        true,
        { stepNumber: String(i + 1) }
      );

      // Check for user confirmation if required
      if (step.requiresConfirmation) {
        console.log(`\n⚠️  About to: ${step.description}`);
        const proceed = await this.promptUser('Press Enter to continue, or "q" to abort: ');
        if (proceed.toLowerCase() === 'q') {
          return false;
        }
      }

      // Execute the step
      const success = await this.executeStep(step);
      if (!success) {
        console.log(`Failed to execute step: ${step.description}`);
        return false;
      }

      // Wait after step
      const waitTime = step.waitAfter ?? 1500;
      await this.sleep(waitTime);
    }

    return true;
  }

  /**
   * Execute a single cancellation step
   */
  private async executeStep(step: CancellationStep): Promise<boolean> {
    try {
      switch (step.action) {
        case 'click':
          if (step.selector) {
            await this.browser.click(step.selector);
          } else {
            // Use AI to find element
            const screenshot = await this.browser.takeScreenshot();
            const location = await this.ai.findElement(screenshot, step.description);
            if (!location) {
              return false;
            }
            await this.browser.clickAt(location.x, location.y);
          }
          break;

        case 'type':
          if (step.value) {
            await this.browser.type(step.value);
          }
          break;

        case 'wait':
          await this.sleep(step.waitAfter ?? 1000);
          break;

        case 'select':
          // For select, we click the option with the given value
          if (step.selector && step.value) {
            await this.browser.click(`${step.selector} option[value="${step.value}"]`);
          }
          break;
      }

      return true;
    } catch (err) {
      console.error(`Step execution error: ${err}`);
      return false;
    }
  }

  /**
   * Verify cancellation success
   */
  private async verifySuccess(config: ServiceConfig): Promise<boolean> {
    const indicator = config.cancellation!.successIndicator;

    // Wait for page to update
    await this.sleep(2000);

    if (indicator.text) {
      return await this.browser.waitForText(indicator.text, 5000);
    }

    if (indicator.selector) {
      try {
        await this.browser.waitForSelector(indicator.selector, 5000);
        return true;
      } catch {
        return false;
      }
    }

    // No indicator defined, assume success
    return true;
  }

  /**
   * Prompt user for input
   */
  private promptUser(prompt: string): Promise<string> {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout,
    });

    return new Promise((resolve) => {
      rl.question(prompt, (answer) => {
        rl.close();
        resolve(answer);
      });
    });
  }

  /**
   * Sleep for given milliseconds
   */
  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}
