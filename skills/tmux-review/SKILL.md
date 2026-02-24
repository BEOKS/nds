---
name: tmux-review
description: "GitLab MR URL을 받아 tmux 멀티 pane 환경에서 인터랙티브 코드 리뷰를 수행한다. 왼쪽 pane에서 claude가 리뷰를 진행하고, 오른쪽 위 lazygit으로 변경사항 확인, 오른쪽 아래 helix로 코드 탐색이 가능하다. /tmux-review MR-URL 형식으로 호출. 예: /tmux-review https://gitlab.gabia.com/gabia/idc/security-portal/-/merge_requests/762"
---

# Tmux Review

GitLab MR URL로부터 tmux 기반 인터랙티브 코드 리뷰 환경을 구성한다.

## Layout

```
┌──────────────────┬──────────────┐
│                  │   lazygit    │
│    claude        ├──────────────┤
│   (review)       │    hx .      │
│                  │              │
└──────────────────┴──────────────┘
```

## Workflow

```
1. MR URL 파싱 → host, project_path, mr_id 추출
2. GitLab MR CLI로 MR 정보 조회
3. Git 프로젝트 준비 (clone or fetch)
4. 리뷰 프롬프트 파일 생성
5. tmux-review.sh 실행 → 3-pane 환경 구성
```

## Phase 0: 의존성 확인

tmux 환경 구성에 필요한 도구가 설치되어 있는지 확인한다.

```bash
for cmd in tmux lazygit hx claude; do
  command -v "$cmd" >/dev/null 2>&1 || MISSING+=("$cmd")
done
```

누락된 도구가 있으면 사용자에게 설치를 권장하고, 승인 시 자동 설치 후 이어서 진행한다.

| 도구 | macOS 설치 |
|------|-----------|
| tmux | `brew install tmux` |
| lazygit | `brew install lazygit` |
| hx (helix) | `brew install helix` |
| claude | `npm install -g @anthropic-ai/claude-code` |

```
예: "lazygit, hx가 설치되어 있지 않습니다. 설치할까요?"
→ 승인 시: brew install lazygit helix 실행 후 Phase 1로 진행
→ 거부 시: 중단
```

## Phase 1: MR URL 파싱

인자로 받은 URL에서 정보를 추출한다.

URL 형식: `https://<host>/<project-path>/-/merge_requests/<mr-id>`

```
예: https://gitlab.gabia.com/gabia/idc/security-portal/-/merge_requests/762
→ host: gitlab.gabia.com
→ project_path: gabia/idc/security-portal
→ mr_id: 762
→ project_name: security-portal
```

URL이 `/-/merge_requests/` 패턴을 포함하지 않으면 올바른 MR URL을 입력하라고 안내한다.

## Phase 2: MR 정보 조회

`gabia-dev-mcp-gitlab-merge-requests` 스킬의 CLI를 사용한다.

```bash
# MR 상세 조회
python3 ~/.claude/skills/gabia-dev-mcp-gitlab-merge-requests/scripts/gitlab_mr_cli.py get \
  --project-id "<project_path>" \
  --merge-request-id <mr_id>
```

조회 실패 시 안내하고 중단. 성공 시 `title`, `description`, `source_branch`, `target_branch`, `web_url`, `author` 를 확보.

## Phase 3: Git 프로젝트 준비

작업 디렉토리: `~/.claude/tmux-review/`

```bash
PROJECT_DIR="$HOME/.claude/tmux-review/<project_name>"
```

디렉토리가 없으면 clone:

```bash
mkdir -p ~/.claude/tmux-review
git clone "https://<host>/<project_path>.git" "$PROJECT_DIR"
```

이미 있으면 fetch:

```bash
cd "$PROJECT_DIR" && git fetch --all --prune
```

### Worktree 생성

같은 프로젝트의 여러 MR을 동시에 리뷰할 수 있도록 worktree를 사용한다.

```bash
cd "$PROJECT_DIR"
mkdir -p .worktree

# 브랜치명의 /를 -로 치환한 디렉토리명
WORKTREE_DIR=".worktree/$(echo '<source_branch>' | tr '/' '-')"

# 이미 존재하면 삭제 후 재생성
if [ -d "$WORKTREE_DIR" ]; then
  git worktree remove "$WORKTREE_DIR" --force
fi

git worktree add "$WORKTREE_DIR" "origin/<source_branch>" --detach
cd "$WORKTREE_DIR"
git checkout -B "<source_branch>" "origin/<source_branch>"

REVIEW_DIR="$PROJECT_DIR/$WORKTREE_DIR"
```

이후 Phase 4~5에서 `PROJECT_DIR` 대신 `REVIEW_DIR`을 사용한다.

## Phase 4: 리뷰 프롬프트 생성

`/tmp/tmux-review-prompt-<mr_id>.md` 파일을 생성한다.

프롬프트에는 다음을 포함:
1. MR 정보 (URL, 제목, 작성자, 브랜치)
2. `references/review-rules.md` 의 리뷰 규칙 전문을 읽어서 삽입
3. 리뷰 지시사항

프롬프트 템플릿:

```
이 프로젝트의 GitLab MR을 리뷰해주세요.

## MR 정보
- URL: {web_url}
- 제목: {title}
- 작성자: {author}
- 브랜치: {source_branch} → {target_branch}
- 설명: {description}

## 리뷰 지시사항
1. `git diff {target_branch}...{source_branch}` 로 변경사항을 확인하세요
2. 변경된 파일을 읽고 코드 컨텍스트를 파악하세요
3. 프로젝트 구조를 파악하여 아키텍처 적합성을 검토하세요
4. 아래 리뷰 규칙에 따라 P-Level 형식으로 리뷰 결과를 출력하세요

## 리뷰 규칙
{references/review-rules.md 전체 내용}
```

## Phase 5: tmux 환경 구성

스크립트를 실행하여 tmux 레이아웃을 구성한다.

```bash
bash ~/.claude/skills/tmux-review/scripts/tmux-review.sh \
  "$REVIEW_DIR" \
  "${project_name}-review" \
  "/tmp/tmux-review-prompt-${mr_id}.md"
```

윈도우 이름은 `{project_name}-review` 형식.

스크립트 실행 후 사용자에게 안내:

```
tmux 리뷰 환경이 구성되었습니다.
- 왼쪽: claude가 MR 리뷰를 진행 중입니다
- 오른쪽 위: lazygit으로 변경사항을 확인할 수 있습니다
- 오른쪽 아래: helix로 코드를 탐색할 수 있습니다

tmux 윈도우 "{project_name}-review" 로 전환해주세요.
```
