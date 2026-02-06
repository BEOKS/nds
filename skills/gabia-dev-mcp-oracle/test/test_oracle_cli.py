#!/usr/bin/env python3
"""
oracle_cli.py 단위 테스트

mock을 사용하여 외부 의존성(Java, JDBC, sqlplus)을 격리하고
각 함수의 정상/에러 케이스를 테스트
"""
import sys
from pathlib import Path
from unittest import mock

import pytest

# 테스트 대상 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from oracle_cli import (
    _env,
    _require_env,
    _oracle_config,
    _jdbc_url,
    _find_ojdbc_jar,
    _run_java,
    _sqlplus_login,
    _run_sqlplus,
    _normalize_query,
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


# ========== Oracle 설정 테스트 ==========

def test_oracle_config_with_service_name():
    """ORACLE_SERVICE_NAME이 있는 경우"""
    env_vars = {
        "ORACLE_HOST": "localhost",
        "ORACLE_USERNAME": "testuser",
        "ORACLE_PASSWORD": "testpass",
        "ORACLE_PORT": "1521",
        "ORACLE_SERVICE_NAME": "TESTSERVICE",
    }
    with mock.patch.dict("os.environ", env_vars, clear=True):
        config = _oracle_config()
        assert config["host"] == "localhost"
        assert config["username"] == "testuser"
        assert config["password"] == "testpass"
        assert config["port"] == "1521"
        assert config["service"] == "TESTSERVICE"


def test_oracle_config_with_sid_only():
    """ORACLE_SID만 있는 경우 (SERVICE_NAME 없음)"""
    env_vars = {
        "ORACLE_HOST": "localhost",
        "ORACLE_USERNAME": "testuser",
        "ORACLE_PASSWORD": "testpass",
        "ORACLE_SID": "TESTSID",
    }
    with mock.patch.dict("os.environ", env_vars, clear=True):
        config = _oracle_config()
        assert config["sid"] == "TESTSID"
        assert config["service"] == ""


def test_oracle_config_defaults():
    """포트와 SID 기본값 확인"""
    env_vars = {
        "ORACLE_HOST": "localhost",
        "ORACLE_USERNAME": "testuser",
        "ORACLE_PASSWORD": "testpass",
    }
    with mock.patch.dict("os.environ", env_vars, clear=True):
        config = _oracle_config()
        assert config["port"] == "1521"
        assert config["sid"] == "DEVGABIA"


def test_oracle_config_missing_required():
    """필수 환경변수가 없으면 에러"""
    with mock.patch.dict("os.environ", {}, clear=True):
        with pytest.raises(SystemExit):
            _oracle_config()


# ========== JDBC URL 생성 테스트 ==========

def test_jdbc_url_with_service_name():
    """SERVICE_NAME이 있으면 service 형식 URL"""
    config = {
        "host": "localhost",
        "port": "1521",
        "service": "TESTSERVICE",
        "sid": "TESTSID",
        "username": "user",
        "password": "pass",
    }
    url = _jdbc_url(config)
    assert url == "jdbc:oracle:thin:@//localhost:1521/TESTSERVICE"


def test_jdbc_url_with_sid_only():
    """SERVICE_NAME이 없으면 SID 형식 URL"""
    config = {
        "host": "localhost",
        "port": "1521",
        "service": "",
        "sid": "TESTSID",
        "username": "user",
        "password": "pass",
    }
    url = _jdbc_url(config)
    assert url == "jdbc:oracle:thin:@localhost:1521:TESTSID"


# ========== OJDBC JAR 검색 테스트 ==========

def test_find_ojdbc_jar_from_env(tmp_path):
    """ORACLE_JDBC_JAR 환경변수로 JAR 경로 지정"""
    jar_file = tmp_path / "ojdbc8.jar"
    jar_file.touch()

    with mock.patch.dict("os.environ", {"ORACLE_JDBC_JAR": str(jar_file)}):
        result = _find_ojdbc_jar()
        assert result == jar_file.resolve()


def test_find_ojdbc_jar_not_found():
    """JAR를 찾을 수 없으면 None 반환"""
    with mock.patch.dict("os.environ", {}, clear=True):
        with mock.patch.object(Path, "exists", return_value=False):
            result = _find_ojdbc_jar()
            assert result is None


def test_find_ojdbc_jar_from_gradle_cache(tmp_path):
    """Gradle 캐시에서 JAR 자동 검색"""
    gradle_cache = tmp_path / ".gradle" / "caches" / "modules-2" / "files-2.1" / "com.oracle" / "ojdbc8"
    gradle_cache.mkdir(parents=True)
    jar_file = gradle_cache / "ojdbc8-21.1.0.0.jar"
    jar_file.touch()

    with mock.patch.dict("os.environ", {}, clear=True):
        with mock.patch.object(Path, "home", return_value=tmp_path):
            result = _find_ojdbc_jar()
            assert result is not None
            assert "ojdbc" in result.name


# ========== Java 실행 테스트 ==========

def test_run_java_missing_jar():
    """JDBC JAR가 없으면 에러"""
    config = {"host": "localhost", "port": "1521", "username": "user", "password": "pass", "sid": "SID", "service": ""}

    with mock.patch("oracle_cli._find_ojdbc_jar", return_value=None):
        with pytest.raises(SystemExit) as exc_info:
            _run_java("test", config, None)
        assert "JDBC jar not found" in str(exc_info.value)


def test_run_java_missing_javac():
    """javac가 없으면 에러"""
    config = {"host": "localhost", "port": "1521", "username": "user", "password": "pass", "sid": "SID", "service": ""}

    with mock.patch("oracle_cli._find_ojdbc_jar", return_value=Path("/tmp/ojdbc.jar")):
        with mock.patch("shutil.which", side_effect=lambda x: None if x == "javac" else "/usr/bin/java"):
            with pytest.raises(SystemExit) as exc_info:
                _run_java("test", config, None)
            assert "java/javac not found" in str(exc_info.value)


def test_run_java_compile_failure(tmp_path):
    """javac 컴파일 실패 시 에러"""
    config = {"host": "localhost", "port": "1521", "username": "user", "password": "pass", "sid": "SID", "service": ""}
    jar_file = tmp_path / "ojdbc.jar"
    jar_file.touch()

    mock_compile = mock.Mock()
    mock_compile.returncode = 1
    mock_compile.stderr = "Compilation error"

    with mock.patch("oracle_cli._find_ojdbc_jar", return_value=jar_file):
        with mock.patch("shutil.which", return_value="/usr/bin/javac"):
            with mock.patch("subprocess.run", return_value=mock_compile):
                with pytest.raises(SystemExit) as exc_info:
                    _run_java("test", config, None)
                assert "javac failed" in str(exc_info.value)


def test_run_java_success(tmp_path):
    """정상적인 Java 실행"""
    config = {"host": "localhost", "port": "1521", "username": "user", "password": "pass", "sid": "SID", "service": ""}
    jar_file = tmp_path / "ojdbc.jar"
    jar_file.touch()

    mock_compile = mock.Mock()
    mock_compile.returncode = 0

    mock_run = mock.Mock()
    mock_run.returncode = 0
    mock_run.stdout = b'{"connected":true}'
    mock_run.stderr = b''

    with mock.patch("oracle_cli._find_ojdbc_jar", return_value=jar_file):
        with mock.patch("shutil.which", return_value="/usr/bin/java"):
            with mock.patch("subprocess.run", side_effect=[mock_compile, mock_run]):
                result = _run_java("test", config, None)
                assert result == 0


# ========== sqlplus 로그인 문자열 테스트 ==========

def test_sqlplus_login_with_service():
    """SERVICE_NAME이 있는 경우 로그인 문자열"""
    config = {
        "host": "localhost",
        "port": "1521",
        "service": "TESTSERVICE",
        "username": "testuser",
        "password": "testpass",
        "sid": "",
    }
    login = _sqlplus_login(config)
    assert login == "testuser/testpass@localhost:1521/TESTSERVICE"


def test_sqlplus_login_with_sid():
    """SID만 있는 경우 로그인 문자열"""
    config = {
        "host": "localhost",
        "port": "1521",
        "service": "",
        "username": "testuser",
        "password": "testpass",
        "sid": "TESTSID",
    }
    login = _sqlplus_login(config)
    assert login == "testuser/testpass@localhost:1521:TESTSID"


# ========== sqlplus 실행 테스트 ==========

def test_run_sqlplus_not_found():
    """sqlplus가 없으면 에러"""
    config = {"host": "localhost", "port": "1521", "username": "user", "password": "pass", "sid": "SID", "service": ""}

    with mock.patch("shutil.which", return_value=None):
        with pytest.raises(SystemExit) as exc_info:
            _run_sqlplus("SELECT 1 FROM DUAL;", config)
        assert "sqlplus not found" in str(exc_info.value)


def test_run_sqlplus_success():
    """정상적인 sqlplus 실행"""
    config = {"host": "localhost", "port": "1521", "username": "user", "password": "pass", "sid": "SID", "service": ""}

    mock_proc = mock.Mock()
    mock_proc.returncode = 0
    mock_proc.stdout = "1\n"
    mock_proc.stderr = ""

    with mock.patch("shutil.which", return_value="/usr/bin/sqlplus"):
        with mock.patch("subprocess.run", return_value=mock_proc):
            result = _run_sqlplus("SELECT 1 FROM DUAL;", config)
            assert result == 0


# ========== 쿼리 정규화 테스트 ==========

def test_normalize_query_removes_semicolon():
    """세미콜론 제거"""
    result = _normalize_query("SELECT * FROM users;")
    assert result == "SELECT * FROM users"


def test_normalize_query_strips_whitespace():
    """공백 제거"""
    result = _normalize_query("  SELECT * FROM users  ")
    assert result == "SELECT * FROM users"


def test_normalize_query_case_insensitive():
    """대소문자 구분 없이 SELECT 허용"""
    result = _normalize_query("select * from users")
    assert result == "select * from users"


def test_normalize_query_rejects_non_select():
    """SELECT가 아닌 쿼리는 거부"""
    with pytest.raises(SystemExit) as exc_info:
        _normalize_query("DROP TABLE users")
    assert "Only SELECT queries" in str(exc_info.value)


def test_normalize_query_allows_select():
    """SELECT 쿼리는 허용"""
    result = _normalize_query("SELECT * FROM users")
    assert result.startswith("SELECT")


# ========== 명령어 테스트 (test) ==========

def test_cmd_test_jdbc_success():
    """JDBC 엔진으로 연결 테스트 성공"""
    env_vars = {
        "ORACLE_HOST": "localhost",
        "ORACLE_USERNAME": "testuser",
        "ORACLE_PASSWORD": "testpass",
    }

    args = mock.Mock()
    args.engine = "jdbc"

    with mock.patch.dict("os.environ", env_vars):
        with mock.patch("oracle_cli._run_java", return_value=0):
            with pytest.raises(SystemExit) as exc_info:
                cmd_test(args)
            assert exc_info.value.code == 0


def test_cmd_test_jdbc_failure():
    """JDBC 연결 실패"""
    env_vars = {
        "ORACLE_HOST": "localhost",
        "ORACLE_USERNAME": "testuser",
        "ORACLE_PASSWORD": "testpass",
    }

    args = mock.Mock()
    args.engine = "jdbc"

    with mock.patch.dict("os.environ", env_vars):
        with mock.patch("oracle_cli._run_java", return_value=2):
            with pytest.raises(SystemExit) as exc_info:
                cmd_test(args)
            assert exc_info.value.code == 2


def test_cmd_test_auto_fallback_to_sqlplus():
    """auto 모드에서 JDBC 실패 시 sqlplus로 폴백"""
    env_vars = {
        "ORACLE_HOST": "localhost",
        "ORACLE_USERNAME": "testuser",
        "ORACLE_PASSWORD": "testpass",
    }

    args = mock.Mock()
    args.engine = "auto"

    with mock.patch.dict("os.environ", env_vars):
        # JDBC 실패
        with mock.patch("oracle_cli._run_java", side_effect=SystemExit(2)):
            # sqlplus 성공
            with mock.patch("oracle_cli._run_sqlplus", return_value=0):
                with pytest.raises(SystemExit) as exc_info:
                    cmd_test(args)
                assert exc_info.value.code == 0


# ========== 명령어 테스트 (select) ==========

def test_cmd_select_with_query_arg():
    """--query 인자로 쿼리 실행"""
    env_vars = {
        "ORACLE_HOST": "localhost",
        "ORACLE_USERNAME": "testuser",
        "ORACLE_PASSWORD": "testpass",
    }

    args = mock.Mock()
    args.engine = "jdbc"
    args.query = "SELECT * FROM users"
    args.query_file = None

    with mock.patch.dict("os.environ", env_vars):
        with mock.patch("oracle_cli._run_java", return_value=0):
            with pytest.raises(SystemExit) as exc_info:
                cmd_select(args)
            assert exc_info.value.code == 0


def test_cmd_select_with_query_file(tmp_path):
    """--query-file로 쿼리 실행"""
    env_vars = {
        "ORACLE_HOST": "localhost",
        "ORACLE_USERNAME": "testuser",
        "ORACLE_PASSWORD": "testpass",
    }

    query_file = tmp_path / "query.sql"
    query_file.write_text("SELECT * FROM users", encoding="utf-8")

    args = mock.Mock()
    args.engine = "jdbc"
    args.query = None
    args.query_file = str(query_file)

    with mock.patch.dict("os.environ", env_vars):
        with mock.patch("oracle_cli._run_java", return_value=0):
            with pytest.raises(SystemExit) as exc_info:
                cmd_select(args)
            assert exc_info.value.code == 0


def test_cmd_select_from_stdin():
    """stdin으로 쿼리 입력"""
    env_vars = {
        "ORACLE_HOST": "localhost",
        "ORACLE_USERNAME": "testuser",
        "ORACLE_PASSWORD": "testpass",
    }

    args = mock.Mock()
    args.engine = "jdbc"
    args.query = None
    args.query_file = None

    with mock.patch.dict("os.environ", env_vars):
        with mock.patch("sys.stdin.isatty", return_value=False):
            with mock.patch("sys.stdin.read", return_value="SELECT * FROM users"):
                with mock.patch("oracle_cli._run_java", return_value=0):
                    with pytest.raises(SystemExit) as exc_info:
                        cmd_select(args)
                    assert exc_info.value.code == 0


def test_cmd_select_stdin_tty_error():
    """stdin이 tty인데 쿼리가 없으면 에러"""
    env_vars = {
        "ORACLE_HOST": "localhost",
        "ORACLE_USERNAME": "testuser",
        "ORACLE_PASSWORD": "testpass",
    }

    args = mock.Mock()
    args.engine = "jdbc"
    args.query = None
    args.query_file = None

    with mock.patch.dict("os.environ", env_vars):
        with mock.patch("sys.stdin.isatty", return_value=True):
            with pytest.raises(SystemExit) as exc_info:
                cmd_select(args)
            assert "Provide --query" in str(exc_info.value)


def test_cmd_select_rejects_non_select():
    """SELECT가 아닌 쿼리는 거부"""
    env_vars = {
        "ORACLE_HOST": "localhost",
        "ORACLE_USERNAME": "testuser",
        "ORACLE_PASSWORD": "testpass",
    }

    args = mock.Mock()
    args.engine = "jdbc"
    args.query = "DROP TABLE users"
    args.query_file = None

    with mock.patch.dict("os.environ", env_vars):
        with pytest.raises(SystemExit) as exc_info:
            cmd_select(args)
        assert "Only SELECT queries" in str(exc_info.value)


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
