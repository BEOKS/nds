---
name: hiworks-admin
description: Hiworks 관리자 전용 근무/인사 데이터 다운로드와 월간 보고서 생성을 안내한다.
---

# Hiworks Admin Skill

## When to use

- 관리자 권한으로 근무 엑셀 원본을 받아야 할 때
- 월간 근무현황 HTML 보고서를 생성해야 할 때
- 임직원 명부, 휴직자 목록, 휴직 이력을 내려받아야 할 때

## Primary commands

```bash
hiworks admin work-report --year 2026 --month 4
hiworks admin work-report --year 2026 --month 4 --output report.html
hiworks admin work-export --year 2026 --month 4 --type sum
hiworks admin work-export --year 2026 --month 4 --type work
hiworks admin employees-export
hiworks admin employees-export --node-id <node_id>
hiworks admin leave-employees
hiworks admin leave-histories
```

## Workflow

```bash
hiworks whoami
hiworks org tree
hiworks admin employees-export --node-id <node_id>
hiworks admin work-report --year 2026 --month 4
```

## Rules

- `/me`의 `level`이 `admin`이어야 합니다.
- 부서별 명부가 필요하면 먼저 `org tree`로 정확한 `node_id`를 확인합니다.
- 월간 보고서 생성 전에 필요한 원본 엑셀(`work-export`)을 먼저 받아 검증할 수 있습니다.
- 관리자 기능은 일반 사용자 계정에서 실패하는 것이 정상일 수 있습니다.
