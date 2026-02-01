#!/usr/bin/env bash
# SubStretcher Uninstall Script
# Cleanly removes all SubStretcher artifacts with user control
# Usage: ./uninstall.sh [--yes] [--keep-data] [--dry-run]

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source the library functions
source "$SCRIPT_DIR/install-lib.sh"

# ============================================================================
# Configuration
# ============================================================================

DATA_DIR="$HOME/.substretcher"

# ============================================================================
# Flags
# ============================================================================

AUTO_YES=false
KEEP_DATA=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yes|-y)
      AUTO_YES=true
      shift
      ;;
    --keep-data)
      KEEP_DATA=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: ./uninstall.sh [--yes] [--keep-data] [--dry-run]"
      exit 1
      ;;
  esac
done

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
dry_run_msg() { echo -e "${YELLOW}[DRY-RUN]${NC} Would: $1"; }

# Prompt helper (respects AUTO_YES)
# Usage: confirm "prompt" "default" → returns 0 if yes
confirm() {
  local prompt="$1"
  local default="${2:-y}"
  if [[ "$AUTO_YES" == true ]]; then
    return 0
  fi
  read -rp "$prompt " answer
  answer="${answer:-$default}"
  # Convert to lowercase for comparison (portable way)
  answer=$(echo "$answer" | tr '[:upper:]' '[:lower:]')
  [[ "$answer" == "y" || "$answer" == "yes" ]]
}

# ============================================================================
# Detection Functions
# ============================================================================

# Detect which package manager was used to link globally
# Returns: "pnpm", "npm", or "none"
detect_package_manager() {
  if command -v pnpm &>/dev/null && pnpm list -g 2>/dev/null | grep -q "substretcher"; then
    echo "pnpm"
  elif command -v npm &>/dev/null && npm list -g 2>/dev/null | grep -q "substretcher"; then
    echo "npm"
  else
    echo "none"
  fi
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

  success "Project directory verified"
}

# ============================================================================
# Removal Functions
# ============================================================================

remove_global_link() {
  step "Removing global command..."

  local pkg_manager
  pkg_manager=$(detect_package_manager)

  if [[ "$pkg_manager" == "none" ]]; then
    info "Global 'substretcher' command not found. Skipping."
    return 0
  fi

  if ! confirm "Remove global 'substretcher' command? [Y/n]"; then
    info "Skipping global command removal."
    return 0
  fi

  if [[ "$DRY_RUN" == true ]]; then
    dry_run_msg "Remove global link using $pkg_manager"
    return 0
  fi

  cd "$SCRIPT_DIR"
  if [[ "$pkg_manager" == "pnpm" ]]; then
    # pnpm remove -g works more reliably than pnpm unlink --global
    pnpm remove -g substretcher 2>/dev/null || pnpm unlink --global 2>/dev/null || true
  else
    npm unlink --global 2>/dev/null || npm remove -g substretcher 2>/dev/null || true
  fi

  success "Global command removed (was linked via $pkg_manager)"
}

remove_data_dir() {
  step "User data directory..."

  if [[ ! -d "$DATA_DIR" ]]; then
    info "Data directory $DATA_DIR does not exist. Skipping."
    return 0
  fi

  if [[ "$KEEP_DATA" == true ]]; then
    info "Keeping data directory (--keep-data flag specified)."
    return 0
  fi

  echo ""
  warn "This directory contains your custom configs and audit logs:"
  echo "  $DATA_DIR"
  echo ""

  # Default is NO for data removal (destructive action)
  if [[ "$AUTO_YES" == true ]]; then
    # In auto mode, default to NO (preserve data) unless --keep-data is explicitly not set
    # and user explicitly provided --yes
    if ! confirm "Remove user data (~/.substretcher/)? [y/N]" "n"; then
      info "Keeping data directory."
      return 0
    fi
  else
    local answer
    read -rp "Remove user data (~/.substretcher/)? This includes custom configs and audit logs. [y/N] " answer
    answer="${answer:-n}"
    # Convert to lowercase for comparison (portable way)
    answer=$(echo "$answer" | tr '[:upper:]' '[:lower:]')
    if [[ "$answer" != "y" && "$answer" != "yes" ]]; then
      info "Keeping data directory."
      return 0
    fi
  fi

  if [[ "$DRY_RUN" == true ]]; then
    dry_run_msg "Remove directory $DATA_DIR"
    return 0
  fi

  rm -rf "$DATA_DIR"
  success "Removed $DATA_DIR"
}

remove_shell_entry() {
  step "Shell profile API key..."

  local profile_file
  profile_file=$(detect_shell_profile)

  if [[ -z "$profile_file" ]]; then
    warn "Could not detect shell profile. Skipping API key removal."
    return 0
  fi

  if [[ ! -f "$profile_file" ]]; then
    info "Shell profile $profile_file does not exist. Skipping."
    return 0
  fi

  # Check if the SubStretcher API key entry exists
  if ! string_in_file "# SubStretcher API key" "$profile_file"; then
    info "No SubStretcher API key entry found in $profile_file. Skipping."
    return 0
  fi

  if ! confirm "Remove API key entry from $profile_file? [Y/n]"; then
    info "Skipping API key removal from shell profile."
    return 0
  fi

  if [[ "$DRY_RUN" == true ]]; then
    dry_run_msg "Remove SubStretcher API key lines from $profile_file"
    return 0
  fi

  # Create backup before modifying
  cp "$profile_file" "$profile_file.substretcher-backup"
  info "Created backup: $profile_file.substretcher-backup"

  # Remove the SubStretcher comment and the export line that follows it
  # Use a temp file approach for portability (works on both macOS and Linux)
  local temp_file
  temp_file=$(mktemp)

  # Filter out the comment line and the export line
  grep -v "# SubStretcher API key" "$profile_file" | grep -v "^export ANTHROPIC_API_KEY=" > "$temp_file" || true
  mv "$temp_file" "$profile_file"

  success "Removed API key entry from $profile_file"
  info "Restart your terminal or run 'source $profile_file' to apply changes"
}

remove_build_artifacts() {
  step "Build artifacts..."

  local has_artifacts=false
  [[ -d "$SCRIPT_DIR/dist" ]] && has_artifacts=true
  [[ -d "$SCRIPT_DIR/node_modules" ]] && has_artifacts=true

  if [[ "$has_artifacts" == false ]]; then
    info "No build artifacts found. Skipping."
    return 0
  fi

  if ! confirm "Remove build artifacts (dist/ and node_modules/)? [Y/n]"; then
    info "Skipping build artifacts removal."
    return 0
  fi

  if [[ "$DRY_RUN" == true ]]; then
    [[ -d "$SCRIPT_DIR/dist" ]] && dry_run_msg "Remove $SCRIPT_DIR/dist/"
    [[ -d "$SCRIPT_DIR/node_modules" ]] && dry_run_msg "Remove $SCRIPT_DIR/node_modules/"
    return 0
  fi

  if [[ -d "$SCRIPT_DIR/dist" ]]; then
    rm -rf "$SCRIPT_DIR/dist"
    success "Removed dist/"
  fi

  if [[ -d "$SCRIPT_DIR/node_modules" ]]; then
    rm -rf "$SCRIPT_DIR/node_modules"
    success "Removed node_modules/"
  fi
}

remove_chrome_helper() {
  step "Chrome helper script..."

  local helper_file="$SCRIPT_DIR/start-chrome.sh"

  if [[ ! -f "$helper_file" ]]; then
    info "Chrome helper script not found. Skipping."
    return 0
  fi

  if ! confirm "Remove start-chrome.sh helper? [Y/n]"; then
    info "Skipping Chrome helper removal."
    return 0
  fi

  if [[ "$DRY_RUN" == true ]]; then
    dry_run_msg "Remove $helper_file"
    return 0
  fi

  rm -f "$helper_file"
  success "Removed start-chrome.sh"
}

# ============================================================================
# Summary
# ============================================================================

print_summary() {
  echo ""
  echo -e "${BOLD}Uninstall Summary${NC}"
  echo "================="
  echo ""

  if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}This was a dry run. No changes were made.${NC}"
    echo ""
    return 0
  fi

  echo "The following items may have been removed:"
  echo ""

  # Check what's gone
  if ! command -v substretcher &>/dev/null; then
    echo "  [✓] Global 'substretcher' command"
  fi

  if [[ ! -d "$DATA_DIR" ]]; then
    echo "  [✓] Data directory (~/.substretcher/)"
  else
    echo "  [ ] Data directory preserved at ~/.substretcher/"
  fi

  if [[ ! -d "$SCRIPT_DIR/dist" ]]; then
    echo "  [✓] Build artifacts (dist/)"
  fi

  if [[ ! -d "$SCRIPT_DIR/node_modules" ]]; then
    echo "  [✓] Dependencies (node_modules/)"
  fi

  if [[ ! -f "$SCRIPT_DIR/start-chrome.sh" ]]; then
    echo "  [✓] Chrome helper (start-chrome.sh)"
  fi

  local profile_file
  profile_file=$(detect_shell_profile)
  if [[ -n "$profile_file" ]] && [[ -f "$profile_file" ]]; then
    if ! string_in_file "# SubStretcher API key" "$profile_file"; then
      echo "  [✓] Shell profile entry"
    fi
  fi

  echo ""
  echo -e "${GREEN}${BOLD}Uninstall complete!${NC}"
  echo ""

  # Note about reinstalling
  if [[ -d "$SCRIPT_DIR/src" ]]; then
    echo "To reinstall, run: ./install.sh"
  fi
}

# ============================================================================
# Main
# ============================================================================

main() {
  echo ""
  echo -e "${BOLD}SubStretcher Uninstall${NC}"
  echo "======================"

  if [[ "$DRY_RUN" == true ]]; then
    echo -e "${YELLOW}Running in dry-run mode. No changes will be made.${NC}"
  fi

  echo ""

  # Verify we're in the right directory
  check_directory

  # Remove artifacts in logical order
  remove_global_link
  remove_data_dir
  remove_shell_entry
  remove_build_artifacts
  remove_chrome_helper

  # Show summary
  print_summary
}

# Run main
main "$@"
