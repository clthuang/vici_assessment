# SubTerminator PRD

## Product Requirements Document
**Version:** 2.0  
**Author:** Terry  
**Date:** February 2, 2026  
**Status:** Draft

---

## 1. Executive Summary

Simplest oneliner: `subterminator cancels subscriptions`
This is a command line tool to cancel subscription services with minimal friction.

### 1.1 Problem Statement

Subscription services deliberately design cancellation flows to maximize friction. Users encounter:

- Buried account settings requiring multiple navigation steps
- Mandatory retention offers that must be explicitly declined
- Exit surveys that cannot be skipped
- Confirmation dialogs with confusing "cancel" vs "cancel cancellation" language
- Session timeouts mid-flow requiring re-authentication
- A/B tested variations meaning flows differ between users

Users waste time, abandon cancellations out of frustration, or continue paying for unused services.

### 1.2 Proposed Solution

An automation tool that navigates subscription cancellation flows on behalf of users, handling the complexity and variation while keeping humans in control of irreversible decisions.

### 1.3 MVP Scope

**In Scope (v1):**
- Netflix cancellation flow
- CLI-based invocation
- Screenshot capture and HTML dump to Claude for the accurate cancellation flow identification
- Human-in-the-loop for authentication and final confirmation
- Comprehensive logging and failure diagnostics

**Out of Scope (v1):**
- Browser extension integration
- Subscription detection/monitoring
- Multiple concurrent cancellations
- Mobile app subscriptions (iOS/Android in-app purchases)
- Services requiring phone/chat support to cancel

---

## 2. Goals and Success Criteria

### 2.1 Primary Goals

| Goal | Success Criteria | How to Measure |
|------|------------------|----------------|
| **Complete Netflix cancellation** | Successfully cancel an active Netflix subscription end-to-end | Manual E2E test with real account |
| **Handle flow variations** | System completes cancellation regardless of which A/B variant is shown | Test against multiple accounts or document observed variants |
| **Graceful degradation** | When automation cannot proceed, provide clear diagnostics enabling manual completion | Failure output includes screenshot, current state, and suggested manual steps |
| **Human safety** | No irreversible action taken without explicit human confirmation | Code review; confirmation prompt mandatory before final submit |

### 2.2 Secondary Goals

| Goal | Success Criteria |
|------|------------------|
| **Extensibility** | Architecture allows adding a second service (e.g., Spotify) without rewriting core logic |
| **Observability** | Any failure can be diagnosed from logs and screenshots alone |
| **Testability** | Core logic testable without live browser or network |

### 2.3 Non-Goals

- Speed optimization (reliability > speed)
- Bypassing CAPTCHAs automatically
- Storing user credentials
- Cancelling without any user interaction

### 2.4 Technical constraints
- use Python as the main language
- use Playwright for browser automation
- use Claude for cancellation flow identification
- use Git for version control
- use GitHub for code hosting
- use GitHub Actions for CI/CD: setup CI/CD stages, run tests on feature branch, only tests passed PR is created and manually merged. Cannot commit directly to main branch.

---

## 3. User Personas

### 3.1 Primary Persona: Frustrated Subscriber

**Name:** Alex  
**Context:** Has 6 streaming subscriptions, uses 2 regularly. Knows they should cancel the others but keeps postponing because it's annoying.  
**Technical skill:** Comfortable running CLI commands, not a developer.  
**Need:** "Just cancel this for me, I'll confirm at the end."  
**Concern:** "Don't mess up my account or cancel the wrong thing."

### 3.2 Secondary Persona: Developer/Power User

**Name:** Sam  
**Context:** Wants to understand how the tool works, may want to extend it.  
**Technical skill:** Software developer.  
**Need:** Clean code, clear architecture, ability to add new services.  
**Concern:** "Is this well-engineered or a hacky script?"

### 3.3 Evaluator Persona (VICI)

**Name:** VICI Engineering Team  
**Context:** Evaluating candidate's engineering thinking, not the product itself.  
**Need:** Evidence of systematic problem decomposition, edge case thinking, code quality.  
**Concern:** "Does this person think like a senior engineer?"

---

## 4. User Stories

### 4.1 Core Stories

#### US-1: Basic Cancellation
```
As a user with an active Netflix subscription,
I want to run a command that cancels my subscription,
So that I stop being charged without navigating the flow myself.

Acceptance Criteria:
- Command initiates browser-based cancellation flow
- System navigates to account page
- System proceeds through cancellation steps
- System pauses for my confirmation before final submission
- System reports success with confirmation screenshot
- My Netflix account shows subscription as cancelled
```

#### US-2: Already Cancelled
```
As a user who may have already cancelled,
I want the system to detect this and exit gracefully,
So that I don't waste time or cause errors.

Acceptance Criteria:
- System detects "already cancelled" state
- System reports status without attempting further action
- No errors thrown
- Clear message: "Subscription already cancelled. No action taken."
```

#### US-3: Authentication Required
```
As a user who is not logged into Netflix,
I want the system to pause and let me authenticate,
So that I can complete login manually (including 2FA if needed).

Acceptance Criteria:
- System detects login page
- System pauses with clear instruction
- Browser window visible for manual login
- System detects successful login and resumes
- Timeout after reasonable period (5 min) with clear message
```

#### US-4: Failure with Diagnostics
```
As a user whose cancellation fails mid-flow,
I want clear information about what went wrong,
So that I can complete the cancellation manually or report the issue.

Acceptance Criteria:
- Screenshot captured at failure point
- Current URL and page state logged
- Last successful step identified
- Suggested manual steps provided
- All artifacts saved to predictable location
```

#### US-5: Dry Run Mode
```
As a user who wants to verify setup before real cancellation,
I want to run a test mode that stops before any irreversible action,
So that I can confirm the system works without risk.

Acceptance Criteria:
- --dry-run flag available
- System proceeds through all detection and navigation
- System stops at final confirmation step
- Clear indication this is a dry run
- Report what would have happened
```

### 4.2 Edge Case Stories

#### US-6: Retention Offer Handling
```
As a user who encounters a retention offer,
I want the system to decline it automatically,
So that I don't have to manually navigate past upsells.

Acceptance Criteria:
- System detects retention offer page
- System declines offer (clicks appropriate button)
- System continues to cancellation
- Offer details logged (for user awareness)
```

#### US-7: Exit Survey Handling
```
As a user who encounters an exit survey,
I want the system to complete it with minimal information,
So that I can proceed without manual input.

Acceptance Criteria:
- System detects survey page
- System selects a generic option (e.g., "Other" or "Too expensive")
- System submits survey
- System continues to final confirmation
```

#### US-8: Session Timeout Recovery
```
As a user whose session times out mid-flow,
I want the system to detect this and prompt re-authentication,
So that I can continue without starting over.

Acceptance Criteria:
- System detects session timeout / login redirect
- System pauses for re-authentication
- System resumes from appropriate point after login
- State not lost
```

#### US-9: Ambiguous Page State
```
As a user on a page the system doesn't recognize,
I want clear communication about uncertainty,
So that I can decide whether to proceed manually.

Acceptance Criteria:
- System indicates low confidence in page interpretation
- Screenshot and page info provided
- User prompted to confirm or take manual control
- System doesn't guess on ambiguous states
```

#### US-10: Network/Browser Failure
```
As a user experiencing network issues,
I want the system to handle transient failures gracefully,
So that temporary issues don't cause permanent failures.

Acceptance Criteria:
- Transient failures (timeout, network blip) trigger retry
- Retry limit prevents infinite loops
- After retry exhaustion, clear failure message
- Distinction between transient and permanent failures
```

---

## 5. User Web Journeys

### 5.1 Journey Map: Happy Path Cancellation

```
User Action                          System Response                         Netflix Page State
───────────────────────────────────────────────────────────────────────────────────────────────

$ subterminator cancel netflix       Launches browser                        -
                                     Navigates to netflix.com/account        Loading...
                                     Waits for page load                     Account Settings page
                                     Detects: logged in, active sub          Shows membership details
                                     Finds "Cancel Membership" link          
                                     Clicks link                             Loading cancel page...
                                     Waits for page load                     "Cancel Membership" page
                                     Detects: cancel page loaded             "Why are you leaving?" survey
                                     Selects survey option                   
                                     Clicks continue                         Loading...
                                     Waits for page load                     Retention offer OR final confirm
                                     Detects: retention offer                "Before you go..." offer
                                     Declines offer                          
                                     Clicks continue                         Loading...
                                     Waits for page load                     Final confirmation page

[SYSTEM PAUSES]

"Final confirmation required.         
 Review the browser window.           
 Type 'confirm' to proceed: "        Waits for user input                   Final confirmation visible

User types: confirm                  Clicks final cancel button             Loading...
                                     Waits for page load                     Confirmation page
                                     Detects: cancellation confirmed         "Your cancellation is complete"
                                     Captures screenshot                     
                                     Reports success                         

"✓ Netflix cancellation complete.
 Effective date: March 1, 2026
 Screenshot: ./screenshots/..."
```

### 5.2 Journey Map: Authentication Required

```
User Action                          System Response                         Netflix Page State
───────────────────────────────────────────────────────────────────────────────────────────────

$ subterminator cancel netflix       Launches browser                        -
                                     Navigates to netflix.com/account        Loading...
                                     Waits for page load                     Login page (redirected)
                                     Detects: login required                 "Sign In" form

[SYSTEM PAUSES]

"Authentication required.
 Please log in to Netflix in the 
 browser window.
 Press Enter when complete..."       Waits for user input                   User logs in manually
                                                                            (possibly with 2FA)

User presses Enter                   Checks current page                    Account Settings page
                                     Detects: logged in, active sub         Shows membership details
                                     Continues normal flow...               
```

### 5.3 Journey Map: Already Cancelled

```
User Action                          System Response                         Netflix Page State
───────────────────────────────────────────────────────────────────────────────────────────────

$ subterminator cancel netflix       Launches browser                        -
                                     Navigates to netflix.com/account        Loading...
                                     Waits for page load                     Account Settings page
                                     Detects: already cancelled              "Restart Membership" shown
                                                                            No "Cancel" option visible

"ℹ Netflix subscription already 
 cancelled.
 Status: Ended January 15, 2026
 No action taken."

                                     Closes browser                          -
```

### 5.4 Journey Map: Failure Mid-Flow

```
User Action                          System Response                         Netflix Page State
───────────────────────────────────────────────────────────────────────────────────────────────

$ subterminator cancel netflix       Launches browser                        -
                                     Navigates to netflix.com/account        Loading...
                                     Waits for page load                     Account Settings page
                                     Detects: logged in, active sub          
                                     Clicks "Cancel Membership"              Loading...
                                     Waits for page load                     Unexpected error page
                                     Cannot interpret page state             "Something went wrong"
                                     Retries interpretation                  Still unrecognized
                                     Captures screenshot                     

"✗ Cancellation failed.

 Last successful state: ACTIVE_SUBSCRIPTION
 Failed at: Page interpretation after clicking cancel
 
 Diagnostics:
   URL: https://www.netflix.com/error
   Screenshot: ./screenshots/netflix_20260203_101530/error.png
   Log: ./logs/netflix_20260203_101530.json
 
 Suggested manual steps:
   1. Navigate to netflix.com/account
   2. Click 'Cancel Membership'
   3. Complete cancellation manually
 
 Please report this issue if it persists."
```

### 5.5 Journey Map: User Aborts at Confirmation

```
User Action                          System Response                         Netflix Page State
───────────────────────────────────────────────────────────────────────────────────────────────

$ subterminator cancel netflix       [... normal flow to final confirm ...]  Final confirmation page

[SYSTEM PAUSES]

"Final confirmation required.
 Type 'confirm' to proceed: "        Waits for user input                   

User types: no                       Detects abort                          
                                     Captures screenshot                    

"⚠ Cancellation aborted by user.
 
 Your subscription was NOT cancelled.
 To complete manually, click 'Finish 
 Cancellation' in the browser window."

                                     Leaves browser open                     Final confirmation still visible
```

---

## 6. Netflix Cancellation Flow Analysis

### 6.1 Known Flow Variants

Based on research, Netflix cancellation can follow different paths:

**Variant A: Direct to Survey**
```
Account Page → Cancel Link → Survey → Final Confirm → Done
```

**Variant B: Retention Offer First**
```
Account Page → Cancel Link → Retention Offer → Survey → Final Confirm → Done
```

**Variant C: Multiple Retention Offers**
```
Account Page → Cancel Link → Offer 1 → Offer 2 → Survey → Final Confirm → Done
```

**Variant D: No Survey (Rare)**
```
Account Page → Cancel Link → Retention Offer → Final Confirm → Done
```

### 6.2 Page States to Detect

| State | Identifying Signals | Confidence Indicators |
|-------|--------------------|-----------------------|
| **Logged Out** | URL contains /login; "Sign In" form visible; email/password fields | High: URL pattern |
| **Account Page (Active)** | URL is /account; "Cancel Membership" link present | High: Link presence |
| **Account Page (Cancelled)** | URL is /account; "Restart Membership" text; no cancel option | High: Text pattern |
| **Cancel Initiation** | URL contains /cancelplan; heading mentions cancellation | Medium: URL pattern |
| **Retention Offer** | "Before you go", "Special offer", discount language; "Continue to Cancel" button | Medium: Text patterns |
| **Exit Survey** | "Why are you leaving", "Reason for cancelling"; radio buttons or dropdown | Medium: Text patterns |
| **Final Confirmation** | "Finish Cancellation" button; effective date shown; warning language | Medium: Button text |
| **Cancellation Complete** | "Cancelled" in heading; confirmation number; future date shown | High: Explicit confirmation |
| **Error Page** | "Something went wrong", "Error", HTTP error codes | Medium: Text patterns |
| **Unexpected State** | None of the above | N/A |

### 6.3 Interactive Elements by State

| State | Primary Action | Fallback Action |
|-------|---------------|-----------------|
| **Account Page (Active)** | Click "Cancel Membership" link | Look for "Cancel" in any link text |
| **Retention Offer** | Click "Continue to Cancel" or similar | Look for secondary/decline button |
| **Exit Survey** | Select first available option, submit | Skip if skip button available |
| **Final Confirmation** | PAUSE for human | Never auto-click |

---

## 7. Branch Points and Decision Tree

### 7.1 Complete Decision Tree

```
START
│
├─► Navigate to netflix.com/account
│
▼
[Page Load Result?]
│
├─► Timeout ──────────────────────────────► RETRY (max 3) ──► FAIL: Network timeout
│
├─► Login page ───────────────────────────► PAUSE: Request authentication
│   │                                           │
│   │                                           ├─► User completes login ──► Resume from START
│   │                                           │
│   │                                           └─► Timeout (5 min) ──► FAIL: Auth timeout
│
├─► Account page loaded
│   │
│   ▼
│   [Subscription Status?]
│   │
│   ├─► Already cancelled ────────────────► SUCCESS: Already cancelled (no action)
│   │
│   ├─► Active subscription
│   │   │
│   │   ▼
│   │   [Find Cancel Link?]
│   │   │
│   │   ├─► Found ────────────────────────► Click link
│   │   │   │
│   │   │   ▼
│   │   │   [Page After Click?]
│   │   │   │
│   │   │   ├─► Cancel page ──────────────► Continue to Cancel Flow (below)
│   │   │   │
│   │   │   ├─► Error page ───────────────► RETRY (max 2) ──► FAIL: Navigation error
│   │   │   │
│   │   │   ├─► Login page ───────────────► PAUSE: Session expired, re-auth
│   │   │   │
│   │   │   └─► Unknown ──────────────────► FAIL: Unexpected state
│   │   │
│   │   └─► Not found ────────────────────► FAIL: Cannot locate cancel option
│   │
│   └─► Cannot determine ─────────────────► FAIL: Ambiguous subscription status
│
└─► Unexpected page ──────────────────────► FAIL: Unexpected initial state


CANCEL FLOW (after clicking cancel link)
│
▼
[Current Page Type?]
│
├─► Retention Offer
│   │
│   ▼
│   [Find Decline/Continue Button?]
│   │
│   ├─► Found ────────────────────────────► Click decline ──► Loop back to [Current Page Type?]
│   │
│   └─► Not found ────────────────────────► FAIL: Cannot navigate retention offer
│
├─► Exit Survey
│   │
│   ▼
│   [Survey Format?]
│   │
│   ├─► Radio buttons ────────────────────► Select first/generic option
│   │
│   ├─► Dropdown ─────────────────────────► Select first/generic option
│   │
│   ├─► Free text only ───────────────────► Enter minimal text ("No longer needed")
│   │
│   └─► Unknown format ───────────────────► PAUSE: Request human assistance
│   │
│   ▼
│   [Submit Survey]
│   │
│   ├─► Success ──────────────────────────► Loop back to [Current Page Type?]
│   │
│   └─► Error ────────────────────────────► RETRY ──► FAIL: Survey submission failed
│
├─► Final Confirmation Page
│   │
│   ▼
│   ══════════════════════════════════════
│   MANDATORY HUMAN CHECKPOINT
│   ══════════════════════════════════════
│   │
│   ├─► User confirms ────────────────────► Click final cancel button
│   │   │
│   │   ▼
│   │   [Result?]
│   │   │
│   │   ├─► Confirmation page ────────────► SUCCESS: Cancellation complete
│   │   │
│   │   ├─► Error ────────────────────────► FAIL: Final submission failed
│   │   │
│   │   └─► Unexpected ───────────────────► FAIL: Unknown result state
│   │
│   └─► User aborts ──────────────────────► ABORT: User cancelled operation
│
├─► Confirmation Page (already complete?)
│   │
│   └─► SUCCESS: Cancellation complete (possibly from previous attempt)
│
├─► Error Page
│   │
│   └─► FAIL: Error during cancellation
│
└─► Unknown Page
    │
    ▼
    [Attempt AI interpretation]
    │
    ├─► High confidence match ────────────► Route to appropriate handler
    │
    └─► Low confidence ───────────────────► PAUSE: Request human guidance
```

---

## 8. Edge Cases and Failure Modes

### 8.1 Authentication Edge Cases

| Edge Case | Description | Expected Behavior |
|-----------|-------------|-------------------|
| **EC-AUTH-1** | User has 2FA enabled (SMS, authenticator app) | Pause allows user to complete 2FA manually |
| **EC-AUTH-2** | User has hardware security key | Pause allows user to use key |
| **EC-AUTH-3** | "Remember me" session exists but expired | Detect redirect to login, trigger auth pause |
| **EC-AUTH-4** | Multiple Netflix profiles on account | Handle profile selection or default to account owner |
| **EC-AUTH-5** | CAPTCHA on login page | Pause allows user to solve manually |
| **EC-AUTH-6** | Account locked due to suspicious activity | Detect and report; cannot proceed |
| **EC-AUTH-7** | Password change required | Detect and report; cannot proceed without human |
| **EC-AUTH-8** | Account requires email verification | Detect and report; human must verify |

### 8.2 Subscription State Edge Cases

| Edge Case | Description | Expected Behavior |
|-----------|-------------|-------------------|
| **EC-SUB-1** | Subscription cancelled but still in paid period | Detect as "already cancelled" with end date |
| **EC-SUB-2** | Subscription on hold/paused (if Netflix offers this) | Detect and report; clarify what user wants |
| **EC-SUB-3** | Free trial active | Handle same as paid subscription |
| **EC-SUB-4** | Gift subscription (may have different cancel flow) | Detect and warn; flow may differ |
| **EC-SUB-5** | Bundle subscription (T-Mobile, etc.) | Detect and report; cannot cancel through Netflix |
| **EC-SUB-6** | iTunes/Google Play billing | Detect and report; must cancel through Apple/Google |
| **EC-SUB-7** | Multiple subscriptions on account (if possible) | Clarify which to cancel |
| **EC-SUB-8** | Subscription renewal pending | Proceed; note renewal will be cancelled |

### 8.3 Navigation Edge Cases

| Edge Case | Description | Expected Behavior |
|-----------|-------------|-------------------|
| **EC-NAV-1** | Cancel link not visible (below fold) | Scroll to find; use accessibility tree |
| **EC-NAV-2** | Cancel link in unexpected location (UI redesign) | Fall back to text search |
| **EC-NAV-3** | Cancel link is actually a dropdown menu item | Handle dropdown interaction |
| **EC-NAV-4** | Page loads but JavaScript errors prevent interaction | Detect non-responsive elements; report |
| **EC-NAV-5** | Popup/modal obscures cancel link | Detect and dismiss modal first |
| **EC-NAV-6** | Cookie consent banner blocking interaction | Dismiss banner first |
| **EC-NAV-7** | A/B test shows completely different page layout | Rely on semantic detection, not position |
| **EC-NAV-8** | Page loads in wrong language | Handle multilingual text detection |

### 8.4 Retention Flow Edge Cases

| Edge Case | Description | Expected Behavior |
|-----------|-------------|-------------------|
| **EC-RET-1** | Multiple sequential retention offers | Decline each; limit to prevent infinite loop |
| **EC-RET-2** | Retention offer requires clicking "No thanks" vs "Continue" | Identify correct decline action |
| **EC-RET-3** | Offer has countdown timer | Proceed regardless of timer |
| **EC-RET-4** | Offer requires scrolling to see decline button | Scroll to find button |
| **EC-RET-5** | "Call us to cancel" as only option | Report as cannot-automate; suggest manual steps |
| **EC-RET-6** | Chat window opens for retention | Report as cannot-automate; close chat |
| **EC-RET-7** | Personalized offer based on viewing history | Ignore content; find decline button |

### 8.5 Survey Edge Cases

| Edge Case | Description | Expected Behavior |
|-----------|-------------|-------------------|
| **EC-SRV-1** | Survey is required (no skip option) | Complete with generic selection |
| **EC-SRV-2** | Survey has skip option | Skip if available |
| **EC-SRV-3** | Multiple survey pages | Complete each page |
| **EC-SRV-4** | Survey requires free-text (mandatory) | Enter minimal generic text |
| **EC-SRV-5** | Survey validation rejects generic answers | Try alternative selections |
| **EC-SRV-6** | Survey has "Other" option requiring explanation | Select "Other" + minimal text |

### 8.6 Final Confirmation Edge Cases

| Edge Case | Description | Expected Behavior |
|-----------|-------------|-------------------|
| **EC-FIN-1** | Multiple confirmation buttons (confusing UX) | Identify correct "confirm cancel" button |
| **EC-FIN-2** | Confirmation text is misleading ("Cancel" cancels the cancellation) | Parse carefully; present to user |
| **EC-FIN-3** | Final page shows warning about losing content | Show warning to user in confirmation prompt |
| **EC-FIN-4** | Page shows refund information | Include in confirmation prompt |
| **EC-FIN-5** | Effective date is immediate vs end of billing period | Include in confirmation prompt |

### 8.7 Technical/Browser Edge Cases

| Edge Case | Description | Expected Behavior |
|-----------|-------------|-------------------|
| **EC-TECH-1** | Page takes >30s to load | Extended timeout; eventual failure |
| **EC-TECH-2** | Browser crashes mid-flow | Detect; report with last known state |
| **EC-TECH-3** | Netflix shows maintenance page | Detect; suggest retry later |
| **EC-TECH-4** | Geographic restriction message | Report; cannot proceed |
| **EC-TECH-5** | Netflix rate limiting/blocking automation | Detect if possible; report |
| **EC-TECH-6** | SSL certificate error | Fail safely; do not proceed |
| **EC-TECH-7** | DNS resolution failure | Retry; report network issue |
| **EC-TECH-8** | Page partially loads (some elements missing) | Detect incomplete state; retry |

### 8.8 User Interaction Edge Cases

| Edge Case | Description | Expected Behavior |
|-----------|-------------|-------------------|
| **EC-USR-1** | User closes browser window during automation | Detect; report interrupted |
| **EC-USR-2** | User manually navigates away during automation | Detect URL change; attempt recovery |
| **EC-USR-3** | User doesn't respond to auth prompt (long timeout) | Timeout after 5 min; clear message |
| **EC-USR-4** | User types wrong confirmation (not "confirm") | Treat as abort; leave browser open |
| **EC-USR-5** | Ctrl+C during execution | Graceful shutdown; report state |
| **EC-USR-6** | User runs command twice simultaneously | Prevent or warn about concurrent runs |

---

## 9. Functional Requirements

### 9.1 Core Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| **FR-1** | System SHALL navigate to Netflix account page | Must |
| **FR-2** | System SHALL detect whether user is logged in | Must |
| **FR-3** | System SHALL pause for manual authentication when logged out | Must |
| **FR-4** | System SHALL detect current subscription status (active/cancelled) | Must |
| **FR-5** | System SHALL navigate through cancellation flow | Must |
| **FR-6** | System SHALL handle retention offers without human input | Must |
| **FR-7** | System SHALL handle exit surveys without human input | Must |
| **FR-8** | System SHALL pause for human confirmation before final cancellation | Must |
| **FR-9** | System SHALL report success with confirmation details | Must |
| **FR-10** | System SHALL report failures with diagnostic information | Must |

### 9.2 Resilience Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| **FR-11** | System SHALL retry transient failures (network, timeout) up to 3 times | Must |
| **FR-12** | System SHALL distinguish transient from permanent failures | Should |
| **FR-13** | System SHALL handle session expiry during flow | Should |
| **FR-14** | System SHALL detect and report cannot-automate scenarios | Must |
| **FR-15** | System SHALL not loop infinitely on unrecognized states | Must |

### 9.3 Observability Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| **FR-16** | System SHALL capture screenshot at each state transition | Must |
| **FR-17** | System SHALL log all state transitions with timestamps | Must |
| **FR-18** | System SHALL provide failure diagnostics sufficient for manual completion | Must |
| **FR-19** | System SHALL report which page states were detected by heuristics vs AI | Should |
| **FR-20** | System SHALL save session logs to persistent storage | Must |

### 9.4 Safety Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| **FR-21** | System SHALL NOT complete cancellation without explicit human confirmation | Must |
| **FR-22** | System SHALL NOT store user credentials | Must |
| **FR-23** | System SHALL NOT proceed on ambiguous final confirmation states | Must |
| **FR-24** | System SHALL leave browser open if user aborts | Should |
| **FR-25** | Dry-run mode SHALL NOT execute final cancellation click | Must |

---

## 10. Non-Functional Requirements

### 10.1 Performance

| ID | Requirement | Target |
|----|-------------|--------|
| **NFR-1** | Page load timeout | 30 seconds |
| **NFR-2** | Element detection timeout | 10 seconds |
| **NFR-3** | Total flow completion (happy path) | < 2 minutes |
| **NFR-4** | Authentication wait timeout | 5 minutes |
| **NFR-5** | AI interpretation response time | < 10 seconds |

### 10.2 Reliability

| ID | Requirement | Target |
|----|-------------|--------|
| **NFR-6** | Success rate on happy path (stable Netflix UI) | > 95% |
| **NFR-7** | Graceful failure rate (vs crash) | 100% |
| **NFR-8** | Retry success rate for transient failures | > 80% |

### 10.3 Usability

| ID | Requirement | Target |
|----|-------------|--------|
| **NFR-9** | Setup time for new user | < 5 minutes |
| **NFR-10** | Clear error messages | All failures have actionable message |
| **NFR-11** | Documentation completeness | README covers all common scenarios |

### 10.4 Maintainability

| ID | Requirement | Target |
|----|-------------|--------|
| **NFR-12** | Adding new service | < 1 day for experienced developer |
| **NFR-13** | Test coverage (core logic) | > 80% |
| **NFR-14** | Code documentation | All public functions documented |

---

## 11. Assumptions

| ID | Assumption | Risk if Invalid |
|----|------------|-----------------|
| **A-1** | Netflix web cancellation flow exists and is accessible | Fatal; project not viable |
| **A-2** | Netflix does not actively block automation | High; may need to mimic human timing |
| **A-3** | User has a valid Netflix account | Medium; need clear error handling |
| **A-4** | User can run Python CLI tools | Medium; documentation must be clear |
| **A-5** | Netflix UI changes infrequently | Medium; AI interpretation provides buffer |
| **A-6** | Evaluator has Anthropic API access for testing | Low; can provide demo video |

---

## 12. Dependencies

| ID | Dependency | Type | Risk |
|----|------------|------|------|
| **D-1** | Playwright browser automation | Library | Low; stable, well-maintained |
| **D-2** | Anthropic Claude API | External service | Low; reliable |
| **D-3** | Netflix web interface | External service | Medium; can change without notice |
| **D-4** | Python 3.10+ | Runtime | Low; standard |

---

## 13. Open Questions

| ID | Question | Impact | Decision Needed By |
|----|----------|--------|-------------------|
| **Q-1** | Can we test E2E without an active subscription? | High | Day 1 |
| **Q-2** | How does Netflix handle automation detection? | High | Day 2 |
| **Q-3** | Should surveys be answered honestly or generically? | Low | Day 3 |
| **Q-4** | What's the retention offer frequency in practice? | Low | During testing |
| **Q-5** | Should second service (Spotify) be attempted? | Medium | Day 5 |

---

## 14. Glossary

| Term | Definition |
|------|------------|
| **Retention offer** | A discount or incentive shown to users attempting to cancel |
| **Exit survey** | Questions asked about reasons for cancellation |
| **Transient failure** | A temporary error that may succeed on retry (network timeout, rate limit) |
| **Permanent failure** | An error that will not resolve with retry (invalid state, cannot-automate scenario) |
| **Human-in-the-loop** | A checkpoint requiring explicit human action before proceeding |
| **State machine** | A model where the system exists in defined states with valid transitions between them |
| **Dry run** | Execution mode that stops before any irreversible action |

---

## Appendix A: Netflix Research Notes

*To be populated with observations from manual flow testing:*
- Exact URLs at each step
- Button text variations observed
- A/B test variants encountered
- Timing between page loads
- Any anti-automation measures observed

## Appendix B: Competitive Analysis

*Brief notes on existing solutions:*
- Truebill/Rocket Money: Full service, handles cancellation via human agents
- DoNotPay: Automated, but subscription service itself
- Manual: Average time ~5-10 minutes per service

## Appendix C: Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-02 | Terry | Initial draft with implementation |
| 2.0 | 2026-02-02 | Terry | Refocused on requirements; removed implementation |