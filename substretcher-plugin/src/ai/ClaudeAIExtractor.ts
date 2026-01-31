import Anthropic from '@anthropic-ai/sdk';
import type { AIExtractor, AuthCheckResult, ElementLocation } from './AIExtractor.js';
import type { BillingInfo, ServiceConfig } from '../types/index.js';
import {
  EXTRACTION_PROMPT,
  AUTH_CHECK_PROMPT,
  ELEMENT_FIND_PROMPT,
  formatPrompt,
} from './prompts.js';

/**
 * AI extractor using Claude Vision
 */
export class ClaudeAIExtractor implements AIExtractor {
  private client: Anthropic;

  constructor(apiKey?: string) {
    this.client = new Anthropic({
      apiKey: apiKey ?? process.env.ANTHROPIC_API_KEY,
    });
  }

  /**
   * Extract billing information from screenshot
   */
  async extractBillingInfo(
    screenshot: Buffer,
    config: ServiceConfig
  ): Promise<BillingInfo> {
    const prompt = formatPrompt(EXTRACTION_PROMPT, {
      serviceName: config.name,
    });

    const response = await this.callClaudeVision(screenshot, prompt);
    const parsed = this.safeParseJSON(response);

    if (!parsed) {
      return this.createEmptyBillingInfo(config, ['Failed to parse AI response']);
    }

    // Type-safe extraction from parsed JSON
    const status = parsed.status as string | undefined;
    const validStatuses = ['active', 'cancelled', 'paused', 'trial', 'unknown'] as const;
    const normalizedStatus = validStatuses.includes(status as typeof validStatuses[number])
      ? (status as typeof validStatuses[number])
      : 'unknown';

    // Parse cost object if present
    const parsedCost = parsed.cost as { amount?: number; currency?: string; cycle?: string } | null;
    const validCycles = ['weekly', 'monthly', 'annual', 'unknown'] as const;
    const cost = parsedCost && typeof parsedCost.amount === 'number'
      ? {
          amount: parsedCost.amount,
          currency: (parsedCost.currency as string) ?? 'USD',
          cycle: validCycles.includes(parsedCost.cycle as typeof validCycles[number])
            ? (parsedCost.cycle as typeof validCycles[number])
            : 'unknown' as const,
        }
      : null;

    return {
      serviceId: config.id,
      serviceName: config.name,
      status: normalizedStatus,
      renewalDate: (parsed.renewalDate as string) ?? null,
      cost,
      paymentMethod: (parsed.paymentMethod as string) ?? null,
      confidence: (parsed.confidence as number) ?? 0,
      extractedAt: new Date().toISOString(),
      errors: [],
    };
  }

  /**
   * Check if user is logged in
   */
  async isLoggedIn(
    screenshot: Buffer,
    serviceName: string
  ): Promise<AuthCheckResult> {
    const prompt = formatPrompt(AUTH_CHECK_PROMPT, { serviceName });

    const response = await this.callClaudeVision(screenshot, prompt);
    const parsed = this.safeParseJSON(response);

    if (!parsed) {
      return {
        loggedIn: false,
        confidence: 0,
        reason: 'Failed to parse AI response',
      };
    }

    return {
      loggedIn: (parsed.loggedIn as boolean) ?? false,
      confidence: (parsed.confidence as number) ?? 0,
      reason: (parsed.reason as string) ?? 'No reason provided',
    };
  }

  /**
   * Find element by description
   */
  async findElement(
    screenshot: Buffer,
    description: string
  ): Promise<ElementLocation | null> {
    const prompt = formatPrompt(ELEMENT_FIND_PROMPT, { description });

    const response = await this.callClaudeVision(screenshot, prompt);
    const parsed = this.safeParseJSON(response);

    if (!parsed || !parsed.found) {
      return null;
    }

    return {
      x: parsed.x as number,
      y: parsed.y as number,
      width: parsed.width as number,
      height: parsed.height as number,
      confidence: (parsed.confidence as number) ?? 0,
    };
  }

  /**
   * Call Claude Vision API with screenshot
   */
  private async callClaudeVision(
    screenshot: Buffer,
    prompt: string
  ): Promise<string> {
    const base64Image = screenshot.toString('base64');

    const response = await this.client.messages.create({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 1024,
      messages: [
        {
          role: 'user',
          content: [
            {
              type: 'image',
              source: {
                type: 'base64',
                media_type: 'image/png',
                data: base64Image,
              },
            },
            {
              type: 'text',
              text: prompt,
            },
          ],
        },
      ],
    });

    // Extract text content from response
    const textContent = response.content.find((c) => c.type === 'text');
    return textContent?.type === 'text' ? textContent.text : '';
  }

  /**
   * Safely parse JSON, handling malformed responses
   */
  private safeParseJSON(text: string): Record<string, unknown> | null {
    try {
      // Try to extract JSON from response (may be wrapped in markdown)
      const jsonMatch = text.match(/\{[\s\S]*\}/);
      if (!jsonMatch) {
        return null;
      }

      return JSON.parse(jsonMatch[0]);
    } catch {
      return null;
    }
  }

  /**
   * Create empty billing info for error cases
   */
  private createEmptyBillingInfo(
    config: ServiceConfig,
    errors: string[]
  ): BillingInfo {
    return {
      serviceId: config.id,
      serviceName: config.name,
      status: 'unknown',
      renewalDate: null,
      cost: null,
      paymentMethod: null,
      confidence: 0,
      extractedAt: new Date().toISOString(),
      errors,
    };
  }
}
