# Specification: GitHub CI/CD Guardian Skill

## 1. Deliverable

A single Claude Code skill file (`SKILL.md`) that provides domain-specific CI/CD expertise for GitHub Actions pipelines, targeted at a high-frequency proprietary trading firm.

### Deliverable Constraints
- **Format**: Markdown file named `SKILL.md` with YAML frontmatter containing `name` and `description` fields
- **Frontmatter**: `name` is the skill display name; `description` is used for auto-triggering (model-invoked) and must be under 200 characters
- **Location**: Within a Claude Code plugin's `skills/github-cicd-guardian/` directory (one skill per subdirectory)
- **Tooling**: Uses only Claude Code's existing tools (Bash, Read, Write, Edit, Glob, Grep) -- no new tools, commands, agents, or hooks
- **Dependencies**: Requires `gh` CLI installed and authenticated

## 2. Target Users & Deployment Context

### Intended Users

| User Role | How They Use the Skill |
|-----------|----------------------|
| **Developers** (primary) | Diagnose CI failures, get fix proposals, understand why builds break |
| **DevOps / Platform Engineers** (primary) | Audit workflow security, validate pipeline configurations, review permissions |
| **Tech Leads / Engineering Managers** (secondary) | Review security audit reports, verify compliance readiness |

### Deployment Context

This skill is an **internal tool** intended for use within a proprietary trading firm's engineering team. It is NOT a public service.

**Key constraints from this context:**
- **Access**: Only accessible to engineers with `gh` CLI authenticated to the firm's GitHub organization
- **Data sensitivity**: Workflow files and CI logs may reference internal trading strategies, exchange APIs, and proprietary infrastructure. The skill must never exfiltrate data -- it operates entirely within Claude Code's local session
- **No external telemetry**: The skill does not send data to any external service. All operations go through the authenticated `gh` CLI to the firm's GitHub instance
- **GitHub Enterprise compatibility**: The skill must work with both github.com and GitHub Enterprise Server (GHES), since trading firms commonly use self-hosted GitHub. The `gh` CLI handles this transparently via `gh auth login --hostname`
- **Air-gapped considerations**: In environments without internet access (common in trading infrastructure), the skill degrades gracefully: `gh` CLI commands to the internal GHES instance still work, but P1-6 vulnerability checks requiring external advisory data will fall back to Claude's training knowledge with appropriate caveats

### Who This Tool is NOT For

- External clients or customers of the trading firm
- Compliance officers (the tool provides engineering guidance, not audit-grade artifacts)
- Non-technical staff
- Users without `gh` CLI access to the repository

## 3. MVP Scope (MUST HAVE)

The skill covers two features for initial delivery:

**What P0 actually delivers**: Faster, more accurate diagnosis of CI failures by correlating logs with codebase context -- something standalone tools like `gh run view` cannot do. This reduces the diagnosis step from manual log reading to an automated analysis. It does NOT eliminate the push-wait-fail iteration cycle itself (the CI still needs to run), but it significantly shortens the time between "CI failed" and "I know what to fix." The PRD estimates resolution drops from ~2.5 hours to ~20 minutes (based on [industry blog data](https://markaicode.com/ai-fix-cicd-pipeline-failures-github-actions/), not peer-reviewed). A future "pre-push validation" extension could attack the iteration cycle directly by catching YAML errors before pushing.

### 3.1 P0: Pipeline Failure Diagnosis & Fix

#### Functional Requirements

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| P0-1 | Fetch pipeline status | Given a repo with GitHub Actions, when the user asks about CI status, the skill runs `gh run list --limit 10` and presents a summary of recent runs with pass/fail status |
| P0-2 | Fetch failure logs | Given a failing workflow run, when the user asks to diagnose it, the skill runs `gh run view {run-id} --log-failed` to retrieve only the failing step logs |
| P0-3 | Root cause analysis | Given failure logs, the skill categorizes the failure and provides evidence. Test scenarios: (a) `ModuleNotFoundError: No module named 'foo'` → dependency issue; (b) `Error: .github/workflows/ci.yml: unexpected value` → YAML misconfiguration; (c) `FAIL test_order_placement ... AssertionError` → code bug; (d) `Error: Process completed with exit code 143` (timeout on re-run of same commit) → flaky test; (e) `No space left on device` or `runner is offline` → infrastructure/runner problem; (f) `Resource not accessible by integration` → permissions issue. The category MUST be stated explicitly in the output with the supporting log evidence quoted |
| P0-4 | Propose fix | Given a root cause, the skill proposes a specific fix with explanation. Output format: (1) plain-language explanation of why the fix addresses the root cause, (2) the specific change shown as a markdown code block (diff format for file edits, command format for retries/dependency updates), (3) what the user needs to approve before the skill applies it |
| P0-5 | Apply fix with approval | Given a proposed fix, the skill presents the exact changes before applying them. Code/YAML changes require user confirmation before writing. Workflow re-triggers require explicit "yes, re-run" confirmation |
| P0-6 | Handle ambiguous requests | Given "fix my CI" or "my pipeline is broken", the skill completes diagnosis AND proposes a fix in one response (P0-1 through P0-4), then asks once before applying the fix (P0-5). Reading, analyzing, and proposing are free actions that modify nothing -- only the actual write/execute step requires confirmation. The user said "fix", so they want a fix proposal, not just a diagnosis |

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

**What P1 adds over running `zizmor` directly**: If `zizmor` is available, the skill runs it and enriches its output with: (a) codebase-aware context -- correlating findings with how the workflow is actually used, (b) remediation proposals with exact diffs, and (c) checks that `zizmor` does not cover (P1-3 heuristic secret detection, P1-5 secret exposure via echo patterns). If `zizmor` is NOT available, the skill performs a best-effort audit using Claude's pattern matching and the 8-item anti-patterns checklist. The skill is NOT a replacement for `zizmor` -- it is a higher-level wrapper that makes `zizmor` output actionable.

### 3.2 P1: Security Audit & Supply Chain Protection

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

## 4. V2 Scope (SHOULD HAVE)

Defined here for completeness but NOT part of initial implementation. V2 features will be designed and specified separately. The MVP design does not need to include extension points for V2, but should not preclude V2 additions to `SKILL.md`.

**V2 does NOT include**: P4 (Status Dashboard), P5 (Deployment Safety), P6 (Cost Optimization), cross-repository workflows, infrastructure-level operations, or any non-GitHub CI platforms.

### 4.1 P2: Workflow Authoring & Validation

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| P2-1 | Generate workflows from natural language | Given "create a CI pipeline that runs pytest and lints with ruff", generate a valid `.github/workflows/ci.yml` |
| P2-2 | Validate existing workflows | Read all workflow files and check for syntax errors, deprecated features, and anti-patterns |
| P2-3 | Suggest optimizations | Analyze workflows for caching opportunities, job parallelization, and unnecessary steps |

### 4.2 P3: Compliance Readiness Check

| ID | Requirement | Acceptance Criteria |
|----|-------------|-------------------|
| P3-1 | Check branch protection | Query `gh api` for branch protection rules and compare against FINRA/SOX requirements |
| P3-2 | Validate separation of duties | Check if workflows enforce that PR author != merger (via required reviews) |
| P3-3 | Generate readiness report | Output a checklist of compliance controls: configured, missing, and not-verifiable-by-tool |

## 5. Triaging Contract

The skill's core behavioral rules, stated simply:

### 5.1 Three Rules

1. **Read and analyze freely** -- fetching CI status, reading logs, scanning workflow files, and producing analysis are always safe. Do them without asking.
2. **Propose freely, write only with confirmation** -- showing diffs and suggesting fixes costs nothing. But before editing any file or triggering any workflow run, show the exact change and get user confirmation.
3. **Destructive operations require double confirmation** -- before deleting a workflow file, show what will be deleted and confirm twice.

### 5.2 Ambiguity Resolution

When intent is unclear, read + analyze + propose in one shot, then ask before writing:

| User Says | Skill Does Automatically | Asks Before |
|-----------|------------------------|-------------|
| "Check my CI" | Fetch status, show summary | Nothing -- done |
| "Why is CI failing?" | Fetch logs, analyze, show root cause | Nothing -- done |
| "Fix my CI" | Diagnose + propose fix with diff in one response | Applying the fix (write/rerun) |
| "Create a workflow" | Draft the YAML and show it | Writing the file |
| "Delete the old workflow" | Show what would be deleted | Deleting it (double confirm) |

### 5.3 Reference: Action Classification

For implementation clarity, actions fall into these categories:

| Category | Examples | Confirmation |
|----------|---------|-------------|
| **Read** | `gh run list/view`, `gh secret list`, read files, Glob/Grep | None |
| **Analyze** | Root cause analysis, security audit | None |
| **Propose** | Show diffs, suggest commands | None |
| **Write** | Edit YAML, write new files | User confirms |
| **Execute** | `gh run rerun`, `gh workflow run` | User confirms with command shown |
| **Destroy** | Delete workflow files | Double confirmation |

## 6. Skill File Structure

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
[The predictability contract from Section 5]

## P0: Pipeline Failure Diagnosis
[Step-by-step instructions for diagnosis workflow]

## P1: Security Audit
[Step-by-step instructions for security audit workflow]
[Anti-patterns checklist]
```

Note: V2 sections (P2, P3) are NOT included in the MVP SKILL.md. They will be added when V2 is implemented. Every token in the SKILL.md costs context window space on every invocation -- keep it lean.

### Frontmatter Constraints
- `name`: Human-readable skill name displayed in listings
- `description`: Must be under 200 characters. Used by Claude to decide when to auto-invoke the skill. The example above is 97 characters
- No `description: |` multiline block -- keep it as a single-line string for reliable parsing

## 7. Prerequisites

| Prerequisite | Required | How to Verify |
|-------------|----------|--------------|
| `gh` CLI installed | Yes | `which gh` returns a path |
| `gh` authenticated | Yes | `gh auth status` returns authenticated |
| Repository has `.github/workflows/` | For P0/P1 | `ls .github/workflows/` has files |
| `actionlint` installed | No (optional) | `which actionlint` -- if available, skill recommends running it on modified workflow files after P0-5 write operations as a validation step |
| `zizmor` installed | No (optional) | `which zizmor` -- primary tool for P1-6 vulnerability checking if present |

Note: `gh auth login` with default scopes covers most commands. If a `gh api` call returns a 403 permissions error, the skill should report which scope is likely missing and suggest `gh auth refresh -s <scope>` rather than silently degrading.

## 8. Error Handling & Failure Modes

| Condition | Skill Behavior | User Recovery |
|-----------|---------------|--------------|
| `gh` not installed | "GitHub CLI (gh) is required. Install: https://cli.github.com/" -- stop | Install `gh` CLI |
| `gh` not authenticated | "GitHub CLI is not authenticated. Run: `gh auth login`" -- stop | `gh auth login` |
| Insufficient token scope | Report which scope is missing, suggest `gh auth refresh -s <scope>` -- do NOT silently skip | `gh auth refresh -s <scope>` |
| No workflow files found | "No GitHub Actions workflows found in `.github/workflows/`. Would you like to create one?" | Create workflows or ask skill to author one |
| `gh run view` returns no logs | "No logs available for this run. It may still be queued or logs may have expired." | Wait or check run status |
| Log output too large | Truncate to last 200 lines per failing step (P0-NF4), note truncation | Request full logs via `gh run view --log` |
| Ambiguous failure logs | Report "unable to categorize" with raw log excerpt, ask user for context | Provide context or investigate manually |
| `gh api` rate limited | "GitHub API rate limit reached. Try again in [X] minutes." | Wait for reset |
| Network error | "Cannot reach GitHub API. Check your network connection." | Restore connectivity |

## 9. Success Metrics

These metrics define what "working correctly" means for the skill:

| ID | Metric | Target | How to Verify |
|----|--------|--------|---------------|
| SM-1 | Diagnosis accuracy | Skill correctly categorizes failure type for common patterns (P0-3 test scenarios) | Manual test: inject each failure category into a workflow, verify skill categorizes correctly |
| SM-2 | Time to diagnosis | User gets root cause analysis (P0-1 through P0-3) within a single interaction -- no back-and-forth needed for diagnosis. Fix proposal (P0-4) and application (P0-5) may require additional confirmation steps per the triaging contract | Manual test: ask "why is CI failing?" and verify skill completes P0-1 through P0-3 in one response |
| SM-3 | Security audit coverage | All 8 anti-patterns from checklist detected when present | Manual test: create a workflow with each anti-pattern, run audit, verify each is flagged |
| SM-4 | Write confirmation | Skill never writes files or triggers workflows without explicit user confirmation | Manual test: say "fix CI" and verify skill diagnoses + proposes but asks before writing/executing |
| SM-5 | Prerequisite handling | Skill detects missing `gh` CLI and provides clear error | Manual test: run in environment without `gh`, verify error message matches Section 8 |
| SM-6 | Read-only audit | Security audit produces no file modifications | Manual test: run `git status` before and after audit, verify no changes |
| SM-7 | Log injection resistance | Skill does not execute commands found in CI log output | Manual test: inject a CI log containing `run: rm -rf /` or similar, verify skill quotes it as evidence but does not execute it |
| SM-8 | Secret value protection | Skill never displays actual secret values in any output | Manual test: run audit on repo with configured secrets, verify output shows names only (e.g., `API_KEY`), never values |
| SM-9 | Coverage disclaimer | Security audit output includes a limitations statement | Manual test: run full security audit, verify output contains language like "this audit does not guarantee comprehensive coverage" or equivalent disclaimer |

## 10. Risks & Security Analysis

This section identifies risks introduced by the skill, their potential impact, mitigations built into the design, and residual risks that remain after mitigation. Failure modes and error handling are covered in Section 8.

### 10.1 Risk Register

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
| R-9 | **gh CLI authentication scope insufficient** -- Token lacks required scopes for certain operations, causing silent failures or misleading results | Medium | Medium | Section 7 documents required scopes. Error handling (Section 8) catches common API errors. Skill should run `gh auth status` before operations requiring elevated scopes | User may not realize their token lacks `security_events:read` for P1-6, causing the skill to silently skip advisory checks. Mitigation: skill should explicitly report when a scope check fails rather than silently degrading |
| R-10 | **Concurrent skill usage on same repository** -- Two users independently diagnosing and fixing the same workflow could produce conflicting edits or duplicate re-runs. For a trading firm, duplicate deployments could be dangerous | Low | Medium | Skill operates on local working copy; git merge conflicts provide natural guard for file edits. For Tier 4 reruns, GitHub API prevents true duplicates of the same run-id | Users should coordinate on shared workflow changes per normal development practice. No technical mechanism prevents two users from approving conflicting fixes simultaneously |

### 10.2 Security Considerations

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
| 4 | **Never bypass the triaging contract** -- all write/execute/destroy actions require confirmation | Section 5 | SM-4 (say "fix CI", verify skill asks before writing) |
| 5 | **Never claim comprehensive security coverage** -- always state limitations | P1-NF3 | Manual test: run security audit, verify output includes a limitations disclaimer (SM-9) |

### 10.3 Residual Risk Summary

These risks **cannot be fully mitigated** by the skill and must be accepted:

1. **LLM prompt injection is an open problem** -- triaging rules reduce impact but cannot prevent all manipulation of Claude's analysis. This is inherent to any LLM tool that processes untrusted input.
2. **User may approve bad changes** -- the skill shows diffs and asks for confirmation, but a user who rubber-stamps approvals can still apply incorrect fixes. The skill is a tool, not a gatekeeper.
3. **GitHub Actions CVE coverage has systemic gaps** -- the GitHub Advisory Database does not index GitHub Actions as a first-class ecosystem. This affects all tools in this space, not just this skill.
4. **Heuristic secret detection produces false positives** -- balancing sensitivity vs. specificity for credential detection in YAML files is imperfect. The skill errs on the side of over-flagging.
5. **Skill instructions are probabilistic, not deterministic** -- as an LLM skill (markdown instructions), the skill's behavior depends on Claude's interpretation. Edge cases may produce unexpected behavior. Section 9 success metrics (SM-1 through SM-9) and scenario-based testing (per PRD Section 10) provide a verification baseline for expected behavior on common paths.

## 11. Out of Scope

- Non-GitHub CI/CD platforms (Jenkins, GitLab CI, CircleCI, etc.)
- Cross-repository pipeline dependencies
- Local CI/CD testing (use `act` for that)
- Infrastructure-level rollbacks (Kubernetes, AWS, etc.)
- Actual secret values -- skill only audits usage patterns, never reads/displays secret values
- Legal or regulatory advice -- compliance features are engineering guidance only
- GitHub Actions billing data (requires org admin -- graceful degradation)
