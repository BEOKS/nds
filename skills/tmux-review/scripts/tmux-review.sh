#!/usr/bin/env bash
# tmux-review.sh - GitLab MR 코드 리뷰를 위한 tmux 레이아웃 설정
#
# Usage: tmux-review.sh <project_dir> <window_name> <prompt_file>
#
# Layout:
# ┌──────────────────┬──────────────┐
# │                  │   lazygit    │
# │    claude        ├──────────────┤
# │   (review)       │    hx .      │
# │                  │              │
# └──────────────────┴──────────────┘
set -euo pipefail

PROJECT_DIR="$1"
WINDOW_NAME="$2"
PROMPT_FILE="$3"

# Create new tmux window (pane 0 = left)
tmux new-window -n "$WINDOW_NAME" -c "$PROJECT_DIR"

# Split horizontally: right pane takes 40%
tmux split-window -h -l 40% -c "$PROJECT_DIR" -t "$WINDOW_NAME"

# Split right pane vertically: bottom-right takes 50%
tmux split-window -v -l 50% -c "$PROJECT_DIR"

# Pane 0: left       → claude review
# Pane 1: top-right  → lazygit
# Pane 2: bottom-right → hx .

tmux send-keys -t "$WINDOW_NAME.2" 'hx .' Enter
tmux send-keys -t "$WINDOW_NAME.1" 'lazygit' Enter
tmux send-keys -t "$WINDOW_NAME.0" "cat '${PROMPT_FILE}' | claude" Enter

# Focus on left pane (claude)
tmux select-pane -t "$WINDOW_NAME.0"
