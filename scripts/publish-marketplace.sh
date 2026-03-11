#!/usr/bin/env bash
#
# NDS Marketplace Publisher
#
# Nexus(repo.gabia.com)에 마켓플레이스와 플러그인을 배포합니다.
#
# 사전 준비:
#   1. Nexus npm-hosted 레포지토리 생성 (https://repo.gabia.com)
#   2. npm 인증 설정:
#      npm login --registry=https://repo.gabia.com/repository/npm-hosted/
#
# 사용법:
#   ./scripts/publish-marketplace.sh
#   ./scripts/publish-marketplace.sh --bump patch|minor|major
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLUGIN_DIR="$PROJECT_ROOT/plugins/nds-skills"
MARKETPLACE_JSON="$PROJECT_ROOT/.claude-plugin/marketplace.json"
NEXUS_RAW_URL="${NDS_NEXUS_URL:-https://repo.gabia.com/repository/raw-repository/nds}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}[OK]${NC} $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ============================================================================
# Parse arguments
# ============================================================================
BUMP_TYPE=""
while [ $# -gt 0 ]; do
    case $1 in
        --bump)
            BUMP_TYPE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--bump patch|minor|major]"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ============================================================================
# Resolve symlink: copy real skills into plugin dir for npm publish
# ============================================================================
prepare_plugin() {
    info "Preparing plugin directory..."

    # Remove existing symlink and copy real files
    if [ -L "$PLUGIN_DIR/skills" ]; then
        rm "$PLUGIN_DIR/skills"
        cp -R "$PROJECT_ROOT/skills" "$PLUGIN_DIR/skills"

        # Clean up unnecessary files
        find "$PLUGIN_DIR/skills" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find "$PLUGIN_DIR/skills" -name ".DS_Store" -delete 2>/dev/null || true
        rm -f "$PLUGIN_DIR/skills/manifest.txt" 2>/dev/null || true
        rm -rf "$PLUGIN_DIR/skills/.claude" 2>/dev/null || true

        success "Skills copied to plugin directory"
    elif [ -d "$PLUGIN_DIR/skills" ]; then
        info "Skills directory already exists (not a symlink)"
    else
        error "Skills directory not found"
        exit 1
    fi
}

# ============================================================================
# Restore symlink after publish
# ============================================================================
restore_symlink() {
    if [ -d "$PLUGIN_DIR/skills" ] && [ ! -L "$PLUGIN_DIR/skills" ]; then
        rm -rf "$PLUGIN_DIR/skills"
        cd "$PLUGIN_DIR" && ln -s ../../skills skills
        cd "$PROJECT_ROOT"
        info "Restored symlink"
    fi
}
trap restore_symlink EXIT

# ============================================================================
# Bump version
# ============================================================================
bump_version() {
    if [ -n "$BUMP_TYPE" ]; then
        info "Bumping version: $BUMP_TYPE"
        cd "$PLUGIN_DIR"
        npm version "$BUMP_TYPE" --no-git-tag-version
        local new_version
        new_version=$(node -p "require('./package.json').version")
        cd "$PROJECT_ROOT"

        # Update plugin.json version
        local plugin_json="$PLUGIN_DIR/.claude-plugin/plugin.json"
        if command -v jq >/dev/null 2>&1; then
            jq --arg v "$new_version" '.version = $v' "$plugin_json" > "${plugin_json}.tmp" && mv "${plugin_json}.tmp" "$plugin_json"
        else
            sed -i.bak "s/\"version\": \"[^\"]*\"/\"version\": \"$new_version\"/" "$plugin_json"
            rm -f "${plugin_json}.bak"
        fi

        # Update marketplace.json version
        if command -v jq >/dev/null 2>&1; then
            jq --arg v "$new_version" '.plugins[0].version = $v' "$MARKETPLACE_JSON" > "${MARKETPLACE_JSON}.tmp" && mv "${MARKETPLACE_JSON}.tmp" "$MARKETPLACE_JSON"
        else
            sed -i.bak "s/\"version\": \"[^\"]*\"/\"version\": \"$new_version\"/" "$MARKETPLACE_JSON"
            rm -f "${MARKETPLACE_JSON}.bak"
        fi

        success "Version bumped to $new_version"
    fi
}

# ============================================================================
# Publish npm package
# ============================================================================
publish_npm() {
    info "Publishing npm package to Nexus..."
    cd "$PLUGIN_DIR"
    npm publish
    cd "$PROJECT_ROOT"
    success "npm package published"
}

# ============================================================================
# Upload marketplace.json to Nexus raw repository
# ============================================================================
upload_marketplace_json() {
    info "Uploading marketplace.json to Nexus raw repository..."

    local target_url="${NEXUS_RAW_URL}/marketplace.json"

    if [ -n "${NEXUS_USER:-}" ] && [ -n "${NEXUS_PASSWORD:-}" ]; then
        curl -fsSL -u "${NEXUS_USER}:${NEXUS_PASSWORD}" \
            --upload-file "$MARKETPLACE_JSON" \
            "$target_url"
    else
        warn "NEXUS_USER and NEXUS_PASSWORD not set, skipping raw upload"
        warn "Upload manually: curl -u user:pass --upload-file $MARKETPLACE_JSON $target_url"
        return 0
    fi

    success "marketplace.json uploaded to $target_url"
}

# ============================================================================
# Main
# ============================================================================
main() {
    echo ""
    echo -e "${CYAN}================================${NC}"
    echo -e "${CYAN}   NDS Marketplace Publisher${NC}"
    echo -e "${CYAN}================================${NC}"
    echo ""

    bump_version
    prepare_plugin
    publish_npm
    upload_marketplace_json

    echo ""
    echo -e "${CYAN}================================${NC}"
    success "Marketplace published successfully!"
    echo -e "${CYAN}================================${NC}"
    echo ""
    echo "Users can now install with:"
    echo "  /plugin marketplace add ${NEXUS_RAW_URL}/marketplace.json"
    echo "  /plugin install nds-skills@nds-marketplace"
    echo ""
}

main "$@"
