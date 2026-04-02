---
name: hiworks-reference
description: Hiworks CLI의 문서 탐색 기능. search, flow, ids, capability, spec, names를 사용해 API와 식별자를 찾는다.
---

# Hiworks Reference Skill

## When to use

- 어떤 API나 기능을 써야 할지 먼저 찾아야 할 때
- 식별자 의미나 혼동 규칙을 확인해야 할 때
- 구현 흐름이나 spec 위치를 빠르게 찾아야 할 때
- raw `docs/msa-vault` 파일을 직접 열기 전에 검색하고 싶을 때

## Primary commands

```bash
hiworks search memo master_user_no
hiworks flow search memo
hiworks flow show memo-master-user-send
hiworks ids search office_user_no
hiworks ids show master_user_no
hiworks capability list --domain 전자결재
hiworks capability show schedule-read
hiworks spec list --repo hr-api
hiworks spec show <spec_id>
hiworks names audit
```

## Workflow

```bash
hiworks search 예약 회의실
hiworks capability list --domain 예약
hiworks flow search booking
hiworks spec list --repo booking-api
```

## Rules

- vault 원문을 직접 탐색하기 전에 `search`, `capability`, `flow`를 우선 사용합니다.
- 사람 기준 작업을 찾을 때는 `capability`, 실제 endpoint/spec를 찾을 때는 `spec`을 사용합니다.
- ID 의미 확인은 `ids`, 중복되거나 모호한 API 제목 확인은 `names audit`를 사용합니다.
