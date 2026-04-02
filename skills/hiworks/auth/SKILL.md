---
name: hiworks-auth
description: Hiworks OAuth 인증, 로그인, 토큰 상태 확인, 토큰 갱신, raw API 호출을 안내한다.
---

# Hiworks Auth Skill

## When to use

- Bearer token이 없어서 Hiworks CLI 명령이 실패할 때
- 현재 세션 파일, 토큰 만료 상태, 프로필 기본값을 확인해야 할 때
- refresh token으로 access token을 다시 발급해야 할 때
- 래퍼 명령이 없는 API를 `auth call`로 직접 호출해야 할 때

## Primary commands

```bash
hiworks auth browser-login
hiworks auth status
hiworks whoami
hiworks doctor
hiworks auth refresh
hiworks auth me
hiworks auth call --url https://cache-api.gabiaoffice.hiworks.com/me
hiworks auth clear
```

## Workflow

```bash
hiworks auth browser-login
hiworks auth status
hiworks whoami
hiworks doctor
```

## Rules

- 브라우저/localhost callback 가능하면 `auth browser-login`을 우선 사용합니다.
- access token이 만료되면 먼저 `auth refresh`를 시도합니다.
- raw API 호출은 `auth call`을 사용하되, 이미 래퍼 명령이 있는 기능이면 래퍼 명령을 우선 사용합니다.
- 세션을 초기화해야 하면 `auth clear`로 로컬 토큰을 삭제합니다.
- 프로필 전환이 필요하면 `--profile gabia` 또는 `--profile dev`를 명시합니다.
