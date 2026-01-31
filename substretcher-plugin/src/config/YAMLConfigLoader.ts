import { readFile, readdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parse as parseYAML } from 'yaml';
import type { ConfigLoader } from './ConfigLoader.js';
import type { ServiceConfig } from '../types/index.js';
import { parseServiceConfig, safeParseServiceConfig } from './schema.js';

const __dirname = dirname(fileURLToPath(import.meta.url));

/**
 * Loads service configurations from YAML files
 */
export class YAMLConfigLoader implements ConfigLoader {
  private readonly configDirs: string[];
  private cache: Map<string, ServiceConfig> = new Map();

  constructor(additionalPaths?: string[]) {
    this.configDirs = [
      // Project services directory (relative to dist)
      join(__dirname, '../../services'),
      // User custom services
      join(homedir(), '.substretcher', 'services'),
      // Additional paths provided
      ...(additionalPaths ?? []),
    ];
  }

  /**
   * Load a single service by ID
   */
  async loadService(serviceId: string): Promise<ServiceConfig> {
    // Check cache first
    const cached = this.cache.get(serviceId);
    if (cached) {
      return cached;
    }

    // Search all config directories
    for (const dir of this.configDirs) {
      const filePath = join(dir, `${serviceId}.yaml`);
      if (existsSync(filePath)) {
        const config = await this.loadYAML(filePath);
        const validated = parseServiceConfig(config);
        this.cache.set(serviceId, validated);
        return validated;
      }

      // Also check .yml extension
      const ymlPath = join(dir, `${serviceId}.yml`);
      if (existsSync(ymlPath)) {
        const config = await this.loadYAML(ymlPath);
        const validated = parseServiceConfig(config);
        this.cache.set(serviceId, validated);
        return validated;
      }
    }

    throw new Error(`Service configuration not found: ${serviceId}`);
  }

  /**
   * Load all available service configurations
   */
  async loadAllServices(): Promise<ServiceConfig[]> {
    const services: ServiceConfig[] = [];
    const seenIds = new Set<string>();

    for (const dir of this.configDirs) {
      if (!existsSync(dir)) {
        continue;
      }

      try {
        const files = await readdir(dir);
        const yamlFiles = files.filter(
          (f) => f.endsWith('.yaml') || f.endsWith('.yml')
        );

        for (const file of yamlFiles) {
          const filePath = join(dir, file);
          try {
            const config = await this.loadYAML(filePath);
            const validated = safeParseServiceConfig(config);

            if (validated && !seenIds.has(validated.id)) {
              services.push(validated);
              seenIds.add(validated.id);
              this.cache.set(validated.id, validated);
            }
          } catch (err) {
            // Skip invalid configs, log warning
            console.warn(`Warning: Invalid config ${file}: ${err}`);
          }
        }
      } catch {
        // Directory doesn't exist or can't be read
        continue;
      }
    }

    return services;
  }

  /**
   * List all available service IDs
   */
  async listServiceIds(): Promise<string[]> {
    const services = await this.loadAllServices();
    return services.map((s) => s.id);
  }

  /**
   * Get the configuration search paths
   */
  getConfigPaths(): string[] {
    return [...this.configDirs];
  }

  /**
   * Load and parse a YAML file
   */
  private async loadYAML(path: string): Promise<unknown> {
    const content = await readFile(path, 'utf-8');
    return parseYAML(content);
  }
}
