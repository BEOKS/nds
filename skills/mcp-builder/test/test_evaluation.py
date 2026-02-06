#!/usr/bin/env python3
"""
evaluation.py 단위 테스트
pytest로 MCP 서버 평가 기능 검증
"""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock, mock_open

import pytest

# 테스트 대상 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from evaluation import (
    parse_evaluation_file,
    extract_xml_content,
    agent_loop,
    evaluate_single_task,
    parse_headers,
    parse_env_vars,
)


class TestParseEvaluationFile:
    """parse_evaluation_file 함수 테스트"""

    def test_valid_xml_file(self, tmp_path):
        """정상적인 XML 파일 파싱 테스트"""
        xml_content = """<?xml version="1.0"?>
<evaluations>
    <qa_pair>
        <question>What is 2+2?</question>
        <answer>4</answer>
    </qa_pair>
    <qa_pair>
        <question>What is the capital of France?</question>
        <answer>Paris</answer>
    </qa_pair>
</evaluations>"""
        xml_file = tmp_path / "eval.xml"
        xml_file.write_text(xml_content)

        result = parse_evaluation_file(xml_file)

        assert len(result) == 2
        assert result[0]["question"] == "What is 2+2?"
        assert result[0]["answer"] == "4"
        assert result[1]["question"] == "What is the capital of France?"
        assert result[1]["answer"] == "Paris"

    def test_empty_xml_file(self, tmp_path):
        """빈 XML 파일 테스트"""
        xml_content = """<?xml version="1.0"?>
<evaluations>
</evaluations>"""
        xml_file = tmp_path / "empty.xml"
        xml_file.write_text(xml_content)

        result = parse_evaluation_file(xml_file)

        assert result == []

    def test_xml_with_whitespace(self, tmp_path):
        """공백이 포함된 XML 테스트"""
        xml_content = """<?xml version="1.0"?>
<evaluations>
    <qa_pair>
        <question>  What is 2+2?  </question>
        <answer>  4  </answer>
    </qa_pair>
</evaluations>"""
        xml_file = tmp_path / "whitespace.xml"
        xml_file.write_text(xml_content)

        result = parse_evaluation_file(xml_file)

        # strip()되어야 함
        assert result[0]["question"] == "What is 2+2?"
        assert result[0]["answer"] == "4"

    def test_missing_question(self, tmp_path):
        """question이 없는 경우 테스트"""
        xml_content = """<?xml version="1.0"?>
<evaluations>
    <qa_pair>
        <answer>4</answer>
    </qa_pair>
</evaluations>"""
        xml_file = tmp_path / "missing_q.xml"
        xml_file.write_text(xml_content)

        result = parse_evaluation_file(xml_file)

        # question이나 answer가 없으면 포함되지 않음
        assert result == []

    def test_missing_answer(self, tmp_path):
        """answer가 없는 경우 테스트"""
        xml_content = """<?xml version="1.0"?>
<evaluations>
    <qa_pair>
        <question>What is 2+2?</question>
    </qa_pair>
</evaluations>"""
        xml_file = tmp_path / "missing_a.xml"
        xml_file.write_text(xml_content)

        result = parse_evaluation_file(xml_file)

        assert result == []

    def test_malformed_xml(self, tmp_path):
        """잘못된 XML 형식 테스트"""
        xml_content = """<?xml version="1.0"?>
<evaluations>
    <qa_pair>
        <question>Unclosed tag
    </qa_pair>
</evaluations>"""
        xml_file = tmp_path / "malformed.xml"
        xml_file.write_text(xml_content)

        result = parse_evaluation_file(xml_file)

        # 파싱 에러 발생 시 빈 리스트 반환
        assert result == []

    def test_file_not_found(self):
        """존재하지 않는 파일 테스트"""
        result = parse_evaluation_file(Path("/nonexistent/file.xml"))

        assert result == []


class TestExtractXmlContent:
    """extract_xml_content 함수 테스트"""

    def test_extract_single_tag(self):
        """단일 태그 추출 테스트"""
        text = "Some text <response>Hello World</response> more text"
        result = extract_xml_content(text, "response")

        assert result == "Hello World"

    def test_extract_with_newlines(self):
        """줄바꿈이 포함된 태그 추출 테스트"""
        text = """<summary>
        Step 1: Do something
        Step 2: Do something else
        </summary>"""
        result = extract_xml_content(text, "summary")

        assert "Step 1" in result
        assert "Step 2" in result

    def test_multiple_same_tags(self):
        """동일한 태그가 여러 개 있는 경우 테스트"""
        text = "<response>First</response> <response>Second</response>"
        result = extract_xml_content(text, "response")

        # 마지막 태그 내용 반환
        assert result == "Second"

    def test_tag_not_found(self):
        """태그가 없는 경우 테스트"""
        text = "No tags here"
        result = extract_xml_content(text, "response")

        assert result is None

    def test_nested_tags(self):
        """중첩된 태그 테스트"""
        text = "<outer><inner>content</inner></outer>"
        result = extract_xml_content(text, "inner")

        assert result == "content"

    def test_empty_tag(self):
        """빈 태그 테스트"""
        text = "<response></response>"
        result = extract_xml_content(text, "response")

        assert result == ""


class TestParseHeaders:
    """parse_headers 함수 테스트"""

    def test_valid_headers(self):
        """정상적인 헤더 파싱 테스트"""
        headers = ["Authorization: Bearer token", "Content-Type: application/json"]
        result = parse_headers(headers)

        assert result == {
            "Authorization": "Bearer token",
            "Content-Type": "application/json"
        }

    def test_empty_list(self):
        """빈 리스트 테스트"""
        result = parse_headers([])

        assert result == {}

    def test_none_input(self):
        """None 입력 테스트"""
        result = parse_headers(None)

        assert result == {}

    def test_malformed_header(self):
        """잘못된 형식의 헤더 테스트"""
        headers = ["Authorization: Bearer token", "MalformedHeader"]
        result = parse_headers(headers)

        # 정상적인 헤더만 파싱
        assert "Authorization" in result
        assert "MalformedHeader" not in result

    def test_header_with_multiple_colons(self):
        """콜론이 여러 개 있는 헤더 테스트"""
        headers = ["Authorization: Bearer: token:123"]
        result = parse_headers(headers)

        # 첫 번째 콜론으로 분할
        assert result["Authorization"] == "Bearer: token:123"

    def test_whitespace_trimming(self):
        """공백 제거 테스트"""
        headers = ["  Authorization  :  Bearer token  "]
        result = parse_headers(headers)

        assert result["Authorization"] == "Bearer token"


class TestParseEnvVars:
    """parse_env_vars 함수 테스트"""

    def test_valid_env_vars(self):
        """정상적인 환경변수 파싱 테스트"""
        env_vars = ["API_KEY=secret123", "DEBUG=true"]
        result = parse_env_vars(env_vars)

        assert result == {
            "API_KEY": "secret123",
            "DEBUG": "true"
        }

    def test_empty_list(self):
        """빈 리스트 테스트"""
        result = parse_env_vars([])

        assert result == {}

    def test_none_input(self):
        """None 입력 테스트"""
        result = parse_env_vars(None)

        assert result == {}

    def test_malformed_env_var(self):
        """잘못된 형식의 환경변수 테스트"""
        env_vars = ["API_KEY=secret", "MALFORMED"]
        result = parse_env_vars(env_vars)

        # 정상적인 환경변수만 파싱
        assert "API_KEY" in result
        assert "MALFORMED" not in result

    def test_env_var_with_equals_in_value(self):
        """값에 =가 포함된 환경변수 테스트"""
        env_vars = ["FORMULA=a=b+c"]
        result = parse_env_vars(env_vars)

        # 첫 번째 =로 분할
        assert result["FORMULA"] == "a=b+c"

    def test_whitespace_trimming(self):
        """공백 제거 테스트"""
        env_vars = ["  API_KEY  =  secret123  "]
        result = parse_env_vars(env_vars)

        assert result["API_KEY"] == "secret123"


@pytest.mark.asyncio
class TestAgentLoop:
    """agent_loop 함수 테스트"""

    async def test_single_tool_call(self):
        """단일 도구 호출 테스트"""
        mock_client = MagicMock()
        mock_connection = AsyncMock()

        # 첫 번째 응답: tool_use
        first_response = MagicMock()
        first_response.stop_reason = "tool_use"
        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "test_tool"
        tool_use_block.input = {"arg": "value"}
        tool_use_block.id = "tool_123"
        first_response.content = [tool_use_block]

        # 두 번째 응답: end_turn
        second_response = MagicMock()
        second_response.stop_reason = "end_turn"
        text_block = MagicMock()
        text_block.text = "<response>Result</response>"
        second_response.content = [text_block]

        mock_client.messages.create.side_effect = [first_response, second_response]
        mock_connection.call_tool.return_value = {"result": "success"}

        result, metrics = await agent_loop(
            mock_client,
            "claude-3-7-sonnet-20250219",
            "Test question",
            [],
            mock_connection
        )

        assert "<response>Result</response>" in result
        assert "test_tool" in metrics
        assert metrics["test_tool"]["count"] == 1

    async def test_no_tool_calls(self):
        """도구 호출 없이 바로 응답하는 경우 테스트"""
        mock_client = MagicMock()
        mock_connection = AsyncMock()

        response = MagicMock()
        response.stop_reason = "end_turn"
        text_block = MagicMock()
        text_block.text = "<response>Direct answer</response>"
        response.content = [text_block]

        mock_client.messages.create.return_value = response

        result, metrics = await agent_loop(
            mock_client,
            "claude-3-7-sonnet-20250219",
            "Simple question",
            [],
            mock_connection
        )

        assert "Direct answer" in result
        assert metrics == {}

    async def test_tool_call_error(self):
        """도구 호출 중 에러 발생 테스트"""
        mock_client = MagicMock()
        mock_connection = AsyncMock()

        # 첫 번째 응답: tool_use
        first_response = MagicMock()
        first_response.stop_reason = "tool_use"
        tool_use_block = MagicMock()
        tool_use_block.type = "tool_use"
        tool_use_block.name = "error_tool"
        tool_use_block.input = {}
        tool_use_block.id = "tool_456"
        first_response.content = [tool_use_block]

        # 두 번째 응답: end_turn
        second_response = MagicMock()
        second_response.stop_reason = "end_turn"
        text_block = MagicMock()
        text_block.text = "<response>Handled error</response>"
        second_response.content = [text_block]

        mock_client.messages.create.side_effect = [first_response, second_response]
        mock_connection.call_tool.side_effect = Exception("Tool error")

        result, metrics = await agent_loop(
            mock_client,
            "claude-3-7-sonnet-20250219",
            "Test question",
            [],
            mock_connection
        )

        # 에러가 발생해도 계속 진행
        assert result is not None
        assert "error_tool" in metrics


@pytest.mark.asyncio
class TestEvaluateSingleTask:
    """evaluate_single_task 함수 테스트"""

    async def test_correct_answer(self):
        """정답인 경우 테스트"""
        mock_client = MagicMock()
        mock_connection = AsyncMock()

        response = MagicMock()
        response.stop_reason = "end_turn"
        text_block = MagicMock()
        text_block.text = """<summary>Used tool X</summary>
<feedback>Tool was great</feedback>
<response>42</response>"""
        response.content = [text_block]

        mock_client.messages.create.return_value = response

        qa_pair = {"question": "What is 6*7?", "answer": "42"}
        result = await evaluate_single_task(
            mock_client,
            "claude-3-7-sonnet-20250219",
            qa_pair,
            [],
            mock_connection,
            0
        )

        assert result["score"] == 1
        assert result["actual"] == "42"
        assert result["expected"] == "42"
        assert "Used tool X" in result["summary"]
        assert "Tool was great" in result["feedback"]

    async def test_incorrect_answer(self):
        """오답인 경우 테스트"""
        mock_client = MagicMock()
        mock_connection = AsyncMock()

        response = MagicMock()
        response.stop_reason = "end_turn"
        text_block = MagicMock()
        text_block.text = "<response>43</response>"
        response.content = [text_block]

        mock_client.messages.create.return_value = response

        qa_pair = {"question": "What is 6*7?", "answer": "42"}
        result = await evaluate_single_task(
            mock_client,
            "claude-3-7-sonnet-20250219",
            qa_pair,
            [],
            mock_connection,
            0
        )

        assert result["score"] == 0
        assert result["actual"] == "43"
        assert result["expected"] == "42"

    async def test_not_found_response(self):
        """응답을 찾지 못한 경우 테스트"""
        mock_client = MagicMock()
        mock_connection = AsyncMock()

        response = MagicMock()
        response.stop_reason = "end_turn"
        text_block = MagicMock()
        text_block.text = "<response>NOT_FOUND</response>"
        response.content = [text_block]

        mock_client.messages.create.return_value = response

        qa_pair = {"question": "Unknown question", "answer": "42"}
        result = await evaluate_single_task(
            mock_client,
            "claude-3-7-sonnet-20250219",
            qa_pair,
            [],
            mock_connection,
            0
        )

        assert result["score"] == 0
        assert result["actual"] == "NOT_FOUND"


class TestEdgeCases:
    """경계 케이스 테스트"""

    def test_parse_evaluation_with_nested_elements(self, tmp_path):
        """중첩된 요소가 있는 XML 테스트"""
        xml_content = """<?xml version="1.0"?>
<evaluations>
    <qa_pair>
        <question>What is <code>2+2</code>?</question>
        <answer>4</answer>
    </qa_pair>
</evaluations>"""
        xml_file = tmp_path / "nested.xml"
        xml_file.write_text(xml_content)

        result = parse_evaluation_file(xml_file)

        # 중첩된 태그는 텍스트로 처리되지 않음
        assert len(result) == 1

    def test_extract_xml_with_cdata(self):
        """CDATA가 포함된 XML 추출 테스트"""
        text = "<response><![CDATA[Special <chars>]]></response>"
        result = extract_xml_content(text, "response")

        # CDATA는 정규식으로 추출되지 않을 수 있음
        assert result is not None

    def test_parse_headers_empty_value(self):
        """빈 값이 있는 헤더 테스트"""
        headers = ["Authorization: "]
        result = parse_headers(headers)

        assert result["Authorization"] == ""

    def test_parse_env_vars_empty_value(self):
        """빈 값이 있는 환경변수 테스트"""
        env_vars = ["EMPTY="]
        result = parse_env_vars(env_vars)

        assert result["EMPTY"] == ""
