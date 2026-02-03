# CI/CD Auto-Merge Pipeline - Technical Design

**Feature:** 002-ci-cd-auto-merge
**Version:** 1.0
**Date:** February 3, 2026
**Status:** Draft

---

## 1. Architecture Overview

### 1.1 System Context

```
┌──────────────────────────────────────────────────────────────┐
│                    GitHub Repository                          │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  Developer Push                                               │
│       │                                                       │
│       ▼                                                       │
│  ┌─────────────────────────────────────────────────────┐     │
│  │              .github/workflows/ci.yml                │     │
│  ├─────────────────────────────────────────────────────┤     │
│  │                                                      │     │
│  │  ┌───────┐    ┌──────┐    ┌───────┐                │     │
│  │  │ lint  │    │ test │    │ build │                │     │
│  │  └───┬───┘    └──┬───┘    └───┬───┘                │     │
│  │      │           │            │                     │     │
│  │      └─────┬─────┘            │                     │     │
│  │            │ (test must pass) │                     │     │
│  │            ▼                  │                     │     │
│  │      ┌───────────┐            │                     │     │
│  │      │ create-pr │◄───────────┘                     │     │
│  │      └─────┬─────┘   (needs: lint, test, build)    │     │
│  │            │                                        │     │
│  └────────────│────────────────────────────────────────┘     │
│               │                                               │
│               ▼                                               │
│  ┌─────────────────────────────────────────────────────┐     │
│  │           Branch Protection Rules (External)         │     │
│  │  • Require 1+ approval                               │     │
│  │  • Require status checks (lint, test, build)         │     │
│  │  • Require branch up-to-date                         │     │
│  └─────────────────────────────────────────────────────┘     │
│               │                                               │
│               ▼ (after approval)                              │
│         Auto-merge executes                                   │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 1.2 Design Principles

| Principle | Application |
|-----------|-------------|
| **Safety First** | Branch protection verification before auto-merge |
| **Minimal Permissions** | Use only GITHUB_TOKEN, no PATs |
| **Fail Fast** | Coverage gate blocks PR creation early |
| **Idempotent** | Skip PR creation if already exists |
| **Single Responsibility** | Each job has one purpose |

---

## 2. Component Design

### 2.1 Workflow Structure

The CI workflow will be modified to add a `create-pr` job. Here's the target structure:

```yaml
name: CI

on:
  push:
    branches: [main, feature/*, fix/*]
  pull_request:
    branches: [main]

jobs:
  lint:
    # Existing - no changes

  test:
    # Modified - add coverage enforcement

  build:
    # Existing - no changes

  create-pr:  # NEW JOB
    # Creates PR and enables auto-merge
```

### 2.2 Job: test (Modified)

**Changes Required:**
- Add `--cov-fail-under=85` to enforce coverage minimum
- Upload coverage.xml as artifact for visibility

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

### 2.3 Job: create-pr (New)

**Responsibilities:**
1. Check if PR already exists (skip if so)
2. Verify branch protection is configured
3. Create PR with generated title and body
4. Enable auto-merge with squash strategy

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
        fetch-depth: 0  # Need full history for commit list

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
        # Get the last commit message for title
        TITLE=$(git log -1 --pretty=format:'%s')
        echo "title=$TITLE" >> $GITHUB_OUTPUT

        # Generate body with commit list
        BODY=$(cat <<'BODY_EOF'
        ## Changes

        $(git log origin/main..HEAD --pretty=format:'- %s')

        ## Status

        - Tests: Passed
        - Coverage: >= 85%

        ---
        *Auto-generated PR. Review and approve to merge.*
        BODY_EOF
        )

        # Use delimiter for multiline output
        echo "body<<EOF" >> $GITHUB_OUTPUT
        echo "$BODY" >> $GITHUB_OUTPUT
        echo "EOF" >> $GITHUB_OUTPUT

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

---

## 3. Interface Contracts

### 3.1 Job Dependencies

```
lint ───────┐
            │
test ───────┼──► create-pr
            │
build ──────┘
```

| Dependency | Purpose |
|------------|---------|
| `needs: [lint, test, build]` | Ensures all quality gates pass before PR |
| `if: github.event_name == 'push'` | Only on direct push, not PR events |
| `if: startsWith(...)` | Only for feature/* and fix/* branches |

### 3.2 GitHub API Interactions

| API Call | Purpose | Permissions |
|----------|---------|-------------|
| `gh pr list` | Check for existing PR | `pull-requests: read` |
| `gh api .../protection` | Verify branch protection | `contents: read` |
| `gh pr create` | Create new PR | `pull-requests: write` |
| `gh pr merge --auto` | Enable auto-merge | `contents: write` |

### 3.3 Environment Variables

| Variable | Source | Purpose |
|----------|--------|---------|
| `GH_TOKEN` | `${{ github.token }}` | GitHub CLI authentication |
| `GITHUB_REF_NAME` | Built-in | Current branch name |
| `GITHUB_REPOSITORY` | Built-in | Owner/repo for API calls |

---

## 4. Error Handling

### 4.1 Error Scenarios

| Scenario | Detection | Response |
|----------|-----------|----------|
| Tests fail | Job fails | `create-pr` not triggered (needs dependency) |
| Coverage < 85% | `--cov-fail-under=85` exits non-zero | Job fails, no PR |
| PR already exists | `gh pr list` returns PR number | Skip PR creation, exit 0 |
| Branch protection missing | API returns "Branch not protected" | Fail with clear error |
| API rate limit | gh CLI handles with backoff | Automatic retry |
| Merge conflict | Auto-merge fails | PR stays open, developer must rebase |

### 4.2 Error Messages

```
Error: Branch protection not configured on main. Auto-merge requires branch protection.

To fix:
1. Go to Settings > Branches > Branch protection rules
2. Add rule for 'main' branch
3. Enable: Require pull request, Required approvals (1+), Required status checks
4. Re-run this workflow
```

---

## 5. Security Considerations

### 5.1 Permission Model

```yaml
permissions:
  contents: write      # For creating commits (squash merge)
  pull-requests: write # For creating and managing PRs
```

**Principle of Least Privilege:**
- No `secrets` access beyond GITHUB_TOKEN
- No PAT required
- Permissions scoped to job level

### 5.2 GITHUB_TOKEN Limitations

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| Cannot trigger other workflows | Auto-merge won't trigger post-merge workflows | Acceptable for MVP |
| 1000 API calls/hour | Rate limit for large repos | Unlikely to hit with this workflow |
| Cannot bypass branch protection | Good - enforces human review | By design |

### 5.3 Safety Guards

| Guard | Implementation |
|-------|----------------|
| Human review required | Branch protection rule (external) |
| Tests must pass | `needs: [lint, test, build]` |
| Coverage minimum | `--cov-fail-under=85` |
| No force push | Default branch protection |
| Squash merge only | `--squash` flag |

---

## 6. Migration Path

### 6.1 Changes to Existing ci.yml

| Section | Change Type | Description |
|---------|-------------|-------------|
| `on.push.branches` | Modify | Add `fix/*` pattern |
| `test` job | Modify | Add coverage enforcement, uv migration |
| `create-pr` job | Add | New job for PR automation |

### 6.2 No Breaking Changes

- Existing `lint`, `build` jobs unchanged in behavior
- `test` job adds enforcement but same test execution
- New job only activates on feature/fix branches

### 6.3 Rollback Plan

If issues arise:
1. Remove `create-pr` job from ci.yml
2. Remove `--cov-fail-under=85` from test job
3. Revert to manual PR creation

---

## 7. Testing Strategy

### 7.1 Manual Verification

| Test | Steps | Expected Result |
|------|-------|-----------------|
| Happy path | Push to feature/* with passing tests | PR created, auto-merge enabled |
| Failing tests | Push with test failure | No PR created |
| Low coverage | Push with <85% coverage | Job fails, no PR |
| Existing PR | Push to branch with open PR | Skips PR creation |
| No branch protection | Remove protection, push | Fails with clear error |

### 7.2 Test Branch Strategy

```bash
# Create test branch
git checkout -b feature/test-auto-pr

# Make changes that pass tests
echo "# Test" >> README.md
git add README.md
git commit -m "test: verify auto-PR workflow"
git push -u origin feature/test-auto-pr

# Observe: PR should be created automatically
```

---

## 8. Dependencies

### 8.1 GitHub Actions

| Action | Version | Purpose |
|--------|---------|---------|
| `actions/checkout` | v4 | Clone repository |
| `actions/setup-python` | v5 | Install Python 3.12 |
| `astral-sh/setup-uv` | v3 | Install uv package manager |
| `actions/upload-artifact` | v4 | Upload coverage report |

### 8.2 External Requirements

| Requirement | Status | Notes |
|-------------|--------|-------|
| Branch protection on main | Manual setup | Must be configured before use |
| Repository write access | Default for GITHUB_TOKEN | No additional setup |
| gh CLI | Pre-installed on runners | No additional setup |

---

## 9. Open Decisions

| Decision | Options | Recommendation |
|----------|---------|----------------|
| Coverage report in PR | Post as comment vs artifact only | Artifact only (MVP) |
| PR description format | Simple vs detailed | Simple with commit list |
| Merge strategy | Squash vs merge commit | Squash (cleaner history) |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-03 | Claude | Initial design from spec |
