#!/usr/bin/env bash
#
# install.sh 테스트용 Docker 샌드박스
#
# 사용법:
#   ./test-sandbox.sh          # 인터랙티브 쉘 진입
#   ./test-sandbox.sh auto     # 자동 검증 모드
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE_NAME="nds-test-sandbox"

# Dockerfile 생성 (임시)
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

cat > "$TEMP_DIR/Dockerfile" << 'DOCKERFILE'
FROM alpine:3.20
RUN apk add --no-cache bash curl unzip coreutils ncurses
RUN adduser -D testuser
USER testuser
WORKDIR /home/testuser
DOCKERFILE

echo "[1/2] Docker 이미지 빌드 중..."
docker build -t "$IMAGE_NAME" "$TEMP_DIR" -q > /dev/null

if [ "$1" = "auto" ]; then
    echo "[2/2] 자동 검증 모드 실행..."
    echo ""
    docker run --rm \
        -v "$SCRIPT_DIR/install.sh:/tmp/install.sh:ro" \
        "$IMAGE_NAME" \
        bash -c '
echo "========================================="
echo "  NDS install.sh 자동 검증"
echo "========================================="
echo ""

echo "[TEST 1] 환경변수 없는 깨끗한 환경 확인"
VARS=$(env | grep -cE "CONFLUENCE|GITLAB|MATTERMOST|FIGMA|SENTRY|LDAP|HIWORKS|ORACLE|MYSQL" || true)
if [ "$VARS" = "0" ] || [ -z "$VARS" ]; then
    echo "  ✅ PASS: 관련 환경변수 없음"
else
    echo "  ❌ FAIL: 환경변수가 존재함 ($VARS개)"
fi
echo ""

echo "[TEST 2] --help 실행"
if bash /tmp/install.sh --help > /dev/null 2>&1; then
    echo "  ✅ PASS: --help 정상"
else
    echo "  ❌ FAIL: --help 에러"
fi
echo ""

echo "[TEST 3] --list 실행"
if bash /tmp/install.sh --list > /dev/null 2>&1; then
    echo "  ✅ PASS: --list 정상"
else
    echo "  ❌ FAIL: --list 에러"
fi
echo ""

echo "[TEST 4] configure_environment_variables 함수에 새 환경변수 포함 확인"
MISSING=""
for var in CONFLUENCE_BASE_URL SENTRY_TOKEN LDAP_USER LDAP_PWD HIWORKS_ID HIWORKS_DOMAIN HIWORKS_PWD; do
    if grep -q "$var" /tmp/install.sh; then
        echo "  ✅ $var 존재"
    else
        echo "  ❌ $var 누락"
        MISSING="$MISSING $var"
    fi
done
echo ""

if [ -z "$MISSING" ]; then
    echo "========================================="
    echo "  ✅ 모든 검증 통과"
    echo "========================================="
else
    echo "========================================="
    echo "  ❌ 누락된 변수:$MISSING"
    echo "========================================="
    exit 1
fi
'
else
    echo "[2/2] 인터랙티브 쉘 시작..."
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  깨끗한 샌드박스 환경 (alpine + bash)"
    echo "  환경변수: 없음"
    echo ""
    echo "  테스트 명령어:"
    echo "    bash /tmp/install.sh --claude"
    echo "    bash /tmp/install.sh --all"
    echo "    bash /tmp/install.sh --list"
    echo "    bash /tmp/install.sh --help"
    echo ""
    echo "  종료: exit"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    docker run --rm -it \
        -v "$SCRIPT_DIR/install.sh:/tmp/install.sh:ro" \
        "$IMAGE_NAME" \
        bash
fi
