# Security Anti-Patterns Checklist

Reference for P1 Step 3b. Check each workflow file against all 8 patterns below.

## 1. Unpinned Actions (P1-1) [Critical]

**Look for**: `uses:` lines with `@v*` tag references instead of `@{40-char-sha}`
**Example bad**: `uses: actions/checkout@v4`
**Example good**: `uses: actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11`
**Remediation**: Pin to the full commit SHA of the current release tag. Use `gh api repos/{owner}/{repo}/git/ref/tags/{tag} --jq .object.sha` to find it.

## 2. Overly Broad Permissions (P1-2) [Critical]

**Look for**: `permissions: write-all` or missing `permissions:` block at workflow or job level
**Example bad**: `permissions: write-all` or no `permissions:` key at all
**Example good**: `permissions: { contents: read, pull-requests: write }`
**Remediation**: Add explicit least-privilege `permissions:` block scoped to what the workflow actually needs.

## 3. Hardcoded Secrets (P1-3) [Critical]

**Look for**: Known credential patterns in workflow YAML values (not `${{ secrets.* }}` references).
**Regex patterns**:
- AWS access keys: `AKIA[0-9A-Z]{16}`
- GitHub PATs: `ghp_[A-Za-z0-9_]{36}`
- Generic GitHub tokens: `gh[pousr]_[A-Za-z0-9_]{36,}`
**YAML key patterns**: `password:`, `token:`, `api_key:`, `secret:`, `credential:` with inline string values instead of `${{ secrets.* }}`
**Example bad**: `api_key: AKIAIOSFODNN7EXAMPLE`
**Example good**: `api_key: ${{ secrets.AWS_ACCESS_KEY_ID }}`
**Remediation**: Move value to GitHub Secrets and reference via `${{ secrets.SECRET_NAME }}`.

## 4. Secret in Echo (P1-5) [Critical]

**Look for**: `echo ${{ secrets.*` or `echo "${{ secrets.*` in `run:` blocks
**Example bad**: `run: echo ${{ secrets.API_KEY }}`
**Example good**: `run: echo "::add-mask::${{ secrets.API_KEY }}"` (or remove echo entirely)
**Remediation**: Remove echo of secret values. Use the `::add-mask::` workflow command if logging is needed for debugging.

## 5. Pull Request Target Trigger (P1-7) [Warning]

**Look for**: `on: pull_request_target` combined with `actions/checkout` referencing PR head ref
**Example bad**:
```yaml
on: pull_request_target
jobs:
  build:
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.pull_request.head.ref }}
```
**Example good**: Use `on: pull_request` instead, or if `pull_request_target` is needed, pin checkout to merge commit SHA and restrict permissions
**Remediation**: If checkout of PR code is needed with `pull_request_target`, use explicit SHA and restrict permissions.

## 6. Mutable Action References (P1-1 subset) [Warning]

**Look for**: `uses:` lines with `@main`, `@master`, or other branch refs
**Example bad**: `uses: some-org/some-action@main`
**Example good**: `uses: some-org/some-action@a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2`
**Remediation**: Pin to commit SHA instead of branch reference.

## 7. Missing CODEOWNERS (P1-7) [Informational]

**Look for**: Absence of `.github/CODEOWNERS` file, or no entry covering `.github/workflows/`
**Example bad**: No CODEOWNERS file, or CODEOWNERS exists but has no rule for `.github/workflows/`
**Example good**: `.github/CODEOWNERS` contains `/.github/workflows/ @platform-team`
**Remediation**: Add CODEOWNERS with team ownership for workflow files to require review of CI changes.

## 8. Artifact Exposure (P1-7) [Warning]

**Look for**: `actions/upload-artifact` steps that reference directories potentially containing secrets, `.env` files, or credential stores
**Example bad**: `uses: actions/upload-artifact@v4` with `path: .` or `path: $HOME`
**Example good**: `uses: actions/upload-artifact@v4` with `path: ./dist` (specific, non-sensitive directory)
**Remediation**: Review artifact contents. Exclude sensitive files from upload using explicit paths or `.gitignore`-style patterns.
