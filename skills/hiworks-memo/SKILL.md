---
name: hiworks-memo
description: Hiworks 쪽지(메모) API 클라이언트. 크롬 브라우저 세션 또는 환경변수로 인증. 쪽지 목록 조회, 상세 조회, 읽지 않은 쪽지 수 확인. 사용자가 "쪽지 확인", "쪽지 목록", "안 읽은 쪽지", "쪽지 조회", "hiworks memo" 등 요청 시 사용.
---

# Hiworks Memo Skill

Hiworks 쪽지 API를 호출하여 쪽지 목록 조회, 상세 조회, 읽지 않은 쪽지 수를 확인한다.

## 인증 방식

### 1. 크롬 브라우저 세션 (권장)

크롬 브라우저에서 hiworks.com에 로그인되어 있으면 별도 설정 없이 자동 인증됨.

```bash
pip install browser_cookie3
```

### 2. 환경변수 기반 (fallback)

크롬 세션이 없거나 만료된 경우 환경변수로 인증.

```bash
export HIWORKS_ID="user_id"           # 사용자 ID (@ 앞부분)
export HIWORKS_DOMAIN="company.com"   # 도메인
export HIWORKS_PWD="password"         # 비밀번호
export HIWORKS_OTP_SECRET="..."       # OTP 시크릿 (선택, TOTP 기반)
export HIWORKS_ENV="prod"             # 환경: prod/dev/stage (기본: prod)
```

### 인증 모드 선택

```bash
export HIWORKS_AUTH_MODE="auto"       # auto (기본) | cookie | env
```

- `auto`: 쿠키 인증 우선 시도, 실패 시 환경변수 인증
- `cookie`: 크롬 쿠키 인증만 사용
- `env`: 환경변수 인증만 사용

## 사용법

### 쪽지 목록 조회

```bash
python scripts/hiworks_memo.py list [--type recv|send] [--filter unread|is_star|has_attach] [--limit N] [--offset N]
```

옵션:
- `--type`: `recv` (받은 쪽지), `send` (보낸 쪽지). 생략 시 전체 조회
- `--filter`: `unread` (안 읽음), `is_star` (별표), `has_attach` (첨부파일)
- `--limit`: 조회 개수 (기본: 20)
- `--offset`: 시작 위치 (기본: 0)

### 쪽지 상세 조회

```bash
python scripts/hiworks_memo.py read <memo_no>
```

`memo_no`는 목록 조회 결과의 `messages_no` 값을 사용한다. `/memo/messages/<messages_no>` 경로로 조회하며 본문(content)을 포함한 상세 정보를 반환한다.

### 읽지 않은 쪽지 수 조회

```bash
python scripts/hiworks_memo.py count
```

## 응답 예시

### 목록 조회 응답

```json
{
  "meta": {
    "page": {"limit": 20, "offset": 0, "total": 6301}
  },
  "data": [
    {
      "no": 25323383,
      "messages_no": 2141703,
      "sender": {"name": "Alan(김환승)", "user_no": 8767134, "read_at": "2026-02-04T14:06:28"},
      "receiver": {"name": "Aiden(곽영일)", "user_no": 7220028, "read_at": "2026-02-04T14:07:54"},
      "type": "recv",
      "subject": "회의 안내",
      "receivers_count": 16,
      "is_read": true,
      "created_at": "2026-02-04T14:06:28",
      "is_star": false,
      "has_attach": false
    }
  ]
}
```

### 상세 조회 응답 (`/memo/messages/<messages_no>`)

```json
{
  "data": {
    "no": 2141703,
    "subject": "회의 안내",
    "content": "<p>내일 오후 2시에 회의가 있습니다.</p>",
    "sender": {"name": "Alan(김환승)", "user_no": 8767134},
    "receivers": [{"name": "Aiden(곽영일)", "user_no": 7220028}],
    "created_at": "2026-02-04T14:06:28"
  }
}
```

참고: `content` 필드는 HTML 형식이므로 태그 제거 후 표시한다.

### 읽지 않은 쪽지 수 응답

```json
{
  "data": {
    "unread": 16,
    "total": 6301
  }
}
```

## 의존성

```bash
# 크롬 세션 인증용 (권장)
pip install browser_cookie3 requests

# 환경변수 인증용 (fallback)
pip install pyotp pycryptodome requests
```

## 인증 흐름

### 크롬 세션 인증
1. browser_cookie3로 크롬 쿠키 추출 (`.hiworks.com` 도메인)
2. 쿠키를 세션에 설정하여 API 호출
3. 세션 만료 시 "브라우저에서 다시 로그인하세요" 메시지 출력

### 환경변수 인증 (fallback)
1. `/wpf/gateway/getinfo_new`에서 `app_no` 획득 (실패 시 정적 값 사용)
2. AES-256-CBC로 사용자 정보 암호화
3. `/wpf/main/multi/make_key` (또는 `/make_key_otp`)로 `auth_key` 획득
4. `Authorization: Messenger {auth_key}` + `X-Office-No` 헤더로 API 호출

## 주의사항

- 크롬 브라우저가 실행 중이면 쿠키 접근이 제한될 수 있음 (macOS Keychain)
- 세션 만료 시 브라우저에서 hiworks.com 재로그인 필요
- OTP가 필요한 계정에서 환경변수 인증 시 `HIWORKS_OTP_SECRET` 설정 필수
- 프로덕션 환경이 기본값, 개발/스테이지 환경은 `HIWORKS_ENV`로 지정
- `subject` 필드에 HTML 엔티티(`&gt;` 등)가 포함될 수 있으므로 `html.unescape()` 처리 필요
- gabia.com 계열 도메인은 별도 memo API 호스트(`memo-api.gabiaoffice.hiworks.com`) 사용
