#!/bin/bash
# 서브모듈 upstream remote 설정 스크립트
# 사용법: ./scripts/setup-submodule-remotes.sh

set -e

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

setup_remote() {
  local submodule="$1"
  local remote_name="$2"
  local remote_url="$3"
  local submodule_path="${REPO_ROOT}/${submodule}"

  if [ ! -d "$submodule_path" ]; then
    echo "[-] ${submodule} 디렉토리가 없습니다. git submodule update --init 을 먼저 실행하세요."
    return 1
  fi

  cd "$submodule_path"

  if git remote get-url "$remote_name" &>/dev/null; then
    echo "[=] ${submodule}: '${remote_name}' 리모트가 이미 존재합니다 ($(git remote get-url "$remote_name"))"
  else
    git remote add "$remote_name" "$remote_url"
    echo "[+] ${submodule}: '${remote_name}' -> ${remote_url} 추가 완료"
  fi
}

echo "=== 서브모듈 upstream remote 설정 ==="
echo ""

setup_remote "openwork" "upstream" "https://github.com/different-ai/openwork.git"
setup_remote "opencode" "upstream" "https://github.com/anomalyco/opencode.git"

echo ""
echo "완료."
