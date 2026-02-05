---
name: hiworks-mail
description: Hiworks 메일 API 클라이언트. 크롬 브라우저 세션으로 인증. 메일함 목록, 메일 목록 조회, 메일 상세 조회. 사용자가 "메일 확인", "메일 목록", "안 읽은 메일", "메일 조회", "hiworks mail" 등 요청 시 사용.
---

# Hiworks Mail Skill

Hiworks 메일 API를 호출하여 메일함 목록, 메일 목록 조회, 메일 상세 조회를 수행한다.

## 인증 방식

크롬 브라우저에서 hiworks.com에 로그인되어 있으면 별도 설정 없이 자동 인증됨.

```bash
pip install browser_cookie3 requests
```

## 사용법

### 메일함 목록 조회

```bash
python scripts/hiworks_mail.py mailboxes
```

### 메일 목록 조회

```bash
python scripts/hiworks_mail.py list [--mailbox b0|b1|b4|b5] [--filter unread|starred|important] [--limit N] [--offset N]
```

옵션:
- `--mailbox`: 메일함 ID
  - `b0`: 받은 메일함 (기본값)
  - `b1`: 보낸 메일함
  - `b2`: 보낼 메일함
  - `b3`: 임시 메일함
  - `b4`: 스팸 메일함
  - `b5`: 휴지통
- `--filter`: `unread` (안 읽음), `starred` (별표), `important` (중요)
- `--limit`: 조회 개수 (기본: 20)
- `--offset`: 시작 위치 (기본: 0)

### 메일 상세 조회

```bash
python scripts/hiworks_mail.py read <mail_no> [--strip-html]
```

`mail_no`는 목록 조회 결과의 `no` 값을 사용한다.

옵션:
- `--strip-html`: HTML 태그 제거 후 텍스트만 표시

### 읽지 않은 메일 수 조회

```bash
python scripts/hiworks_mail.py count [--mailbox b0]
```

## 응답 예시

### 메일함 목록 응답

```json
{
  "data": [
    {"no": "b0", "name": "받은 메일함", "order": 1},
    {"no": "b1", "name": "보낸 메일함", "order": 2},
    {"no": "b4", "name": "스팸 메일함", "order": 5},
    {"no": "b5", "name": "휴지통", "order": 6}
  ]
}
```

### 메일 목록 응답

```json
{
  "meta": {"page": {"limit": 20, "offset": 0, "total": 17523}},
  "data": [
    {
      "no": 1149134684,
      "mailbox_id": "b0",
      "from": "Alan(김환승) <alan@example.com>",
      "to_address": ["user@example.com"],
      "subject": "회의 안내",
      "received_date": "2026-02-05T06:54:40Z",
      "is_new": true,
      "is_starred": false,
      "is_important": false,
      "file_attached": false,
      "size": 22934
    }
  ]
}
```

### 메일 상세 응답

```json
{
  "data": {
    "no": 1149134684,
    "subject": "회의 안내",
    "content": "<p>내일 오후 2시에 회의가 있습니다.</p>",
    "from": "Alan(김환승) <alan@example.com>",
    "to_address": ["user@example.com"],
    "received_date": "2026-02-05T06:54:40Z"
  }
}
```

## 의존성

```bash
pip install browser_cookie3 requests
```

## 주의사항

- 크롬 브라우저가 실행 중이면 쿠키 접근이 제한될 수 있음 (macOS Keychain)
- 세션 만료 시 브라우저에서 hiworks.com 재로그인 필요
- `subject`/`content` 필드에 HTML 엔티티가 포함될 수 있음
- gabia.com 계열 도메인은 `mail-api.gabiaoffice.hiworks.com` 사용
