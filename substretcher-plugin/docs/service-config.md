# Service Configuration Reference

Service configurations define how SubStretcher interacts with subscription services.

## File Location

Configurations are loaded from:
1. `./services/*.yaml` (project directory)
2. `~/.substretcher/services/*.yaml` (user directory)

Files are named by service ID: `netflix.yaml`, `spotify.yaml`, etc.

## Schema

```yaml
# Required fields
id: string          # Unique identifier (lowercase, no spaces)
name: string        # Display name
domain: string      # Primary domain (for grouping)
billingUrl: string  # Direct URL to billing page

# Optional fields
navigation:         # Steps to reach billing page
  steps: NavigationStep[]

extraction:         # CSS selector hints for AI
  status: { selector: string }
  renewalDate: { selector: string }
  cost: { selector: string }

cancellation:       # Cancellation workflow
  enabled: boolean
  steps: CancellationStep[]
  successIndicator:
    text?: string
    selector?: string
```

## Field Reference

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique service identifier. Used in CLI commands. |
| `name` | string | Human-readable name for display. |
| `domain` | string | Primary domain (e.g., `netflix.com`). |
| `billingUrl` | string | Direct URL to the billing/account page. Must be valid URL. |

### Navigation

Used when the billing page isn't directly accessible via URL.

```yaml
navigation:
  steps:
    - description: "Click profile menu in header"
      selector: "[data-testid='profile-menu']"
      action: click          # click | hover | wait (default: click)
      waitAfter: 1500        # ms to wait after action (default: 1000)
```

**NavigationStep fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `description` | string | Yes | Human-readable description. Used by AI when selector fails. |
| `selector` | string | No | CSS selector. If omitted, AI finds the element. |
| `action` | string | No | `click`, `hover`, or `wait`. Default: `click`. |
| `waitAfter` | number | No | Milliseconds to wait after action. Default: 1000. |

### Extraction

Hints for the AI extractor. These are optional—AI can extract without them.

```yaml
extraction:
  status:
    selector: ".membership-status"
  renewalDate:
    selector: ".next-billing-date"
  cost:
    selector: ".plan-price"
```

**Extraction fields:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | `{ selector: string }` | CSS selector for subscription status element. |
| `renewalDate` | `{ selector: string }` | CSS selector for renewal/billing date. |
| `cost` | `{ selector: string }` | CSS selector for price/cost display. |

### Cancellation

Defines the automated cancellation workflow.

```yaml
cancellation:
  enabled: true
  steps:
    - action: click
      description: "Click Cancel Membership button"
      selector: "#cancel-btn"
      waitAfter: 2000
    - action: type
      description: "Enter cancellation reason"
      selector: "#reason-input"
      value: "Too expensive"
    - action: click
      description: "Confirm cancellation"
      selector: "#confirm-cancel"
      requiresConfirmation: true
  successIndicator:
    text: "Your membership has been cancelled"
```

**CancellationStep fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `action` | string | Yes | `click`, `type`, `select`, or `wait`. |
| `description` | string | Yes | Human-readable description. Used by AI when selector fails. |
| `selector` | string | No | CSS selector. If omitted, AI finds the element. |
| `value` | string | No | Text to type (for `type` action) or option to select. |
| `waitAfter` | number | No | Milliseconds to wait after action. |
| `requiresConfirmation` | boolean | No | If true, pauses and asks user before this step. |

**SuccessIndicator fields:**

| Field | Type | Description |
|-------|------|-------------|
| `text` | string | Text to look for on page after cancellation. |
| `selector` | string | CSS selector for success element. |

At least one of `text` or `selector` should be provided.

## Examples

### Minimal Configuration

```yaml
id: basic-service
name: Basic Service
domain: basic.com
billingUrl: https://basic.com/account
```

The AI will:
1. Navigate directly to `billingUrl`
2. Take a screenshot
3. Extract billing info from the page

### With Navigation Steps

```yaml
id: complex-service
name: Complex Service
domain: complex.com
billingUrl: https://complex.com/dashboard

navigation:
  steps:
    - description: "Open account dropdown"
      selector: ".account-dropdown-trigger"
      action: hover
      waitAfter: 500
    - description: "Click billing link"
      selector: "a[href='/billing']"
      waitAfter: 2000
```

### With Extraction Hints

```yaml
id: hints-service
name: Service with Hints
domain: hints.com
billingUrl: https://hints.com/billing

extraction:
  status:
    selector: "[data-testid='subscription-status']"
  renewalDate:
    selector: ".billing-cycle .date"
  cost:
    selector: ".plan-details .price"
```

### Full Cancellation Workflow

```yaml
id: cancellable-service
name: Cancellable Service
domain: cancellable.com
billingUrl: https://cancellable.com/account

navigation:
  steps:
    - description: "Navigate to subscription settings"
      selector: "a[href*='subscription']"
      waitAfter: 1500

extraction:
  status:
    selector: ".sub-status"
  renewalDate:
    selector: ".renewal-date"
  cost:
    selector: ".monthly-cost"

cancellation:
  enabled: true
  steps:
    - action: click
      description: "Click manage subscription"
      selector: "#manage-sub"
      waitAfter: 1000
    - action: click
      description: "Click cancel subscription"
      selector: "#cancel-link"
      waitAfter: 1500
    - action: click
      description: "Select 'Too expensive' as reason"
      selector: "input[value='too_expensive']"
    - action: click
      description: "Click Continue"
      selector: "#continue-btn"
      waitAfter: 1000
    - action: click
      description: "Confirm final cancellation"
      selector: "#final-cancel"
      requiresConfirmation: true
  successIndicator:
    text: "Successfully cancelled"
    selector: ".cancellation-success"
```

## Validation

Configurations are validated using Zod schemas. Invalid configs are skipped with a warning.

**Validation rules:**
- `id`, `name`, `domain` must be non-empty strings
- `billingUrl` must be a valid URL
- `action` must be one of: `click`, `type`, `select`, `wait`, `hover`
- `waitAfter` must be a positive number if provided

## Testing Your Configuration

```bash
# List all services (verify it loads)
substretcher list

# Test extraction
substretcher scan your-service -v

# Test cancellation (dry run with confirmation)
substretcher cancel your-service
```

## AI Fallback

When a CSS selector fails or isn't provided, SubStretcher uses Claude Vision to:
1. Take a screenshot
2. Send to AI with the `description` text
3. Get coordinates of the target element
4. Perform action at those coordinates

This makes configurations resilient to UI changes.

## Best Practices

1. **Always provide descriptions** - Even with selectors, descriptions help AI fallback
2. **Use data-testid selectors** - More stable than class names
3. **Add waitAfter for slow pages** - Prevents racing ahead
4. **Use requiresConfirmation** - For destructive actions
5. **Test on logged-in browser** - Configs assume user is authenticated
