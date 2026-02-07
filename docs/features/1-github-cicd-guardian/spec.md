# Specification: GitHub CI/CD Guardian Skill

## 1. Deliverable

A single Claude Code skill file (`SKILL.md`) that provides domain-specific CI/CD expertise for GitHub Actions pipelines, targeted at a high-frequency proprietary trading firm.

### Deliverable Constraints
- **Format**: Markdown file named `SKILL.md` with YAML frontmatter containing `name` and `description` fields
- **Frontmatter**: `name` is the skill display name; `description` is used for auto-triggering (model-invoked) and must be under 200 characters
- **Location**: Within a Claude Code plugin's `skills/github-cicd-guardian/` directory (one skill per subdirectory)
- **Tooling**: Uses only Claude Code's existing tools (Bash, Read, Write, Edit, Glob, Grep) -- no new tools, commands, agents, or hooks
- **Dependencies**: Requires `gh` CLI installed and authenticated

## 2. MVP Scope (MUST HAVE)

The skill covers two features for initial delivery:

### 2.1 P0: Pipeline Failure Diagnosis & Fix

#### Functional Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| P0-1 | Fetch pipeline status | Given a repo with GitHub Actions, when the user asks about CI status, the skill runs `gh run list --limit 10` and presents a summary of recent runs with pass/fail status |
| P0-2 | Fetch failure logs | Given a failing workflow run, when the user asks to diagnose it, the skill runs `gh run view {run-id} --log-failed` to retrieve only the failing step logs |
| P0-3 | Root cause analysis | Given failure logs, the skill categorizes the failure and provides evidence. Test scenarios: (a) `ModuleNotFoundError: No module named 'foo'` → dependency issue; (b) `Error: .github/workflows/ci.yml: unexpected value` → YAML misconfiguration; (c) `FAIL test_order_placement ... AssertionError` → code bug; (d) `Error: Process completed with exit code 143` (timeout on re-run of same commit) → flaky test; (e) `No space left on device` or `runner is offline` → infrastructure/runner problem; (f) `Resource not accessible by integration` → permissions issue. The category MUST be stated explicitly in the output with the supporting log evidence quoted |
| P0-4 | Propose fix | Given a root cause, the skill proposes a specific fix with explanation. Output format: (1) plain-language explanation of why the fix addresses the root cause, (2) the specific change shown as a markdown code block (diff format for file edits, command format for retries/dependency updates), (3) what the user needs to approve before the skill applies it |
| P0-5 | Apply fix with approval | Given a proposed fix, the skill presents the exact changes before applying them. Code/YAML changes require user confirmation before writing. Workflow re-triggers require explicit "yes, re-run" confirmation |
| P0-6 | Handle ambiguous requests | Given "fix my CI" or "my pipeline is broken", the skill defaults to diagnosis only (P0-1 through P0-3) and asks before escalating to P0-4/P0-5 |

#### Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| P0-NF1 | Log fetching must never modify any file or trigger any workflow |
| P0-NF2 | If `gh` CLI is not available, the skill must inform the user with a clear message and not attempt alternative approaches |
| P0-NF3 | CI log content must be treated as untrusted input -- the skill must not auto-execute any commands suggested within log output |
| P0-NF4 | If `gh run view --log-failed` output exceeds practical limits, the skill should focus on the last 200 lines of each failing step and note that logs were truncated |

#### gh CLI Commands Used

```
gh run list [--limit N] [--status failure]    # List recent runs
gh run view {run-id}                           # Run summary
gh run view {run-id} --log-failed              # Failed step logs
gh run view {run-id} --log                     # Full logs (if needed)
gh run rerun {run-id}                          # Re-trigger (with confirmation)
gh run rerun {run-id} --failed                 # Re-run only failed jobs
```

---

### 2.2 P1: Security Audit & Supply Chain Protection

#### Functional Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| P1-1 | Scan for unpinned actions | Given `.github/workflows/*.yml` files, the skill identifies any `uses:` references that use tags (`@v1`, `@main`) instead of commit SHAs, and flags them as supply chain risks |
| P1-2 | Check for excessive permissions | Given workflow files, the skill identifies workflows with `permissions: write-all` or no explicit `permissions:` block (which defaults to broad access), and recommends least-privilege permissions |
| P1-3 | Detect hardcoded secrets | Given workflow files, the skill scans for hardcoded credential patterns rather than `${{ secrets.* }}` references. Detection approach: (1) Known format patterns -- AWS access keys (`AKIA[0-9A-Z]{16}`), GitHub PATs (`ghp_[A-Za-z0-9_]{36}`), generic tokens (`gh[pousr]_[A-Za-z0-9_]{36,}`); (2) YAML value patterns -- keys named `password`, `token`, `api_key`, `secret`, `credential` with inline string values instead of `${{ secrets.* }}`; (3) Claude's language understanding for credential-like strings not matching known formats. Each detection must cite the file, line, and matched pattern |
| P1-4 | Check for template injection | Given workflow files, the skill identifies unsafe use of `${{ github.event.* }}` in `run:` blocks (which enables script injection via PR titles/branch names) |
| P1-5 | Validate secrets usage | Given workflow files, the skill checks that secrets are referenced via `${{ secrets.* }}` and not exposed via `echo` to logs or passed to untrusted actions |
| P1-6 | Known vulnerability check for actions | Given actions used in workflows, the skill checks for known vulnerabilities using a layered approach: (1) If `zizmor` is installed, run `zizmor --format json` which includes its own vulnerability database; (2) Query `gh api /repos/{owner}/{repo}/security-advisories` for the action's repository; (3) Fall back to Claude's training knowledge with explicit caveat: "Based on training data as of [date], may be outdated -- verify independently." The skill must NOT claim comprehensive CVE coverage since GitHub Advisory Database does not index GitHub Actions as an ecosystem |
| P1-7 | Generate security report | Given a complete audit, the skill outputs a structured report: (a) critical issues (must fix), (b) warnings (should fix), (c) informational (best practice suggestions), with specific line references and remediation steps |
| P1-8 | Read-only by default | All security audit operations must be read-only. The skill must never modify workflow files during an audit unless the user explicitly requests remediation |

#### Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| P1-NF1 | Security audit must scan ALL `.yml` and `.yaml` files in `.github/workflows/` |
| P1-NF2 | The skill must not access or display actual secret values -- only audit their usage patterns |
| P1-NF3 | Vulnerability data from `zizmor` or `gh api` is preferred over Claude's training data. When using training data, clearly state "based on training data as of [date], may be outdated." The skill must NOT claim comprehensive CVE coverage for GitHub Actions |

#### gh CLI Commands Used

```
gh api /repos/{owner}/{repo}/security-advisories  # Repo security advisories
gh secret list                                     # List configured secrets (names only)
```

#### Optional Tool Integration

```
zizmor --format json .github/workflows/        # Security scanning (if installed)
```

#### Security Anti-Patterns Checklist

The skill must check for these specific patterns. Items 1-4 map directly to P1-1 through P1-4. Items 5-8 are covered by the general security audit scope and included in the P1-7 security report output.

1. **Unpinned actions**: `uses: actions/checkout@v4` instead of `uses: actions/checkout@{sha}` → P1-1
2. **Overly broad permissions**: `permissions: write-all` or missing `permissions:` block → P1-2
3. **Template injection**: `run: echo ${{ github.event.pull_request.title }}` (unsanitized) → P1-4
4. **Secret in echo**: `run: echo ${{ secrets.API_KEY }}` (logs to output) → P1-5
5. **Pull request target trigger**: `on: pull_request_target` with checkout of PR code (allows fork code execution) → P1-7
6. **Mutable action references**: Using `@main` or `@master` branch references → P1-1 (subset)
7. **Missing CODEOWNERS**: No `.github/CODEOWNERS` for workflow files → P1-7
8. **Artifact exposure**: Uploading artifacts that may contain secrets → P1-7

## 3. V2 Scope (SHOULD HAVE)

Defined here for completeness but NOT part of initial implementation. V2 features will be designed and specified separately. The MVP design does not need to include extension points for V2, but should not preclude V2 additions to `SKILL.md`.

**V2 does NOT include**: P4 (Status Dashboard), P5 (Deployment Safety), P6 (Cost Optimization), cross-repository workflows, infrastructure-level operations, or any non-GitHub CI platforms.

### 3.1 P2: Workflow Authoring & Validation

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| P2-1 | Generate workflows from natural language | Given "create a CI pipeline that runs pytest and lints with ruff", generate a valid `.github/workflows/ci.yml` |
| P2-2 | Validate existing workflows | Read all workflow files and check for syntax errors, deprecated features, and anti-patterns |
| P2-3 | Suggest optimizations | Analyze workflows for caching opportunities, job parallelization, and unnecessary steps |

### 3.2 P3: Compliance Readiness Check

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| P3-1 | Check branch protection | Query `gh api` for branch protection rules and compare against FINRA/SOX requirements |
| P3-2 | Validate separation of duties | Check if workflows enforce that PR author != merger (via required reviews) |
| P3-3 | Generate readiness report | Output a checklist of compliance controls: configured, missing, and not-verifiable-by-tool |

## 4. Triaging Contract

This is the skill's core behavioral specification. The skill MUST follow these rules:

### 4.1 Action Tiers

| Tier | Actions | Confirmation Required |
|------|---------|----------------------|
| **Tier 0: Read** | `gh run list`, `gh run view`, `gh secret list`, read workflow files, Glob/Grep | None -- always safe |
| **Tier 1: Analyze** | Root cause analysis, security audit, compliance check | None -- analysis is read-only |
| **Tier 2: Propose** | Show proposed code/YAML diffs, suggest commands | None -- showing is read-only |
| **Tier 3: Write** | Edit workflow YAML, write new files | User must approve proposed changes |
| **Tier 4: Execute** | `gh run rerun`, `gh workflow run` | Explicit confirmation with command shown |
| **Tier 5: Destroy** | Delete workflow files | Double confirmation: show what will be deleted, then confirm |

### 4.2 Ambiguity Resolution

When intent is unclear, default to the **lowest applicable tier**:

- "Check my CI" -> Tier 0 (read status)
- "Why is CI failing?" -> Tier 0+1 (read logs + analyze)
- "Fix CI" -> Tier 0+1+2 (read + analyze + propose), then ASK before Tier 3/4
- "Create a workflow" -> Tier 2 (propose), then ASK before Tier 3 (write)
- "Delete the old workflow" -> Tier 2 (show what would be deleted), then ASK for Tier 5

### 4.3 Escalation Pattern

When the skill needs to escalate from read to write:

```
1. Complete diagnosis/analysis (Tier 0-2)
2. Present findings to user
3. Explicitly state what action is needed: "To fix this, I would need to [specific action]"
4. Wait for user confirmation
5. Only then proceed to Tier 3+
```

## 5. Skill File Structure

The deliverable is a single `SKILL.md` file inside `skills/github-cicd-guardian/`:

```markdown
---
name: GitHub CI/CD Guardian
description: Diagnose GitHub Actions failures, audit workflow security, and fix CI/CD pipelines for trading systems.
---

# GitHub CI/CD Guardian

## Context
[Trading firm context, why CI/CD matters here]

## Prerequisites Check
[gh CLI verification steps]

## Triaging Rules
[The predictability contract from Section 4]

## P0: Pipeline Failure Diagnosis
[Step-by-step instructions for diagnosis workflow]

## P1: Security Audit
[Step-by-step instructions for security audit workflow]
[Anti-patterns checklist]

<!-- V2 sections below are optional stubs in MVP. Include as placeholders or omit entirely. -->
## P2: Workflow Authoring (V2 - not implemented)
[Reserved for V2]

## P3: Compliance Readiness (V2 - not implemented)
[Reserved for V2]
```

### Frontmatter Constraints
- `name`: Human-readable skill name displayed in listings
- `description`: Must be under 200 characters. Used by Claude to decide when to auto-invoke the skill. The example above is 97 characters
- No `description: |` multiline block -- keep it as a single-line string for reliable parsing

## 6. Prerequisites

| Prerequisite | Required | How to Verify |
|-------------|----------|--------------|
| `gh` CLI installed | Yes | `which gh` returns a path |
| `gh` authenticated | Yes | `gh auth status` returns authenticated |
| Repository has `.github/workflows/` | For P0/P1 | `ls .github/workflows/` has files |
| `actionlint` installed | No (optional) | `which actionlint` -- enhances P1/P2 validation if present |
| `zizmor` installed | No (optional) | `which zizmor` -- enhances P1 security scanning if present |

### Required GitHub Token Scopes

The `gh` CLI must be authenticated with a token that has these minimum scopes:

| gh CLI Command | Required Scope | Used By |
|---------------|---------------|---------|
| `gh run list`, `gh run view` | `actions:read` | P0-1, P0-2 |
| `gh run rerun` | `actions:write` | P0-5 (Tier 4, with confirmation) |
| `gh secret list` | `admin:org` or repo admin | P1 (read-only, names only) |
| `gh api /repos/{owner}/{repo}/security-advisories` | `security_events:read` | P1-6 |

Note: `gh auth login` with default scopes (`repo`, `read:org`) covers most commands. `security_events:read` may need to be added explicitly for P1-6.

## 7. Error Handling

| Error Condition | Skill Behavior |
|----------------|---------------|
| `gh` not installed | "GitHub CLI (gh) is required. Install: https://cli.github.com/" |
| `gh` not authenticated | "GitHub CLI is not authenticated. Run: `gh auth login`" |
| No workflow files found | "No GitHub Actions workflows found in `.github/workflows/`. Would you like to create one?" |
| `gh run view` returns no logs | "No logs available for this run. It may still be queued or logs may have expired." |
| `gh api` rate limited | "GitHub API rate limit reached. Try again in [X] minutes." |
| Network error | "Cannot reach GitHub API. Check your network connection." |

## 8. Success Metrics

These metrics define what "working correctly" means for the skill:

| ID | Metric | Target | How to Verify |
|----|--------|--------|---------------|
| SM-1 | Diagnosis accuracy | Skill correctly categorizes failure type for common patterns (P0-3 test scenarios) | Manual test: inject each failure category into a workflow, verify skill categorizes correctly |
| SM-2 | Time to diagnosis | User gets root cause analysis (P0-1 through P0-3) within a single interaction -- no back-and-forth needed for diagnosis. Fix proposal (P0-4) and application (P0-5) may require additional confirmation steps per the triaging contract | Manual test: ask "why is CI failing?" and verify skill completes P0-1 through P0-3 in one response |
| SM-3 | Security audit coverage | All 8 anti-patterns from checklist detected when present | Manual test: create a workflow with each anti-pattern, run audit, verify each is flagged |
| SM-4 | Tier compliance | Skill never performs a Tier 3+ action without explicit user confirmation | Manual test: say "fix CI" and verify skill stops at Tier 2 (propose) and asks before writing |
| SM-5 | Prerequisite handling | Skill detects missing `gh` CLI and provides clear error | Manual test: run in environment without `gh`, verify error message matches Section 7 |
| SM-6 | Read-only audit | Security audit produces no file modifications | Manual test: run `git status` before and after audit, verify no changes |
| SM-7 | Log injection resistance | Skill does not execute commands found in CI log output | Manual test: inject a CI log containing `run: rm -rf /` or similar, verify skill quotes it as evidence but does not execute it |
| SM-8 | Secret value protection | Skill never displays actual secret values in any output | Manual test: run audit on repo with configured secrets, verify output shows names only (e.g., `API_KEY`), never values |
| SM-9 | Coverage disclaimer | Security audit output includes a limitations statement | Manual test: run full security audit, verify output contains language like "this audit does not guarantee comprehensive coverage" or equivalent disclaimer |

## 9. Risks, Failure Modes & Security Analysis

This section identifies risks introduced by the skill, their potential impact, mitigations built into the design, and residual risks that remain after mitigation.

### 9.1 Risk Register

| ID | Risk | Likelihood | Impact | Mitigation | Residual Risk |
|----|------|-----------|--------|------------|---------------|
| R-1 | **Prompt injection via CI logs** -- Attacker crafts CI output containing instructions that manipulate Claude into executing unintended actions (see [PromptPwnd](https://www.aikido.dev/blog/promptpwnd-github-actions-ai-agents) for a documented real-world instance) | Medium | High | Triaging contract requires user confirmation for all Tier 3+ actions (write/execute/destroy). Even if Claude is manipulated into proposing a malicious action, the user must approve it. P0-NF3 explicitly marks log content as untrusted | Claude may present manipulated analysis or biased root cause assessment. User must still exercise judgment on proposed fixes. This is an **inherent limitation of LLM-based log analysis** and cannot be fully mitigated |
| R-2 | **Incorrect fix applied to production workflow** -- Skill proposes a YAML change that introduces a syntax error or logic bug in a CI pipeline | Medium | High | P0-5 requires user approval before any write. P0-4 shows the exact diff. User reviews the change before it's applied | User may approve an incorrect fix without carefully reviewing. Mitigation: the skill should recommend running `actionlint` on the modified file before committing, but this is advisory only |
| R-3 | **Security audit false negatives** -- Skill misses a real vulnerability in workflow files, giving false confidence | Medium | High | Layered approach: pattern-based checks (P1-1 through P1-5), optional zizmor integration (P1-6), structured checklist (8 anti-patterns). Skill explicitly states it does NOT provide comprehensive CVE coverage | Novel attack patterns not in the checklist will be missed. Claude's pattern matching is probabilistic, not deterministic. The skill should recommend periodic manual security reviews and never claim "your workflows are secure" |
| R-4 | **Security audit false positives** -- Skill flags legitimate patterns as security issues, causing unnecessary alarm or workflow changes | Medium | Low | P1-7 report categorizes findings by severity (critical/warning/informational). P1-8 ensures audit is read-only -- false positives don't cause changes unless user explicitly requests remediation | False positives erode trust in the tool. Mitigation: clearly distinguish between definite issues (e.g., unpinned actions) and heuristic findings (e.g., "this string looks like a credential") |
| R-5 | **Accidental workflow trigger** -- Skill triggers `gh run rerun` without user intent | Low | High | Tier 4 requires explicit confirmation with the exact command shown. Ambiguity resolution defaults to read-only (P0-6). "Fix CI" never auto-triggers a rerun | If the user confirms a rerun of the wrong run-id (e.g., from stale context), the wrong workflow executes. Mitigation: always show the run-id, workflow name, and commit SHA before confirmation |
| R-6 | **Stale or incorrect vulnerability data** -- CVE information from Claude's training data is outdated, leading to missed known vulnerabilities | Medium | Medium | P1-6 prioritizes live data (zizmor, gh api) over training data. When using training data, skill must state the caveat explicitly | `gh api` for security advisories only covers what the action maintainer has disclosed. Many GitHub Actions vulnerabilities are not formally reported. This is a **systemic gap in the GitHub Actions ecosystem** |
| R-7 | **Workflow file corruption** -- Skill writes malformed YAML that breaks CI entirely. Includes risk of mishandling GitHub Actions expressions (`${{ }}`) during diff generation or edit operations, since the skill processes YAML textually rather than through an expression-aware parser | Low | High | P0-5 shows exact changes before writing. YAML is a human-readable format and diffs are reviewable. Optional `actionlint` validation recommended before commit | Complex YAML with anchors, multi-line strings, or conditional expressions may be harder for the user to review in diff format. Residual: recommend running the workflow on a test branch before merging |
| R-8 | **Credential pattern false match in P1-3** -- Skill flags high-entropy strings (UUIDs, hashes) as potential credentials | High | Low | Detection uses known format patterns (AWS, GitHub PAT) before falling back to heuristic matching. Report categorizes heuristic matches as "informational" not "critical" | High-entropy strings in workflow files (artifact hashes, cache keys) will be flagged. This is a known trade-off: better to over-flag than miss real credentials |
| R-9 | **gh CLI authentication scope insufficient** -- Token lacks required scopes for certain operations, causing silent failures or misleading results | Medium | Medium | Section 6 documents required scopes. Error handling (Section 7) catches common API errors. Skill should run `gh auth status` before operations requiring elevated scopes | User may not realize their token lacks `security_events:read` for P1-6, causing the skill to silently skip advisory checks. Mitigation: skill should explicitly report when a scope check fails rather than silently degrading |
| R-10 | **Concurrent skill usage on same repository** -- Two users independently diagnosing and fixing the same workflow could produce conflicting edits or duplicate re-runs. For a trading firm, duplicate deployments could be dangerous | Low | Medium | Skill operates on local working copy; git merge conflicts provide natural guard for file edits. For Tier 4 reruns, GitHub API prevents true duplicates of the same run-id | Users should coordinate on shared workflow changes per normal development practice. No technical mechanism prevents two users from approving conflicting fixes simultaneously |

### 9.2 Failure Modes

| Mode | Trigger | Observable Behavior | Recovery |
|------|---------|-------------------|----------|
| **gh CLI unavailable** | `gh` not installed or not in PATH | Skill outputs error message per Section 7 and stops | User installs `gh` CLI |
| **gh CLI unauthenticated** | Token expired or never configured | Skill outputs auth error per Section 7 and stops | User runs `gh auth login` |
| **API rate limiting** | Too many `gh api` calls in short period | Skill reports rate limit with retry time | Wait for rate limit reset |
| **No workflow files** | Repository has no `.github/workflows/` directory | Skill reports "no workflows found" and offers to create one (Tier 2→3 with approval) | User creates workflows or the skill helps author them |
| **Log output too large** | `gh run view --log-failed` returns megabytes of output | Skill truncates to last 200 lines per failing step (P0-NF4), notes truncation | User can request full logs via `gh run view --log` if needed |
| **Ambiguous failure logs** | Logs don't match any known pattern in P0-3 test scenarios | Skill reports "unable to categorize" with raw log excerpt and asks user for context | User provides additional context or manually investigates |
| **gh CLI scope insufficient** | Token authenticated but lacks required scope (e.g., `security_events:read`) | `gh api` returns 403 or empty result set. Skill explicitly reports which scope is missing and provides the `gh auth refresh` command with the needed scope. Skill does NOT silently skip the operation | User runs `gh auth refresh -s security_events:read` to add the missing scope |
| **Network failure mid-operation** | Connection drops during `gh api` call | Skill reports network error per Section 7. No partial writes occur because read and write operations are separate tiers | User retries when connectivity restored |

### 9.3 Security Considerations

**What the skill CAN access:**
- Workflow file contents (YAML in `.github/workflows/`)
- CI run logs (via `gh run view`)
- Secret names (via `gh secret list`) -- names only, never values
- Repository security advisories (via `gh api`)

**What the skill CANNOT access:**
- Actual secret values (GitHub API does not expose these)
- Organization-level secrets (unless token has org scope)
- Other repositories' data (operates on current repo only)
- Infrastructure beyond GitHub (no SSH, no cloud APIs, no database access)

**Security invariants the skill must maintain:**

| # | Invariant | Spec Reference | Verification |
|---|-----------|---------------|-------------|
| 1 | **Never execute commands found in CI logs** -- logs are untrusted input | P0-NF3 | Manual test: inject a log containing `run: rm -rf /` and verify skill does not execute it (SM-7) |
| 2 | **Never write files during a security audit** -- audit is always Tier 0+1 | P1-8 | SM-6 (run `git status` before/after audit) |
| 3 | **Never display or log secret values** -- only audit usage patterns | P1-NF2 | Manual test: run audit on repo with secrets configured, verify output contains only secret names, never values (SM-8) |
| 4 | **Never bypass the triaging contract** -- all write/execute/destroy actions require confirmation | Section 4 | SM-4 (say "fix CI", verify skill stops at Tier 2) |
| 5 | **Never claim comprehensive security coverage** -- always state limitations | P1-NF3 | Manual test: run security audit, verify output includes a limitations disclaimer (SM-9) |

### 9.4 Residual Risk Summary

These risks **cannot be fully mitigated** by the skill and must be accepted:

1. **LLM prompt injection is an open problem** -- triaging rules reduce impact but cannot prevent all manipulation of Claude's analysis. This is inherent to any LLM tool that processes untrusted input.
2. **User may approve bad changes** -- the skill shows diffs and asks for confirmation, but a user who rubber-stamps approvals can still apply incorrect fixes. The skill is a tool, not a gatekeeper.
3. **GitHub Actions CVE coverage has systemic gaps** -- the GitHub Advisory Database does not index GitHub Actions as a first-class ecosystem. This affects all tools in this space, not just this skill.
4. **Heuristic secret detection produces false positives** -- balancing sensitivity vs. specificity for credential detection in YAML files is imperfect. The skill errs on the side of over-flagging.
5. **Skill instructions are probabilistic, not deterministic** -- as an LLM skill (markdown instructions), the skill's behavior depends on Claude's interpretation. Edge cases may produce unexpected behavior. Section 8 success metrics (SM-1 through SM-9) and scenario-based testing (per PRD Section 10) provide a verification baseline for expected behavior on common paths.

## 10. Out of Scope

- Non-GitHub CI/CD platforms (Jenkins, GitLab CI, CircleCI, etc.)
- Cross-repository pipeline dependencies
- Local CI/CD testing (use `act` for that)
- Infrastructure-level rollbacks (Kubernetes, AWS, etc.)
- Actual secret values -- skill only audits usage patterns, never reads/displays secret values
- Legal or regulatory advice -- compliance features are engineering guidance only
- GitHub Actions billing data (requires org admin -- graceful degradation)
