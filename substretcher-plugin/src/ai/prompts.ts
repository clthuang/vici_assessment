/**
 * Prompt for extracting billing information from a screenshot
 */
export const EXTRACTION_PROMPT = `
Analyze this screenshot of a subscription billing page for {serviceName}.
Extract the following information:

1. Subscription Status: (active, cancelled, paused, trial, or unknown)
2. Renewal Date: The next billing date (format as ISO 8601: YYYY-MM-DD)
3. Cost: Amount, currency, and billing cycle (weekly/monthly/annual)
4. Payment Method: Card type and last 4 digits if visible

Return ONLY valid JSON with this exact structure:
{
  "status": "active|cancelled|paused|trial|unknown",
  "renewalDate": "YYYY-MM-DD" or null,
  "cost": { "amount": number, "currency": "USD", "cycle": "monthly|annual|weekly|unknown" } or null,
  "paymentMethod": "Visa ****1234" or null,
  "confidence": 0.0-1.0
}

If you cannot determine a field with confidence, use null.
The confidence score should reflect your overall certainty about the extraction.
`;

/**
 * Prompt for checking if user is logged in
 */
export const AUTH_CHECK_PROMPT = `
Is the user logged in to {serviceName}?

Look for indicators that the user IS logged in:
- Profile icons or avatars
- Username or email displayed
- Account menu or settings
- Personalized content

Look for indicators that the user is NOT logged in:
- Login or Sign In buttons
- Authentication prompts
- "Create account" links
- Generic landing page content

Return ONLY valid JSON with this exact structure:
{
  "loggedIn": true or false,
  "confidence": 0.0-1.0,
  "reason": "Brief explanation of what you observed"
}
`;

/**
 * Prompt for finding a clickable element by description
 */
export const ELEMENT_FIND_PROMPT = `
Find the clickable element described as: "{description}"

Look for buttons, links, or other interactive elements that match this description.
Consider the visual appearance, text content, and context.

Return ONLY valid JSON with this exact structure:
{
  "found": true or false,
  "x": pixel X coordinate of center (integer),
  "y": pixel Y coordinate of center (integer),
  "width": approximate element width in pixels (integer),
  "height": approximate element height in pixels (integer),
  "confidence": 0.0-1.0,
  "description": "What element you found"
}

If you cannot find the element, set found to false and omit coordinates.
`;

/**
 * Replace placeholders in a prompt template
 */
export function formatPrompt(
  template: string,
  values: Record<string, string>
): string {
  let result = template;
  for (const [key, value] of Object.entries(values)) {
    result = result.replace(new RegExp(`\\{${key}\\}`, 'g'), value);
  }
  return result;
}
