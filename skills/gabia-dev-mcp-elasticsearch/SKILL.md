---
name: gabia-dev-mcp-elasticsearch
description: Kibana API를 통해 Elasticsearch 로그를 검색/조회할 때 사용한다. MCP가 없어도 scripts/elasticsearch_cli.py로 수행한다. Kibana Discover URL이 주어지면 자동으로 파싱하여 로그를 조회한다. kubernetes 서비스 로그 조회, KQL 쿼리 검색, 인덱스 패턴/필드 확인을 지원한다. 사용자가 "로그 조회", "로그 검색", "elasticsearch", "kibana", "서비스 로그" 등을 요청할 때 사용.
---

# Elasticsearch/Kibana 로그 조회 자동화

## 제공 기능

- **로그 검색**: KQL 쿼리로 Elasticsearch 로그 검색
- **서비스 로그 간편 조회**: kubernetes.service-name 기준 서비스 로그 빠른 검색
- **Kibana URL 자동 파싱**: Kibana Discover URL을 입력하면 space/index/KQL/시간 범위 자동 추출 후 검색
- **인덱스 패턴 목록**: Kibana space의 인덱스 패턴 확인
- **필드 목록 조회**: 인덱스 패턴의 필드 구조 확인
- **Kibana Space 목록**: 사용 가능한 space 확인

## 인증 방식 (2단계 인증)

Kibana 접근 시 2단계 인증이 필요하다:

1. **nginx Basic Auth** - LDAP 계정으로 프록시 인증 통과
2. **Kibana 세션 로그인** - Elasticsearch 계정으로 `/internal/security/login` API를 통해 세션 쿠키 획득

CLI가 자동으로 두 단계를 모두 처리한다.

## 사전 조건(환경변수)

- **필수**: `LDAP_USER` - LDAP 사용자 ID (nginx Basic Auth용)
- **필수**: `LDAP_PWD` - LDAP 비밀번호 (nginx Basic Auth용)
- **선택**: `KIBANA_USER` - Kibana 로그인 사용자 (기본값: `developer`)
- **선택**: `KIBANA_PWD` - Kibana 로그인 비밀번호 (기본값: `roqkfroqkf!@#$`)
- **선택**: `KIBANA_URL` (기본값: `http://211.47.70.165`)
- **선택**: `KIBANA_SPACE` (기본값: `kubernetes`)
- **선택**: `KIBANA_INDEX_PATTERN` (기본값: `c8095940-0c7b-11ed-a662-5ff9b95a299f`)
- **선택**: `KIBANA_SSL_VERIFY` (기본값: `false`)

## 기본 워크플로우

1. Kibana URL이 주어지면 → `url-search` 명령으로 자동 파싱 후 검색
2. 서비스 로그를 빠르게 보고 싶으면 → `service-logs {서비스명}`
3. 자유 KQL 쿼리로 검색하고 싶으면 → `search --kql "..."`
4. 인덱스 패턴 ID를 모르면 → `index-patterns` 명령으로 확인
5. 필드명을 모르면 → `fields --filter keyword` 명령으로 확인

## 예시

### Kibana URL로 로그 조회 (가장 일반적)

```bash
python3 scripts/elasticsearch_cli.py url-search \
  "http://211.47.70.165/s/kubernetes/app/discover#/?_g=(filters:!(),query:(language:kuery,query:''),refreshInterval:(pause:!t,value:0),time:(from:now-25h,to:now))&_a=(columns:!(),filters:!(),index:c8095940-0c7b-11ed-a662-5ff9b95a299f,interval:auto,query:(language:kuery,query:'kubernetes.service-name%20:%20%20%22*gsecu-api-stage*%22'),sort:!(!('@timestamp',desc)))" \
  --size 100
```

### 서비스 로그 간편 조회

```bash
# 기본 (최근 24시간)
python3 scripts/elasticsearch_cli.py service-logs gsecu-api-stage

# 최근 1시간, 간결한 출력
python3 scripts/elasticsearch_cli.py service-logs gsecu-api-stage \
  --time-from now-1h --compact

# 특정 필드만 조회
python3 scripts/elasticsearch_cli.py service-logs gsecu-api-stage \
  --fields "@timestamp,message,level" --size 20

# 추가 KQL 조건
python3 scripts/elasticsearch_cli.py service-logs gsecu-api-stage \
  --extra-kql 'level : "ERROR"'
```

### KQL 쿼리로 검색

```bash
# kubernetes 서비스 로그 검색
python3 scripts/elasticsearch_cli.py search \
  --kql 'kubernetes.service-name : "*gsecu-api-stage*"' \
  --time-from now-6h --size 100 --compact

# 에러 로그만 검색
python3 scripts/elasticsearch_cli.py search \
  --kql 'kubernetes.service-name : "*gsecu-api*" AND level : "ERROR"' \
  --time-from now-1h

# 다른 space/index 사용
python3 scripts/elasticsearch_cli.py search \
  --space my-space --index-pattern abc123-def456 \
  --kql 'message : "*timeout*"'
```

### 인덱스 패턴 확인

```bash
# kubernetes space의 인덱스 패턴 목록
python3 scripts/elasticsearch_cli.py index-patterns

# 다른 space
python3 scripts/elasticsearch_cli.py index-patterns --space my-space

# 키워드로 검색
python3 scripts/elasticsearch_cli.py index-patterns --search "kubernetes"
```

### 필드 목록 조회

```bash
# 기본 인덱스 패턴의 전체 필드
python3 scripts/elasticsearch_cli.py fields

# kubernetes 관련 필드만 필터
python3 scripts/elasticsearch_cli.py fields --filter kubernetes

# 필드명만 간결하게
python3 scripts/elasticsearch_cli.py fields --filter level --names-only
```

### Kibana Space 목록

```bash
python3 scripts/elasticsearch_cli.py spaces
```

## KQL 쿼리 문법

`--kql` 파라미터는 Kibana Query Language(KQL) 문법을 지원한다:

| 패턴 | 설명 | 예시 |
|------|------|------|
| `field : "value"` | 정확 일치 | `level : "ERROR"` |
| `field : *value*` | 와일드카드 | `kubernetes.service-name : "*api*"` |
| `A AND B` | AND 조건 | `level : "ERROR" AND message : "*timeout*"` |

## 시간 범위 표현식

`--time-from`, `--time-to`에 사용 가능한 표현식:

| 표현식 | 의미 |
|--------|------|
| `now` | 현재 시간 |
| `now-30m` | 30분 전 |
| `now-1h` | 1시간 전 |
| `now-24h` | 24시간 전 |
| `now-7d` | 7일 전 |
| ISO 8601 | 예: `2024-01-01T00:00:00Z` |

## 주의사항

- Kibana `api/console/proxy`를 통해 Elasticsearch에 직접 쿼리한다 (Kibana 7.17.4 기준)
- `--size`가 크면 응답이 느려질 수 있으므로 필요한 만큼만 요청할 것
- 기본 인덱스 패턴(`c8095940-0c7b-11ed-a662-5ff9b95a299f`)은 kubernetes space 전용이며, 실제 인덱스는 `filebeat-*`로 자동 변환된다
- 다른 space를 사용할 때는 `index-patterns` 명령으로 해당 space의 인덱스 패턴 ID를 먼저 확인할 것
- 와일드카드 KQL 쿼리(예: `*api*`)는 자동으로 `.keyword` 서브필드를 사용한다
