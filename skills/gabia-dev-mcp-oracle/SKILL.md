---
name: gabia-dev-mcp-oracle
description: Oracle DB에 대해 연결 테스트와 SELECT 쿼리 실행을 자동화할 때 사용한다. MCP 없이 scripts/oracle_cli.py가 JDBC 또는 sqlplus로 수행한다.
---

# Oracle Automation

## 제공 기능

- 연결 테스트
- SELECT 쿼리 실행(기본: JDBC, fallback: sqlplus)

## 사전 조건(환경변수)

- `ORACLE_HOST`, `ORACLE_USERNAME`, `ORACLE_PASSWORD` (필수)
- (선택) `ORACLE_PORT` 기본값 `1521`
- (선택) `ORACLE_SID` 기본값 `DEVGABIA`
- (선택) `ORACLE_SERVICE_NAME` 설정 시 JDBC URL을 service name 방식으로 구성합니다.
- JDBC 엔진 사용 시(기본)
  - (권장) `ORACLE_JDBC_JAR`에 `ojdbc*.jar` 경로를 지정합니다.
  - 미지정이면 `~/.gradle/caches/...`에서 `ojdbc*.jar`를 best-effort로 탐색합니다.
- sqlplus 엔진 사용 시
  - 로컬에 `sqlplus`가 설치되어 있어야 합니다.

## 사용 가이드

- 먼저 `python3 scripts/oracle_cli.py test`로 연결을 확인합니다.
- `select`는 SELECT만 허용합니다(INSERT/UPDATE/DELETE/DDL 불가).
- 쿼리 끝의 세미콜론(`;`)은 자동 제거합니다.
- 결과가 큰 테이블은 `WHERE`/`ROWNUM`/`FETCH FIRST` 등으로 범위를 제한합니다.

## 예시

```bash
python3 scripts/oracle_cli.py test
```

```bash
python3 scripts/oracle_cli.py select --query 'SELECT * FROM users WHERE id = 1'
```

```bash
cat query.sql | python3 scripts/oracle_cli.py select
```

```bash
# 엔진 강제 선택
python3 scripts/oracle_cli.py --engine jdbc test
python3 scripts/oracle_cli.py --engine sqlplus select --query 'SELECT 1 FROM dual'
```
