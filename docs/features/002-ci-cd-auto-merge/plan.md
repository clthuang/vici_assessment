# CI/CD Auto-Merge Pipeline - Implementation Plan

**Feature:** 002-ci-cd-auto-merge
**Date:** February 3, 2026
**Status:** Ready for Implementation

---

## Overview

This plan details the implementation steps for the CI/CD auto-merge pipeline. The work modifies a single file (`.github/workflows/ci.yml`) with careful sequencing to ensure each change can be tested independently.

---

## Dependency Graph

```
P1: Update trigger branches
       │
       ▼
P2: Migrate lint job to uv
       │
       ▼
P3: Migrate test job to uv + coverage enforcement
       │
       ▼
P4: Migrate build job to uv
       │
       ▼
P5: Add create-pr job
       │
       ▼
P6: Manual verification
       │
       ▼
P7: Configure branch protection (manual)
```

---

## Implementation Steps

### P1: Update Trigger Branches

**Description:** Add `fix/*` pattern to push trigger branches.

**File:** `.github/workflows/ci.yml`

**Changes:**
```yaml
# Before
on:
  push:
    branches: [main, feature/*]

# After
on:
  push:
    branches: [main, feature/*, fix/*]
```

**Verification:**
- Workflow YAML syntax valid
- Push to `fix/test` branch triggers workflow

**Dependencies:** None

---

### P2: Migrate lint Job to uv

**Description:** Convert lint job from pip to uv for consistency.

**File:** `.github/workflows/ci.yml`

**Changes:**
```yaml
lint:
  name: Lint
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"

    - name: Install uv
      uses: astral-sh/setup-uv@v3

    - name: Install dependencies
      run: uv sync --all-groups

    - name: Run ruff
      run: uv run ruff check src/

    - name: Run mypy
      run: uv run mypy src/ --ignore-missing-imports
```

**Verification:**
- Lint job passes on push
- Same lint results as before migration

**Dependencies:** P1

---

### P3: Migrate test Job to uv + Coverage Enforcement

**Description:** Convert test job to uv, add 85% coverage gate, upload artifact.

**File:** `.github/workflows/ci.yml`

**Changes:**
```yaml
test:
  name: Test
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"

    - name: Install uv
      uses: astral-sh/setup-uv@v3

    - name: Install dependencies
      run: uv sync --all-groups

    - name: Install Playwright browsers
      run: uv run playwright install chromium --with-deps

    - name: Run tests with coverage
      run: |
        uv run pytest tests/unit/ tests/integration/ -v \
          --cov=src/subterminator \
          --cov-report=xml \
          --cov-fail-under=85

    - name: Upload coverage artifact
      uses: actions/upload-artifact@v4
      if: always()
      with:
        name: coverage-report
        path: coverage.xml
```

**Removals:**
- Remove codecov-action step (not needed for MVP)

**Verification:**
- Test job passes with coverage >= 85%
- Test job fails with coverage < 85%
- Coverage artifact uploaded

**Dependencies:** P2

---

### P4: Migrate build Job to uv

**Description:** Convert build job from pip to uv for consistency.

**File:** `.github/workflows/ci.yml`

**Changes:**
```yaml
build:
  name: Build
  runs-on: ubuntu-latest
  needs: [lint, test]
  steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: "3.12"

    - name: Install uv
      uses: astral-sh/setup-uv@v3

    - name: Build package
      run: uv build

    - name: Upload artifacts
      uses: actions/upload-artifact@v4
      with:
        name: dist
        path: dist/
```

**Verification:**
- Build job passes
- dist/ artifact uploaded

**Dependencies:** P3

---

### P5: Add create-pr Job

**Description:** Add new job that creates PR and enables auto-merge.

**File:** `.github/workflows/ci.yml`

**Changes:** Add the following job after `build`:

```yaml
create-pr:
  name: Create PR
  runs-on: ubuntu-latest
  needs: [lint, test, build]
  if: |
    github.event_name == 'push' &&
    (startsWith(github.ref, 'refs/heads/feature/') ||
     startsWith(github.ref, 'refs/heads/fix/'))
  permissions:
    contents: write
    pull-requests: write
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0

    - name: Check for existing PR
      id: check-pr
      env:
        GH_TOKEN: ${{ github.token }}
      run: |
        EXISTING=$(gh pr list --head "${{ github.ref_name }}" --json number --jq '.[0].number // empty')
        if [ -n "$EXISTING" ]; then
          echo "exists=true" >> $GITHUB_OUTPUT
          echo "PR #$EXISTING already exists for this branch"
        else
          echo "exists=false" >> $GITHUB_OUTPUT
        fi

    - name: Verify branch protection
      if: steps.check-pr.outputs.exists == 'false'
      env:
        GH_TOKEN: ${{ github.token }}
      run: |
        PROTECTION=$(gh api repos/${{ github.repository }}/branches/main/protection 2>&1 || true)
        if echo "$PROTECTION" | grep -q "Branch not protected"; then
          echo "::error::Branch protection not configured on main. Auto-merge requires branch protection."
          exit 1
        fi
        echo "Branch protection verified"

    - name: Generate PR content
      if: steps.check-pr.outputs.exists == 'false'
      id: pr-content
      run: |
        TITLE=$(git log -1 --pretty=format:'%s')
        echo "title=$TITLE" >> $GITHUB_OUTPUT

        COMMITS=$(git log origin/main..HEAD --pretty=format:'- %s')

        {
          echo "body<<EOF"
          echo "## Changes"
          echo ""
          echo "$COMMITS"
          echo ""
          echo "## Status"
          echo ""
          echo "- Tests: Passed"
          echo "- Coverage: >= 85%"
          echo ""
          echo "---"
          echo "*Auto-generated PR. Review and approve to merge.*"
          echo "EOF"
        } >> $GITHUB_OUTPUT

    - name: Create PR
      if: steps.check-pr.outputs.exists == 'false'
      id: create-pr
      env:
        GH_TOKEN: ${{ github.token }}
      run: |
        PR_URL=$(gh pr create \
          --title "${{ steps.pr-content.outputs.title }}" \
          --body "${{ steps.pr-content.outputs.body }}" \
          --base main)
        echo "url=$PR_URL" >> $GITHUB_OUTPUT
        echo "Created PR: $PR_URL"

    - name: Enable auto-merge
      if: steps.check-pr.outputs.exists == 'false'
      env:
        GH_TOKEN: ${{ github.token }}
      run: |
        gh pr merge "${{ steps.create-pr.outputs.url }}" \
          --auto \
          --squash \
          --delete-branch
        echo "Auto-merge enabled with squash strategy"
```

**Verification:**
- Job runs only on feature/* and fix/* branches
- Job skips PR creation if PR already exists
- Job fails if branch protection not configured
- PR created with correct title and body
- Auto-merge enabled

**Dependencies:** P4

---

### P6: Manual Verification

**Description:** Test the complete workflow end-to-end.

**Test Cases:**

| Test | Steps | Expected |
|------|-------|----------|
| Happy path | Push to feature/* with passing tests | PR created, auto-merge enabled |
| Failing tests | Introduce test failure | No PR created |
| Low coverage | Comment out tests | Job fails, no PR |
| Existing PR | Push again to same branch | Skips PR creation |
| No protection | Disable branch protection | Fails with error |

**Verification Script:**
```bash
# Create test branch
git checkout -b feature/test-auto-pr-workflow
echo "# Test change" >> README.md
git add README.md
git commit -m "test: verify auto-PR workflow"
git push -u origin feature/test-auto-pr-workflow

# Watch GitHub Actions
# Verify: PR created automatically
# Verify: Auto-merge enabled on PR
```

**Dependencies:** P5

---

### P7: Configure Branch Protection (Manual)

**Description:** Document branch protection setup for repository admin.

**Steps:**
1. Go to repository Settings > Branches
2. Add rule for `main` branch
3. Enable:
   - Require a pull request before merging
   - Require approvals: 1
   - Dismiss stale pull request approvals
   - Require status checks to pass before merging
   - Select status checks: `Lint`, `Test`, `Build`
   - Require branches to be up to date before merging

**Note:** This is a one-time manual setup. The workflow verifies protection is configured before enabling auto-merge.

**Dependencies:** P6 (should work after workflow is deployed)

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| uv migration breaks CI | Test P2-P4 independently, rollback if needed |
| Coverage gate too strict | Current coverage is ~85%, should pass |
| Auto-merge without review | Branch protection verification blocks this |

---

## Rollback Plan

If issues arise after deployment:

1. **Quick rollback:** Remove `create-pr` job, keep uv migration
2. **Full rollback:** Revert entire ci.yml to previous version

```bash
# Quick rollback
git revert HEAD  # Assuming P5 is last commit

# Full rollback
git checkout main~1 -- .github/workflows/ci.yml
git commit -m "revert: rollback CI changes"
```

---

## Success Criteria

- [ ] All existing tests pass in CI
- [ ] Coverage remains >= 85%
- [ ] Push to feature/* auto-creates PR
- [ ] Auto-merge enabled on created PR
- [ ] No duplicate PRs created
- [ ] Branch protection verified before auto-merge

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Claude | Initial plan from design |
