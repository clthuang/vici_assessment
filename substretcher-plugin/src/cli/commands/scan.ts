import chalk from 'chalk';
import { ScanOrchestrator } from '../../orchestrator/ScanOrchestrator.js';
import { ResumeManager } from '../../orchestrator/ResumeManager.js';
import { ChromeDevToolsAdapter } from '../../browser/ChromeDevToolsAdapter.js';
import { ClaudeAIExtractor } from '../../ai/ClaudeAIExtractor.js';
import { YAMLConfigLoader } from '../../config/YAMLConfigLoader.js';
import { AuditLogger } from '../../infra/AuditLogger.js';
import { FileExporter } from '../../infra/FileExporter.js';
import { ErrorHandler } from '../../infra/ErrorHandler.js';
import { formatBillingTable, formatSummary, createSpinner } from '../output/index.js';
import type { ScanOptions } from '../../types/index.js';

interface ScanCommandOptions extends ScanOptions {
  output?: string;
  all?: boolean;
}

/**
 * Handle the scan command
 */
export async function scanCommand(
  services: string[],
  options: ScanCommandOptions
): Promise<void> {
  const errorHandler = new ErrorHandler();

  try {
    // Create dependencies
    const browser = new ChromeDevToolsAdapter();
    const ai = new ClaudeAIExtractor();
    const config = new YAMLConfigLoader();
    const resume = new ResumeManager();
    const audit = new AuditLogger();

    // Determine which services to scan
    let serviceIds = services;

    if (options.all) {
      const spinner = createSpinner('Loading service configurations...');
      spinner.start();

      serviceIds = await config.listServiceIds();
      spinner.succeed(`Found ${serviceIds.length} services`);
    }

    if (serviceIds.length === 0) {
      console.error(chalk.red('No services specified. Use --all or provide service names.'));
      process.exit(1);
    }

    // Create orchestrator
    const orchestrator = new ScanOrchestrator({
      browserAdapter: browser,
      aiExtractor: ai,
      configLoader: config,
      resumeManager: resume,
      auditLogger: audit,
    });

    // Run scan
    console.log(chalk.blue(`\nScanning ${serviceIds.length} service(s)...\n`));

    const result = await orchestrator.scan(serviceIds, {
      verbose: options.verbose,
      timeout: options.timeout,
      fresh: options.fresh,
    });

    // Display results
    console.log('\n' + formatBillingTable(result.services));
    console.log(formatSummary(result));

    // Export if requested
    if (options.output) {
      const exporter = new FileExporter();

      if (options.output.endsWith('.csv')) {
        await exporter.exportCSV(result, options.output);
      } else {
        await exporter.exportJSON(result, options.output);
      }

      console.log(chalk.green(`\nResults exported to ${options.output}`));
    }
  } catch (err) {
    const classified = errorHandler.classify(err as Error);
    console.error(chalk.red('\n' + errorHandler.formatForUser(classified)));
    process.exit(1);
  }
}
