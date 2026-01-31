import ora, { type Ora } from 'ora';

/**
 * Create a spinner with the given text
 */
export function createSpinner(text: string): Ora {
  return ora({
    text,
    spinner: 'dots',
  });
}
