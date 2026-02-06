#!/usr/bin/env python3
"""
memory_cli.py 단위 테스트

mock을 사용하여 파일 I/O를 격리하고 각 함수의 정상/에러 케이스를 테스트
"""
import json
import sys
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest

# 테스트 대상 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from memory_cli import (
    Entity,
    Relation,
    _env,
    _resolve_memory_path,
    _read_input_json,
    _load_graph,
    _save_graph,
    _graph_to_json,
    cmd_create_entities,
    cmd_create_relations,
    cmd_add_observations,
    cmd_delete_entities,
    cmd_delete_observations,
    cmd_delete_relations,
    cmd_read_graph,
    cmd_search_nodes,
    cmd_open_nodes,
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


def test_env_returns_none_for_empty_string():
    """빈 문자열 환경변수는 None 반환"""
    with mock.patch.dict("os.environ", {"EMPTY": "   "}):
        assert _env("EMPTY") is None


def test_resolve_memory_path_with_override():
    """--memory-file 인자로 명시적 경로 지정"""
    result = _resolve_memory_path("/absolute/path/memory.json")
    assert result == Path("/absolute/path/memory.json")


def test_resolve_memory_path_from_env():
    """MEMORY_FILE_PATH 환경변수에서 경로 가져오기"""
    with mock.patch.dict("os.environ", {"MEMORY_FILE_PATH": "/env/memory.json"}):
        result = _resolve_memory_path(None)
        assert result == Path("/env/memory.json")


def test_resolve_memory_path_default():
    """기본값: 현재 디렉토리의 memory.json"""
    with mock.patch.dict("os.environ", {}, clear=True):
        result = _resolve_memory_path(None)
        assert result == Path.cwd() / "memory.json"


def test_read_input_json_from_file(tmp_path):
    """--input 파일에서 JSON 읽기"""
    test_file = tmp_path / "input.json"
    test_file.write_text('{"key": "value"}', encoding="utf-8")

    result = _read_input_json(str(test_file))
    assert result == {"key": "value"}


def test_read_input_json_from_stdin():
    """stdin으로 JSON 입력 받기"""
    fake_stdin = StringIO('{"key": "value"}')
    with mock.patch("sys.stdin", fake_stdin):
        with mock.patch("sys.stdin.isatty", return_value=False):
            result = _read_input_json(None)
            assert result == {"key": "value"}


def test_read_input_json_error_on_tty():
    """stdin이 tty인 경우 에러 발생"""
    with mock.patch("sys.stdin.isatty", return_value=True):
        with pytest.raises(SystemExit) as exc_info:
            _read_input_json(None)
        assert "Provide --input" in str(exc_info.value)


def test_read_input_json_error_on_non_object():
    """JSON이 객체가 아니면 에러 발생"""
    fake_stdin = StringIO('["not", "an", "object"]')
    with mock.patch("sys.stdin", fake_stdin):
        with mock.patch("sys.stdin.isatty", return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                _read_input_json(None)
            assert "must be an object" in str(exc_info.value)


# ========== 데이터 클래스 테스트 ==========

def test_entity_creation():
    """Entity 데이터클래스 생성"""
    e = Entity(name="Alice", entityType="Person", observations=["smart", "friendly"])
    assert e.name == "Alice"
    assert e.entityType == "Person"
    assert len(e.observations) == 2


def test_relation_creation():
    """Relation 데이터클래스 생성"""
    r = Relation(from_="Alice", to="Bob", relationType="knows")
    assert r.from_ == "Alice"
    assert r.to == "Bob"
    assert r.relationType == "knows"


# ========== 그래프 로드/저장 테스트 ==========

def test_load_graph_from_empty_file():
    """존재하지 않는 파일은 빈 그래프 반환"""
    with mock.patch.object(Path, "exists", return_value=False):
        entities, relations = _load_graph(Path("/nonexistent.json"))
        assert entities == []
        assert relations == []


def test_load_graph_with_entities_and_relations(tmp_path):
    """파일에서 entities와 relations 로드"""
    memory_file = tmp_path / "memory.json"
    content = '\n'.join([
        json.dumps({"type": "entity", "name": "Alice", "entityType": "Person", "observations": ["smart"]}),
        json.dumps({"type": "relation", "from": "Alice", "to": "Bob", "relationType": "knows"}),
    ])
    memory_file.write_text(content, encoding="utf-8")

    entities, relations = _load_graph(memory_file)
    assert len(entities) == 1
    assert entities[0].name == "Alice"
    assert len(relations) == 1
    assert relations[0].from_ == "Alice"


def test_load_graph_ignores_malformed_lines(tmp_path):
    """잘못된 JSON 라인은 무시"""
    memory_file = tmp_path / "memory.json"
    content = '\n'.join([
        json.dumps({"type": "entity", "name": "Alice", "entityType": "Person", "observations": []}),
        "NOT JSON",
        json.dumps({"type": "invalid"}),
    ])
    memory_file.write_text(content, encoding="utf-8")

    entities, relations = _load_graph(memory_file)
    assert len(entities) == 1


def test_save_graph(tmp_path):
    """entities와 relations를 파일에 저장"""
    memory_file = tmp_path / "memory.json"
    entities = [Entity(name="Alice", entityType="Person", observations=["smart"])]
    relations = [Relation(from_="Alice", to="Bob", relationType="knows")]

    _save_graph(memory_file, entities, relations)

    lines = memory_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert "entity" in lines[0]
    assert "relation" in lines[1]


def test_graph_to_json():
    """그래프를 JSON 딕셔너리로 변환"""
    entities = [Entity(name="Alice", entityType="Person", observations=["smart"])]
    relations = [Relation(from_="Alice", to="Bob", relationType="knows")]

    result = _graph_to_json(entities, relations)

    assert "entities" in result
    assert "relations" in result
    assert len(result["entities"]) == 1
    assert result["entities"][0]["name"] == "Alice"


# ========== 명령어 테스트 (create-entities) ==========

def test_cmd_create_entities_success(tmp_path, capsys):
    """새로운 entities 생성"""
    memory_file = tmp_path / "memory.json"
    input_data = {"entities": [{"name": "Alice", "entityType": "Person", "observations": ["smart"]}]}

    args = mock.Mock()
    args.memory_file = str(memory_file)
    args.input = None

    with mock.patch("memory_cli._read_input_json", return_value=input_data):
        cmd_create_entities(args)

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert len(result) == 1
    assert result[0]["name"] == "Alice"


def test_cmd_create_entities_skip_duplicate(tmp_path, capsys):
    """중복된 entity는 생성하지 않음"""
    memory_file = tmp_path / "memory.json"
    # 기존 데이터
    existing = [Entity(name="Alice", entityType="Person", observations=[])]
    _save_graph(memory_file, existing, [])

    input_data = {"entities": [{"name": "Alice", "entityType": "Person", "observations": []}]}

    args = mock.Mock()
    args.memory_file = str(memory_file)
    args.input = None

    with mock.patch("memory_cli._read_input_json", return_value=input_data):
        cmd_create_entities(args)

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert len(result) == 0  # 중복이므로 생성되지 않음


def test_cmd_create_entities_invalid_input():
    """entities 필드가 배열이 아니면 에러"""
    args = mock.Mock()
    args.memory_file = "/tmp/memory.json"
    args.input = None

    with mock.patch("memory_cli._read_input_json", return_value={"entities": "not_an_array"}):
        with pytest.raises(SystemExit) as exc_info:
            cmd_create_entities(args)
        assert "must be an array" in str(exc_info.value)


# ========== 명령어 테스트 (create-relations) ==========

def test_cmd_create_relations_success(tmp_path, capsys):
    """새로운 relations 생성"""
    memory_file = tmp_path / "memory.json"
    input_data = {"relations": [{"from": "Alice", "to": "Bob", "relationType": "knows"}]}

    args = mock.Mock()
    args.memory_file = str(memory_file)
    args.input = None

    with mock.patch("memory_cli._read_input_json", return_value=input_data):
        cmd_create_relations(args)

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert len(result) == 1
    assert result[0]["from"] == "Alice"


def test_cmd_create_relations_skip_duplicate(tmp_path, capsys):
    """중복된 relation은 생성하지 않음"""
    memory_file = tmp_path / "memory.json"
    existing_rel = [Relation(from_="Alice", to="Bob", relationType="knows")]
    _save_graph(memory_file, [], existing_rel)

    input_data = {"relations": [{"from": "Alice", "to": "Bob", "relationType": "knows"}]}

    args = mock.Mock()
    args.memory_file = str(memory_file)
    args.input = None

    with mock.patch("memory_cli._read_input_json", return_value=input_data):
        cmd_create_relations(args)

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert len(result) == 0


# ========== 명령어 테스트 (add-observations) ==========

def test_cmd_add_observations_success(tmp_path, capsys):
    """entity에 새로운 observations 추가"""
    memory_file = tmp_path / "memory.json"
    existing = [Entity(name="Alice", entityType="Person", observations=["smart"])]
    _save_graph(memory_file, existing, [])

    input_data = {"observations": [{"entityName": "Alice", "contents": ["friendly", "creative"]}]}

    args = mock.Mock()
    args.memory_file = str(memory_file)
    args.input = None

    with mock.patch("memory_cli._read_input_json", return_value=input_data):
        cmd_add_observations(args)

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert len(result[0]["contents"]) == 2


def test_cmd_add_observations_entity_not_found(tmp_path):
    """존재하지 않는 entity에 observation 추가 시도 시 에러"""
    memory_file = tmp_path / "memory.json"
    _save_graph(memory_file, [], [])

    input_data = {"observations": [{"entityName": "NonExistent", "contents": ["test"]}]}

    args = mock.Mock()
    args.memory_file = str(memory_file)
    args.input = None

    with mock.patch("memory_cli._read_input_json", return_value=input_data):
        with pytest.raises(SystemExit) as exc_info:
            cmd_add_observations(args)
        assert "not found" in str(exc_info.value)


# ========== 명령어 테스트 (delete-entities) ==========

def test_cmd_delete_entities_success(tmp_path, capsys):
    """entities와 관련 relations 삭제"""
    memory_file = tmp_path / "memory.json"
    entities = [
        Entity(name="Alice", entityType="Person", observations=[]),
        Entity(name="Bob", entityType="Person", observations=[]),
    ]
    relations = [Relation(from_="Alice", to="Bob", relationType="knows")]
    _save_graph(memory_file, entities, relations)

    input_data = {"entityNames": ["Alice"]}

    args = mock.Mock()
    args.memory_file = str(memory_file)
    args.input = None

    with mock.patch("memory_cli._read_input_json", return_value=input_data):
        cmd_delete_entities(args)

    # 삭제 후 확인
    entities, relations = _load_graph(memory_file)
    assert len(entities) == 1
    assert entities[0].name == "Bob"
    assert len(relations) == 0  # Alice 관련 relation 삭제됨


def test_cmd_delete_entities_invalid_input():
    """entityNames가 문자열 배열이 아니면 에러"""
    args = mock.Mock()
    args.memory_file = "/tmp/memory.json"
    args.input = None

    with mock.patch("memory_cli._read_input_json", return_value={"entityNames": "not_an_array"}):
        with pytest.raises(SystemExit):
            cmd_delete_entities(args)


# ========== 명령어 테스트 (delete-observations) ==========

def test_cmd_delete_observations_success(tmp_path, capsys):
    """entity의 특정 observations 삭제"""
    memory_file = tmp_path / "memory.json"
    entities = [Entity(name="Alice", entityType="Person", observations=["smart", "friendly", "creative"])]
    _save_graph(memory_file, entities, [])

    input_data = {"deletions": [{"entityName": "Alice", "observations": ["friendly"]}]}

    args = mock.Mock()
    args.memory_file = str(memory_file)
    args.input = None

    with mock.patch("memory_cli._read_input_json", return_value=input_data):
        cmd_delete_observations(args)

    entities, _ = _load_graph(memory_file)
    assert "friendly" not in entities[0].observations
    assert "smart" in entities[0].observations


# ========== 명령어 테스트 (delete-relations) ==========

def test_cmd_delete_relations_success(tmp_path, capsys):
    """특정 relations 삭제"""
    memory_file = tmp_path / "memory.json"
    relations = [
        Relation(from_="Alice", to="Bob", relationType="knows"),
        Relation(from_="Bob", to="Charlie", relationType="likes"),
    ]
    _save_graph(memory_file, [], relations)

    input_data = {"relations": [{"from": "Alice", "to": "Bob", "relationType": "knows"}]}

    args = mock.Mock()
    args.memory_file = str(memory_file)
    args.input = None

    with mock.patch("memory_cli._read_input_json", return_value=input_data):
        cmd_delete_relations(args)

    _, relations = _load_graph(memory_file)
    assert len(relations) == 1
    assert relations[0].from_ == "Bob"


# ========== 명령어 테스트 (read-graph) ==========

def test_cmd_read_graph(tmp_path, capsys):
    """전체 그래프 읽기"""
    memory_file = tmp_path / "memory.json"
    entities = [Entity(name="Alice", entityType="Person", observations=[])]
    relations = [Relation(from_="Alice", to="Bob", relationType="knows")]
    _save_graph(memory_file, entities, relations)

    args = mock.Mock()
    args.memory_file = str(memory_file)

    cmd_read_graph(args)

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert len(result["entities"]) == 1
    assert len(result["relations"]) == 1


# ========== 명령어 테스트 (search-nodes) ==========

def test_cmd_search_nodes_by_name(tmp_path, capsys):
    """이름으로 nodes 검색"""
    memory_file = tmp_path / "memory.json"
    entities = [
        Entity(name="Alice", entityType="Person", observations=[]),
        Entity(name="Bob", entityType="Person", observations=[]),
    ]
    _save_graph(memory_file, entities, [])

    args = mock.Mock()
    args.memory_file = str(memory_file)
    args.query = "alice"

    cmd_search_nodes(args)

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert len(result["entities"]) == 1
    assert result["entities"][0]["name"] == "Alice"


def test_cmd_search_nodes_by_observation(tmp_path, capsys):
    """observation으로 nodes 검색"""
    memory_file = tmp_path / "memory.json"
    entities = [
        Entity(name="Alice", entityType="Person", observations=["python expert"]),
        Entity(name="Bob", entityType="Person", observations=["java expert"]),
    ]
    _save_graph(memory_file, entities, [])

    args = mock.Mock()
    args.memory_file = str(memory_file)
    args.query = "python"

    cmd_search_nodes(args)

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert len(result["entities"]) == 1
    assert result["entities"][0]["name"] == "Alice"


# ========== 명령어 테스트 (open-nodes) ==========

def test_cmd_open_nodes(tmp_path, capsys):
    """특정 이름의 nodes만 가져오기"""
    memory_file = tmp_path / "memory.json"
    entities = [
        Entity(name="Alice", entityType="Person", observations=[]),
        Entity(name="Bob", entityType="Person", observations=[]),
        Entity(name="Charlie", entityType="Person", observations=[]),
    ]
    relations = [
        Relation(from_="Alice", to="Bob", relationType="knows"),
        Relation(from_="Bob", to="Charlie", relationType="knows"),
    ]
    _save_graph(memory_file, entities, relations)

    args = mock.Mock()
    args.memory_file = str(memory_file)
    args.names = ["Alice", "Bob"]

    cmd_open_nodes(args)

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert len(result["entities"]) == 2
    assert len(result["relations"]) == 1  # Alice-Bob relation만 포함


# ========== 파서 테스트 ==========

def test_build_parser():
    """argparse 파서 생성 확인"""
    parser = build_parser()
    assert parser is not None

    # create-entities 서브커맨드 테스트
    args = parser.parse_args(["create-entities"])
    assert args.cmd == "create-entities"
