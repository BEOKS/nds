---
name: gitlab-review
description: "GitLab MR URL을 받아 코드를 clone/worktree 하고 P-Level(P1~P5) 기반 코드 리뷰를 수행한다. /gitlab-review MR-URL 형식으로 호출한다. 예: /gitlab-review https://gitlab.gabia.com/gabia/idc/security-portal/-/merge_requests/762"
---

# GitLab Code Review

GitLab MR URL로부터 코드 리뷰를 수행하는 워크플로우.

## 워크플로우

```
1. MR URL 파싱 → project_path, mr_id 추출
2. GitLab MR CLI로 MR 정보 + diff 조회
3. ~/.claude/gitlab-review/ 하위 git 프로젝트 확인/clone
4. .worktree/ 에 MR 소스 브랜치 worktree 추가
5. worktree 디렉토리에서 코드 리뷰 수행
6. P-Level 형식으로 리뷰 결과 제출 (자연어, GitLab 등록 금지)
7. worktree 삭제 여부 확인
```

## Phase 1: MR URL 파싱

인자로 받은 URL에서 정보를 추출한다.

URL 형식: `https://<host>/<project-path>/-/merge_requests/<mr-id>`

```
예: https://gitlab.gabia.com/gabia/idc/security-portal/-/merge_requests/762
→ host: gitlab.gabia.com
→ project_path: gabia/idc/security-portal
→ mr_id: 762
→ project_name: security-portal (마지막 세그먼트)
```

URL이 올바르지 않거나 `/-/merge_requests/` 패턴이 없으면 사용자에게 올바른 MR URL을 입력하라고 안내한다.

## Phase 2: MR 정보 조회

`gabia-dev-mcp-gitlab-merge-requests` 스킬의 CLI를 사용한다.

```bash
# MR 상세 조회
python3 ~/.claude/skills/gabia-dev-mcp-gitlab-merge-requests/scripts/gitlab_mr_cli.py get \
  --project-id "<project_path>" \
  --merge-request-id <mr_id>

# MR diff 조회
python3 ~/.claude/skills/gabia-dev-mcp-gitlab-merge-requests/scripts/gitlab_mr_cli.py diffs \
  --project-id "<project_path>" \
  --merge-request-id <mr_id> \
  --view inline
```

조회 실패 시 "올바른 MR URL을 입력해주세요"라고 안내하고 중단한다.

MR 정보에서 다음을 확인:
- `title`, `description`: MR 목적
- `source_branch`: worktree에 사용할 브랜치명
- `target_branch`: 비교 대상 브랜치
- `web_url`: 원본 MR 링크
- `author`: 작성자 정보

MR 정보를 요약하여 사용자에게 보여준 후 코드 리뷰를 진행한다.

## Phase 3: Git 프로젝트 준비

작업 디렉토리: `~/.claude/gitlab-review/`

### 3.1 프로젝트 디렉토리 확인

```bash
PROJECT_DIR="$HOME/.claude/gitlab-review/<project_name>"
```

디렉토리가 없으면 clone:

```bash
mkdir -p ~/.claude/gitlab-review
git clone "https://gitlab.gabia.com/<project_path>.git" "$PROJECT_DIR"
```

디렉토리가 이미 있으면 fetch:

```bash
cd "$PROJECT_DIR" && git fetch --all --prune
```

### 3.2 Worktree 생성

MR의 `source_branch`로 worktree를 추가한다.

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
```

## Phase 4: 코드 리뷰 수행

worktree 디렉토리에서 코드를 읽고 리뷰한다.

### 리뷰 범위

1. **MR diff 기반**: Phase 2에서 조회한 diff를 중심으로 리뷰
2. **코드 컨텍스트**: 변경된 파일의 전체 내용과 관련 파일을 읽어 맥락 파악
3. **프로젝트 구조**: 프로젝트 전체 구조를 파악하여 아키텍처 적합성 검토

### 리뷰 관점

- 기능 정확성: 의도한 대로 동작하는가
- 보안 취약점: SQL injection, XSS, 인증/인가 문제
- 성능: N+1 쿼리, 불필요한 연산, 메모리 누수
- 에러 처리: 예외 처리 누락, 에러 전파
- 코드 품질: 가독성, 네이밍, 중복 코드
- 아키텍처: 설계 원칙 준수, 의존성 방향
- 테스트: 테스트 누락, 엣지 케이스 미검증

## Phase 5: 리뷰 결과 제출

**절대 GitLab에 코멘트를 등록하지 않는다.** 사용자에게 자연어로 응답한다.

### P-Level 코드 리뷰 형식

```
## 코드 리뷰: <MR 제목>

**MR**: <web_url>
**작성자**: <author>
**브랜치**: <source_branch> → <target_branch>

---

### P1: 반드시 반영해야 함 (Critical)
> 기능적 오류, 데이터 무결성 결함, 보안 취약점 등 치명적 문제

- **[파일:라인]** 설명
  - 문제: ...
  - 제안: ...

### P2: 적극적으로 권장함 (Major)
> 아키텍처 결함, 성능 저하, 유지보수성을 크게 해치는 설계

- **[파일:라인]** 설명
  - 문제: ...
  - 제안: ...

### P3: 가급적 반영해 주세요 (Minor)
> 코드 스타일, 네이밍 개선, 간단한 리팩토링 제안

- **[파일:라인]** 설명
  - 제안: ...

### P4: 제안/의견 (Opinion)
> 개인적 견해, 대안 라이브러리/패턴 공유

- **[파일:라인]** 설명

### P5: 칭찬과 격려 (Praise)
> 좋은 코드, 꼼꼼한 처리에 대한 긍정적 피드백

- **[파일:라인]** 설명
```

해당 레벨에 코멘트가 없으면 해당 섹션은 "없음"으로 표기한다.

## Phase 6: Worktree 정리

리뷰 결과 제출 후 사용자에게 worktree 삭제 여부를 질문한다.

```
AskUserQuestion: "코드 리뷰가 완료되었습니다. worktree를 삭제할까요?"
```

- 삭제 승인 시:
  ```bash
  cd "$PROJECT_DIR" && git worktree remove "$WORKTREE_DIR" --force
  ```
- 삭제 거부 또는 추가 질문 시: 응답 후 **매번** worktree 삭제 여부를 다시 질문한다.

**중요**: 사용자가 리뷰 결과에 대해 추가 질문을 할 때마다 응답 후 반드시 worktree 삭제 여부를 재차 물어야 한다.
