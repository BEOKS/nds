#!/usr/bin/env python3
"""Sentry API CLI - 이슈/이벤트/프로젝트 조회 자동화 도구.

표준 라이브러리만 사용하며, 환경변수 기반 인증을 지원한다.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request


# ---------------------------------------------------------------------------
# 환경변수 유틸
# ---------------------------------------------------------------------------

def _env(name: str) -> str | None:
    v = os.environ.get(name)
    return v.strip() if v else None


def _require_env(name: str) -> str:
    v = _env(name)
    if not v:
        raise SystemExit(f"[ERROR] 환경변수 {name} 이(가) 설정되지 않았습니다.")
    return v


# ---------------------------------------------------------------------------
# API 기본 설정
# ---------------------------------------------------------------------------

def _api_base() -> str:
    return (_env("SENTRY_API_URL") or "https://sentry.gabia.io:9000").rstrip("/")


def _org_slug() -> str:
    return _env("SENTRY_ORG") or "sentry-gabia"


def _auth_headers() -> dict[str, str]:
    token = _require_env("SENTRY_TOKEN")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# SSL 컨텍스트 (self-hosted 인증서 처리)
# ---------------------------------------------------------------------------

def _ssl_context() -> ssl.SSLContext:
    verify = (_env("SENTRY_SSL_VERIFY") or "false").lower()
    if verify in ("0", "false", "no"):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    return ssl.create_default_context()


# ---------------------------------------------------------------------------
# HTTP 유틸
# ---------------------------------------------------------------------------

def _http_json(
    method: str,
    url: str,
    *,
    params: dict | None = None,
    body: dict | None = None,
) -> object:
    if params:
        qs = urllib.parse.urlencode(params, doseq=True)
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{qs}"

    data = json.dumps(body).encode("utf-8") if body else None
    req = urllib.request.Request(url, data=data, headers=_auth_headers(), method=method)

    try:
        with urllib.request.urlopen(req, timeout=60, context=_ssl_context()) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return {}
            result = json.loads(raw)
            # 페이지네이션 헤더 추출
            link_header = resp.headers.get("Link", "")
            if link_header and isinstance(result, list):
                result = {
                    "items": result,
                    "pagination": _parse_link_header(link_header),
                }
            return result
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"[ERROR] Sentry API 오류: {e.code} {e.reason}\n{err_body}")
    except urllib.error.URLError as e:
        raise SystemExit(f"[ERROR] 네트워크 오류: {e}")


def _parse_link_header(header: str) -> dict:
    """Link 헤더에서 페이지네이션 정보 추출."""
    info = {}
    for part in header.split(","):
        match = re.search(r'<([^>]+)>;\s*rel="(\w+)";\s*results="(\w+)";\s*cursor="([^"]*)"', part)
        if match:
            info[match.group(2)] = {
                "url": match.group(1),
                "results": match.group(3) == "true",
                "cursor": match.group(4),
            }
    return info


# ---------------------------------------------------------------------------
# URL 파싱
# ---------------------------------------------------------------------------

def _parse_sentry_url(url: str) -> dict | None:
    """Sentry 이슈 URL에서 org, issue_id, project 추출.

    지원 형식:
      https://sentry.gabia.io:9000/organizations/{org}/issues/{issue_id}/?project={id}
    """
    m = re.search(r"/organizations/([^/]+)/issues/(\d+)/", url)
    if not m:
        return None
    result = {"org": m.group(1), "issue_id": m.group(2)}
    # project 파라미터 추출
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    if "project" in qs:
        result["project"] = qs["project"][0]
    return result


# ---------------------------------------------------------------------------
# 서브커맨드 핸들러
# ---------------------------------------------------------------------------

def cmd_projects(args: argparse.Namespace) -> None:
    """조직의 프로젝트 목록 조회."""
    org = args.org or _org_slug()
    url = f"{_api_base()}/api/0/organizations/{org}/projects/"
    params = {}
    if args.cursor:
        params["cursor"] = args.cursor
    data = _http_json("GET", url, params=params or None)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_issues(args: argparse.Namespace) -> None:
    """이슈 목록 검색."""
    org = args.org or _org_slug()
    url = f"{_api_base()}/api/0/organizations/{org}/issues/"
    params: dict = {}
    if args.query:
        params["query"] = args.query
    if args.project:
        params["project"] = args.project
    if args.sort:
        params["sort"] = args.sort
    if args.stats_period:
        params["statsPeriod"] = args.stats_period
    if args.limit:
        params["limit"] = str(args.limit)
    if args.cursor:
        params["cursor"] = args.cursor
    if args.environment:
        params["environment"] = args.environment
    data = _http_json("GET", url, params=params or None)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_issue_get(args: argparse.Namespace) -> None:
    """이슈 상세 조회 (URL 또는 issue_id)."""
    org = args.org or _org_slug()
    issue_id = args.issue_id

    # URL이 입력된 경우 파싱
    parsed = _parse_sentry_url(issue_id)
    if parsed:
        org = parsed["org"]
        issue_id = parsed["issue_id"]

    url = f"{_api_base()}/api/0/organizations/{org}/issues/{issue_id}/"
    data = _http_json("GET", url)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_issue_events(args: argparse.Namespace) -> None:
    """이슈의 이벤트 목록 조회."""
    org = args.org or _org_slug()
    issue_id = args.issue_id

    parsed = _parse_sentry_url(issue_id)
    if parsed:
        org = parsed["org"]
        issue_id = parsed["issue_id"]

    url = f"{_api_base()}/api/0/organizations/{org}/issues/{issue_id}/events/"
    params: dict = {}
    if args.full:
        params["full"] = "true"
    if args.cursor:
        params["cursor"] = args.cursor
    data = _http_json("GET", url, params=params or None)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_event_get(args: argparse.Namespace) -> None:
    """특정 이벤트 상세 조회."""
    org = args.org or _org_slug()
    issue_id = args.issue_id
    event_id = args.event_id  # 'latest', 'oldest', 'recommended' 또는 실제 ID

    parsed = _parse_sentry_url(issue_id)
    if parsed:
        org = parsed["org"]
        issue_id = parsed["issue_id"]

    url = f"{_api_base()}/api/0/organizations/{org}/issues/{issue_id}/events/{event_id}/"
    data = _http_json("GET", url)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_issue_update(args: argparse.Namespace) -> None:
    """이슈 상태 변경 (resolve, ignore, unresolve 등)."""
    org = args.org or _org_slug()
    issue_id = args.issue_id

    parsed = _parse_sentry_url(issue_id)
    if parsed:
        org = parsed["org"]
        issue_id = parsed["issue_id"]

    url = f"{_api_base()}/api/0/organizations/{org}/issues/{issue_id}/"
    body: dict = {}
    if args.status:
        body["status"] = args.status
    if args.assignedTo:
        body["assignedTo"] = args.assignedTo
    if args.has_seen is not None:
        body["hasSeen"] = args.has_seen

    if not body:
        raise SystemExit("[ERROR] 변경할 항목을 지정하세요 (--status, --assigned-to, --has-seen)")

    data = _http_json("PUT", url, body=body)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_url_info(args: argparse.Namespace) -> None:
    """Sentry URL에서 정보 추출 후 이슈 상세 조회."""
    parsed = _parse_sentry_url(args.url)
    if not parsed:
        raise SystemExit(f"[ERROR] Sentry 이슈 URL을 파싱할 수 없습니다: {args.url}")

    org = parsed["org"]
    issue_id = parsed["issue_id"]

    # 이슈 상세 조회
    url = f"{_api_base()}/api/0/organizations/{org}/issues/{issue_id}/"
    data = _http_json("GET", url)

    # latest 이벤트도 함께 조회
    if args.with_latest:
        event_url = f"{_api_base()}/api/0/organizations/{org}/issues/{issue_id}/events/latest/"
        try:
            latest = _http_json("GET", event_url)
            data["_latestEvent"] = latest
        except SystemExit:
            data["_latestEvent"] = None

    print(json.dumps(data, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# CLI 파서
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sentry_cli",
        description="Sentry API CLI - 이슈/이벤트/프로젝트 조회",
    )
    p.add_argument("--org", help="조직 slug (기본: SENTRY_ORG 또는 sentry-gabia)")
    sub = p.add_subparsers(dest="command", required=True)

    # projects
    sp = sub.add_parser("projects", help="프로젝트 목록 조회")
    sp.add_argument("--cursor", help="페이지네이션 커서")

    # issues (검색)
    sp = sub.add_parser("issues", help="이슈 목록 검색")
    sp.add_argument("--query", "-q", default="is:unresolved", help="검색 쿼리 (기본: is:unresolved)")
    sp.add_argument("--project", action="append", help="프로젝트 ID (여러 개 가능)")
    sp.add_argument("--sort", choices=["date", "freq", "new", "trends", "user"], help="정렬 기준")
    sp.add_argument("--stats-period", help="통계 기간 (예: 24h, 7d)")
    sp.add_argument("--limit", type=int, help="최대 결과 수 (기본 100, 최대 100)")
    sp.add_argument("--cursor", help="페이지네이션 커서")
    sp.add_argument("--environment", action="append", help="환경 필터 (여러 개 가능)")

    # issue-get (상세 조회)
    sp = sub.add_parser("issue-get", help="이슈 상세 조회")
    sp.add_argument("issue_id", help="이슈 ID 또는 Sentry 이슈 URL")

    # issue-events
    sp = sub.add_parser("issue-events", help="이슈의 이벤트 목록")
    sp.add_argument("issue_id", help="이슈 ID 또는 Sentry 이슈 URL")
    sp.add_argument("--full", action="store_true", help="전체 이벤트 본문 포함 (stacktrace 등)")
    sp.add_argument("--cursor", help="페이지네이션 커서")

    # event-get
    sp = sub.add_parser("event-get", help="특정 이벤트 상세 조회")
    sp.add_argument("issue_id", help="이슈 ID 또는 Sentry 이슈 URL")
    sp.add_argument("event_id", help="이벤트 ID (또는 latest, oldest, recommended)")

    # issue-update
    sp = sub.add_parser("issue-update", help="이슈 상태 변경")
    sp.add_argument("issue_id", help="이슈 ID 또는 Sentry 이슈 URL")
    sp.add_argument("--status", choices=["resolved", "unresolved", "ignored"], help="이슈 상태")
    sp.add_argument("--assigned-to", dest="assignedTo", help="담당자 (username 또는 team:slug)")
    sp.add_argument("--has-seen", dest="has_seen", type=bool, help="확인 여부")

    # url-info (URL로 이슈 조회)
    sp = sub.add_parser("url-info", help="Sentry URL로 이슈 상세 조회")
    sp.add_argument("url", help="Sentry 이슈 URL")
    sp.add_argument("--with-latest", action="store_true", help="최신 이벤트 정보도 함께 조회")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    handlers = {
        "projects": cmd_projects,
        "issues": cmd_issues,
        "issue-get": cmd_issue_get,
        "issue-events": cmd_issue_events,
        "event-get": cmd_event_get,
        "issue-update": cmd_issue_update,
        "url-info": cmd_url_info,
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
