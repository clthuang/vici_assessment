import chalk from 'chalk';
import { ChromeDevToolsAdapter } from '../../browser/ChromeDevToolsAdapter.js';
import { createSpinner } from '../output/index.js';

/**
 * Handle the status command
 */
export async function statusCommand(): Promise<void> {
  const spinner = createSpinner('Checking Chrome connection...');
  spinner.start();

  const browser = new ChromeDevToolsAdapter();

  try {
    await browser.connect();
    spinner.succeed('Connected to Chrome');

    // Get current URL
    const url = await browser.getCurrentUrl();
    console.log(chalk.dim(`  Current URL: ${url}`));

    await browser.disconnect();
    console.log(chalk.green('\n✓ Chrome is running and accessible on port 9222'));
  } catch (err) {
    spinner.fail('Could not connect to Chrome');

    console.log(chalk.red('\n✗ Chrome is not running with debugging enabled'));
    console.log('\nTo start Chrome with debugging:');
    console.log(
      chalk.cyan(
        '  /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222'
      )
    );
    console.log(
      chalk.dim('\nOr on Linux:')
    );
    console.log(
      chalk.cyan('  google-chrome --remote-debugging-port=9222')
    );

    process.exit(1);
  }
}
