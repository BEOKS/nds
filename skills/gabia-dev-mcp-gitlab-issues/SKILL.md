---
name: gabia-dev-mcp-gitlab-issues
description: GitLab REST API를 직접 호출해 이슈 생성/조회/수정/삭제, 토론 조회, 스레드 노트 추가/수정, 이슈 링크 관리를 자동화할 때 사용한다. MCP가 없어도 scripts/gitlab_issue_cli.py로 수행한다.
---

# GitLab Issues Automation

## 제공 기능

- 이슈 생성/목록 조회/상세 조회/수정/삭제
- 이슈 토론(Discussion) 조회
- 토론 스레드 note 추가/수정
- 이슈 링크 조회/생성/삭제

## 사전 조건(환경변수)

- `GITLAB_TOKEN` (필수)
- (선택) `GITLAB_API_URL` (기본값: `https://gitlab.gabia.com/api/v4`)

## 기본 워크플로우

1. `python3 scripts/gitlab_issue_cli.py list`로 대상 이슈를 찾습니다(프로젝트 한정 또는 전체).
2. `get`으로 이슈 본문/메타를 확인합니다.
3. 상태/담당자/라벨/본문 변경은 `update`를 사용합니다.
4. 토론 확인은 `discussions`를 사용합니다.
5. note는 “기존 discussion(thread)”에만 붙일 수 있으므로 `create-note`/`update-note` 전에 discussion_id/note_id를 먼저 확보합니다.
6. 이슈 관계는 `list-links` / `create-link` / `delete-link`로 관리합니다.

## 도구별 사용 팁

- `--project-id`는 숫자 ID 또는 `group/project` 경로 모두 가능합니다.
- `update`로 닫기/열기: `--state-event close|reopen`
- note 추가/수정은 discussion_id/note_id가 필요합니다.
- `list`에서 부족한 필터는 `--param key=value`로 추가합니다.

## 예시

### 이슈 목록 조회(프로젝트 내, 라벨 필터)

```bash
python3 scripts/gitlab_issue_cli.py list \
  --project-id group/project \
  --state opened \
  --labels bug \
  --labels P1 \
  --per-page 20
```

### 이슈 상세 조회

```bash
python3 scripts/gitlab_issue_cli.py get \
  --project-id group/project \
  --issue-iid 456
```

### 이슈 업데이트(라벨 추가 + 닫기)

```bash
python3 scripts/gitlab_issue_cli.py update \
  --project-id group/project \
  --issue-iid 456 \
  --labels bug \
  --labels fixed \
  --state-event close
```

### 토론 조회 → 특정 스레드에 노트 추가

```bash
python3 scripts/gitlab_issue_cli.py discussions \
  --project-id group/project \
  --issue-iid 456 \
  --per-page 100
```

```bash
python3 scripts/gitlab_issue_cli.py create-note \
  --project-id group/project \
  --issue-iid 456 \
  --discussion-id DISCUSSION_ID_FROM_LIST \
  --body '확인했습니다. 재현 로그를 첨부합니다.'
```
