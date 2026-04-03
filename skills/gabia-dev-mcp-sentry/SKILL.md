---
name: gabia-dev-mcp-sentry
description: Sentry REST API를 직접 호출해 이슈 상세 조회, 이슈 검색, 이벤트/스택트레이스 조회, 프로젝트 목록 조회, 이슈 상태 변경을 자동화할 때 사용한다. MCP가 없어도 scripts/sentry_cli.py로 수행한다. Sentry URL이 주어지면 자동으로 파싱하여 이슈 정보를 조회한다.
---

# Sentry 이슈/이벤트 조회 자동화

## 제공 기능

- **프로젝트 목록 조회**: 조직 내 Sentry 프로젝트 목록 확인 (이름/slug 검색, 전체 페이지 탐색)
- **이슈 검색**: 키워드, 프로젝트, 환경 필터로 이슈 검색
- **최신 이슈 빠른 조회**: 프로젝트 이름/slug로 가장 최근 이슈 1건 즉시 조회
- **이슈 상세 조회**: 이슈 ID 또는 Sentry URL로 상세 정보 확인
- **이벤트/스택트레이스 조회**: 이슈에 연결된 이벤트 목록 및 상세 조회
- **이슈 상태 변경**: resolved, unresolved, ignored 상태 전환
- **URL 자동 파싱**: Sentry 웹 URL을 입력하면 org/issue_id를 자동 추출

## 사전 조건(환경변수)

- **필수**: `SENTRY_TOKEN` - Sentry Auth Token (Settings > Auth Tokens에서 발급, `event:read` 스코프 필요)
- **선택**: `SENTRY_API_URL` (기본값: `https://sentry.gabia.io:9000`)
- **선택**: `SENTRY_ORG` (기본값: `sentry-gabia`)
- **선택**: `SENTRY_SSL_VERIFY` (기본값: `false`, self-hosted 인증서 검증 비활성화)

## 기본 워크플로우

1. Sentry URL이 주어지면 → `url-info` 명령으로 이슈 상세 + 최신 이벤트 조회
2. 키워드로 이슈를 찾고 싶으면 → `issues --query` 명령으로 검색
3. 특정 이슈의 스택트레이스가 필요하면 → `issue-events {issue_id} --full` 또는 `event-get {issue_id} latest`
4. 프로젝트 이름/slug로 최신 이슈 바로 조회 → `issue-latest --project <slug|name>`
5. 프로젝트 이름/slug를 모르면 → `projects --query <키워드>` 또는 `projects --all`로 검색

## 예시

### Sentry URL로 이슈 조회 (가장 일반적)

```bash
python3 scripts/sentry_cli.py url-info \
  "https://sentry.gabia.io:9000/organizations/sentry-gabia/issues/29934/?project=84&query=is%3Aunresolved" \
  --with-latest
```

### 프로젝트 목록 확인 및 검색

```bash
# 전체 목록 (첫 페이지)
python3 scripts/sentry_cli.py projects

# 이름/slug 부분 일치 검색 (전체 페이지 탐색)
python3 scripts/sentry_cli.py projects --query contract-internal-api --all

# slug exact match
python3 scripts/sentry_cli.py projects --slug contract-internal-api

# 결과 개수 제한
python3 scripts/sentry_cli.py projects --all --limit 20
```

### 이슈 검색 (키워드)

```bash
# 미해결 이슈에서 키워드 검색
python3 scripts/sentry_cli.py issues --query "is:unresolved NullPointerException" --project 84

# 최근 24시간 이슈
python3 scripts/sentry_cli.py issues --query "is:unresolved" --project 84 --stats-period 24h --sort date

# 특정 환경 필터
python3 scripts/sentry_cli.py issues --query "is:unresolved" --environment production --limit 10
```

### 이슈 상세 조회

```bash
# ID로 조회
python3 scripts/sentry_cli.py issue-get 29934

# URL로 조회 (자동 파싱)
python3 scripts/sentry_cli.py issue-get "https://sentry.gabia.io:9000/organizations/sentry-gabia/issues/29934/?project=84"
```

### 이벤트/스택트레이스 조회

```bash
# 이슈의 이벤트 목록 (본문/스택트레이스 포함)
python3 scripts/sentry_cli.py issue-events 29934 --full

# 최신 이벤트 단일 상세 조회
python3 scripts/sentry_cli.py event-get 29934 latest

# 특정 이벤트 ID로 단일 상세 조회
python3 scripts/sentry_cli.py event-get 29934 abc123def456
```

> `issue-events --full`: 이벤트 목록 + 각 이벤트 본문(스택트레이스 등) 포함
> `event-get latest`: 최신 이벤트 1건 상세 조회

### 가장 최근 이슈 빠르게 조회

```bash
# 프로젝트 slug로 최신 이슈 1건 (모든 상태)
python3 scripts/sentry_cli.py issue-latest --project contract-internal-api

# 미해결 이슈 중 최신 1건
python3 scripts/sentry_cli.py issue-latest --project contract-internal-api --status unresolved

# 최신 이슈 + 해당 이벤트 상세까지 한 번에
python3 scripts/sentry_cli.py issue-latest --project contract-internal-api --with-latest-event

# 프로젝트 숫자 ID도 사용 가능
python3 scripts/sentry_cli.py issue-latest --project 84 --status any
```

### 이슈 상태 변경

```bash
# 이슈 해결 처리
python3 scripts/sentry_cli.py issue-update 29934 --status resolved

# 담당자 지정
python3 scripts/sentry_cli.py issue-update 29934 --assigned-to username
```

## 검색 쿼리 문법

Sentry `--query` 파라미터는 다음 필터를 지원한다:

| 필터 | 설명 | 예시 |
|------|------|------|
| `is:unresolved` | 미해결 이슈 (기본값) | `is:unresolved` |
| `is:resolved` | 해결된 이슈 | `is:resolved` |
| `is:ignored` | 무시된 이슈 | `is:ignored` |
| `assigned:me` | 나에게 할당된 이슈 | `assigned:me` |
| `assigned:username` | 특정 사용자에게 할당 | `assigned:john` |
| `level:error` | 에러 레벨 필터 | `level:error` |
| `platform:java` | 플랫폼 필터 | `platform:python` |
| 키워드 | 이슈 제목/메시지 검색 | `NullPointerException` |

여러 필터를 공백으로 조합 가능: `is:unresolved level:error NullPointer`
