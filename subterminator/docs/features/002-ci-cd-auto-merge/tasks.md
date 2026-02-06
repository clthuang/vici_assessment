# CI/CD Auto-Merge Pipeline - Tasks

**Feature:** 002-ci-cd-auto-merge
**Date:** February 3, 2026

---

## Task Overview

| ID | Task | Status | Blocked By |
|----|------|--------|------------|
| T1 | Add fix/* to push triggers | pending | - |
| T2 | Migrate lint job to uv | pending | T1 |
| T3 | Migrate test job to uv | pending | T2 |
| T4 | Add coverage enforcement | pending | T3 |
| T5 | Migrate build job to uv | pending | T4 |
| T6 | Add create-pr job skeleton | pending | T5 |
| T7 | Add check-existing-PR step | pending | T6 |
| T8 | Add branch protection verification | pending | T7 |
| T9 | Add PR content generation | pending | T8 |
| T10 | Add PR creation step | pending | T9 |
| T11 | Add auto-merge step | pending | T10 |
| T12 | Commit and push workflow | pending | T11 |
| T13 | Verify workflow runs | pending | T12 |

---

## Tasks

### T1: Add fix/* to Push Triggers

**Plan Reference:** P1

**Description:** Add `fix/*` branch pattern to the workflow's push trigger.

**File:** `.github/workflows/ci.yml`

**Changes:**
```yaml
# Line ~5-6
on:
  push:
    branches: [main, feature/*, fix/*]  # Add fix/*
```

**Acceptance Criteria:**
- [ ] YAML syntax valid (`python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"`)
- [ ] `fix/*` added to branches list

---

### T2: Migrate lint Job to uv

**Plan Reference:** P2

**Description:** Convert lint job from pip to uv package manager.

**File:** `.github/workflows/ci.yml`

**Changes:**
Replace the entire `lint` job with:
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

**Acceptance Criteria:**
- [ ] Python version changed to 3.12
- [ ] `astral-sh/setup-uv@v3` action added
- [ ] `uv sync --all-groups` replaces pip install
- [ ] `uv run` prefix added to ruff and mypy commands
- [ ] YAML syntax valid

---

### T3: Migrate test Job to uv

**Plan Reference:** P3 (part 1)

**Description:** Convert test job from pip to uv package manager.

**File:** `.github/workflows/ci.yml`

**Changes:**
Update `test` job steps 1-5:
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
```

**Acceptance Criteria:**
- [ ] Python version changed to 3.12
- [ ] `astral-sh/setup-uv@v3` action added
- [ ] `uv sync --all-groups` replaces pip install
- [ ] `uv run` prefix added to playwright command
- [ ] YAML syntax valid

---

### T4: Add Coverage Enforcement

**Plan Reference:** P3 (part 2)

**Description:** Add 85% coverage gate and upload coverage artifact.

**File:** `.github/workflows/ci.yml`

**Changes:**
Update test job's test and coverage steps:
```yaml
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
- Remove `codecov/codecov-action@v4` step and its env block

**Acceptance Criteria:**
- [ ] `--cov-fail-under=85` added to pytest command
- [ ] `uv run` prefix added to pytest
- [ ] `actions/upload-artifact@v4` replaces codecov action
- [ ] `if: always()` ensures upload even on failure
- [ ] codecov step removed
- [ ] YAML syntax valid

---

### T5: Migrate build Job to uv

**Plan Reference:** P4

**Description:** Convert build job from pip to uv.

**File:** `.github/workflows/ci.yml`

**Changes:**
Replace the entire `build` job with:
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

**Acceptance Criteria:**
- [ ] Python version changed to 3.12
- [ ] `astral-sh/setup-uv@v3` action added
- [ ] `uv build` replaces `python -m build`
- [ ] `pip install build` removed
- [ ] YAML syntax valid

---

### T6: Add create-pr Job Skeleton

**Plan Reference:** P5 (part 1)

**Description:** Add the new create-pr job with basic structure.

**File:** `.github/workflows/ci.yml`

**Changes:**
Add after the `build` job:
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
```

**Acceptance Criteria:**
- [ ] Job name is `create-pr`
- [ ] `needs: [lint, test, build]` specified
- [ ] `if` condition filters feature/* and fix/* branches
- [ ] `permissions` block with contents and pull-requests write
- [ ] `fetch-depth: 0` for full git history
- [ ] YAML syntax valid

---

### T7: Add Check-Existing-PR Step

**Plan Reference:** P5 (part 2)

**Description:** Add step to check if PR already exists.

**File:** `.github/workflows/ci.yml`

**Changes:**
Add step to `create-pr` job:
```yaml
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
```

**Acceptance Criteria:**
- [ ] Step id is `check-pr`
- [ ] Uses `GH_TOKEN` environment variable
- [ ] Outputs `exists=true` or `exists=false`
- [ ] YAML syntax valid

---

### T8: Add Branch Protection Verification

**Plan Reference:** P5 (part 3)

**Description:** Add step to verify branch protection before PR creation.

**File:** `.github/workflows/ci.yml`

**Changes:**
Add step to `create-pr` job:
```yaml
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
```

**Acceptance Criteria:**
- [ ] Step skipped if PR exists (`if` condition)
- [ ] Checks GitHub API for branch protection
- [ ] Fails with clear error if not protected
- [ ] YAML syntax valid

---

### T9: Add PR Content Generation

**Plan Reference:** P5 (part 4)

**Description:** Add step to generate PR title and body.

**File:** `.github/workflows/ci.yml`

**Changes:**
Add step to `create-pr` job:
```yaml
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
```

**Acceptance Criteria:**
- [ ] Step id is `pr-content`
- [ ] Outputs `title` from last commit message
- [ ] Outputs `body` with commit list and status
- [ ] Uses EOF delimiter for multiline output
- [ ] YAML syntax valid

---

### T10: Add PR Creation Step

**Plan Reference:** P5 (part 5)

**Description:** Add step to create the PR using gh CLI.

**File:** `.github/workflows/ci.yml`

**Changes:**
Add step to `create-pr` job:
```yaml
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
```

**Acceptance Criteria:**
- [ ] Step id is `create-pr`
- [ ] Uses outputs from `pr-content` step
- [ ] `--base main` specified
- [ ] Outputs `url` for next step
- [ ] YAML syntax valid

---

### T11: Add Auto-Merge Step

**Plan Reference:** P5 (part 6)

**Description:** Add step to enable auto-merge with squash strategy.

**File:** `.github/workflows/ci.yml`

**Changes:**
Add step to `create-pr` job:
```yaml
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

**Acceptance Criteria:**
- [ ] Uses `--auto` flag for auto-merge
- [ ] Uses `--squash` for squash merge strategy
- [ ] Uses `--delete-branch` for cleanup
- [ ] YAML syntax valid

---

### T12: Commit and Push Workflow

**Plan Reference:** P5 completion

**Description:** Commit all workflow changes and push to trigger CI.

**Commands:**
```bash
git add .github/workflows/ci.yml
git commit -m "feat(002): implement CI/CD auto-merge pipeline

- Migrate lint, test, build jobs to uv
- Add 85% coverage enforcement
- Add create-pr job with auto-merge

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
git push
```

**Acceptance Criteria:**
- [ ] All changes committed
- [ ] Pushed to remote
- [ ] CI workflow triggered

---

### T13: Verify Workflow Runs

**Plan Reference:** P6

**Description:** Verify the workflow runs correctly on the current branch.

**Steps:**
1. Check GitHub Actions tab for workflow run
2. Verify all jobs pass (lint, test, build)
3. Verify create-pr job runs
4. Check if PR was created (or error if no branch protection)

**Acceptance Criteria:**
- [ ] Workflow triggered on push
- [ ] lint job passes
- [ ] test job passes with >= 85% coverage
- [ ] build job passes
- [ ] create-pr job runs (may fail if no branch protection - expected)

---

## Notes

- **Branch protection (P7)** is an external manual setup, not a code task
- Tasks T6-T11 can be combined into a single commit if preferred
- If any task fails, check the YAML syntax first
