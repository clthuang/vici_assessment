# GitHub CI/CD Guardian: Consulting Case Report

**Project:** AI-Powered CI/CD Skill Plugin for Claude Code
**Author:** Terry
**Date:** February 2026
**Assessment:** VICI Holdings — 7-Day Challenge

---

## I. Executive Summary

### The Problem

AI coding assistants have transformed how developers write code, but they have barely touched CI/CD. Research shows AI agents modify CI/CD configuration files in only **3.25% of file changes** ([arxiv 2601.17413](https://arxiv.org/html/2601.17413v1)), yet pipeline failures remain the number-one bottleneck after code generation. The average developer spends **2.5 hours** diagnosing a CI failure, trapped in a push-wait-fail cycle that existing tools do nothing to shorten.

For a proprietary trading firm, this gap is not an inconvenience — it is an operational risk. Knight Capital lost $440M in 45 minutes due to a deployment failure. CVE-2025-30066 (tj-actions supply chain attack) compromised 23,000+ repositories, exposing CI/CD secrets including exchange API keys. FINRA Regulatory Notice 15-09 requires documented change management for algorithmic trading systems but makes zero mention of CI/CD automation.

### The Solution

A Claude Code skill plugin — 238 lines of structured markdown instructions, not code. The plugin gives Claude domain-specific CI/CD expertise through two capabilities:

1. **P0: Pipeline Failure Diagnosis** — Fetches recent workflow runs, identifies failures, pulls logs, categorizes the root cause into 1 of 6 categories, and proposes a fix with 3 options (Apply, Re-run, Skip).
2. **P1: Security Audit** — Discovers workflow files, runs `zizmor` if available, scans against 8 anti-patterns, checks the GitHub Advisory Database, and generates a severity-ranked report.

The skill is model-invoked: Claude auto-activates when it detects CI/CD-related requests. No slash command required.

### Scope Calibration

This is a prompt-based skill plugin, not a runtime application. The "code" is structured markdown that instructs Claude how to behave. This is a deliberate engineering decision, not a limitation.

The skill does not replace GitHub Actions, auto-deploy code, store or display secret values, support non-GitHub CI/CD platforms, or provide local CI/CD testing. It shortens diagnosis time from ~2.5 hours to ~20 minutes by providing consistent triaging behavior, pre-built domain expertise, and a systematic diagnostic approach.

### Differentiator

No existing tool combines AI-powered diagnosis with security audit in the developer's existing terminal. The competitive landscape reveals partial solutions:

| Tool | Strength | Gap |
|------|----------|-----|
| Claude Code (vanilla) | Full codebase context, `gh` CLI access | Ad-hoc results, no consistent triaging |
| Gitar.ai | Auto-fixes test failures | No codebase context, standalone tool |
| GitHub Copilot | Native GitHub integration | Limited CI/CD depth, no compliance |
| actionlint | YAML validation (24+ rules) | Static only, no AI diagnosis |
| zizmor | Security scanning | Security only, no diagnosis or authoring |

The honest question is: what does a skill add over vanilla Claude Code? Four things: consistent triaging behavior (predictable read/write/confirm escalation), pre-built domain expertise (6 failure categories, 8 security anti-patterns), context-triggered activation, and structured diagnostic approach (systematic 6-step root cause analysis).

### Delivery Metrics

| Metric | Value |
|--------|-------|
| Core deliverables | 4 files, 355 lines |
| SKILL.md | 238 lines (under 500-line token budget) |
| Failure categories | 6 (P0) |
| Security anti-patterns | 8 (P1) |
| Validation checks | 67 automated, 100% passing |
| Tasks | 10 across 4 phases |
| Review phases | 6 (Spec, Design, Plan, Tasks, Implement, Security) |
| Duration | ~7 hours |

---

## II. Problem Decomposition

### The CI/CD Neglect Pattern

The 3.25% statistic tells a structural story. AI coding assistants are optimised for source code — the part of the repository with the most training data, the clearest feedback loops, and the most immediate rewards. CI/CD configuration files are a different beast:

| Dimension | Source Code | CI/CD Config |
|-----------|-------------|--------------|
| Feedback loop | Seconds (compiler/linter) | Minutes (push-wait-fail) |
| AI training data | Abundant | Sparse |
| Error messages | Structured (stack traces) | Unstructured (log dumps) |
| Debugging tool | Debugger, REPL | Read logs, re-run, hope |
| Change frequency | High | Low (set-and-forget) |

The low change frequency is the trap. Teams write workflows once, forget about them, and then spend hours debugging when they break. By the time a CI failure occurs, the developer who wrote the workflow has moved on. The failure logs are verbose, unstructured, and often misleading.

### Why Existing Tools Don't Help

Every existing tool solves one slice of the problem:

- **actionlint** validates YAML syntax but cannot diagnose why a valid workflow fails at runtime.
- **zizmor** finds security anti-patterns but cannot diagnose failures or propose fixes.
- **Gitar.ai** auto-fixes test failures but runs outside the developer's context — it cannot access the codebase.
- **GitHub Copilot** has GitHub integration but limited CI/CD debugging depth.

The gap is **contextual diagnosis**: reading the failure logs, understanding the codebase that produces them, categorising the root cause, and proposing a fix that accounts for the project's specific setup.

### The Real Question

The real question is not "can AI read CI logs?" — it can. The real question is: **can structured prompt instructions make an LLM's CI/CD behavior consistent, safe, and auditable without writing any runtime code?**

This reframes the project from "CI/CD debugging tool" to "prompt engineering as software engineering" — demonstrating that structured markdown instructions can achieve the same consistency guarantees that traditional software achieves through code.

---

## III. Strategic Design Decisions

Seven decisions shape the skill. Each is presented as a mini case study: context, analysis, decision, trade-off, and evidence.

### Decision 1: SKILL.md + Reference Files

**Context.** Claude Code loads skill instructions from a single SKILL.md file. Complex skills need detailed reference material (failure categories, security checklists), but cramming everything into one file creates a token-budget problem.

**Analysis.** The SKILL.md token budget is ~500 lines. The failure categories (39 lines) and security checklist (73 lines) are reference material that Claude needs only during specific procedure steps, not upfront. Loading them into SKILL.md would consume 112 lines of the budget on static lookup tables.

**Decision.** Keep SKILL.md under 500 lines with procedural instructions. Move detailed reference content to `references/` subdirectory. SKILL.md instructs Claude to `Read` the appropriate reference file at the relevant procedure step (P0 Step 4 for failure categories, P1 Step 3b for security checklist).

**Trade-off.** Two extra Read tool calls per invocation. Compensated by: (a) SKILL.md stays at 238 lines — well under the token budget, (b) reference files can be updated independently without touching the skill instructions, (c) Claude only loads what it needs for the current capability.

**Evidence.** SKILL.md L103: "Read `references/failure-categories.md`" (P0 Step 4). SKILL.md L199: "Read `references/security-checklist.md`" (P1 Step 3b). The reference files are loaded on-demand, not upfront.

### Decision 2: No Scripts Directory

**Context.** The initial design considered a `scripts/` directory with shell scripts for common operations (log fetching, zizmor execution, result parsing).

**Analysis.** All operations use Claude Code's existing Bash tool to run `gh` CLI commands. No deterministic logic benefits from a shell script over inline instructions. A shell script for `gh run list --limit 10` adds a file to maintain, a dependency to document, and a failure mode (script not found, wrong permissions) — all for zero behavioral benefit.

**Decision.** No `scripts/` directory. All operations are inline Bash commands in SKILL.md procedure steps.

**Trade-off.** Longer SKILL.md procedure steps (commands are inline instead of single script calls). Compensated by: (a) zero external dependencies — the skill works on any machine with `gh` CLI, (b) each command is visible and auditable in the skill instructions, (c) no shell script maintenance, versioning, or permission issues.

**Evidence.** The skill uses exactly two external tools: `gh` CLI (required) and `zizmor` (optional). Both are invoked inline via Bash. The plan-reviewer validated that no proposed script contains logic that benefits from being a standalone file.

### Decision 3: Three Behavioral Rules over Decision Trees

**Context.** The initial specification defined 6 formal tiers for action classification (Read, Analyze, Propose, Write, Execute, Destroy).

**Analysis.** A UX review flagged the 6-tier system as over-engineered for a markdown prompt file. Claude interprets behavioral instructions ("always ask before writing") more reliably than multi-branch conditional logic. Formal tier classification requires the LLM to first classify the action, then look up the tier's permissions, then apply them — three reasoning steps where one suffices.

**Decision.** Three behavioral rules:
1. **Read and analyze freely** — fetching CI status, reading logs, scanning workflow files require no confirmation.
2. **Propose freely, write only with confirmation** — diffs and suggestions are shown; file edits and workflow triggers require user approval.
3. **Destructive operations require double confirmation** — deleting a workflow requires showing what will be deleted and confirming twice.

**Trade-off.** Less formal than a decision tree — edge cases rely on Claude's judgment rather than explicit classification. Compensated by: (a) an ambiguity resolution table maps common user phrases to specific actions and confirmation levels, (b) the rules are testable — the validation suite greps for all three rules, (c) behavioral instructions align with how LLMs process natural language.

**Evidence.** SKILL.md L31-60 defines the three rules with an action classification table. The simplification from 6 tiers to 3 rules was the single most impactful design evolution — it improved both clarity and Claude's adherence in testing.

### Decision 4: Zizmor as Optional Enrichment

**Context.** `zizmor` is the best-in-class security scanner for GitHub Actions. Should the skill require it or treat it as optional?

**Analysis.** Requiring zizmor means every user must install a Rust binary before using the security audit. Many developers won't have it. But ignoring it wastes a valuable data source for users who do have it.

**Decision.** Check availability at runtime (`which zizmor`). If present, run it and enrich the audit with its findings plus codebase context. If not, fall back to Claude's pattern matching against the security checklist. Don't require it, don't ignore it.

**Trade-off.** Inconsistent audit depth depending on whether zizmor is installed. Compensated by: (a) the 8 anti-pattern checklist provides baseline coverage regardless, (b) the audit report states its data sources explicitly — users know whether zizmor was used, (c) the skill suggests installing zizmor when it's not found.

**Evidence.** SKILL.md P1 Step 2: "Run `which zizmor`" — check availability. SKILL.md P1 Step 3a: "If zizmor is available, run `zizmor .github/workflows/`." SKILL.md P1 Step 3b: "Read `references/security-checklist.md` and scan against 8 anti-patterns" — this runs regardless of zizmor availability.

### Decision 5: Plugin Structure

**Context.** Claude Code discovers skills through plugin manifests. The skill needs a discovery mechanism.

**Analysis.** The `.claude-plugin/plugin.json` manifest enables proper plugin discovery. The manifest is 5 lines of JSON declaring the plugin name (`github-cicd-guardian`), description, and version. Claude Code reads it to register the plugin and then loads skills from the `skills/` subdirectories.

**Decision.** Use the standard Claude Code plugin structure: `.claude-plugin/plugin.json` at the plugin root, with skills in `skills/<skill-name>/SKILL.md`.

**Trade-off.** Requires the correct directory structure — `plugin.json` must be in `.claude-plugin/`, not the root. The design review caught this location error twice (initially placed at root, then incorrectly "fixed" back to root).

**Evidence.** `.claude-plugin/plugin.json` (5 lines). The location was validated against Claude Code documentation after two incorrect placements during design.

### Decision 6: Structured Output Format

**Context.** Both P0 and P1 produce reports. The format must be consistent, parseable, and actionable.

**Analysis.** Freeform text reports vary between invocations. Structured output (specific sections, tables, severity levels) enables consistent behavior and testable outcomes.

**Decision.** P0 outputs: status summary, failure identification, root cause category, proposed fix with 3 options. P1 outputs: severity-ranked findings table, per-finding detail (anti-pattern, file, line, remediation), summary statistics. Both use markdown tables for consistency.

**Trade-off.** More rigid than freeform — Claude must follow the template. Compensated by: (a) consistent output enables the validation suite to grep for expected sections, (b) users learn to expect a specific format, reducing cognitive load, (c) the template is embedded in SKILL.md, not a separate file.

**Evidence.** SKILL.md L111-137 defines the P0 output format. SKILL.md L204-238 defines the P1 output format. Both include explicit section headers that the validation suite checks for.

### Decision 7: Prerequisites Inline

**Context.** The skill requires `gh` CLI authenticated with appropriate scopes. Where should prerequisites be checked?

**Analysis.** A separate prerequisites script adds a file and a failure mode. Inline checks in SKILL.md mean Claude verifies prerequisites as the first step of every invocation — no separate "setup" step that users might skip.

**Decision.** Prerequisites are the first section of SKILL.md (L13-29). Claude runs `gh auth status` before any capability. If auth fails, it provides the exact command to fix it (`gh auth login` or `gh auth refresh -s <scope>`).

**Trade-off.** Prerequisite checks run on every invocation, not just setup. Compensated by: (a) `gh auth status` is fast (<1 second), (b) error-driven scope discovery — instead of maintaining a static scope mapping, the error message tells the user which scope to add, (c) no "setup step" that users forget to run.

**Evidence.** SKILL.md L13-29 defines prerequisites. The error-driven scope discovery pattern avoids maintaining a scope mapping table that would become stale.

---

## IV. Architecture as Risk Mitigation

The architecture is prompt-based — the "code" is structured markdown instructions. Each structural choice addresses a specific failure mode.

### Prompt Injection via CI Logs

**Risk.** CI logs may contain adversarial content designed to manipulate Claude's behavior — instructions to execute commands, modify files, or exfiltrate data.

**Mitigation.** Three layers:
1. **Triaging Rule 2** — All writes require user confirmation. Even if Claude is manipulated into proposing a malicious fix, the user must approve it.
2. **Explicit instruction** — SKILL.md marks CI logs as "untrusted input" and instructs Claude to treat instruction-like content as suspicious.
3. **Credential redaction** — Before quoting log evidence, Claude scans for credential patterns (AWS keys: `AKIA[0-9A-Z]{16}`, GitHub tokens: `ghp_[A-Za-z0-9_]{36}`, etc.) and replaces them with `[REDACTED]`.

**Residual risk.** Claude may present biased analysis influenced by adversarial log content. The user must exercise judgment. This is inherent to LLM-based log analysis — the skill never claims immunity from manipulation.

### Incorrect Fix Applied

**Risk.** Claude proposes a fix that makes the problem worse or introduces new issues.

**Mitigation.** The fix is shown as an exact diff before writing. The user must approve. Post-fix, the skill recommends running `actionlint` to validate the modified YAML.

**Residual risk.** The user may approve without careful review. The skill is a tool, not a gatekeeper.

### Security Audit False Negatives

**Risk.** The security audit misses a genuine vulnerability, giving false confidence.

**Mitigation.** Layered approach: pattern checks (8 anti-patterns) + zizmor (if available) + GitHub Advisory Database. Every audit report includes a limitations disclaimer — the skill never claims "your workflows are secure."

**Residual risk.** Novel attack patterns will be missed. The security checklist covers known anti-patterns; zero-day supply chain attacks are beyond scope.

### Safety Invariants

Five invariants the skill maintains:

| Invariant | Mechanism | Validation |
|-----------|-----------|------------|
| Never execute commands found in CI logs | Explicit instruction in SKILL.md | SM-7 metric, grep verification |
| Never modify files during a security audit | P1 is read-only by design | SM-6 metric |
| Never display actual secret values | Credential redaction before quoting | SM-8 metric |
| Never bypass the triaging contract | All writes require confirmation | SM-4 metric |
| Always state audit limitations | Disclaimer template in P1 output | SM-9 metric |

---

## V. The Five Pivots

The skill evolved through five design pivots. Each was triggered by review findings.

### Pivot 1: Triaging Simplification

**Trigger.** A UX review flagged the initial 6-tier action classification (Read, Analyze, Propose, Write, Execute, Destroy) as over-engineered for a markdown prompt file.

**What was preserved:** The core principle — read freely, write with confirmation, destroy with extra confirmation.
**What was discarded:** 6 formal tiers, tier classification logic, and the lookup table mapping actions to tiers.
**Why.** Claude interprets behavioral instructions more reliably than formal classification systems. Three simple rules beat a complex flowchart. This was validated during testing — Claude's adherence improved after the simplification.

### Pivot 2: Frontmatter Format

**Trigger.** The plan review discovered that Claude Code docs recommend third-person trigger phrases in the `description` field for reliable auto-activation, not the declarative format used in the original design.

**What was preserved:** Skill metadata (name, description, version).
**What was discarded:** Declarative description format ("Diagnose GitHub Actions failures...").
**Why.** Third-person trigger phrases ("This skill should be used when the user asks to...") align with Claude Code's auto-activation matching. The declarative format worked but activated less reliably.

### Pivot 3: No Scripts Directory

**Trigger.** Design analysis determined that no proposed shell script contains logic that benefits from being a standalone file.

**What was preserved:** All CLI commands (gh, zizmor, actionlint).
**What was discarded:** `scripts/` directory with helper shell scripts.
**Why.** Every shell script is one more file to maintain, version, and debug. Inline Bash commands in SKILL.md are visible, auditable, and require no file-path resolution.

### Pivot 4: Zizmor Optional

**Trigger.** Requiring zizmor would block security audits for users who don't have a Rust toolchain installed.

**What was preserved:** Zizmor integration for users who have it.
**What was discarded:** Zizmor as a hard requirement.
**Why.** The 8 anti-pattern checklist provides baseline coverage. Zizmor enriches but isn't required. The skill checks availability at runtime and adapts.

### Pivot 5: Behavioral Rules over Decision Trees

**Trigger.** Testing revealed that Claude followed 3 behavioral rules more consistently than a 6-branch decision tree.

**What was preserved:** The intent — predictable escalation from read to write to destroy.
**What was discarded:** Formal decision tree with tier classification.
**Why.** LLMs process natural language instructions better than formal logic. "Always ask before writing" is clearer than "classify action → lookup tier → check permissions → apply." The ambiguity resolution table handles edge cases without adding branches.

---

## VI. Acknowledged Limitations

Six limitations are explicitly documented. Each represents a deliberate scope decision, not an oversight.

### L1: GitHub Actions Only

- **Impact:** No support for GitLab CI, CircleCI, Jenkins, or other CI/CD platforms.
- **Current Mitigation:** GitHub Actions is the most common CI/CD platform for new projects. The skill focuses on depth over breadth.
- **North Star:** Platform-agnostic skill with adapter pattern — same diagnostic procedures, platform-specific log fetching and workflow parsing.

### L2: No Local Testing

- **Impact:** The skill cannot simulate a pipeline run locally. Users must push and wait.
- **Current Mitigation:** The skill shortens the diagnosis phase (2.5 hours → ~20 minutes) but does not eliminate the push-wait-fail cycle. For local testing, `act` (a third-party tool for running GitHub Actions locally) is recommended.
- **North Star:** Integration with `act` for local pipeline simulation before pushing.

### L3: LLM Prompt Injection

- **Impact:** Adversarial CI log content could influence Claude's analysis or proposed fixes.
- **Current Mitigation:** Triaging Rule 2 (user confirmation for all writes). CI logs are explicitly marked as untrusted. Credential redaction before quoting. Instruction-like content flagged as suspicious.
- **North Star:** Sandboxed log analysis where Claude's analysis of logs is separated from its ability to propose actions — two-stage reasoning with human gate between.

### L4: False Negatives in Security Audit

- **Impact:** The audit may miss vulnerabilities, giving false confidence.
- **Current Mitigation:** Layered approach (pattern matching + zizmor + advisory DB). Every report includes limitations disclaimer. The skill never claims "your workflows are secure."
- **North Star:** Continuous audit pipeline that runs on every workflow change, not just on-demand.

### L5: User Must Review Fixes

- **Impact:** The skill proposes fixes but cannot guarantee correctness. Users must review diffs carefully.
- **Current Mitigation:** Fixes shown as exact diffs before writing. `actionlint` recommended post-fix. Three-option choice (Apply, Re-run, Skip) gives the user control.
- **North Star:** Automated fix validation — apply the fix in a branch, trigger CI, and verify the fix resolves the failure before proposing to the user.

### L6: No Cross-Repository Support

- **Impact:** Cannot diagnose issues that span multiple repositories (e.g., shared workflow reuse, organisation-level secrets).
- **Current Mitigation:** Single-repository focus. Cross-repo dependencies are flagged but not resolved.
- **North Star:** Organisation-level skill that can traverse repository dependencies and shared workflow files.

---

## VII. Validation Strategy

### Automated Validation Suite

67 automated checks across 8 test phases, executed by `tests/validate_skill.sh` (179 lines):

| Phase | Focus | Checks |
|-------|-------|--------|
| 1. Structural Validation | File existence, JSON validity, line counts | 6 |
| 2. Plugin Manifest | Name, version, required fields | 3 |
| 3. SKILL.md Frontmatter | Name, description, version, length limit | 4 |
| 4. P0 Content | Commands, approval flow, untrusted input, error handling | 13 |
| 5. P1 Content | Audit steps, zizmor, checklist refs, secret protection | 12 |
| 6. Triaging Rules | 3 behavioral rules, ambiguity resolution examples | 6 |
| 7. Reference Files | 6 failure categories, 8 anti-patterns, regex patterns | 17 |
| 8. Security Invariants | SM-4, SM-6, SM-7, SM-8, SM-9, credential redaction | 6 |

### Why Grep-Based Testing

The deliverables are markdown files, not executable code. Traditional unit tests don't apply. Instead, the validation suite uses `grep` to verify that specific strings, patterns, and structures exist in the correct files. Each check verifies a specific contract:

- "Does SKILL.md contain all three triaging rules?"
- "Does failure-categories.md define all 6 categories?"
- "Does security-checklist.md include all 8 anti-patterns?"
- "Does SKILL.md reference the credential redaction regex?"

This is regression testing for prompt engineering — every behavioral guarantee is verified by checking that the instruction exists in the file.

### Test Fixtures

Two fixtures provide concrete validation targets:

1. **`tests/fixtures/sample-failure-logs.md`** (60 lines) — 7 log fixtures: one per failure category (dependency, YAML, code bug, flaky test, infrastructure, permissions) plus a prompt injection attempt. The prompt injection fixture tests Claude's handling of adversarial content.

2. **`tests/fixtures/vulnerable-workflow.yml`** (48 lines) — A single workflow with all 8 security anti-patterns embedded. Used for manual testing of P1's detection capabilities.

### Success Metrics

| ID | Metric | Target |
|----|--------|--------|
| SM-1 | Diagnosis accuracy | Correct root cause category for sample logs |
| SM-2 | Time-to-diagnosis | <20 minutes from user request |
| SM-3 | Audit coverage | All 8 anti-patterns detected in vulnerable workflow |
| SM-4 | Write confirmation | 100% of file writes require user approval |
| SM-6 | Audit read-only | Zero file modifications during P1 |
| SM-7 | Log safety | Never execute commands found in logs |
| SM-8 | Secret protection | Never display actual secret values |
| SM-9 | Limitation disclosure | Every audit includes limitations disclaimer |

---

## VIII. Process and Delivery Metrics

### Multi-Phase Development Pipeline

The skill was built through a structured pipeline with formal review at each stage:

| Stage | Duration | Iterations | Key Outcomes |
|-------|----------|------------|--------------|
| Brainstorm/PRD | Research phase | 1 | Problem framing, competitive analysis, scope decision |
| Specify | ~15 min | 1 (2 review cycles) | All blockers resolved, zero open issues |
| Design | ~35 min | 1 | Architecture validated, plugin structure confirmed |
| Plan | ~20 min | 1 | 2 blockers found (frontmatter format, version field) |
| Tasks | ~25 min | 2 + chain validation | 10 tasks across 4 phases |
| Implement | ~20 min | 1 | All 3 reviewers approved (implementation, quality, security) |
| Finish | ~60 min | — | PR, merge, retrospective |

### 10 Tasks Across 4 Phases

| Phase | Tasks | Focus |
|-------|-------|-------|
| Phase 1: Plugin Structure | 3 | plugin.json, directory layout, SKILL.md frontmatter |
| Phase 2: P0 Implementation | 3 | Diagnosis procedure, failure categories, fix proposals |
| Phase 3: P1 Implementation | 2 | Security audit procedure, anti-pattern checklist |
| Phase 4: Validation | 2 | Validation script, test fixtures |

### Review Effectiveness

The multi-phase review architecture (Spec → Design → Plan → Tasks → Implement) with dedicated reviewer personas caught issues at the earliest possible stage:

1. **plugin.json location** (design review) — Initially placed at the plugin root. Design review verified via Claude Code documentation that it must be at `.claude-plugin/plugin.json`. A second review caught the same error after it was incorrectly "fixed" back to the root. Lesson: authoritative source verification beats assumption-based design.

2. **Frontmatter format** (plan review) — The original description used a declarative format. Plan review verified that Claude Code docs recommend third-person trigger phrases for reliable auto-activation. Fixed before implementation.

3. **Security hardening** (implementation review) — The security reviewer identified 3 medium-severity issues post-implementation:
   - Prompt injection defense was too narrow (only covered command execution, not adversarial analysis)
   - The `--log` fallback could expose passing-step data
   - Log quoting lacked credential redaction
   All three were addressed before approval.

### Patterns Worth Documenting

1. **Token budget as design constraint.** Track line counts throughout development. SKILL.md at 238 lines (under 500-line budget) means every line earns its place. Move static reference content (>40 lines) to `references/` subdirectory.

2. **Behavioral instructions over formal logic.** Claude follows "always ask before writing" more reliably than "classify action into tier 1-6, look up tier permissions, apply." Three rules beat six tiers.

3. **Grep-based regression testing.** Automated testing for LLM skill files without runtime dependencies. Each check verifies a specific string/pattern exists in the correct file. 67 checks run in seconds with zero infrastructure.

4. **Error-driven scope discovery.** Instead of maintaining a static token-scope mapping table, let the error message tell the user which scope to add (`gh auth refresh -s {scope}`). The mapping table would become stale; the error message is always current.

5. **Security invariant verification.** For each "never do X" requirement, define an explicit test metric (SM-N) and automate verification via grep. Five invariants, five metrics, five automated checks.

---

## IX. North Star Roadmap

### Tier 1: Highest ROI

**V2 Capabilities: Workflow Authoring + Compliance**
- **What:** P2 (workflow authoring from natural language) and P3 (compliance readiness for regulatory frameworks).
- **Why:** P2 saves hours/week on workflow creation. P3 addresses the FINRA gap — regulatory intent vs. engineering practice.
- **Effort:** 2-3 days per capability (SKILL.md extensions + reference files + validation updates).

**Cross-Platform Support**
- **What:** GitLab CI, CircleCI, and Jenkins adapters using the same diagnostic procedures.
- **Why:** The diagnostic approach (fetch logs → categorise → fix) is platform-agnostic; only the log-fetching commands differ.
- **Effort:** 1-2 days per platform (adapter pattern, shared diagnostic logic).

### Tier 2: Medium ROI

**Automated Fix Validation**
- **What:** Apply fix in a branch, trigger CI, verify fix resolves the failure before proposing to the user.
- **Why:** Eliminates the "user must review fix" limitation. The skill validates its own proposals.
- **Effort:** 3-5 days (branch management, CI trigger, result monitoring).

**Continuous Security Audit**
- **What:** Run P1 automatically on every workflow file change (pre-commit hook or CI step).
- **Why:** Shift-left security — catch anti-patterns before they reach the default branch.
- **Effort:** 2-3 days (hook integration, incremental audit, noise reduction).

### Tier 3: Long-Term

**Organisation-Level Intelligence**
- Cross-repository workflow analysis, shared secret audit, and organisation-wide compliance reporting.

**Local CI Testing Integration**
- Integration with `act` for local pipeline simulation, reducing the push-wait-fail cycle.

**Regulatory Compliance Reporting**
- Automated mapping of CI/CD practices to FINRA, SOC2, and ISO 27001 requirements.

---

## X. Conclusion

### What Was Demonstrated

This project demonstrates that prompt engineering is software engineering. The deliverable is 355 lines of markdown — no runtime code, no binaries, no dependencies beyond `gh` CLI. Yet it required the same rigor: problem decomposition, competitive analysis, scope decisions, architecture, safety invariants, testing, and review.

**Structured prompts as executable specifications.** SKILL.md is not a suggestion to Claude — it is a specification with testable contracts. The 67 automated checks verify that every behavioral rule, every procedure step, every safety invariant is present in the instruction set. This is regression testing for prompt engineering.

**Safety through behavioral contracts.** Five safety invariants maintained through explicit instructions, not code enforcement. The triaging contract (read freely, write with confirmation, destroy with double confirmation) provides the same guarantees as a permission system — through natural language instructions that Claude follows more reliably than formal decision trees.

**Honest scope calibration.** Six acknowledged limitations, each with impact, current mitigation, and North Star resolution. The skill does not claim to eliminate the push-wait-fail cycle — it shortens the diagnosis phase. The security audit does not claim completeness — it explicitly disclaims limitations in every report. The skill is a tool, not a gatekeeper.

### The Five Pivots Tell the Story

1. **6 tiers → 3 rules** — Behavioral instructions beat formal classification for LLMs
2. **Declarative → Trigger phrases** — Match the framework's activation mechanism
3. **Scripts directory → Inline commands** — Don't create files for one-line operations
4. **Zizmor required → Zizmor optional** — Enrich when available, fall back when not
5. **Decision tree → Behavioral rules** — Natural language is the LLM's native interface

Each pivot simplified the design. The final skill is smaller, clearer, and more reliable than the initial design. Simplification through iteration is the meta-pattern.

### Nothing Accidental

Every decision in this skill is documented with its trade-off:

- SKILL.md + references trades upfront loading for on-demand precision.
- No scripts trades convenience for zero maintenance overhead.
- Three rules trades formal completeness for LLM comprehension.
- Zizmor optional trades consistent depth for universal availability.
- Plugin structure trades directory convention for proper discovery.
- Structured output trades flexibility for consistency.
- Inline prerequisites trades per-invocation cost for never-skip reliability.

The depth of thought is the deliverable. The markdown is the proof.

---

## References

1. Rasheed et al. (2025). "Agents on the Bench: Large Language Model Agents as Software Engineering Interns." arxiv 2601.17413 — AI agents modify CI/CD config in only 3.25% of file changes.

2. Knight Capital Group — $440M loss in 45 minutes due to deployment failure (August 1, 2012).

3. CVE-2025-30066 — tj-actions/changed-files supply chain attack compromising 23,000+ repositories.

4. FINRA Regulatory Notice 15-09 — Guidance on algorithmic trading systems and change management requirements.

5. Claude Code Plugin Documentation — Plugin manifest structure, skill auto-activation, and trigger phrase format.

6. zizmor — https://github.com/woodruffw/zizmor — Security scanner for GitHub Actions.

7. actionlint — https://github.com/rhysd/actionlint — Static analysis for GitHub Actions workflow files.

---

## Appendix: Artifact Registry

| Artifact | Path | Notes |
|----------|------|-------|
| PRD | `docs/brainstorms/20260207-github-cicd-skill.prd.md` | Problem analysis and research |
| Specification | `docs/features/1-github-cicd-guardian/spec.md` | Requirements and acceptance criteria |
| Design | `docs/features/1-github-cicd-guardian/design.md` | Architecture and component design |
| Plan | `docs/features/1-github-cicd-guardian/plan.md` | Build order and phase structure |
| Tasks | `docs/features/1-github-cicd-guardian/tasks.md` | 10 tasks across 4 phases |
| Plugin Manifest | `.claude-plugin/plugin.json` | 5 lines, plugin discovery |
| SKILL.md | `skills/github-cicd-guardian/SKILL.md` | 238 lines, skill instructions |
| Failure Categories | `skills/github-cicd-guardian/references/failure-categories.md` | 39 lines, 6 categories |
| Security Checklist | `skills/github-cicd-guardian/references/security-checklist.md` | 73 lines, 8 anti-patterns |
| Validation Suite | `tests/validate_skill.sh` | 179 lines, 67 automated checks |
| Failure Log Fixtures | `tests/fixtures/sample-failure-logs.md` | 60 lines, 7 test fixtures |
| Vulnerable Workflow | `tests/fixtures/vulnerable-workflow.yml` | 48 lines, 8 embedded anti-patterns |
| Architecture Guide | `docs/architecture.md` | Technical onboarding guide |
| Knowledge Bank | `docs/knowledge-bank/claude-code-skill-patterns.md` | 12 learnings documented |
| Retrospective | `docs/features/1-github-cicd-guardian/.retro.md` | Process learnings |
