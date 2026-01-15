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
2. `scripts/confluence_cli.py get`로 본문을 가져옵니다(LLM 처리 목적이면 `--convert-to-markdown` 권장).
3. 새 문서면 `create`, 기존 문서 수정이면 `update`를 사용합니다.
4. 변경 이력/추가 설명은 `comment`로 남깁니다.

## 사용법(스크립트)

- 검색
  - `python3 scripts/confluence_cli.py search --query "deployment guide" --limit 10`
  - `--spaces-filter ""`를 주면 space 필터를 강제로 해제합니다.
- 페이지 조회
  - `python3 scripts/confluence_cli.py get --page-id 123456 --convert-to-markdown`
  - 또는 `python3 scripts/confluence_cli.py get --space-key DEV --title "문서 제목"`
- 페이지 생성/수정/댓글
  - `--format` 기본은 `markdown`이며, 스크립트가 Confluence storage HTML로 변환해 업로드합니다.
  - 이미 storage/wiki 포맷을 갖고 있으면 `--format storage|wiki`로 그대로 전달합니다.

## 예시

### 검색 → 페이지 열기

```bash
python3 scripts/confluence_cli.py search \
  --query 'space = "DEV" AND title ~ "API*" ORDER BY lastmodified DESC' \
  --limit 5
```

```bash
python3 scripts/confluence_cli.py get \
  --page-id 123456789 \
  --convert-to-markdown \
  --include-metadata
```

### 페이지 생성

```bash
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
