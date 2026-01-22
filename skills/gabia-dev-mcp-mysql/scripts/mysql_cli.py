#!/usr/bin/env python3
import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Any


# 환경변수에서 공백 제거 후 값을 가져오는 헬퍼

def _env(name: str) -> str | None:
    v = os.getenv(name)
    if v is None:
        return None
    v = v.strip()
    return v or None


# 필수 환경변수 확인

def _require_env(name: str) -> str:
    v = _env(name)
    if not v:
        raise SystemExit(f"[ERROR] Missing required env: {name}")
    return v


@dataclass
class MySQLAccount:
    name: str
    host: str
    port: str
    username: str
    password: str
    database: str


# 계정 정보 정규화 (키 이름 변형을 허용)

def _normalize_account(raw: dict[str, Any], fallback_name: str) -> MySQLAccount:
    name = str(raw.get("name") or fallback_name)
    host = raw.get("host") or raw.get("hostname")
    username = raw.get("username") or raw.get("user")
    password = raw.get("password")
    port = raw.get("port") or 3306
    database = raw.get("database") or raw.get("schema") or ""
    if not host or not username or password is None:
        raise SystemExit("[ERROR] Invalid account entry: host/username/password are required")
    return MySQLAccount(
        name=name,
        host=str(host),
        port=str(port),
        username=str(username),
        password=str(password),
        database=str(database),
    )


# 환경변수에서 여러 계정 정보를 파싱

def _load_accounts() -> list[MySQLAccount]:
    raw = _env("MYSQL_ACCOUNTS")
    if raw:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"[ERROR] MYSQL_ACCOUNTS is not valid JSON: {exc}")

        accounts: list[MySQLAccount] = []
        if isinstance(data, list):
            for idx, item in enumerate(data):
                if not isinstance(item, dict):
                    raise SystemExit("[ERROR] MYSQL_ACCOUNTS list items must be objects")
                accounts.append(_normalize_account(item, f"account_{idx + 1}"))
        elif isinstance(data, dict):
            if all(isinstance(v, dict) for v in data.values()):
                for key, value in data.items():
                    value = dict(value)
                    value.setdefault("name", key)
                    accounts.append(_normalize_account(value, key))
            else:
                accounts.append(_normalize_account(data, "default"))
        else:
            raise SystemExit("[ERROR] MYSQL_ACCOUNTS must be a JSON array or object")

        if not accounts:
            raise SystemExit("[ERROR] MYSQL_ACCOUNTS is empty")
        return accounts

    # 단일 계정 모드 (기존 환경변수 호환)
    host = _require_env("MYSQL_HOST")
    username = _require_env("MYSQL_USERNAME")
    password = _require_env("MYSQL_PASSWORD")
    port = _env("MYSQL_PORT") or "3306"
    database = _env("MYSQL_DATABASE") or ""
    return [
        MySQLAccount(
            name="default",
            host=host,
            port=port,
            username=username,
            password=password,
            database=database,
        )
    ]


# 계정 선택 로직

def _select_account(accounts: list[MySQLAccount], account_name: str | None) -> MySQLAccount:
    if account_name:
        for account in accounts:
            if account.name == account_name:
                return account
        names = ", ".join(a.name for a in accounts)
        raise SystemExit(f"[ERROR] Unknown account '{account_name}'. Available: {names}")

    if len(accounts) == 1:
        return accounts[0]

    default_name = _env("MYSQL_DEFAULT_ACCOUNT")
    if default_name:
        for account in accounts:
            if account.name == default_name:
                return account
        names = ", ".join(a.name for a in accounts)
        raise SystemExit(f"[ERROR] MYSQL_DEFAULT_ACCOUNT='{default_name}' not found. Available: {names}")

    names = ", ".join(a.name for a in accounts)
    raise SystemExit(f"[ERROR] Multiple accounts found. Use --account. Available: {names}")


# MySQL CLI 호출

def _run_mysql(sql: str, account: MySQLAccount, schema: str | None) -> subprocess.CompletedProcess:
    if not shutil.which("mysql"):
        raise SystemExit("[ERROR] mysql client not found. Install mysql client (or use a container).")

    cmd = [
        "mysql",
        "--protocol=TCP",
        f"--host={account.host}",
        f"--port={account.port}",
        f"--user={account.username}",
        "--batch",
        "--silent",
        "--default-character-set=utf8mb4",
        "--column-names",
        "--execute",
        sql,
    ]
    if schema:
        cmd.insert(-2, f"--database={schema}")

    env = os.environ.copy()
    env["MYSQL_PWD"] = account.password

    return subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )


# mysql --batch 출력 문자열 디코딩

def _unescape_mysql(value: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(value):
        c = value[i]
        if c == "\\" and i + 1 < len(value):
            nxt = value[i + 1]
            if nxt == "t":
                out.append("\t")
            elif nxt == "n":
                out.append("\n")
            elif nxt == "r":
                out.append("\r")
            elif nxt == "0":
                out.append("\0")
            elif nxt == "Z":
                out.append("\x1a")
            elif nxt == "b":
                out.append("\b")
            elif nxt == "\\":
                out.append("\\")
            elif nxt == "\"":
                out.append("\"")
            elif nxt == "'":
                out.append("'")
            else:
                out.append(nxt)
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


# TSV 결과를 JSON 형태로 변환

def _parse_tsv(output: str) -> tuple[list[str], list[dict[str, Any]]]:
    lines = output.splitlines()
    if not lines:
        return [], []

    columns = [_unescape_mysql(cell) for cell in lines[0].split("\t")]
    rows: list[dict[str, Any]] = []
    for line in lines[1:]:
        cells = line.split("\t")
        row: dict[str, Any] = {}
        for idx, col in enumerate(columns):
            cell = cells[idx] if idx < len(cells) else ""
            if cell == r"\N":
                value: Any = None
            else:
                value = _unescape_mysql(cell)
            row[col] = value
        rows.append(row)
    return columns, rows


# 안전한 쿼리 제한 (읽기 전용)

def _normalize_query(query: str) -> str:
    q = query.strip()
    if q.endswith(";"):
        q = q[:-1].strip()
    if not q:
        raise SystemExit("[ERROR] Empty query")

    first_token = q.split(None, 1)[0].upper()
    allowed = {"SELECT", "WITH", "EXPLAIN", "SHOW", "DESCRIBE", "DESC"}
    if first_token not in allowed:
        raise SystemExit("[ERROR] Only read-only queries are allowed (SELECT/SHOW/DESCRIBE/EXPLAIN/WITH)")
    return q


# 계정/스키마 선택 헬퍼

def _resolve_schema(account: MySQLAccount, schema_arg: str | None) -> str | None:
    if schema_arg:
        return schema_arg
    default_schema = _env("MYSQL_DEFAULT_SCHEMA")
    if default_schema:
        return default_schema
    return account.database or None


def cmd_test(args: argparse.Namespace) -> None:
    account = _select_account(_load_accounts(), args.account)
    schema = _resolve_schema(account, args.schema)
    sql = "SELECT 1 AS ok"
    proc = _run_mysql(sql, account, schema)
    if proc.returncode == 0:
        print("{\"connected\":true}")
        raise SystemExit(0)
    err = proc.stderr.strip().replace("\"", "\\\"")
    print(f"{{\"connected\":false,\"error\":\"{err}\"}}")
    raise SystemExit(proc.returncode or 2)


def cmd_select(args: argparse.Namespace) -> None:
    account = _select_account(_load_accounts(), args.account)
    schema = _resolve_schema(account, args.schema)

    if args.query is not None:
        query = args.query
    elif args.query_file is not None:
        with open(args.query_file, "r", encoding="utf-8") as f:
            query = f.read()
    else:
        if sys.stdin.isatty():
            raise SystemExit("[ERROR] Provide --query/--query-file or pipe SQL via stdin.")
        query = sys.stdin.read()

    query = _normalize_query(query)

    proc = _run_mysql(query, account, schema)
    if proc.returncode != 0:
        err = proc.stderr.strip()
        raise SystemExit(f"[ERROR] mysql failed: {err}")

    columns, rows = _parse_tsv(proc.stdout)
    payload = {"columns": columns, "rows": rows, "rowCount": len(rows)}
    print(json.dumps(payload, ensure_ascii=True))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="MySQL CLI (no MCP required)")
    p.add_argument("--account", help="Account name from MYSQL_ACCOUNTS")
    p.add_argument("--schema", "--database", dest="schema", help="Override schema/database")
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("test", help="Test MySQL connection")
    t.set_defaults(func=cmd_test)

    s = sub.add_parser("select", help="Execute read-only query")
    s.add_argument("--query", help="Query string")
    s.add_argument("--query-file", help="Path to a .sql file")
    s.set_defaults(func=cmd_select)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
