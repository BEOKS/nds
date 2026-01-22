---
name: gabia-dev-mcp-mysql
description: MySQL DB에 대해 연결 테스트와 읽기 전용 쿼리(SELECT/SHOW/DESCRIBE/EXPLAIN/WITH) 실행을 자동화할 때 사용한다. MCP 없이 scripts/mysql_cli.py가 mysql client로 수행하며, 다중 계정/스키마를 환경변수로 선택한다.
---

# MySQL Automation

## 제공 기능

- 연결 테스트
- 읽기 전용 쿼리 실행 (JSON 결과 출력)

## 사전 조건(환경변수)

### 다중 계정 모드

- `MYSQL_ACCOUNTS`에 JSON으로 여러 계정을 등록합니다.
- 각 계정은 `host`, `username`, `password`가 필수이며 `port`, `database`는 선택입니다.
- JSON 배열 또는 객체 둘 다 지원합니다.

```bash
export MYSQL_ACCOUNTS='[
  {"name":"dev","host":"127.0.0.1","port":3306,"username":"app","password":"secret","database":"app_db"},
  {"name":"report","host":"10.0.0.10","username":"ro","password":"secret","database":"report_db"}
]'
export MYSQL_DEFAULT_ACCOUNT=dev
export MYSQL_DEFAULT_SCHEMA=app_db
```

```bash
export MYSQL_ACCOUNTS='{
  "dev":{"host":"127.0.0.1","username":"app","password":"secret","database":"app_db"},
  "report":{"host":"10.0.0.10","username":"ro","password":"secret","database":"report_db"}
}'
```

### 단일 계정 모드

- `MYSQL_HOST`, `MYSQL_USERNAME`, `MYSQL_PASSWORD` (필수)
- (선택) `MYSQL_PORT` 기본값 `3306`
- (선택) `MYSQL_DATABASE`

### 공통

- (선택) `MYSQL_DEFAULT_ACCOUNT` 다중 계정에서 기본 계정 지정
- (선택) `MYSQL_DEFAULT_SCHEMA` 기본 스키마 지정
- 로컬에 `mysql` 클라이언트가 설치되어 있어야 합니다.

### mysql-client 설치 (macOS, Homebrew)

```bash
brew install mysql-client
echo 'export PATH="/opt/homebrew/opt/mysql-client/bin:$PATH"' >> ~/.zshrc
```

```bash
source ~/.zshrc
mysql --version
```

## 사용 가이드

- 먼저 `python3 scripts/mysql_cli.py test`로 연결을 확인합니다.
- 다중 계정은 `--account`로 선택합니다.
- 스키마는 `--schema` 또는 `--database`로 변경합니다.
- 읽기 전용 쿼리만 허용합니다(SELECT/SHOW/DESCRIBE/EXPLAIN/WITH).
- 쿼리 끝의 세미콜론(`;`)은 자동 제거합니다.

## 예시

```bash
python3 scripts/mysql_cli.py test
```

```bash
python3 scripts/mysql_cli.py --account dev --schema app_db select --query 'SELECT * FROM users WHERE id = 1'
```

```bash
cat query.sql | python3 scripts/mysql_cli.py --account report select
```
