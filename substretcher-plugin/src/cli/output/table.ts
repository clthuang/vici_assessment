import Table from 'cli-table3';
import chalk from 'chalk';
import type { BillingInfo, ScanResult } from '../../types/index.js';

/**
 * Format billing info as a table row
 */
function formatBillingRow(billing: BillingInfo): string[] {
  const statusColor =
    billing.status === 'active'
      ? chalk.green
      : billing.status === 'cancelled'
        ? chalk.red
        : chalk.yellow;

  const costStr = billing.cost
    ? `${billing.cost.currency} ${billing.cost.amount}/${billing.cost.cycle}`
    : '-';

  const confidenceStr =
    billing.confidence >= 0.8
      ? chalk.green(`${Math.round(billing.confidence * 100)}%`)
      : billing.confidence >= 0.5
        ? chalk.yellow(`${Math.round(billing.confidence * 100)}%`)
        : chalk.red(`${Math.round(billing.confidence * 100)}%`);

  return [
    billing.serviceName,
    statusColor(billing.status),
    billing.renewalDate ?? '-',
    costStr,
    billing.paymentMethod ?? '-',
    confidenceStr,
  ];
}

/**
 * Format billing results as a table
 */
export function formatBillingTable(services: BillingInfo[]): string {
  const table = new Table({
    head: [
      chalk.bold('Service'),
      chalk.bold('Status'),
      chalk.bold('Renewal'),
      chalk.bold('Cost'),
      chalk.bold('Payment'),
      chalk.bold('Conf'),
    ],
    style: {
      head: [],
      border: [],
    },
  });

  for (const billing of services) {
    table.push(formatBillingRow(billing));
  }

  return table.toString();
}

/**
 * Format scan summary
 */
export function formatSummary(result: ScanResult): string {
  const lines: string[] = [];

  lines.push('');
  lines.push(chalk.bold('Summary:'));
  lines.push(`  Total services: ${result.summary.total}`);
  lines.push(`  Successful: ${chalk.green(result.summary.successful)}`);
  lines.push(`  Failed: ${chalk.red(result.summary.failed)}`);

  if (result.summary.skipped > 0) {
    lines.push(`  Skipped: ${chalk.yellow(result.summary.skipped)}`);
  }

  if (result.summary.totalMonthlyCost > 0) {
    lines.push('');
    lines.push(
      chalk.bold(
        `  Total monthly cost: ${result.summary.currency} ${result.summary.totalMonthlyCost}`
      )
    );
  }

  return lines.join('\n');
}

/**
 * Format service list
 */
export function formatServiceList(services: Array<{ id: string; name: string; domain: string }>): string {
  const table = new Table({
    head: [chalk.bold('ID'), chalk.bold('Name'), chalk.bold('Domain')],
    style: {
      head: [],
      border: [],
    },
  });

  for (const service of services) {
    table.push([service.id, service.name, service.domain]);
  }

  return table.toString();
}
