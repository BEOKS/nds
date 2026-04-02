---
name: hiworks-contacts
description: Hiworks 주소록/계정 검색. 이름, 팀명, 키워드로 내부 사용자를 찾을 때 사용한다.
---

# Hiworks Contacts Skill

## When to use

- 사람 이름, user_id, 조직 키워드로 내부 계정을 찾아야 할 때
- memo, mail, approval 전에 사용자 식별자가 필요한데 정확한 값을 모를 때

## Primary commands

```bash
hiworks contacts search --keyword 홍길동
hiworks contacts search --keyword 재무팀
```

## Workflow

```bash
hiworks contacts search --keyword 홍길동
hiworks contacts search --keyword 플랫폼
```

## Rules

- 사람 이름 기반 검색을 먼저 시도하고, 필요하면 조직/팀 키워드로 좁힙니다.
- 이후 메일/쪽지/결재로 이어지는 작업은 검색 결과를 기준으로 수행합니다.
