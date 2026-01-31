import type { ServiceConfig } from '../types/index.js';

/**
 * Interface for loading service configurations
 */
export interface ConfigLoader {
  /**
   * Load single service by ID
   * @throws ServiceNotFoundError if not found
   * @throws ConfigValidationError if invalid
   */
  loadService(serviceId: string): Promise<ServiceConfig>;

  /**
   * Load all available services
   * Skips invalid configs (logs warning)
   */
  loadAllServices(): Promise<ServiceConfig[]>;

  /**
   * List all service IDs
   */
  listServiceIds(): Promise<string[]>;

  /**
   * Get paths being searched for configs
   */
  getConfigPaths(): string[];
}
