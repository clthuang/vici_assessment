import { readFile, writeFile, unlink, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import { homedir } from 'node:os';
import { join, dirname } from 'node:path';
import { v4 as uuidv4 } from 'uuid';
import type { ResumeState, BillingInfo } from '../types/index.js';

/**
 * Manages scan resume state persistence
 */
export class ResumeManager {
  private readonly statePath: string;

  constructor(statePath?: string) {
    this.statePath =
      statePath ?? join(homedir(), '.substretcher', 'resume-state.json');
  }

  /**
   * Load resume state from disk
   * @returns ResumeState or null if not exists
   */
  async loadState(): Promise<ResumeState | null> {
    if (!existsSync(this.statePath)) {
      return null;
    }

    try {
      const content = await readFile(this.statePath, 'utf-8');
      return JSON.parse(content) as ResumeState;
    } catch {
      return null;
    }
  }

  /**
   * Save resume state to disk
   */
  async saveState(state: ResumeState): Promise<void> {
    // Ensure directory exists
    const dir = dirname(this.statePath);
    if (!existsSync(dir)) {
      await mkdir(dir, { recursive: true });
    }

    const content = JSON.stringify(state, null, 2);
    await writeFile(this.statePath, content, 'utf-8');
  }

  /**
   * Clear resume state (delete file)
   */
  async clearState(): Promise<void> {
    if (existsSync(this.statePath)) {
      await unlink(this.statePath);
    }
  }

  /**
   * Check if a service has been completed
   */
  isServiceCompleted(state: ResumeState, serviceId: string): boolean {
    return state.completed.includes(serviceId);
  }

  /**
   * Update state with a new result
   */
  updateWithResult(state: ResumeState, result: BillingInfo): ResumeState {
    return {
      ...state,
      completed: [...state.completed, result.serviceId],
      results: [...state.results, result],
      lastUpdated: new Date().toISOString(),
    };
  }

  /**
   * Create a new resume state
   */
  createState(services: string[]): ResumeState {
    return {
      scanId: uuidv4(),
      startedAt: new Date().toISOString(),
      services,
      completed: [],
      results: [],
      lastUpdated: new Date().toISOString(),
    };
  }

  /**
   * Get the state file path
   */
  getStatePath(): string {
    return this.statePath;
  }
}
