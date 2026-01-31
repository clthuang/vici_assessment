import chalk from 'chalk';
import { CancelOrchestrator } from '../../orchestrator/CancelOrchestrator.js';
import { ChromeDevToolsAdapter } from '../../browser/ChromeDevToolsAdapter.js';
import { ClaudeAIExtractor } from '../../ai/ClaudeAIExtractor.js';
import { YAMLConfigLoader } from '../../config/YAMLConfigLoader.js';
import { AuditLogger } from '../../infra/AuditLogger.js';
import { ErrorHandler } from '../../infra/ErrorHandler.js';
import type { CancelOptions } from '../../types/index.js';

interface CancelCommandOptions extends CancelOptions {
  confirm?: boolean;
}

/**
 * Handle the cancel command
 */
export async function cancelCommand(
  service: string,
  options: CancelCommandOptions
): Promise<void> {
  const errorHandler = new ErrorHandler();

  try {
    // Create dependencies
    const browser = new ChromeDevToolsAdapter();
    const ai = new ClaudeAIExtractor();
    const config = new YAMLConfigLoader();
    const audit = new AuditLogger();

    // Create orchestrator
    const orchestrator = new CancelOrchestrator({
      browserAdapter: browser,
      aiExtractor: ai,
      configLoader: config,
      auditLogger: audit,
    });

    // Run cancellation
    console.log(chalk.blue(`\nInitiating cancellation for ${service}...\n`));

    const result = await orchestrator.cancel(service, {
      confirm: options.confirm,
      verbose: options.verbose,
      timeout: options.timeout,
    });

    // Display result
    if (result.success) {
      console.log(chalk.green('\n✓ ' + result.message));
      if (result.endDate) {
        console.log(chalk.yellow(`  Access ends: ${result.endDate}`));
      }
    } else {
      console.log(chalk.red('\n✗ ' + result.message));
    }
  } catch (err) {
    const classified = errorHandler.classify(err as Error);
    console.error(chalk.red('\n' + errorHandler.formatForUser(classified)));
    process.exit(1);
  }
}
