import { z } from 'zod';
import type { ServiceConfig } from '../types/index.js';

/**
 * Schema for navigation steps
 */
export const NavigationStepSchema = z.object({
  description: z.string().min(1),
  selector: z.string().optional(),
  action: z.enum(['click', 'hover', 'wait']).optional(),
  waitAfter: z.number().positive().optional(),
});

/**
 * Schema for cancellation steps
 */
export const CancellationStepSchema = z.object({
  action: z.enum(['click', 'type', 'select', 'wait']),
  description: z.string().min(1),
  selector: z.string().optional(),
  value: z.string().optional(),
  waitAfter: z.number().positive().optional(),
  requiresConfirmation: z.boolean().optional(),
});

/**
 * Schema for service configuration
 */
export const ServiceConfigSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  domain: z.string().min(1),
  billingUrl: z.string().url(),
  navigation: z
    .object({
      steps: z.array(NavigationStepSchema),
    })
    .optional(),
  extraction: z
    .object({
      status: z.object({ selector: z.string() }).optional(),
      renewalDate: z.object({ selector: z.string() }).optional(),
      cost: z.object({ selector: z.string() }).optional(),
    })
    .optional(),
  cancellation: z
    .object({
      enabled: z.boolean(),
      steps: z.array(CancellationStepSchema),
      successIndicator: z.object({
        text: z.string().optional(),
        selector: z.string().optional(),
      }),
    })
    .optional(),
});

/**
 * Parse and validate a service configuration
 * @throws z.ZodError if validation fails
 */
export function parseServiceConfig(data: unknown): ServiceConfig {
  return ServiceConfigSchema.parse(data) as ServiceConfig;
}

/**
 * Safely parse a service configuration, returning null on failure
 */
export function safeParseServiceConfig(
  data: unknown
): ServiceConfig | null {
  const result = ServiceConfigSchema.safeParse(data);
  return result.success ? (result.data as ServiceConfig) : null;
}
