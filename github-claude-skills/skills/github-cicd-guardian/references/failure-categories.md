# Failure Categories

Reference for P0 Step 4 (categorization). Match log output against these patterns.

## 1. Dependency Issue

**Log signatures**: `ModuleNotFoundError`, `package not found`, `cannot resolve`, `No matching version`, `Could not find a version that satisfies`
**Example**: `ModuleNotFoundError: No module named 'foo'`
**Typical cause**: Missing or incorrect dependency in requirements/package config.

## 2. YAML Misconfiguration

**Log signatures**: `unexpected value`, `mapping values are not allowed`, `workflow is not valid`, `Invalid workflow file`
**Example**: `Error: .github/workflows/ci.yml: unexpected value`
**Typical cause**: Syntax error in workflow YAML (bad indentation, wrong key, missing colon).

## 3. Code Bug

**Log signatures**: `FAIL`, `AssertionError`, `Error:`, `FAILED`, `TypeError`, `ValueError`, `test failure`
**Example**: `FAIL test_order_placement ... AssertionError: expected 200 but got 500`
**Typical cause**: Application code defect surfaced by a test.

## 4. Flaky Test

**Log signatures**: `exit code 143`, intermittent pass/fail on same commit, `timeout`, `SIGTERM`
**Example**: `Error: Process completed with exit code 143`
**Typical cause**: Test timeout, race condition, or non-deterministic behavior. Same commit passes on retry.

## 5. Infrastructure

**Log signatures**: `No space left on device`, `runner is offline`, `unable to start`, `ENOMEM`, `disk quota exceeded`
**Example**: `No space left on device`
**Typical cause**: Runner resource exhaustion, GitHub infrastructure issue, or self-hosted runner problem.

## 6. Permissions

**Log signatures**: `Resource not accessible by integration`, `403`, `insufficient permissions`, `Permission denied`, `RequestError [HttpError]: Not Found`
**Example**: `Resource not accessible by integration`
**Typical cause**: GitHub token missing required scope, or workflow `permissions:` block too restrictive.
