# Architecture: GitHub CI/CD Guardian

This document is a technical onboarding guide for engineers contributing to the GitHub CI/CD Guardian skill plugin. It covers the plugin structure, component architecture with verified line references, data flows for both capabilities (P0 and P1), tool invocations, the testing architecture, and how to extend the skill. After reading it, you should be able to trace any behavior back to a specific file and line, understand why each component exists, and add new failure categories or security anti-patterns without breaking the validation suite.

## 1. System Overview

### 1.1 What This Plugin Is

The GitHub CI/CD Guardian is a **Claude Code skill plugin** -- it consists of markdown instruction files, not runtime code. When installed, Claude Code gains domain-specific CI/CD expertise: it can diagnose pipeline failures (P0) and audit workflow security (P1) using structured, repeatable procedures.

The skill is **model-invoked**: Claude Code automatically activates it when the user's request matches trigger phrases in the SKILL.md frontmatter (e.g., "fix my CI", "audit workflow security"). No slash command or explicit invocation is needed.

### 1.2 Plugin Discovery

Claude Code discovers plugins via the `.claude-plugin/plugin.json` manifest at the plugin root:

```
github-claude-skills/.claude-plugin/plugin.json
```

This 5-line JSON file declares the plugin name (`github-cicd-guardian`), description, and version. Claude Code reads it to register the plugin and then loads skills from the `skills/` subdirectories.

### 1.3 File Inventory

| File | Path | Lines | Purpose |
|------|------|-------|---------|
| Plugin manifest | `.claude-plugin/plugin.json` | 5 | Plugin discovery and registration |
| Skill instructions | `skills/github-cicd-guardian/SKILL.md` | 238 | Primary skill -- all behavioral rules and procedures |
| Failure categories | `skills/github-cicd-guardian/references/failure-categories.md` | 39 | 6 failure categories with log signatures (P0) |
| Security checklist | `skills/github-cicd-guardian/references/security-checklist.md` | 73 | 8 anti-patterns with remediation steps (P1) |
| Validation suite | `tests/validate_skill.sh` | 179 | 67 automated checks across 8 phases |
| Failure log fixtures | `tests/fixtures/sample-failure-logs.md` | 60 | 7 test log fixtures (6 categories + prompt injection) |
| Vulnerable workflow | `tests/fixtures/vulnerable-workflow.yml` | 48 | All 8 anti-patterns in one workflow file |

Now that you know where the files live, the next section explains how they connect.

## 2. Component Architecture

### 2.1 SKILL.md Structure

The skill file has 6 logical sections. Each section's line range is verified against the source:

| Section | Lines | Purpose |
|---------|-------|---------|
| Frontmatter | L1-5 | `name`, `description` (trigger phrases), `version` |
| Context | L9-11 | Sets CI/CD specialist persona and trading domain expertise |
| Prerequisites | L13-29 | `gh auth status` check, `{owner}/{repo}` resolution |
| Triaging Rules | L31-60 | 3 behavioral rules, ambiguity resolution table, action classification |
| P0: Pipeline Failure Diagnosis | L62-158 | 6-step diagnosis procedure with error handling |
| P1: Security Audit | L160-238 | 5-step audit procedure with report format |

### 2.2 Reference Files

**failure-categories.md** (39 lines): Contains the 6 failure categories with log signature patterns. Loaded by Claude at P0 Step 4 when SKILL.md instructs: "Read `references/failure-categories.md`" (SKILL.md L103). Categories: Dependency Issue, YAML Misconfiguration, Code Bug, Flaky Test, Infrastructure, Permissions.

**security-checklist.md** (73 lines): Contains the 8 security anti-patterns with detection patterns, examples, severity levels, and remediation steps. Loaded by Claude at P1 Step 3b when SKILL.md instructs: "Read `references/security-checklist.md`" (SKILL.md L199). Also contains the P1-3 credential regex patterns (L22-25): `AKIA[0-9A-Z]{16}`, `ghp_[A-Za-z0-9_]{36}`, `gh[pousr]_[A-Za-z0-9_]{36,}`.

### 2.3 Cross-File Reference Map

| SKILL.md Line | References | Purpose |
|---------------|------------|---------|
| L68 | `references/security-checklist.md` P1-3 regex | Credential redaction during P0 log quoting |
| L103 | `references/failure-categories.md` | P0 Step 4 failure categorization |
| L199 | `references/security-checklist.md` | P1 Step 3b anti-pattern checks |

### 2.4 Component Diagram

```mermaid
graph TB
    subgraph Plugin["github-claude-skills/"]
        PJ[".claude-plugin/plugin.json<br/><i>5 lines</i>"]

        subgraph SkillDir["skills/github-cicd-guardian/"]
            SM["SKILL.md<br/><i>238 lines</i>"]

            subgraph Refs["references/"]
                FC["failure-categories.md<br/><i>39 lines — 6 categories</i>"]
                SC["security-checklist.md<br/><i>73 lines — 8 anti-patterns</i>"]
            end
        end

        subgraph Tests["tests/"]
            VS["validate_skill.sh<br/><i>179 lines — 67 checks</i>"]
            subgraph Fixtures["fixtures/"]
                SFL["sample-failure-logs.md<br/><i>60 lines — 7 fixtures</i>"]
                VW["vulnerable-workflow.yml<br/><i>48 lines — 8 anti-patterns</i>"]
            end
        end
    end

    SM -->|"L103: Read"| FC
    SM -->|"L199: Read"| SC
    SM -->|"L68: regex from"| SC
    VS -->|validates| SM
    VS -->|validates| FC
    VS -->|validates| SC
```

Understanding the structure sets up the data flow section.

## 3. Data Flows

### 3.1 P0: Pipeline Failure Diagnosis

```mermaid
flowchart TD
    Start([User: CI question]) --> RunID{Run ID provided?}
    RunID -->|Yes| FetchLogs
    RunID -->|No| FetchStatus["Step 1: gh run list --limit 10"]
    FetchStatus --> Identify["Step 2: Select most recent failure"]
    Identify --> FetchLogs["Step 3: gh run view {id} --log-failed"]
    FetchLogs --> LogEmpty{Output empty?}
    LogEmpty -->|Yes| Fallback["gh run view {id} --log<br/>Truncate: last 200 lines/step"]
    LogEmpty -->|No| Categorize
    Fallback --> FallbackEmpty{Still empty?}
    FallbackEmpty -->|Yes| NoLogs["'No logs available' — STOP"]
    FallbackEmpty -->|No| Categorize["Step 4: Read failure-categories.md<br/>Match log patterns"]
    Categorize --> ClearMatch{Clear match?}
    ClearMatch -->|No| Ambiguous["Show excerpts, ask user"]
    ClearMatch -->|Yes| Propose["Step 5: Generate fix proposal<br/>3 options: Apply / Re-run / Skip"]
    Propose --> Confirm{User confirms?}
    Confirm -->|Apply| Write["Step 6: Write/Edit file<br/>Suggest actionlint"]
    Confirm -->|Re-run| Rerun["Step 6: gh run rerun {id} --failed"]
    Confirm -->|Skip| Done([Done])
    Write --> Done
    Rerun --> Done

    style FetchStatus fill:#4A90D9,color:#fff
    style Identify fill:#4A90D9,color:#fff
    style FetchLogs fill:#4A90D9,color:#fff
    style Categorize fill:#5BB5A2,color:#fff
    style Write fill:#E8943A,color:#fff
    style Rerun fill:#E8943A,color:#fff
```

**Step-by-step with tool references:**

| Step | Action | Tool | SKILL.md Lines | Confirmation |
|------|--------|------|---------------|-------------|
| 1 | Fetch recent runs (skip if run ID given) | `gh run list --limit 10` | L72-80 | None |
| 2 | Select most recent failure | Selection logic | L82-84 | None |
| 3 | Fetch logs (with `--log` fallback) | `gh run view {id} --log-failed` | L86-99 | None |
| 4 | Categorize against 6 patterns | Read `failure-categories.md` | L101-109 | None |
| 5 | Generate fix proposal with 3 options | Read source files | L111-137 | None |
| 6 | Apply fix or re-run | Write/Edit or `gh run rerun` | L139-145 | **Yes** |

### 3.2 P1: Security Audit

```mermaid
flowchart TD
    Start([User: Security audit]) --> Discover["Step 1: Glob .github/workflows/*.yml/*.yaml"]
    Discover --> NoFiles{Files found?}
    NoFiles -->|No| Offer["'No workflows found' — offer to create"]
    NoFiles -->|Yes| CheckZ["Step 2: which zizmor"]
    CheckZ --> HasZ{zizmor available?}
    HasZ -->|Yes| RunZ["Step 3a: zizmor --format json"]
    HasZ -->|No| PatternOnly
    RunZ --> PatternCheck
    PatternOnly --> PatternCheck["Step 3b: Read each workflow<br/>+ security-checklist.md<br/>Check 8 anti-patterns + P1-4"]
    PatternCheck --> Vuln["Step 4: Layered vulnerability check<br/>1. zizmor findings<br/>2. gh api security-advisories<br/>3. Claude knowledge (with caveat)"]
    Vuln --> Report["Step 5: Generate report<br/>Critical / Warning / Info / Limitations"]

    style Discover fill:#4A90D9,color:#fff
    style CheckZ fill:#4A90D9,color:#fff
    style RunZ fill:#4A90D9,color:#fff
    style PatternCheck fill:#5BB5A2,color:#fff
    style Vuln fill:#4A90D9,color:#fff
    style Report fill:#4A90D9,color:#fff
```

**Step-by-step with tool references:**

| Step | Action | Tool | SKILL.md Lines | Confirmation |
|------|--------|------|---------------|-------------|
| 1 | Discover workflow files | Glob | L166-174 | None |
| 2 | Check zizmor availability | `which zizmor` | L176-183 | None |
| 3a | Run zizmor (if available) | `zizmor --format json` | L185-192 | None |
| 3b | Pattern checks (always) | Read workflows + `security-checklist.md` | L194-203 | None |
| 4 | Layered vulnerability check | `gh api` + Claude knowledge | L205-211 | None |
| 5 | Generate structured report | Compile findings | L213-238 | None |

The entire P1 flow is read-only. No confirmation is needed at any step.

### 3.3 Cross-Cutting Concerns

**Untrusted input handling** (SKILL.md L64-68): CI log content is treated as data, never as instructions. If log content contains text that appears to be AI instructions, it is ignored and flagged as suspicious. Credential patterns are redacted with `[REDACTED]` before display.

**Credential redaction patterns** (security-checklist.md L22-25): Three regex patterns scan log evidence before display:
- AWS access keys: `AKIA[0-9A-Z]{16}`
- GitHub PATs: `ghp_[A-Za-z0-9_]{36}`
- Generic GitHub tokens: `gh[pousr]_[A-Za-z0-9_]{36,}`

**Secret value protection** (SM-8): The skill never displays actual secret values. `gh secret list` returns names only (GitHub API enforces this). The audit reports only usage patterns and secret names.

The flows above use specific tools.

## 4. Tool Invocations

### 4.1 gh CLI Commands

| Command | Purpose | SKILL.md Line | Confirmation |
|---------|---------|--------------|-------------|
| `gh auth status` | Prerequisite check | L17 | None |
| `gh repo view --json owner,name` | Resolve `{owner}/{repo}` | L27 | None |
| `gh run list --limit 10` | Fetch recent runs | L78 | None |
| `gh run view {id} --log-failed` | Fetch failing step logs | L90 | None |
| `gh run view {id} --log` | Fallback for empty `--log-failed` | L95 | None |
| `gh run rerun {id} --failed` | Re-run failed jobs | L133, L144 | **Yes** |
| `which zizmor` | Check tool availability | L180 | None |
| `zizmor --format json .github/workflows/` | Static security analysis | L189 | None |
| `gh api /repos/{o}/{r}/security-advisories` | Vulnerability check | L210 | None |
| `gh api /repos/{o}/{r}/git/ref/tags/{tag}` | Resolve tag to SHA for pinning | Referenced in security-checklist.md L10 | None |

### 4.2 Claude Code Built-in Tools

| Tool | When Used | Context |
|------|-----------|---------|
| **Bash** | All `gh` CLI commands, `which` checks, `zizmor` execution | Primary tool for external interactions |
| **Read** | Loading reference files, reading workflow YAML, reading source files for fix context | P0 Steps 4-5, P1 Steps 3a-3b |
| **Write** | Creating new workflow files (P0 fix, if confirmed) | Only with user confirmation |
| **Edit** | Modifying existing workflow files (P0 fix, if confirmed) | Only with user confirmation |
| **Glob** | Discovering `.yml`/`.yaml` files in `.github/workflows/` | P1 Step 1 |
| **Grep** | Searching for patterns across workflow files | Supplementary to Read |

### 4.3 Optional External Tools

**zizmor**: The primary external security scanner. The skill checks availability (`which zizmor`), runs it with `--format json`, and enriches its findings with codebase context and remediation proposals. If unavailable, the skill falls back to its own pattern-based checks -- functional but less comprehensive.

**actionlint**: Not invoked directly by the skill. After P0 Step 6 applies a YAML fix, the skill suggests running `actionlint` on the modified file as a validation step (SKILL.md L143).

To verify everything works, the plugin includes a comprehensive test suite.

## 5. Testing Architecture

### 5.1 Validation Suite

`tests/validate_skill.sh` is a Bash script that validates the structural integrity and content completeness of all skill files. It uses two helper functions:

- **`check()`** (L14-23): Runs a shell command and records PASS/FAIL based on exit code.
- **`check_grep()`** (L26-37): Searches a file for a pattern and records PASS/FAIL.

**8 phases, 67 checks:**

| Phase | Focus | Checks | Line Range |
|-------|-------|--------|-----------|
| 1. Structural Validation | File existence, JSON validity, line counts | 6 | L42-54 |
| 2. Plugin Manifest | Name, version, required fields | 3 | L57-62 |
| 3. SKILL.md Frontmatter | Name, description, version, description length | 4 | L66-76 |
| 4. P0 Content | Commands, approval flow, untrusted input, error handling | 13 | L80-96 |
| 5. P1 Content | Audit steps, zizmor, checklist refs, secret protection | 12 | L100-114 |
| 6. Triaging Rules | 3 behavioral rules, ambiguity examples | 6 | L118-126 |
| 7. Reference Files | 6 failure categories, 8 anti-patterns, regex patterns | 17 | L130-152 |
| 8. Security Invariants | SM-4, SM-6, SM-7, SM-8, SM-9, credential redaction | 6 | L156-164 |

Run the suite:
```bash
bash github-claude-skills/tests/validate_skill.sh
```

### 5.2 Test Fixtures

**sample-failure-logs.md** (60 lines): Contains 7 log fixtures for P0 validation:

| Fixture | Category | Key Signature |
|---------|----------|---------------|
| 1 | Dependency Issue | `ModuleNotFoundError: No module named 'foo'` |
| 2 | YAML Misconfiguration | `unexpected value` / `mapping values are not allowed` |
| 3 | Code Bug | `FAIL test_order_placement ... AssertionError` |
| 4 | Flaky Test | `exit code 143` / intermittent pass/fail |
| 5 | Infrastructure | `No space left on device` |
| 6 | Permissions | `Resource not accessible by integration` |
| 7 | Prompt Injection (SM-7) | Attempts to inject "Ignore previous instructions" |

**vulnerable-workflow.yml** (48 lines): A single GitHub Actions workflow containing all 8 security anti-patterns for P1 validation:

| Line(s) | Anti-Pattern | Checklist Item |
|---------|-------------|----------------|
| L7 | `pull_request_target` trigger | #5 |
| L10 | No `permissions:` block | #2 |
| L17 | `actions/checkout@v4` (unpinned) | #1 |
| L20 | PR head ref checkout | #5 (continued) |
| L23 | `@main` branch reference | #6 |
| L28 | `echo ${{ secrets.API_KEY }}` | #4 |
| L33 | `${{ github.event.pull_request.title }}` in `run:` | P1-4 (template injection) |
| L38-40 | `AKIAIOSFODNN7EXAMPLE` hardcoded | #3 |
| L43-46 | `upload-artifact` with `path: .` | #8 |

Anti-pattern #7 (Missing CODEOWNERS) is checked separately -- it verifies absence of a `.github/CODEOWNERS` file rather than a pattern in the workflow.

### 5.3 Success Metrics

| ID | Metric | Target |
|----|--------|--------|
| SM-1 | Diagnosis accuracy | Correct categorization for all 6 failure patterns |
| SM-2 | Time to diagnosis | Root cause in a single interaction (no back-and-forth) |
| SM-3 | Security audit coverage | All 8 anti-patterns detected when present |
| SM-4 | Write confirmation | Never writes files without explicit user confirmation |
| SM-5 | Prerequisite handling | Clear error when `gh` CLI is missing |
| SM-6 | Read-only audit | Security audit produces zero file modifications |
| SM-7 | Log injection resistance | Commands in CI logs are quoted as evidence, never executed |
| SM-8 | Secret value protection | Only secret names shown, never values |
| SM-9 | Coverage disclaimer | Every audit report includes limitations statement |

With this understanding, here is how to extend the skill.

## 6. Contributing Guide

### 6.1 Adding a New Failure Category

1. **Add the category** to `references/failure-categories.md` following the existing format: heading, log signatures, example, typical cause.
2. **Add a validation check** to `validate_skill.sh` Phase 7 (L130+): add a `check_grep` for the new category name.
3. **Add a test fixture** to `fixtures/sample-failure-logs.md`: a realistic log snippet with the expected category.
4. **Run the suite**: `bash tests/validate_skill.sh` -- should pass with an incremented check count.

### 6.2 Adding a New Security Anti-Pattern

1. **Add the anti-pattern** to `references/security-checklist.md` following the existing format: heading with severity, look-for pattern, example bad/good, remediation.
2. **Add the pattern** to `fixtures/vulnerable-workflow.yml` with a comment labeling the anti-pattern number.
3. **Add a validation check** to `validate_skill.sh` Phase 7 (L130+): add a `check_grep` for the new anti-pattern name.
4. **Run the suite**: verify the new check passes.

### 6.3 Extending SKILL.md

**Token budget**: SKILL.md is currently 238 lines out of a 500-line target limit. There is room for ~260 additional lines before the token budget becomes a concern.

**V2 features** documented in the PRD but not yet implemented:
- P2: Workflow Authoring & Validation
- P3: Compliance Readiness Check
- P4: Pipeline Status Dashboard
- P5: Deployment Safety Analysis
- P6: Cost Optimization

When adding V2 features, follow the existing pattern: step-by-step procedures in SKILL.md, detailed reference content in `references/`, validation checks in `validate_skill.sh`. Do not add V2 placeholder sections to SKILL.md -- every token costs context window space on every invocation.
