---
name: gabia-dev-mcp-confluence
description: Confluence REST API를 직접 호출해 페이지 검색/조회/생성/수정/삭제/댓글을 자동화할 때 사용한다. MCP가 없어도 scripts/confluence_cli.py로 수행한다.
---

# Confluence Automation

## 제공 기능

- 페이지 검색(단순 텍스트 또는 CQL)
- 페이지 조회(page_id 또는 title+space_key)
- 페이지 생성/수정/삭제
- 댓글 추가
- **첨부파일 목록 조회**
- **첨부파일 다운로드** (개별 또는 전체)
- Markdown ↔ Confluence storage HTML(간이 변환)

## 사전 조건(환경변수)

- `CONFLUENCE_BASE_URL` (필수)
- 인증(아래 중 1개)
  - `ATLASSIAN_OAUTH_ACCESS_TOKEN`
  - `CONFLUENCE_USERNAME` + `CONFLUENCE_API_TOKEN`
  - `ATLASSIAN_EMAIL` + `ATLASSIAN_API_TOKEN`
- (선택) `CONFLUENCE_SPACES_FILTER`: 검색 결과를 특정 space로 제한(쉼표 구분)

## 기본 워크플로우(권장)

1. `scripts/confluence_cli.py search`로 관련 페이지를 찾습니다.
2. `scripts/confluence_cli.py get`로 본문을 가져옵니다.
   - 기본: HTML (렌더링된 결과)
   - `--output-format storage`: 원본 XML (매크로 포함)
   - `--output-format markdown`: Markdown 변환 (LLM 처리용)
3. 새 문서면 `create`, 기존 문서 수정이면 `update`를 사용합니다.
4. 변경 이력/추가 설명은 `comment`로 남깁니다.

## 사용법(스크립트)

- 검색
  - `python3 scripts/confluence_cli.py search --query "deployment guide" --limit 10`
  - `--spaces-filter ""`를 주면 space 필터를 강제로 해제합니다.
- 페이지 조회
  - `python3 scripts/confluence_cli.py get --page-id 123456` (기본: HTML)
  - `python3 scripts/confluence_cli.py get --page-id 123456 --output-format storage` (원본 XML, 매크로 포함)
  - `python3 scripts/confluence_cli.py get --page-id 123456 --output-format markdown` (Markdown 변환)
  - 또는 `python3 scripts/confluence_cli.py get --space-key DEV --title "문서 제목"`
- 페이지 생성/수정/댓글
  - `--format` 기본은 `storage`(HTML)이며, 본문을 그대로 Confluence에 업로드합니다.
  - Markdown으로 작성하려면 `--format markdown`을 지정하면 스크립트가 HTML로 변환합니다.
- 첨부파일 목록 조회
  - `python3 scripts/confluence_cli.py attachments --page-id 123456`
- 첨부파일 다운로드
  - `python3 scripts/confluence_cli.py download --page-id 123456` (전체 다운로드)
  - `python3 scripts/confluence_cli.py download --page-id 123456 --filename "문서.pdf"` (특정 파일)
  - `python3 scripts/confluence_cli.py download --page-id 123456 -o ./downloads` (저장 경로 지정)

## 예시

### 검색 → 페이지 열기

```bash
python3 scripts/confluence_cli.py search \
  --query 'space = "DEV" AND title ~ "API*" ORDER BY lastmodified DESC' \
  --limit 5
```

```bash
# HTML로 조회 (기본값, 렌더링된 결과)
python3 scripts/confluence_cli.py get \
  --page-id 123456789 \
  --include-metadata

# Storage format으로 조회 (원본 XML, 매크로 코드 확인 가능)
python3 scripts/confluence_cli.py get \
  --page-id 123456789 \
  --output-format storage \
  --include-metadata

# Markdown으로 변환해서 조회
python3 scripts/confluence_cli.py get \
  --page-id 123456789 \
  --output-format markdown \
  --include-metadata
```

### 페이지 생성

```bash
# HTML로 생성 (기본값)
python3 scripts/confluence_cli.py create \
  --space DEV \
  --title '릴리즈 노트 - 2026-01-07' \
  --content '<h1>릴리즈 노트</h1><p>본문 내용</p>'

# Markdown 파일로 생성
python3 scripts/confluence_cli.py create \
  --space DEV \
  --title '릴리즈 노트 - 2026-01-07' \
  --format markdown \
  --content-file ./release-note.md
```

### 페이지 수정 + 댓글 남기기

```bash
python3 scripts/confluence_cli.py update \
  --page-id 123456789 \
  --title '릴리즈 노트 - 2026-01-07' \
  --version-comment '자동 업데이트: MR 요약 반영' \
  --content-file ./release-note.md
```

```bash
python3 scripts/confluence_cli.py comment \
  --page-id 123456789 \
  --format markdown \
  --content '변경 요약: 배포 후 모니터링 항목을 추가했습니다.'
```

### 첨부파일 조회 및 다운로드

```bash
# 첨부파일 목록 조회
python3 scripts/confluence_cli.py attachments \
  --page-id 123456789

# 출력 예시:
# [{"id": "att123", "title": "guide.pdf", "mediaType": "application/pdf", "fileSize": 1234567, ...}]
```

```bash
# 모든 첨부파일 다운로드 (현재 디렉토리)
python3 scripts/confluence_cli.py download \
  --page-id 123456789

# 특정 파일만 다운로드
python3 scripts/confluence_cli.py download \
  --page-id 123456789 \
  --filename "가이드문서.pdf"

# 지정 경로에 다운로드 (기존 파일 덮어쓰기)
python3 scripts/confluence_cli.py download \
  --page-id 123456789 \
  --output-dir ./attachments \
  --overwrite
```
