#!/usr/bin/env bash
# install-lib.sh - Library functions for install.sh
# These functions are sourced, not executed directly.
# Designed to be testable with bats-core.

# Parse Node.js version string, return major version number
# Usage: parse_node_version "v18.17.0" → prints "18"
parse_node_version() {
  local version="$1"
  echo "$version" | sed -E 's/^v?([0-9]+).*/\1/'
}

# Check if version A >= version B (major version only)
# Usage: version_gte 18 16 → returns 0 (true)
version_gte() {
  [[ "$1" -ge "$2" ]]
}

# Trim whitespace from string
# Usage: trim "  hello  " → prints "hello"
trim() {
  local var="$1"
  var="${var#"${var%%[![:space:]]*}"}"
  var="${var%"${var##*[![:space:]]}"}"
  echo "$var"
}

# Validate API key format (basic check for Anthropic keys)
# Usage: validate_api_key "sk-ant-..." → returns 0 if valid format
validate_api_key() {
  local key="$1"
  [[ "$key" =~ ^sk-ant- ]]
}

# Detect shell profile file based on current shell
# Usage: detect_shell_profile → prints path like "/home/user/.zshrc"
detect_shell_profile() {
  local shell_name
  shell_name=$(basename "$SHELL")
  case "$shell_name" in
    zsh)
      echo "${ZDOTDIR:-$HOME}/.zshrc"
      ;;
    bash)
      # macOS uses .bash_profile for login shells, Linux uses .bashrc
      if [[ -f "$HOME/.bash_profile" ]]; then
        echo "$HOME/.bash_profile"
      else
        echo "$HOME/.bashrc"
      fi
      ;;
    *)
      # Unsupported shell - return empty string
      echo ""
      ;;
  esac
}

# Check if string already exists in file
# Usage: string_in_file "ANTHROPIC_API_KEY" ~/.zshrc → returns 0 if found
string_in_file() {
  local string="$1"
  local file="$2"
  [[ -f "$file" ]] && grep -q "$string" "$file"
}

# Detect Chrome executable path based on OS
# Usage: detect_chrome_path → prints path or empty if not found
detect_chrome_path() {
  local os_type
  os_type=$(uname -s)

  case "$os_type" in
    Darwin)
      # macOS - check common locations
      local chrome_paths=(
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary"
        "/Applications/Chromium.app/Contents/MacOS/Chromium"
        "$HOME/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
      )
      for path in "${chrome_paths[@]}"; do
        if [[ -x "$path" ]]; then
          echo "$path"
          return 0
        fi
      done
      ;;
    Linux)
      # Linux - check common commands
      local chrome_cmds=(
        "google-chrome"
        "google-chrome-stable"
        "chromium"
        "chromium-browser"
      )
      for cmd in "${chrome_cmds[@]}"; do
        if command -v "$cmd" &>/dev/null; then
          command -v "$cmd"
          return 0
        fi
      done
      ;;
  esac

  # Not found
  echo ""
  return 1
}

# Check if a port is in use
# Usage: is_port_in_use 9222 → returns 0 if in use
is_port_in_use() {
  local port="$1"
  if command -v lsof &>/dev/null; then
    lsof -i :"$port" &>/dev/null
  elif command -v nc &>/dev/null; then
    nc -z localhost "$port" &>/dev/null
  else
    # Can't check - assume not in use
    return 1
  fi
}

# Get the OS type in a normalized form
# Usage: get_os_type → prints "macos", "linux", or "unknown"
get_os_type() {
  local os_type
  os_type=$(uname -s)
  case "$os_type" in
    Darwin) echo "macos" ;;
    Linux) echo "linux" ;;
    *) echo "unknown" ;;
  esac
}

# Generate Chrome launch command for the current OS
# Usage: get_chrome_launch_command → prints the command string
get_chrome_launch_command() {
  local chrome_path
  chrome_path=$(detect_chrome_path)

  if [[ -z "$chrome_path" ]]; then
    echo ""
    return 1
  fi

  local os_type
  os_type=$(get_os_type)

  case "$os_type" in
    macos)
      echo "\"$chrome_path\" --remote-debugging-port=9222"
      ;;
    linux)
      echo "$chrome_path --remote-debugging-port=9222"
      ;;
    *)
      echo ""
      return 1
      ;;
  esac
}

# Check if package.json exists and has correct name
# Usage: is_substretcher_project "/path/to/dir" → returns 0 if valid
is_substretcher_project() {
  local dir="${1:-.}"
  local pkg_file="$dir/package.json"

  if [[ ! -f "$pkg_file" ]]; then
    return 1
  fi

  # Check if name is substretcher
  grep -q '"name"[[:space:]]*:[[:space:]]*"substretcher"' "$pkg_file"
}
