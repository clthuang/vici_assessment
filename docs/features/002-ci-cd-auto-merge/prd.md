# PRD: CI/CD Auto-Merge Pipeline

**Status:** Brainstorm
**Created:** 2026-02-03
**Author:** Claude (Brainstorm Agent)

---

## Problem Statement

Currently, feature branches require manual intervention to merge after tests pass. Developers must:
1. Wait for CI to complete
2. Manually create a PR
3. Request reviews
4. Manually merge after approval

This creates friction and delays in the development workflow, especially for validated changes that have already passed all quality gates.

## Proposed Solution

Implement an automated CI/CD pipeline that:
1. **Automatically creates PRs** when feature branches pass validation (tests + 85% coverage)
2. **Requires human approval** before merging (not fully automatic)
3. **Auto-merges after approval** when all checks pass

This balances automation efficiency with human oversight for code quality.

---

## User Stories

### US-1: Developer pushes feature branch
**As a** developer
**I want** my feature branch to automatically create a PR when tests pass
**So that** I don't have to manually create PRs for validated code

**Acceptance Criteria:**
- Push to `feature/*` branch triggers CI workflow
- If tests pass AND coverage >= 85%, PR is auto-created
- If tests fail OR coverage < 85%, no PR created, developer notified
- PR title and body are auto-generated from commit history

### US-2: Reviewer approves PR
**As a** reviewer
**I want** approved PRs to auto-merge when all checks pass
**So that** I don't have to manually click merge after approval

**Acceptance Criteria:**
- After PR approval, auto-merge is enabled
- PR merges automatically when all status checks pass
- Squash merge is used by default (configurable)
- Developer is notified when merge completes

### US-3: CI blocks bad code
**As a** team lead
**I want** PRs to be blocked if coverage drops below 85%
**So that** code quality is maintained automatically

**Acceptance Criteria:**
- Coverage check is a required status check
- PRs cannot be merged if coverage < 85%
- Coverage report is posted as PR comment
- Clear error message when coverage check fails

---

## Technical Design

### Architecture

```
Developer Push
      │
      ▼
┌─────────────────┐
│  GitHub Actions │
│   CI Workflow   │
└────────┬────────┘
         │
    ┌────┴────┐
    │ Tests   │
    │ Pass?   │
    └────┬────┘
         │
    ┌────┴────┐
    │Coverage │
    │ >= 85%? │
    └────┬────┘
         │ Yes
         ▼
┌─────────────────┐
│  Create PR      │
│  (gh pr create) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Human Review    │
│ (Required)      │
└────────┬────────┘
         │ Approved
         ▼
┌─────────────────┐
│  Auto-Merge     │
│  (enabled)      │
└─────────────────┘
```

### Key Components

#### 1. CI Workflow (`.github/workflows/ci.yml`)

```yaml
name: CI

on:
  push:
    branches: [feature/*, fix/*]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install uv
        uses: astral-sh/setup-uv@v3

      - name: Install dependencies
        run: uv sync --all-groups

      - name: Run tests with coverage
        run: |
          uv run pytest tests/ --ignore=tests/e2e/ \
            --cov=subterminator \
            --cov-report=xml \
            --cov-fail-under=85

      - name: Upload coverage report
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage.xml

  create-pr:
    needs: test
    if: github.event_name == 'push' && (startsWith(github.ref, 'refs/heads/feature/') || startsWith(github.ref, 'refs/heads/fix/'))
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Check if PR exists
        id: check-pr
        run: |
          PR_EXISTS=$(gh pr list --head "${{ github.ref_name }}" --json number --jq length)
          echo "exists=$PR_EXISTS" >> $GITHUB_OUTPUT
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Create PR
        if: steps.check-pr.outputs.exists == '0'
        run: |
          gh pr create \
            --title "$(git log -1 --format='%s')" \
            --body "$(cat <<EOF
          ## Summary
          Auto-generated PR for branch: ${{ github.ref_name }}

          ## Commits
          $(git log origin/main..HEAD --oneline)

          ## Test Results
          - All tests passing
          - Coverage >= 85%

          ---
          *Auto-created by CI workflow*
          EOF
          )" \
            --base main
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Enable auto-merge
        run: gh pr merge --auto --squash
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

#### 2. Branch Protection Rules

Configure via GitHub Settings or API:

```json
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["test"]
  },
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true
  },
  "enforce_admins": true,
  "restrictions": null
}
```

#### 3. Coverage Comment Action (Optional Enhancement)

```yaml
- name: Post coverage comment
  uses: MishaKav/pytest-coverage-comment@main
  with:
    pytest-coverage-path: coverage.xml
    junitxml-path: pytest.xml
```

### Security Considerations

1. **Use `GITHUB_TOKEN`** - Built-in token with minimal permissions
2. **Branch protection** - Prevent direct pushes to main
3. **Required reviews** - Human must approve before merge
4. **No force push** - Prevent history rewriting on protected branches
5. **Status checks required** - Cannot bypass failing tests

### Limitations

- PRs created with `GITHUB_TOKEN` won't trigger other workflows (GitHub security feature)
- If additional workflows needed on merge, use a PAT (with security implications)

---

## Dependencies

### GitHub Actions Used

| Action | Purpose | Source |
|--------|---------|--------|
| `actions/checkout@v4` | Clone repository | GitHub Official |
| `actions/setup-python@v5` | Install Python | GitHub Official |
| `astral-sh/setup-uv@v3` | Install uv package manager | Astral |
| `MishaKav/pytest-coverage-comment` | Post coverage to PR | Community |

### Branch Protection Requirements (CRITICAL PREREQUISITE)

> **WARNING:** Auto-merge relies on branch protection rules. If branch protection is not configured, PRs may merge immediately without human review.

**Manual Setup Required Before Using This Workflow:**

1. Go to **Settings > Branches > Add rule**
2. Branch name pattern: `main`
3. Enable:
   - [x] Require a pull request before merging
   - [x] Require approvals: 1
   - [x] Dismiss stale pull request approvals when new commits are pushed
   - [x] Require status checks to pass before merging
   - [x] Require branches to be up to date before merging
   - [x] Status checks: `test` (from this workflow)
4. Save changes

**How Auto-Merge Works (Clarification):**
- `gh pr merge --auto --squash` **enables** auto-merge, it does not merge immediately
- The PR will only merge AFTER:
  1. All required status checks pass (test job)
  2. Required number of approvals received (branch protection)
- If branch protection is not configured, the PR may merge immediately (unsafe!)

---

## Setup Verification

Add this check to verify branch protection before enabling auto-merge:

```yaml
      - name: Verify branch protection exists
        run: |
          PROTECTION=$(gh api repos/${{ github.repository }}/branches/main/protection 2>/dev/null || echo "none")
          if [ "$PROTECTION" = "none" ]; then
            echo "::error::Branch protection not configured on main. Auto-merge disabled for safety."
            exit 1
          fi
          echo "Branch protection verified."
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Enable auto-merge
        run: gh pr merge --auto --squash
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| PR creation | Manual | Automated |
| Coverage enforcement | Manual review | Automated gate |
| Merge after approval | Manual click | Automatic |

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Auto-PR spam | Medium | Only create PR on first push, check if exists |
| False positive tests | High | Require human review before merge |
| Coverage gaming | Medium | Review actual test quality in PR |
| Workflow failures | Low | Notifications on failure, manual fallback |

---

## Decisions (Resolved from Open Questions)

1. **Auto-merge:** Always enabled for feature/* branches that pass tests. (Can revisit if noisy)
2. **Merge strategy:** Squash merge for cleaner history.
3. **Branch deletion:** Auto-delete after merge (add `delete-branch: true` to gh pr merge).
4. **Merge conflicts:**
   - Auto-merge is automatically disabled when conflicts exist
   - Developer must manually rebase and push
   - After successful rebase, auto-merge re-enables automatically
   - No notification needed - developer sees conflict in GitHub UI
5. **fix/* branches:** Treated same as feature/* - added to PR creation condition.

## Open Questions (Remaining)

1. Should coverage report be posted as PR comment? (nice-to-have, adds complexity)

---

## References

- [pascalgn/automerge-action](https://github.com/pascalgn/automerge-action)
- [peter-evans/enable-pull-request-automerge](https://github.com/peter-evans/enable-pull-request-automerge)
- [GitHub Branch Protection Docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
- [pytest-coverage-comment](https://github.com/marketplace/actions/pytest-coverage-comment)
- [GitHub Actions CI/CD Best Practices](https://github.com/github/awesome-copilot/blob/main/instructions/github-actions-ci-cd-best-practices.instructions.md)
