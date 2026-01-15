#!/bin/bash
# setup-skills.sh - skills를 ~/.claude/skills로 복사하는 스크립트

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 스크립트 위치 기준 프로젝트 루트 찾기
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SKILLS_SRC="$PROJECT_ROOT/skills"
SKILLS_DEST="$HOME/.claude/skills"

echo -e "${GREEN}=== Skills 설정 스크립트 ===${NC}"
echo "소스: $SKILLS_SRC"
echo "대상: $SKILLS_DEST"
echo ""

# 소스 디렉토리 확인
if [ ! -d "$SKILLS_SRC" ]; then
    echo -e "${RED}오류: skills 디렉토리를 찾을 수 없습니다: $SKILLS_SRC${NC}"
    exit 1
fi

# 대상 디렉토리 생성
mkdir -p "$SKILLS_DEST"

# 옵션 파싱
FORCE=false
DRY_RUN=false
EXCLUDE_CACHE=true

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE=true
            shift
            ;;
        -n|--dry-run)
            DRY_RUN=true
            shift
            ;;
        --include-cache)
            EXCLUDE_CACHE=false
            shift
            ;;
        -h|--help)
            echo "사용법: $0 [옵션]"
            echo ""
            echo "옵션:"
            echo "  -f, --force       기존 파일 덮어쓰기"
            echo "  -n, --dry-run     실제 복사 없이 미리보기"
            echo "  --include-cache   __pycache__ 포함"
            echo "  -h, --help        도움말 표시"
            exit 0
            ;;
        *)
            echo -e "${RED}알 수 없는 옵션: $1${NC}"
            exit 1
            ;;
    esac
done

# rsync 옵션 구성
RSYNC_OPTS="-av"
if [ "$EXCLUDE_CACHE" = true ]; then
    RSYNC_OPTS="$RSYNC_OPTS --exclude='__pycache__' --exclude='*.pyc' --exclude='.DS_Store'"
fi
if [ "$DRY_RUN" = true ]; then
    RSYNC_OPTS="$RSYNC_OPTS --dry-run"
    echo -e "${YELLOW}[DRY-RUN 모드]${NC}"
fi

# workspace 디렉토리 제외 (작업 파일)
RSYNC_OPTS="$RSYNC_OPTS --exclude='workspace'"

echo "복사 시작..."
echo ""

# skills 디렉토리 내용 복사
eval rsync $RSYNC_OPTS "$SKILLS_SRC/" "$SKILLS_DEST/"

echo ""
if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY-RUN 완료. 실제 복사하려면 -n 옵션 없이 실행하세요.${NC}"
else
    echo -e "${GREEN}✅ Skills 복사 완료!${NC}"
    echo ""
    echo "설치된 skills:"
    ls -1 "$SKILLS_DEST" | grep -v "README.md" | sed 's/^/  - /'
fi
