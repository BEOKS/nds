---
name: hiworks-work
description: Hiworks 휴가 캘린더, 휴가자 조회, 개인 휴가 잔여량, 휴가 신청을 안내한다.
---

# Hiworks Work Skill

## When to use

- 특정 월의 전사 휴가 현황을 확인해야 할 때
- 특정 날짜의 휴가자/부재자를 빠르게 확인해야 할 때
- 내 휴가 잔여량과 요청 가능 상태를 보고 싶을 때
- 실제 휴가 신청을 제출해야 할 때

## Primary commands

```bash
hiworks work vacation-calendar --year 2026 --month 4
hiworks work leave-employees --date 2026-04-02
hiworks work vacation-request-calendar --from 2026-04-01 --to 2026-04-30
hiworks work vacation-types
hiworks work vacation-request --vacation-type 1 --date 2026-04-03 --reason 개인사유 --dry-run
hiworks work vacation-request --vacation-type 1 --date 2026-04-03 --reason 개인사유
```

## Workflow

```bash
hiworks work vacation-types
hiworks work vacation-request-calendar --from 2026-04-01 --to 2026-04-30
hiworks work vacation-request --vacation-type 1 --date 2026-04-03 --reason 개인사유 --dry-run
hiworks work vacation-request --vacation-type 1 --date 2026-04-03 --reason 개인사유
```

## Rules

- 휴가 종류 ID는 먼저 `vacation-types`로 확인합니다.
- 휴가 신청 전 `vacation-request-calendar`로 잔여 휴가와 기존 요청을 확인합니다.
- 실제 신청 전 항상 `--dry-run`으로 검증합니다.
- 일정 조회는 `work`가 아니라 schedule 스킬을 사용합니다.
