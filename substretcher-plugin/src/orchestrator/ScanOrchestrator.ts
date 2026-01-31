import * as readline from 'node:readline';
import type { BrowserAdapter } from '../browser/BrowserAdapter.js';
import type { AIExtractor } from '../ai/AIExtractor.js';
import type { ConfigLoader } from '../config/ConfigLoader.js';
import type { AuditLogger } from '../infra/AuditLogger.js';
import type { ResumeManager } from './ResumeManager.js';
import type {
  BillingInfo,
  ScanResult,
  ScanOptions,
  ServiceConfig,
  ResumeState,
} from '../types/index.js';

export interface ScanOrchestratorDeps {
  browserAdapter: BrowserAdapter;
  aiExtractor: AIExtractor;
  configLoader: ConfigLoader;
  resumeManager: ResumeManager;
  auditLogger: AuditLogger;
}

/**
 * Orchestrates multi-service scanning with resume support
 */
export class ScanOrchestrator {
  private browser: BrowserAdapter;
  private ai: AIExtractor;
  private config: ConfigLoader;
  private resume: ResumeManager;
  private audit: AuditLogger;

  constructor(deps: ScanOrchestratorDeps) {
    this.browser = deps.browserAdapter;
    this.ai = deps.aiExtractor;
    this.config = deps.configLoader;
    this.resume = deps.resumeManager;
    this.audit = deps.auditLogger;
  }

  /**
   * Scan multiple services
   */
  async scan(serviceIds: string[], options: ScanOptions = {}): Promise<ScanResult> {
    const results: BillingInfo[] = [];
    let state: ResumeState | null = null;

    // Load or create resume state
    if (!options.fresh) {
      state = await this.resume.loadState();
    }

    if (!state) {
      state = this.resume.createState(serviceIds);
    }

    // Connect to browser
    await this.browser.connect();

    try {
      for (const serviceId of serviceIds) {
        // Skip if already completed
        if (this.resume.isServiceCompleted(state, serviceId)) {
          if (options.verbose) {
            console.log(`Skipping ${serviceId} (already completed)`);
          }
          continue;
        }

        // Log scan start
        await this.audit.log('scan_start', serviceId, `Starting scan for ${serviceId}`, true);

        try {
          // Load service config
          const config = await this.config.loadService(serviceId);

          // Scan the service
          const result = await this.scanService(config, options);
          results.push(result);

          // Update resume state
          state = this.resume.updateWithResult(state, result);
          await this.resume.saveState(state);

          // Log scan complete
          await this.audit.log(
            'scan_complete',
            serviceId,
            `Completed scan for ${serviceId} (confidence: ${result.confidence})`,
            true
          );
        } catch (err) {
          // Create error result
          const errorResult: BillingInfo = {
            serviceId,
            serviceName: serviceId,
            status: 'unknown',
            renewalDate: null,
            cost: null,
            paymentMethod: null,
            confidence: 0,
            extractedAt: new Date().toISOString(),
            errors: [err instanceof Error ? err.message : String(err)],
          };
          results.push(errorResult);

          // Log but continue to next service
          await this.audit.log(
            'scan_complete',
            serviceId,
            `Failed to scan ${serviceId}: ${err}`,
            false
          );
        }
      }

      // Clear resume state on successful completion
      await this.resume.clearState();
    } finally {
      // Always disconnect
      await this.browser.disconnect();
    }

    // Combine with any previous results
    const allResults = [...(state?.results ?? []).filter(
      r => !results.some(nr => nr.serviceId === r.serviceId)
    ), ...results];

    return this.aggregateResults(allResults);
  }

  /**
   * Scan a single service
   */
  private async scanService(
    config: ServiceConfig,
    options: ScanOptions
  ): Promise<BillingInfo> {
    // Navigate to billing page
    await this.browser.navigateTo(config.billingUrl, options.timeout);

    // Wait for page to settle
    await this.sleep(2000);

    // Take screenshot
    const screenshot = await this.browser.takeScreenshot();

    // Check if logged in
    const authCheck = await this.ai.isLoggedIn(screenshot, config.name);

    if (!authCheck.loggedIn && authCheck.confidence > 0.7) {
      // Handle login wall
      const loggedIn = await this.handleLoginWall(config);
      if (!loggedIn) {
        await this.audit.log(
          'user_skip',
          config.id,
          `User skipped ${config.name} (login required)`,
          true
        );

        return {
          serviceId: config.id,
          serviceName: config.name,
          status: 'unknown',
          renewalDate: null,
          cost: null,
          paymentMethod: null,
          confidence: 0,
          extractedAt: new Date().toISOString(),
          errors: ['Login required - user skipped'],
        };
      }

      // Take new screenshot after login
      const newScreenshot = await this.browser.takeScreenshot();
      return await this.ai.extractBillingInfo(newScreenshot, config);
    }

    // Extract billing info
    return await this.ai.extractBillingInfo(screenshot, config);
  }

  /**
   * Handle login wall - prompt user to log in
   */
  private async handleLoginWall(config: ServiceConfig): Promise<boolean> {
    await this.audit.log(
      'login_prompt',
      config.id,
      `Login required for ${config.name}`,
      true
    );

    console.log(`\n⚠️  Login required for ${config.name}`);
    console.log(`Please log in to ${config.name} in the browser window.`);
    console.log(`Press Enter when done, or type 'q' to skip this service.\n`);

    const input = await this.promptUser('> ');

    if (input.toLowerCase() === 'q') {
      return false;
    }

    // Wait for user to complete login
    await this.sleep(2000);

    // Verify login
    const screenshot = await this.browser.takeScreenshot();
    const authCheck = await this.ai.isLoggedIn(screenshot, config.name);

    if (!authCheck.loggedIn || authCheck.confidence < 0.7) {
      console.log(`Still not logged in. Skipping ${config.name}.`);
      return false;
    }

    return true;
  }

  /**
   * Aggregate results into ScanResult
   */
  private aggregateResults(results: BillingInfo[]): ScanResult {
    const successful = results.filter(
      (r) => r.errors.length === 0 && r.confidence > 0.5
    );
    const failed = results.filter(
      (r) => r.errors.length > 0 || r.confidence <= 0.5
    );

    // Calculate total monthly cost
    let totalMonthlyCost = 0;
    let currency = 'USD';

    for (const result of successful) {
      if (result.cost && result.status === 'active') {
        let monthlyCost = result.cost.amount;

        // Normalize to monthly
        if (result.cost.cycle === 'annual') {
          monthlyCost = monthlyCost / 12;
        } else if (result.cost.cycle === 'weekly') {
          monthlyCost = monthlyCost * 4;
        }

        totalMonthlyCost += monthlyCost;
        currency = result.cost.currency;
      }
    }

    return {
      scannedAt: new Date().toISOString(),
      services: results,
      summary: {
        total: results.length,
        successful: successful.length,
        failed: failed.length,
        skipped: 0,
        totalMonthlyCost: Math.round(totalMonthlyCost * 100) / 100,
        currency,
      },
    };
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
