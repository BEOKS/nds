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
NDS 스킬 설치기

사용법:
  curl -fsSL <url>/install.sh | bash
  curl -fsSL <url>/install.sh | bash -s -- [옵션]

옵션:
  --claude           Claude Code에 설치 (~/.claude/skills)
  --cursor           Cursor에 설치 (~/.claude/skills)
  --codex            Codex CLI에 설치 (~/.codex/skills)
  --gemini           Gemini CLI에 설치 (~/.gemini/skills)
  --antigravity      Antigravity에 설치 (~/.gemini/antigravity/global_skills)
  --copilot          GitHub Copilot에 설치 (~/.claude/skills)
  --all              모든 에이전트에 설치
  --list             사용 가능한 스킬 목록 출력 후 종료
  --skills "a,b,c"   지정한 스킬만 설치 (쉼표로 구분)
  --no-interactive   TUI 선택 건너뜀 (에이전트 플래그와 함께 사용)
  -h, --help         도움말 표시

환경변수:
  NDS_GITLAB_HOST    GitLab 호스트 (기본값: gitlab.gabia.com)
  NDS_GITLAB_PROJECT GitLab 프로젝트 경로 (기본값: nds/skills)
  NDS_BRANCH         사용할 브랜치 (기본값: main)

예시:
  # 대화형 모드 (TUI 선택)
  curl -fsSL <url>/install.sh | bash

  # 특정 에이전트에 설치
  curl -fsSL <url>/install.sh | bash -s -- --claude --codex

  # 모든 에이전트에 설치
  curl -fsSL <url>/install.sh | bash -s -- --all

  # Claude에 특정 스킬 설치
  curl -fsSL <url>/install.sh | bash -s -- --claude --skills "gabia-dev-mcp-oracle,pptx"

  # 사용 가능한 스킬 목록 확인
  curl -fsSL <url>/install.sh | bash -s -- --list
EOF
            exit 0
            ;;
        *)
            error "알 수 없는 옵션: $1"
            echo "--help를 사용하여 사용법을 확인하세요"
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
        error "필수 도구가 없습니다:$missing"
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
    info "macOS에서 Python 설치 시도 중..."

    # Check for Homebrew
    if command -v brew >/dev/null 2>&1; then
        info "Homebrew를 통해 Python 설치 중..."
        brew install python
        return $?
    fi

    # Check for MacPorts
    if command -v port >/dev/null 2>&1; then
        info "MacPorts를 통해 Python 설치 중..."
        sudo port install python311
        return $?
    fi

    # Fallback: Download from python.org
    warn "패키지 관리자를 찾을 수 없습니다. Python을 수동으로 설치하세요:"
    echo "  1. https://www.python.org/downloads/ 방문"
    echo "  2. Python 3.11 이상 버전 다운로드 및 설치"
    echo "  3. 이 설치기를 다시 실행하세요"
    return 1
}

install_python_linux() {
    info "Linux에서 Python 설치 시도 중..."

    # Detect package manager
    if command -v apt-get >/dev/null 2>&1; then
        info "apt를 통해 Python 설치 중..."
        sudo apt-get update
        sudo apt-get install -y python3 python3-pip python3-venv
        return $?
    elif command -v dnf >/dev/null 2>&1; then
        info "dnf를 통해 Python 설치 중..."
        sudo dnf install -y python3 python3-pip
        return $?
    elif command -v yum >/dev/null 2>&1; then
        info "yum을 통해 Python 설치 중..."
        sudo yum install -y python3 python3-pip
        return $?
    elif command -v pacman >/dev/null 2>&1; then
        info "pacman을 통해 Python 설치 중..."
        sudo pacman -S --noconfirm python python-pip
        return $?
    elif command -v apk >/dev/null 2>&1; then
        info "apk를 통해 Python 설치 중..."
        apk add --no-cache python3 py3-pip
        return $?
    elif command -v zypper >/dev/null 2>&1; then
        info "zypper를 통해 Python 설치 중..."
        sudo zypper install -y python3 python3-pip
        return $?
    fi

    warn "패키지 관리자를 감지할 수 없습니다. Python을 수동으로 설치하세요."
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
            warn "지원하지 않는 OS: $os_type"
            warn "Python 3.8+ 를 수동으로 설치하세요"
            return 1
            ;;
    esac
}

check_and_install_python() {
    echo ""
    echo -e "${CYAN}================================${NC}"
    echo -e "${CYAN}   Python 환경 설정${NC}"
    echo -e "${CYAN}================================${NC}"
    echo ""

    if detect_python; then
        local version
        version=$(get_python_version)
        success "Python 발견: $PYTHON_CMD (버전 $version)"

        if [ -z "$PIP_CMD" ]; then
            warn "pip을 찾을 수 없습니다. 설치 시도 중..."
            $PYTHON_CMD -m ensurepip --upgrade 2>/dev/null || true
            detect_python
        fi

        if [ -n "$PIP_CMD" ]; then
            success "pip 발견: $PIP_CMD"
        else
            warn "pip을 사용할 수 없습니다. Python 의존성이 설치되지 않습니다."
            return 1
        fi
        return 0
    fi

    warn "이 시스템에서 Python 3을 찾을 수 없습니다."
    echo ""
    echo "많은 NDS 스킬이 정상 작동하려면 Python이 필요합니다."
    echo ""
    echo -n "Python을 자동으로 설치하시겠습니까? (y/n): "

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
                    success "Python 설치 완료: $PYTHON_CMD"
                    return 0
                fi
            fi
            error "Python 설치 실패"
            return 1
            ;;
        *)
            warn "Python 설치를 건너뜁니다"
            SKIP_PYTHON=true
            return 1
            ;;
    esac
}

install_python_dependencies() {
    if [ "$SKIP_PYTHON" = true ]; then
        warn "Python 의존성 설치를 건너뜁니다"
        return 0
    fi

    echo ""
    info "Python 의존성 설치 중..."

    # Download requirements.txt from Nexus
    local req_url="${NEXUS_BASE_URL}/requirements.txt"
    local req_file="${TEMP_DIR:-/tmp}/nds-requirements.txt"

    if curl -fsSL "$req_url" -o "$req_file" 2>/dev/null; then
        info "Nexus에서 requirements.txt 다운로드 완료"
    else
        # Fallback: try GitLab
        req_url="https://${GITLAB_HOST}/${GITLAB_PROJECT}/-/raw/${BRANCH}/requirements.txt"
        if curl -fsSL "$req_url" -o "$req_file" 2>/dev/null; then
            info "GitLab에서 requirements.txt 다운로드 완료"
        else
            warn "requirements.txt를 다운로드할 수 없습니다"
            return 1
        fi
    fi

    # Install dependencies
    info "패키지 설치 중 (몇 분 소요될 수 있습니다)..."

    local pip_log="${TEMP_DIR:-/tmp}/nds-pip-install.log"
    local pip_exit_code=0

    # Try uv first (fastest, handles externally-managed-environment)
    if command -v uv &> /dev/null; then
        info "uv를 사용하여 설치 중..."
        uv pip install --system --break-system-packages -r "$req_file" > "$pip_log" 2>&1 || pip_exit_code=$?
    elif [ -n "$PIP_CMD" ]; then
        info "pip를 사용하여 설치 중..."
        # Try with --break-system-packages first (pip 23.0+, needed for PEP 668)
        if $PIP_CMD install --user --break-system-packages -r "$req_file" > "$pip_log" 2>&1; then
            pip_exit_code=0
        else
            # Fallback: try without --break-system-packages (older pip or non-PEP668 systems)
            info "--break-system-packages 없이 재시도 중..."
            $PIP_CMD install --user -r "$req_file" > "$pip_log" 2>&1 || pip_exit_code=$?
        fi
    else
        warn "패키지 관리자를 찾을 수 없습니다 (uv 또는 pip)."
        warn "uv 설치: curl -LsSf https://astral.sh/uv/install.sh | sh"
        return 1
    fi

    # Show relevant output
    if [ -f "$pip_log" ]; then
        while IFS= read -r line; do
            if echo "$line" | grep -qiE "installed|Installed"; then
                echo -e "${GREEN}[OK]${NC} $line"
            elif echo "$line" | grep -qi "error"; then
                echo -e "${RED}[ERROR]${NC} $line"
            fi
        done < "$pip_log"
        rm -f "$pip_log"
    fi

    if [ $pip_exit_code -eq 0 ]; then
        success "Python 의존성 설치 완료"
    else
        warn "일부 Python 의존성 설치에 실패했을 수 있습니다 (종료 코드: $pip_exit_code)"
        warn "나중에 수동으로 설치할 수 있습니다:"
        echo ""
        echo "  # 방법 1: uv 설치 (권장)"
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        echo "  uv pip install --system --break-system-packages -r requirements.txt"
        echo ""
        echo "  # 방법 2: pip 직접 사용"
        echo "  pip install --user --break-system-packages -r requirements.txt"
        return 1
    fi

    # Install optional dependencies (non-fatal)
    local opt_req_url="${NEXUS_BASE_URL}/requirements-optional.txt"
    local opt_req_file="${TEMP_DIR:-/tmp}/nds-requirements-optional.txt"
    local opt_downloaded=false

    if curl -fsSL "$opt_req_url" -o "$opt_req_file" 2>/dev/null; then
        opt_downloaded=true
    else
        opt_req_url="https://${GITLAB_HOST}/${GITLAB_PROJECT}/-/raw/${BRANCH}/requirements-optional.txt"
        if curl -fsSL "$opt_req_url" -o "$opt_req_file" 2>/dev/null; then
            opt_downloaded=true
        fi
    fi

    if [ "$opt_downloaded" = true ]; then
        info "선택적 의존성 설치 중 (mcp, anthropic)..."
        local opt_log="${TEMP_DIR:-/tmp}/nds-pip-optional.log"
        if command -v uv &> /dev/null; then
            uv pip install --system --break-system-packages -r "$opt_req_file" > "$opt_log" 2>&1 || true
        elif [ -n "$PIP_CMD" ]; then
            $PIP_CMD install --user --break-system-packages -r "$opt_req_file" > "$opt_log" 2>&1 || \
            $PIP_CMD install --user -r "$opt_req_file" > "$opt_log" 2>&1 || true
        fi
        if grep -qi "error" "$opt_log" 2>/dev/null; then
            warn "선택적 의존성 (mcp, anthropic)을 설치할 수 없습니다."
            warn "이는 mcp-builder 스킬에만 필요합니다 (Python 3.10+ 필요)."
        else
            success "선택적 의존성 설치 완료"
        fi
        rm -f "$opt_log"
    fi

    return 0
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
        echo -e "${CYAN}   NDS 스킬 설치기${NC}"
        echo -e "${CYAN}================================${NC}"
        echo ""
        echo -e "${BOLD}스킬을 설치할 코딩 에이전트를 선택하세요:${NC}"
        echo ""
        echo -e "${DIM}  [Space] 선택/해제  [Enter] 확인  [a] 전체 선택  [n] 전체 해제  [q] 종료${NC}"
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
                local key2 key3
                read -rsn1 -t 1 key2 || true
                read -rsn1 -t 1 key3 || true
                case "${key2}${key3}" in
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
                info "설치가 취소되었습니다"
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
    local manifest_url="${NEXUS_BASE_URL}/manifest.txt"

    # Try to fetch manifest from Nexus
    local manifest
    manifest=$(curl -fsSL "$manifest_url" 2>/dev/null || echo "")

    # Check if response is valid (not HTML and not empty)
    if [ -n "$manifest" ] && ! echo "$manifest" | head -1 | grep -q "<!DOCTYPE\|<html"; then
        echo "$manifest"
        return 0
    fi

    # No fallback - manifest.txt must be available from Nexus
    error "Nexus에서 manifest.txt 다운로드 실패"
    error "네트워크 연결을 확인하거나 관리자에게 문의하세요"
    return 1
}

# ============================================================================
# List skills
# ============================================================================
list_skills() {
    echo ""
    echo -e "${CYAN}사용 가능한 NDS 스킬:${NC}"
    echo "========================"
    get_skills_list | while IFS= read -r skill; do
        [ -z "$skill" ] && continue
        echo "  • $skill"
    done
    echo ""
    echo "총: $(get_skills_list | grep -c .)"
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

    info "Nexus에서 스킬 아카이브 다운로드 중..."

    if ! curl -fsSL "$archive_url" -o "$archive_file" 2>/dev/null; then
        error "Nexus에서 아카이브 다운로드 실패"
        error "URL: $archive_url"
        error "파일이 존재하고 접근 가능한지 확인하세요"
        return 1
    fi

    info "압축 해제 중..."

    # Extract zip file
    unzip -q "$archive_file" -d "$TEMP_DIR"

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

        local src_skill_dir="${TEMP_DIR}/${skill}"
        local src_skill_file="${TEMP_DIR}/${skill}.skill"
        local dest_skill_dir="${target_dir}/${skill}"
        local dest_skill_file="${target_dir}/${skill}.skill"

        # Check for directory-based skill
        if [ -d "$src_skill_dir" ]; then
            rm -rf "$dest_skill_dir"
            cp -R "$src_skill_dir" "$dest_skill_dir"

            # Remove __pycache__ directories
            find "$dest_skill_dir" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

            success "설치 완료: $skill"
            installed=$((installed + 1))
        # Check for .skill file
        elif [ -f "$src_skill_file" ]; then
            cp "$src_skill_file" "$dest_skill_file"
            success "설치 완료: ${skill}.skill"
            installed=$((installed + 1))
        else
            warn "찾을 수 없음: $skill"
            skipped=$((skipped + 1))
        fi
    done << EOF
$skills_to_install
EOF

    echo ""
    info "설치 완료: $installed개 스킬"
    [ $skipped -gt 0 ] && warn "건너뜀: $skipped개 스킬"

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
    info "${agent_name} (${skills_dir})에 설치 중..."

    # Create skills directory
    mkdir -p "$skills_dir"

    # Download and install
    if download_all_skills "$skills_dir"; then
        success "${agent_name} 설치 완료"
        return 0
    else
        error "${agent_name} 설치 실패"
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
        success "$var_name 이미 설정되어 있습니다"
        return 0
    fi

    echo ""
    echo -e "${YELLOW}▶ $var_name${NC}"
    echo "  $description"
    if [ -n "$token_url" ]; then
        echo -e "  ${DIM}토큰 생성: $token_url${NC}"
    fi

    local prompt_text="  값을 입력하세요"
    if [ "$is_optional" = "true" ]; then
        prompt_text="$prompt_text (건너뛰려면 Enter를 누르세요)"
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
            warn "건너뜀 $var_name"
            return 0
        else
            warn "건너뜀 $var_name (이 스킬에 필요합니다)"
            return 1
        fi
    fi

    # Add to shell profile
    ENV_VARS_ADDED+=("export $var_name=\"$value\"")
    success "설정 완료 $var_name"
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

    prompt_env_var "ATLASSIAN_OAUTH_ACCESS_TOKEN" \
        "Confluence 개인용 액세스 토큰 (Bearer 인증). confluence.gabia.com 사용 시 https://confluence.gabia.com/plugins/personalaccesstokens/usertokens.action 에서 발급한 토큰을 입력하세요." \
        "https://confluence.gabia.com/plugins/personalaccesstokens/usertokens.action" \
        "true"

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
        info "환경변수가 설정되지 않았습니다"
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
            # Remove existing NDS block if present
            if grep -q "# NDS Skills Environment Variables" "$shell_profile" 2>/dev/null; then
                sed -i.bak '/# NDS Skills Environment Variables/,/^$/d' "$shell_profile"
                rm -f "${shell_profile}.bak"
            fi
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
    echo -e "${CYAN}   NDS 스킬 설치기${NC}"
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
                warn "에이전트가 선택되지 않았습니다"
                exit 0
            fi
        else
            # No TTY available (piped input), try to read from /dev/tty
            if [ -e /dev/tty ]; then
                echo "사용 가능한 코딩 에이전트:"
                echo "  1) Claude Code  (~/.claude/skills)"
                echo "  2) Cursor       (~/.claude/skills)"
                echo "  3) Codex CLI    (~/.codex/skills)"
                echo "  4) Gemini CLI   (~/.gemini/skills)"
                echo "  5) Antigravity  (~/.gemini/antigravity/global_skills)"
                echo "  6) Copilot      (~/.claude/skills)"
                echo ""
                echo -n "번호를 공백으로 구분하여 입력하세요 (예: '1 3 4') 또는 'all': "
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
                    warn "에이전트가 선택되지 않았습니다"
                    exit 0
                fi
            else
                # No TTY at all, default to all agents
                info "대화형 터미널을 사용할 수 없어 모든 에이전트에 설치합니다"
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
    info "소스: ${NEXUS_BASE_URL}"
    echo ""
    info "선택된 에이전트:"
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
        error "설치가 오류와 함께 완료되었습니다"
        exit 1
    fi

    success "스킬 설치 완료!"
    echo -e "${CYAN}================================${NC}"
    echo ""

    # Install Python dependencies
    install_python_dependencies

    # Configure environment variables
    configure_environment_variables

    echo ""
    echo "다음 단계:"
    echo "  1. 코딩 에이전트를 재시작하세요"
    echo "  2. 쉘 프로필을 다시 로드하세요: source ~/.zshrc (또는 ~/.bashrc)"
    if [ -n "$PYTHON_CMD" ]; then
        echo "  3. 스킬에 필요한 Python 의존성이 설치되었습니다"
    fi
    echo ""
}

main "$@"
