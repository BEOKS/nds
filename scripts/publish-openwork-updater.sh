#!/usr/bin/env bash
# publish-openwork-updater.sh - OpenWork(Tauri) updater 산출물을 Nexus(raw-repository)에 업로드합니다.
#
# 요구사항:
# - curl, node
# - Nexus raw repository에 PUT 업로드 권한이 있는 계정
#
# 업로드 구조(기본):
#   <NEXUS_BASE_URL>/openwork-updater/<platform>/latest.json
#   <NEXUS_BASE_URL>/openwork-updater/<platform>/<update-file>
#   <NEXUS_BASE_URL>/openwork-updater/<platform>/<update-file>.sig (옵션)
#
# latest.json은 platforms.<platform>.url을 위 경로로 자동 치환합니다.

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

usage() {
  cat <<'EOF'
사용법: ./scripts/publish-openwork-updater.sh --bundle-dir <path> [옵션]

옵션:
  --bundle-dir <path>        tauri build 산출물 bundle 디렉토리 (필수)
  --latest-json <path>       latest.json 경로를 직접 지정(기본: bundle-dir 하위 검색)
  --nexus-base-url <url>     Nexus raw repository base URL
                             (기본: $NDS_NEXUS_URL 또는 https://repo.gabia.com/repository/raw-repository/nds)
  --dest-prefix <path>       업로드 prefix (기본: openwork-updater)
  --username <u>             Nexus 사용자명 (기본: $NDS_NEXUS_USERNAME 또는 $NEXUS_USERNAME)
  --password <p>             Nexus 비밀번호 (기본: $NDS_NEXUS_PASSWORD 또는 $NEXUS_PASSWORD)
  -n, --dry-run              실제 업로드 없이 업로드 대상만 출력
  -h, --help                 도움말

예시:
  ./scripts/publish-openwork-updater.sh \
    --bundle-dir ./openwork/packages/desktop/src-tauri/target/aarch64-apple-darwin/release/bundle \
    --username "$NDS_NEXUS_USERNAME" --password "$NDS_NEXUS_PASSWORD"
EOF
}

need_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo -e "${RED}오류: '$cmd' 명령을 찾을 수 없습니다.${NC}"
    exit 1
  fi
}

die() {
  echo -e "${RED}오류: $*${NC}"
  exit 1
}

warn() {
  echo -e "${YELLOW}[WARN]${NC} $*"
}

info() {
  echo -e "${GREEN}[INFO]${NC} $*"
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BUNDLE_DIR=""
LATEST_JSON=""
NEXUS_BASE_URL="${NDS_NEXUS_URL:-https://repo.gabia.com/repository/raw-repository/nds}"
DEST_PREFIX="openwork-updater"
NEXUS_USERNAME="${NDS_NEXUS_USERNAME:-${NEXUS_USERNAME:-}}"
NEXUS_PASSWORD="${NDS_NEXUS_PASSWORD:-${NEXUS_PASSWORD:-}}"
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bundle-dir)
      BUNDLE_DIR="${2:-}"
      shift 2
      ;;
    --latest-json)
      LATEST_JSON="${2:-}"
      shift 2
      ;;
    --nexus-base-url)
      NEXUS_BASE_URL="${2:-}"
      shift 2
      ;;
    --dest-prefix)
      DEST_PREFIX="${2:-}"
      shift 2
      ;;
    --username)
      NEXUS_USERNAME="${2:-}"
      shift 2
      ;;
    --password)
      NEXUS_PASSWORD="${2:-}"
      shift 2
      ;;
    -n|--dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "알 수 없는 옵션: $1"
      ;;
  esac
done

need_cmd curl
need_cmd node

[[ -n "$BUNDLE_DIR" ]] || die "--bundle-dir는 필수입니다."
[[ -d "$BUNDLE_DIR" ]] || die "bundle 디렉토리를 찾을 수 없습니다: $BUNDLE_DIR"

NEXUS_BASE_URL="${NEXUS_BASE_URL%/}"
DEST_PREFIX="${DEST_PREFIX#/}"
DEST_PREFIX="${DEST_PREFIX%/}"

if [[ -z "$NEXUS_USERNAME" || -z "$NEXUS_PASSWORD" ]]; then
  die "Nexus 인증 정보가 필요합니다. (--username/--password 또는 NDS_NEXUS_USERNAME/NDS_NEXUS_PASSWORD)"
fi

if [[ -z "$LATEST_JSON" ]]; then
  mapfile -t candidates < <(find "$BUNDLE_DIR" -type f -name latest.json 2>/dev/null || true)
  if [[ "${#candidates[@]}" -eq 0 ]]; then
    die "bundle 하위에서 latest.json을 찾을 수 없습니다. --latest-json로 지정하세요."
  fi
  if [[ "${#candidates[@]}" -gt 1 ]]; then
    die "latest.json 후보가 여러 개입니다. --latest-json로 정확히 지정하세요.\n- ${candidates[*]}"
  fi
  LATEST_JSON="${candidates[0]}"
fi

[[ -f "$LATEST_JSON" ]] || die "latest.json을 찾을 수 없습니다: $LATEST_JSON"

tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/openwork-updater-publish.XXXXXX")"
trap 'rm -rf "$tmp_dir"' EXIT

public_base_url="${NEXUS_BASE_URL}/${DEST_PREFIX}"
rewritten_latest="$tmp_dir/latest.json"

node "$SCRIPT_DIR/openwork-updater-rewrite-latest-json.js" \
  --in "$LATEST_JSON" \
  --out "$rewritten_latest" \
  --bundle-dir "$BUNDLE_DIR" \
  --public-base-url "$public_base_url"

# platforms 리스트: "<platform>\t<updateFileName>"
mapfile -t platform_lines < <(
  node -e '
    const fs=require("fs");
    const p=require("path");
    const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));
    const plats=j.platforms||{};
    for (const [k,v] of Object.entries(plats)) {
      const url=String((v||{}).url||"");
      const file=p.basename(url);
      if (!file) continue;
      console.log(`${k}\t${file}`);
    }
  ' "$rewritten_latest"
)

if [[ "${#platform_lines[@]}" -eq 0 ]]; then
  die "latest.json에서 platforms를 찾지 못했습니다: $LATEST_JSON"
fi

upload() {
  local src="$1"
  local dst_url="$2"

  if [[ "$DRY_RUN" = true ]]; then
    echo "DRY_RUN: $src -> $dst_url"
    return 0
  fi

  curl --fail --silent --show-error \
    -u "${NEXUS_USERNAME}:${NEXUS_PASSWORD}" \
    --upload-file "$src" \
    "$dst_url" >/dev/null
}

info "업로드 시작"
info "bundle: $BUNDLE_DIR"
info "latest.json: $LATEST_JSON"
info "public base: $public_base_url"

for line in "${platform_lines[@]}"; do
  platform="${line%%$'\t'*}"
  update_file="${line#*$'\t'}"

  [[ -n "$platform" ]] || continue
  [[ -n "$update_file" ]] || continue

  update_src="$(find "$BUNDLE_DIR" -type f -name "$update_file" 2>/dev/null | head -n 1 || true)"
  if [[ -z "$update_src" || ! -f "$update_src" ]]; then
    die "업데이트 파일을 bundle에서 찾을 수 없습니다: $update_file"
  fi

  sig_name="${update_file}.sig"
  sig_src="$(find "$BUNDLE_DIR" -type f -name "$sig_name" 2>/dev/null | head -n 1 || true)"
  if [[ -z "$sig_src" ]]; then
    warn "signature 파일을 찾지 못했습니다(업로드는 생략): $sig_name"
  fi

  dest_dir="${public_base_url}/${platform}"
  dest_update="${dest_dir}/${update_file}"
  dest_latest="${dest_dir}/latest.json"

  info "platform: $platform"
  upload "$update_src" "$dest_update"

  if [[ -n "$sig_src" && -f "$sig_src" ]]; then
    upload "$sig_src" "${dest_dir}/${sig_name}"
  fi

  upload "$rewritten_latest" "$dest_latest"
  echo "OK: $dest_latest"
done

info "✅ 완료"

