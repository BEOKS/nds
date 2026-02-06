#!/usr/bin/env python3
"""
mysql_cli.py 단위 테스트

mock을 사용하여 외부 의존성(MySQL 클라이언트)을 격리하고
각 함수의 정상/에러 케이스를 테스트
"""
import json
import sys
from pathlib import Path
from unittest import mock

import pytest

# 테스트 대상 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from mysql_cli import (
    MySQLAccount,
    _env,
    _require_env,
    _normalize_account,
    _load_accounts,
    _select_account,
    _run_mysql,
    _unescape_mysql,
    _parse_tsv,
    _normalize_query,
    _resolve_schema,
    cmd_test,
    cmd_select,
    build_parser,
)


# ========== 헬퍼 함수 테스트 ==========

def test_env_returns_stripped_value():
    """환경변수 값을 공백 제거 후 반환"""
    with mock.patch.dict("os.environ", {"TEST_VAR": "  value  "}):
        assert _env("TEST_VAR") == "value"


def test_env_returns_none_for_missing():
    """존재하지 않는 환경변수는 None 반환"""
    with mock.patch.dict("os.environ", {}, clear=True):
        assert _env("NONEXISTENT") is None


def test_env_returns_none_for_empty():
    """공백만 있는 환경변수는 None 반환"""
    with mock.patch.dict("os.environ", {"EMPTY": "   "}):
        assert _env("EMPTY") is None


def test_require_env_returns_value():
    """필수 환경변수가 있으면 값 반환"""
    with mock.patch.dict("os.environ", {"REQUIRED": "value"}):
        assert _require_env("REQUIRED") == "value"


def test_require_env_raises_on_missing():
    """필수 환경변수가 없으면 SystemExit 발생"""
    with mock.patch.dict("os.environ", {}, clear=True):
        with pytest.raises(SystemExit) as exc_info:
            _require_env("MISSING_VAR")
        assert "Missing required env" in str(exc_info.value)


# ========== MySQLAccount 데이터클래스 테스트 ==========

def test_mysql_account_creation():
    """MySQLAccount 데이터클래스 생성"""
    account = MySQLAccount(
        name="test",
        host="localhost",
        port="3306",
        username="user",
        password="pass",
        database="testdb",
    )
    assert account.name == "test"
    assert account.host == "localhost"
    assert account.port == "3306"


# ========== 계정 정규화 테스트 ==========

def test_normalize_account_full_fields():
    """모든 필드가 있는 경우"""
    raw = {
        "name": "test",
        "host": "localhost",
        "port": 3306,
        "username": "user",
        "password": "pass",
        "database": "testdb",
    }
    account = _normalize_account(raw, "fallback")
    assert account.name == "test"
    assert account.host == "localhost"
    assert account.port == "3306"
    assert account.username == "user"
    assert account.password == "pass"
    assert account.database == "testdb"


def test_normalize_account_hostname_alias():
    """host 대신 hostname 사용 가능"""
    raw = {"hostname": "localhost", "username": "user", "password": "pass"}
    account = _normalize_account(raw, "fallback")
    assert account.host == "localhost"


def test_normalize_account_user_alias():
    """username 대신 user 사용 가능"""
    raw = {"host": "localhost", "user": "testuser", "password": "pass"}
    account = _normalize_account(raw, "fallback")
    assert account.username == "testuser"


def test_normalize_account_schema_alias():
    """database 대신 schema 사용 가능"""
    raw = {"host": "localhost", "username": "user", "password": "pass", "schema": "testdb"}
    account = _normalize_account(raw, "fallback")
    assert account.database == "testdb"


def test_normalize_account_defaults():
    """기본값 적용 (port, database)"""
    raw = {"host": "localhost", "username": "user", "password": "pass"}
    account = _normalize_account(raw, "fallback")
    assert account.port == "3306"
    assert account.database == ""


def test_normalize_account_fallback_name():
    """name이 없으면 fallback 사용"""
    raw = {"host": "localhost", "username": "user", "password": "pass"}
    account = _normalize_account(raw, "default_name")
    assert account.name == "default_name"


def test_normalize_account_missing_required():
    """필수 필드(host, username, password)가 없으면 에러"""
    with pytest.raises(SystemExit) as exc_info:
        _normalize_account({"host": "localhost"}, "fallback")
    assert "Invalid account entry" in str(exc_info.value)


# ========== 계정 로드 테스트 ==========

def test_load_accounts_from_json_array():
    """MYSQL_ACCOUNTS가 배열 형태인 경우"""
    accounts_json = json.dumps([
        {"name": "acc1", "host": "host1", "username": "user1", "password": "pass1"},
        {"name": "acc2", "host": "host2", "username": "user2", "password": "pass2"},
    ])
    with mock.patch.dict("os.environ", {"MYSQL_ACCOUNTS": accounts_json}, clear=True):
        accounts = _load_accounts()
        assert len(accounts) == 2
        assert accounts[0].name == "acc1"
        assert accounts[1].name == "acc2"


def test_load_accounts_from_json_object():
    """MYSQL_ACCOUNTS가 객체 형태인 경우"""
    accounts_json = json.dumps({
        "prod": {"host": "prod-host", "username": "prod-user", "password": "prod-pass"},
        "dev": {"host": "dev-host", "username": "dev-user", "password": "dev-pass"},
    })
    with mock.patch.dict("os.environ", {"MYSQL_ACCOUNTS": accounts_json}, clear=True):
        accounts = _load_accounts()
        assert len(accounts) == 2
        names = {a.name for a in accounts}
        assert "prod" in names
        assert "dev" in names


def test_load_accounts_from_json_single_object():
    """MYSQL_ACCOUNTS가 단일 계정 객체인 경우"""
    accounts_json = json.dumps({
        "host": "localhost",
        "username": "user",
        "password": "pass",
    })
    with mock.patch.dict("os.environ", {"MYSQL_ACCOUNTS": accounts_json}, clear=True):
        accounts = _load_accounts()
        assert len(accounts) == 1
        assert accounts[0].name == "default"


def test_load_accounts_from_legacy_env():
    """MYSQL_ACCOUNTS 없이 레거시 환경변수 사용"""
    env_vars = {
        "MYSQL_HOST": "localhost",
        "MYSQL_USERNAME": "user",
        "MYSQL_PASSWORD": "pass",
        "MYSQL_PORT": "3307",
        "MYSQL_DATABASE": "testdb",
    }
    with mock.patch.dict("os.environ", env_vars, clear=True):
        accounts = _load_accounts()
        assert len(accounts) == 1
        assert accounts[0].name == "default"
        assert accounts[0].host == "localhost"
        assert accounts[0].port == "3307"
        assert accounts[0].database == "testdb"


def test_load_accounts_json_invalid():
    """MYSQL_ACCOUNTS가 잘못된 JSON이면 에러"""
    with mock.patch.dict("os.environ", {"MYSQL_ACCOUNTS": "NOT JSON"}, clear=True):
        with pytest.raises(SystemExit) as exc_info:
            _load_accounts()
        assert "not valid JSON" in str(exc_info.value)


def test_load_accounts_empty_array():
    """MYSQL_ACCOUNTS가 빈 배열이면 에러"""
    with mock.patch.dict("os.environ", {"MYSQL_ACCOUNTS": "[]"}, clear=True):
        with pytest.raises(SystemExit) as exc_info:
            _load_accounts()
        assert "empty" in str(exc_info.value)


# ========== 계정 선택 테스트 ==========

def test_select_account_by_name():
    """--account 인자로 계정 선택"""
    accounts = [
        MySQLAccount("acc1", "host1", "3306", "user1", "pass1", ""),
        MySQLAccount("acc2", "host2", "3306", "user2", "pass2", ""),
    ]
    result = _select_account(accounts, "acc2")
    assert result.name == "acc2"


def test_select_account_not_found():
    """존재하지 않는 계정 이름이면 에러"""
    accounts = [MySQLAccount("acc1", "host1", "3306", "user1", "pass1", "")]
    with pytest.raises(SystemExit) as exc_info:
        _select_account(accounts, "nonexistent")
    assert "Unknown account" in str(exc_info.value)


def test_select_account_single_default():
    """계정이 하나뿐이면 자동 선택"""
    accounts = [MySQLAccount("only", "host", "3306", "user", "pass", "")]
    result = _select_account(accounts, None)
    assert result.name == "only"


def test_select_account_multiple_with_default_env():
    """여러 계정 중 MYSQL_DEFAULT_ACCOUNT로 선택"""
    accounts = [
        MySQLAccount("acc1", "host1", "3306", "user1", "pass1", ""),
        MySQLAccount("acc2", "host2", "3306", "user2", "pass2", ""),
    ]
    with mock.patch.dict("os.environ", {"MYSQL_DEFAULT_ACCOUNT": "acc2"}):
        result = _select_account(accounts, None)
        assert result.name == "acc2"


def test_select_account_multiple_no_default():
    """여러 계정이 있는데 기본값이 없으면 에러"""
    accounts = [
        MySQLAccount("acc1", "host1", "3306", "user1", "pass1", ""),
        MySQLAccount("acc2", "host2", "3306", "user2", "pass2", ""),
    ]
    with mock.patch.dict("os.environ", {}, clear=True):
        with pytest.raises(SystemExit) as exc_info:
            _select_account(accounts, None)
        assert "Multiple accounts" in str(exc_info.value)


# ========== MySQL 실행 테스트 ==========

def test_run_mysql_client_not_found():
    """mysql 클라이언트가 없으면 에러"""
    account = MySQLAccount("test", "localhost", "3306", "user", "pass", "testdb")

    with mock.patch("shutil.which", return_value=None):
        with pytest.raises(SystemExit) as exc_info:
            _run_mysql("SELECT 1", account, None)
        assert "mysql client not found" in str(exc_info.value)


def test_run_mysql_success():
    """정상적인 mysql 실행"""
    account = MySQLAccount("test", "localhost", "3306", "user", "pass", "testdb")

    mock_proc = mock.Mock()
    mock_proc.returncode = 0
    mock_proc.stdout = "1\n"
    mock_proc.stderr = ""

    with mock.patch("shutil.which", return_value="/usr/bin/mysql"):
        with mock.patch("subprocess.run", return_value=mock_proc) as mock_run:
            result = _run_mysql("SELECT 1", account, None)
            assert result.returncode == 0
            # MYSQL_PWD 환경변수 확인
            call_kwargs = mock_run.call_args[1]
            assert call_kwargs["env"]["MYSQL_PWD"] == "pass"


def test_run_mysql_with_schema():
    """--schema 인자로 데이터베이스 지정"""
    account = MySQLAccount("test", "localhost", "3306", "user", "pass", "")

    mock_proc = mock.Mock()
    mock_proc.returncode = 0
    mock_proc.stdout = ""
    mock_proc.stderr = ""

    with mock.patch("shutil.which", return_value="/usr/bin/mysql"):
        with mock.patch("subprocess.run", return_value=mock_proc) as mock_run:
            _run_mysql("SELECT 1", account, "custom_db")
            # --database 인자 확인
            call_args = mock_run.call_args[0][0]
            assert "--database=custom_db" in call_args


# ========== MySQL 이스케이프 해제 테스트 ==========

def test_unescape_mysql_tab():
    """\\t를 탭 문자로 변환"""
    assert _unescape_mysql("hello\\tworld") == "hello\tworld"


def test_unescape_mysql_newline():
    """\\n을 개행 문자로 변환"""
    assert _unescape_mysql("line1\\nline2") == "line1\nline2"


def test_unescape_mysql_carriage_return():
    """\\r을 캐리지 리턴으로 변환"""
    assert _unescape_mysql("text\\rmore") == "text\rmore"


def test_unescape_mysql_null():
    """\\0을 NULL 문자로 변환"""
    assert _unescape_mysql("text\\0end") == "text\0end"


def test_unescape_mysql_backslash():
    """\\\\를 백슬래시로 변환"""
    assert _unescape_mysql("path\\\\to\\\\file") == "path\\to\\file"


def test_unescape_mysql_no_escape():
    """이스케이프가 없는 일반 문자열"""
    assert _unescape_mysql("hello world") == "hello world"


# ========== TSV 파싱 테스트 ==========

def test_parse_tsv_single_row():
    """단일 행 TSV 파싱"""
    output = "id\tname\n1\tAlice"
    columns, rows = _parse_tsv(output)
    assert columns == ["id", "name"]
    assert len(rows) == 1
    assert rows[0]["id"] == "1"
    assert rows[0]["name"] == "Alice"


def test_parse_tsv_multiple_rows():
    """여러 행 TSV 파싱"""
    output = "id\tname\n1\tAlice\n2\tBob"
    columns, rows = _parse_tsv(output)
    assert len(rows) == 2
    assert rows[1]["id"] == "2"
    assert rows[1]["name"] == "Bob"


def test_parse_tsv_null_value():
    """NULL 값(\\N) 처리"""
    output = "id\tname\n1\t\\N"
    columns, rows = _parse_tsv(output)
    assert rows[0]["name"] is None


def test_parse_tsv_empty():
    """빈 출력"""
    columns, rows = _parse_tsv("")
    assert columns == []
    assert rows == []


def test_parse_tsv_with_escapes():
    """이스케이프 문자 포함"""
    output = "text\nhello\\tworld"
    columns, rows = _parse_tsv(output)
    assert rows[0]["text"] == "hello\tworld"


# ========== 쿼리 정규화 테스트 ==========

def test_normalize_query_removes_semicolon():
    """세미콜론 제거"""
    result = _normalize_query("SELECT * FROM users;")
    assert result == "SELECT * FROM users"


def test_normalize_query_strips_whitespace():
    """공백 제거"""
    result = _normalize_query("  SELECT * FROM users  ")
    assert result == "SELECT * FROM users"


def test_normalize_query_allows_select():
    """SELECT 쿼리 허용"""
    result = _normalize_query("SELECT * FROM users")
    assert result == "SELECT * FROM users"


def test_normalize_query_allows_with():
    """WITH (CTE) 쿼리 허용"""
    result = _normalize_query("WITH cte AS (SELECT 1) SELECT * FROM cte")
    assert result.startswith("WITH")


def test_normalize_query_allows_show():
    """SHOW 명령 허용"""
    result = _normalize_query("SHOW TABLES")
    assert result == "SHOW TABLES"


def test_normalize_query_allows_describe():
    """DESCRIBE 명령 허용"""
    result = _normalize_query("DESCRIBE users")
    assert result == "DESCRIBE users"


def test_normalize_query_allows_explain():
    """EXPLAIN 명령 허용"""
    result = _normalize_query("EXPLAIN SELECT * FROM users")
    assert result == "EXPLAIN SELECT * FROM users"


def test_normalize_query_rejects_insert():
    """INSERT 쿼리 거부"""
    with pytest.raises(SystemExit) as exc_info:
        _normalize_query("INSERT INTO users VALUES (1)")
    assert "Only read-only queries" in str(exc_info.value)


def test_normalize_query_rejects_update():
    """UPDATE 쿼리 거부"""
    with pytest.raises(SystemExit) as exc_info:
        _normalize_query("UPDATE users SET name='test'")
    assert "Only read-only queries" in str(exc_info.value)


def test_normalize_query_rejects_delete():
    """DELETE 쿼리 거부"""
    with pytest.raises(SystemExit) as exc_info:
        _normalize_query("DELETE FROM users")
    assert "Only read-only queries" in str(exc_info.value)


def test_normalize_query_empty():
    """빈 쿼리 거부"""
    with pytest.raises(SystemExit) as exc_info:
        _normalize_query("   ")
    assert "Empty query" in str(exc_info.value)


# ========== 스키마 선택 테스트 ==========

def test_resolve_schema_from_arg():
    """--schema 인자 우선"""
    account = MySQLAccount("test", "localhost", "3306", "user", "pass", "default_db")
    result = _resolve_schema(account, "custom_db")
    assert result == "custom_db"


def test_resolve_schema_from_env():
    """MYSQL_DEFAULT_SCHEMA 환경변수"""
    account = MySQLAccount("test", "localhost", "3306", "user", "pass", "default_db")
    with mock.patch.dict("os.environ", {"MYSQL_DEFAULT_SCHEMA": "env_db"}):
        result = _resolve_schema(account, None)
        assert result == "env_db"


def test_resolve_schema_from_account():
    """계정의 database 필드 사용"""
    account = MySQLAccount("test", "localhost", "3306", "user", "pass", "account_db")
    with mock.patch.dict("os.environ", {}, clear=True):
        result = _resolve_schema(account, None)
        assert result == "account_db"


def test_resolve_schema_none():
    """모든 소스가 없으면 None"""
    account = MySQLAccount("test", "localhost", "3306", "user", "pass", "")
    with mock.patch.dict("os.environ", {}, clear=True):
        result = _resolve_schema(account, None)
        assert result is None


# ========== 명령어 테스트 (test) ==========

def test_cmd_test_success(capsys):
    """연결 테스트 성공"""
    env_vars = {
        "MYSQL_HOST": "localhost",
        "MYSQL_USERNAME": "user",
        "MYSQL_PASSWORD": "pass",
    }

    args = mock.Mock()
    args.account = None
    args.schema = None

    mock_proc = mock.Mock()
    mock_proc.returncode = 0
    mock_proc.stdout = "ok\n1"
    mock_proc.stderr = ""

    with mock.patch.dict("os.environ", env_vars, clear=True):
        with mock.patch("shutil.which", return_value="/usr/bin/mysql"):
            with mock.patch("subprocess.run", return_value=mock_proc):
                with pytest.raises(SystemExit) as exc_info:
                    cmd_test(args)
                assert exc_info.value.code == 0

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["connected"] is True


def test_cmd_test_failure(capsys):
    """연결 테스트 실패"""
    env_vars = {
        "MYSQL_HOST": "localhost",
        "MYSQL_USERNAME": "user",
        "MYSQL_PASSWORD": "pass",
    }

    args = mock.Mock()
    args.account = None
    args.schema = None

    mock_proc = mock.Mock()
    mock_proc.returncode = 1
    mock_proc.stdout = ""
    mock_proc.stderr = "Connection failed"

    with mock.patch.dict("os.environ", env_vars, clear=True):
        with mock.patch("shutil.which", return_value="/usr/bin/mysql"):
            with mock.patch("subprocess.run", return_value=mock_proc):
                with pytest.raises(SystemExit) as exc_info:
                    cmd_test(args)
                assert exc_info.value.code != 0

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["connected"] is False


# ========== 명령어 테스트 (select) ==========

def test_cmd_select_with_query_arg(capsys):
    """--query 인자로 쿼리 실행"""
    env_vars = {
        "MYSQL_HOST": "localhost",
        "MYSQL_USERNAME": "user",
        "MYSQL_PASSWORD": "pass",
    }

    args = mock.Mock()
    args.account = None
    args.schema = None
    args.query = "SELECT * FROM users"
    args.query_file = None

    mock_proc = mock.Mock()
    mock_proc.returncode = 0
    mock_proc.stdout = "id\tname\n1\tAlice"
    mock_proc.stderr = ""

    with mock.patch.dict("os.environ", env_vars, clear=True):
        with mock.patch("shutil.which", return_value="/usr/bin/mysql"):
            with mock.patch("subprocess.run", return_value=mock_proc):
                cmd_select(args)

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert len(result["rows"]) == 1
    assert result["rows"][0]["name"] == "Alice"


def test_cmd_select_with_query_file(tmp_path, capsys):
    """--query-file로 쿼리 실행"""
    env_vars = {
        "MYSQL_HOST": "localhost",
        "MYSQL_USERNAME": "user",
        "MYSQL_PASSWORD": "pass",
    }

    query_file = tmp_path / "query.sql"
    query_file.write_text("SELECT * FROM users", encoding="utf-8")

    args = mock.Mock()
    args.account = None
    args.schema = None
    args.query = None
    args.query_file = str(query_file)

    mock_proc = mock.Mock()
    mock_proc.returncode = 0
    mock_proc.stdout = "id\n1"
    mock_proc.stderr = ""

    with mock.patch.dict("os.environ", env_vars, clear=True):
        with mock.patch("shutil.which", return_value="/usr/bin/mysql"):
            with mock.patch("subprocess.run", return_value=mock_proc):
                cmd_select(args)

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["rowCount"] == 1


def test_cmd_select_from_stdin(capsys):
    """stdin으로 쿼리 입력"""
    env_vars = {
        "MYSQL_HOST": "localhost",
        "MYSQL_USERNAME": "user",
        "MYSQL_PASSWORD": "pass",
    }

    args = mock.Mock()
    args.account = None
    args.schema = None
    args.query = None
    args.query_file = None

    mock_proc = mock.Mock()
    mock_proc.returncode = 0
    mock_proc.stdout = "count\n42"
    mock_proc.stderr = ""

    with mock.patch.dict("os.environ", env_vars, clear=True):
        with mock.patch("sys.stdin.isatty", return_value=False):
            with mock.patch("sys.stdin.read", return_value="SELECT COUNT(*) AS count FROM users"):
                with mock.patch("shutil.which", return_value="/usr/bin/mysql"):
                    with mock.patch("subprocess.run", return_value=mock_proc):
                        cmd_select(args)

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["rows"][0]["count"] == "42"


def test_cmd_select_stdin_tty_error():
    """stdin이 tty인데 쿼리가 없으면 에러"""
    env_vars = {
        "MYSQL_HOST": "localhost",
        "MYSQL_USERNAME": "user",
        "MYSQL_PASSWORD": "pass",
    }

    args = mock.Mock()
    args.account = None
    args.schema = None
    args.query = None
    args.query_file = None

    with mock.patch.dict("os.environ", env_vars, clear=True):
        with mock.patch("sys.stdin.isatty", return_value=True):
            with pytest.raises(SystemExit) as exc_info:
                cmd_select(args)
            assert "Provide --query" in str(exc_info.value)


def test_cmd_select_rejects_non_select():
    """SELECT가 아닌 쿼리는 거부"""
    env_vars = {
        "MYSQL_HOST": "localhost",
        "MYSQL_USERNAME": "user",
        "MYSQL_PASSWORD": "pass",
    }

    args = mock.Mock()
    args.account = None
    args.schema = None
    args.query = "DROP TABLE users"
    args.query_file = None

    with mock.patch.dict("os.environ", env_vars, clear=True):
        with pytest.raises(SystemExit) as exc_info:
            cmd_select(args)
        assert "Only read-only queries" in str(exc_info.value)


def test_cmd_select_mysql_error():
    """mysql 실행 실패"""
    env_vars = {
        "MYSQL_HOST": "localhost",
        "MYSQL_USERNAME": "user",
        "MYSQL_PASSWORD": "pass",
    }

    args = mock.Mock()
    args.account = None
    args.schema = None
    args.query = "SELECT * FROM users"
    args.query_file = None

    mock_proc = mock.Mock()
    mock_proc.returncode = 1
    mock_proc.stdout = ""
    mock_proc.stderr = "Table doesn't exist"

    with mock.patch.dict("os.environ", env_vars, clear=True):
        with mock.patch("shutil.which", return_value="/usr/bin/mysql"):
            with mock.patch("subprocess.run", return_value=mock_proc):
                with pytest.raises(SystemExit) as exc_info:
                    cmd_select(args)
                assert "mysql failed" in str(exc_info.value)


# ========== 파서 테스트 ==========

def test_build_parser():
    """argparse 파서 생성 확인"""
    parser = build_parser()
    assert parser is not None

    # test 서브커맨드
    args = parser.parse_args(["test"])
    assert args.cmd == "test"

    # select 서브커맨드
    args = parser.parse_args(["select", "--query", "SELECT 1"])
    assert args.cmd == "select"
    assert args.query == "SELECT 1"

    # --account 옵션
    args = parser.parse_args(["--account", "prod", "test"])
    assert args.account == "prod"
