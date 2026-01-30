#!/bin/bash
# build-openwork-installer.sh - 로컬 opencode + openwork를 빌드해 macOS DMG 설치 파일을 생성합니다.

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
  cat <<'EOF'
사용법: ./scripts/build-openwork-installer.sh [옵션]

로컬 소스(opencode + openwork)를 빌드하고, opencode 바이너리를 OpenWork(Tauri) sidecar로 포함해
단일 설치 파일(DMG)을 생성합니다.

옵션:
  --target <triple>          Tauri/Rust target triple (기본값: 현재 머신)
                             예) aarch64-apple-darwin, x86_64-apple-darwin
  --bundles <list>           Tauri bundles (기본값: dmg,app)
                             예) dmg,app
  --baseline                 opencode baseline 빌드 포함(가능 시 baseline 바이너리 우선 사용)
  --opencode-bin <path>      opencode 바이너리 경로를 직접 지정(이 경우 opencode 빌드를 건너뜀)
  --dmg-skip-jenkins         DMG 생성 시 Finder/AppleScript 단계를 건너뜀(헤드리스/권한 제한 환경용)
  --with-updater-artifacts   createUpdaterArtifacts=true 유지(기본은 false로 덮어써 빌드)
  --updater-base-url <url>   OpenWork Updater latest.json 호스팅 base URL
                             예) https://repo.gabia.com/repository/raw-repository/nds/openwork-updater
                             설정 시 endpoints는 <base>/{{target}}/latest.json 으로 주입됩니다.
  --updater-pubkey <string>  Updater 서명 검증용 pubkey(공개키) 주입(1줄 문자열)
  --updater-pubkey-file <p>  pubkey를 파일에서 읽어 주입
  --no-frozen-lockfile       pnpm install 시 --frozen-lockfile 미사용
  -h, --help                 도움말 표시

예시:
  ./scripts/build-openwork-installer.sh
  ./scripts/build-openwork-installer.sh --baseline
  ./scripts/build-openwork-installer.sh --target x86_64-apple-darwin --opencode-bin /path/to/opencode
EOF
}

need_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo -e "${RED}오류: '$cmd' 명령을 찾을 수 없습니다.${NC}"
    exit 1
  fi
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

OPENWORK_DIR="$PROJECT_ROOT/openwork"
OPENCODE_DIR="$PROJECT_ROOT/opencode"
OPENCODE_PKG_DIR="$OPENCODE_DIR/packages/opencode"
OPENWORK_DESKTOP_DIR="$OPENWORK_DIR/packages/desktop"
OPENWORK_TAURI_CONF="$OPENWORK_DESKTOP_DIR/src-tauri/tauri.conf.json"
OPENWORK_SIDECARS_DIR="$OPENWORK_DESKTOP_DIR/src-tauri/sidecars"

TARGET=""
BUNDLES="dmg,app"
BASELINE=false
OPENCODE_BIN=""
DMG_SKIP_JENKINS=false
WITH_UPDATER_ARTIFACTS=false
FROZEN_LOCKFILE=true
UPDATER_BASE_URL="${OPENWORK_UPDATER_BASE_URL:-}"
UPDATER_PUBKEY="${OPENWORK_UPDATER_PUBKEY:-}"
UPDATER_PUBKEY_FILE="${OPENWORK_UPDATER_PUBKEY_FILE:-}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET="${2:-}"
      shift 2
      ;;
    --bundles)
      BUNDLES="${2:-}"
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
    --dmg-skip-jenkins)
      DMG_SKIP_JENKINS=true
      shift
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

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo -e "${RED}오류: 이 스크립트는 macOS에서만 실행 가능합니다.${NC}"
  exit 1
fi

if [[ -n "$UPDATER_PUBKEY_FILE" ]]; then
  if [[ ! -f "$UPDATER_PUBKEY_FILE" ]]; then
    echo -e "${RED}오류: updater pubkey 파일을 찾을 수 없습니다: $UPDATER_PUBKEY_FILE${NC}"
    exit 1
  fi
  UPDATER_PUBKEY="$(cat "$UPDATER_PUBKEY_FILE")"
fi

if [[ -n "$UPDATER_BASE_URL" ]]; then
  # trailing slash 제거
  UPDATER_BASE_URL="${UPDATER_BASE_URL%/}"
fi

if [[ -n "$UPDATER_PUBKEY" ]]; then
  # 개행 제거(키는 1줄 문자열로 기대)
  UPDATER_PUBKEY="$(printf '%s' "$UPDATER_PUBKEY" | tr -d '\r\n')"
fi

bundles_include() {
  local bundles_csv="$1"
  local needle="$2"
  # 쉼표로 구분된 list에서 정확히 일치하는 토큰만 찾습니다.
  echo ",${bundles_csv}," | grep -q ",${needle},"
}

bundles_remove() {
  local bundles_csv="$1"
  local remove="$2"
  echo "$bundles_csv" | tr ',' '\n' | grep -v "^${remove}$" | paste -sd, - | sed 's/^,$//; s/,$//'
}

if [[ ! -d "$OPENWORK_DIR" || ! -d "$OPENCODE_DIR" ]]; then
  echo -e "${RED}오류: submodule(openwork/opencode) 디렉토리를 찾을 수 없습니다.${NC}"
  echo -e "${YELLOW}힌트: git submodule update --init --recursive${NC}"
  exit 1
fi

host_arch="$(uname -m)"
case "$host_arch" in
  arm64)
    host_target="aarch64-apple-darwin"
    opencode_arch="arm64"
    ;;
  x86_64)
    host_target="x86_64-apple-darwin"
    opencode_arch="x64"
    ;;
  *)
    echo -e "${RED}오류: 지원하지 않는 아키텍처: $host_arch${NC}"
    exit 1
    ;;
esac

if [[ -z "$TARGET" ]]; then
  TARGET="$host_target"
fi

echo -e "${GREEN}=== OpenWork 설치 파일 빌드(macOS) ===${NC}"
echo "프로젝트 루트: $PROJECT_ROOT"
echo "타겟: $TARGET"
echo "번들: $BUNDLES"
echo ""

need_cmd bun
need_cmd pnpm
need_cmd node
need_cmd cargo

if [[ -z "$OPENCODE_BIN" ]]; then
  if [[ "$TARGET" != "$host_target" ]]; then
    echo -e "${RED}오류: 현재 머신($host_target)과 다른 타겟($TARGET)으로 opencode를 자동 빌드할 수 없습니다.${NC}"
    echo -e "${YELLOW}해결: --opencode-bin으로 해당 타겟 바이너리를 직접 지정하세요.${NC}"
    exit 1
  fi

  if [[ ! -d "$OPENCODE_PKG_DIR" ]]; then
    echo -e "${RED}오류: opencode 패키지 경로를 찾을 수 없습니다: $OPENCODE_PKG_DIR${NC}"
    exit 1
  fi

  echo -e "${GREEN}[1/3] opencode 빌드${NC}"
  pushd "$OPENCODE_PKG_DIR" >/dev/null
  bun install
  if [[ "$BASELINE" = true ]]; then
    bun run build --single --baseline
  else
    bun run build --single
  fi
  popd >/dev/null

  dist_root="$OPENCODE_PKG_DIR/dist"
  if [[ ! -d "$dist_root" ]]; then
    echo -e "${RED}오류: opencode dist 디렉토리를 찾을 수 없습니다: $dist_root${NC}"
    exit 1
  fi

  # baseline 옵션이 켜져 있으면 baseline 산출물을 우선 사용합니다.
  if [[ "$BASELINE" = true && "$opencode_arch" = "x64" && -f "$dist_root/opencode-darwin-x64-baseline/bin/opencode" ]]; then
    OPENCODE_BIN="$dist_root/opencode-darwin-x64-baseline/bin/opencode"
  elif [[ -f "$dist_root/opencode-darwin-$opencode_arch/bin/opencode" ]]; then
    OPENCODE_BIN="$dist_root/opencode-darwin-$opencode_arch/bin/opencode"
  else
    # 예상 경로가 없으면 dist 아래에서 첫 번째 후보를 탐색합니다.
    OPENCODE_BIN="$(find "$dist_root" -maxdepth 4 -type f -name opencode -perm -u+x 2>/dev/null | head -n 1 || true)"
  fi
fi

if [[ -z "$OPENCODE_BIN" || ! -f "$OPENCODE_BIN" ]]; then
  echo -e "${RED}오류: opencode 바이너리를 찾을 수 없습니다.${NC}"
  echo -e "${YELLOW}힌트: --opencode-bin /path/to/opencode${NC}"
  exit 1
fi

echo -e "${GREEN}[2/3] OpenWork sidecar 준비${NC}"
mkdir -p "$OPENWORK_SIDECARS_DIR"
sidecar_target_path="$OPENWORK_SIDECARS_DIR/opencode-$TARGET"
cp "$OPENCODE_BIN" "$sidecar_target_path"
chmod 755 "$sidecar_target_path"
echo "opencode sidecar: $sidecar_target_path"
echo ""

echo -e "${GREEN}[3/3] OpenWork(Tauri) 빌드${NC}"

if [[ ! -f "$OPENWORK_TAURI_CONF" ]]; then
  echo -e "${RED}오류: OpenWork tauri.conf.json을 찾을 수 없습니다: $OPENWORK_TAURI_CONF${NC}"
  exit 1
fi

tauri_conf_path="$OPENWORK_TAURI_CONF"
temp_conf=""
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

build_bundles="$BUNDLES"
if bundles_include "$build_bundles" "dmg"; then
  # 헤드리스 환경에선 DMG 단계가 실패할 수 있으므로, 요청이 있으면 app만 빌드하고 DMG는 별도 생성합니다.
  if [[ "$DMG_SKIP_JENKINS" = true ]]; then
    build_bundles="$(bundles_remove "$build_bundles" "dmg")"
    if [[ -z "$build_bundles" ]]; then
      build_bundles="app"
    fi
  fi
fi

pushd "$OPENWORK_DIR" >/dev/null
if [[ "$FROZEN_LOCKFILE" = true ]]; then
  pnpm install --frozen-lockfile
else
  pnpm install
fi

tauri_ok=true
if ! pnpm --filter @different-ai/openwork exec tauri build \
  --config "$tauri_conf_path" \
  --target "$TARGET" \
  --bundles "$build_bundles"; then
  tauri_ok=false
fi
popd >/dev/null

bundle_dir="$OPENWORK_DESKTOP_DIR/src-tauri/target/$TARGET/release/bundle"

create_dmg_fallback() {
  local app_path="$1"
  local dmg_out_path="$2"

  local volname="OpenWork"
  if [[ -f "$tauri_conf_path" ]]; then
    volname="$(node -e 'const fs=require("fs");const c=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));process.stdout.write(String(c.productName||"OpenWork"));' "$tauri_conf_path" 2>/dev/null || echo "OpenWork")"
  fi

  local stage_dir
  stage_dir="$(mktemp -d "${TMPDIR:-/tmp}/openwork-dmg-stage.XXXXXX")"
  cp -R "$app_path" "$stage_dir/"
  ln -s /Applications "$stage_dir/Applications"

  mkdir -p "$(dirname "$dmg_out_path")"
  rm -f "$dmg_out_path"

  echo -e "${YELLOW}DMG 번들이 실패했거나 건너뜁니다. hdiutil로 DMG를 생성합니다.${NC}"
  hdiutil create -fs HFS+ -format UDZO -volname "$volname" -srcfolder "$stage_dir" -ov -o "$dmg_out_path" >/dev/null
  rm -rf "$stage_dir"
}

if bundles_include "$BUNDLES" "dmg"; then
  app_path="$bundle_dir/macos/OpenWork.app"
  if [[ ! -d "$app_path" ]]; then
    # 일부 환경에선 앱 번들이 먼저 생기므로, tauri_ok가 false더라도 확인 후 시도합니다.
    app_path="$(find "$bundle_dir" -maxdepth 3 -type d -name "*.app" 2>/dev/null | head -n 1 || true)"
  fi

  if [[ "$DMG_SKIP_JENKINS" = true ]]; then
    if [[ -z "$app_path" || ! -d "$app_path" ]]; then
      echo -e "${RED}오류: DMG 생성을 위한 .app 번들을 찾을 수 없습니다.${NC}"
      exit 1
    fi

    version="0.0.0"
    if [[ -f "$tauri_conf_path" ]]; then
      version="$(node -e 'const fs=require("fs");const c=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));process.stdout.write(String(c.version||"0.0.0"));' "$tauri_conf_path" 2>/dev/null || echo "0.0.0")"
    fi
    arch_label="aarch64"
    case "$TARGET" in
      x86_64-apple-darwin) arch_label="x64" ;;
      aarch64-apple-darwin) arch_label="aarch64" ;;
    esac

    dmg_out="$bundle_dir/dmg/OpenWork_${version}_${arch_label}.dmg"
    create_dmg_fallback "$app_path" "$dmg_out"
    tauri_ok=true
  else
    # tauri build가 실패했고 DMG가 포함된 요청이었다면, headless 환경일 가능성이 높습니다.
    if [[ "$tauri_ok" = false ]]; then
      if [[ -z "$app_path" || ! -d "$app_path" ]]; then
        echo -e "${RED}오류: tauri build 실패 + .app 번들 미생성. 로그를 확인하세요.${NC}"
        exit 1
      fi

      version="0.0.0"
      if [[ -f "$tauri_conf_path" ]]; then
        version="$(node -e 'const fs=require("fs");const c=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));process.stdout.write(String(c.version||"0.0.0"));' "$tauri_conf_path" 2>/dev/null || echo "0.0.0")"
      fi
      arch_label="aarch64"
      case "$TARGET" in
        x86_64-apple-darwin) arch_label="x64" ;;
        aarch64-apple-darwin) arch_label="aarch64" ;;
      esac
      dmg_out="$bundle_dir/dmg/OpenWork_${version}_${arch_label}.dmg"
      create_dmg_fallback "$app_path" "$dmg_out"
      tauri_ok=true
    fi
  fi
fi

if [[ -n "$temp_conf" && -f "$temp_conf" ]]; then
  rm -f "$temp_conf"
fi

if [[ -d "$OPENWORK_DIR/packages" ]]; then
  # bun 빌드 과정에서 submodule 디렉토리에 생성되는 임시 파일로 인해 `git status`가 더러워지는 것을 방지합니다.
  find "$OPENWORK_DIR/packages" -maxdepth 4 -type f -name "*.bun-build" -delete 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}✅ 완료!${NC}"

if [[ -d "$bundle_dir/macos/OpenWork.app" ]]; then
  echo "APP: $bundle_dir/macos/OpenWork.app"
else
  app_found="$(find "$bundle_dir" -maxdepth 3 -type d -name "*.app" 2>/dev/null | head -n 1 || true)"
  if [[ -n "$app_found" ]]; then
    echo "APP: $app_found"
  fi
fi

if [[ -d "$bundle_dir/dmg" ]]; then
  find "$bundle_dir/dmg" -maxdepth 1 -type f -name "*.dmg" -print 2>/dev/null || true
fi

if [[ "$tauri_ok" = false ]]; then
  echo -e "${RED}오류: tauri build가 실패했습니다. 로그를 확인하세요.${NC}"
  exit 1
fi
