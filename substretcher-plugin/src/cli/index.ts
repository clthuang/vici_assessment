#!/usr/bin/env node

import { Command } from 'commander';
import { scanCommand, cancelCommand, listCommand, statusCommand } from './commands/index.js';

const program = new Command();

program
  .name('substretcher')
  .description('Subscription billing extraction and auto-cancel tool')
  .version('0.1.0');

// Scan command
program
  .command('scan [services...]')
  .description('Extract billing info from specified services')
  .option('--all', 'Scan all configured services')
  .option('-o, --output <file>', 'Export results to file (JSON/CSV)')
  .option('-v, --verbose', 'Show detailed progress')
  .option('--timeout <ms>', 'Page load timeout in milliseconds', '30000')
  .option('--fresh', 'Ignore resume state, start fresh')
  .action(async (services: string[], options) => {
    await scanCommand(services, {
      ...options,
      timeout: parseInt(options.timeout, 10),
    });
  });

// Cancel command
program
  .command('cancel <service>')
  .description('Cancel subscription for specified service')
  .option('--confirm', 'Skip confirmation prompt')
  .option('-v, --verbose', 'Show detailed progress')
  .option('--timeout <ms>', 'Page load timeout in milliseconds', '30000')
  .action(async (service: string, options) => {
    await cancelCommand(service, {
      ...options,
      timeout: parseInt(options.timeout, 10),
    });
  });

// List command
program
  .command('list')
  .description('List available service configurations')
  .action(async () => {
    await listCommand();
  });

// Status command
program
  .command('status')
  .description('Show connection status to Chrome')
  .action(async () => {
    await statusCommand();
  });

// Handle SIGINT for graceful shutdown
process.on('SIGINT', () => {
  console.log('\n\nInterrupted. Exiting...');
  process.exit(0);
});

// Parse arguments and run
program.parse();
