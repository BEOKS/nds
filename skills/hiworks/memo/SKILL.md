---
name: memo
description: Hiworks 쪽지 전송, 받은 쪽지 조회, 이름 기반 수신자 검색을 안내한다.
---

# Hiworks Memo Skill

## When to use

- 사람 이름만 알고 쪽지를 보내야 할 때
- 받은 쪽지/보낸 쪽지를 제목, 발신자, 수신자 기준으로 찾고 싶을 때
- 특정 `memo_no`의 본문과 수신자 목록을 읽고 싶을 때

## Primary commands

```bash
hiworks memo resolve-recipient --name 홍길동
hiworks memo send --subject 테스트 --content 안녕하세요 --to-name 홍길동 --yes
hiworks memo list --subject-like 테스트 --type send
hiworks memo recv --sender-name-like Gaon
hiworks memo read 25673853
```

## Workflow

```bash
hiworks memo resolve-recipient --name 홍길동
hiworks memo recv --sender-name-like 홍길동
hiworks memo send --subject 테스트 --content 안녕하세요 --to-name 홍길동 --dry-run
hiworks memo send --subject 테스트 --content 안녕하세요 --to-name 홍길동 --yes
```

## Rules

- raw `master_user_no`보다 이름 기반 수신자 검색을 우선 사용합니다.
- 수신자 이름이 모호하면 TTY에서는 선택, 비대화형에서는 실패시켜야 합니다.
- 실제 전송은 `--yes`가 있을 때만 수행합니다.
