#!/usr/bin/env python3
"""mattermost_cli.py 단위 테스트"""
import json
import os
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

# 테스트 대상 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import mattermost_cli


class TestEnvFunctions(unittest.TestCase):
    """환경변수 관련 함수 테스트"""

    @patch.dict(os.environ, {"TEST_VAR": "value"})
    def test_env_returns_value(self):
        """정상 케이스: 환경변수가 존재하는 경우"""
        result = mattermost_cli._env("TEST_VAR")
        self.assertEqual(result, "value")

    @patch.dict(os.environ, {}, clear=True)
    def test_env_returns_none_when_missing(self):
        """정상 케이스: 환경변수가 없는 경우"""
        result = mattermost_cli._env("MISSING_VAR")
        self.assertIsNone(result)

    @patch.dict(os.environ, {"EMPTY_VAR": "  "})
    def test_env_strips_whitespace(self):
        """정상 케이스: 공백만 있는 경우 None 반환"""
        result = mattermost_cli._env("EMPTY_VAR")
        self.assertIsNone(result)

    @patch.dict(os.environ, {"REQUIRED_VAR": "value"})
    def test_require_env_returns_value(self):
        """정상 케이스: 필수 환경변수가 존재하는 경우"""
        result = mattermost_cli._require_env("REQUIRED_VAR")
        self.assertEqual(result, "value")

    @patch.dict(os.environ, {}, clear=True)
    def test_require_env_raises_on_missing(self):
        """에러 케이스: 필수 환경변수가 없는 경우 SystemExit 발생"""
        with self.assertRaises(SystemExit) as cm:
            mattermost_cli._require_env("MISSING_VAR")
        self.assertIn("Missing required env", str(cm.exception))


class TestApiBase(unittest.TestCase):
    """API 베이스 URL 함수 테스트"""

    @patch.dict(os.environ, {"MATTERMOST_API_URL": "https://custom.mattermost.com/api/v4"})
    def test_custom_api_url(self):
        """정상 케이스: 커스텀 API URL 사용"""
        result = mattermost_cli._api_base()
        self.assertEqual(result, "https://custom.mattermost.com/api/v4")

    @patch.dict(os.environ, {}, clear=True)
    def test_default_api_url(self):
        """정상 케이스: 기본 API URL 사용"""
        result = mattermost_cli._api_base()
        self.assertEqual(result, "https://mattermost.gabia.com/api/v4")

    @patch.dict(os.environ, {"MATTERMOST_API_URL": "https://example.com/api/v4/"})
    def test_strips_trailing_slash(self):
        """정상 케이스: 끝 슬래시 제거"""
        result = mattermost_cli._api_base()
        self.assertEqual(result, "https://example.com/api/v4")


class TestBoardsApiBase(unittest.TestCase):
    """Boards API 베이스 URL 함수 테스트"""

    @patch.dict(os.environ, {"MATTERMOST_BOARDS_API_URL": "https://custom.boards.com/api/v2"})
    def test_custom_boards_url(self):
        """정상 케이스: 커스텀 Boards API URL 사용"""
        result = mattermost_cli._boards_api_base()
        self.assertEqual(result, "https://custom.boards.com/api/v2")

    @patch.dict(os.environ, {}, clear=True)
    def test_default_boards_url(self):
        """정상 케이스: 기본 Boards API URL 사용"""
        result = mattermost_cli._boards_api_base()
        self.assertEqual(result, "https://mattermost.gabia.com/plugins/focalboard/api/v2")


class TestAuthHeaders(unittest.TestCase):
    """인증 헤더 생성 함수 테스트"""

    @patch.dict(os.environ, {"MATTERMOST_TOKEN": "test_token"})
    def test_basic_auth_headers(self):
        """정상 케이스: 기본 인증 헤더 생성"""
        headers = mattermost_cli._auth_headers()
        self.assertEqual(headers["Accept"], "application/json")
        self.assertEqual(headers["Authorization"], "Bearer test_token")

    @patch.dict(os.environ, {"MATTERMOST_TOKEN": "test_token"})
    def test_json_body_headers(self):
        """정상 케이스: JSON body용 헤더 생성"""
        headers = mattermost_cli._auth_headers(json_body=True)
        self.assertEqual(headers["Content-Type"], "application/json")

    @patch.dict(os.environ, {"MATTERMOST_TOKEN": "test_token"})
    def test_extra_headers(self):
        """정상 케이스: 추가 헤더 포함"""
        headers = mattermost_cli._auth_headers(extra={"X-Custom": "value"})
        self.assertEqual(headers["X-Custom"], "value")

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_token_raises_error(self):
        """에러 케이스: 토큰이 없는 경우 SystemExit 발생"""
        with self.assertRaises(SystemExit) as cm:
            mattermost_cli._auth_headers()
        self.assertIn("Missing required env: MATTERMOST_TOKEN", str(cm.exception))


class TestHttpJson(unittest.TestCase):
    """HTTP JSON 요청 함수 테스트"""

    @patch("urllib.request.urlopen")
    def test_get_request(self, mock_urlopen):
        """정상 케이스: GET 요청"""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"result": "success"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = mattermost_cli._http_json(
            "GET",
            "https://api.example.com/test",
            headers={"Authorization": "Bearer token"}
        )

        self.assertEqual(result, {"result": "success"})

    @patch("urllib.request.urlopen")
    def test_post_request_with_body(self, mock_urlopen):
        """정상 케이스: POST 요청 with body"""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"created": true}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = mattermost_cli._http_json(
            "POST",
            "https://api.example.com/create",
            body={"data": "test"},
            headers={"Authorization": "Bearer token"}
        )

        self.assertEqual(result, {"created": True})

    @patch("urllib.request.urlopen")
    def test_request_with_params(self, mock_urlopen):
        """정상 케이스: 쿼리 파라미터 포함 요청"""
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"data": []}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        mattermost_cli._http_json(
            "GET",
            "https://api.example.com/search",
            params={"q": "test", "limit": "10"},
            headers={"Authorization": "Bearer token"}
        )

        # URL에 파라미터가 추가되었는지 확인
        call_args = mock_urlopen.call_args[0][0]
        self.assertIn("q=test", call_args.full_url)
        self.assertIn("limit=10", call_args.full_url)

    @patch("urllib.request.urlopen")
    def test_http_error_handling(self, mock_urlopen):
        """에러 케이스: HTTP 에러 처리"""
        from urllib.error import HTTPError
        from io import BytesIO

        mock_error = HTTPError(
            "https://api.example.com/test",
            404,
            "Not Found",
            {},
            BytesIO(b'{"error": "Not found"}')
        )
        mock_urlopen.side_effect = mock_error

        with self.assertRaises(SystemExit) as cm:
            mattermost_cli._http_json("GET", "https://api.example.com/test")

        self.assertIn("404", str(cm.exception))


class TestParseBoardCardUrl(unittest.TestCase):
    """보드 카드 URL 파싱 함수 테스트"""

    def test_parse_team_board_card_url(self):
        """정상 케이스: team/boardId/cardId 형식 파싱"""
        url = "https://mattermost.com/team/team123/board123/view456/card789"
        result = mattermost_cli._parse_board_card_url(url)

        self.assertIsNotNone(result)
        self.assertEqual(result["teamId"], "team123")
        self.assertEqual(result["boardId"], "board123")
        self.assertEqual(result["viewId"], "view456")
        self.assertEqual(result["cardId"], "card789")

    def test_parse_team_shared_board_url(self):
        """정상 케이스: team/shared/boardId/cardId 형식 파싱"""
        url = "https://mattermost.com/team/team123/shared/board456/view789/card012"
        result = mattermost_cli._parse_board_card_url(url)

        self.assertIsNotNone(result)
        self.assertEqual(result["teamId"], "team123")
        self.assertEqual(result["boardId"], "board456")
        self.assertEqual(result["cardId"], "card012")

    def test_parse_board_direct_url(self):
        """정상 케이스: board/boardId/cardId 형식 파싱"""
        url = "https://mattermost.com/board/board123/view456/card789"
        result = mattermost_cli._parse_board_card_url(url)

        self.assertIsNotNone(result)
        self.assertIsNone(result["teamId"])
        self.assertEqual(result["boardId"], "board123")
        self.assertEqual(result["cardId"], "card789")

    def test_parse_shared_board_url(self):
        """정상 케이스: shared/boardId/cardId 형식 파싱"""
        url = "https://mattermost.com/shared/board123/view456/card789"
        result = mattermost_cli._parse_board_card_url(url)

        self.assertIsNotNone(result)
        self.assertIsNone(result["teamId"])
        self.assertEqual(result["boardId"], "board123")
        self.assertEqual(result["cardId"], "card789")

    def test_parse_workspace_board_url(self):
        """정상 케이스: workspace/workspaceId/boardId/cardId 형식 파싱"""
        url = "https://mattermost.com/workspace/ws123/board456/view789/card012"
        result = mattermost_cli._parse_board_card_url(url)

        self.assertIsNotNone(result)
        self.assertEqual(result["boardId"], "board456")
        self.assertEqual(result["cardId"], "card012")

    def test_parse_workspace_shared_url(self):
        """정상 케이스: workspace/workspaceId/shared/boardId/cardId 형식 파싱"""
        url = "https://mattermost.com/workspace/ws123/shared/board456/view789/card012"
        result = mattermost_cli._parse_board_card_url(url)

        self.assertIsNotNone(result)
        self.assertEqual(result["boardId"], "board456")
        self.assertEqual(result["cardId"], "card012")

    def test_parse_invalid_url(self):
        """에러 케이스: 잘못된 URL 형식"""
        invalid_urls = [
            "https://mattermost.com/invalid",
            "https://mattermost.com/team/team123",  # cardId 누락
            "not-a-url",
            "",
        ]
        for url in invalid_urls:
            result = mattermost_cli._parse_board_card_url(url)
            self.assertIsNone(result, f"Should return None for invalid URL: {url}")

    def test_parse_url_with_extra_path(self):
        """정상 케이스: 추가 경로가 있는 URL"""
        url = "https://mattermost.com/prefix/team/team123/board456/view789/card012"
        result = mattermost_cli._parse_board_card_url(url)

        self.assertIsNotNone(result)
        self.assertEqual(result["teamId"], "team123")
        self.assertEqual(result["cardId"], "card012")


class TestCollectContentOrderIds(unittest.TestCase):
    """콘텐츠 순서 ID 수집 함수 테스트"""

    def test_collect_string_id(self):
        """정상 케이스: 문자열 ID 수집"""
        collector = []
        mattermost_cli._collect_content_order_ids("block123", collector)
        self.assertEqual(collector, ["block123"])

    def test_collect_nested_list(self):
        """정상 케이스: 중첩된 리스트에서 ID 수집"""
        collector = []
        mattermost_cli._collect_content_order_ids(
            ["block1", ["block2", "block3"], "block4"],
            collector
        )
        self.assertEqual(collector, ["block1", "block2", "block3", "block4"])

    def test_collect_deeply_nested(self):
        """정상 케이스: 깊게 중첩된 구조"""
        collector = []
        mattermost_cli._collect_content_order_ids(
            ["a", ["b", ["c", ["d"]]]],
            collector
        )
        self.assertEqual(collector, ["a", "b", "c", "d"])

    def test_collect_empty_list(self):
        """정상 케이스: 빈 리스트"""
        collector = []
        mattermost_cli._collect_content_order_ids([], collector)
        self.assertEqual(collector, [])


class TestExtractContentOrder(unittest.TestCase):
    """콘텐츠 순서 추출 함수 테스트"""

    def test_extract_from_valid_card(self):
        """정상 케이스: 올바른 카드에서 순서 추출"""
        card = {
            "fields": {
                "contentOrder": ["block1", "block2", ["block3", "block4"]]
            }
        }
        result = mattermost_cli._extract_content_order(card)
        self.assertEqual(result, ["block1", "block2", "block3", "block4"])

    def test_extract_from_card_without_content_order(self):
        """정상 케이스: contentOrder가 없는 카드"""
        card = {"fields": {}}
        result = mattermost_cli._extract_content_order(card)
        self.assertEqual(result, [])

    def test_extract_from_none(self):
        """정상 케이스: None 입력"""
        result = mattermost_cli._extract_content_order(None)
        self.assertEqual(result, [])

    def test_extract_from_card_without_fields(self):
        """정상 케이스: fields가 없는 카드"""
        card = {}
        result = mattermost_cli._extract_content_order(card)
        self.assertEqual(result, [])


class TestBuildCardPropertyValues(unittest.TestCase):
    """카드 속성값 구축 함수 테스트"""

    def test_build_property_values(self):
        """정상 케이스: 카드 속성값 구축"""
        board = {
            "cardProperties": [
                {"id": "prop1", "name": "Status", "type": "select"},
                {"id": "prop2", "name": "Priority", "type": "select"}
            ]
        }
        card = {
            "fields": {
                "properties": {
                    "prop1": "Done",
                    "prop2": "High"
                }
            }
        }

        result = mattermost_cli._build_card_property_values(board, card)

        self.assertEqual(len(result), 2)
        prop1 = next(p for p in result if p["propertyId"] == "prop1")
        self.assertEqual(prop1["propertyName"], "Status")
        self.assertEqual(prop1["type"], "select")
        self.assertEqual(prop1["value"], "Done")

    def test_build_with_no_properties(self):
        """정상 케이스: 속성이 없는 경우"""
        board = {"cardProperties": []}
        card = {"fields": {"properties": {}}}

        result = mattermost_cli._build_card_property_values(board, card)
        self.assertEqual(result, [])

    def test_build_with_unknown_property(self):
        """정상 케이스: 알려지지 않은 속성"""
        board = {"cardProperties": [{"id": "prop1", "name": "Status"}]}
        card = {
            "fields": {
                "properties": {
                    "prop1": "Done",
                    "prop2": "Unknown"  # 보드 정의에 없음
                }
            }
        }

        result = mattermost_cli._build_card_property_values(board, card)
        self.assertEqual(len(result), 2)
        # 알려지지 않은 속성도 포함되지만 템플릿 정보는 없음
        prop2 = next(p for p in result if p["propertyId"] == "prop2")
        self.assertIsNone(prop2["propertyName"])

    def test_build_with_none_board(self):
        """정상 케이스: board가 None인 경우"""
        result = mattermost_cli._build_card_property_values(None, {"fields": {}})
        self.assertEqual(result, [])

    def test_build_with_none_card(self):
        """정상 케이스: card가 None인 경우"""
        result = mattermost_cli._build_card_property_values({"cardProperties": []}, None)
        self.assertEqual(result, [])


class TestFetchCardContents(unittest.TestCase):
    """카드 콘텐츠 조회 함수 테스트"""

    @patch("mattermost_cli._fetch_blocks_by_parent_id")
    def test_fetch_with_content_order(self, mock_fetch):
        """정상 케이스: contentOrder에 따라 정렬"""
        mock_fetch.return_value = [
            {"id": "block2", "createAt": 200},
            {"id": "block1", "createAt": 100},
            {"id": "block3", "createAt": 300}
        ]

        result = mattermost_cli._fetch_card_contents("board123", "card456", ["block3", "block1", "block2"])

        # contentOrder 순서대로 정렬
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["id"], "block3")
        self.assertEqual(result[1]["id"], "block1")
        self.assertEqual(result[2]["id"], "block2")

    @patch("mattermost_cli._fetch_blocks_by_parent_id")
    def test_fetch_without_content_order(self, mock_fetch):
        """정상 케이스: contentOrder 없이 createAt으로 정렬"""
        mock_fetch.return_value = [
            {"id": "block2", "createAt": 200},
            {"id": "block1", "createAt": 100},
            {"id": "block3", "createAt": 300}
        ]

        result = mattermost_cli._fetch_card_contents("board123", "card456", [])

        # createAt 순서대로 정렬
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["id"], "block1")
        self.assertEqual(result[1]["id"], "block2")
        self.assertEqual(result[2]["id"], "block3")

    @patch("mattermost_cli._fetch_blocks_by_parent_id")
    def test_fetch_with_partial_content_order(self, mock_fetch):
        """정상 케이스: 일부만 contentOrder에 있는 경우"""
        mock_fetch.return_value = [
            {"id": "block1", "createAt": 100},
            {"id": "block2", "createAt": 200},
            {"id": "block3", "createAt": 300}
        ]

        # block2만 contentOrder에 있음
        result = mattermost_cli._fetch_card_contents("board123", "card456", ["block2"])

        # block2가 먼저, 나머지는 createAt 순서
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["id"], "block2")
        self.assertEqual(result[1]["id"], "block1")
        self.assertEqual(result[2]["id"], "block3")

    @patch("mattermost_cli._fetch_blocks_by_parent_id")
    def test_fetch_no_blocks(self, mock_fetch):
        """정상 케이스: 블록이 없는 경우"""
        mock_fetch.return_value = []

        result = mattermost_cli._fetch_card_contents("board123", "card456", [])
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
