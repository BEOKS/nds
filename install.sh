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
#   curl ... | bash -s -- --copilot          # Install to GitHub Copilot only
#   curl ... | bash -s -- --all              # Install to all agents
#   curl ... | bash -s -- --skills "a,b,c"   # Install specific skills only
#   curl ... | bash -s -- --list             # List available skills
#

set -e

# ============================================================================
# Configuration
# ============================================================================
NEXUS_BASE_URL="${NDS_NEXUS_URL:-https://repo.gabia.com/repository/raw-repository/nds}"
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
AGENT_KEYS="claude cursor codex gemini antigravity copilot"

get_agent_path() {
    case "$1" in
        claude)      echo "$HOME/.claude/skills" ;;
        cursor)      echo "$HOME/.claude/skills" ;;
        codex)       echo "$HOME/.codex/skills" ;;
        gemini)      echo "$HOME/.gemini/skills" ;;
        antigravity) echo "$HOME/.gemini/antigravity/global_skills" ;;
        copilot)     echo "$HOME/.claude/skills" ;;
    esac
}

get_agent_name() {
    case "$1" in
        claude)      echo "Claude Code" ;;
        cursor)      echo "Cursor" ;;
        codex)       echo "Codex CLI" ;;
        gemini)      echo "Gemini CLI" ;;
        antigravity) echo "Antigravity" ;;
        copilot)     echo "GitHub Copilot" ;;
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
        --copilot)
            SELECTED_AGENTS="$SELECTED_AGENTS copilot"
            INTERACTIVE=false
            shift
            ;;
        --all)
            SELECTED_AGENTS="claude cursor codex gemini antigravity copilot"
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
  --copilot          Install to GitHub Copilot (~/.claude/skills)
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
# Python installation and dependency management
# ============================================================================
PYTHON_CMD=""
PIP_CMD=""
SKIP_PYTHON=false

detect_python() {
    # Try python3 first, then python
    if command -v python3 >/dev/null 2>&1; then
        PYTHON_CMD="python3"
    elif command -v python >/dev/null 2>&1; then
        # Check if it's Python 3
        if python --version 2>&1 | grep -q "Python 3"; then
            PYTHON_CMD="python"
        fi
    fi

    if [ -n "$PYTHON_CMD" ]; then
        # Always prefer $PYTHON_CMD -m pip to ensure pip matches Python version
        if $PYTHON_CMD -m pip --version >/dev/null 2>&1; then
            PIP_CMD="$PYTHON_CMD -m pip"
        elif command -v pip3 >/dev/null 2>&1; then
            # Verify pip3 points to the same Python
            local pip3_python
            pip3_python=$(pip3 --version 2>&1 | grep -oE 'python [0-9.]+' | head -1)
            if [ -n "$pip3_python" ]; then
                PIP_CMD="pip3"
            fi
        fi
        return 0
    fi
    return 1
}

get_python_version() {
    if [ -n "$PYTHON_CMD" ]; then
        $PYTHON_CMD --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+'
    fi
}

install_python_macos() {
    info "Attempting to install Python on macOS..."

    # Check for Homebrew
    if command -v brew >/dev/null 2>&1; then
        info "Installing Python via Homebrew..."
        brew install python
        return $?
    fi

    # Check for MacPorts
    if command -v port >/dev/null 2>&1; then
        info "Installing Python via MacPorts..."
        sudo port install python311
        return $?
    fi

    # Fallback: Download from python.org
    warn "No package manager found. Please install Python manually:"
    echo "  1. Visit https://www.python.org/downloads/"
    echo "  2. Download and install Python 3.11 or later"
    echo "  3. Re-run this installer"
    return 1
}

install_python_linux() {
    info "Attempting to install Python on Linux..."

    # Detect package manager
    if command -v apt-get >/dev/null 2>&1; then
        info "Installing Python via apt..."
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip python3-venv
        return $?
    elif command -v dnf >/dev/null 2>&1; then
        info "Installing Python via dnf..."
        sudo dnf install -y python3 python3-pip
        return $?
    elif command -v yum >/dev/null 2>&1; then
        info "Installing Python via yum..."
        sudo yum install -y python3 python3-pip
        return $?
    elif command -v pacman >/dev/null 2>&1; then
        info "Installing Python via pacman..."
        sudo pacman -S --noconfirm python python-pip
        return $?
    elif command -v apk >/dev/null 2>&1; then
        info "Installing Python via apk..."
        apk add --no-cache python3 py3-pip
        return $?
    elif command -v zypper >/dev/null 2>&1; then
        info "Installing Python via zypper..."
        sudo zypper install -y python3 python3-pip
        return $?
    fi

    warn "Could not detect package manager. Please install Python manually."
    return 1
}

install_python() {
    local os_type
    os_type=$(uname -s)

    case "$os_type" in
        Darwin)
            install_python_macos
            ;;
        Linux)
            install_python_linux
            ;;
        *)
            warn "Unsupported OS: $os_type"
            warn "Please install Python 3.8+ manually"
            return 1
            ;;
    esac
}

check_and_install_python() {
    echo ""
    echo -e "${CYAN}================================${NC}"
    echo -e "${CYAN}   Python Environment Setup${NC}"
    echo -e "${CYAN}================================${NC}"
    echo ""

    if detect_python; then
        local version
        version=$(get_python_version)
        success "Python found: $PYTHON_CMD (version $version)"

        if [ -z "$PIP_CMD" ]; then
            warn "pip not found. Attempting to install..."
            $PYTHON_CMD -m ensurepip --upgrade 2>/dev/null || true
            detect_python
        fi

        if [ -n "$PIP_CMD" ]; then
            success "pip found: $PIP_CMD"
        else
            warn "pip not available. Python dependencies will not be installed."
            return 1
        fi
        return 0
    fi

    warn "Python 3 not found on this system."
    echo ""
    echo "Python is required for many NDS skills to work properly."
    echo ""
    echo -n "Would you like to install Python automatically? (y/n): "

    local answer
    if [ -e /dev/tty ]; then
        read -r answer </dev/tty
    else
        read -r answer
    fi

    case "$answer" in
        [Yy]|[Yy][Ee][Ss])
            if install_python; then
                # Re-detect after installation
                if detect_python; then
                    success "Python installed successfully: $PYTHON_CMD"
                    return 0
                fi
            fi
            error "Failed to install Python"
            return 1
            ;;
        *)
            warn "Skipping Python installation"
            SKIP_PYTHON=true
            return 1
            ;;
    esac
}

install_python_dependencies() {
    if [ "$SKIP_PYTHON" = true ] || [ -z "$PIP_CMD" ]; then
        warn "Skipping Python dependencies installation"
        return 0
    fi

    echo ""
    info "Installing Python dependencies..."

    # Download requirements.txt from Nexus
    local req_url="${NEXUS_BASE_URL}/requirements.txt"
    local req_file="${TEMP_DIR:-/tmp}/nds-requirements.txt"

    if curl -fsSL "$req_url" -o "$req_file" 2>/dev/null; then
        info "Downloaded requirements.txt from Nexus"
    else
        # Fallback: try GitLab
        req_url="https://${GITLAB_HOST}/${GITLAB_PROJECT}/-/raw/${BRANCH}/requirements.txt"
        if curl -fsSL "$req_url" -o "$req_file" 2>/dev/null; then
            info "Downloaded requirements.txt from GitLab"
        else
            warn "Could not download requirements.txt"
            return 1
        fi
    fi

    # Install dependencies
    info "Installing packages (this may take a few minutes)..."

    # Use temp file to capture pip output and exit code properly
    local pip_log="${TEMP_DIR:-/tmp}/nds-pip-install.log"
    local pip_exit_code=0

    $PIP_CMD install --user -r "$req_file" > "$pip_log" 2>&1 || pip_exit_code=$?

    # Show relevant output
    if [ -f "$pip_log" ]; then
        while IFS= read -r line; do
            if echo "$line" | grep -q "Successfully installed"; then
                echo -e "${GREEN}[OK]${NC} $line"
            elif echo "$line" | grep -q "ERROR\|error"; then
                echo -e "${RED}[ERROR]${NC} $line"
            fi
        done < "$pip_log"
        rm -f "$pip_log"
    fi

    if [ $pip_exit_code -eq 0 ]; then
        success "Python dependencies installed successfully"
        return 0
    else
        warn "Some Python dependencies may have failed to install (exit code: $pip_exit_code)"
        warn "You can manually install them later with:"
        echo "  pip install -r requirements.txt"
        return 1
    fi
}

# ============================================================================
# TUI Multi-select Menu
# ============================================================================
show_multiselect_menu() {
    local cursor=0
    local num_options=6

    # Selection states (0=unselected, 1=selected)
    local sel_claude=0
    local sel_cursor=0
    local sel_codex=0
    local sel_gemini=0
    local sel_antigravity=0
    local sel_copilot=0

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
        for agent in claude cursor codex gemini antigravity copilot; do
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
                copilot)     is_selected=$sel_copilot ;;
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
                    5) sel_copilot=$((1 - sel_copilot)) ;;
                esac
                ;;
            'a'|'A')  # Select all
                sel_claude=1; sel_cursor=1; sel_codex=1; sel_gemini=1; sel_antigravity=1; sel_copilot=1
                ;;
            'n'|'N')  # Select none
                sel_claude=0; sel_cursor=0; sel_codex=0; sel_gemini=0; sel_antigravity=0; sel_copilot=0
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
    [ $sel_copilot -eq 1 ] && SELECTED_AGENTS="$SELECTED_AGENTS copilot"
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
    local archive_file="${TEMP_DIR}/nds-skills.zip"

    # Nexus archive URL
    local archive_url="${NEXUS_BASE_URL}/nds-skills.zip"

    info "Downloading skills archive from Nexus..."

    if ! curl -fsSL "$archive_url" -o "$archive_file" 2>/dev/null; then
        error "Failed to download archive from Nexus"
        error "URL: $archive_url"
        error "Check if the file exists and is accessible"
        return 1
    fi

    info "Extracting..."

    # Extract zip file
    unzip -q "$archive_file" -d "$TEMP_DIR"

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
# Environment variable configuration
# ============================================================================
ENV_VARS_ADDED=()

prompt_env_var() {
    local var_name="$1"
    local description="$2"
    local token_url="$3"
    local is_optional="$4"

    # Check if already set
    local current_value
    eval "current_value=\${$var_name:-}"

    if [ -n "$current_value" ]; then
        success "$var_name is already set"
        return 0
    fi

    echo ""
    echo -e "${YELLOW}▶ $var_name${NC}"
    echo "  $description"
    if [ -n "$token_url" ]; then
        echo -e "  ${DIM}토큰 생성: $token_url${NC}"
    fi

    local prompt_text="  Enter value"
    if [ "$is_optional" = "true" ]; then
        prompt_text="$prompt_text (or press Enter to skip)"
    fi
    echo -n "$prompt_text: "

    local value
    if [ -e /dev/tty ]; then
        read -r value </dev/tty
    else
        read -r value
    fi

    if [ -z "$value" ]; then
        if [ "$is_optional" = "true" ]; then
            warn "Skipped $var_name"
            return 0
        else
            warn "Skipped $var_name (required for this skill)"
            return 1
        fi
    fi

    # Add to shell profile
    ENV_VARS_ADDED+=("export $var_name=\"$value\"")
    success "Set $var_name"
    return 0
}

configure_environment_variables() {
    echo ""
    echo -e "${CYAN}================================${NC}"
    echo -e "${CYAN}   Environment Variables Setup${NC}"
    echo -e "${CYAN}================================${NC}"
    echo ""
    echo "설치된 스킬에 필요한 환경변수를 설정합니다."
    echo "사용하지 않는 스킬은 Enter를 눌러 스킵할 수 있습니다."
    echo ""

    # GitLab Token
    echo -e "${BOLD}[GitLab - Issues & Merge Requests]${NC}"
    prompt_env_var "GITLAB_TOKEN" \
        "GitLab 액세스 토큰 (Issues, MR 스킬에 필요)" \
        "https://gitlab.gabia.com/-/profile/personal_access_tokens" \
        "true"

    # Confluence
    echo ""
    echo -e "${BOLD}[Confluence]${NC}"
    prompt_env_var "CONFLUENCE_BASE_URL" \
        "Confluence 서버 베이스 URL (예: https://confluence.gabia.com)" \
        "" \
        "true"

    prompt_env_var "CONFLUENCE_API_TOKEN" \
        "Confluence API 토큰" \
        "https://confluence.gabia.com/plugins/personalaccesstokens/usertokens.action" \
        "true"

    if [ -z "${CONFLUENCE_USERNAME:-}" ]; then
        prompt_env_var "CONFLUENCE_USERNAME" \
            "Confluence 사용자명 (API 토큰과 함께 사용)" \
            "" \
            "true"
    fi

    # Mattermost Token
    echo ""
    echo -e "${BOLD}[Mattermost]${NC}"
    prompt_env_var "MATTERMOST_TOKEN" \
        "Mattermost 액세스 토큰" \
        "" \
        "true"

    # Figma Token
    echo ""
    echo -e "${BOLD}[Figma]${NC}"
    prompt_env_var "FIGMA_API_KEY" \
        "Figma API 키" \
        "" \
        "true"

    # Sentry
    echo ""
    echo -e "${BOLD}[Sentry]${NC}"
    prompt_env_var "SENTRY_TOKEN" \
        "Sentry Auth Token (event:read 스코프 필요)" \
        "" \
        "true"

    # Elasticsearch / Kibana
    echo ""
    echo -e "${BOLD}[Elasticsearch / Kibana]${NC}"
    prompt_env_var "LDAP_USER" \
        "LDAP 사용자 ID (nginx Basic Auth)" \
        "" \
        "true"

    if printf '%s\n' "${ENV_VARS_ADDED[@]}" | grep -q "LDAP_USER"; then
        prompt_env_var "LDAP_PWD" \
            "LDAP 비밀번호" \
            "" \
            "true"
    fi

    # Hiworks 쪽지
    echo ""
    echo -e "${BOLD}[Hiworks 쪽지]${NC}"
    prompt_env_var "HIWORKS_ID" \
        "Hiworks 사용자 ID (이메일의 @ 앞부분)" \
        "" \
        "true"

    if printf '%s\n' "${ENV_VARS_ADDED[@]}" | grep -q "HIWORKS_ID"; then
        prompt_env_var "HIWORKS_DOMAIN" \
            "Hiworks 도메인 (예: company.com)" \
            "" \
            "true"
        prompt_env_var "HIWORKS_PWD" \
            "Hiworks 비밀번호" \
            "" \
            "true"
    fi

    # Oracle DB
    echo ""
    echo -e "${BOLD}[Oracle DB]${NC}"
    prompt_env_var "ORACLE_HOST" \
        "Oracle DB 호스트" \
        "" \
        "true"

    # Only ask for other Oracle vars if host was provided
    if printf '%s\n' "${ENV_VARS_ADDED[@]}" | grep -q "ORACLE_HOST"; then
        prompt_env_var "ORACLE_USERNAME" \
            "Oracle DB 사용자명" \
            "" \
            "true"
        prompt_env_var "ORACLE_PASSWORD" \
            "Oracle DB 비밀번호" \
            "" \
            "true"
    fi

    # MySQL DB
    echo ""
    echo -e "${BOLD}[MySQL DB]${NC}"
    prompt_env_var "MYSQL_HOST" \
        "MySQL DB 호스트 (단일 계정 사용 시)" \
        "" \
        "true"

    # Only ask for other MySQL vars if host was provided
    if printf '%s\n' "${ENV_VARS_ADDED[@]}" | grep -q "MYSQL_HOST"; then
        prompt_env_var "MYSQL_USERNAME" \
            "MySQL DB 사용자명" \
            "" \
            "true"
        prompt_env_var "MYSQL_PASSWORD" \
            "MySQL DB 비밀번호" \
            "" \
            "true"
    fi

    # Save to shell profile if any vars were added
    if [ ${#ENV_VARS_ADDED[@]} -gt 0 ]; then
        echo ""
        echo -e "${CYAN}================================${NC}"
        save_environment_variables
    else
        echo ""
        info "No environment variables were configured"
    fi
}

save_environment_variables() {
    # Determine shell profile
    local shell_profile=""
    if [ -n "${ZSH_VERSION:-}" ] || [ "$SHELL" = "/bin/zsh" ] || [ "$SHELL" = "/usr/bin/zsh" ]; then
        shell_profile="$HOME/.zshrc"
    elif [ -n "${BASH_VERSION:-}" ] || [ "$SHELL" = "/bin/bash" ] || [ "$SHELL" = "/usr/bin/bash" ]; then
        shell_profile="$HOME/.bashrc"
    else
        shell_profile="$HOME/.profile"
    fi

    echo ""
    echo "환경변수를 저장할 위치를 선택하세요:"
    echo "  1) $shell_profile (권장)"
    echo "  2) 화면에 출력만 (직접 복사)"
    echo "  3) 저장 안 함"
    echo ""
    echo -n "선택 (1/2/3): "

    local choice
    if [ -e /dev/tty ]; then
        read -r choice </dev/tty
    else
        read -r choice
    fi

    case "$choice" in
        1)
            echo "" >> "$shell_profile"
            echo "# NDS Skills Environment Variables (added by installer)" >> "$shell_profile"
            for var in "${ENV_VARS_ADDED[@]}"; do
                echo "$var" >> "$shell_profile"
            done
            echo "" >> "$shell_profile"
            success "환경변수가 $shell_profile 에 저장되었습니다"
            info "적용하려면 실행: source $shell_profile"
            ;;
        2)
            echo ""
            echo -e "${CYAN}아래 내용을 쉘 프로필에 추가하세요:${NC}"
            echo ""
            echo "# NDS Skills Environment Variables"
            for var in "${ENV_VARS_ADDED[@]}"; do
                echo "$var"
            done
            echo ""
            ;;
        *)
            info "환경변수 저장을 건너뛰었습니다"
            ;;
    esac
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

    # Check and install Python (don't fail if Python unavailable)
    check_and_install_python || true

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
            # No TTY available (piped input), try to read from /dev/tty
            if [ -e /dev/tty ]; then
                echo "Available coding agents:"
                echo "  1) Claude Code  (~/.claude/skills)"
                echo "  2) Cursor       (~/.claude/skills)"
                echo "  3) Codex CLI    (~/.codex/skills)"
                echo "  4) Gemini CLI   (~/.gemini/skills)"
                echo "  5) Antigravity  (~/.gemini/antigravity/global_skills)"
                echo "  6) Copilot      (~/.claude/skills)"
                echo ""
                echo -n "Enter numbers separated by space (e.g., '1 3 4') or 'all': "
                read -r selection </dev/tty

                if [ "$selection" = "all" ]; then
                    SELECTED_AGENTS="claude cursor codex gemini antigravity copilot"
                else
                    for num in $selection; do
                        case $num in
                            1) SELECTED_AGENTS="$SELECTED_AGENTS claude" ;;
                            2) SELECTED_AGENTS="$SELECTED_AGENTS cursor" ;;
                            3) SELECTED_AGENTS="$SELECTED_AGENTS codex" ;;
                            4) SELECTED_AGENTS="$SELECTED_AGENTS gemini" ;;
                            5) SELECTED_AGENTS="$SELECTED_AGENTS antigravity" ;;
                            6) SELECTED_AGENTS="$SELECTED_AGENTS copilot" ;;
                        esac
                    done
                fi

                if [ -z "$SELECTED_AGENTS" ]; then
                    warn "No agents selected"
                    exit 0
                fi
            else
                # No TTY at all, default to all agents
                info "No interactive terminal available, installing to all agents"
                SELECTED_AGENTS="claude cursor codex gemini antigravity copilot"
            fi
        fi
    fi

    # Default to all if still no agents selected
    if [ -z "$SELECTED_AGENTS" ]; then
        SELECTED_AGENTS="claude cursor codex gemini antigravity copilot"
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
    info "Source: ${NEXUS_BASE_URL}"
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

    success "Skills installation complete!"
    echo -e "${CYAN}================================${NC}"
    echo ""

    # Install Python dependencies
    install_python_dependencies

    # Configure environment variables
    configure_environment_variables

    echo ""
    echo "Next steps:"
    echo "  1. Restart your coding agent"
    echo "  2. Source your shell profile: source ~/.zshrc (or ~/.bashrc)"
    if [ -n "$PYTHON_CMD" ]; then
        echo "  3. Python dependencies have been installed for skills"
    fi
    echo ""
}

main "$@"
