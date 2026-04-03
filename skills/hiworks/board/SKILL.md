---
name: hiworks-board
description: Hiworks 게시판 조회, 게시글 작성, 댓글, 읽음 사용자, goodjob 토글을 안내한다.
---

# Hiworks Board Skill

## When to use

- 게시판 목록과 최근 글을 빠르게 보고 싶을 때
- 특정 게시판의 글 목록, 상세, 첨부를 읽어야 할 때
- 게시글에 댓글을 달거나 `goodjob` 상태를 바꿔야 할 때
- 실제 게시글 작성 전에 요청 payload를 먼저 검토하고 싶을 때

## Primary commands

```bash
hiworks board boards
hiworks board recent
hiworks board recent-read --index 1
hiworks board recent-open --index 1
hiworks board posts 123 --search 회의
hiworks board read 123 456
hiworks board comments 123 456
hiworks board comment-add 123 456 --content '좋은 글 감사합니다'
hiworks board readers 123 456
hiworks board goodjob 123 456 --toggle
hiworks board attachments 123 456
hiworks board write 123 --title 제목 --content 본문 --dry-run
hiworks board write 123 --title 제목 --content 본문 --yes
```

## Workflow

```bash
hiworks board boards
hiworks board recent
hiworks board recent-read --index 1
hiworks board recent-comments --index 1
hiworks board write 123 --title 제목 --content 본문 --dry-run
```

## Rules

- 빠른 탐색은 `recent`, 정교한 조회는 `boards -> posts -> read` 순서를 기본으로 합니다.
- 댓글/좋아요/작성처럼 상태가 바뀌는 작업은 대상 글을 먼저 읽고 수행합니다.
- 게시글 작성은 항상 `--dry-run` 후 `--yes` 순서로 진행합니다.
- 브라우저에서 바로 열어야 하면 `recent-open --index N`을 사용합니다.
