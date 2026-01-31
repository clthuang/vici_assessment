import { describe, it, expect } from 'vitest';
import { ServiceConfigSchema, NavigationStepSchema, CancellationStepSchema } from './schema.js';

describe('ServiceConfigSchema', () => {
  const validConfig = {
    id: 'netflix',
    name: 'Netflix',
    domain: 'netflix.com',
    billingUrl: 'https://netflix.com/youraccount',
    navigation: {
      steps: [
        {
          description: 'Click account link',
          selector: '.account-link',
          action: 'click',
        },
      ],
    },
    cancellation: {
      enabled: true,
      steps: [
        {
          action: 'click',
          description: 'Click cancel',
          selector: '#cancel-button',
        },
      ],
      successIndicator: {
        text: 'Successfully cancelled',
      },
    },
  };

  it('should validate a correct service config', () => {
    const result = ServiceConfigSchema.safeParse(validConfig);
    expect(result.success).toBe(true);
  });

  it('should require id, name, and domain', () => {
    const result = ServiceConfigSchema.safeParse({
      billingUrl: 'https://example.com',
    });
    expect(result.success).toBe(false);
  });

  it('should allow optional navigation and cancellation', () => {
    const result = ServiceConfigSchema.safeParse({
      id: 'test',
      name: 'Test',
      domain: 'test.com',
      billingUrl: 'https://test.com/billing',
    });
    expect(result.success).toBe(true);
  });

  it('should validate URL format for billingUrl', () => {
    const result = ServiceConfigSchema.safeParse({
      id: 'test',
      name: 'Test',
      domain: 'test.com',
      billingUrl: 'not-a-url',
    });
    expect(result.success).toBe(false);
  });

  it('should validate extraction selectors', () => {
    const result = ServiceConfigSchema.safeParse({
      id: 'test',
      name: 'Test',
      domain: 'test.com',
      billingUrl: 'https://test.com/billing',
      extraction: {
        status: { selector: '.status' },
        renewalDate: { selector: '.renewal-date' },
        cost: { selector: '.cost' },
      },
    });
    expect(result.success).toBe(true);
  });
});

describe('NavigationStepSchema', () => {
  it('should validate step with description and selector', () => {
    const result = NavigationStepSchema.safeParse({
      description: 'Click the button',
      selector: '.button',
      action: 'click',
    });
    expect(result.success).toBe(true);
  });

  it('should validate step with waitAfter', () => {
    const result = NavigationStepSchema.safeParse({
      description: 'Wait for content',
      selector: '.content',
      action: 'wait',
      waitAfter: 5000,
    });
    expect(result.success).toBe(true);
  });

  it('should validate minimal step with just description', () => {
    const result = NavigationStepSchema.safeParse({
      description: 'Take screenshot',
    });
    expect(result.success).toBe(true);
  });

  it('should require description', () => {
    const result = NavigationStepSchema.safeParse({
      selector: '.button',
    });
    expect(result.success).toBe(false);
  });

  it('should reject invalid action type', () => {
    const result = NavigationStepSchema.safeParse({
      description: 'Invalid step',
      action: 'invalid',
    });
    expect(result.success).toBe(false);
  });
});

describe('CancellationStepSchema', () => {
  it('should validate click step', () => {
    const result = CancellationStepSchema.safeParse({
      action: 'click',
      description: 'Click cancel button',
      selector: '#cancel',
    });
    expect(result.success).toBe(true);
  });

  it('should validate type step with value', () => {
    const result = CancellationStepSchema.safeParse({
      action: 'type',
      description: 'Enter reason',
      selector: '#reason-input',
      value: 'Too expensive',
    });
    expect(result.success).toBe(true);
  });

  it('should require action and description', () => {
    const result = CancellationStepSchema.safeParse({
      selector: '#button',
    });
    expect(result.success).toBe(false);
  });
});
