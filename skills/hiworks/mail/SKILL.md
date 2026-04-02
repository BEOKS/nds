---
name: mail
description: Hiworks 메일함 조회, 잠금 메일함 해제, 수신자 검색, preflight 확인, 메일 발송을 안내한다.
---

# Hiworks Mail Skill

## When to use

- 메일을 읽기 전에 메일함 잠금 상태를 확인해야 할 때
- 메일 목록을 날짜/제목/키워드 기준으로 조회해야 할 때
- 사내 이름, user_id, 이메일 주소로 수신자를 찾아야 할 때
- 실제 발송 전 sender 가능 여부와 preflight 결과를 확인해야 할 때

## Primary commands

```bash
hiworks mail mailboxes
hiworks mail list --mailbox-id b0 --limit 10
hiworks mail read --mail-no 12345 --mailbox-id b0
hiworks mail check-sender
hiworks mail resolve-recipient --name 홍길동
hiworks mail resolve-recipient --user-id crong
hiworks mail resolve-recipient --email user@example.com
hiworks mail preflight-send --to-name 홍길동 --subject 테스트 --content 본문
hiworks mail send --to-name 홍길동 --subject 테스트 --content 본문 --yes
hiworks mail unlock --mailbox-id b0 --password <비밀번호>
```

## Workflow

```bash
hiworks mail mailboxes
hiworks mail check-sender
hiworks mail resolve-recipient --name 홍길동
hiworks mail preflight-send --to-name 홍길동 --subject 테스트 --content 본문
hiworks mail send --to-name 홍길동 --subject 테스트 --content 본문 --dry-run
hiworks mail send --to-name 홍길동 --subject 테스트 --content 본문 --yes
```

## Rules

- 메일 읽기는 `mailboxes -> list -> read` 순서를 기본으로 합니다.
- 잠긴 메일함이면 먼저 `unlock`으로 mailbox token을 저장한 뒤 다시 읽습니다.
- 실제 발송 전 `check-sender` 또는 `preflight-send`를 먼저 실행합니다.
- 외부 메일 주소는 `--to external@example.com` 형식으로 직접 지정할 수 있습니다.
- 실제 발송은 `--yes`가 있을 때만 진행합니다.
