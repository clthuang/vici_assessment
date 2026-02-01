#!/usr/bin/env bats
# Unit tests for install-lib.sh
# Run with: bats tests/install.bats

# Load the library before each test
setup() {
  # Get the directory of this test file, then go up to find install-lib.sh
  TEST_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")" && pwd)"
  PROJECT_DIR="$(dirname "$TEST_DIR")"
  source "$PROJECT_DIR/install-lib.sh"
}

# ============================================================================
# parse_node_version tests
# ============================================================================

@test "parse_node_version: extracts major from v18.17.0" {
  result=$(parse_node_version "v18.17.0")
  [[ "$result" == "18" ]]
}

@test "parse_node_version: extracts major from 20.10.0 (no v prefix)" {
  result=$(parse_node_version "20.10.0")
  [[ "$result" == "20" ]]
}

@test "parse_node_version: handles single digit version" {
  result=$(parse_node_version "v8.0.0")
  [[ "$result" == "8" ]]
}

@test "parse_node_version: handles v22.1.0" {
  result=$(parse_node_version "v22.1.0")
  [[ "$result" == "22" ]]
}

# ============================================================================
# version_gte tests
# ============================================================================

@test "version_gte: 18 >= 18 is true" {
  run version_gte 18 18
  [[ "$status" -eq 0 ]]
}

@test "version_gte: 20 >= 18 is true" {
  run version_gte 20 18
  [[ "$status" -eq 0 ]]
}

@test "version_gte: 16 >= 18 is false" {
  run version_gte 16 18
  [[ "$status" -ne 0 ]]
}

@test "version_gte: 22 >= 18 is true" {
  run version_gte 22 18
  [[ "$status" -eq 0 ]]
}

@test "version_gte: 10 >= 18 is false" {
  run version_gte 10 18
  [[ "$status" -ne 0 ]]
}

# ============================================================================
# trim tests
# ============================================================================

@test "trim: removes leading whitespace" {
  result=$(trim "  hello")
  [[ "$result" == "hello" ]]
}

@test "trim: removes trailing whitespace" {
  result=$(trim "hello  ")
  [[ "$result" == "hello" ]]
}

@test "trim: removes both leading and trailing whitespace" {
  result=$(trim "  hello world  ")
  [[ "$result" == "hello world" ]]
}

@test "trim: handles empty string" {
  result=$(trim "")
  [[ "$result" == "" ]]
}

@test "trim: handles string with only whitespace" {
  result=$(trim "   ")
  [[ "$result" == "" ]]
}

@test "trim: preserves internal whitespace" {
  result=$(trim "  hello   world  ")
  [[ "$result" == "hello   world" ]]
}

@test "trim: handles tabs" {
  result=$(trim "	hello	")
  [[ "$result" == "hello" ]]
}

# ============================================================================
# validate_api_key tests
# ============================================================================

@test "validate_api_key: accepts valid key with sk-ant- prefix" {
  run validate_api_key "sk-ant-api03-xxxxx"
  [[ "$status" -eq 0 ]]
}

@test "validate_api_key: accepts another valid key format" {
  run validate_api_key "sk-ant-abc123def456"
  [[ "$status" -eq 0 ]]
}

@test "validate_api_key: rejects invalid prefix" {
  run validate_api_key "invalid-key"
  [[ "$status" -ne 0 ]]
}

@test "validate_api_key: rejects empty string" {
  run validate_api_key ""
  [[ "$status" -ne 0 ]]
}

@test "validate_api_key: rejects key with wrong prefix" {
  run validate_api_key "sk-openai-xxx"
  [[ "$status" -ne 0 ]]
}

@test "validate_api_key: rejects partial prefix" {
  run validate_api_key "sk-an"
  [[ "$status" -ne 0 ]]
}

# ============================================================================
# detect_shell_profile tests
# ============================================================================

@test "detect_shell_profile: returns zshrc for zsh" {
  SHELL="/bin/zsh"
  unset ZDOTDIR
  result=$(detect_shell_profile)
  [[ "$result" == "$HOME/.zshrc" ]]
}

@test "detect_shell_profile: respects ZDOTDIR for zsh" {
  SHELL="/bin/zsh"
  ZDOTDIR="/custom/zsh"
  result=$(detect_shell_profile)
  [[ "$result" == "/custom/zsh/.zshrc" ]]
  unset ZDOTDIR
}

@test "detect_shell_profile: returns bashrc for bash when no bash_profile" {
  SHELL="/bin/bash"
  # Create a temp home without bash_profile
  local temp_home
  temp_home=$(mktemp -d)
  HOME="$temp_home"
  result=$(detect_shell_profile)
  [[ "$result" == "$temp_home/.bashrc" ]]
  rm -rf "$temp_home"
}

@test "detect_shell_profile: returns bash_profile for bash when it exists" {
  SHELL="/bin/bash"
  local temp_home
  temp_home=$(mktemp -d)
  touch "$temp_home/.bash_profile"
  HOME="$temp_home"
  result=$(detect_shell_profile)
  [[ "$result" == "$temp_home/.bash_profile" ]]
  rm -rf "$temp_home"
}

@test "detect_shell_profile: returns empty for unsupported shell" {
  SHELL="/bin/fish"
  result=$(detect_shell_profile)
  [[ "$result" == "" ]]
}

# ============================================================================
# string_in_file tests
# ============================================================================

@test "string_in_file: finds existing string" {
  local temp_file
  temp_file=$(mktemp)
  echo "ANTHROPIC_API_KEY=test" > "$temp_file"
  run string_in_file "ANTHROPIC_API_KEY" "$temp_file"
  [[ "$status" -eq 0 ]]
  rm "$temp_file"
}

@test "string_in_file: returns false for missing string" {
  local temp_file
  temp_file=$(mktemp)
  echo "OTHER_VAR=test" > "$temp_file"
  run string_in_file "ANTHROPIC_API_KEY" "$temp_file"
  [[ "$status" -ne 0 ]]
  rm "$temp_file"
}

@test "string_in_file: returns false for missing file" {
  run string_in_file "ANTHROPIC_API_KEY" "/tmp/nonexistent-file-12345"
  [[ "$status" -ne 0 ]]
}

@test "string_in_file: finds string in multi-line file" {
  local temp_file
  temp_file=$(mktemp)
  cat > "$temp_file" << 'EOF'
# My config
export PATH=/usr/bin
export ANTHROPIC_API_KEY=sk-ant-xxx
export OTHER=value
EOF
  run string_in_file "ANTHROPIC_API_KEY" "$temp_file"
  [[ "$status" -eq 0 ]]
  rm "$temp_file"
}

@test "string_in_file: handles empty file" {
  local temp_file
  temp_file=$(mktemp)
  run string_in_file "ANTHROPIC_API_KEY" "$temp_file"
  [[ "$status" -ne 0 ]]
  rm "$temp_file"
}

# ============================================================================
# get_os_type tests
# ============================================================================

@test "get_os_type: returns valid os type" {
  result=$(get_os_type)
  # Should be one of: macos, linux, unknown
  [[ "$result" == "macos" || "$result" == "linux" || "$result" == "unknown" ]]
}

# ============================================================================
# is_substretcher_project tests
# ============================================================================

@test "is_substretcher_project: returns true for valid project" {
  local temp_dir
  temp_dir=$(mktemp -d)
  echo '{"name": "substretcher", "version": "1.0.0"}' > "$temp_dir/package.json"
  run is_substretcher_project "$temp_dir"
  [[ "$status" -eq 0 ]]
  rm -rf "$temp_dir"
}

@test "is_substretcher_project: returns false for different project name" {
  local temp_dir
  temp_dir=$(mktemp -d)
  echo '{"name": "other-project", "version": "1.0.0"}' > "$temp_dir/package.json"
  run is_substretcher_project "$temp_dir"
  [[ "$status" -ne 0 ]]
  rm -rf "$temp_dir"
}

@test "is_substretcher_project: returns false for missing package.json" {
  local temp_dir
  temp_dir=$(mktemp -d)
  run is_substretcher_project "$temp_dir"
  [[ "$status" -ne 0 ]]
  rm -rf "$temp_dir"
}

# ============================================================================
# is_port_in_use tests (limited - depends on system state)
# ============================================================================

@test "is_port_in_use: returns false for unlikely port" {
  # Port 59999 is unlikely to be in use
  run is_port_in_use 59999
  [[ "$status" -ne 0 ]]
}

# ============================================================================
# Portable lowercase conversion tests (tr command)
# ============================================================================

@test "tr lowercase: converts Y to y" {
  result=$(echo "Y" | tr '[:upper:]' '[:lower:]')
  [[ "$result" == "y" ]]
}

@test "tr lowercase: converts YES to yes" {
  result=$(echo "YES" | tr '[:upper:]' '[:lower:]')
  [[ "$result" == "yes" ]]
}

@test "tr lowercase: preserves already lowercase" {
  result=$(echo "yes" | tr '[:upper:]' '[:lower:]')
  [[ "$result" == "yes" ]]
}

@test "tr lowercase: handles mixed case" {
  result=$(echo "YeS" | tr '[:upper:]' '[:lower:]')
  [[ "$result" == "yes" ]]
}
