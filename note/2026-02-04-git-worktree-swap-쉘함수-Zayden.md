# Git Worktree Swap 쉘 함수

> IDEA 프로젝트 경로를 고정한 채 worktree 브랜치를 치환하는 쉘 함수. `.worktree/` 하위에 브랜치별 worktree를 관리하고 `wt swap` 한 줄로 전환한다.

## 동작 원리

```
~/Project/nds/              ← IDEA가 항상 여는 경로 (고정)
~/Project/nds/.worktree/
    ├── develop/            ← develop 브랜치 worktree
    ├── feature-auth/       ← feature/auth 브랜치 worktree
    └── hotfix-login/       ← hotfix 브랜치 worktree
```

`wt swap develop` 실행 시:
1. 대상 worktree를 git 목록에서 제거 (브랜치 잠금 해제)
2. 메인 디렉토리에서 대상 브랜치로 checkout
3. 이전 메인 브랜치를 `.worktree/`에 worktree로 재등록
4. IDEA는 같은 경로를 보고 있으므로 자동 반영

## 사전 준비

```bash
# .gitignore에 .worktree/ 추가
echo ".worktree/" >> .gitignore

# fzf 설치 (선택사항 - wt swap에서 대화형 선택 가능)
brew install fzf
```

## 설치

아래 코드를 `~/.zshrc` 또는 `~/.bashrc` 끝에 추가한다.

```bash
# ============================================================
# Git Worktree Swap System
# 사용법:
#   wt list          - worktree 목록
#   wt add <branch>  - worktree 추가
#   wt swap <name>   - 메인과 worktree 치환
#   wt swap          - fzf로 선택하여 치환
#   wt rm <name>     - worktree 삭제
# ============================================================
wt() {
  local git_root
  git_root=$(git rev-parse --show-toplevel 2>/dev/null)
  if [ -z "$git_root" ]; then
    echo "Error: git 저장소가 아닙니다"
    return 1
  fi

  local wt_dir="${git_root}/.worktree"
  local cmd="${1:-list}"
  shift 2>/dev/null

  case "$cmd" in
    list|ls)
      echo "=== Main ==="
      git -C "$git_root" branch --show-current
      echo ""
      echo "=== Worktrees ==="
      if [ -d "$wt_dir" ]; then
        for d in "$wt_dir"/*/; do
          [ -d "$d" ] || continue
          local name=$(basename "$d")
          local branch=$(git -C "$d" branch --show-current 2>/dev/null || echo "?")
          echo "  $name ($branch)"
        done
      else
        echo "  (없음)"
      fi
      ;;

    add)
      local branch="$1"
      if [ -z "$branch" ]; then
        echo "Usage: wt add <branch-name>"
        return 1
      fi
      mkdir -p "$wt_dir"
      local dir_name="${branch//\//-}"
      git worktree add "${wt_dir}/${dir_name}" "$branch"
      ;;

    swap)
      local target="$1"

      if [ -z "$target" ]; then
        if ! command -v fzf &>/dev/null; then
          echo "Usage: wt swap <worktree-name>"
          echo "또는 fzf 설치: brew install fzf"
          wt list
          return 1
        fi
        target=$(ls -1 "$wt_dir" 2>/dev/null | fzf --height 40% --reverse --header "swap할 worktree 선택")
        [ -z "$target" ] && return 0
      fi

      local target_path="${wt_dir}/${target}"
      if [ ! -d "$target_path" ]; then
        echo "Error: worktree '$target' 없음"
        wt list
        return 1
      fi

      local current_branch
      current_branch=$(git -C "$git_root" branch --show-current)
      local current_name="${current_branch//\//-}"

      local target_branch
      target_branch=$(git -C "$target_path" branch --show-current)

      echo "Swap: $current_branch ↔ $target_branch"

      if ! git -C "$git_root" diff --quiet || ! git -C "$git_root" diff --cached --quiet; then
        echo "⚠️  메인에 uncommitted 변경사항이 있습니다"
        read -q "REPLY?계속하시겠습니까? (y/n) " || { echo; return 1; }
        echo
      fi

      git worktree remove "$target_path" --force 2>/dev/null
      git -C "$git_root" checkout "$target_branch"

      mkdir -p "$wt_dir"
      git worktree add "${wt_dir}/${current_name}" "$current_branch" 2>/dev/null

      echo "✅ 완료: 메인이 $target_branch 브랜치로 전환됨"
      ;;

    rm|remove)
      local name="$1"
      if [ -z "$name" ]; then
        echo "Usage: wt rm <worktree-name>"
        return 1
      fi
      git worktree remove "${wt_dir}/${name}"
      ;;

    *)
      echo "Usage: wt <list|add|swap|rm> [args]"
      echo ""
      echo "  wt list          worktree 목록"
      echo "  wt add <branch>  worktree 추가"
      echo "  wt swap [name]   메인과 worktree 치환"
      echo "  wt rm <name>     worktree 삭제"
      ;;
  esac
}
```

## 사용 예시

```bash
# worktree 추가
wt add develop
wt add feature/auth

# 목록 확인
wt list
# === Main ===
# master
#
# === Worktrees ===
#   develop (develop)
#   feature-auth (feature/auth)

# develop으로 치환
wt swap develop
# Swap: master ↔ develop
# ✅ 완료: 메인이 develop 브랜치로 전환됨

# fzf로 선택하여 치환
wt swap

# 다시 master로 돌아가기
wt swap master

# worktree 삭제
wt rm feature-auth
```

## 코드 상세 설명 (bash 문법)

### 변수와 명령어 치환

| 문법 | 의미 | 예시 |
|------|------|------|
| `local var` | 함수 내 지역변수 선언 | `local git_root` |
| `$(...)` | 명령어 실행 후 결과를 변수에 저장 | `git_root=$(git rev-parse ...)` |
| `${1:-기본값}` | 첫번째 인자가 없으면 기본값 사용 | `${1:-list}` |
| `${var//A/B}` | 변수 내 A를 모두 B로 치환 | `${branch//\//-}` → `/`를 `-`로 |
| `$1, $2` | 함수에 전달된 인자 (순서대로) | `wt swap develop` → `$1=swap` |
| `shift` | 인자를 한 칸 왼쪽으로 밀기 | shift 후 `$1`이 다음 인자로 변경 |

### 조건 검사

| 문법 | 의미 |
|------|------|
| `[ -z "$var" ]` | 변수가 비어있으면 참 |
| `[ -d "path" ]` | 디렉토리가 존재하면 참 |
| `[ ! -d "path" ]` | 디렉토리가 존재하지 않으면 참 |
| `!` | 부정 (결과 뒤집기) |

### 흐름 제어

| 문법 | 의미 |
|------|------|
| `if ... then ... fi` | 조건문 (fi = if 뒤집은것) |
| `case ... esac` | switch문 (esac = case 뒤집은것) |
| `for ... do ... done` | 반복문 |
| `\|\|` | 앞이 실패하면 뒤 실행 (OR) |
| `&&` | 앞이 성공하면 뒤 실행 (AND) |
| `return 0` | 함수 정상 종료 |
| `return 1` | 함수 에러 종료 |
| `;;` | case 블록 끝 (break 역할) |
| `*)` | case의 default (나머지 전부 매칭) |

### 리다이렉션

| 문법 | 의미 |
|------|------|
| `2>/dev/null` | 에러 메시지 숨기기 |
| `&>/dev/null` | 모든 출력 숨기기 |
| `\|` | 파이프 - 앞 명령의 출력을 뒤 명령의 입력으로 |

## 주의사항

- `wt swap` 전에 uncommitted 변경사항은 commit 또는 stash 권장
- IDEA에서 swap 후 `File > Reload All from Disk` 또는 자동 감지 대기
- `.worktree/`는 반드시 `.gitignore`에 추가
- `read -q`는 zsh 전용. bash에서는 `read -p "계속? (y/n) " -n 1 REPLY`로 변경 필요
