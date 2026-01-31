import chalk from 'chalk';
import { YAMLConfigLoader } from '../../config/YAMLConfigLoader.js';
import { formatServiceList, createSpinner } from '../output/index.js';

/**
 * Handle the list command
 */
export async function listCommand(): Promise<void> {
  const spinner = createSpinner('Loading service configurations...');
  spinner.start();

  try {
    const config = new YAMLConfigLoader();
    const services = await config.loadAllServices();

    spinner.succeed(`Found ${services.length} service(s)`);

    if (services.length === 0) {
      console.log(chalk.yellow('\nNo service configurations found.'));
      console.log('Add YAML files to ./services/ or ~/.substretcher/services/');
      return;
    }

    const serviceInfo = services.map((s) => ({
      id: s.id,
      name: s.name,
      domain: s.domain,
    }));

    console.log('\n' + formatServiceList(serviceInfo));

    console.log(chalk.dim('\nConfig paths searched:'));
    for (const path of config.getConfigPaths()) {
      console.log(chalk.dim(`  - ${path}`));
    }
  } catch (err) {
    spinner.fail('Failed to load configurations');
    console.error(chalk.red(`Error: ${err}`));
    process.exit(1);
  }
}
