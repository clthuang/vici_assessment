import { describe, it, expect } from 'vitest';
import { ErrorHandler } from './ErrorHandler.js';
import { ErrorType } from '../types/index.js';

describe('ErrorHandler', () => {
  const handler = new ErrorHandler();

  describe('classify', () => {
    it('should classify connection refused as CHROME_NOT_RUNNING', () => {
      const error = new Error('ECONNREFUSED - connection refused');
      const classified = handler.classify(error);

      expect(classified.type).toBe(ErrorType.CHROME_NOT_RUNNING);
      expect(classified.recoverable).toBe(false);
      expect(classified.originalError).toBe(error);
    });

    it('should classify timeout errors as NAVIGATION_TIMEOUT', () => {
      const error = new Error('Page load timed out');
      const classified = handler.classify(error);

      expect(classified.type).toBe(ErrorType.NAVIGATION_TIMEOUT);
      expect(classified.recoverable).toBe(true);
    });

    it('should classify not found errors as SERVICE_NOT_FOUND', () => {
      const error = new Error('Service not found');
      const classified = handler.classify(error);

      expect(classified.type).toBe(ErrorType.SERVICE_NOT_FOUND);
      expect(classified.recoverable).toBe(false);
    });

    it('should classify unknown errors as UNKNOWN type', () => {
      const error = new Error('Something unexpected happened');
      const classified = handler.classify(error);

      expect(classified.type).toBe(ErrorType.UNKNOWN);
      expect(classified.recoverable).toBe(false);
    });

    it('should classify rate limit errors', () => {
      const error = new Error('429 Too Many Requests');
      const classified = handler.classify(error);

      expect(classified.type).toBe(ErrorType.RATE_LIMITED);
      expect(classified.recoverable).toBe(true);
    });

    it('should classify auth required errors', () => {
      const error = new Error('Please login to continue');
      const classified = handler.classify(error);

      expect(classified.type).toBe(ErrorType.AUTH_REQUIRED);
      expect(classified.recoverable).toBe(true);
    });
  });

  describe('formatForUser', () => {
    it('should format errors with user action', () => {
      const error = new Error('ECONNREFUSED');
      const classified = handler.classify(error);
      const message = handler.formatForUser(classified);

      expect(message).toContain('Error:');
      expect(message).toContain('→');
    });

    it('should format unknown errors without action hint', () => {
      const error = new Error('Random error');
      const classified = handler.classify(error);
      const message = handler.formatForUser(classified);

      expect(message).toContain('Error:');
      expect(message).toContain('Random error');
    });
  });

  describe('shouldRetry', () => {
    it('should return true for recoverable timeout errors', () => {
      const error = new Error('Request timed out');
      const classified = handler.classify(error);

      expect(handler.shouldRetry(classified)).toBe(true);
    });

    it('should return true for rate limited errors', () => {
      const error = new Error('Rate limit exceeded');
      const classified = handler.classify(error);

      expect(handler.shouldRetry(classified)).toBe(true);
    });

    it('should return false for non-recoverable errors', () => {
      const error = new Error('Service not found');
      const classified = handler.classify(error);

      expect(handler.shouldRetry(classified)).toBe(false);
    });

    it('should return false for chrome not running', () => {
      const error = new Error('ECONNREFUSED');
      const classified = handler.classify(error);

      expect(handler.shouldRetry(classified)).toBe(false);
    });
  });
});
