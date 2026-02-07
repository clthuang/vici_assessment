# GitHub Claude Skills

Claude Code skill plugin for GitHub Actions CI/CD diagnosis and security auditing.

**VICI Challenge Task 3 — Medium**

## Status

Complete (v1.0.0) — P0 Pipeline Failure Diagnosis + P1 Security Audit

## Available Skills

### GitHub CI/CD Guardian

AI-powered CI/CD specialist that diagnoses pipeline failures and audits workflow security.

**Trigger phrases:** "fix my CI", "why is CI failing", "audit workflow security", "check CI security"

| Capability | Description |
|---|---|
| **P0: Pipeline Failure Diagnosis** | Fetches failed run logs, categorizes failures (6 categories), proposes fixes with user approval |
| **P1: Security Audit** | Scans workflow files against 8 anti-patterns, checks for hardcoded secrets, generates severity-ranked report |

## Prerequisites

- [GitHub CLI (`gh`)](https://cli.github.com/) installed and authenticated
- Repository with GitHub Actions workflows

## Plugin Structure

```
github-claude-skills/
  .claude-plugin/
    plugin.json                              # Plugin manifest
  skills/
    github-cicd-guardian/
      SKILL.md                               # Skill instructions (238 lines)
      references/
        failure-categories.md                # 6 failure categories with log signatures
        security-checklist.md                # 8 security anti-patterns with remediation
  tests/
    validate_skill.sh                        # 67 automated validation checks
    fixtures/
      sample-failure-logs.md                 # Test fixtures for P0 categorization
      vulnerable-workflow.yml                # Test fixture with all 8 anti-patterns
```

## Validation

```bash
bash github-claude-skills/tests/validate_skill.sh
```

Runs 67 checks across 8 phases: structural integrity, plugin manifest, frontmatter, P0 content, P1 content, triaging rules, reference files, and security invariants.
