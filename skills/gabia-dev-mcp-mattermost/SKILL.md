---
name: gabia-dev-mcp-mattermost
description: Mattermost REST API와 Boards API를 직접 호출해 포스트/파일 검색, 팀/채널/사용자 조회, Boards 카드 URL 상세 조회를 자동화할 때 사용한다. MCP가 없어도 scripts/mattermost_cli.py로 수행한다.
---

# Mattermost Automation

## 제공 기능

- 포스트/파일 검색
- 팀/채널/사용자 목록 조회
- Boards 카드 URL 상세 조회(보드/카드/뷰/콘텐츠)

## 사전 조건(환경변수)

- `MATTERMOST_TOKEN` (필수)
- (선택) `MATTERMOST_API_URL` (기본값: `https://mattermost.gabia.com/api/v4`)
- (선택) `MATTERMOST_BOARDS_API_URL` (기본값: `https://mattermost.gabia.com/plugins/focalboard/api/v2`)

## 기본 워크플로우

1. `python3 scripts/mattermost_cli.py teams`로 팀 목록을 가져옵니다(팀 ID 확보).
2. 팀 범위 검색은 `search-posts` / `search-files`에 `--team-id`를 포함합니다.
3. 채널 탐색이 필요하면 `channels`를 사용합니다.
4. Boards 카드 정보는 `board-card --card-url ...`로 조회합니다.

## 예시

### 팀 목록 조회

```bash
python3 scripts/mattermost_cli.py teams --per-page 50
```

### 포스트 검색(팀 범위)

```bash
python3 scripts/mattermost_cli.py search-posts \
  --team-id TEAM_ID \
  --terms 'deploy failed' \
  --per-page 20
```

### 파일 검색(전체 또는 팀 범위)

```bash
python3 scripts/mattermost_cli.py search-files \
  --terms runbook \
  --per-page 20
```

### Boards 카드 URL로 상세 조회

```bash
python3 scripts/mattermost_cli.py board-card \
  --card-url "https://mattermost.example.com/boards/team/TEAM/BOARD/VIEW/CARD"
```
