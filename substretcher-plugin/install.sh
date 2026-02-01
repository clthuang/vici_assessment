#!/usr/bin/env bash
# SubStretcher Installation Script
# Interactive setup for new users
# Usage: ./install.sh [--yes|-y]

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source the library functions
source "$SCRIPT_DIR/install-lib.sh"

# ============================================================================
# Configuration
# ============================================================================

MIN_NODE_VERSION=18
DEBUG_PORT=9222
DATA_DIR="$HOME/.substretcher"
SERVICES_DIR="$DATA_DIR/services"
CHROME_PROFILE_DIR="$DATA_DIR/chrome-profile"

# ============================================================================
# Flags
# ============================================================================

AUTO_YES=false
if [[ "$1" == "--yes" || "$1" == "-y" ]]; then
  AUTO_YES=true
fi

# ============================================================================
# Colors (disabled if not a terminal)
# ============================================================================

if [[ -t 1 ]]; then
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  YELLOW='\033[1;33m'
  BLUE='\033[0;34m'
  BOLD='\033[1m'
  NC='\033[0m'  # No Color
else
  RED='' GREEN='' YELLOW='' BLUE='' BOLD='' NC=''
fi

# ============================================================================
# Output Helpers
# ============================================================================

info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; }
step() { echo -e "\n${BOLD}==> $1${NC}"; }

# Prompt helper (respects AUTO_YES)
confirm() {
  local prompt="$1"
  local default="${2:-y}"
  if [[ "$AUTO_YES" == true ]]; then
    return 0
  fi
  read -rp "$prompt " answer
  answer="${answer:-$default}"
  # Use tr for lowercase conversion (portable across bash 3.2+ and zsh)
  answer=$(echo "$answer" | tr '[:upper:]' '[:lower:]')
  [[ "$answer" == "y" || "$answer" == "yes" ]]
}

# ============================================================================
# Check Functions
# ============================================================================

check_directory() {
  step "Checking project directory..."

  if ! is_substretcher_project "$SCRIPT_DIR"; then
    error "This doesn't appear to be the SubStretcher project directory."
    error "Expected to find package.json with name 'substretcher'."
    error "Please run this script from the substretcher-plugin directory."
    exit 1
  fi

  if [[ ! -d "$SCRIPT_DIR/src" ]]; then
    error "Source directory (src/) not found."
    error "Please make sure you have the complete project."
    exit 1
  fi

  success "Project directory verified"
}

check_node() {
  step "Checking Node.js..."

  if ! command -v node &>/dev/null; then
    error "Node.js is not installed."
    error "Please install Node.js $MIN_NODE_VERSION or later from https://nodejs.org"
    exit 1
  fi

  local node_version
  node_version=$(node --version)
  local major_version
  major_version=$(parse_node_version "$node_version")

  if ! version_gte "$major_version" "$MIN_NODE_VERSION"; then
    error "Node.js version $node_version is too old."
    error "Please upgrade to Node.js $MIN_NODE_VERSION or later."
    exit 1
  fi

  success "Node.js $node_version detected"
}

check_pnpm() {
  step "Checking pnpm..."

  if command -v pnpm &>/dev/null; then
    local pnpm_version
    pnpm_version=$(pnpm --version)
    success "pnpm $pnpm_version detected"
    return 0
  fi

  warn "pnpm is not installed."

  # Check if corepack is available
  if command -v corepack &>/dev/null; then
    if confirm "Install pnpm via corepack? [Y/n]"; then
      info "Enabling corepack..."
      corepack enable
      info "Installing pnpm..."
      corepack prepare pnpm@latest --activate
      success "pnpm installed via corepack"
      return 0
    fi
  fi

  # Fallback: check for npm
  if command -v npm &>/dev/null; then
    warn "pnpm not available. Will use npm instead."
    return 1
  fi

  error "No package manager available (pnpm or npm)."
  error "Please install pnpm: npm install -g pnpm"
  exit 1
}

check_chrome() {
  step "Checking Chrome..."

  local chrome_path
  chrome_path=$(detect_chrome_path)

  if [[ -n "$chrome_path" ]]; then
    success "Chrome detected: $chrome_path"
    return 0
  fi

  warn "Chrome not found in standard locations."
  warn "You'll need Chrome (or Chromium) installed to use SubStretcher."
  warn "Download from: https://www.google.com/chrome/"
  return 1
}

check_port() {
  step "Checking debug port $DEBUG_PORT..."

  if is_port_in_use "$DEBUG_PORT"; then
    warn "Port $DEBUG_PORT is already in use."
    warn "If Chrome is running, please close all Chrome windows before"
    warn "starting it with the debug flag."
    return 1
  fi

  success "Port $DEBUG_PORT is available"
  return 0
}

# ============================================================================
# Installation Functions
# ============================================================================

install_deps() {
  step "Installing dependencies..."

  cd "$SCRIPT_DIR"

  if command -v pnpm &>/dev/null; then
    pnpm install
  else
    npm install
  fi

  success "Dependencies installed"
}

build_project() {
  step "Building project..."

  cd "$SCRIPT_DIR"

  # Clean first to avoid stale artifacts
  if command -v pnpm &>/dev/null; then
    pnpm run clean 2>/dev/null || true
    pnpm run build
  else
    npm run clean 2>/dev/null || true
    npm run build
  fi

  if [[ ! -f "$SCRIPT_DIR/dist/cli/index.js" ]]; then
    error "Build failed: dist/cli/index.js not found"
    exit 1
  fi

  success "Project built successfully"
}

setup_global_link() {
  step "Global command setup..."

  if confirm "Link globally to use 'substretcher' command anywhere? [Y/n]"; then
    cd "$SCRIPT_DIR"
    if command -v pnpm &>/dev/null; then
      pnpm link --global
    else
      npm link
    fi
    success "Global command 'substretcher' installed"
  else
    info "Skipping global link. You can run via: node $SCRIPT_DIR/dist/cli/index.js"
  fi
}

create_data_dirs() {
  step "Creating data directories..."

  if [[ ! -d "$DATA_DIR" ]]; then
    mkdir -p "$DATA_DIR"
    info "Created $DATA_DIR"
  fi

  if [[ ! -d "$SERVICES_DIR" ]]; then
    mkdir -p "$SERVICES_DIR"
    info "Created $SERVICES_DIR"
  fi

  success "Data directories ready"
}

setup_api_key() {
  step "API key configuration..."

  local profile_file
  profile_file=$(detect_shell_profile)

  # Check if already configured
  if [[ -n "$ANTHROPIC_API_KEY" ]]; then
    success "ANTHROPIC_API_KEY is already set in environment"
    return 0
  fi

  if [[ -n "$profile_file" ]] && string_in_file "ANTHROPIC_API_KEY" "$profile_file"; then
    success "ANTHROPIC_API_KEY found in $profile_file"
    return 0
  fi

  if [[ "$AUTO_YES" == true ]]; then
    warn "Skipping API key setup in non-interactive mode"
    return 0
  fi

  echo ""
  info "SubStretcher requires an Anthropic API key."
  info "Get one at: https://console.anthropic.com/"
  echo ""

  read -rp "Enter your Anthropic API key (or press Enter to skip): " api_key
  api_key=$(trim "$api_key")

  if [[ -z "$api_key" ]]; then
    warn "Skipping API key setup. You'll need to set ANTHROPIC_API_KEY later."
    return 0
  fi

  if ! validate_api_key "$api_key"; then
    warn "This doesn't look like a valid Anthropic API key (expected sk-ant-...)"
    if ! confirm "Save anyway? [y/N]" "n"; then
      warn "API key not saved. You'll need to set ANTHROPIC_API_KEY manually."
      return 0
    fi
  fi

  if [[ -z "$profile_file" ]]; then
    warn "Could not detect shell profile. Please add manually:"
    echo "  export ANTHROPIC_API_KEY=$api_key"
    return 0
  fi

  if confirm "Add API key to $profile_file? [Y/n]"; then
    echo "" >> "$profile_file"
    echo "# SubStretcher API key" >> "$profile_file"
    echo "export ANTHROPIC_API_KEY=$api_key" >> "$profile_file"
    success "API key added to $profile_file"
    info "Run 'source $profile_file' or restart your terminal to activate"
  else
    info "You can add it manually:"
    echo "  export ANTHROPIC_API_KEY=$api_key"
  fi
}

setup_chrome_helper() {
  step "Chrome helper script..."

  local chrome_cmd
  chrome_cmd=$(get_chrome_launch_command)

  if [[ -z "$chrome_cmd" ]]; then
    warn "Could not determine Chrome path. Skipping helper script."
    return 0
  fi

  if confirm "Create start-chrome.sh helper script? [Y/n]"; then
    local helper_file="$SCRIPT_DIR/start-chrome.sh"

    cat > "$helper_file" << EOF
#!/usr/bin/env bash
# Start Chrome with remote debugging enabled for SubStretcher
# Generated by install.sh

echo "Starting Chrome with remote debugging on port $DEBUG_PORT..."
echo ""

# Use a separate Chrome profile to allow debugging even when Chrome is already running
CHROME_PROFILE="\$HOME/.substretcher/chrome-profile"
mkdir -p "\$CHROME_PROFILE"

$chrome_cmd &

echo ""
echo "Chrome started with debug profile at: \$CHROME_PROFILE"
echo "You can now run: substretcher status"
EOF

    chmod +x "$helper_file"
    success "Created $helper_file"
  else
    info "To start Chrome with debugging, run:"
    echo "  $chrome_cmd"
  fi
}

# ============================================================================
# Verification
# ============================================================================

verify_installation() {
  step "Verifying installation..."

  local all_good=true

  # Check build output
  if [[ -f "$SCRIPT_DIR/dist/cli/index.js" ]]; then
    success "Build output exists"
  else
    error "Build output missing"
    all_good=false
  fi

  # Check data directory
  if [[ -d "$DATA_DIR" ]]; then
    success "Data directory exists: $DATA_DIR"
  else
    error "Data directory missing"
    all_good=false
  fi

  # Check global command (if linked)
  if command -v substretcher &>/dev/null; then
    success "Global command available: substretcher"
  else
    info "Global command not installed (run via node dist/cli/index.js)"
  fi

  # Check Chrome connection (optional - may fail if Chrome not running)
  if is_port_in_use "$DEBUG_PORT"; then
    info "Attempting Chrome connection test..."
    if node "$SCRIPT_DIR/dist/cli/index.js" status 2>/dev/null; then
      success "Chrome connection verified!"
    else
      warn "Could not connect to Chrome on port $DEBUG_PORT"
    fi
  else
    info "Chrome not running on port $DEBUG_PORT (this is fine for now)"
  fi

  echo ""
  if [[ "$all_good" == true ]]; then
    echo -e "${GREEN}${BOLD}Installation complete!${NC}"
  else
    echo -e "${YELLOW}${BOLD}Installation completed with warnings.${NC}"
  fi
}

# ============================================================================
# Summary
# ============================================================================

print_next_steps() {
  echo ""
  echo -e "${BOLD}Next steps:${NC}"
  echo ""
  echo "1. Start Chrome with remote debugging:"

  local chrome_cmd
  chrome_cmd=$(get_chrome_launch_command)
  if [[ -n "$chrome_cmd" ]]; then
    if [[ -f "$SCRIPT_DIR/start-chrome.sh" ]]; then
      echo "   ./start-chrome.sh"
    else
      echo "   $chrome_cmd"
    fi
  else
    echo "   (see README.md for your platform)"
  fi

  echo ""
  echo "2. Set your API key (if not already done):"
  echo "   export ANTHROPIC_API_KEY=sk-ant-..."
  echo ""
  echo "3. Verify connection:"
  if command -v substretcher &>/dev/null; then
    echo "   substretcher status"
  else
    echo "   node dist/cli/index.js status"
  fi
  echo ""
  echo "4. Scan your subscriptions:"
  if command -v substretcher &>/dev/null; then
    echo "   substretcher scan --all"
  else
    echo "   node dist/cli/index.js scan --all"
  fi
  echo ""
}

# ============================================================================
# Main
# ============================================================================

main() {
  echo ""
  echo -e "${BOLD}SubStretcher Installation${NC}"
  echo "========================="
  echo ""

  # Prerequisites
  check_directory
  check_node
  check_pnpm || true  # Continue even if pnpm not found (we'll use npm)
  check_chrome || true  # Continue even if Chrome not found
  check_port || true  # Continue even if port in use

  # Installation
  install_deps
  build_project

  # Optional setup
  setup_global_link
  create_data_dirs
  setup_api_key
  setup_chrome_helper

  # Verification
  verify_installation
  print_next_steps
}

# Run main
main "$@"
