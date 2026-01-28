#!/usr/bin/env bash
#
# NDS Skills Installer
#
# Usage:
#   curl -fsSL https://gitlab.gabia.com/<group>/nds/-/raw/main/install.sh | bash
#
# Options:
#   curl ... | bash -s -- --claude           # Install to Claude Code only
#   curl ... | bash -s -- --cursor           # Install to Cursor only
#   curl ... | bash -s -- --codex            # Install to Codex only
#   curl ... | bash -s -- --gemini           # Install to Gemini CLI only
#   curl ... | bash -s -- --antigravity      # Install to Antigravity only
#   curl ... | bash -s -- --all              # Install to all agents
#   curl ... | bash -s -- --skills "a,b,c"   # Install specific skills only
#   curl ... | bash -s -- --list             # List available skills
#

set -e

# ============================================================================
# Configuration - Update these values for your GitLab instance
# ============================================================================
GITLAB_HOST="${NDS_GITLAB_HOST:-gitlab.gabia.com}"
GITLAB_PROJECT="${NDS_GITLAB_PROJECT:-gabia/idc/nds}"
BRANCH="${NDS_BRANCH:-main}"

# ============================================================================
# Colors and logging
# ============================================================================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ============================================================================
# Agent configurations (compatible with bash 3.2)
# ============================================================================
AGENT_KEYS="claude cursor codex gemini antigravity"

get_agent_path() {
    case "$1" in
        claude)      echo "$HOME/.claude/skills" ;;
        cursor)      echo "$HOME/.claude/skills" ;;
        codex)       echo "$HOME/.codex/skills" ;;
        gemini)      echo "$HOME/.gemini/skills" ;;
        antigravity) echo "$HOME/.gemini/antigravity/global_skills" ;;
    esac
}

get_agent_name() {
    case "$1" in
        claude)      echo "Claude Code" ;;
        cursor)      echo "Cursor" ;;
        codex)       echo "Codex CLI" ;;
        gemini)      echo "Gemini CLI" ;;
        antigravity) echo "Antigravity" ;;
    esac
}

# ============================================================================
# Variables
# ============================================================================
SELECTED_AGENTS=""
SELECTED_SKILLS=""
LIST_ONLY=false
INTERACTIVE=true
TEMP_DIR=""

# ============================================================================
# Cleanup handler
# ============================================================================
cleanup() {
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
    fi
    # Restore terminal settings
    stty echo 2>/dev/null || true
    tput cnorm 2>/dev/null || true
}
trap cleanup EXIT

# ============================================================================
# Parse arguments
# ============================================================================
while [ $# -gt 0 ]; do
    case $1 in
        --claude)
            SELECTED_AGENTS="$SELECTED_AGENTS claude"
            INTERACTIVE=false
            shift
            ;;
        --cursor)
            SELECTED_AGENTS="$SELECTED_AGENTS cursor"
            INTERACTIVE=false
            shift
            ;;
        --codex)
            SELECTED_AGENTS="$SELECTED_AGENTS codex"
            INTERACTIVE=false
            shift
            ;;
        --gemini)
            SELECTED_AGENTS="$SELECTED_AGENTS gemini"
            INTERACTIVE=false
            shift
            ;;
        --antigravity)
            SELECTED_AGENTS="$SELECTED_AGENTS antigravity"
            INTERACTIVE=false
            shift
            ;;
        --all)
            SELECTED_AGENTS="claude cursor codex gemini antigravity"
            INTERACTIVE=false
            shift
            ;;
        --list)
            LIST_ONLY=true
            INTERACTIVE=false
            shift
            ;;
        --skills)
            SELECTED_SKILLS="$2"
            shift 2
            ;;
        --skills=*)
            SELECTED_SKILLS="${1#*=}"
            shift
            ;;
        --no-interactive)
            INTERACTIVE=false
            shift
            ;;
        -h|--help)
            cat << 'EOF'
NDS Skills Installer

Usage:
  curl -fsSL <url>/install.sh | bash
  curl -fsSL <url>/install.sh | bash -s -- [OPTIONS]

Options:
  --claude           Install to Claude Code (~/.claude/skills)
  --cursor           Install to Cursor (~/.claude/skills)
  --codex            Install to Codex CLI (~/.codex/skills)
  --gemini           Install to Gemini CLI (~/.gemini/skills)
  --antigravity      Install to Antigravity (~/.gemini/antigravity/global_skills)
  --all              Install to all agents
  --list             List available skills and exit
  --skills "a,b,c"   Install only specified skills (comma-separated)
  --no-interactive   Skip TUI selection (use with agent flags)
  -h, --help         Show this help message

Environment Variables:
  NDS_GITLAB_HOST    GitLab host (default: gitlab.gabia.com)
  NDS_GITLAB_PROJECT GitLab project path (default: nds/skills)
  NDS_BRANCH         Branch to use (default: main)

Examples:
  # Interactive mode (TUI selection)
  curl -fsSL <url>/install.sh | bash

  # Install to specific agents
  curl -fsSL <url>/install.sh | bash -s -- --claude --codex

  # Install to all agents
  curl -fsSL <url>/install.sh | bash -s -- --all

  # Install specific skills to Claude
  curl -fsSL <url>/install.sh | bash -s -- --claude --skills "gabia-dev-mcp-oracle,pptx"

  # List available skills
  curl -fsSL <url>/install.sh | bash -s -- --list
EOF
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# ============================================================================
# Check requirements
# ============================================================================
check_requirements() {
    local missing=""

    command -v curl >/dev/null 2>&1 || missing="$missing curl"
    if ! command -v unzip >/dev/null 2>&1 && ! command -v tar >/dev/null 2>&1; then
        missing="$missing unzip/tar"
    fi

    if [ -n "$missing" ]; then
        error "Missing required tools:$missing"
        exit 1
    fi
}

# ============================================================================
# TUI Multi-select Menu
# ============================================================================
show_multiselect_menu() {
    local cursor=0
    local num_options=5

    # Selection states (0=unselected, 1=selected)
    local sel_claude=0
    local sel_cursor=0
    local sel_codex=0
    local sel_gemini=0
    local sel_antigravity=0

    # Hide cursor and disable echo
    tput civis 2>/dev/null || true
    stty -echo 2>/dev/null || true

    while true; do
        # Clear screen and show menu
        clear
        echo ""
        echo -e "${CYAN}================================${NC}"
        echo -e "${CYAN}   NDS Skills Installer${NC}"
        echo -e "${CYAN}================================${NC}"
        echo ""
        echo -e "${BOLD}Select coding agents to install skills:${NC}"
        echo ""
        echo -e "${DIM}  [Space] Toggle  [Enter] Confirm  [a] Select All  [n] Select None  [q] Quit${NC}"
        echo ""

        # Display options
        local i=0
        for agent in claude cursor codex gemini antigravity; do
            local name=$(get_agent_name "$agent")
            local path=$(get_agent_path "$agent")
            local prefix="  "
            local checkbox="[ ]"
            local highlight=""

            if [ $i -eq $cursor ]; then
                prefix="> "
                highlight="${BOLD}"
            fi

            # Check selection state
            local is_selected=0
            case $agent in
                claude)      is_selected=$sel_claude ;;
                cursor)      is_selected=$sel_cursor ;;
                codex)       is_selected=$sel_codex ;;
                gemini)      is_selected=$sel_gemini ;;
                antigravity) is_selected=$sel_antigravity ;;
            esac

            if [ $is_selected -eq 1 ]; then
                checkbox="${GREEN}[✓]${NC}"
            fi

            echo -e "${highlight}${prefix}${checkbox} ${name}${NC}"
            echo -e "${DIM}      ${path}${NC}"
            echo ""

            i=$((i + 1))
        done

        # Read single character
        local key
        IFS= read -rsn1 key

        case "$key" in
            $'\x1b')  # Escape sequence
                local key2
                read -rsn2 -t 0.1 key2 || true
                case "$key2" in
                    '[A')  # Up arrow
                        cursor=$((cursor - 1))
                        [ $cursor -lt 0 ] && cursor=$((num_options - 1))
                        ;;
                    '[B')  # Down arrow
                        cursor=$((cursor + 1))
                        [ $cursor -ge $num_options ] && cursor=0
                        ;;
                esac
                ;;
            ' ')  # Space - toggle selection
                case $cursor in
                    0) sel_claude=$((1 - sel_claude)) ;;
                    1) sel_cursor=$((1 - sel_cursor)) ;;
                    2) sel_codex=$((1 - sel_codex)) ;;
                    3) sel_gemini=$((1 - sel_gemini)) ;;
                    4) sel_antigravity=$((1 - sel_antigravity)) ;;
                esac
                ;;
            'a'|'A')  # Select all
                sel_claude=1; sel_cursor=1; sel_codex=1; sel_gemini=1; sel_antigravity=1
                ;;
            'n'|'N')  # Select none
                sel_claude=0; sel_cursor=0; sel_codex=0; sel_gemini=0; sel_antigravity=0
                ;;
            'q'|'Q')  # Quit
                tput cnorm 2>/dev/null || true
                stty echo 2>/dev/null || true
                echo ""
                info "Installation cancelled"
                exit 0
                ;;
            '')  # Enter - confirm
                break
                ;;
            'j')  # vim-style down
                cursor=$((cursor + 1))
                [ $cursor -ge $num_options ] && cursor=0
                ;;
            'k')  # vim-style up
                cursor=$((cursor - 1))
                [ $cursor -lt 0 ] && cursor=$((num_options - 1))
                ;;
        esac
    done

    # Restore cursor and terminal
    tput cnorm 2>/dev/null || true
    stty echo 2>/dev/null || true
    clear

    # Build result
    SELECTED_AGENTS=""
    [ $sel_claude -eq 1 ] && SELECTED_AGENTS="$SELECTED_AGENTS claude"
    [ $sel_cursor -eq 1 ] && SELECTED_AGENTS="$SELECTED_AGENTS cursor"
    [ $sel_codex -eq 1 ] && SELECTED_AGENTS="$SELECTED_AGENTS codex"
    [ $sel_gemini -eq 1 ] && SELECTED_AGENTS="$SELECTED_AGENTS gemini"
    [ $sel_antigravity -eq 1 ] && SELECTED_AGENTS="$SELECTED_AGENTS antigravity"
}

# ============================================================================
# Get available skills list
# ============================================================================
get_skills_list() {
    local manifest_url="https://${GITLAB_HOST}/${GITLAB_PROJECT}/-/raw/${BRANCH}/skills/manifest.txt"

    # Try to fetch manifest (only if response looks like a skill list, not HTML)
    local manifest
    manifest=$(curl -fsSL "$manifest_url" 2>/dev/null || echo "")

    # Check if response is valid (not HTML and not empty)
    if [ -n "$manifest" ] && ! echo "$manifest" | head -1 | grep -q "<!DOCTYPE\|<html"; then
        echo "$manifest"
        return 0
    fi

    # Fallback: hardcoded list
    cat << 'SKILLS_LIST'
algorithmic-art
board-resolver
brand-guidelines
canvas-design
code-simplifier
dev-plan
divide-conquer-tasks
doc-coauthoring
docx
frontend-design
gabia-dev-mcp-confluence
gabia-dev-mcp-figma
gabia-dev-mcp-gitlab-issues
gabia-dev-mcp-gitlab-merge-requests
gabia-dev-mcp-mattermost
gabia-dev-mcp-memory
gabia-dev-mcp-mysql
gabia-dev-mcp-oracle
hiworks-memo
internal-comms
mac-cron
mcp-builder
pdf
pptx
skill-creator
slack-gif-creator
theme-factory
web-artifacts-builder
webapp-testing
work-logger
xlsx
SKILLS_LIST
}

# ============================================================================
# List skills
# ============================================================================
list_skills() {
    echo ""
    echo -e "${CYAN}Available NDS Skills:${NC}"
    echo "========================"
    get_skills_list | while IFS= read -r skill; do
        [ -z "$skill" ] && continue
        echo "  • $skill"
    done
    echo ""
    echo "Total: $(get_skills_list | grep -c .)"
    echo ""
}

# ============================================================================
# Download entire skills directory as archive
# ============================================================================
download_all_skills() {
    local target_dir="$1"

    TEMP_DIR=$(mktemp -d)
    local archive_file="${TEMP_DIR}/nds.zip"
    local project_name="${GITLAB_PROJECT##*/}"

    # GitLab archive URL
    local archive_url="https://${GITLAB_HOST}/${GITLAB_PROJECT}/-/archive/${BRANCH}/${project_name}-${BRANCH}.zip"

    info "Downloading skills archive..."

    if ! curl -fsSL "$archive_url" -o "$archive_file" 2>/dev/null; then
        # Try tar.gz if zip fails
        archive_url="https://${GITLAB_HOST}/${GITLAB_PROJECT}/-/archive/${BRANCH}/${project_name}-${BRANCH}.tar.gz"
        archive_file="${TEMP_DIR}/nds.tar.gz"

        if ! curl -fsSL "$archive_url" -o "$archive_file" 2>/dev/null; then
            error "Failed to download archive from GitLab"
            error "URL: $archive_url"
            error "Check if the repository exists and is accessible"
            return 1
        fi
    fi

    info "Extracting..."

    # Extract based on file type
    case "$archive_file" in
        *.zip) unzip -q "$archive_file" -d "$TEMP_DIR" ;;
        *)     tar -xzf "$archive_file" -C "$TEMP_DIR" ;;
    esac

    # Find the skills directory
    local extracted_dir
    extracted_dir=$(find "$TEMP_DIR" -maxdepth 2 -type d -name "skills" | head -1)

    if [ -z "$extracted_dir" ] || [ ! -d "$extracted_dir" ]; then
        error "Skills directory not found in archive"
        return 1
    fi

    # Determine which skills to install
    local skills_to_install
    if [ -n "$SELECTED_SKILLS" ]; then
        skills_to_install=$(echo "$SELECTED_SKILLS" | tr ',' '\n')
    else
        skills_to_install=$(get_skills_list)
    fi

    # Install each skill
    local installed=0
    local skipped=0

    while IFS= read -r skill; do
        [ -z "$skill" ] && continue
        skill=$(echo "$skill" | tr -d '[:space:]')

        local src_skill_dir="${extracted_dir}/${skill}"
        local src_skill_file="${extracted_dir}/${skill}.skill"
        local dest_skill_dir="${target_dir}/${skill}"
        local dest_skill_file="${target_dir}/${skill}.skill"

        # Check for directory-based skill
        if [ -d "$src_skill_dir" ]; then
            rm -rf "$dest_skill_dir"
            cp -R "$src_skill_dir" "$dest_skill_dir"

            # Remove __pycache__ directories
            find "$dest_skill_dir" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

            success "Installed: $skill"
            installed=$((installed + 1))
        # Check for .skill file
        elif [ -f "$src_skill_file" ]; then
            cp "$src_skill_file" "$dest_skill_file"
            success "Installed: ${skill}.skill"
            installed=$((installed + 1))
        else
            warn "Not found: $skill"
            skipped=$((skipped + 1))
        fi
    done << EOF
$skills_to_install
EOF

    echo ""
    info "Installed: $installed skills"
    [ $skipped -gt 0 ] && warn "Skipped: $skipped skills"

    return 0
}

# ============================================================================
# Install to a target directory
# ============================================================================
install_to() {
    local agent_key="$1"
    local skills_dir=$(get_agent_path "$agent_key")
    local agent_name=$(get_agent_name "$agent_key")

    echo ""
    info "Installing to ${agent_name} (${skills_dir})..."

    # Create skills directory
    mkdir -p "$skills_dir"

    # Download and install
    if download_all_skills "$skills_dir"; then
        success "Installation to ${agent_name} complete"
        return 0
    else
        error "Installation to ${agent_name} failed"
        return 1
    fi
}

# ============================================================================
# Main
# ============================================================================
main() {
    echo ""
    echo -e "${CYAN}================================${NC}"
    echo -e "${CYAN}   NDS Skills Installer${NC}"
    echo -e "${CYAN}================================${NC}"
    echo ""

    check_requirements

    if [ "$LIST_ONLY" = true ]; then
        list_skills
        exit 0
    fi

    # Interactive TUI selection if no agents specified
    if [ "$INTERACTIVE" = true ] && [ -z "$SELECTED_AGENTS" ]; then
        # Check if we have a TTY
        if [ -t 0 ]; then
            show_multiselect_menu

            if [ -z "$SELECTED_AGENTS" ]; then
                warn "No agents selected"
                exit 0
            fi
        else
            # No TTY available (piped input), show simple prompt
            echo "Available coding agents:"
            echo "  1) Claude Code  (~/.claude/skills)"
            echo "  2) Cursor       (~/.claude/skills)"
            echo "  3) Codex CLI    (~/.codex/skills)"
            echo "  4) Gemini CLI   (~/.gemini/skills)"
            echo "  5) Antigravity  (~/.gemini/antigravity/global_skills)"
            echo ""
            echo "Enter numbers separated by space (e.g., '1 3 4') or 'all':"
            read -r selection

            if [ "$selection" = "all" ]; then
                SELECTED_AGENTS="claude cursor codex gemini antigravity"
            else
                for num in $selection; do
                    case $num in
                        1) SELECTED_AGENTS="$SELECTED_AGENTS claude" ;;
                        2) SELECTED_AGENTS="$SELECTED_AGENTS cursor" ;;
                        3) SELECTED_AGENTS="$SELECTED_AGENTS codex" ;;
                        4) SELECTED_AGENTS="$SELECTED_AGENTS gemini" ;;
                        5) SELECTED_AGENTS="$SELECTED_AGENTS antigravity" ;;
                    esac
                done
            fi

            if [ -z "$SELECTED_AGENTS" ]; then
                warn "No agents selected"
                exit 0
            fi
        fi
    fi

    # Default to all if still no agents selected
    if [ -z "$SELECTED_AGENTS" ]; then
        SELECTED_AGENTS="claude cursor codex gemini antigravity"
    fi

    # Remove duplicates (claude and cursor share the same path)
    local unique_paths=""
    local final_agents=""
    for agent in $SELECTED_AGENTS; do
        local path=$(get_agent_path "$agent")
        if ! echo "$unique_paths" | grep -q "$path"; then
            unique_paths="$unique_paths $path"
            final_agents="$final_agents $agent"
        fi
    done

    echo ""
    info "GitLab: https://${GITLAB_HOST}/${GITLAB_PROJECT}"
    info "Branch: ${BRANCH}"
    echo ""
    info "Selected agents:"
    for agent in $SELECTED_AGENTS; do
        echo "  • $(get_agent_name "$agent") ($(get_agent_path "$agent"))"
    done
    echo ""

    local install_failed=false

    for agent in $final_agents; do
        if ! install_to "$agent"; then
            install_failed=true
        fi
    done

    echo ""
    echo -e "${CYAN}================================${NC}"

    if [ "$install_failed" = true ]; then
        error "Installation completed with errors"
        exit 1
    fi

    success "Installation complete!"
    echo -e "${CYAN}================================${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Configure environment variables for skills that need them"
    echo "     (See each skill's SKILL.md for required variables)"
    echo "  2. Restart your coding agent"
    echo ""
    echo "For environment variable setup, see:"
    echo "  https://${GITLAB_HOST}/${GITLAB_PROJECT}/-/blob/${BRANCH}/skills/README.md"
    echo ""
}

main "$@"
