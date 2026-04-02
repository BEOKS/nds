---
name: hiworks-booking
description: Hiworks 회의실/자원 검색, 예약 현황 조회, 예약 생성/반납/취소를 안내한다.
---

# Hiworks Booking Skill

## When to use

- 회의실이나 자원 이름만 알고 예약 후보를 찾고 싶을 때
- 카테고리별 자원 목록과 예약 현황을 확인해야 할 때
- 빈 시간대를 먼저 본 뒤 예약하고 싶을 때
- 내 예약 목록을 보고 반납/취소해야 할 때

## Primary commands

```bash
hiworks booking categories
hiworks booking categories --with-resources --is-use
hiworks booking search-resources --name-like 회의실
hiworks booking available --date 2026-04-02 --duration 60
hiworks booking my
hiworks booking reserve --resource-name 603S --start 2026-04-02T10:00:00 --end 2026-04-02T11:00:00 --reason 팀미팅 --dry-run
hiworks booking reserve --resource-name 603S --start 2026-04-02T10:00:00 --end 2026-04-02T11:00:00 --reason 팀미팅 --yes
hiworks booking return --booking-id <booking_id> --dry-run
hiworks booking cancel --booking-id <booking_id> --dry-run
```

## Workflow

```bash
hiworks booking categories --with-resources --is-use
hiworks booking search-resources --name-like 603S
hiworks booking reserve --resource-name 603S --start 2026-04-02T10:00:00 --end 2026-04-02T11:00:00 --reason 팀미팅 --dry-run
hiworks booking reserve --resource-name 603S --start 2026-04-02T10:00:00 --end 2026-04-02T11:00:00 --reason 팀미팅 --yes
```

## Rules

- 자원명만 아는 경우 `search-resources` 또는 `categories --with-resources`를 먼저 사용합니다.
- 예약 생성, 반납, 취소는 먼저 `--dry-run`으로 확인합니다.
- 실제 변경은 `--yes`가 있을 때만 진행합니다.
- 이미 확정된 내 예약을 기준으로 취소/반납 대상을 고르려면 `booking my`를 먼저 확인합니다.
