---
name: gabia-dev-mcp-gitlab-merge-requests
description: GitLab REST API를 직접 호출해 MR 조회/변경사항/토론 수집 및 MR 생성/목록 조회를 자동화할 때 사용한다. MCP가 없어도 scripts/gitlab_mr_cli.py로 수행한다.
---

# GitLab Merge Requests Automation

## 제공 기능

- MR 상세 조회
- MR 변경사항(changes/diffs) 조회
- MR 토론/리뷰(discussions) 조회
- MR 생성
- MR 목록 조회(필터/페이지네이션)

## 사전 조건(환경변수)

- `GITLAB_TOKEN` (필수)
- (선택) `GITLAB_API_URL` (기본값: `https://gitlab.gabia.com/api/v4`)

## 기본 워크플로우

1. `python3 scripts/gitlab_mr_cli.py list`로 후보 MR을 찾습니다.
2. `get`으로 상세(설명/상태/작성자 등)를 가져옵니다.
3. `diffs`로 변경사항을 가져옵니다.
4. `discussions`로 리뷰/토론을 가져옵니다.
5. 새 MR 생성이 필요하면 `create`를 사용합니다.

## 도구별 사용 팁

- `--project-id`는 숫자 ID 또는 `group/project` 경로 모두 가능합니다.
- `get` / `diffs`는 `--merge-request-id` 또는 `--source-branch` 중 하나가 필요합니다.
- `list`는 `--labels`, `--state`, `--author-username` 등으로 범위를 줄이고, 부족한 필터는 `--param key=value`로 추가합니다.

## 예시

### MR 목록 조회(열린 MR)

```bash
python3 scripts/gitlab_mr_cli.py list \
  --project-id group/project \
  --state opened \
  --per-page 20
```

### MR 상세 + diff 조회

```bash
python3 scripts/gitlab_mr_cli.py get \
  --project-id group/project \
  --merge-request-id 123
```

```bash
python3 scripts/gitlab_mr_cli.py diffs \
  --project-id group/project \
  --merge-request-id 123 \
  --view inline
```

### MR 토론 조회

```bash
python3 scripts/gitlab_mr_cli.py discussions \
  --project-id group/project \
  --merge-request-id 123 \
  --per-page 100
```

### MR 생성

```bash
python3 scripts/gitlab_mr_cli.py create \
  --project-id group/project \
  --source-branch feature/my-change \
  --target-branch main \
  --title 'feat: 설명' \
  --draft \
  --description-file ./mr.md
```
