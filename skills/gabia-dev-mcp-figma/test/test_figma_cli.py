#!/usr/bin/env python3
"""
Figma CLI 스크립트의 단위 테스트
외부 API 호출은 mock으로 처리하여 네트워크 의존성 제거
"""
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

# 테스트 대상 모듈 import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import figma_cli


class TestRateLimitInfo:
    """RateLimitInfo 데이터클래스 테스트"""

    def test_to_dict(self):
        """to_dict 메서드가 올바른 딕셔너리를 반환하는지 확인"""
        info = figma_cli.RateLimitInfo(
            retry_after=60,
            plan_tier="pro",
            rate_limit_type="low",
            upgrade_link="https://example.com/upgrade",
        )
        result = info.to_dict()
        assert result["retry_after_seconds"] == 60
        assert result["plan_tier"] == "pro"
        assert result["rate_limit_type"] == "low"
        assert result["upgrade_link"] == "https://example.com/upgrade"

    def test_str_representation(self):
        """문자열 표현이 모든 정보를 포함하는지 확인"""
        info = figma_cli.RateLimitInfo(
            retry_after=30,
            plan_tier="starter",
            rate_limit_type="low",
            upgrade_link=None,
        )
        result = str(info)
        assert "30 seconds" in result
        assert "starter" in result
        assert "View/Collaborator seat" in result


class TestRateLimitError:
    """RateLimitError 예외 클래스 테스트"""

    def test_exception_creation(self):
        """예외가 올바른 정보를 담고 있는지 확인"""
        info = figma_cli.RateLimitInfo(60, "pro", "high", None)
        error = figma_cli.RateLimitError(info)
        assert error.info == info
        assert "60 seconds" in str(error)


class TestHelperFunctions:
    """헬퍼 함수들의 단위 테스트"""

    def test_parse_rate_limit_headers_complete(self):
        """모든 헤더가 존재할 때 정상 파싱"""
        headers = {
            "Retry-After": "90",
            "X-Figma-Plan-Tier": "enterprise",
            "X-Figma-Rate-Limit-Type": "high",
            "X-Figma-Upgrade-Link": "https://figma.com/upgrade",
        }
        info = figma_cli._parse_rate_limit_headers(headers)
        assert info.retry_after == 90
        assert info.plan_tier == "enterprise"
        assert info.rate_limit_type == "high"
        assert info.upgrade_link == "https://figma.com/upgrade"

    def test_parse_rate_limit_headers_minimal(self):
        """필수 헤더만 존재할 때 기본값 적용"""
        headers = {}
        info = figma_cli._parse_rate_limit_headers(headers)
        assert info.retry_after == 60  # 기본값
        assert info.plan_tier is None
        assert info.rate_limit_type is None
        assert info.upgrade_link is None

    def test_parse_rate_limit_headers_case_insensitive(self):
        """헤더 이름이 대소문자 무관하게 처리되는지 확인"""
        headers = {
            "retry-after": "45",
            "x-figma-plan-tier": "org",
        }
        info = figma_cli._parse_rate_limit_headers(headers)
        assert info.retry_after == 45
        assert info.plan_tier == "org"

    def test_env_normal(self):
        """환경변수가 정상적으로 반환되는지 확인"""
        with patch.dict(os.environ, {"TEST_VAR": "value"}):
            assert figma_cli._env("TEST_VAR") == "value"

    def test_env_missing(self):
        """환경변수가 없을 때 None 반환"""
        with patch.dict(os.environ, {}, clear=True):
            assert figma_cli._env("MISSING_VAR") is None

    def test_env_empty_string(self):
        """빈 문자열 환경변수는 None으로 처리"""
        with patch.dict(os.environ, {"EMPTY_VAR": "  "}):
            assert figma_cli._env("EMPTY_VAR") is None

    def test_auth_headers_with_oauth(self):
        """OAuth 토큰이 있을 때 Authorization 헤더 생성"""
        with patch.dict(os.environ, {"FIGMA_OAUTH_TOKEN": "oauth_token_123"}):
            headers = figma_cli._auth_headers()
            assert headers["Authorization"] == "Bearer oauth_token_123"
            assert "X-Figma-Token" not in headers

    def test_auth_headers_with_api_key(self):
        """API 키만 있을 때 X-Figma-Token 헤더 생성"""
        with patch.dict(os.environ, {"FIGMA_API_KEY": "api_key_456"}, clear=True):
            headers = figma_cli._auth_headers()
            assert headers["X-Figma-Token"] == "api_key_456"
            assert "Authorization" not in headers

    def test_auth_headers_missing_credentials(self):
        """인증 정보가 없을 때 SystemExit 발생"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                figma_cli._auth_headers()
            assert "Missing Figma auth" in str(exc_info.value)

    def test_apply_suffix_with_extension(self):
        """파일 확장자가 있을 때 suffix 적용"""
        result = figma_cli._apply_suffix("icon.png", "2x")
        assert result == "icon-2x.png"

    def test_apply_suffix_without_extension(self):
        """확장자가 없을 때 suffix를 뒤에 추가"""
        result = figma_cli._apply_suffix("myfile", "large")
        assert result == "myfile-large"

    def test_apply_suffix_already_exists(self):
        """suffix가 이미 포함되어 있으면 추가하지 않음"""
        result = figma_cli._apply_suffix("icon-2x.png", "2x")
        assert result == "icon-2x.png"

    def test_apply_suffix_none(self):
        """suffix가 None이면 원본 반환"""
        result = figma_cli._apply_suffix("file.svg", None)
        assert result == "file.svg"


class TestHttpJson:
    """HTTP JSON 요청 함수 테스트"""

    @patch("figma_cli.urllib.request.urlopen")
    @patch("figma_cli._auth_headers")
    def test_http_json_success(self, mock_auth, mock_urlopen):
        """정상 API 응답 처리"""
        mock_auth.return_value = {"Authorization": "Bearer token"}
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "ok"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = figma_cli._http_json("GET", "https://api.figma.com/v1/test")
        assert result == {"status": "ok"}

    @patch("figma_cli.urllib.request.urlopen")
    @patch("figma_cli._auth_headers")
    def test_http_json_with_params(self, mock_auth, mock_urlopen):
        """쿼리 파라미터가 URL에 올바르게 추가되는지 확인"""
        mock_auth.return_value = {"Authorization": "Bearer token"}
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"data": []}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        figma_cli._http_json(
            "GET",
            "https://api.figma.com/v1/test",
            params={"key": "value", "ids": ["a", "b"]},
        )
        # urlopen이 호출된 request 객체 확인
        request = mock_urlopen.call_args[0][0]
        assert "key=value" in request.full_url
        assert "ids=a" in request.full_url

    @patch("figma_cli.urllib.request.urlopen")
    @patch("figma_cli._auth_headers")
    @patch("figma_cli.time.sleep")
    def test_http_json_rate_limit_auto_retry(self, mock_sleep, mock_auth, mock_urlopen):
        """Rate limit 발생 시 자동 재시도 기능"""
        mock_auth.return_value = {"Authorization": "Bearer token"}

        # 첫 번째 호출: 429 에러
        error_response = MagicMock()
        error_response.code = 429
        error_response.headers = {"Retry-After": "2"}
        error_response.read.return_value = b"Rate limit exceeded"

        # 두 번째 호출: 성공
        success_response = MagicMock()
        success_response.read.return_value = b'{"status": "ok"}'

        mock_urlopen.side_effect = [
            figma_cli.urllib.error.HTTPError("url", 429, "Too Many Requests", error_response.headers, error_response),
            MagicMock(__enter__=MagicMock(return_value=success_response)),
        ]

        result = figma_cli._http_json(
            "GET",
            "https://api.figma.com/v1/test",
            auto_retry=True,
            max_retries=3,
        )
        assert result == {"status": "ok"}
        mock_sleep.assert_called_once_with(2)

    @patch("figma_cli.urllib.request.urlopen")
    @patch("figma_cli._auth_headers")
    def test_http_json_rate_limit_no_retry(self, mock_auth, mock_urlopen):
        """Rate limit 발생 시 재시도하지 않으면 SystemExit"""
        mock_auth.return_value = {"Authorization": "Bearer token"}

        error_response = MagicMock()
        error_response.code = 429
        error_response.headers = {"Retry-After": "60"}
        error_response.read.return_value = b"Rate limit exceeded"

        mock_urlopen.side_effect = figma_cli.urllib.error.HTTPError(
            "url", 429, "Too Many Requests", error_response.headers, error_response
        )

        with pytest.raises(SystemExit) as exc_info:
            figma_cli._http_json("GET", "https://api.figma.com/v1/test", auto_retry=False)
        assert "RATE_LIMIT" in str(exc_info.value)

    @patch("figma_cli.urllib.request.urlopen")
    @patch("figma_cli._auth_headers")
    def test_http_json_http_error(self, mock_auth, mock_urlopen):
        """일반 HTTP 에러 처리"""
        mock_auth.return_value = {"Authorization": "Bearer token"}

        error_response = MagicMock()
        error_response.read.return_value = b"Not Found"

        mock_urlopen.side_effect = figma_cli.urllib.error.HTTPError(
            "url", 404, "Not Found", {}, error_response
        )

        with pytest.raises(SystemExit) as exc_info:
            figma_cli._http_json("GET", "https://api.figma.com/v1/test")
        assert "404" in str(exc_info.value)


class TestDownloadBytes:
    """바이트 다운로드 함수 테스트"""

    @patch("figma_cli.urllib.request.urlopen")
    def test_download_bytes_success(self, mock_urlopen):
        """정상적인 바이너리 데이터 다운로드"""
        mock_response = MagicMock()
        mock_response.read.return_value = b"\x89PNG\r\n\x1a\n"
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = figma_cli._download_bytes("https://example.com/image.png")
        assert result == b"\x89PNG\r\n\x1a\n"

    @patch("figma_cli.urllib.request.urlopen")
    @patch("figma_cli.time.sleep")
    def test_download_bytes_rate_limit_retry(self, mock_sleep, mock_urlopen):
        """Rate limit 발생 시 재시도"""
        error_response = MagicMock()
        error_response.code = 429
        error_response.headers = {"Retry-After": "1"}
        error_response.read.return_value = b"Rate limit"

        success_response = MagicMock()
        success_response.read.return_value = b"image_data"

        mock_urlopen.side_effect = [
            figma_cli.urllib.error.HTTPError("url", 429, "Too Many Requests", error_response.headers, error_response),
            MagicMock(__enter__=MagicMock(return_value=success_response)),
        ]

        result = figma_cli._download_bytes("https://example.com/image.png", auto_retry=True, max_retries=2)
        assert result == b"image_data"
        mock_sleep.assert_called_once()


class TestReadNodes:
    """노드 JSON 읽기 함수 테스트"""

    def test_read_nodes_valid(self, tmp_path):
        """정상적인 노드 JSON 파일 읽기"""
        nodes_file = tmp_path / "nodes.json"
        nodes_data = [
            {"fileName": "icon.png", "nodeId": "123"},
            {"fileName": "logo.svg", "imageRef": "ref456"},
        ]
        nodes_file.write_text(json.dumps(nodes_data))

        result = figma_cli._read_nodes(str(nodes_file))
        assert len(result) == 2
        assert result[0]["fileName"] == "icon.png"
        assert result[1]["fileName"] == "logo.svg"

    def test_read_nodes_invalid_json(self, tmp_path):
        """JSON 배열이 아닌 경우 에러"""
        nodes_file = tmp_path / "nodes.json"
        nodes_file.write_text('{"not": "array"}')

        with pytest.raises(SystemExit) as exc_info:
            figma_cli._read_nodes(str(nodes_file))
        assert "must be an array" in str(exc_info.value)

    def test_read_nodes_missing_filename(self, tmp_path):
        """fileName이 없는 항목은 건너뜀"""
        nodes_file = tmp_path / "nodes.json"
        nodes_data = [
            {"fileName": "valid.png", "nodeId": "123"},
            {"nodeId": "456"},  # fileName 없음
            {"fileName": "", "nodeId": "789"},  # 빈 문자열
        ]
        nodes_file.write_text(json.dumps(nodes_data))

        result = figma_cli._read_nodes(str(nodes_file))
        assert len(result) == 1
        assert result[0]["fileName"] == "valid.png"

    def test_read_nodes_none(self):
        """파일 경로가 None인 경우 에러"""
        with pytest.raises(SystemExit) as exc_info:
            figma_cli._read_nodes(None)
        assert "Provide --nodes-json" in str(exc_info.value)


class TestCmdGet:
    """get 명령어 테스트"""

    @patch("figma_cli._http_json")
    @patch("builtins.print")
    def test_cmd_get_file(self, mock_print, mock_http):
        """파일 전체 조회"""
        mock_http.return_value = {"name": "Test File", "document": {}}

        args = MagicMock(
            file_key="abc123",
            node_id=None,
            depth=None,
            auto_retry=False,
            max_retries=3,
        )
        figma_cli.cmd_get(args)

        mock_http.assert_called_once()
        assert "files/abc123" in mock_http.call_args[0][1]
        mock_print.assert_called_once()

    @patch("figma_cli._http_json")
    @patch("builtins.print")
    def test_cmd_get_node(self, mock_print, mock_http):
        """특정 노드 조회"""
        mock_http.return_value = {"nodes": {"node1": {"name": "Button"}}}

        args = MagicMock(
            file_key="abc123",
            node_id="node1",
            depth=2,
            auto_retry=True,
            max_retries=5,
        )
        figma_cli.cmd_get(args)

        mock_http.assert_called_once()
        assert "nodes" in mock_http.call_args[0][1]
        assert mock_http.call_args[1]["auto_retry"] is True
        assert mock_http.call_args[1]["max_retries"] == 5


class TestCmdDownload:
    """download 명령어 테스트"""

    @patch("figma_cli._download_bytes")
    @patch("figma_cli._http_json")
    @patch("figma_cli._read_nodes")
    @patch("builtins.print")
    def test_cmd_download_fills(self, mock_print, mock_read_nodes, mock_http, mock_download):
        """이미지 fill 다운로드"""
        mock_read_nodes.return_value = [
            {"fileName": "bg.png", "imageRef": "ref123"},
        ]
        mock_http.return_value = {
            "meta": {"images": {"ref123": "https://example.com/image.png"}}
        }
        mock_download.return_value = b"image_data"

        with patch("pathlib.Path.write_bytes") as mock_write:
            args = MagicMock(
                file_key="file123",
                local_path="/tmp/output",
                nodes_json="nodes.json",
                png_scale=2,
                auto_retry=False,
                max_retries=3,
            )
            figma_cli.cmd_download(args)

            mock_download.assert_called_once_with(
                "https://example.com/image.png",
                auto_retry=False,
                max_retries=3,
            )
            mock_write.assert_called_once()

    @patch("figma_cli._download_bytes")
    @patch("figma_cli._http_json")
    @patch("figma_cli._read_nodes")
    @patch("builtins.print")
    def test_cmd_download_png_render(self, mock_print, mock_read_nodes, mock_http, mock_download):
        """PNG 렌더링 다운로드"""
        mock_read_nodes.return_value = [
            {"fileName": "icon.png", "nodeId": "node1"},
        ]
        # 첫 번째 호출: fills 조회, 두 번째 호출: PNG 렌더링
        mock_http.side_effect = [
            {"meta": {"images": {}}},
            {"images": {"node1": "https://example.com/rendered.png"}},
        ]
        mock_download.return_value = b"png_data"

        with patch("pathlib.Path.write_bytes") as mock_write:
            args = MagicMock(
                file_key="file123",
                local_path="/tmp/output",
                nodes_json="nodes.json",
                png_scale=3,
                auto_retry=True,
                max_retries=5,
            )
            figma_cli.cmd_download(args)

            # PNG 렌더링 요청 확인
            render_call = mock_http.call_args_list[1]
            assert "images/file123" in render_call[0][1]
            assert render_call[1]["params"]["format"] == "png"
            assert render_call[1]["params"]["scale"] == "3"

    @patch("figma_cli._download_bytes")
    @patch("figma_cli._http_json")
    @patch("figma_cli._read_nodes")
    @patch("builtins.print")
    def test_cmd_download_svg_render(self, mock_print, mock_read_nodes, mock_http, mock_download):
        """SVG 렌더링 다운로드"""
        mock_read_nodes.return_value = [
            {"fileName": "icon.svg", "nodeId": "node2"},
        ]
        # SVG 파일만 있으므로 2개의 HTTP 호출 발생
        # 1. fills 조회, 2. SVG 렌더링
        mock_http.side_effect = [
            {"meta": {"images": {}}},  # fills 조회
            {"images": {"node2": "https://example.com/rendered.svg"}},  # SVG 렌더링
        ]
        mock_download.return_value = b"<svg></svg>"

        with patch("pathlib.Path.write_bytes") as mock_write:
            args = MagicMock(
                file_key="file123",
                local_path="/tmp/output",
                nodes_json="nodes.json",
                png_scale=2,
                auto_retry=False,
                max_retries=3,
            )
            figma_cli.cmd_download(args)

            # SVG 렌더링 요청 확인 (두 번째 호출)
            svg_render_call = mock_http.call_args_list[1]
            params = svg_render_call[1]["params"]
            assert params["format"] == "svg"
            # extra 파라미터들이 params에 병합됨
            assert params["svg_outline_text"] == "true"


class TestBuildParser:
    """argparse 파서 테스트"""

    def test_parser_get_command(self):
        """get 명령어 파싱"""
        parser = figma_cli.build_parser()
        args = parser.parse_args(["get", "--file-key", "abc123"])
        assert args.cmd == "get"
        assert args.file_key == "abc123"
        assert args.func == figma_cli.cmd_get

    def test_parser_get_with_node(self):
        """get 명령어에 node-id 옵션"""
        parser = figma_cli.build_parser()
        args = parser.parse_args(["get", "--file-key", "abc", "--node-id", "node1", "--depth", "3"])
        assert args.node_id == "node1"
        assert args.depth == 3

    def test_parser_download_command(self):
        """download 명령어 파싱"""
        parser = figma_cli.build_parser()
        args = parser.parse_args([
            "download",
            "--file-key", "abc123",
            "--local-path", "/tmp/out",
            "--nodes-json", "nodes.json",
            "--png-scale", "4",
        ])
        assert args.cmd == "download"
        assert args.file_key == "abc123"
        assert args.local_path == "/tmp/out"
        assert args.nodes_json == "nodes.json"
        assert args.png_scale == 4

    def test_parser_auto_retry_options(self):
        """auto-retry 옵션 파싱"""
        parser = figma_cli.build_parser()
        args = parser.parse_args([
            "get",
            "--file-key", "abc",
            "--auto-retry",
            "--max-retries", "5",
        ])
        assert args.auto_retry is True
        assert args.max_retries == 5

    def test_parser_missing_required(self):
        """필수 인자 누락 시 에러"""
        parser = figma_cli.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["get"])  # file-key 누락


class TestMainFunction:
    """main 함수 테스트"""

    @patch("figma_cli.build_parser")
    def test_main_calls_func(self, mock_build_parser):
        """main이 파싱된 함수를 호출하는지 확인"""
        mock_func = MagicMock()
        mock_args = MagicMock(func=mock_func)
        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = mock_args
        mock_build_parser.return_value = mock_parser

        figma_cli.main()

        mock_func.assert_called_once_with(mock_args)
