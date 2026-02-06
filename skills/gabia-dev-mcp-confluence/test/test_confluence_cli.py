#!/usr/bin/env python3
"""confluence_cli.py 단위 테스트"""
import json
import os
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

# 테스트 대상 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import confluence_cli


class TestEnvFunctions(unittest.TestCase):
    """환경변수 관련 함수 테스트"""

    @patch.dict(os.environ, {"TEST_VAR": "value"})
    def test_env_returns_value(self):
        """정상 케이스: 환경변수가 존재하는 경우"""
        result = confluence_cli._env("TEST_VAR")
        self.assertEqual(result, "value")

    @patch.dict(os.environ, {}, clear=True)
    def test_env_returns_none_when_missing(self):
        """정상 케이스: 환경변수가 없는 경우"""
        result = confluence_cli._env("MISSING_VAR")
        self.assertIsNone(result)

    @patch.dict(os.environ, {"EMPTY_VAR": "  "})
    def test_env_strips_whitespace(self):
        """정상 케이스: 공백만 있는 경우 None 반환"""
        result = confluence_cli._env("EMPTY_VAR")
        self.assertIsNone(result)

    @patch.dict(os.environ, {"REQUIRED_VAR": "value"})
    def test_require_env_returns_value(self):
        """정상 케이스: 필수 환경변수가 존재하는 경우"""
        result = confluence_cli._require_env("REQUIRED_VAR")
        self.assertEqual(result, "value")

    @patch.dict(os.environ, {}, clear=True)
    def test_require_env_raises_on_missing(self):
        """에러 케이스: 필수 환경변수가 없는 경우 SystemExit 발생"""
        with self.assertRaises(SystemExit) as cm:
            confluence_cli._require_env("MISSING_VAR")
        self.assertIn("Missing required env", str(cm.exception))


class TestBuildAuthHeader(unittest.TestCase):
    """인증 헤더 생성 함수 테스트"""

    @patch.dict(os.environ, {"ATLASSIAN_OAUTH_ACCESS_TOKEN": "oauth_token"})
    def test_oauth_token_priority(self):
        """정상 케이스: OAuth 토큰이 우선순위 1순위"""
        result = confluence_cli._build_auth_header()
        self.assertEqual(result, "Bearer oauth_token")

    @patch.dict(os.environ, {
        "CONFLUENCE_USERNAME": "user@example.com",
        "CONFLUENCE_API_TOKEN": "api_token"
    }, clear=True)
    def test_basic_auth_with_confluence_vars(self):
        """정상 케이스: CONFLUENCE_* 환경변수로 Basic Auth 생성"""
        result = confluence_cli._build_auth_header()
        self.assertTrue(result.startswith("Basic "))

    @patch.dict(os.environ, {
        "ATLASSIAN_EMAIL": "user@example.com",
        "ATLASSIAN_API_TOKEN": "api_token"
    }, clear=True)
    def test_basic_auth_with_atlassian_vars(self):
        """정상 케이스: ATLASSIAN_* 환경변수로 Basic Auth 생성"""
        result = confluence_cli._build_auth_header()
        self.assertTrue(result.startswith("Basic "))

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_auth_raises_error(self):
        """에러 케이스: 인증 정보가 없는 경우 SystemExit 발생"""
        with self.assertRaises(SystemExit) as cm:
            confluence_cli._build_auth_header()
        self.assertIn("Missing Confluence auth", str(cm.exception))


class TestWrapSimpleQueryToCQL(unittest.TestCase):
    """CQL 쿼리 변환 함수 테스트"""

    def test_simple_text_wraps_to_sitesearch(self):
        """정상 케이스: 단순 텍스트를 siteSearch로 변환"""
        result = confluence_cli.wrap_simple_query_to_cql("hello world")
        self.assertEqual(result, 'siteSearch ~ "hello world"')

    def test_cql_query_returns_unchanged(self):
        """정상 케이스: CQL 쿼리는 그대로 반환"""
        cql = 'space = "DEV" AND type = "page"'
        result = confluence_cli.wrap_simple_query_to_cql(cql)
        self.assertEqual(result, cql)

    def test_escapes_quotes_in_simple_text(self):
        """정상 케이스: 따옴표 이스케이프 처리"""
        result = confluence_cli.wrap_simple_query_to_cql('test "quoted"')
        self.assertEqual(result, 'siteSearch ~ "test \\"quoted\\""')

    def test_detects_cql_operators(self):
        """정상 케이스: CQL 연산자 감지"""
        queries = [
            "title = test",
            "content ~ keyword",
            "created > 2024-01-01",
            "label < value",
            "space = DEV AND type = page",
            "space = DEV OR type = blogpost",
            "creator = currentUser()"
        ]
        for query in queries:
            result = confluence_cli.wrap_simple_query_to_cql(query)
            self.assertEqual(result, query)


class TestApplySpacesFilter(unittest.TestCase):
    """스페이스 필터 적용 함수 테스트"""

    def test_no_filter_returns_original(self):
        """정상 케이스: 필터가 없으면 원본 반환"""
        cql = 'siteSearch ~ "test"'
        result = confluence_cli.apply_spaces_filter(cql, None)
        self.assertEqual(result, cql)

    def test_single_space_filter(self):
        """정상 케이스: 단일 스페이스 필터 적용"""
        cql = 'siteSearch ~ "test"'
        result = confluence_cli.apply_spaces_filter(cql, "DEV")
        self.assertEqual(result, '(space = "DEV") AND (siteSearch ~ "test")')

    def test_multiple_spaces_filter(self):
        """정상 케이스: 여러 스페이스 필터 적용"""
        cql = 'siteSearch ~ "test"'
        result = confluence_cli.apply_spaces_filter(cql, "DEV, PROD, TEST")
        expected = '(space = "DEV" OR space = "PROD" OR space = "TEST") AND (siteSearch ~ "test")'
        self.assertEqual(result, expected)

    def test_empty_string_filter_returns_original(self):
        """정상 케이스: 빈 문자열 필터는 무시"""
        cql = 'siteSearch ~ "test"'
        result = confluence_cli.apply_spaces_filter(cql, "")
        self.assertEqual(result, cql)


class TestToSimpleResults(unittest.TestCase):
    """검색 결과 단순화 함수 테스트"""

    def test_simplifies_search_results(self):
        """정상 케이스: 검색 결과를 단순화"""
        payload = {
            "results": [
                {
                    "id": "123",
                    "title": "Test Page",
                    "space": {"key": "DEV"},
                    "excerpt": "Test excerpt"
                }
            ]
        }
        base_url = "https://confluence.example.com"
        result = confluence_cli.to_simple_results(payload, base_url)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "123")
        self.assertEqual(result[0]["title"], "Test Page")
        self.assertEqual(result[0]["spaceKey"], "DEV")
        self.assertEqual(result[0]["url"], "https://confluence.example.com/spaces/DEV/pages/123")

    def test_handles_nested_content_structure(self):
        """정상 케이스: 중첩된 content 구조 처리"""
        payload = {
            "results": [
                {
                    "content": {
                        "id": "456",
                        "title": "Nested Page",
                        "space": {"key": "PROD"}
                    }
                }
            ]
        }
        result = confluence_cli.to_simple_results(payload, None)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "456")
        self.assertEqual(result[0]["title"], "Nested Page")

    def test_empty_results(self):
        """정상 케이스: 빈 결과 처리"""
        payload = {"results": []}
        result = confluence_cli.to_simple_results(payload, None)
        self.assertEqual(result, [])


class TestMarkdownToStorage(unittest.TestCase):
    """마크다운 → Confluence Storage 변환 함수 테스트"""

    def test_converts_headings(self):
        """정상 케이스: 제목 변환"""
        markdown = "# H1\n## H2\n### H3"
        result = confluence_cli.markdown_to_storage(markdown)
        self.assertIn("<h1>H1</h1>", result)
        self.assertIn("<h2>H2</h2>", result)
        self.assertIn("<h3>H3</h3>", result)

    def test_converts_bold_text(self):
        """정상 케이스: 볼드 텍스트 변환"""
        markdown = "**bold** and __also bold__"
        result = confluence_cli.markdown_to_storage(markdown)
        self.assertEqual(result.count("<strong>"), 2)
        self.assertEqual(result.count("</strong>"), 2)

    def test_converts_italic_text(self):
        """정상 케이스: 이탤릭 텍스트 변환"""
        markdown = "*italic* and _also italic_"
        result = confluence_cli.markdown_to_storage(markdown)
        self.assertEqual(result.count("<em>"), 2)

    def test_converts_links(self):
        """정상 케이스: 링크 변환"""
        markdown = "[Example](https://example.com)"
        result = confluence_cli.markdown_to_storage(markdown)
        self.assertIn('<a href="https://example.com">Example</a>', result)

    def test_converts_code_inline(self):
        """정상 케이스: 인라인 코드 변환"""
        markdown = "This is `code` inline"
        result = confluence_cli.markdown_to_storage(markdown)
        self.assertIn("<code>code</code>", result)

    def test_converts_code_block(self):
        """정상 케이스: 코드 블록 변환"""
        markdown = "```\ncode block\n```"
        result = confluence_cli.markdown_to_storage(markdown)
        self.assertIn("<pre><code>", result)
        self.assertIn("</code></pre>", result)

    def test_converts_unordered_list(self):
        """정상 케이스: 순서 없는 리스트 변환"""
        markdown = "- Item 1\n- Item 2"
        result = confluence_cli.markdown_to_storage(markdown)
        self.assertIn("<ul>", result)
        self.assertIn("<li>Item 1</li>", result)
        self.assertIn("</ul>", result)

    def test_converts_ordered_list(self):
        """정상 케이스: 순서 있는 리스트 변환"""
        markdown = "1. First\n2. Second"
        result = confluence_cli.markdown_to_storage(markdown)
        self.assertIn("<ol>", result)
        self.assertIn("<li>First</li>", result)
        self.assertIn("</ol>", result)

    def test_converts_table(self):
        """정상 케이스: 테이블 변환"""
        markdown = "| Col1 | Col2 |\n|------|------|\n| A | B |"
        result = confluence_cli.markdown_to_storage(markdown)
        self.assertIn("<table>", result)
        self.assertIn("<thead>", result)
        self.assertIn("<tbody>", result)
        self.assertIn("<th>Col1</th>", result)
        self.assertIn("<td>A</td>", result)

    def test_converts_blockquote(self):
        """정상 케이스: 인용구 변환"""
        markdown = "> This is a quote"
        result = confluence_cli.markdown_to_storage(markdown)
        self.assertIn("<blockquote>", result)
        self.assertIn("</blockquote>", result)

    def test_converts_horizontal_rule(self):
        """정상 케이스: 수평선 변환"""
        markdown = "---"
        result = confluence_cli.markdown_to_storage(markdown)
        self.assertIn("<hr/>", result)

    def test_escapes_html_entities(self):
        """정상 케이스: HTML 엔티티 이스케이프"""
        markdown = "Test <tag> & special"
        result = confluence_cli.markdown_to_storage(markdown)
        self.assertIn("&lt;tag&gt;", result)
        self.assertIn("&amp;", result)


class TestHtmlToMarkdownLight(unittest.TestCase):
    """HTML → 마크다운 변환 함수 테스트"""

    def test_converts_headings(self):
        """정상 케이스: HTML 제목을 마크다운으로 변환"""
        html = "<h1>Title</h1><h2>Subtitle</h2>"
        result = confluence_cli.html_to_markdown_light(html)
        self.assertIn("# Title", result)
        self.assertIn("## Subtitle", result)

    def test_converts_bold(self):
        """정상 케이스: 볼드 텍스트 변환"""
        html = "<strong>bold</strong> and <b>also bold</b>"
        result = confluence_cli.html_to_markdown_light(html)
        self.assertEqual(result.count("**"), 4)

    def test_converts_italic(self):
        """정상 케이스: 이탤릭 텍스트 변환"""
        html = "<em>italic</em> and <i>also italic</i>"
        result = confluence_cli.html_to_markdown_light(html)
        self.assertEqual(result.count("*"), 4)

    def test_converts_links(self):
        """정상 케이스: 링크 변환"""
        html = '<a href="https://example.com">Link</a>'
        result = confluence_cli.html_to_markdown_light(html)
        self.assertIn("[Link](https://example.com)", result)

    def test_converts_lists(self):
        """정상 케이스: 리스트 변환"""
        html = "<ul><li>Item 1</li><li>Item 2</li></ul>"
        result = confluence_cli.html_to_markdown_light(html)
        self.assertIn("- Item 1", result)
        self.assertIn("- Item 2", result)

    def test_converts_code(self):
        """정상 케이스: 코드 변환"""
        html = "<code>inline</code> and <pre><code>block</code></pre>"
        result = confluence_cli.html_to_markdown_light(html)
        self.assertIn("`inline`", result)
        self.assertIn("```", result)

    def test_strips_remaining_tags(self):
        """정상 케이스: 나머지 HTML 태그 제거"""
        html = "<div><span>Text</span></div>"
        result = confluence_cli.html_to_markdown_light(html)
        self.assertEqual(result.strip(), "Text")


class TestReadTextArgument(unittest.TestCase):
    """텍스트 인자 읽기 함수 테스트"""

    def test_returns_direct_value(self):
        """정상 케이스: 직접 값이 제공된 경우"""
        result = confluence_cli._read_text_argument("direct value", None)
        self.assertEqual(result, "direct value")

    @patch("builtins.open", mock_open(read_data="file content"))
    def test_reads_from_file(self):
        """정상 케이스: 파일에서 읽기"""
        result = confluence_cli._read_text_argument(None, "/path/to/file.txt")
        self.assertEqual(result, "file content")

    @patch("sys.stdin")
    def test_reads_from_stdin(self, mock_stdin):
        """정상 케이스: stdin에서 읽기"""
        mock_stdin.isatty.return_value = False
        mock_stdin.read.return_value = "stdin content"
        result = confluence_cli._read_text_argument(None, None)
        self.assertEqual(result, "stdin content")

    @patch("sys.stdin")
    def test_raises_when_no_input(self, mock_stdin):
        """에러 케이스: 입력이 없는 경우"""
        mock_stdin.isatty.return_value = True
        with self.assertRaises(SystemExit) as cm:
            confluence_cli._read_text_argument(None, None)
        self.assertIn("Provide --content", str(cm.exception))


class TestExtractBody(unittest.TestCase):
    """페이지 본문 추출 함수 테스트"""

    def test_extract_storage_format(self):
        """정상 케이스: storage 포맷 추출"""
        page_obj = {
            "body": {
                "storage": {"value": "<p>Storage content</p>"},
                "export_view": {"value": "<p>Export view content</p>"}
            }
        }
        fmt, body = confluence_cli._extract_body(page_obj, output_format="storage")
        self.assertEqual(fmt, "storage")
        self.assertEqual(body, "<p>Storage content</p>")

    def test_extract_html_format(self):
        """정상 케이스: html 포맷 추출 (export_view 우선)"""
        page_obj = {
            "body": {
                "export_view": {"value": "<p>Export view</p>"},
                "storage": {"value": "<p>Storage</p>"}
            }
        }
        fmt, body = confluence_cli._extract_body(page_obj, output_format="html")
        self.assertEqual(fmt, "html")
        self.assertEqual(body, "<p>Export view</p>")

    def test_extract_markdown_format(self):
        """정상 케이스: markdown 포맷 추출"""
        page_obj = {
            "body": {
                "export_view": {"value": "<h1>Title</h1><p>Content</p>"}
            }
        }
        fmt, body = confluence_cli._extract_body(page_obj, output_format="markdown")
        self.assertEqual(fmt, "markdown")
        self.assertIn("# Title", body)

    def test_fallback_to_storage_when_export_view_missing(self):
        """정상 케이스: export_view가 없으면 storage로 폴백"""
        page_obj = {
            "body": {
                "storage": {"value": "<p>Storage only</p>"}
            }
        }
        fmt, body = confluence_cli._extract_body(page_obj, output_format="html")
        self.assertEqual(body, "<p>Storage only</p>")

    def test_empty_body(self):
        """정상 케이스: 빈 본문 처리"""
        page_obj = {"body": {}}
        fmt, body = confluence_cli._extract_body(page_obj, output_format="html")
        self.assertEqual(body, "")


class TestNormalizeBody(unittest.TestCase):
    """본문 정규화 함수 테스트"""

    def test_storage_format_passthrough(self):
        """정상 케이스: storage 포맷은 그대로 반환"""
        content = "<p>Storage content</p>"
        result, representation = confluence_cli._normalize_body(content, "storage")
        self.assertEqual(result, content)
        self.assertEqual(representation, "storage")

    def test_wiki_format_passthrough(self):
        """정상 케이스: wiki 포맷은 그대로 반환"""
        content = "h1. Wiki heading"
        result, representation = confluence_cli._normalize_body(content, "wiki")
        self.assertEqual(result, content)
        self.assertEqual(representation, "wiki")

    def test_markdown_converts_to_storage(self):
        """정상 케이스: markdown은 storage로 변환"""
        content = "# Heading\n\n**Bold text**"
        result, representation = confluence_cli._normalize_body(content, "markdown")
        self.assertIn("<h1>", result)
        self.assertEqual(representation, "storage")

    def test_default_is_markdown(self):
        """정상 케이스: 기본값은 markdown"""
        content = "# Heading"
        result, representation = confluence_cli._normalize_body(content, None)
        self.assertIn("<h1>", result)
        self.assertEqual(representation, "storage")


class TestHttpJson(unittest.TestCase):
    """HTTP JSON 요청 함수 테스트"""

    @patch("urllib.request.urlopen")
    @patch("confluence_cli._build_auth_header")
    def test_get_request(self, mock_auth, mock_urlopen):
        """정상 케이스: GET 요청"""
        mock_auth.return_value = "Bearer token"
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"result": "success"}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = confluence_cli._http_json("GET", "https://api.example.com/test")

        self.assertEqual(result, {"result": "success"})

    @patch("urllib.request.urlopen")
    @patch("confluence_cli._build_auth_header")
    def test_post_request_with_body(self, mock_auth, mock_urlopen):
        """정상 케이스: POST 요청 with body"""
        mock_auth.return_value = "Bearer token"
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"created": true}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        result = confluence_cli._http_json(
            "POST",
            "https://api.example.com/create",
            body={"title": "Test"}
        )

        self.assertEqual(result, {"created": True})

    @patch("urllib.request.urlopen")
    @patch("confluence_cli._build_auth_header")
    def test_request_with_params(self, mock_auth, mock_urlopen):
        """정상 케이스: 쿼리 파라미터 포함 요청"""
        mock_auth.return_value = "Bearer token"
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"data": []}'
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        confluence_cli._http_json(
            "GET",
            "https://api.example.com/search",
            params={"q": "test", "limit": "10"}
        )

        # URL에 파라미터가 추가되었는지 확인
        call_args = mock_urlopen.call_args[0][0]
        self.assertIn("q=test", call_args.full_url)
        self.assertIn("limit=10", call_args.full_url)

    @patch("urllib.request.urlopen")
    @patch("confluence_cli._build_auth_header")
    def test_http_error_handling(self, mock_auth, mock_urlopen):
        """에러 케이스: HTTP 에러 처리"""
        from urllib.error import HTTPError
        from io import BytesIO

        mock_auth.return_value = "Bearer token"
        mock_error = HTTPError(
            "https://api.example.com/test",
            404,
            "Not Found",
            {},
            BytesIO(b'{"error": "Page not found"}')
        )
        mock_urlopen.side_effect = mock_error

        with self.assertRaises(SystemExit) as cm:
            confluence_cli._http_json("GET", "https://api.example.com/test")

        self.assertIn("404", str(cm.exception))


class TestBuildPageUrl(unittest.TestCase):
    """페이지 URL 생성 함수 테스트"""

    def test_builds_valid_url(self):
        """정상 케이스: 올바른 URL 생성"""
        url = confluence_cli._build_page_url(
            "https://confluence.example.com",
            "DEV",
            "123456"
        )
        self.assertEqual(url, "https://confluence.example.com/spaces/DEV/pages/123456")

    def test_returns_none_when_missing_parts(self):
        """정상 케이스: 필수 정보 누락 시 None 반환"""
        self.assertIsNone(confluence_cli._build_page_url(None, "DEV", "123"))
        self.assertIsNone(confluence_cli._build_page_url("https://example.com", None, "123"))
        self.assertIsNone(confluence_cli._build_page_url("https://example.com", "DEV", None))


if __name__ == "__main__":
    unittest.main()
