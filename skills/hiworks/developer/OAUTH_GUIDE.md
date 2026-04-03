# Hiworks OAuth 연동 가이드

Hiworks CLI 밖에서 자체 앱이나 에이전트가 OAuth로 Hiworks API를 호출해야 할 때 참고하는 개발자 문서입니다.

- CLI 동작, 최신 명령 체계, 문서 원본 기준 저장소: `https://gitlab.gabia.com/hiworks/ai/hiworks-cli`

## 빠른 시작

이미 `hiworks` CLI가 설치되어 있다면 먼저 CLI로 인증이 정상 동작하는지 확인합니다.

```bash
hiworks auth browser-login
hiworks whoami
hiworks auth status
```

이 세 단계가 동작하면 OAuth 클라이언트, redirect, token 교환 흐름이 최소한 현재 환경에서 유효하다는 뜻입니다.

## 프로필과 엔드포인트

- Dev 테스트: `hiworks --profile dev ...`
- Gabia 업무 환경: `hiworks --profile gabia ...`

대표 엔드포인트 예시:

- authorize: `https://auth-api.gabiaoffice.hiworks.com/oauth/authorize`
- token: `https://auth-api.gabiaoffice.hiworks.com/oauth/token`
- me: `https://cache-api.gabiaoffice.hiworks.com/me`

현재 기본값은 `hiworks doctor`, `hiworks auth status`로 확인할 수 있습니다.

## OAuth 기본 흐름

1. OAuth client를 환경별로 등록합니다.
2. 브라우저를 `/oauth/authorize`로 보냅니다.
3. callback에서 authorization code를 받습니다.
4. `/oauth/token`으로 code를 access token / refresh token으로 교환합니다.
5. `Authorization: Bearer <access_token>` 헤더로 API를 호출합니다.
6. access token 만료 시 refresh token으로 재발급합니다.

## 로컬 개발 체크리스트

```bash
# 브라우저 로그인
hiworks auth browser-login

# 사용자 확인
hiworks whoami

# raw API 호출 테스트
hiworks auth call --url https://cache-api.gabiaoffice.hiworks.com/me
```

- callback URL은 등록한 값과 정확히 일치해야 합니다.
- profile마다 client와 endpoint가 다를 수 있으므로 dev/gabia를 혼용하지 않습니다.

## 자체 앱 연동 원칙

- secret은 환경변수나 secret store에만 보관합니다.
- access token, refresh token은 로컬 파일이나 DB에 안전하게 저장합니다.
- 먼저 CLI로 동일 시나리오가 되는지 검증한 뒤 앱 구현으로 넘어갑니다.
- wrapper 명령이 이미 있는 기능이면 직접 raw API를 재구현하기보다 CLI 동작을 먼저 참고합니다.

## 문제 해결

- 세션/토큰 상태: `hiworks auth status`
- 현재 사용자/권한 확인: `hiworks whoami`
- 프로필/엔드포인트/로컬 경로 확인: `hiworks doctor`
- 실제 호출 URL 추적: `hiworks --trace-http ...`
