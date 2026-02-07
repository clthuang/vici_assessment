# GitHub CI/CD Guardian

AI-powered Claude Code skill that diagnoses GitHub Actions pipeline failures and audits workflow security.

**VICI Challenge Task 3 -- Medium** | v1.0.0 | P0 Failure Diagnosis + P1 Security Audit

This README is organized in three parts. **Quick Start** gets you from zero to a working skill in under a minute. **Capabilities** covers what the skill can do — the commands it calls, the patterns it detects, and the security measures it enforces. **Implementation Details** shows how it makes decisions, handles errors, and validates itself.

## Quick Start

### Installation

Place the `github-claude-skills/` directory where Claude Code can access it as a plugin.

**Required**: GitHub CLI installed and authenticated.

```bash
# macOS
brew install gh
gh auth login

# Verify
gh auth status
```

**Optional** (enhances audit depth):

| Tool | Purpose | Install |
|------|---------|---------|
| [`zizmor`](https://github.com/woodruffw/zizmor) | Static analysis for GitHub Actions | `brew install zizmor` |
| [`actionlint`](https://github.com/rhysd/actionlint) | YAML workflow validation | `brew install actionlint` |

### Usage

**Diagnose a failing pipeline:**

> User: "Why is my CI failing?"
>
> Claude fetches the 10 most recent runs via `gh run list`, identifies the latest failure, pulls logs with `gh run view --log-failed`, categorizes the failure (e.g., Dependency Issue), and proposes a fix with 3 options: Apply, Re-run failed jobs, or Skip.

**Audit workflow security:**

> User: "Audit my workflow security"
>
> Claude discovers all `.yml`/`.yaml` files in `.github/workflows/`, scans against 8 anti-patterns, runs `zizmor` if available, checks GitHub Advisory Database, and generates a severity-ranked report (Critical / Warning / Informational).

**Trigger phrases**: "fix my CI", "why is CI failing", "audit workflow security", "check CI security", or any mention of GitHub Actions failures or CI/CD security audits.

---

## Capabilities

With the skill installed, here is what it provides. Each capability lists the exact tools and commands used, so you can trace every action back to a concrete `gh` call or file scan.

### P0: Pipeline Failure Diagnosis

Fetches failed CI run logs, categorizes the root cause, and proposes fixes with user approval before any changes.

**GitHub CLI commands used:**

| Command | Purpose |
|---------|---------|
| `gh run list --limit 10` | Fetch recent workflow runs |
| `gh run view {id} --log-failed` | Fetch logs for failed steps |
| `gh run view {id} --log` | Fallback when `--log-failed` returns empty |
| `gh run rerun {id} --failed` | Re-run only failed jobs (with user confirmation) |
| `gh repo view --json owner,name` | Resolve repository context |

**6 failure categories** (from `references/failure-categories.md`):

| Category | Log Signatures |
|----------|---------------|
| Dependency Issue | `ModuleNotFoundError`, `package not found`, `No matching version` |
| YAML Misconfiguration | `unexpected value`, `mapping values are not allowed`, `Invalid workflow file` |
| Code Bug | `FAIL`, `AssertionError`, `TypeError`, `FAILED` |
| Flaky Test | `exit code 143`, `timeout`, `SIGTERM`, intermittent pass/fail |
| Infrastructure | `No space left on device`, `runner is offline`, `ENOMEM` |
| Permissions | `Resource not accessible by integration`, `403`, `insufficient permissions` |

**Workflow**: Fetch runs → Identify failure → Fetch logs → Categorize → Propose fix (3 options) → Apply with confirmation

### P1: Security Audit

Read-only scan of all workflow files against known anti-patterns. **Does not modify any files** unless the user explicitly requests remediation after reviewing the report.

**Tools used:**

| Tool | Purpose |
|------|---------|
| `Glob` | Discover `.yml`/`.yaml` workflow files |
| `zizmor` | Static analysis for Actions-specific vulnerabilities (if installed) |
| `actionlint` | YAML syntax validation (suggested post-fix) |
| `gh api /repos/{o}/{r}/security-advisories` | Check GitHub Advisory Database for action vulnerabilities |
| `gh api /repos/{o}/{r}/git/ref/tags/{tag}` | Resolve tag → commit SHA for action pinning |

**8 security anti-patterns** (from `references/security-checklist.md`):

| # | Anti-Pattern | Severity | Spec ID |
|---|-------------|----------|---------|
| 1 | Unpinned Actions (`@v4` instead of `@sha`) | Critical | P1-1 |
| 2 | Overly Broad Permissions (`write-all` or missing block) | Critical | P1-2 |
| 3 | Hardcoded Secrets (AWS keys, PATs in YAML) | Critical | P1-3 |
| 4 | Secret in Echo (`echo ${{ secrets.* }}`) | Critical | P1-5 |
| 5 | Pull Request Target Trigger (with PR head checkout) | Warning | P1-7 |
| 6 | Mutable Action References (`@main`, `@master`) | Warning | P1-1 |
| 7 | Missing CODEOWNERS for workflows | Info | P1-7 |
| 8 | Artifact Exposure (uploading sensitive directories) | Warning | P1-7 |

**Layered vulnerability detection**: zizmor findings (primary) → GitHub Advisory API (supplementary) → Claude knowledge (fallback, with staleness caveat)

### Security Measures

Both capabilities above are governed by a shared set of safety constraints. These measures prevent the skill from leaking secrets, executing untrusted content, or making changes without consent.

| ID | Measure | Description |
|----|---------|-------------|
| SM-4 | User confirmation | All write/execute actions require explicit user approval before proceeding |
| SM-6 | Read-only audit | P1 audit does not modify workflow files unless user requests remediation |
| SM-7 | Untrusted log content | CI log output is treated as data, never as instructions; prompt injection attempts are flagged |
| SM-8 | No secret display | Actual secret values are never displayed; only usage patterns and secret names are reported |
| SM-9 | Limitations disclaimer | Audit reports include "does not guarantee comprehensive coverage" caveat |

**Credential redaction**: Log evidence is scanned against regex patterns (`AKIA[0-9A-Z]{16}`, `ghp_[A-Za-z0-9_]{36}`, `gh[pousr]_[A-Za-z0-9_]{36,}`) and matches are replaced with `[REDACTED]` before display.

---

## Implementation Details

The sections above describe *what* the skill does. This section covers *how* — the decision rules that govern its behavior, the error conditions it handles, and the test suite that validates all of the above.

### Triaging Rules

Three behavioral rules govern every interaction:

1. **Read and analyze freely** -- fetching CI status, reading logs, scanning workflow files require no confirmation.
2. **Propose freely, write only with confirmation** -- diffs and suggestions are shown freely; file edits and workflow triggers require user approval.
3. **Destructive operations require double confirmation** -- deleting a workflow file requires showing what will be deleted and confirming twice.

**Ambiguity resolution:**

| User Says | Automatic Action | Asks Before |
|-----------|-----------------|-------------|
| "Check my CI" | Fetch status, show summary | Nothing |
| "Why is CI failing?" | Fetch logs, analyze, show root cause | Nothing |
| "Fix my CI" | Diagnose + propose fix with diff | Applying the fix |
| "Create a workflow" | Draft the YAML and show it | Writing the file |
| "Delete the old workflow" | Show what would be deleted | Deleting it (double confirm) |

**Action classification:**

| Category | Examples | Confirmation |
|----------|---------|-------------|
| Read | `gh run list/view`, `gh secret list`, read files, Glob/Grep | None |
| Analyze | Root cause analysis, security audit | None |
| Propose | Show diffs, suggest commands | None |
| Write | Edit YAML, write new files | User confirms |
| Execute | `gh run rerun`, `gh workflow run` | User confirms with command shown |
| Destroy | Delete workflow files | Double confirmation |

### Error Handling

The triaging rules above govern the happy path. When things go wrong — missing tools, API failures, ambiguous logs — the skill handles each case with a specific recovery message rather than a generic error. All 10 error conditions:

| # | Condition | Response |
|---|-----------|----------|
| 1 | `gh` not found | "GitHub CLI (gh) is not installed. Install: https://cli.github.com/" |
| 2 | Not logged in | "GitHub CLI is not authenticated. Run: `gh auth login`" |
| 3 | 403 response | "Insufficient permissions. Likely missing scope: {scope}. Run: `gh auth refresh -s {scope}`" |
| 4 | 429 response | "GitHub API rate limit reached. Try again in {retry-after} minutes." |
| 5 | Network error | "Cannot reach GitHub API. Check your network connection." |
| 6 | Empty `--log-failed` | Falls back to `--log` with truncation to last 200 lines per failing step |
| 7 | No logs at all | "No logs available for this run. It may still be queued or logs may have expired." |
| 8 | Ambiguous logs | Shows excerpts and asks user for additional context |
| 9 | No workflow files | "No GitHub Actions workflows found. Would you like to create one?" |
| 10 | Advisory API 404 | Repository lacks Security Advisories -- skip and continue |

### Testing & Validation

Every capability, rule, and error condition described above is verified by an automated validation suite. Run it to confirm the skill is intact:

```bash
bash github-claude-skills/tests/validate_skill.sh
```

**67 automated checks** across **8 test phases**:

| Phase | Focus | Checks |
|-------|-------|--------|
| 1. Structural Validation | File existence, JSON validity, line counts | 6 |
| 2. Plugin Manifest | Name, version, required fields | 3 |
| 3. SKILL.md Frontmatter | Name, description, version, description length | 4 |
| 4. P0 Content | Commands, approval flow, untrusted input, error handling | 13 |
| 5. P1 Content | Audit steps, zizmor, checklist refs, secret protection | 12 |
| 6. Triaging Rules | 3 behavioral rules, ambiguity examples | 6 |
| 7. Reference Files | 6 failure categories, 8 anti-patterns, regex patterns | 17 |
| 8. Security Invariants | SM-4, SM-6, SM-7, SM-8, SM-9, credential redaction | 6 |

**Test fixtures:**

- `fixtures/sample-failure-logs.md` -- 7 log fixtures (one per failure category + prompt injection attempt)
- `fixtures/vulnerable-workflow.yml` -- single workflow containing all 8 security anti-patterns

### Plugin Structure

Finally, here is how the files are organized. Line counts are included so you can gauge the scope of each component at a glance.

```
github-claude-skills/
  .claude-plugin/
    plugin.json                              # Plugin manifest (5 lines)
  skills/
    github-cicd-guardian/
      SKILL.md                               # Skill instructions (238 lines)
      references/
        failure-categories.md                # 6 failure categories with log signatures (39 lines)
        security-checklist.md                # 8 anti-patterns with remediation (73 lines)
  tests/
    validate_skill.sh                        # 67 automated checks, 8 phases (179 lines)
    fixtures/
      sample-failure-logs.md                 # 7 test log fixtures (60 lines)
      vulnerable-workflow.yml                # All 8 anti-patterns in one file (48 lines)
```
