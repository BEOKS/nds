#!/bin/bash
# install_wt.sh - wt 쉘 함수를 사용자의 쉘 설정 파일에 등록

set -e

WT_FUNCTION='
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
        echo "Error: worktree '"'"'$target'"'"' 없음"
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
}'

# 쉘 설정 파일 감지
SHELL_NAME=$(basename "$SHELL")
if [ "$SHELL_NAME" = "zsh" ]; then
  RC_FILE="$HOME/.zshrc"
elif [ "$SHELL_NAME" = "bash" ]; then
  RC_FILE="$HOME/.bashrc"
else
  echo "지원하지 않는 쉘: $SHELL_NAME (zsh 또는 bash만 지원)"
  exit 1
fi

# 이미 등록 여부 확인
if grep -q "Git Worktree Swap System" "$RC_FILE" 2>/dev/null; then
  echo "wt 함수가 이미 $RC_FILE 에 등록되어 있습니다."
  exit 0
fi

# 등록
echo "$WT_FUNCTION" >> "$RC_FILE"
echo "wt 함수를 $RC_FILE 에 등록했습니다."
echo "적용하려면: source $RC_FILE"
