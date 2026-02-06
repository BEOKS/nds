#!/usr/bin/env python3
"""
GitLab Merge Requests CLI 스크립트의 단위 테스트
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
import gitlab_mr_cli


class TestHelperFunctions:
    """헬퍼 함수들의 단위 테스트"""

    def test_env_normal(self):
        """환경변수가 정상적으로 반환되는지 확인"""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            assert gitlab_mr_cli._env("TEST_VAR") == "test_value"

    def test_env_missing(self):
        """환경변수가 없을 때 None 반환"""
        with patch.dict(os.environ, {}, clear=True):
            assert gitlab_mr_cli._env("MISSING_VAR") is None

    def test_env_whitespace_only(self):
        """공백만 있는 환경변수는 None으로 처리"""
        with patch.dict(os.environ, {"WHITESPACE": "   \t\n  "}):
            assert gitlab_mr_cli._env("WHITESPACE") is None

    def test_require_env_success(self):
        """필수 환경변수가 존재하면 값 반환"""
        with patch.dict(os.environ, {"REQUIRED": "value"}):
            assert gitlab_mr_cli._require_env("REQUIRED") == "value"

    def test_require_env_missing(self):
        """필수 환경변수가 없으면 SystemExit"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                gitlab_mr_cli._require_env("REQUIRED")
            assert "Missing required env" in str(exc_info.value)

    def test_api_base_default(self):
        """기본 API base URL 반환"""
        with patch.dict(os.environ, {}, clear=True):
            assert gitlab_mr_cli._api_base() == "https://gitlab.gabia.com/api/v4"

    def test_api_base_custom(self):
        """커스텀 API base URL 사용 (trailing slash 제거)"""
        with patch.dict(os.environ, {"GITLAB_API_URL": "https://custom.gitlab.com/api/v4///"}):
            assert gitlab_mr_cli._api_base() == "https://custom.gitlab.com/api/v4"

    def test_auth_headers(self):
        """인증 헤더 생성"""
        with patch.dict(os.environ, {"GITLAB_TOKEN": "secret_token"}):
            headers = gitlab_mr_cli._auth_headers()
            assert headers["Authorization"] == "Bearer secret_token"
            assert headers["PRIVATE-TOKEN"] == "secret_token"
            assert headers["Accept"] == "application/json"
            assert headers["Content-Type"] == "application/json"

    def test_encode_project_id_simple(self):
        """단순 문자열 project ID"""
        result = gitlab_mr_cli._encode_project_id("simple")
        assert result == "simple"

    def test_encode_project_id_with_slash(self):
        """슬래시를 포함한 project ID URL 인코딩"""
        result = gitlab_mr_cli._encode_project_id("group/subgroup/project")
        assert result == "group%2Fsubgroup%2Fproject"

    def test_encode_project_id_already_encoded(self):
        """이미 인코딩된 ID는 재인코딩"""
        result = gitlab_mr_cli._encode_project_id("group%2Fproject")
        assert result == "group%2Fproject"

    def test_json_parsing(self):
        """바이트를 JSON으로 파싱"""
        raw = b'{"key": "value", "num": 42}'
        result = gitlab_mr_cli._json(raw)
        assert result == {"key": "value", "num": 42}

    def test_json_parsing_unicode(self):
        """유니코드 문자 파싱"""
        raw = '{"name": "한글"}'.encode("utf-8")
        result = gitlab_mr_cli._json(raw)
        assert result == {"name": "한글"}

    def test_pagination_complete(self):
        """완전한 페이지네이션 헤더"""
        headers = {
            "x-page": "3",
            "x-per-page": "100",
            "x-total": "350",
            "x-total-pages": "4",
        }
        result = gitlab_mr_cli._pagination(headers)
        assert result["page"] == 3
        assert result["per_page"] == 100
        assert result["total"] == 350
        assert result["total_pages"] == 4

    def test_pagination_defaults(self):
        """페이지네이션 헤더가 없을 때 기본값"""
        headers = {}
        result = gitlab_mr_cli._pagination(headers)
        assert result["page"] == 1
        assert result["per_page"] == 20
        assert result["total"] == 0
        assert result["total_pages"] == 0

    def test_pagination_invalid_values(self):
        """잘못된 값이 있을 때 기본값 사용"""
        headers = {"x-page": "not-a-number", "x-total": "also-invalid"}
        result = gitlab_mr_cli._pagination(headers)
        assert result["page"] == 1
        assert result["total"] == 0

    def test_read_text_argument_direct_value(self):
        """직접 값 제공"""
        result = gitlab_mr_cli._read_text_argument("direct value", None)
        assert result == "direct value"

    def test_read_text_argument_from_file(self, tmp_path):
        """파일에서 읽기"""
        test_file = tmp_path / "desc.txt"
        test_file.write_text("file content\nline2", encoding="utf-8")
        result = gitlab_mr_cli._read_text_argument(None, str(test_file))
        assert result == "file content\nline2"

    @patch("sys.stdin.isatty", return_value=False)
    @patch("sys.stdin.read", return_value="stdin input")
    def test_read_text_argument_stdin(self, mock_read, mock_isatty):
        """stdin에서 읽기"""
        result = gitlab_mr_cli._read_text_argument(None, None)
        assert result == "stdin input"

    @patch("sys.stdin.isatty", return_value=True)
    def test_read_text_argument_none(self, mock_isatty):
        """모든 소스가 없을 때 None"""
        result = gitlab_mr_cli._read_text_argument(None, None)
        assert result is None


class TestHttpFunction:
    """HTTP 요청 함수 테스트"""

    @patch("gitlab_mr_cli.urllib.request.urlopen")
    @patch("gitlab_mr_cli._auth_headers")
    def test_http_get_success(self, mock_auth, mock_urlopen):
        """GET 요청 성공"""
        mock_auth.return_value = {"Authorization": "Bearer token"}
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"mr_id": 1}'
        mock_response.headers.items.return_value = [("X-Total", "10")]
        mock_urlopen.return_value.__enter__.return_value = mock_response

        raw, headers = gitlab_mr_cli._http("GET", "https://gitlab.com/api/v4/merge_requests/1")
        assert raw == b'{"mr_id": 1}'
        assert headers["x-total"] == "10"

    @patch("gitlab_mr_cli.urllib.request.urlopen")
    @patch("gitlab_mr_cli._auth_headers")
    def test_http_post_with_body(self, mock_auth, mock_urlopen):
        """POST 요청에 JSON body 포함"""
        mock_auth.return_value = {"Authorization": "Bearer token"}
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"id": 123}'
        mock_response.headers.items.return_value = []
        mock_urlopen.return_value.__enter__.return_value = mock_response

        body = {"title": "New MR", "source_branch": "feature"}
        raw, _ = gitlab_mr_cli._http("POST", "https://gitlab.com/api/v4/merge_requests", body=body)

        request = mock_urlopen.call_args[0][0]
        assert request.method == "POST"
        assert request.data == json.dumps(body).encode("utf-8")

    @patch("gitlab_mr_cli.urllib.request.urlopen")
    @patch("gitlab_mr_cli._auth_headers")
    def test_http_with_params(self, mock_auth, mock_urlopen):
        """쿼리 파라미터 추가"""
        mock_auth.return_value = {"Authorization": "Bearer token"}
        mock_response = MagicMock()
        mock_response.read.return_value = b'[]'
        mock_response.headers.items.return_value = []
        mock_urlopen.return_value.__enter__.return_value = mock_response

        params = [("state", "merged"), ("labels", "feature")]
        gitlab_mr_cli._http("GET", "https://gitlab.com/api/v4/merge_requests", params=params)

        request = mock_urlopen.call_args[0][0]
        assert "state=merged" in request.full_url
        assert "labels=feature" in request.full_url

    @patch("gitlab_mr_cli.urllib.request.urlopen")
    @patch("gitlab_mr_cli._auth_headers")
    def test_http_error_500(self, mock_auth, mock_urlopen):
        """서버 에러 처리"""
        mock_auth.return_value = {"Authorization": "Bearer token"}
        error_response = MagicMock()
        error_response.read.return_value = b"Internal Server Error"
        mock_urlopen.side_effect = gitlab_mr_cli.urllib.error.HTTPError(
            "url", 500, "Internal Server Error", {}, error_response
        )

        with pytest.raises(SystemExit) as exc_info:
            gitlab_mr_cli._http("GET", "https://gitlab.com/api/v4/merge_requests")
        assert "500" in str(exc_info.value)

    @patch("gitlab_mr_cli.urllib.request.urlopen")
    @patch("gitlab_mr_cli._auth_headers")
    def test_http_network_error(self, mock_auth, mock_urlopen):
        """네트워크 에러 처리"""
        mock_auth.return_value = {"Authorization": "Bearer token"}
        mock_urlopen.side_effect = gitlab_mr_cli.urllib.error.URLError("Network unreachable")

        with pytest.raises(SystemExit) as exc_info:
            gitlab_mr_cli._http("GET", "https://gitlab.com/api/v4/merge_requests")
        assert "Network error" in str(exc_info.value)


class TestCmdGet:
    """get 명령어 테스트"""

    @patch("gitlab_mr_cli._http")
    @patch("builtins.print")
    def test_cmd_get_by_id(self, mock_print, mock_http):
        """MR ID로 조회"""
        mock_http.return_value = (b'{"id": 1, "title": "Test MR"}', {})

        args = MagicMock(
            project_id="myproject",
            merge_request_id="42",
            source_branch=None,
        )
        gitlab_mr_cli.cmd_get(args)

        assert "projects/myproject/merge_requests/42" in mock_http.call_args[0][1]
        mock_print.assert_called_once()

    @patch("gitlab_mr_cli._http")
    @patch("builtins.print")
    def test_cmd_get_by_source_branch(self, mock_print, mock_http):
        """소스 브랜치로 조회"""
        mock_http.return_value = (b'[{"id": 1, "iid": 42}]', {})

        args = MagicMock(
            project_id="myproject",
            merge_request_id=None,
            source_branch="feature-branch",
        )
        gitlab_mr_cli.cmd_get(args)

        call_args = mock_http.call_args
        assert "merge_requests" in call_args[0][1]
        assert call_args[1]["params"][0] == ("source_branch", "feature-branch")

    @patch("gitlab_mr_cli._http")
    @patch("builtins.print")
    def test_cmd_get_no_mr_found(self, mock_print, mock_http):
        """브랜치로 조회했지만 MR이 없는 경우"""
        mock_http.return_value = (b'[]', {})

        args = MagicMock(
            project_id="myproject",
            merge_request_id=None,
            source_branch="non-existent",
        )
        gitlab_mr_cli.cmd_get(args)

        # None이 출력되어야 함
        printed = mock_print.call_args[0][0]
        assert json.loads(printed) is None

    def test_cmd_get_missing_both_args(self):
        """MR ID와 브랜치 모두 없으면 에러"""
        args = MagicMock(
            project_id="myproject",
            merge_request_id=None,
            source_branch=None,
        )
        with pytest.raises(SystemExit) as exc_info:
            gitlab_mr_cli.cmd_get(args)
        assert "Provide --merge-request-id or --source-branch" in str(exc_info.value)


class TestCmdDiffs:
    """diffs 명령어 테스트"""

    @patch("gitlab_mr_cli._http")
    @patch("builtins.print")
    def test_cmd_diffs_by_id(self, mock_print, mock_http):
        """MR ID로 diff 조회"""
        mock_http.return_value = (b'{"changes": [{"diff": "..."}]}', {})

        args = MagicMock(
            project_id="myproject",
            merge_request_id="50",
            source_branch=None,
            view=None,
        )
        gitlab_mr_cli.cmd_diffs(args)

        assert "merge_requests/50/changes" in mock_http.call_args[0][1]

    @patch("gitlab_mr_cli._http")
    @patch("builtins.print")
    def test_cmd_diffs_by_branch(self, mock_print, mock_http):
        """소스 브랜치로 MR을 찾아서 diff 조회"""
        # 첫 번째 호출: MR 찾기
        # 두 번째 호출: changes 조회
        mock_http.side_effect = [
            (b'[{"iid": 60}]', {}),
            (b'{"changes": []}', {}),
        ]

        args = MagicMock(
            project_id="myproject",
            merge_request_id=None,
            source_branch="feature",
            view="inline",
        )
        gitlab_mr_cli.cmd_diffs(args)

        # 두 번째 호출이 changes 엔드포인트인지 확인
        changes_call = mock_http.call_args_list[1]
        assert "merge_requests/60/changes" in changes_call[0][1]
        assert changes_call[1]["params"][0] == ("view", "inline")

    @patch("gitlab_mr_cli._http")
    def test_cmd_diffs_branch_not_found(self, mock_http):
        """브랜치로 MR을 찾지 못한 경우 에러"""
        mock_http.return_value = (b'[]', {})

        args = MagicMock(
            project_id="myproject",
            merge_request_id=None,
            source_branch="unknown",
            view=None,
        )
        with pytest.raises(SystemExit) as exc_info:
            gitlab_mr_cli.cmd_diffs(args)
        assert "No merge request found" in str(exc_info.value)


class TestCmdDiscussions:
    """discussions 명령어 테스트"""

    @patch("gitlab_mr_cli._http")
    @patch("builtins.print")
    def test_cmd_discussions_list(self, mock_print, mock_http):
        """MR 토론 목록 조회"""
        mock_http.return_value = (b'[{"id": "disc1"}]', {"x-total": "1"})

        args = MagicMock(
            project_id="myproject",
            merge_request_id="70",
            page=None,
            per_page=None,
        )
        gitlab_mr_cli.cmd_discussions(args)

        assert "merge_requests/70/discussions" in mock_http.call_args[0][1]

    @patch("gitlab_mr_cli._http")
    @patch("builtins.print")
    def test_cmd_discussions_with_pagination(self, mock_print, mock_http):
        """페이지네이션 파라미터 포함"""
        mock_http.return_value = (b'[]', {})

        args = MagicMock(
            project_id="myproject",
            merge_request_id="70",
            page=2,
            per_page=50,
        )
        gitlab_mr_cli.cmd_discussions(args)

        params = mock_http.call_args[1]["params"]
        assert ("page", "2") in params
        assert ("per_page", "50") in params


class TestCmdCreate:
    """create 명령어 테스트"""

    @patch("sys.stdin.isatty", return_value=True)
    @patch("gitlab_mr_cli._http")
    @patch("builtins.print")
    def test_cmd_create_minimal(self, mock_print, mock_http, mock_isatty):
        """최소 필수 정보로 MR 생성"""
        mock_http.return_value = (b'{"id": 1}', {})

        args = MagicMock(
            project_id="myproject",
            title="New MR",
            source_branch="feature",
            target_branch="main",
            description=None,
            description_file=None,
            target_project_id=None,
            assignee_ids=None,
            reviewer_ids=None,
            labels=None,
            draft=None,
            allow_collaboration=None,
            remove_source_branch=None,
            squash=None,
        )
        gitlab_mr_cli.cmd_create(args)

        payload = mock_http.call_args[1]["body"]
        assert payload["title"] == "New MR"
        assert payload["source_branch"] == "feature"
        assert payload["target_branch"] == "main"

    @patch("gitlab_mr_cli._http")
    @patch("builtins.print")
    def test_cmd_create_full_options(self, mock_print, mock_http):
        """모든 옵션을 포함하여 MR 생성"""
        mock_http.return_value = (b'{"id": 1}', {})

        args = MagicMock(
            project_id="group/project",
            title="Complete MR",
            source_branch="feature",
            target_branch="develop",
            description="Full description",
            description_file=None,
            target_project_id=999,
            assignee_ids=[10, 20],
            reviewer_ids=[30],
            labels=["feature", "urgent"],
            draft=True,
            allow_collaboration=True,
            remove_source_branch=True,
            squash=False,
        )
        gitlab_mr_cli.cmd_create(args)

        payload = mock_http.call_args[1]["body"]
        assert payload["description"] == "Full description"
        assert payload["target_project_id"] == 999
        assert payload["assignee_ids"] == [10, 20]
        assert payload["reviewer_ids"] == [30]
        assert payload["labels"] == "feature,urgent"
        assert payload["draft"] is True
        assert payload["allow_collaboration"] is True
        assert payload["remove_source_branch"] is True
        assert payload["squash"] is False


class TestCmdList:
    """list 명령어 테스트"""

    @patch("gitlab_mr_cli._http")
    @patch("builtins.print")
    def test_cmd_list_basic(self, mock_print, mock_http):
        """기본 MR 목록 조회"""
        mock_http.return_value = (b'[{"id": 1}, {"id": 2}]', {"x-total": "2"})

        args = MagicMock(
            project_id="myproject",
            assignee_id=None,
            assignee_username=None,
            author_id=None,
            author_username=None,
            reviewer_id=None,
            reviewer_username=None,
            created_after=None,
            created_before=None,
            updated_after=None,
            updated_before=None,
            labels=None,
            milestone=None,
            scope=None,
            search=None,
            state=None,
            wip=None,
            with_merge_status_recheck=None,
            order_by=None,
            sort=None,
            view=None,
            my_reaction_emoji=None,
            source_branch=None,
            target_branch=None,
            page=None,
            per_page=None,
            param=None,
        )
        gitlab_mr_cli.cmd_list(args)

        assert "projects/myproject/merge_requests" in mock_http.call_args[0][1]

    @patch("gitlab_mr_cli._http")
    @patch("builtins.print")
    def test_cmd_list_with_filters(self, mock_print, mock_http):
        """필터링 옵션 포함"""
        mock_http.return_value = (b'[]', {})

        args = MagicMock(
            project_id="myproject",
            state="merged",
            author_id=5,
            labels=["bug", "hotfix"],
            source_branch="hotfix-branch",
            target_branch="production",
            page=3,
            per_page=20,
            param=["custom=value"],
            assignee_id=None,
            assignee_username=None,
            author_username=None,
            reviewer_id=None,
            reviewer_username=None,
            created_after=None,
            created_before=None,
            updated_after=None,
            updated_before=None,
            milestone=None,
            scope=None,
            search=None,
            wip=None,
            with_merge_status_recheck=None,
            order_by=None,
            sort=None,
            view=None,
            my_reaction_emoji=None,
        )
        gitlab_mr_cli.cmd_list(args)

        params = mock_http.call_args[1]["params"]
        assert ("state", "merged") in params
        assert ("author_id", "5") in params
        assert ("labels", "bug,hotfix") in params
        assert ("source_branch", "hotfix-branch") in params
        assert ("custom", "value") in params


class TestBuildParser:
    """argparse 파서 테스트"""

    def test_parser_get_command(self):
        """get 명령어 파싱"""
        parser = gitlab_mr_cli.build_parser()
        args = parser.parse_args([
            "get",
            "--project-id", "myproject",
            "--merge-request-id", "10",
        ])
        assert args.cmd == "get"
        assert args.project_id == "myproject"
        assert args.merge_request_id == "10"

    def test_parser_diffs_command(self):
        """diffs 명령어 파싱"""
        parser = gitlab_mr_cli.build_parser()
        args = parser.parse_args([
            "diffs",
            "--project-id", "myproject",
            "--source-branch", "feature",
            "--view", "parallel",
        ])
        assert args.cmd == "diffs"
        assert args.source_branch == "feature"
        assert args.view == "parallel"

    def test_parser_create_command(self):
        """create 명령어 파싱"""
        parser = gitlab_mr_cli.build_parser()
        args = parser.parse_args([
            "create",
            "--project-id", "myproject",
            "--source-branch", "feature",
            "--target-branch", "main",
            "--title", "Test MR",
            "--draft",
        ])
        assert args.cmd == "create"
        assert args.draft is True

    def test_parser_list_command(self):
        """list 명령어 파싱"""
        parser = gitlab_mr_cli.build_parser()
        args = parser.parse_args([
            "list",
            "--project-id", "myproject",
            "--state", "opened",
            "--labels", "feature",
            "--labels", "urgent",
        ])
        assert args.labels == ["feature", "urgent"]

    def test_parser_boolean_optional_action(self):
        """BooleanOptionalAction 테스트"""
        parser = gitlab_mr_cli.build_parser()

        # --draft
        args = parser.parse_args(["create", "--project-id", "p", "--source-branch", "s", "--target-branch", "t", "--title", "t", "--draft"])
        assert args.draft is True

        # --no-draft
        args = parser.parse_args(["create", "--project-id", "p", "--source-branch", "s", "--target-branch", "t", "--title", "t", "--no-draft"])
        assert args.draft is False

    def test_parser_missing_required(self):
        """필수 인자 누락 시 에러"""
        parser = gitlab_mr_cli.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["create", "--project-id", "p"])  # source-branch, target-branch, title 누락


class TestMainFunction:
    """main 함수 테스트"""

    @patch("gitlab_mr_cli.build_parser")
    def test_main_calls_func(self, mock_build_parser):
        """main이 파싱된 함수를 호출하는지 확인"""
        mock_func = MagicMock()
        mock_args = MagicMock(func=mock_func)
        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = mock_args
        mock_build_parser.return_value = mock_parser

        gitlab_mr_cli.main()

        mock_func.assert_called_once_with(mock_args)
