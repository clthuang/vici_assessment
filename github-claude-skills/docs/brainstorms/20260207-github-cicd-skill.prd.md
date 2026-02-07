# PRD: GitHub CI/CD Guardian - A Claude Code Skill for Pipeline Operations

## 1. Problem Statement

GitHub Actions CI/CD is the most neglected area in AI-assisted development. Research shows AI agents modify CI/CD configs in only **3.25% of file changes** ([arxiv 2601.17413](https://arxiv.org/html/2601.17413v1)), yet CI/CD failures are the #1 bottleneck developers face after code generation.

For a **high-frequency proprietary trading firm**, this gap is existential:
- **Knight Capital lost $440M in 45 minutes** due to a manual deployment without automated verification ([source](https://dougseven.com/2014/04/17/knightmare-a-devops-cautionary-tale/))
- FINRA 15-09 requires documented change management, approval protocols, independent QA, and code archival for algorithmic trading systems, but makes **zero mention of CI/CD automation** ([source](https://www.finra.org/rules-guidance/notices/15-09))
- The tj-actions supply chain attack (CVE-2025-30066) compromised **23,000+ repositories**, exposing CI/CD secrets including API keys and credentials ([source](https://thehackernews.com/2025/03/github-action-compromise-puts-cicd.html))
- The universally hated "push-wait-fail-repeat" cycle wastes hours per developer per week ([HN discussion](https://news.ycombinator.com/item?id=46614558))

No existing tool provides a unified, AI-powered CI/CD management experience within the developer's terminal.

### Priority Classification

Features are classified by **value to a prop trading firm** and **implementation complexity**:

| Feature | Value | Complexity | Classification |
|---------|-------|-----------|----------------|
| P0: Pipeline Failure Diagnosis & Fix | **Critical** -- blocked deployments = stale strategies = real money lost | **Low** -- `gh run view` + log analysis, Claude Code already has codebase context | **MUST HAVE** |
| P1: Security Audit & Supply Chain | **Critical** -- leaked exchange API keys = unauthorized market access, existential risk | **Medium** -- needs workflow YAML parsing + `gh api` for advisory DB | **MUST HAVE** |
| P2: Workflow Authoring & Validation | **High** -- saves hours/week per developer, but not blocking trading operations | **Low** -- natural language to YAML generation, Claude already does this well | **SHOULD HAVE** |
| P3: Compliance Readiness Check | **High** -- regulatory requirement, but firms have manual processes today | **Medium** -- needs `gh api` for branch protection, FINRA/SOX knowledge encoding | **SHOULD HAVE** |
| P4: Pipeline Status Dashboard | **Medium** -- convenience, developers can use `gh run list` manually | **Very Low** -- thin wrapper around `gh` CLI read-only commands | **NICE TO HAVE** |
| P5: Deployment Safety Analysis | **Medium** -- important but firms already have kill-switch procedures | **High** -- needs deep workflow analysis, deployment pattern recognition | **NICE TO HAVE** |
| P6: Cost Optimization | **Low** -- cost is a concern but not a trading-floor-blocking pain | **Medium** -- needs billing API access (admin-only), workflow efficiency analysis | **NICE TO HAVE** |

**MVP Scope (Must Have)**: P0 + P1 -- diagnose pipeline failures and audit security. These two features address the highest-frequency pain (blocked deployments) and the highest-risk exposure (supply chain attacks) with manageable complexity.

**V2 Scope (Should Have)**: P2 + P3 -- workflow authoring and compliance readiness. These deliver significant productivity and regulatory value once the foundation is proven.

**Future Scope (Nice to Have)**: P4 + P5 + P6 -- status dashboard, deployment safety, cost optimization. These are genuinely useful but are either thin wrappers over existing tools (P4), require high complexity for moderate value (P5), or address a lower-priority pain (P6).

## 2. Target User

**Primary**: Developers and DevOps engineers at a prop trading firm who manage GitHub Actions workflows, need to diagnose pipeline failures quickly, and must meet regulatory compliance requirements (FINRA, SEC, SOX, MiFID II).

**Secondary**: Any developer using GitHub Actions who wants AI-assisted CI/CD workflow authoring, debugging, and management.

## 3. Skill Overview

**GitHub CI/CD Guardian** is a Claude Code **skill** -- a markdown-based instruction file that provides Claude Code with domain-specific CI/CD expertise. When activated (by context or explicit invocation), it guides Claude Code to use `gh` CLI (for API operations: run status, secrets, PRs) and direct YAML file management (for workflow authoring, validation, and fixing) following a strict predictability contract.

### What is a Claude Code Skill?

A skill is a `.md` file within a Claude Code plugin that:
- Has a YAML frontmatter with a `description` field (used for auto-triggering based on context)
- Contains structured instructions that guide Claude Code's behavior for a specific domain
- Is **model-invoked** -- Claude activates it automatically when the user's request matches the skill's description
- Uses Claude Code's existing tools (Bash for `gh` CLI, Read/Write/Edit for YAML files) -- it does NOT introduce new tools

### Triaging Rules (Predictability Contract)

To ensure consistent, predictable behavior:

| Action Type | Tool Used | When |
|-------------|-----------|------|
| **Read-only queries** (run status, logs, checks) | `gh` CLI | Always - never modifies anything |
| **Workflow file creation/editing** | Direct file read/write | Only when user explicitly requests authoring or when fixing a YAML issue |
| **Secret management** | `gh secret` CLI | Only when user explicitly requests, with confirmation |
| **Pipeline triggering** | `gh workflow run` | Only when user explicitly requests, with confirmation |
| **Destructive operations** (delete workflow, remove secret) | Requires explicit user confirmation | Always - never auto-deletes |

**Core Principle**: Read operations are always safe and automatic. Write operations require explicit intent or confirmation. Destructive operations always require confirmation.

### Ambiguity Resolution Policy

When a user's request is ambiguous (e.g., "fix my CI"), the skill defaults to the **most conservative interpretation** and escalates only with explicit consent:

| User Says | Default Interpretation | Escalation |
|-----------|----------------------|------------|
| "Fix my CI" | Diagnose only (read-only) | "I found the issue. Want me to apply the fix?" |
| "My pipeline is broken" | Fetch logs + analyze (read-only) | "Here's the root cause. Shall I edit the workflow?" |
| "Update the workflow" | Show proposed diff | "Here's what I'd change. Apply it?" |
| "Make CI faster" | Analyze for optimizations (read-only) | "I found 3 optimizations. Want me to apply them?" |

## 4. Features (Priority-Ordered)

### P0: Pipeline Failure Diagnosis & Fix (Highest Frequency Pain)

**Problem**: Developers spend 2.5 hours average diagnosing CI/CD failures. The "push-wait-fail-repeat" cycle is the #1 complaint about GitHub Actions.

**Capability**:
- Fetch latest workflow run status and logs via `gh run list` and `gh run view`
- Analyze failure logs with full codebase context (Claude Code's key advantage over standalone tools like Gitar)
- Identify root cause: is it a code bug, YAML misconfiguration, dependency issue, flaky test, or infrastructure problem?
- Propose a fix (code change, YAML change, or retry) with explanation
- Optionally apply the fix and re-trigger the workflow

**Triaging**: Log fetching is read-only (always safe). Fix application requires user approval. Re-trigger requires explicit confirmation.

**Evidence**: AI-powered pipeline analysis reduces average failure resolution from 2.5 hours to 20 minutes (87% reduction) ([source](https://markaicode.com/ai-fix-cicd-pipeline-failures-github-actions/)).

**Competitive Gap**: Gitar.ai auto-fixes test failures but lacks codebase context. Claude Code already understands the full codebase, making diagnosis significantly more accurate.

---

### P1: Security Audit & Supply Chain Protection (Existential Risk for Trading)

**Problem**: The tj-actions supply chain attack demonstrated that GitHub Actions marketplace actions are a critical attack vector. Native secrets management lacks enterprise-grade features. For trading firms, leaked exchange API credentials = unauthorized market access.

**Capability**:
- Audit workflow files for security vulnerabilities (unpinned actions, template injection, excessive permissions, credential exposure risks)
- Check if any used actions have known CVEs via `gh api` queries to GitHub Advisory Database (note: coverage limited to GitHub's advisory data; recommend supplementing with `zizmor` if available)
- Validate secrets management practices (rotation policies, OIDC vs long-lived credentials)
- Scan for hardcoded secrets or credential patterns in workflow files
- Generate security posture report

**Triaging**: All security audit operations are read-only. Remediation suggestions are presented for user review. Secret rotation requires explicit user action.

**Evidence**: CVE-2025-30066 affected 23,000+ repos. GitHub's native secrets lack rotation, audit trails, and fine-grained access controls ([source](https://www.blacksmith.sh/blog/best-practices-for-managing-secrets-in-github-actions)). The "PromptPwnd" vulnerability demonstrated AI prompt injection through CI/CD pipelines ([source](https://www.aikido.dev/blog/promptpwnd-github-actions-ai-agents)).

**Priority Justification**: Ranked above workflow authoring because for a trading firm, security is existential -- leaked exchange API credentials enable unauthorized market access. You can't author workflows safely without first understanding the security landscape.

---

### P2: Workflow Authoring & Validation (Highest Time Cost)

**Problem**: "YAML is great to read, and a nightmare to write." Average workflows are ~60 lines of YAML with complex syntax, no LSP, and poor documentation. Local testing with `act` only works for Ubuntu containers.

**Capability**:
- Generate GitHub Actions workflows from natural language descriptions (e.g., "create a CI pipeline that runs pytest, lints with ruff, and deploys to staging on merge to main")
- Validate existing workflows using actionlint-style rules (syntax, expression validation, shellcheck integration)
- Detect common anti-patterns: unpinned action versions, excessive permissions, hardcoded secrets, missing concurrency controls
- Suggest optimizations: caching strategies, job parallelization, matrix builds, reusable workflows

**Triaging**: Validation is read-only. Generation writes to `.github/workflows/` with user review. Never overwrites existing workflows without confirmation.

**Evidence**: Only ~10% of projects include deployment steps in workflows. Common deficiencies include "hard-coded versions, excessive permissions, and redundant logic" ([arxiv](https://arxiv.org/html/2507.18062)).

---

### P3: Compliance Readiness Check (Trading-Specific High Value)

**Problem**: FINRA 15-09, SEC 15c3-5, MiFID II RTS 6, and SOX all demand specific controls around algo trading code deployment, but GitHub provides no native tooling to verify whether pipeline configurations meet these requirements.

**Disclaimer**: This feature provides **engineering guidance for compliance readiness**, not legal or regulatory advice. Outputs are not audit-grade artifacts and must be validated by compliance officers before regulatory submission.

**Capability**:
- Check branch protection rules against compliance requirements (required reviewers, status checks, signed commits) -- verifiable via `gh api`
- Validate that workflows enforce separation of duties (SOX: developer != deployer) -- verifiable via workflow YAML + branch protection config
- Verify that approval gates, testing stages, and deployment controls exist in the pipeline -- verifiable via workflow YAML
- Generate a compliance readiness report documenting what is configured and what gaps exist
- Flag where organizational processes (not just technical controls) are needed but cannot be verified by this tool

**What This Feature CANNOT Verify** (requires organizational process, not GitHub config):
- Whether approval protocols are *appropriate* for the scope of code changes (FINRA 15-09)
- Whether QA testing is *independent* of development (organizational structure)
- Whether supervisory staff *understand* algorithmic strategies (human competency)
- Whether code archival periods are *reasonable* for the firm's size (business judgment)

**Triaging**: All compliance checks are read-only. Report generation creates files in a designated output directory. Configuration changes (branch protection, required reviewers) require explicit confirmation.

**Evidence**: SOX compliance requires "formal, auditable change management documenting who requested, approved, implemented, and verified each change" ([Harness](https://www.harness.io/harness-devops-academy/sox-compliance-for-software-delivery-explained)). FINRA expects "a set of approval protocols that are appropriate given the scope of the code or any change(s) to the code" ([FINRA 15-09](https://www.finra.org/rules-guidance/notices/15-09)).

---

### P4: Pipeline Status Dashboard (Quality of Life)

**Problem**: Developers context-switch between terminal and browser to check pipeline status. For trading firms, knowing deployment status during market hours is critical.

**Capability**:
- Show current status of all workflow runs for the repo (via `gh run list`)
- Display run details, job breakdown, and step-level timing
- Highlight failing runs with quick links to relevant logs
- Show deployment status and environment health
- Track pipeline performance trends (duration, success rate)

**Triaging**: Purely read-only. Uses `gh` CLI exclusively. Never modifies anything.

---

### P5: Deployment Safety Analysis (Knight Capital Prevention)

**Problem**: GitHub Actions is forward-only with no native rollback mechanism. Trading firms need deployment patterns analogous to their trading kill switches.

**Capability**:
- Analyze deployment workflows for safety patterns (canary releases, rollback steps, health checks)
- Recommend deployment safety improvements based on the codebase
- Suggest rollback approaches: re-running a previous successful workflow, `git revert` commands, or workflow-defined rollback steps
- Validate that kill-switch/circuit-breaker patterns exist in deployment workflows

**Scope Limitation**: This skill operates at the CI/CD pipeline layer. It can re-trigger workflows and suggest git operations, but **cannot execute infrastructure-level rollbacks** (e.g., Kubernetes rollback, AWS Lambda version revert). Those require infrastructure-specific tooling.

**Triaging**: Analysis and recommendations are read-only. Workflow re-triggers require explicit confirmation.

**Note on Knight Capital**: The Knight Capital incident ($440M loss) was a code deployment failure (old code activated on 1 of 8 servers), not a CI/CD pipeline failure per se. However, it illustrates why the deployment pipeline layer matters: a CI/CD system that verified all servers received the correct code version before routing traffic would have prevented the incident.

**Evidence**: Canary releases reduce rollback incidents by 50%. Knight Capital's deployment failure highlights the need for automated verification ([source](https://www.kosli.com/blog/knight-capital-a-story-about-devops-automated-governance/)).

---

### P6: Cost Optimization (Strategic Value)

**Problem**: GitHub Actions costs are a growing concern, especially with the 2025/2026 pricing changes. Trading firms using self-hosted runners face new per-minute charges.

**Capability**:
- Analyze workflow efficiency: unnecessary steps, missing caches, redundant builds
- Estimate cost impact of workflow changes
- Suggest optimization strategies: job consolidation, cache optimization, conditional execution
- Compare current usage against GitHub pricing tiers

**Triaging**: Purely read-only analysis. Optimization changes to workflow files require user review.

**Evidence**: GitHub Actions now processes 71 million jobs/day. The 5GB cache limit, concurrency limits, and VM spin-up latency cause significant waste ([GitHub Blog](https://github.blog/news-insights/product-news/lets-talk-about-github-actions/)). One case study showed 77% cost reduction through optimization ([source](https://dev.to/aws-builders/cut-cicd-costs-by-77-2x-deployment-speed-with-github-actions-on-eks-auto-2ob2)).

## 5. What This Skill Does NOT Do

- **Does NOT replace GitHub Actions** - it manages, debugs, and improves existing pipelines
- **Does NOT auto-deploy code** - deployment triggering always requires explicit user confirmation
- **Does NOT store secrets** - it audits secrets management practices but never handles credential values
- **Does NOT modify branch protection rules without confirmation** - all config changes require explicit approval
- **Does NOT support non-GitHub CI/CD platforms** (future consideration)
- **Does NOT manage cross-repository pipeline dependencies** -- operates on the current repository only
- **Does NOT provide local CI/CD testing** (use `act` for that; this skill focuses on remote pipeline management)
- **Does NOT provide regulatory or legal advice** -- compliance features are engineering guidance only

## 6. Technical Approach

### Skill Architecture

The deliverable is a single Claude Code skill file (`.md`) that encodes CI/CD domain knowledge and behavioral rules. It leverages Claude Code's existing capabilities:
- **Bash tool**: Executes `gh` CLI commands for all GitHub API interactions
- **Read/Write/Edit tools**: Manages `.github/workflows/` YAML files
- **Glob/Grep tools**: Finds and searches workflow files in the repository

The skill does NOT introduce new slash commands, agents, or hooks. It works by providing Claude Code with structured instructions that activate when the user's request matches CI/CD contexts (pipeline failures, workflow management, security concerns, compliance questions).

**Future expansion**: If warranted, the skill can later be promoted to a full plugin with dedicated slash commands (e.g., `/cicd-diagnose`), agents, and hooks. The skill serves as the knowledge foundation.

### Tools Used

| Tool | Purpose |
|------|---------|
| `gh run list/view/watch` | Pipeline status and logs |
| `gh workflow list/view/run` | Workflow management |
| `gh secret list` | Secrets audit (read-only) |
| `gh api` | Advanced GitHub API queries |
| File Read/Write | Workflow YAML management |
| `actionlint` (if available) | YAML validation |

### Triaging Decision Tree

```
User request received
  |
  +-- Is it a read-only query? (status, logs, audit)
  |     -> Execute immediately via gh CLI
  |
  +-- Is it a YAML modification? (create, edit, fix workflow)
  |     -> Show proposed changes -> Wait for user approval -> Apply
  |
  +-- Is it a pipeline trigger? (run, rerun, cancel)
  |     -> Show what will be triggered -> Require explicit confirmation
  |
  +-- Is it a config change? (branch protection, secrets, environments)
  |     -> Show current state -> Show proposed changes -> Require confirmation
  |
  +-- Is it destructive? (delete workflow, remove secret)
        -> Show what will be deleted -> Require double confirmation
```

## 7. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| CI/CD failure resolution time | < 20 minutes (from ~2.5 hours industry estimate*) | Time from error to fix |
| Workflow authoring time | < 2 minutes for standard pipelines | Time to generate valid workflow |
| Security vulnerabilities detected | > 90% of known anti-patterns | Comparison with actionlint + zizmor |
| Compliance readiness coverage | 100% of FINRA 15-09 requirements **verifiable through GitHub API/YAML inspection** | Checklist of verifiable vs. non-verifiable items |
| Triaging predictability | Zero unintended write operations | Scenario-based testing against ambiguous prompts |

*Note: The 2.5-hour baseline is from an industry blog post ([source](https://markaicode.com/ai-fix-cicd-pipeline-failures-github-actions/)), not a peer-reviewed study. Should be validated against internal data.

## 8. Competitive Landscape

| Competitor | Strength | Gap This Skill Fills |
|-----------|----------|---------------------|
| **Claude Code (unprompted)** | Already has `gh` CLI access, codebase awareness, can read/write YAML | No consistent triaging behavior; no domain-specific CI/CD knowledge; ad-hoc results vary |
| **Gitar.ai** | Auto-fixes test failures autonomously | No codebase context; standalone tool, not in developer's terminal |
| **GitHub Copilot** | Native GitHub integration, Cloud Agent | No compliance features; limited CI/CD debugging depth |
| **Cursor** | `cursor-agent` in Actions | IDE-bound; no trading-specific compliance |
| **OpenAI Codex** | Auto-fix cookbook for CI | No unified tool; no compliance or security audit |
| **actionlint** | YAML validation (24+ rules) | Static only; no AI-powered diagnosis or fix |
| **zizmor** | Security scanning for Actions | Security only; no authoring, diagnosis, or compliance |
| **Datadog CI Visibility** | Pipeline monitoring & observability | Monitoring only; no authoring, fixing, or compliance. Trading firms likely already use this -- P4 (Status Dashboard) is terminal convenience, not a replacement |

**Honest Delta Over Vanilla Claude Code**: A developer can already ask Claude Code "run `gh run list` and tell me what's failing." This skill's actual value-add is:
1. **Consistent triaging behavior** -- predictable read/write/confirm escalation instead of ad-hoc prompting
2. **Pre-built domain expertise** -- trading compliance knowledge, security best practices, FINRA/SOX requirements
3. **Context-triggered activation** -- Claude auto-activates CI/CD expertise when it detects pipeline-related requests
4. **Structured diagnostic approach** -- systematic root cause analysis rather than ad-hoc log reading

## 9. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Skill modifies workflows incorrectly | Strict triaging rules: never auto-write without user review. Ambiguous requests default to read-only. |
| Security audit misses vulnerabilities | Combine AI analysis with static tools (actionlint, zizmor) when available. Clearly state coverage limitations. |
| Compliance advice is legally inaccurate | Prominent disclaimer on all compliance outputs. Explicitly enumerate what can vs. cannot be verified via GitHub API. |
| Over-reliance on gh CLI availability | Check for `gh` on plugin load; graceful degradation with clear error messages if not configured. |
| Prompt injection through CI log analysis | **Open risk.** CI logs are untrusted input. Primary defense: triaging rules require user confirmation for all write operations, so even if log content attempts injection, no write action occurs without human approval. Log sanitization is a secondary defense but cannot fully prevent prompt injection. |
| CVE data staleness | CVE checks via `gh api` to GitHub Advisory Database provide current data. Claude's training knowledge is supplementary but may be stale -- always prefer API data. |
| Cost estimation requires admin permissions | `gh api` billing endpoints require org admin access. Feature gracefully degrades if permissions are insufficient, focusing on workflow-level optimization analysis instead. |

## 10. Implementation Phases

| Phase | Features | Classification | Rationale |
|-------|----------|---------------|-----------|
| **MVP** | P0 (Failure Diagnosis) + P1 (Security Audit) | MUST HAVE | Addresses the two highest-impact problems: blocked deployments and supply chain risk. Low-to-medium complexity. |
| **V2** | P2 (Workflow Authoring) + P3 (Compliance Readiness) | SHOULD HAVE | Productivity + regulatory value. Build on proven MVP foundation. |
| **Future** | P4 (Status Dashboard) + P5 (Deployment Safety) + P6 (Cost Optimization) | NICE TO HAVE | Genuine value but lower priority or higher complexity. P4 can be absorbed into MVP as a thin addition if time permits. |

### Testing Approach

Triaging rules (the skill's core differentiator) will be validated through **scenario-based testing**: a set of ambiguous user prompts will be tested to verify the plugin defaults to the correct action tier. Test scenarios include:
- "Fix my CI" -> must diagnose only, not edit files
- "My workflow has a security issue" -> must audit only, not modify
- "Delete the old workflow" -> must require double confirmation
- "Run the tests" -> must confirm before triggering

---

## References

### Regulatory
- [FINRA Regulatory Notice 15-09](https://www.finra.org/rules-guidance/notices/15-09)
- [FINRA Regulatory Notice 16-21](https://www.finra.org/rules-guidance/notices/16-21)
- [SEC Rule 15c3-5 Market Access Rule](https://www.sec.gov/rules-regulations/staff-guidance/trading-markets-frequently-asked-questions/divisionsmarketregfaq-0)
- [SOX Compliance for Software Delivery](https://www.harness.io/harness-devops-academy/sox-compliance-for-software-delivery-explained)
- [MiFID II RTS 6 Algorithmic Trading](https://www.centralbank.ie/docs/default-source/regulation/industry-market-sectors/investment-firms/mifid-firms/regulatory-requirements-and-guidance/thematic-assessment-of-algorithmic-trading-firms-compliance.pdf)

### Incidents & Case Studies
- [Knight Capital: $440M Loss in 45 Minutes](https://dougseven.com/2014/04/17/knightmare-a-devops-cautionary-tale/)
- [Knight Capital: DevOps Automated Governance](https://www.kosli.com/blog/knight-capital-a-story-about-devops-automated-governance/)
- [tj-actions Supply Chain Attack (CVE-2025-30066)](https://thehackernews.com/2025/03/github-action-compromise-puts-cicd.html)
- [PromptPwnd: AI Prompt Injection in CI/CD](https://www.aikido.dev/blog/promptpwnd-github-actions-ai-agents)

### Developer Pain Points
- [HN: "I Hate GitHub Actions With Passion"](https://news.ycombinator.com/item?id=46614558)
- [HN: "The Pain That Is GitHub Actions"](https://news.ycombinator.com/item?id=43419701)
- [Developers Ditch GitHub Actions Over Reliability](https://www.webpronews.com/developers-ditch-github-actions-over-reliability-and-pricing-issues/)
- [GitHub Actions Pricing Backlash](https://github.com/orgs/community/discussions/182089)

### Research
- [AI Agents & CI/CD Configuration (arxiv 2601.17413)](https://arxiv.org/html/2601.17413v1)
- [GitHub Actions Workflow Complexity Study](https://arxiv.org/html/2507.18062)
- [AI Fix CI/CD Pipeline Failures](https://markaicode.com/ai-fix-cicd-pipeline-failures-github-actions/)

### Existing Tools & Competitors
- [Claude Code GitHub Action](https://github.com/anthropics/claude-code-action)
- [actionlint](https://github.com/rhysd/actionlint)
- [nektos/act](https://github.com/nektos/act)
- [zizmor Security Scanner](https://zizmor.sh/)
- [Gitar.ai](https://cms.gitar.ai/automated-test-failure-resolution-github-github-automation/)
- [OpenAI Codex Auto-Fix Cookbook](https://developers.openai.com/cookbook/examples/codex/autofix-github-actions/)
- [Datadog CI Visibility](https://docs.datadoghq.com/continuous_integration/pipelines/github/)
