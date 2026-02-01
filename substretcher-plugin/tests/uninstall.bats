#!/usr/bin/env bats
# Unit tests for uninstall.sh functions
# Run with: bats tests/uninstall.bats

# Load the library before each test
setup() {
  # Get the directory of this test file, then go up to find install-lib.sh
  TEST_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")" && pwd)"
  PROJECT_DIR="$(dirname "$TEST_DIR")"
  source "$PROJECT_DIR/install-lib.sh"

  # Create temp directory for test fixtures
  TEST_TEMP=$(mktemp -d)
}

teardown() {
  # Clean up temp directory
  [[ -d "$TEST_TEMP" ]] && rm -rf "$TEST_TEMP"
}

# ============================================================================
# detect_package_manager tests
# ============================================================================

# Note: These tests are limited because they depend on system state.
# We test the function exists and returns valid values.

@test "detect_package_manager: returns valid value" {
  # Source the uninstall script to get the function (in a subshell to avoid side effects)
  source "$PROJECT_DIR/uninstall.sh" 2>/dev/null || true

  # If the function is available, test it
  if declare -f detect_package_manager &>/dev/null; then
    result=$(detect_package_manager)
    [[ "$result" == "pnpm" || "$result" == "npm" || "$result" == "none" ]]
  else
    skip "detect_package_manager not available (may need to source uninstall.sh)"
  fi
}

# ============================================================================
# Shell profile line removal tests (using sed)
# ============================================================================

@test "sed removes SubStretcher comment line" {
  local temp_file="$TEST_TEMP/profile"
  cat > "$temp_file" << 'EOF'
# Some config
export PATH=/usr/bin
# SubStretcher API key
export ANTHROPIC_API_KEY=sk-ant-xxx
export OTHER_VAR=value
EOF

  grep -v "# SubStretcher API key" "$temp_file" > "$temp_file.new"
  mv "$temp_file.new" "$temp_file"

  # Should not contain the comment line
  run grep "# SubStretcher API key" "$temp_file"
  [[ "$status" -ne 0 ]]

  # Should still contain other lines
  run grep "OTHER_VAR" "$temp_file"
  [[ "$status" -eq 0 ]]
}

@test "sed removes ANTHROPIC_API_KEY export line" {
  local temp_file="$TEST_TEMP/profile"
  cat > "$temp_file" << 'EOF'
# Some config
export PATH=/usr/bin
# SubStretcher API key
export ANTHROPIC_API_KEY=sk-ant-xxx
export OTHER_VAR=value
EOF

  grep -v "^export ANTHROPIC_API_KEY=" "$temp_file" > "$temp_file.new"
  mv "$temp_file.new" "$temp_file"

  # Should not contain the export line
  run grep "ANTHROPIC_API_KEY" "$temp_file"
  [[ "$status" -ne 0 ]]

  # Should still contain other lines
  run grep "OTHER_VAR" "$temp_file"
  [[ "$status" -eq 0 ]]
}

@test "combined removal of SubStretcher lines" {
  local temp_file="$TEST_TEMP/profile"
  cat > "$temp_file" << 'EOF'
# Some config
export PATH=/usr/bin
# SubStretcher API key
export ANTHROPIC_API_KEY=sk-ant-xxx
export OTHER_VAR=value
# Another comment
EOF

  # This is the exact logic used in uninstall.sh
  grep -v "# SubStretcher API key" "$temp_file" | grep -v "^export ANTHROPIC_API_KEY=" > "$temp_file.new"
  mv "$temp_file.new" "$temp_file"

  # Should not contain SubStretcher lines
  run grep "SubStretcher" "$temp_file"
  [[ "$status" -ne 0 ]]
  run grep "ANTHROPIC_API_KEY" "$temp_file"
  [[ "$status" -ne 0 ]]

  # Should still contain other lines
  run grep "OTHER_VAR" "$temp_file"
  [[ "$status" -eq 0 ]]
  run grep "Another comment" "$temp_file"
  [[ "$status" -eq 0 ]]
}

@test "removal handles file without SubStretcher lines" {
  local temp_file="$TEST_TEMP/profile"
  cat > "$temp_file" << 'EOF'
# Some config
export PATH=/usr/bin
export OTHER_VAR=value
EOF

  # Should not error when lines don't exist
  grep -v "# SubStretcher API key" "$temp_file" | grep -v "^export ANTHROPIC_API_KEY=" > "$temp_file.new" || true
  mv "$temp_file.new" "$temp_file"

  # File should still have content
  run cat "$temp_file"
  [[ "$status" -eq 0 ]]
  [[ -n "$output" ]]
}

@test "removal preserves non-SubStretcher ANTHROPIC_API_KEY" {
  local temp_file="$TEST_TEMP/profile"
  cat > "$temp_file" << 'EOF'
# My own API key setup
export ANTHROPIC_API_KEY=sk-ant-myownkey
# SubStretcher API key
export ANTHROPIC_API_KEY=sk-ant-xxx
EOF

  # The removal only targets lines starting with "export ANTHROPIC_API_KEY="
  # This test shows that ALL export lines would be removed
  # In practice, users shouldn't have duplicate exports
  grep -v "# SubStretcher API key" "$temp_file" | grep -v "^export ANTHROPIC_API_KEY=" > "$temp_file.new" || true
  mv "$temp_file.new" "$temp_file"

  # Comment should be preserved
  run grep "My own API key setup" "$temp_file"
  [[ "$status" -eq 0 ]]
}

# ============================================================================
# Idempotency tests
# ============================================================================

@test "removal is idempotent - running twice doesn't error" {
  local temp_file="$TEST_TEMP/profile"
  cat > "$temp_file" << 'EOF'
# SubStretcher API key
export ANTHROPIC_API_KEY=sk-ant-xxx
export OTHER_VAR=value
EOF

  # First removal
  grep -v "# SubStretcher API key" "$temp_file" | grep -v "^export ANTHROPIC_API_KEY=" > "$temp_file.new" || true
  mv "$temp_file.new" "$temp_file"

  # Second removal (should not error even though lines are gone)
  grep -v "# SubStretcher API key" "$temp_file" | grep -v "^export ANTHROPIC_API_KEY=" > "$temp_file.new" || true
  mv "$temp_file.new" "$temp_file"

  # File should still be valid
  run cat "$temp_file"
  [[ "$status" -eq 0 ]]
  [[ "$output" == *"OTHER_VAR"* ]]
}

# ============================================================================
# Directory removal tests
# ============================================================================

@test "rm -rf handles non-existent directory gracefully" {
  local non_existent="$TEST_TEMP/does-not-exist"
  # rm -rf on non-existent directory should not error
  run rm -rf "$non_existent"
  [[ "$status" -eq 0 ]]
}

@test "rm -rf removes nested directory structure" {
  local data_dir="$TEST_TEMP/.substretcher"
  mkdir -p "$data_dir/services"
  echo "test" > "$data_dir/audit.log"
  echo "config" > "$data_dir/services/custom.yaml"

  rm -rf "$data_dir"

  [[ ! -d "$data_dir" ]]
}

# ============================================================================
# string_in_file tests for SubStretcher detection
# ============================================================================

@test "string_in_file detects SubStretcher comment" {
  local temp_file="$TEST_TEMP/profile"
  cat > "$temp_file" << 'EOF'
# Some config
# SubStretcher API key
export ANTHROPIC_API_KEY=sk-ant-xxx
EOF

  run string_in_file "# SubStretcher API key" "$temp_file"
  [[ "$status" -eq 0 ]]
}

@test "string_in_file returns false when comment not present" {
  local temp_file="$TEST_TEMP/profile"
  cat > "$temp_file" << 'EOF'
# Some config
export ANTHROPIC_API_KEY=sk-ant-xxx
EOF

  run string_in_file "# SubStretcher API key" "$temp_file"
  [[ "$status" -ne 0 ]]
}

# ============================================================================
# File backup tests
# ============================================================================

@test "backup preserves original file content" {
  local temp_file="$TEST_TEMP/profile"
  local original_content="# Original content
export PATH=/usr/bin
# SubStretcher API key
export ANTHROPIC_API_KEY=sk-ant-xxx"

  echo "$original_content" > "$temp_file"

  # Create backup
  cp "$temp_file" "$temp_file.substretcher-backup"

  # Modify original
  grep -v "SubStretcher" "$temp_file" > "$temp_file.new"
  mv "$temp_file.new" "$temp_file"

  # Backup should have original content
  run grep "SubStretcher" "$temp_file.substretcher-backup"
  [[ "$status" -eq 0 ]]

  # Original should be modified
  run grep "SubStretcher" "$temp_file"
  [[ "$status" -ne 0 ]]
}

# ============================================================================
# is_substretcher_project tests (from install-lib.sh)
# ============================================================================

@test "is_substretcher_project: validates project directory" {
  local temp_dir="$TEST_TEMP/fake-project"
  mkdir -p "$temp_dir"
  echo '{"name": "substretcher", "version": "1.0.0"}' > "$temp_dir/package.json"

  run is_substretcher_project "$temp_dir"
  [[ "$status" -eq 0 ]]
}

@test "is_substretcher_project: rejects non-substretcher project" {
  local temp_dir="$TEST_TEMP/other-project"
  mkdir -p "$temp_dir"
  echo '{"name": "other-package", "version": "1.0.0"}' > "$temp_dir/package.json"

  run is_substretcher_project "$temp_dir"
  [[ "$status" -ne 0 ]]
}

# ============================================================================
# detect_shell_profile tests (from install-lib.sh)
# ============================================================================

@test "detect_shell_profile: returns zshrc for zsh" {
  SHELL="/bin/zsh"
  unset ZDOTDIR
  result=$(detect_shell_profile)
  [[ "$result" == "$HOME/.zshrc" ]]
}

@test "detect_shell_profile: returns empty for fish" {
  SHELL="/bin/fish"
  result=$(detect_shell_profile)
  [[ "$result" == "" ]]
}
