---
name: git-worktree
description: "Git worktree 기반 독립 작업 환경 관리. wt 쉘 함수를 활용하여 worktree 생성, 목록 조회, swap, 삭제를 수행한다. 반드시 다음 상황에서 사용해야 한다: (1) 병렬 작업이 필요할 때 - 현재 브랜치와 독립적인 작업을 동시에 진행, (2) 독립된 작업이 필요할 때 - 현재 작업을 보존하면서 다른 브랜치에서 별도 작업 수행, (3) 브랜치 전환 없이 별도 피처/핫픽스 개발, (4) 에이전트가 여러 작업을 병렬로 처리할 때 작업 격리 보장, (5) worktree 관련 명령 실행 (wt list, wt add, wt swap, wt rm). 키워드: 병렬 작업, 독립 작업, worktree, 브랜치 격리, 동시 작업, parallel, isolated work."
---

# Git Worktree Manager

`wt` 쉘 함수를 활용한 git worktree 관리 및 독립 작업 환경 제공.

## 사전 조건 확인

스킬 사용 시 가장 먼저 `wt` 함수 등록 여부를 확인한다.

```bash
# 1. wt 함수 존재 확인
type wt 2>/dev/null
```

`wt not found`이면 `scripts/install_wt.sh`를 실행하여 등록한다:

```bash
bash /Users/leejs/.claude/skills/git-worktree/scripts/install_wt.sh
```

설치 후 현재 쉘에 즉시 로드:

```bash
source ~/.zshrc  # 또는 source ~/.bashrc
```

## 핵심 워크플로우

### 1. 독립 작업 시작

현재 브랜치를 유지하면서 새 브랜치에서 독립 작업:

```bash
# .worktree/ 디렉토리에 worktree 생성
wt add <branch-name>

# 예: feature/auth 브랜치 worktree 추가
wt add feature/auth
```

생성된 worktree 경로: `<git-root>/.worktree/<branch-name>`
(`/`는 `-`로 치환됨. 예: `feature/auth` → `.worktree/feature-auth`)

### 2. Worktree에서 작업 수행

Task 에이전트 또는 직접 명령으로 worktree 디렉토리에서 작업:

```bash
# worktree 경로에서 작업 실행
cd <git-root>/.worktree/<dir-name>
# ... 코드 수정, 커밋 등 ...
```

Task 에이전트 사용 시 worktree 절대 경로를 지정하여 독립성 보장.

### 3. 작업 완료 후 Swap

작업 완료 후 사용자에게 확인을 구한 뒤 메인 디렉토리로 swap:

```
AskUserQuestion: "worktree 작업이 완료되었습니다. 변경 내용을 확인하고 메인 디렉토리에 swap하시겠습니까?"
```

사용자가 승인하면:

```bash
wt swap <worktree-name>
```

swap 동작:
1. 대상 worktree를 git 목록에서 제거 (브랜치 잠금 해제)
2. 메인 디렉토리에서 대상 브랜치로 checkout
3. 이전 메인 브랜치를 `.worktree/`에 worktree로 재등록

### 4. 정리

불필요한 worktree 삭제:

```bash
wt rm <worktree-name>
```

## 명령어 레퍼런스

| 명령어 | 설명 |
|--------|------|
| `wt list` 또는 `wt ls` | 메인 브랜치와 모든 worktree 목록 표시 |
| `wt add <branch>` | 지정 브랜치의 worktree 생성 |
| `wt swap <name>` | 메인과 worktree 치환 (fzf 없이) |
| `wt swap` | fzf로 대화형 선택 후 치환 |
| `wt rm <name>` | worktree 삭제 |

## 에이전트 사용 규칙

### 병렬 작업 시

1. 각 작업마다 별도 worktree 생성 (`wt add`)
2. Task 에이전트에게 worktree 절대 경로 전달
3. 에이전트는 할당된 worktree 내에서만 파일 수정
4. 모든 작업 완료 후 사용자에게 결과 확인 질문
5. 승인 시 `wt swap`으로 메인에 반영

### 독립 작업 시

1. 현재 작업 상태 확인 (`git status`)
2. 새 worktree 생성 (`wt add <branch>`)
3. worktree에서 작업 수행
4. 작업 완료 후 사용자에게 swap 여부 확인
5. 필요 시 swap, 불필요한 worktree 정리

### .gitignore 설정 (필수)

`.worktree/` 디렉토리는 반드시 `.gitignore`에 등록해야 한다. worktree는 로컬 작업 환경이므로 원격 저장소에 포함되면 안 된다.

```bash
# .gitignore에 추가 확인
grep -q '\.worktree' .gitignore 2>/dev/null || echo '.worktree/' >> .gitignore
```

`wt add` 최초 실행 시 `.gitignore`에 `.worktree/` 항목이 없으면 자동 추가되지만, 수동으로 설정하는 경우에도 반드시 확인한다.

### 주의사항

- swap 전 uncommitted 변경사항은 commit 또는 stash 권장
- `.worktree/`는 `.gitignore`에 등록되어 있어야 함 (위 섹션 참고)
- 메인 디렉토리의 파일을 직접 수정하지 말고 반드시 worktree를 통해 작업
