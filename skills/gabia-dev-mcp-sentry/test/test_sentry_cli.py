"""gabia-dev-mcp-sentry CLI 단위 테스트.

외부 Sentry 서버 없이 실행 가능하도록 HTTP 호출을 모두 unittest.mock으로 대체한다.
실행: pytest skills/gabia-dev-mcp-sentry/test/
"""
from __future__ import annotations

import json
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# 스크립트 경로를 sys.path에 추가
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import sentry_cli  # noqa: E402  (경로 추가 후 import)


# ---------------------------------------------------------------------------
# 테스트 픽스처 헬퍼
# ---------------------------------------------------------------------------

def _make_projects(*slugs: str) -> list[dict]:
    """slug 목록으로 간단한 프로젝트 딕셔너리 목록을 생성한다."""
    return [
        {"id": str(100 + i), "slug": slug, "name": slug.replace("-", " ").title()}
        for i, slug in enumerate(slugs)
    ]


def _paginated(items: list[dict], next_results: bool = False, cursor: str = "") -> dict:
    """_http_json 응답 형식(items + pagination)으로 감싼다."""
    return {
        "items": items,
        "pagination": {
            "next": {"results": next_results, "cursor": cursor},
            "prev": {"results": False, "cursor": ""},
        },
    }


# ---------------------------------------------------------------------------
# _parse_link_header
# ---------------------------------------------------------------------------

class TestParseLinkHeader(unittest.TestCase):
    def test_next_page_parsed(self):
        header = (
            '<https://sentry.example.com/api/0/projects/?cursor=0:100:0>; rel="next"; '
            'results="true"; cursor="0:100:0",'
            '<https://sentry.example.com/api/0/projects/?cursor=0:0:1>; rel="prev"; '
            'results="false"; cursor="0:0:1"'
        )
        result = sentry_cli._parse_link_header(header)
        self.assertTrue(result["next"]["results"])
        self.assertEqual(result["next"]["cursor"], "0:100:0")
        self.assertFalse(result["prev"]["results"])

    def test_empty_header(self):
        self.assertEqual(sentry_cli._parse_link_header(""), {})


# ---------------------------------------------------------------------------
# _parse_sentry_url
# ---------------------------------------------------------------------------

class TestParseSentryUrl(unittest.TestCase):
    def test_standard_url(self):
        url = "https://sentry.gabia.io:9000/organizations/sentry-gabia/issues/29934/?project=84"
        result = sentry_cli._parse_sentry_url(url)
        self.assertIsNotNone(result)
        self.assertEqual(result["org"], "sentry-gabia")
        self.assertEqual(result["issue_id"], "29934")
        self.assertEqual(result["project"], "84")

    def test_url_without_project(self):
        url = "https://sentry.gabia.io:9000/organizations/my-org/issues/12345/"
        result = sentry_cli._parse_sentry_url(url)
        self.assertEqual(result["issue_id"], "12345")
        self.assertNotIn("project", result)

    def test_invalid_url(self):
        self.assertIsNone(sentry_cli._parse_sentry_url("https://example.com/not-sentry"))


# ---------------------------------------------------------------------------
# _resolve_project
# ---------------------------------------------------------------------------

class TestResolveProject(unittest.TestCase):
    _ORG = "test-org"

    def _patch_projects(self, projects: list[dict]):
        return patch.object(sentry_cli, "_fetch_all_projects", return_value=projects)

    def test_numeric_id_passthrough(self):
        """숫자 ID는 API 호출 없이 그대로 반환한다."""
        with patch.object(sentry_cli, "_fetch_all_projects") as mock_fetch:
            result = sentry_cli._resolve_project(self._ORG, "84")
            mock_fetch.assert_not_called()
        self.assertEqual(result, "84")

    def test_exact_slug_match(self):
        projects = _make_projects("contract-internal-api", "billing-api")
        with self._patch_projects(projects):
            result = sentry_cli._resolve_project(self._ORG, "contract-internal-api")
        self.assertEqual(result, "100")  # 첫 번째 항목의 id

    def test_exact_name_match(self):
        projects = _make_projects("billing-api")
        projects[0]["name"] = "Billing Api"
        with self._patch_projects(projects):
            result = sentry_cli._resolve_project(self._ORG, "Billing Api")
        self.assertEqual(result, "100")

    def test_partial_match_single(self):
        projects = _make_projects("contract-internal-api", "billing-api")
        with self._patch_projects(projects):
            result = sentry_cli._resolve_project(self._ORG, "billing")
        self.assertEqual(result, "101")

    def test_partial_match_multiple_raises(self):
        """부분 일치가 2건 이상이면 SystemExit과 후보 목록을 반환해야 한다."""
        projects = _make_projects("api-one", "api-two")
        with self._patch_projects(projects):
            with self.assertRaises(SystemExit) as cm:
                sentry_cli._resolve_project(self._ORG, "api")
        self.assertIn("api-one", str(cm.exception))
        self.assertIn("api-two", str(cm.exception))

    def test_duplicate_slug_raises(self):
        """같은 slug가 2건 이상이면 SystemExit이 발생해야 한다."""
        projects = [
            {"id": "1", "slug": "dup-slug", "name": "Dup A"},
            {"id": "2", "slug": "dup-slug", "name": "Dup B"},
        ]
        with self._patch_projects(projects):
            with self.assertRaises(SystemExit):
                sentry_cli._resolve_project(self._ORG, "dup-slug")

    def test_not_found_raises(self):
        projects = _make_projects("some-project")
        with self._patch_projects(projects):
            with self.assertRaises(SystemExit) as cm:
                sentry_cli._resolve_project(self._ORG, "nonexistent")
        self.assertIn("nonexistent", str(cm.exception))


# ---------------------------------------------------------------------------
# _fetch_all_projects (페이지네이션)
# ---------------------------------------------------------------------------

class TestFetchAllProjects(unittest.TestCase):
    def test_single_page(self):
        page1 = _paginated(_make_projects("proj-a", "proj-b"), next_results=False)
        with patch.object(sentry_cli, "_http_json", return_value=page1):
            result = sentry_cli._fetch_all_projects("my-org")
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["slug"], "proj-a")

    def test_multi_page(self):
        page1 = _paginated(_make_projects("proj-a"), next_results=True, cursor="0:1:0")
        page2 = _paginated(_make_projects("proj-b"), next_results=False)

        call_count = 0

        def fake_http(method, url, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return page1
            return page2

        with patch.object(sentry_cli, "_http_json", side_effect=fake_http):
            result = sentry_cli._fetch_all_projects("my-org")
        self.assertEqual(len(result), 2)
        self.assertEqual(call_count, 2)


# ---------------------------------------------------------------------------
# cmd_projects (필터 옵션)
# ---------------------------------------------------------------------------

class TestCmdProjects(unittest.TestCase):
    def _run(self, cli_args: list[str]) -> str:
        """CLI 인자를 파싱하고 cmd_projects를 실행해 stdout을 반환한다."""
        parser = sentry_cli.build_parser()
        args = parser.parse_args(cli_args)
        with patch("builtins.print") as mock_print:
            sentry_cli.cmd_projects(args)
            printed = mock_print.call_args[0][0]
        return printed

    def test_query_filter_single_page(self):
        data = _paginated(_make_projects("alpha-api", "beta-service", "alpha-beta"))
        with patch.object(sentry_cli, "_http_json", return_value=data), \
             patch.object(sentry_cli, "_org_slug", return_value="org"):
            output = self._run(["projects", "--query", "alpha"])
        items = json.loads(output)["items"]
        slugs = [p["slug"] for p in items]
        self.assertIn("alpha-api", slugs)
        self.assertIn("alpha-beta", slugs)
        self.assertNotIn("beta-service", slugs)

    def test_slug_filter(self):
        data = _paginated(_make_projects("alpha-api", "beta-service"))
        with patch.object(sentry_cli, "_http_json", return_value=data), \
             patch.object(sentry_cli, "_org_slug", return_value="org"):
            output = self._run(["projects", "--slug", "alpha-api"])
        items = json.loads(output)["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["slug"], "alpha-api")

    def test_limit(self):
        data = _paginated(_make_projects("a", "b", "c", "d", "e"))
        with patch.object(sentry_cli, "_http_json", return_value=data), \
             patch.object(sentry_cli, "_org_slug", return_value="org"):
            output = self._run(["projects", "--limit", "2"])
        items = json.loads(output)["items"]
        self.assertEqual(len(items), 2)

    def test_all_flag_calls_fetch_all(self):
        all_projects = _make_projects("x", "y")
        with patch.object(sentry_cli, "_fetch_all_projects", return_value=all_projects) as mock_fetch, \
             patch.object(sentry_cli, "_org_slug", return_value="org"), \
             patch("builtins.print"):
            sentry_cli.cmd_projects(
                sentry_cli.build_parser().parse_args(["projects", "--all"])
            )
        mock_fetch.assert_called_once()


# ---------------------------------------------------------------------------
# cmd_issue_latest
# ---------------------------------------------------------------------------

class TestCmdIssueLatest(unittest.TestCase):
    _ISSUE = {
        "id": "999",
        "title": "Test Error",
        "status": "unresolved",
        "lastSeen": "2026-04-01T12:00:00Z",
    }

    def test_returns_latest_issue(self):
        data = _paginated([self._ISSUE])
        with patch.object(sentry_cli, "_resolve_project", return_value="84"), \
             patch.object(sentry_cli, "_http_json", return_value=data), \
             patch.object(sentry_cli, "_org_slug", return_value="org"), \
             patch("builtins.print") as mock_print:
            args = sentry_cli.build_parser().parse_args(
                ["issue-latest", "--project", "contract-internal-api"]
            )
            sentry_cli.cmd_issue_latest(args)
        output = json.loads(mock_print.call_args[0][0])
        self.assertEqual(output["id"], "999")

    def test_status_any_uses_empty_query(self):
        """--status any일 때 query 파라미터가 빠져야 한다."""
        data = _paginated([self._ISSUE])
        with patch.object(sentry_cli, "_resolve_project", return_value="84"), \
             patch.object(sentry_cli, "_http_json", return_value=data) as mock_http, \
             patch.object(sentry_cli, "_org_slug", return_value="org"), \
             patch("builtins.print"):
            args = sentry_cli.build_parser().parse_args(
                ["issue-latest", "--project", "test", "--status", "any"]
            )
            sentry_cli.cmd_issue_latest(args)
        _, kwargs = mock_http.call_args
        params = kwargs.get("params", {})
        self.assertNotIn("query", params)

    def test_status_unresolved_sets_query(self):
        data = _paginated([self._ISSUE])
        with patch.object(sentry_cli, "_resolve_project", return_value="84"), \
             patch.object(sentry_cli, "_http_json", return_value=data) as mock_http, \
             patch.object(sentry_cli, "_org_slug", return_value="org"), \
             patch("builtins.print"):
            args = sentry_cli.build_parser().parse_args(
                ["issue-latest", "--project", "test", "--status", "unresolved"]
            )
            sentry_cli.cmd_issue_latest(args)
        _, kwargs = mock_http.call_args
        self.assertEqual(kwargs["params"]["query"], "is:unresolved")

    def test_with_latest_event(self):
        event = {"id": "evt-001", "message": "err"}
        data = _paginated([self._ISSUE])
        http_responses = [data, event]
        call_idx = 0

        def fake_http(method, url, params=None, body=None):
            nonlocal call_idx
            r = http_responses[call_idx]
            call_idx += 1
            return r

        with patch.object(sentry_cli, "_resolve_project", return_value="84"), \
             patch.object(sentry_cli, "_http_json", side_effect=fake_http), \
             patch.object(sentry_cli, "_org_slug", return_value="org"), \
             patch("builtins.print") as mock_print:
            args = sentry_cli.build_parser().parse_args(
                ["issue-latest", "--project", "test", "--with-latest-event"]
            )
            sentry_cli.cmd_issue_latest(args)
        output = json.loads(mock_print.call_args[0][0])
        self.assertIn("_latestEvent", output)
        self.assertEqual(output["_latestEvent"]["id"], "evt-001")

    def test_no_issues_returns_error(self):
        data = _paginated([])
        with patch.object(sentry_cli, "_resolve_project", return_value="84"), \
             patch.object(sentry_cli, "_http_json", return_value=data), \
             patch.object(sentry_cli, "_org_slug", return_value="org"), \
             patch("builtins.print") as mock_print:
            args = sentry_cli.build_parser().parse_args(
                ["issue-latest", "--project", "empty-project"]
            )
            sentry_cli.cmd_issue_latest(args)
        output = json.loads(mock_print.call_args[0][0])
        self.assertIn("error", output)


# ---------------------------------------------------------------------------
# 회귀 테스트: 기존 서브커맨드 파서 옵션
# ---------------------------------------------------------------------------

class TestRegressionParser(unittest.TestCase):
    """기존 서브커맨드가 파서에서 제거되지 않았는지 확인한다."""

    def _parse(self, *args):
        return sentry_cli.build_parser().parse_args(list(args))

    def test_projects_cursor(self):
        ns = self._parse("projects", "--cursor", "0:10:0")
        self.assertEqual(ns.cursor, "0:10:0")

    def test_issues_query_default(self):
        ns = self._parse("issues")
        self.assertEqual(ns.query, "is:unresolved")

    def test_issues_project_append(self):
        ns = self._parse("issues", "--project", "84", "--project", "85")
        self.assertEqual(ns.project, ["84", "85"])

    def test_issue_get(self):
        ns = self._parse("issue-get", "12345")
        self.assertEqual(ns.issue_id, "12345")

    def test_issue_events_full(self):
        ns = self._parse("issue-events", "12345", "--full")
        self.assertTrue(ns.full)

    def test_event_get(self):
        ns = self._parse("event-get", "12345", "latest")
        self.assertEqual(ns.event_id, "latest")

    def test_issue_update_status(self):
        ns = self._parse("issue-update", "12345", "--status", "resolved")
        self.assertEqual(ns.status, "resolved")

    def test_url_info_with_latest(self):
        ns = self._parse("url-info", "https://sentry.example.com/organizations/org/issues/1/", "--with-latest")
        self.assertTrue(ns.with_latest)

    def test_issue_latest_defaults(self):
        ns = self._parse("issue-latest", "--project", "my-project")
        self.assertEqual(ns.status, "any")
        self.assertFalse(ns.with_latest_event)


if __name__ == "__main__":
    unittest.main()
