# Implementation Plan: GitHub CI/CD Guardian Skill

## Overview

Implement a Claude Code plugin consisting of 4 markdown/JSON files (~345 lines total) that provide CI/CD diagnosis and security audit capabilities. All deliverables are static content files -- no compilation, no runtime dependencies, no build step.

**Source artifacts**: [spec.md](spec.md) | [design.md](design.md) | [prd.md](prd.md)

## Implementation Order

### Phase 1: Foundation (plugin manifest + directory structure)

**Goal**: Establish the plugin structure so Claude Code can discover the plugin.

**Step 1.1: Create directory structure and plugin manifest**
- Create all directories: `github-claude-skills/.claude-plugin/`, `github-claude-skills/skills/github-cicd-guardian/references/`
- Create `github-claude-skills/.claude-plugin/plugin.json`
- Content: exactly as specified in design Section 2.1 (name, description, version)
- ~5 lines
- Note: `github-claude-skills/README.md` already exists in the scaffold -- leave as-is for now

**Verification**: `python -m json.tool github-claude-skills/.claude-plugin/plugin.json` succeeds, `name` field is `"github-cicd-guardian"`, all directories exist

**Dependencies**: None (first step)

---

### Phase 2: Reference Files (loaded on-demand by SKILL.md)

**Goal**: Create the two reference files that SKILL.md will instruct Claude to read. These are independent of each other and of SKILL.md, so they can be written first. Writing them first ensures SKILL.md can reference verified file paths.

**Step 2.1: Create failure-categories.md**
- Create `github-claude-skills/skills/github-cicd-guardian/references/failure-categories.md`
- Content: 6 failure categories with log signature patterns, per design Section 2.7
- Categories: dependency issue, YAML misconfiguration, code bug, flaky test, infrastructure, permissions
- Each category has: name, log signatures (grep-able patterns), example log line
- ~40 lines

**Verification**:
- All 6 categories from spec P0-3 present
- Each category has at least 2 log signature patterns
- Each category has a concrete example

**Dependencies**: Step 1.1 (creates `skills/github-cicd-guardian/references/` directory)

**Step 2.2: Create security-checklist.md**
- Create `github-claude-skills/skills/github-cicd-guardian/references/security-checklist.md`
- Content: 8 anti-patterns with detection patterns, per design Section 2.6
- Follow the design's 8-entry structure exactly (design Section 2.6):
  1. Unpinned Actions (P1-1) [Critical]
  2. Overly Broad Permissions (P1-2) [Critical]
  3. Hardcoded Secrets (P1-3) [Critical]
  4. Secret in Echo (P1-5) [Critical]
  5. Pull Request Target Trigger (P1-7) [Warning]
  6. Mutable Action References (P1-1 subset) [Warning]
  7. Missing CODEOWNERS (P1-7) [Informational]
  8. Artifact Exposure (P1-7) [Warning]
- Note: Template Injection (P1-4) is covered by SKILL.md P1 Step 3b pattern matching, not as a separate checklist entry -- it's checked inline via Claude's reading of workflow files. The 8 entries above match the design's authoritative list.
- Include P1-3 regex patterns: `AKIA[0-9A-Z]{16}`, `ghp_[A-Za-z0-9_]{36}`, `gh[pousr]_[A-Za-z0-9_]{36,}`, plus YAML key patterns
- Each entry: pattern name, spec mapping, "what to look for", severity, remediation
- ~80 lines

**Verification**:
- All 8 anti-patterns from spec Section 3.2 present (cross-reference spec items 1-8 to design entries)
- P1-3 regex patterns included
- Severity levels assigned (Critical/Warning/Informational)
- Each entry has a concrete "look for" pattern and remediation

**Dependencies**: Step 1.1 (creates `skills/github-cicd-guardian/references/` directory)

---

### Phase 3: SKILL.md (primary deliverable)

**Goal**: Create the main skill file that encodes CI/CD expertise as structured instructions for Claude.

**Step 3.1: Write SKILL.md preamble**
- Create `github-claude-skills/skills/github-cicd-guardian/SKILL.md`
- Write frontmatter with 3 fields per Claude Code plugin docs:
  - `name: GitHub CI/CD Guardian`
  - `description`: Use third-person trigger-phrase format for reliable auto-triggering (per Claude Code skill development docs): `This skill should be used when the user asks to "fix my CI", "why is CI failing", "audit workflow security", "check CI security", or mentions GitHub Actions failures, pipeline diagnosis, or CI/CD security audits.` (~199 chars)
  - `version: 1.0.0`
- Note: The spec's original 97-char declarative description is superseded by the trigger-phrase format based on Claude Code's documented best practice for auto-activation. The semantic content is preserved.
- Write context section (trading firm domain expertise, per design Section 2.3)
- Write prerequisites check: `gh auth status` instruction with error table
- Write repository context resolution: `gh repo view --json owner,name --jq` command
- ~30 lines for frontmatter + preamble

**Verification**:
- Frontmatter has `name`, `description`, and `version` fields
- Description uses third-person trigger-phrase format with quoted user intents
- Description is under 200 characters
- Prerequisites check uses `gh auth status` (not separate `which gh` + `gh auth status`)
- Error messages match spec Section 8

**Dependencies**: Step 1.1 (directory exists)

**Step 3.2: Write triaging rules section**
- Add triaging rules: 3 behavioral rules from spec Section 5.1, verbatim
- Add ambiguity resolution table: 5-row table from spec Section 5.2
- Add action classification reference table from spec Section 5.3
- ~30 lines

**Verification**:
- All 3 rules present and match spec Section 5.1
- All 5 ambiguity rows present and match spec Section 5.2
- Action classification covers: read, analyze, propose, write, execute, destroy

**Dependencies**: Step 3.1 (file exists)

**Step 3.3: Write P0 diagnosis workflow**
- Add P0 section with 6-step procedure per design Section 2.4
- Step 1: Fetch status (`gh run list --limit 10`) with run-ID bypass
- Step 2: Identify failure (select most recent failed run)
- Step 3: Fetch logs (`gh run view --log-failed` with `--log` fallback and P0-NF4 truncation)
- Step 4: Categorize (instruct Claude to read `references/failure-categories.md`, match patterns)
- Step 5: Propose fix (3-part output format: explanation, diff, 3-option approval prompt)
- Step 6: Apply with confirmation (write/edit/rerun, suggest actionlint after YAML changes)
- Include error handling inline per design Section 2.8
- ~80 lines

**Verification**:
- All 6 steps present with correct tool assignments
- Step 3 includes `--log-failed` fallback to `--log`
- Step 4 explicitly references `references/failure-categories.md`
- Step 5 output format matches design template exactly (3 options: Apply/Re-run/Skip)
- Step 6 requires user confirmation before any write/execute
- P0-NF3 addressed: log content treated as untrusted (no auto-execution of commands in logs)
- Error handling included: 403 (scope suggestion), 429 (rate limit), network error, empty `--log-failed` (fallback), no logs available, ambiguous logs (ask user)

**Dependencies**: Step 3.2 (sections written in order), Step 2.1 (failure-categories.md path confirmed)

**Step 3.4: Write P1 security audit workflow**
- Add P1 section with 5-step procedure per design Section 2.5
- Step 1: Discover workflow files (Glob `.github/workflows/*.yml` and `*.yaml`)
- Step 2: Check zizmor availability (`which zizmor`)
- Step 3a: If zizmor available, run `zizmor --format json`
- Step 3b: Always read each workflow file + check against `references/security-checklist.md`
- Step 4: Layered vulnerability check (zizmor data > gh api advisories > Claude knowledge with caveat)
- Step 5: Generate report (Critical/Warning/Informational + Limitations disclaimer)
- Handle "no workflows found" error case per spec Section 8
- ~80 lines

**Verification**:
- All 5 steps (with 3a/3b split) present
- Step 1 covers both `.yml` and `.yaml` extensions (P1-NF1)
- Step 3b explicitly references `references/security-checklist.md`
- Step 4 layered approach matches design (zizmor primary, gh api supplementary, Claude fallback with caveat)
- Step 5 report format matches design template (Critical/Warning/Informational/Limitations)
- Entire P1 flow is read-only (P1-8, SM-6)
- Limitations disclaimer always included (SM-9)

**Dependencies**: Step 3.3 (sections written in order), Step 2.2 (security-checklist.md path confirmed)

---

### Phase 4: Validation

**Goal**: Verify the implementation meets all design constraints and spec requirements.

**Step 4.1: Structural validation**
- Verify plugin structure matches design directory tree: `find github-claude-skills/ -type f`
- Verify plugin.json is valid JSON: `python -m json.tool github-claude-skills/.claude-plugin/plugin.json`
- Verify SKILL.md frontmatter: grep for `---` delimiters, `name:`, `description:`, `version:` fields
- Count SKILL.md lines: `wc -l github-claude-skills/skills/github-cicd-guardian/SKILL.md` (target: ~220, must be under 500)
- Count total lines: `wc -l` across all 4 files (target: ~345)

**Step 4.2: Content cross-reference**
- Verify all 6 P0 functional requirements (P0-1 through P0-6) are addressable by SKILL.md instructions
- Verify all 8 P1 functional requirements (P1-1 through P1-8) are addressable by SKILL.md instructions
- Verify all 3 triaging rules present
- Verify all 5 ambiguity resolution rows present
- Verify all 6 failure categories in failure-categories.md
- Verify all 8 anti-patterns in security-checklist.md
- Verify error handling covers all 9 conditions from spec Section 8:
  1. `gh` not installed
  2. `gh` not authenticated
  3. Insufficient token scope (403)
  4. No workflow files found
  5. `gh run view` returns no logs
  6. Log output too large (P0-NF4 truncation)
  7. Ambiguous failure logs
  8. `gh api` rate limited (429)
  9. Network error

**Step 4.3: Security invariant check**
- Verify SKILL.md instructs Claude to never execute commands from logs (P0-NF3, SM-7)
- Verify P1 flow is explicitly read-only with no write instructions (P1-8, SM-6)
- Verify secret values are never displayed -- only names audited (P1-NF2, SM-8)
- Verify limitations disclaimer is part of P1 report template (P1-NF3, SM-9)
- Verify all write/execute actions require user confirmation (SM-4)

**Dependencies**: Steps 3.1-3.4 complete

---

## Dependency Graph

```
Phase 1: Foundation
  1.1 plugin.json ──────────────┐
                                 │
Phase 2: References (parallel)   │
  2.1 failure-categories.md ────┤
  2.2 security-checklist.md ────┤
                                 │
Phase 3: SKILL.md (sequential)   │
  3.1 Preamble ─────────────────┤
  3.2 Triaging rules ───────────┤
  3.3 P0 diagnosis (needs 2.1) ─┤
  3.4 P1 audit (needs 2.2) ─────┤
                                 │
Phase 4: Validation              │
  4.1 Structure ─────────────────┘
  4.2 Content cross-reference
  4.3 Security invariants
```

Steps 2.1 and 2.2 can be implemented in parallel. Steps 3.1-3.4 are sequential (building up the SKILL.md file). Phase 4 runs after all implementation is complete.

## Risks

| Risk | Mitigation |
|------|-----------|
| SKILL.md exceeds ~220 line target | Monitor during Step 3.x writes. If approaching limit, compress prose. Token budget has ~280 line buffer before the 500-line hard limit |
| Reference file paths wrong in SKILL.md | Writing reference files (Phase 2) before SKILL.md (Phase 3) ensures paths are verified |
| Anti-pattern numbering mismatch between spec and design | Design Section 2.6 shows the authoritative 8-entry structure. Follow design, cross-reference spec |
| Claude doesn't follow SKILL.md instructions as intended | Use numbered imperative steps, explicit "THEN" transitions, and prescribed output templates per design D4 and D6 |

## Out of Scope for This Plan

- V2 features (P2, P3) -- explicitly excluded per spec Section 4
- Test workflow creation for T6 scenario -- testing strategy is defined in design Section 5 but execution is post-implementation
- Architecture diagram regeneration for .claude-plugin/ -- noted in review history as deferred
