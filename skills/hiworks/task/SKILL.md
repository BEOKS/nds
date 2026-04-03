---
name: hiworks-task
description: Hiworks 업무 앱 조회, 업무 생성, 상태 변경, 댓글 작성, 자가점검일 업데이트를 안내한다.
---

# Hiworks Task Skill

## When to use

- 내가 참여 중인 업무 앱과 저장된 필터를 확인해야 할 때
- 특정 앱에서 업무 목록/상세를 읽어야 할 때
- 새 업무를 등록하거나 상태를 변경해야 할 때
- 업무 댓글을 읽거나 작성해야 할 때
- 자가점검 DATE 필드를 최신화해야 할 때

## Primary commands

```bash
hiworks task apps
hiworks task filters <app_id>
hiworks task filter <app_id> <filter_id>
hiworks task my --type ASSIGNEE --category-neq DONE --limit 5
hiworks task list <app_id> --limit 10
hiworks task show <app_id> <task_id>
hiworks task forms <app_id>
hiworks task inspect <app_id>
hiworks task create <app_id> '제목' --dry-run
hiworks task create <app_id> '제목' --content '상세 설명' --yes
hiworks task set-status <app_id> <task_id> <status_component_id> <label_id> <category_id> --yes
hiworks task comments <app_id> <task_id>
hiworks task comment <app_id> <task_id> '댓글 내용' --dry-run
hiworks task comment <app_id> <task_id> '댓글 내용' --yes
hiworks task update-selfcheck <app_id> <task_id> <component_id> --dry-run
```

## Workflow

```bash
hiworks task apps
hiworks task inspect <app_id>
hiworks task forms <app_id>
hiworks task create <app_id> '제목' --dry-run
hiworks task create <app_id> '제목' --yes
hiworks task comments <app_id> <task_id>
hiworks task comment <app_id> <task_id> '진행 상황 업데이트' --dry-run
```

## Rules

- `app_id`를 모르면 항상 `task apps`부터 실행합니다.
- 새 업무 생성 전 반드시 `task forms` 또는 `task inspect`로 필드 구조를 확인합니다.
- 상태 변경에 필요한 `status_component_id`, `label_id`, `category_id`는 inspect/forms 결과에서 찾습니다.
- 생성/댓글/상태변경/자가점검일 업데이트는 먼저 `--dry-run`으로 payload를 확인합니다.
- 실제 반영은 `--yes`가 있을 때만 진행합니다.
