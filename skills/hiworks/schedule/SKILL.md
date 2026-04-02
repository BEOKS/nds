---
name: hiworks-schedule
description: Hiworks 캘린더 목록, 기간별 일정 조회, 오늘 일정, 일정 상세 읽기를 안내한다.
---

# Hiworks Schedule Skill

## When to use

- 오늘 또는 특정 기간의 일정을 빠르게 조회해야 할 때
- 어떤 캘린더에 일정이 있는지 먼저 확인해야 할 때
- 특정 `schedule_no`의 상세 내용을 읽어야 할 때

## Primary commands

```bash
hiworks schedule calendars
hiworks schedule today
hiworks schedule list --from 2026-04-02 --to 2026-04-09
hiworks schedule read 12345
```

## Workflow

```bash
hiworks schedule calendars
hiworks schedule today
hiworks schedule list --from 2026-04-02 --to 2026-04-09
hiworks schedule read 12345
```

## Rules

- 먼저 `schedule calendars`로 캘린더/프로젝트 목록을 확인할 수 있습니다.
- 날짜 기준 조회는 `today`, `--from`, `--to`를 우선 사용합니다.
- 휴가/근태는 `schedule`이 아니라 work 스킬을 사용합니다.
