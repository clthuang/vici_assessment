#!/usr/bin/env bash
# GitHub CI/CD Guardian Skill - Validation Suite
# Validates structural integrity and content completeness of the skill plugin.
#
# Usage: bash tests/validate_skill.sh
# Exit code: 0 = all checks pass, 1 = failures found

set -euo pipefail

PLUGIN_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0
FAIL=0

check() {
    local desc="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc"
        FAIL=$((FAIL + 1))
    fi
}

check_grep() {
    local desc="$1"
    local pattern="$2"
    local file="$3"
    if grep -q "$pattern" "$file" 2>/dev/null; then
        echo "  PASS: $desc"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $desc"
        FAIL=$((FAIL + 1))
    fi
}

echo "=== GitHub CI/CD Guardian Skill Validation ==="
echo ""

# ── Phase 1: Structural Validation ──
echo "── Phase 1: Structural Validation ──"

check "plugin.json exists" test -f "$PLUGIN_ROOT/.claude-plugin/plugin.json"
check "plugin.json is valid JSON" python3 -m json.tool "$PLUGIN_ROOT/.claude-plugin/plugin.json"
check "SKILL.md exists" test -f "$PLUGIN_ROOT/skills/github-cicd-guardian/SKILL.md"
check "failure-categories.md exists" test -f "$PLUGIN_ROOT/skills/github-cicd-guardian/references/failure-categories.md"
check "security-checklist.md exists" test -f "$PLUGIN_ROOT/skills/github-cicd-guardian/references/security-checklist.md"

# Line count checks
SKILL_LINES=$(wc -l < "$PLUGIN_ROOT/skills/github-cicd-guardian/SKILL.md")
check "SKILL.md under 500 lines ($SKILL_LINES)" test "$SKILL_LINES" -lt 500

echo ""

# ── Phase 2: Plugin Manifest ──
echo "── Phase 2: Plugin Manifest ──"

check_grep "plugin.json has name field" '"name"' "$PLUGIN_ROOT/.claude-plugin/plugin.json"
check_grep "plugin name is github-cicd-guardian" '"github-cicd-guardian"' "$PLUGIN_ROOT/.claude-plugin/plugin.json"
check_grep "plugin.json has version" '"version"' "$PLUGIN_ROOT/.claude-plugin/plugin.json"

echo ""

# ── Phase 3: SKILL.md Frontmatter ──
echo "── Phase 3: SKILL.md Frontmatter ──"

check_grep "Has name field" "^name:" "$PLUGIN_ROOT/skills/github-cicd-guardian/SKILL.md"
check_grep "Has description field" "^description:" "$PLUGIN_ROOT/skills/github-cicd-guardian/SKILL.md"
check_grep "Has version field" "^version:" "$PLUGIN_ROOT/skills/github-cicd-guardian/SKILL.md"

# Description length check
DESC=$(grep "^description:" "$PLUGIN_ROOT/skills/github-cicd-guardian/SKILL.md" | sed 's/^description: //')
DESC_LEN=${#DESC}
check "Description under 200 chars ($DESC_LEN)" test "$DESC_LEN" -lt 200

echo ""

# ── Phase 4: P0 Content Checks ──
echo "── Phase 4: P0 Content Checks ──"

SKILL="$PLUGIN_ROOT/skills/github-cicd-guardian/SKILL.md"
check_grep "P0 section exists" "## P0: Pipeline Failure Diagnosis" "$SKILL"
check_grep "gh run list command" "gh run list" "$SKILL"
check_grep "gh run view --log-failed" "log-failed" "$SKILL"
check_grep "--log fallback" "fall back" "$SKILL"
check_grep "failure-categories.md reference" "references/failure-categories.md" "$SKILL"
check_grep "3-option approval (Apply)" "Apply" "$SKILL"
check_grep "3-option approval (Re-run)" "Re-run" "$SKILL"
check_grep "3-option approval (Skip)" "Skip" "$SKILL"
check_grep "Untrusted log instruction" "untrusted" "$SKILL"
check_grep "User confirmation required" "user confirms" "$SKILL"
check_grep "Error: 403 handling" "403" "$SKILL"
check_grep "Error: 429 handling" "429" "$SKILL"
check_grep "Error: network error" "Cannot reach" "$SKILL"

echo ""

# ── Phase 5: P1 Content Checks ──
echo "── Phase 5: P1 Content Checks ──"

check_grep "P1 section exists" "## P1: Security Audit" "$SKILL"
check_grep "Read-only instruction" "read-only" "$SKILL"
check_grep "Glob .yml files" ".yml" "$SKILL"
check_grep "Glob .yaml files" ".yaml" "$SKILL"
check_grep "zizmor check" "which zizmor" "$SKILL"
check_grep "security-checklist.md reference" "references/security-checklist.md" "$SKILL"
check_grep "Template injection check (P1-4)" "github.event" "$SKILL"
check_grep "Layered vulnerability check" "layered" "$SKILL"
check_grep "Security advisories API" "security-advisories" "$SKILL"
check_grep "Limitations disclaimer" "does not guarantee" "$SKILL"
check_grep "No workflows found error" "No GitHub Actions workflows" "$SKILL"
check_grep "Secret value protection" "Do not display actual secret values" "$SKILL"

echo ""

# ── Phase 6: Triaging Rules ──
echo "── Phase 6: Triaging Rules ──"

check_grep "Rule 1: Read freely" "Read and analyze freely" "$SKILL"
check_grep "Rule 2: Write with confirmation" "write only with confirmation" "$SKILL"
check_grep "Rule 3: Double confirmation" "double confirmation" "$SKILL"
check_grep "Ambiguity: Check my CI" "Check my CI" "$SKILL"
check_grep "Ambiguity: Fix my CI" "Fix my CI" "$SKILL"
check_grep "Ambiguity: Delete" "Delete" "$SKILL"

echo ""

# ── Phase 7: Reference Files ──
echo "── Phase 7: Reference Files ──"

CATS="$PLUGIN_ROOT/skills/github-cicd-guardian/references/failure-categories.md"
check_grep "Category: Dependency Issue" "Dependency Issue" "$CATS"
check_grep "Category: YAML Misconfiguration" "YAML Misconfiguration" "$CATS"
check_grep "Category: Code Bug" "Code Bug" "$CATS"
check_grep "Category: Flaky Test" "Flaky Test" "$CATS"
check_grep "Category: Infrastructure" "Infrastructure" "$CATS"
check_grep "Category: Permissions" "Permissions" "$CATS"

CHECKS="$PLUGIN_ROOT/skills/github-cicd-guardian/references/security-checklist.md"
check_grep "Anti-pattern 1: Unpinned Actions" "Unpinned Actions" "$CHECKS"
check_grep "Anti-pattern 2: Overly Broad" "Overly Broad" "$CHECKS"
check_grep "Anti-pattern 3: Hardcoded Secrets" "Hardcoded Secrets" "$CHECKS"
check_grep "Anti-pattern 4: Secret in Echo" "Secret in Echo" "$CHECKS"
check_grep "Anti-pattern 5: PR Target Trigger" "Pull Request Target" "$CHECKS"
check_grep "Anti-pattern 6: Mutable Refs" "Mutable Action" "$CHECKS"
check_grep "Anti-pattern 7: CODEOWNERS" "CODEOWNERS" "$CHECKS"
check_grep "Anti-pattern 8: Artifact Exposure" "Artifact Exposure" "$CHECKS"
check_grep "P1-3 regex: AWS keys" "AKIA" "$CHECKS"
check_grep "P1-3 regex: GitHub PATs" "ghp_" "$CHECKS"
check_grep "P1-3 regex: Generic tokens" "gh\[pousr\]" "$CHECKS"

echo ""

# ── Phase 8: Security Invariants ──
echo "── Phase 8: Security Invariants ──"

check_grep "SM-7: Untrusted log content" "untrusted" "$SKILL"
check_grep "SM-6: Read-only audit" "Do NOT modify" "$SKILL"
check_grep "SM-8: No secret values" "Do not display actual secret values" "$SKILL"
check_grep "SM-9: Limitations disclaimer" "does not guarantee comprehensive coverage" "$SKILL"
check_grep "SM-4: User confirmation" "I need your confirmation" "$SKILL"
check_grep "Credential redaction" "REDACTED" "$SKILL"

echo ""
echo "=== Results ==="
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
echo "  Total:  $((PASS + FAIL))"
echo ""

if [ "$FAIL" -gt 0 ]; then
    echo "VALIDATION FAILED"
    exit 1
else
    echo "ALL CHECKS PASSED"
    exit 0
fi
