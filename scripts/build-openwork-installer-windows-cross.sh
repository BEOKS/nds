#!/bin/bash
# build-openwork-installer-windows-cross.sh - macOS에서 Windows용 OpenWork NSIS 설치 파일을 크로스 컴파일합니다.
#
# 주의: MSI는 macOS에서 생성할 수 없습니다. NSIS(.exe 설치 파일)만 지원됩니다.
#
# 사전 요구사항 (처음 한 번만):
#   brew install nsis
#   rustup target add x86_64-pc-windows-msvc
#   cargo install --locked cargo-xwin

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

usage() {
  cat <<'EOF'
사용법: ./scripts/build-openwork-installer-windows-cross.sh [옵션]

macOS에서 Windows용 OpenWork NSIS 설치 파일(.exe)을 크로스 컴파일합니다.

옵션:
  --target <triple>          Rust target triple (기본값: x86_64-pc-windows-msvc)
  --baseline                 opencode baseline 빌드 사용
  --opencode-bin <path>      opencode Windows 바이너리 경로를 직접 지정
  --with-updater-artifacts   createUpdaterArtifacts=true 설정
  --updater-base-url <url>   Updater latest.json 호스팅 base URL
  --updater-pubkey <string>  Updater 서명 검증용 pubkey
  --updater-pubkey-file <p>  pubkey를 파일에서 읽기
  --no-frozen-lockfile       pnpm install 시 --frozen-lockfile 미사용
  --skip-prerequisites       사전 요구사항 검사 건너뛰기
  -h, --help                 도움말 표시

예시:
  # 기본 빌드
  ./scripts/build-openwork-installer-windows-cross.sh

  # 사전 요구사항 검사 건너뛰기
  ./scripts/build-openwork-installer-windows-cross.sh --skip-prerequisites

  # Updater 설정 포함
  ./scripts/build-openwork-installer-windows-cross.sh \
    --with-updater-artifacts \
    --updater-base-url "https://example.com/updates"

사전 요구사항 설치 (처음 한 번):
  brew install nsis
  rustup target add x86_64-pc-windows-msvc
  cargo install --locked cargo-xwin

  # 선택: Windows SDK 캐시 공유
  export XWIN_CACHE_DIR="$HOME/.cache/xwin"
EOF
}

need_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo -e "${RED}오류: '$cmd' 명령을 찾을 수 없습니다.${NC}"
    return 1
  fi
}

check_prerequisites() {
  echo -e "${CYAN}[사전 요구사항 검사]${NC}"
  local missing=()

  # 필수 명령어
  for cmd in bun pnpm node cargo makensis; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      missing+=("$cmd")
    fi
  done

  # cargo-xwin
  if ! cargo xwin --version >/dev/null 2>&1; then
    missing+=("cargo-xwin")
  fi

  # Windows Rust 타겟
  if ! rustup target list --installed | grep -q "x86_64-pc-windows-msvc"; then
    missing+=("rustup target x86_64-pc-windows-msvc")
  fi

  if [[ ${#missing[@]} -gt 0 ]]; then
    echo -e "${RED}오류: 다음 요구사항이 누락되었습니다:${NC}"
    for item in "${missing[@]}"; do
      echo "  - $item"
    done
    echo ""
    echo -e "${YELLOW}설치 방법:${NC}"
    echo "  brew install nsis"
    echo "  rustup target add x86_64-pc-windows-msvc"
    echo "  cargo install --locked cargo-xwin"
    exit 1
  fi

  echo -e "${GREEN}✓ 모든 사전 요구사항 충족${NC}"
  echo ""
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

OPENWORK_DIR="$PROJECT_ROOT/openwork"
OPENCODE_DIR="$PROJECT_ROOT/opencode"
OPENCODE_PKG_DIR="$OPENCODE_DIR/packages/opencode"
OPENWORK_DESKTOP_DIR="$OPENWORK_DIR/packages/desktop"
OPENWORK_TAURI_CONF="$OPENWORK_DESKTOP_DIR/src-tauri/tauri.conf.json"
OPENWORK_SIDECARS_DIR="$OPENWORK_DESKTOP_DIR/src-tauri/sidecars"

TARGET="x86_64-pc-windows-msvc"
BASELINE=false
OPENCODE_BIN=""
WITH_UPDATER_ARTIFACTS=false
FROZEN_LOCKFILE=true
SKIP_PREREQUISITES=false
UPDATER_BASE_URL="${OPENWORK_UPDATER_BASE_URL:-}"
UPDATER_PUBKEY="${OPENWORK_UPDATER_PUBKEY:-}"
UPDATER_PUBKEY_FILE="${OPENWORK_UPDATER_PUBKEY_FILE:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET="${2:-}"
      shift 2
      ;;
    --baseline)
      BASELINE=true
      shift
      ;;
    --opencode-bin)
      OPENCODE_BIN="${2:-}"
      shift 2
      ;;
    --with-updater-artifacts)
      WITH_UPDATER_ARTIFACTS=true
      shift
      ;;
    --updater-base-url)
      UPDATER_BASE_URL="${2:-}"
      shift 2
      ;;
    --updater-pubkey)
      UPDATER_PUBKEY="${2:-}"
      shift 2
      ;;
    --updater-pubkey-file)
      UPDATER_PUBKEY_FILE="${2:-}"
      shift 2
      ;;
    --no-frozen-lockfile)
      FROZEN_LOCKFILE=false
      shift
      ;;
    --skip-prerequisites)
      SKIP_PREREQUISITES=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo -e "${RED}알 수 없는 옵션: $1${NC}"
      usage
      exit 1
      ;;
  esac
done

# macOS 확인
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo -e "${RED}오류: 이 스크립트는 macOS에서만 실행 가능합니다.${NC}"
  exit 1
fi

# 사전 요구사항 검사
if [[ "$SKIP_PREREQUISITES" = false ]]; then
  check_prerequisites
fi

# Updater 설정 처리
if [[ -n "$UPDATER_PUBKEY_FILE" ]]; then
  if [[ ! -f "$UPDATER_PUBKEY_FILE" ]]; then
    echo -e "${RED}오류: updater pubkey 파일을 찾을 수 없습니다: $UPDATER_PUBKEY_FILE${NC}"
    exit 1
  fi
  UPDATER_PUBKEY="$(cat "$UPDATER_PUBKEY_FILE")"
fi

if [[ -n "$UPDATER_BASE_URL" ]]; then
  UPDATER_BASE_URL="${UPDATER_BASE_URL%/}"
fi

if [[ -n "$UPDATER_PUBKEY" ]]; then
  UPDATER_PUBKEY="$(printf '%s' "$UPDATER_PUBKEY" | tr -d '\r\n')"
fi

# submodule 확인
if [[ ! -d "$OPENWORK_DIR" || ! -d "$OPENCODE_DIR" ]]; then
  echo -e "${RED}오류: submodule(openwork/opencode) 디렉토리를 찾을 수 없습니다.${NC}"
  echo -e "${YELLOW}힌트: git submodule update --init --recursive${NC}"
  exit 1
fi

echo -e "${GREEN}=== OpenWork Windows 설치 파일 크로스 빌드 (macOS → Windows) ===${NC}"
echo "프로젝트 루트: $PROJECT_ROOT"
echo "타겟: $TARGET"
echo "번들: nsis (MSI는 macOS에서 지원되지 않음)"
echo ""

# ============================================================
# [1/3] opencode Windows 바이너리 빌드 (Bun 크로스 컴파일)
# ============================================================
if [[ -z "$OPENCODE_BIN" ]]; then
  echo -e "${GREEN}[1/3] opencode Windows 바이너리 빌드 (Bun 크로스 컴파일)${NC}"

  if [[ ! -d "$OPENCODE_PKG_DIR" ]]; then
    echo -e "${RED}오류: opencode 패키지 경로를 찾을 수 없습니다: $OPENCODE_PKG_DIR${NC}"
    exit 1
  fi

  pushd "$OPENCODE_PKG_DIR" >/dev/null

  # 의존성 설치
  bun install

  # Windows 타겟 빌드를 위해 --single 없이 전체 빌드 실행
  # (--single은 현재 플랫폼만 빌드하므로 Windows 바이너리가 생성되지 않음)
  echo -e "${CYAN}Windows 타겟 포함 전체 빌드 실행 중... (시간이 걸릴 수 있습니다)${NC}"
  if [[ "$BASELINE" = true ]]; then
    bun run build --baseline || {
      echo -e "${YELLOW}경고: --baseline 빌드 실패, 일반 빌드 시도${NC}"
      bun run build
    }
  else
    bun run build
  fi

  popd >/dev/null

  dist_root="$OPENCODE_PKG_DIR/dist"
  if [[ ! -d "$dist_root" ]]; then
    echo -e "${RED}오류: opencode dist 디렉토리를 찾을 수 없습니다: $dist_root${NC}"
    exit 1
  fi

  # Windows 바이너리 찾기
  if [[ "$BASELINE" = true && -f "$dist_root/opencode-windows-x64-baseline/bin/opencode.exe" ]]; then
    OPENCODE_BIN="$dist_root/opencode-windows-x64-baseline/bin/opencode.exe"
  elif [[ -f "$dist_root/opencode-windows-x64/bin/opencode.exe" ]]; then
    OPENCODE_BIN="$dist_root/opencode-windows-x64/bin/opencode.exe"
  else
    # 폴백: dist에서 Windows 바이너리 검색
    OPENCODE_BIN="$(find "$dist_root" -maxdepth 4 -type f -name "opencode.exe" 2>/dev/null | head -n 1 || true)"
  fi

  if [[ -z "$OPENCODE_BIN" || ! -f "$OPENCODE_BIN" ]]; then
    echo -e "${RED}오류: opencode Windows 바이너리를 찾을 수 없습니다.${NC}"
    echo -e "${YELLOW}힌트: --opencode-bin /path/to/opencode.exe${NC}"
    exit 1
  fi

  echo "opencode 바이너리: $OPENCODE_BIN"
else
  echo -e "${GREEN}[1/3] opencode 빌드 건너뛰기 (직접 지정됨)${NC}"
  echo "opencode 바이너리: $OPENCODE_BIN"
fi
echo ""

# ============================================================
# [2/3] OpenWork sidecar 준비 (모든 sidecar 크로스 빌드)
# ============================================================
echo -e "${GREEN}[2/3] OpenWork sidecar 준비 (Windows 타겟)${NC}"
mkdir -p "$OPENWORK_SIDECARS_DIR"

# opencode sidecar
sidecar_target_path="$OPENWORK_SIDECARS_DIR/opencode-$TARGET.exe"
cp "$OPENCODE_BIN" "$sidecar_target_path"
echo "opencode sidecar: $sidecar_target_path"

# openwork-server sidecar (Bun 크로스 컴파일)
echo -e "${CYAN}openwork-server 빌드 중...${NC}"
OPENWORK_SERVER_DIR="$OPENWORK_DIR/packages/server"
if [[ -d "$OPENWORK_SERVER_DIR" ]]; then
  pushd "$OPENWORK_SERVER_DIR" >/dev/null
  bun build --compile --target=bun-windows-x64 \
    --outfile "$OPENWORK_SIDECARS_DIR/openwork-server-$TARGET.exe" \
    ./src/index.ts 2>/dev/null || {
      # script/build.ts 사용 시도
      if [[ -f "./script/build.ts" ]]; then
        bun run ./script/build.ts --outdir "$OPENWORK_SIDECARS_DIR" --filename openwork-server --target bun-windows-x64
      elif [[ -f "./scripts/build.ts" ]]; then
        bun run ./scripts/build.ts --outdir "$OPENWORK_SIDECARS_DIR" --filename openwork-server --target bun-windows-x64
      fi
    }
  popd >/dev/null
  echo "openwork-server sidecar: $OPENWORK_SIDECARS_DIR/openwork-server-$TARGET.exe"
fi

# owpenbot sidecar (Bun 크로스 컴파일)
echo -e "${CYAN}owpenbot 빌드 중...${NC}"
OWPENBOT_DIR="$OPENWORK_DIR/packages/owpenbot"
if [[ -d "$OWPENBOT_DIR" ]]; then
  pushd "$OWPENBOT_DIR" >/dev/null
  if [[ -f "./script/build.ts" ]]; then
    bun run ./script/build.ts --outdir "$OPENWORK_SIDECARS_DIR" --filename owpenbot --target bun-windows-x64
  elif [[ -f "./scripts/build.ts" ]]; then
    bun run ./scripts/build.ts --outdir "$OPENWORK_SIDECARS_DIR" --filename owpenbot --target bun-windows-x64
  fi
  popd >/dev/null
  # Tauri는 타겟 트리플 이름을 사용하므로 파일명 변환
  if [[ -f "$OPENWORK_SIDECARS_DIR/owpenbot-bun-windows-x64.exe" ]]; then
    cp "$OPENWORK_SIDECARS_DIR/owpenbot-bun-windows-x64.exe" "$OPENWORK_SIDECARS_DIR/owpenbot-$TARGET.exe"
  fi
  echo "owpenbot sidecar: $OPENWORK_SIDECARS_DIR/owpenbot-$TARGET.exe"
fi

# openwrk sidecar (Bun 크로스 컴파일)
echo -e "${CYAN}openwrk 빌드 중...${NC}"
OPENWRK_DIR="$OPENWORK_DIR/packages/headless"
if [[ -d "$OPENWRK_DIR" && -f "$OPENWRK_DIR/src/cli.ts" ]]; then
  pushd "$OPENWRK_DIR" >/dev/null
  bun build --compile --target=bun-windows-x64 \
    --outfile "$OPENWORK_SIDECARS_DIR/openwrk-$TARGET.exe" \
    ./src/cli.ts 2>/dev/null || true
  popd >/dev/null
  echo "openwrk sidecar: $OPENWORK_SIDECARS_DIR/openwrk-$TARGET.exe"
fi

echo ""

# ============================================================
# [3/3] OpenWork(Tauri) 크로스 빌드 (cargo-xwin)
# ============================================================
echo -e "${GREEN}[3/3] OpenWork(Tauri) 크로스 빌드 (cargo-xwin → NSIS)${NC}"

if [[ ! -f "$OPENWORK_TAURI_CONF" ]]; then
  echo -e "${RED}오류: OpenWork tauri.conf.json을 찾을 수 없습니다: $OPENWORK_TAURI_CONF${NC}"
  exit 1
fi

# tauri.conf.json 임시 수정
temp_conf="$(mktemp "${TMPDIR:-/tmp}/openwork-tauri-conf.XXXXXX")"
node -e '
  const fs = require("fs");
  const src = process.argv[1];
  const dst = process.argv[2];
  const createUpdaterArtifacts = process.argv[3] === "true";
  const updaterBaseUrl = process.argv[4] || "";
  const updaterPubkey = process.argv[5] || "";

  const c = JSON.parse(fs.readFileSync(src, "utf8"));

  c.bundle = { ...(c.bundle || {}), createUpdaterArtifacts };

  // 크로스 컴파일 시 beforeBuildCommand를 UI 빌드만 수행하도록 변경
  // (sidecar는 이미 스크립트에서 준비됨)
  if (c.build) {
    c.build.beforeBuildCommand = "pnpm -w build:ui";
  }

  if (updaterBaseUrl) {
    c.plugins = c.plugins || {};
    c.plugins.updater = c.plugins.updater || {};
    c.plugins.updater.active = true;
    c.plugins.updater.endpoints = [`${updaterBaseUrl}/{{target}}/latest.json`];
  }

  if (updaterPubkey) {
    c.plugins = c.plugins || {};
    c.plugins.updater = c.plugins.updater || {};
    c.plugins.updater.pubkey = updaterPubkey;
  }

  fs.writeFileSync(dst, JSON.stringify(c, null, 2));
' "$OPENWORK_TAURI_CONF" "$temp_conf" "$WITH_UPDATER_ARTIFACTS" "$UPDATER_BASE_URL" "$UPDATER_PUBKEY"

tauri_conf_path="$temp_conf"

# pnpm 의존성 설치
pushd "$OPENWORK_DIR" >/dev/null

if [[ "$FROZEN_LOCKFILE" = true ]]; then
  pnpm install --frozen-lockfile
else
  pnpm install
fi

# cargo-xwin을 runner로 사용하여 크로스 컴파일
# 주의: NSIS만 지원됨 (MSI는 WiX 필요, Windows 전용)
echo ""
echo -e "${CYAN}cargo-xwin으로 Windows 타겟 크로스 컴파일 시작...${NC}"
echo -e "${YELLOW}(첫 실행 시 Windows SDK 다운로드로 시간이 걸릴 수 있습니다)${NC}"
echo ""

tauri_ok=true
# Tauri v2에서는 --bundles 옵션 대신 타겟에 맞는 번들이 자동 선택됨
# Windows 타겟 빌드 시 NSIS가 자동으로 생성됨
if ! pnpm --filter @different-ai/openwork exec tauri build \
  --runner cargo-xwin \
  --config "$tauri_conf_path" \
  --target "$TARGET"; then
  tauri_ok=false
fi

popd >/dev/null

# 임시 파일 정리
if [[ -n "$temp_conf" && -f "$temp_conf" ]]; then
  rm -f "$temp_conf"
fi

# bun 빌드 임시 파일 정리
if [[ -d "$OPENWORK_DIR/packages" ]]; then
  find "$OPENWORK_DIR/packages" -maxdepth 4 -type f -name "*.bun-build" -delete 2>/dev/null || true
fi

# ============================================================
# 결과 출력
# ============================================================
bundle_dir="$OPENWORK_DESKTOP_DIR/src-tauri/target/$TARGET/release/bundle"

echo ""
if [[ "$tauri_ok" = true ]]; then
  echo -e "${GREEN}✅ 완료!${NC}"
else
  echo -e "${RED}⚠️ 빌드 중 오류가 발생했습니다. 로그를 확인하세요.${NC}"
fi

echo ""
echo -e "${CYAN}생성된 설치 파일:${NC}"

if [[ -d "$bundle_dir/nsis" ]]; then
  find "$bundle_dir/nsis" -maxdepth 1 -type f \( -name "*.exe" -o -name "*.nsis" \) -print 2>/dev/null || true
else
  echo -e "${YELLOW}경고: NSIS 번들 디렉토리를 찾지 못했습니다: $bundle_dir/nsis${NC}"
fi

if [[ "$tauri_ok" = false ]]; then
  exit 1
fi
