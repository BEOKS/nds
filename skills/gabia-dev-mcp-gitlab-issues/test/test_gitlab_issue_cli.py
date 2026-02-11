#!/usr/bin/env python3
"""
GitLab Issues CLI 스크립트의 단위 테스트
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
import gitlab_issue_cli


class TestHelperFunctions:
    """헬퍼 함수들의 단위 테스트"""

    def test_env_normal(self):
        """환경변수가 정상적으로 반환되는지 확인"""
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            assert gitlab_issue_cli._env("TEST_VAR") == "test_value"

    def test_env_missing(self):
        """환경변수가 없을 때 None 반환"""
        with patch.dict(os.environ, {}, clear=True):
            assert gitlab_issue_cli._env("MISSING_VAR") is None

    def test_env_empty_string(self):
        """빈 문자열 환경변수는 None으로 처리"""
        with patch.dict(os.environ, {"EMPTY": "   "}):
            assert gitlab_issue_cli._env("EMPTY") is None

    def test_require_env_success(self):
        """필수 환경변수가 존재하면 값 반환"""
        with patch.dict(os.environ, {"REQUIRED_VAR": "value"}):
            assert gitlab_issue_cli._require_env("REQUIRED_VAR") == "value"

    def test_require_env_missing(self):
        """필수 환경변수가 없으면 SystemExit"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit) as exc_info:
                gitlab_issue_cli._require_env("REQUIRED_VAR")
            assert "Missing required env" in str(exc_info.value)

    def test_api_base_default(self):
        """기본 API base URL 반환"""
        with patch.dict(os.environ, {}, clear=True):
            assert gitlab_issue_cli._api_base() == "https://gitlab.gabia.com/api/v4"

    def test_api_base_custom(self):
        """커스텀 API base URL 사용"""
        with patch.dict(os.environ, {"GITLAB_API_URL": "https://custom.gitlab.com/api/v4/"}):
            assert gitlab_issue_cli._api_base() == "https://custom.gitlab.com/api/v4"

    def test_auth_headers(self):
        """인증 헤더 생성"""
        with patch.dict(os.environ, {"GITLAB_TOKEN": "test_token_123"}):
            headers = gitlab_issue_cli._auth_headers()
            assert headers["Authorization"] == "Bearer test_token_123"
            assert headers["PRIVATE-TOKEN"] == "test_token_123"
            assert headers["Accept"] == "application/json"

    def test_encode_project_id_simple(self):
        """단순 문자열 project ID 인코딩"""
        result = gitlab_issue_cli._encode_project_id("myproject")
        assert result == "myproject"

    def test_encode_project_id_with_slash(self):
        """슬래시를 포함한 project ID 인코딩"""
        result = gitlab_issue_cli._encode_project_id("group/project")
        assert result == "group%2Fproject"

    def test_encode_project_id_already_encoded(self):
        """이미 인코딩된 project ID 재인코딩"""
        result = gitlab_issue_cli._encode_project_id("group%2Fproject")
        assert result == "group%2Fproject"

    def test_json_parsing(self):
        """바이트 데이터를 JSON으로 파싱"""
        raw_data = b'{"key": "value", "number": 123}'
        result = gitlab_issue_cli._json(raw_data)
        assert result == {"key": "value", "number": 123}

    def test_pagination_complete_headers(self):
        """완전한 페이지네이션 헤더 파싱"""
        headers = {
            "x-page": "2",
            "x-per-page": "50",
            "x-total": "200",
            "x-total-pages": "4",
        }
        result = gitlab_issue_cli._pagination(headers)
        assert result["page"] == 2
        assert result["per_page"] == 50
        assert result["total"] == 200
        assert result["total_pages"] == 4

    def test_pagination_missing_headers(self):
        """페이지네이션 헤더가 없을 때 기본값 사용"""
        headers = {}
        result = gitlab_issue_cli._pagination(headers)
        assert result["page"] == 1
        assert result["per_page"] == 20
        assert result["total"] == 0
        assert result["total_pages"] == 0

    def test_pagination_invalid_values(self):
        """잘못된 페이지네이션 값 처리"""
        headers = {"x-page": "invalid", "x-total": "abc"}
        result = gitlab_issue_cli._pagination(headers)
        assert result["page"] == 1
        assert result["total"] == 0

    def test_read_text_argument_direct_value(self):
        """직접 값이 제공된 경우"""
        result = gitlab_issue_cli._read_text_argument("direct text", None)
        assert result == "direct text"

    def test_read_text_argument_from_file(self, tmp_path):
        """파일에서 텍스트 읽기"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("file content", encoding="utf-8")
        result = gitlab_issue_cli._read_text_argument(None, str(test_file))
        assert result == "file content"

    @patch("sys.stdin.isatty", return_value=False)
    @patch("sys.stdin.read", return_value="stdin content")
    def test_read_text_argument_from_stdin(self, mock_read, mock_isatty):
        """stdin에서 텍스트 읽기"""
        result = gitlab_issue_cli._read_text_argument(None, None)
        assert result == "stdin content"

    @patch("sys.stdin.isatty", return_value=True)
    def test_read_text_argument_none(self, mock_isatty):
        """모든 입력이 없을 때 None 반환"""
        result = gitlab_issue_cli._read_text_argument(None, None)
        assert result is None


class TestHttpFunction:
    """HTTP 요청 함수 테스트"""

    @patch("gitlab_issue_cli.urllib.request.urlopen")
    @patch("gitlab_issue_cli._auth_headers")
    def test_http_get_success(self, mock_auth, mock_urlopen):
        """GET 요청 성공"""
        mock_auth.return_value = {"Authorization": "Bearer token"}
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status": "success"}'
        mock_response.headers.items.return_value = [
            ("X-Page", "1"),
            ("X-Total", "10"),
        ]
        mock_urlopen.return_value.__enter__.return_value = mock_response

        raw, headers = gitlab_issue_cli._http("GET", "https://gitlab.com/api/v4/issues")
        assert raw == b'{"status": "success"}'
        assert headers["x-page"] == "1"

    @patch("gitlab_issue_cli.urllib.request.urlopen")
    @patch("gitlab_issue_cli._auth_headers")
    def test_http_post_with_body(self, mock_auth, mock_urlopen):
        """POST 요청에 body 포함"""
        mock_auth.return_value = {"Authorization": "Bearer token"}
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"id": 123}'
        mock_response.headers.items.return_value = []
        mock_urlopen.return_value.__enter__.return_value = mock_response

        payload = {"title": "New Issue"}
        raw, _ = gitlab_issue_cli._http("POST", "https://gitlab.com/api/v4/issues", body=payload)

        request = mock_urlopen.call_args[0][0]
        assert request.method == "POST"
        assert request.data == json.dumps(payload).encode("utf-8")

    @patch("gitlab_issue_cli.urllib.request.urlopen")
    @patch("gitlab_issue_cli._auth_headers")
    def test_http_with_query_params(self, mock_auth, mock_urlopen):
        """쿼리 파라미터 추가"""
        mock_auth.return_value = {"Authorization": "Bearer token"}
        mock_response = MagicMock()
        mock_response.read.return_value = b'[]'
        mock_response.headers.items.return_value = []
        mock_urlopen.return_value.__enter__.return_value = mock_response

        params = [("state", "opened"), ("labels", "bug")]
        gitlab_issue_cli._http("GET", "https://gitlab.com/api/v4/issues", params=params)

        request = mock_urlopen.call_args[0][0]
        assert "state=opened" in request.full_url
        assert "labels=bug" in request.full_url

    @patch("gitlab_issue_cli.urllib.request.urlopen")
    @patch("gitlab_issue_cli._auth_headers")
    def test_http_error_404(self, mock_auth, mock_urlopen):
        """404 에러 처리"""
        mock_auth.return_value = {"Authorization": "Bearer token"}
        error_response = MagicMock()
        error_response.read.return_value = b"Not Found"
        mock_urlopen.side_effect = gitlab_issue_cli.urllib.error.HTTPError(
            "url", 404, "Not Found", {}, error_response
        )

        with pytest.raises(SystemExit) as exc_info:
            gitlab_issue_cli._http("GET", "https://gitlab.com/api/v4/issues/999")
        assert "404" in str(exc_info.value)

    @patch("gitlab_issue_cli.urllib.request.urlopen")
    @patch("gitlab_issue_cli._auth_headers")
    def test_http_network_error(self, mock_auth, mock_urlopen):
        """네트워크 에러 처리"""
        mock_auth.return_value = {"Authorization": "Bearer token"}
        mock_urlopen.side_effect = gitlab_issue_cli.urllib.error.URLError("Connection failed")

        with pytest.raises(SystemExit) as exc_info:
            gitlab_issue_cli._http("GET", "https://gitlab.com/api/v4/issues")
        assert "Network error" in str(exc_info.value)


class TestCmdCreate:
    """create 명령어 테스트"""

    @patch("sys.stdin.isatty", return_value=True)
    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_create_minimal(self, mock_print, mock_http, mock_isatty):
        """최소 필수 정보로 이슈 생성"""
        mock_http.return_value = (b'{"id": 1, "title": "Test Issue"}', {})

        args = MagicMock(
            project_id="myproject",
            title="Test Issue",
            description=None,
            description_file=None,
            assignee_ids=None,
            milestone_id=None,
            labels=None,
            issue_type=None,
        )
        gitlab_issue_cli.cmd_create(args)

        call_args = mock_http.call_args
        assert "projects/myproject/issues" in call_args[0][1]
        assert call_args[1]["body"]["title"] == "Test Issue"
        mock_print.assert_called_once()

    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_create_full_options(self, mock_print, mock_http):
        """모든 옵션을 포함하여 이슈 생성"""
        mock_http.return_value = (b'{"id": 1}', {})

        args = MagicMock(
            project_id="group/project",
            title="Full Issue",
            description="Description text",
            description_file=None,
            assignee_ids=[10, 20],
            milestone_id=5,
            labels=["bug", "critical"],
            issue_type="incident",
        )
        gitlab_issue_cli.cmd_create(args)

        payload = mock_http.call_args[1]["body"]
        assert payload["title"] == "Full Issue"
        assert payload["description"] == "Description text"
        assert payload["assignee_ids"] == [10, 20]
        assert payload["milestone_id"] == 5
        assert payload["labels"] == "bug,critical"
        assert payload["issue_type"] == "incident"


class TestCmdList:
    """list 명령어 테스트"""

    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_list_project_scoped(self, mock_print, mock_http):
        """프로젝트 범위로 이슈 목록 조회"""
        mock_http.return_value = (b'[{"id": 1}, {"id": 2}]', {"x-total": "2"})

        args = MagicMock(
            project_id="myproject",
            assignee_id=None,
            assignee_username=None,
            author_id=None,
            author_username=None,
            confidential=None,
            created_after=None,
            created_before=None,
            due_date=None,
            labels=None,
            milestone=None,
            issue_type=None,
            iteration_id=None,
            scope=None,
            search=None,
            state=None,
            updated_after=None,
            updated_before=None,
            weight=None,
            my_reaction_emoji=None,
            order_by=None,
            sort=None,
            with_labels_details=None,
            page=None,
            per_page=None,
            param=None,
        )
        gitlab_issue_cli.cmd_list(args)

        assert "projects/myproject/issues" in mock_http.call_args[0][1]

    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_list_global(self, mock_print, mock_http):
        """전역 범위로 이슈 목록 조회"""
        mock_http.return_value = (b'[]', {})

        args = MagicMock(
            project_id=None,
            assignee_id=10,
            state="opened",
            labels=["bug"],
            page=2,
            per_page=50,
            assignee_username=None,
            author_id=None,
            author_username=None,
            confidential=None,
            created_after=None,
            created_before=None,
            due_date=None,
            milestone=None,
            issue_type=None,
            iteration_id=None,
            scope=None,
            search=None,
            updated_after=None,
            updated_before=None,
            weight=None,
            my_reaction_emoji=None,
            order_by=None,
            sort=None,
            with_labels_details=None,
            param=None,
        )
        gitlab_issue_cli.cmd_list(args)

        url = mock_http.call_args[0][1]
        params = mock_http.call_args[1]["params"]
        assert "/issues" in url
        assert ("assignee_id", "10") in params
        assert ("state", "opened") in params
        assert ("page", "2") in params

    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_list_custom_params(self, mock_print, mock_http):
        """커스텀 파라미터 추가"""
        mock_http.return_value = (b'[]', {})

        args = MagicMock(
            project_id="myproject",
            param=["custom_field=value", "another=test"],
            **{k: None for k in [
                "assignee_id", "assignee_username", "author_id", "author_username",
                "confidential", "created_after", "created_before", "due_date",
                "labels", "milestone", "issue_type", "iteration_id", "scope",
                "search", "state", "updated_after", "updated_before", "weight",
                "my_reaction_emoji", "order_by", "sort", "with_labels_details",
                "page", "per_page"
            ]}
        )
        gitlab_issue_cli.cmd_list(args)

        params = mock_http.call_args[1]["params"]
        assert ("custom_field", "value") in params
        assert ("another", "test") in params


class TestCmdGet:
    """get 명령어 테스트"""

    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_get_success(self, mock_print, mock_http):
        """이슈 조회 성공"""
        mock_http.return_value = (b'{"id": 123, "title": "Issue Title"}', {})

        args = MagicMock(project_id="myproject", issue_iid="45")
        gitlab_issue_cli.cmd_get(args)

        assert "projects/myproject/issues/45" in mock_http.call_args[0][1]
        mock_print.assert_called_once()


class TestCmdUpdate:
    """update 명령어 테스트"""

    @patch("sys.stdin.isatty", return_value=True)
    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_update_title(self, mock_print, mock_http, mock_isatty):
        """이슈 제목만 업데이트"""
        mock_http.return_value = (b'{"id": 1}', {})

        args = MagicMock(
            project_id="myproject",
            issue_iid="10",
            title="Updated Title",
            description=None,
            description_file=None,
            assignee_ids=None,
            confidential=None,
            discussion_locked=None,
            due_date=None,
            labels=None,
            milestone_id=None,
            state_event=None,
            weight=None,
            issue_type=None,
        )
        gitlab_issue_cli.cmd_update(args)

        payload = mock_http.call_args[1]["body"]
        assert payload["title"] == "Updated Title"
        assert "description" not in payload

    @patch("sys.stdin.isatty", return_value=True)
    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_update_state_event(self, mock_print, mock_http, mock_isatty):
        """이슈 상태 변경"""
        mock_http.return_value = (b'{"id": 1}', {})

        args = MagicMock(
            project_id="myproject",
            issue_iid="10",
            title=None,
            state_event="close",
            description=None,
            description_file=None,
            assignee_ids=None,
            confidential=None,
            discussion_locked=None,
            due_date=None,
            labels=None,
            milestone_id=None,
            weight=None,
            issue_type=None,
        )
        gitlab_issue_cli.cmd_update(args)

        payload = mock_http.call_args[1]["body"]
        assert payload["state_event"] == "close"


class TestCmdDelete:
    """delete 명령어 테스트"""

    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_delete_success(self, mock_print, mock_http):
        """이슈 삭제 성공"""
        mock_http.return_value = (b"", {})

        args = MagicMock(project_id="myproject", issue_iid="15")
        gitlab_issue_cli.cmd_delete(args)

        call_args = mock_http.call_args
        assert call_args[0][0] == "DELETE"
        assert "projects/myproject/issues/15" in call_args[0][1]
        mock_print.assert_called_once()


class TestCmdDiscussions:
    """discussions 명령어 테스트"""

    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_discussions_list(self, mock_print, mock_http):
        """토론 목록 조회"""
        mock_http.return_value = (b'[{"id": "disc1"}]', {"x-total": "1"})

        args = MagicMock(
            project_id="myproject",
            issue_iid="20",
            page=None,
            per_page=None,
        )
        gitlab_issue_cli.cmd_discussions(args)

        assert "projects/myproject/issues/20/discussions" in mock_http.call_args[0][1]


class TestCmdNotes:
    """create-note와 update-note 명령어 테스트"""

    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_create_note(self, mock_print, mock_http):
        """토론에 노트 추가"""
        mock_http.return_value = (b'{"id": "note1"}', {})

        args = MagicMock(
            project_id="myproject",
            issue_iid="25",
            discussion_id="disc1",
            body="This is a note",
            created_at=None,
        )
        gitlab_issue_cli.cmd_create_note(args)

        payload = mock_http.call_args[1]["body"]
        assert payload["body"] == "This is a note"
        assert "discussions/disc1/notes" in mock_http.call_args[0][1]

    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_update_note(self, mock_print, mock_http):
        """기존 노트 수정"""
        mock_http.return_value = (b'{"id": "note1"}', {})

        args = MagicMock(
            project_id="myproject",
            issue_iid="25",
            discussion_id="disc1",
            note_id="note1",
            body="Updated note",
        )
        gitlab_issue_cli.cmd_update_note(args)

        payload = mock_http.call_args[1]["body"]
        assert payload["body"] == "Updated note"
        assert "notes/note1" in mock_http.call_args[0][1]


class TestCmdLinks:
    """이슈 링크 관련 명령어 테스트"""

    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_list_links(self, mock_print, mock_http):
        """이슈 링크 목록 조회"""
        mock_http.return_value = (b'[{"id": 1}]', {})

        args = MagicMock(project_id="myproject", issue_iid="30")
        gitlab_issue_cli.cmd_list_links(args)

        assert "projects/myproject/issues/30/links" in mock_http.call_args[0][1]

    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_get_link(self, mock_print, mock_http):
        """특정 이슈 링크 조회"""
        mock_http.return_value = (b'{"id": 1}', {})

        args = MagicMock(
            project_id="myproject",
            issue_iid="30",
            issue_link_id="100",
        )
        gitlab_issue_cli.cmd_get_link(args)

        assert "issues/30/links/100" in mock_http.call_args[0][1]

    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_create_link(self, mock_print, mock_http):
        """이슈 링크 생성"""
        mock_http.return_value = (b'{"id": 1}', {})

        args = MagicMock(
            project_id="myproject",
            issue_iid="30",
            target_project_id="otherproject",
            target_issue_iid="40",
            link_type="blocks",
        )
        gitlab_issue_cli.cmd_create_link(args)

        payload = mock_http.call_args[1]["body"]
        assert payload["target_project_id"] == "otherproject"
        assert payload["target_issue_iid"] == "40"
        assert payload["link_type"] == "blocks"

    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_delete_link(self, mock_print, mock_http):
        """이슈 링크 삭제"""
        mock_http.return_value = (b"", {})

        args = MagicMock(
            project_id="myproject",
            issue_iid="30",
            issue_link_id="100",
        )
        gitlab_issue_cli.cmd_delete_link(args)

        assert mock_http.call_args[0][0] == "DELETE"
        assert "issues/30/links/100" in mock_http.call_args[0][1]


class TestCmdMilestones:
    """마일스톤 명령어 테스트"""

    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_list_milestones_minimal(self, mock_print, mock_http):
        """최소 옵션으로 마일스톤 목록 조회"""
        mock_http.return_value = (b'[{"id": 1, "title": "v1.0"}]', {"x-total": "1"})

        args = MagicMock(
            project_id="myproject",
            iids=None,
            state=None,
            title=None,
            search=None,
            include_parent_milestones=None,
            page=None,
            per_page=None,
        )
        gitlab_issue_cli.cmd_list_milestones(args)

        assert "projects/myproject/milestones" in mock_http.call_args[0][1]
        mock_print.assert_called_once()

    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_list_milestones_with_filters(self, mock_print, mock_http):
        """필터 옵션으로 마일스톤 목록 조회"""
        mock_http.return_value = (b'[{"id": 1}]', {"x-total": "1"})

        args = MagicMock(
            project_id="group/project",
            iids=[1, 2],
            state="active",
            title=None,
            search="release",
            include_parent_milestones=True,
            page=1,
            per_page=10,
        )
        gitlab_issue_cli.cmd_list_milestones(args)

        params = mock_http.call_args[1]["params"]
        assert ("iids[]", "1") in params
        assert ("iids[]", "2") in params
        assert ("state", "active") in params
        assert ("search", "release") in params
        assert ("include_parent_milestones", "true") in params
        assert ("page", "1") in params
        assert ("per_page", "10") in params

    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_get_milestone(self, mock_print, mock_http):
        """마일스톤 상세 조회"""
        mock_http.return_value = (b'{"id": 5, "title": "v2.0", "state": "active"}', {})

        args = MagicMock(project_id="myproject", milestone_id="5")
        gitlab_issue_cli.cmd_get_milestone(args)

        assert "projects/myproject/milestones/5" in mock_http.call_args[0][1]
        mock_print.assert_called_once()

    @patch("gitlab_issue_cli._http")
    @patch("builtins.print")
    def test_cmd_list_milestones_pagination(self, mock_print, mock_http):
        """마일스톤 목록 조회 시 페이지네이션 정보 포함"""
        mock_http.return_value = (
            b'[{"id": 1}]',
            {"x-page": "1", "x-per-page": "20", "x-total": "50", "x-total-pages": "3"},
        )

        args = MagicMock(
            project_id="myproject",
            iids=None,
            state=None,
            title=None,
            search=None,
            include_parent_milestones=None,
            page=None,
            per_page=None,
        )
        gitlab_issue_cli.cmd_list_milestones(args)

        output = json.loads(mock_print.call_args[0][0])
        assert "items" in output
        assert "pagination" in output
        assert output["pagination"]["total"] == 50


class TestBuildParser:
    """argparse 파서 테스트"""

    def test_parser_create_command(self):
        """create 명령어 파싱"""
        parser = gitlab_issue_cli.build_parser()
        args = parser.parse_args([
            "create",
            "--project-id", "myproject",
            "--title", "Test Issue",
        ])
        assert args.cmd == "create"
        assert args.project_id == "myproject"
        assert args.title == "Test Issue"

    def test_parser_list_command(self):
        """list 명령어 파싱"""
        parser = gitlab_issue_cli.build_parser()
        args = parser.parse_args([
            "list",
            "--state", "opened",
            "--labels", "bug",
            "--labels", "critical",
        ])
        assert args.cmd == "list"
        assert args.state == "opened"
        assert args.labels == ["bug", "critical"]

    def test_parser_boolean_optional_action(self):
        """BooleanOptionalAction 파싱"""
        parser = gitlab_issue_cli.build_parser()

        # --confidential
        args = parser.parse_args(["list", "--confidential"])
        assert args.confidential is True

        # --no-confidential
        args = parser.parse_args(["list", "--no-confidential"])
        assert args.confidential is False

        # 기본값
        args = parser.parse_args(["list"])
        assert args.confidential is None

    def test_parser_missing_required(self):
        """필수 인자 누락 시 에러"""
        parser = gitlab_issue_cli.build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["create"])  # project-id와 title 누락


class TestMainFunction:
    """main 함수 테스트"""

    @patch("gitlab_issue_cli.build_parser")
    def test_main_calls_func(self, mock_build_parser):
        """main이 파싱된 함수를 호출하는지 확인"""
        mock_func = MagicMock()
        mock_args = MagicMock(func=mock_func)
        mock_parser = MagicMock()
        mock_parser.parse_args.return_value = mock_args
        mock_build_parser.return_value = mock_parser

        gitlab_issue_cli.main()

        mock_func.assert_called_once_with(mock_args)
