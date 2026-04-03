---
name: hiworks-team
description: Hiworks 팀 주간 업무 현황 조회, 유닛 리포트, 자가점검일 배치 업데이트를 안내한다.
---

# Hiworks Team Skill

## When to use

- 팀 단위로 진행 중인 업무 현황을 빠르게 보고 싶을 때
- 프로젝트/담당자/업무종류 기준으로 주간 유닛 리포트를 보고 싶을 때
- 내 업무 중 오래된 자가점검일을 일괄 업데이트해야 할 때

## Primary commands

```bash
hiworks team weekly-report
hiworks team weekly-report --node-id 639 --detail
hiworks team weekly-report --json
hiworks team unit-report <app_id>
hiworks team unit-report <app_id> --group-by 프로젝트
hiworks team unit-report <app_id> --output csv --save 팀현황.csv
hiworks team selfcheck-update --app-id <app_id> --dry-run
hiworks team selfcheck-update --app-id <app_id> --date 2026-04-04 --yes
```

## Workflow

```bash
hiworks team weekly-report --detail
hiworks task inspect <app_id>
hiworks team unit-report <app_id> --group-by auto
hiworks team selfcheck-update --app-id <app_id> --dry-run
```

## Rules

- 팀 현황을 빠르게 볼 때는 `weekly-report`, 팀장용 집계/댓글 요약은 `unit-report`를 사용합니다.
- 유닛 리포트의 그룹 기준과 자가점검 필드는 `task inspect <app_id>`로 먼저 확인합니다.
- `selfcheck-update`는 실제 반영 전에 `--dry-run`을 먼저 실행합니다.
- 여러 태스크에 동일한 댓글/업데이트를 일괄 적용하기 전에 대상 태스크를 반드시 확인합니다.
