#!/usr/bin/env python3
"""Elasticsearch/Kibana 로그 조회 CLI - Kibana API를 통한 로그 검색 자동화 도구.

표준 라이브러리만 사용한다.
2단계 인증: nginx Basic Auth (LDAP) + Kibana 세션 로그인 (ES 계정).
Kibana console proxy API를 통해 Elasticsearch 쿼리를 실행한다.
"""
from __future__ import annotations

import argparse
import base64
import http.cookiejar
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone


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

def _kibana_base() -> str:
    return (_env("KIBANA_URL") or "http://211.47.70.165").rstrip("/")


def _default_space() -> str:
    return _env("KIBANA_SPACE") or "kubernetes"


def _default_index_pattern() -> str:
    return _env("KIBANA_INDEX_PATTERN") or "c8095940-0c7b-11ed-a662-5ff9b95a299f"


def _nginx_auth_header() -> str:
    """nginx 프록시 Basic Auth 헤더 값."""
    user = _require_env("LDAP_USER")
    pwd = _require_env("LDAP_PWD")
    cred = base64.b64encode(f"{user}:{pwd}".encode()).decode()
    return f"Basic {cred}"


# ---------------------------------------------------------------------------
# SSL 컨텍스트
# ---------------------------------------------------------------------------

def _ssl_context() -> ssl.SSLContext | None:
    base = _kibana_base()
    if base.startswith("https"):
        verify = (_env("KIBANA_SSL_VERIFY") or "false").lower()
        if verify in ("0", "false", "no"):
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            return ctx
        return ssl.create_default_context()
    return None


# ---------------------------------------------------------------------------
# 세션 관리 (2단계 인증: nginx Basic Auth + Kibana 로그인)
# ---------------------------------------------------------------------------

_session_opener: urllib.request.OpenerDirector | None = None


def _get_opener() -> urllib.request.OpenerDirector:
    """Kibana 세션이 활성화된 opener를 반환한다. 최초 호출 시 로그인."""
    global _session_opener
    if _session_opener is not None:
        return _session_opener

    cj = http.cookiejar.CookieJar()
    _session_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    # Kibana 로그인
    kibana_user = _env("KIBANA_USER") or "developer"
    kibana_pwd = _env("KIBANA_PWD") or "roqkfroqkf!@#$"

    login_url = f"{_kibana_base()}/internal/security/login"
    body = json.dumps({
        "providerType": "basic",
        "providerName": "basic",
        "currentURL": f"{_kibana_base()}/",
        "params": {
            "username": kibana_user,
            "password": kibana_pwd,
        },
    }).encode("utf-8")

    req = urllib.request.Request(login_url, data=body, method="POST")
    req.add_header("Authorization", _nginx_auth_header())
    req.add_header("kbn-xsrf", "true")
    req.add_header("Content-Type", "application/json")

    try:
        resp = _session_opener.open(req, timeout=30)
        resp.read()  # consume body
        sys.stderr.write("[INFO] Kibana 로그인 성공\n")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"[ERROR] Kibana 로그인 실패: {e.code} {e.reason}\n{err_body}")
    except urllib.error.URLError as e:
        raise SystemExit(f"[ERROR] 네트워크 오류 (로그인): {e}")

    return _session_opener


# ---------------------------------------------------------------------------
# HTTP 유틸 (세션 기반)
# ---------------------------------------------------------------------------

def _http_json(
    method: str,
    url: str,
    *,
    body: dict | list | None = None,
    params: dict | None = None,
) -> object:
    if params:
        qs = urllib.parse.urlencode(params, doseq=True)
        sep = "&" if "?" in url else "?"
        url = f"{url}{sep}{qs}"

    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", _nginx_auth_header())
    req.add_header("kbn-xsrf", "true")
    req.add_header("Content-Type", "application/json")

    opener = _get_opener()
    ctx = _ssl_context()
    try:
        kwargs = {"timeout": 60}
        if ctx:
            kwargs["context"] = ctx
        with opener.open(req, **kwargs) as resp:
            raw = resp.read().decode("utf-8")
            if not raw:
                return {}
            return json.loads(raw)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"[ERROR] Kibana API 오류: {e.code} {e.reason}\n{err_body}")
    except urllib.error.URLError as e:
        raise SystemExit(f"[ERROR] 네트워크 오류: {e}")


# ---------------------------------------------------------------------------
# 시간 범위 파싱
# ---------------------------------------------------------------------------

def _parse_time_range(time_from: str, time_to: str) -> tuple[str, str]:
    """Kibana 스타일 시간 표현식을 ISO 포맷으로 변환.

    지원 형식:
      - 'now', 'now-1h', 'now-25h', 'now-7d', 'now-30m'
      - ISO 8601 문자열 (그대로 반환)
    """
    now = datetime.now(timezone.utc)

    def _resolve(expr: str) -> str:
        expr = expr.strip()
        if expr == "now":
            return now.isoformat()

        m = re.match(r"^now-(\d+)([smhdwM])$", expr)
        if m:
            val = int(m.group(1))
            unit = m.group(2)
            delta_map = {
                "s": timedelta(seconds=val),
                "m": timedelta(minutes=val),
                "h": timedelta(hours=val),
                "d": timedelta(days=val),
                "w": timedelta(weeks=val),
                "M": timedelta(days=val * 30),
            }
            delta = delta_map.get(unit, timedelta(hours=val))
            return (now - delta).isoformat()

        # ISO 포맷이면 그대로 반환
        return expr

    return _resolve(time_from), _resolve(time_to)


# ---------------------------------------------------------------------------
# Kibana URL 파싱
# ---------------------------------------------------------------------------

def _parse_kibana_url(url: str) -> dict | None:
    """Kibana Discover URL에서 space, index pattern, KQL 쿼리, 시간 범위 추출.

    지원 형식:
      http://host/s/{space}/app/discover#/?_g=(...)&_a=(...)
    """
    result = {}

    # space 추출
    m = re.search(r"/s/([^/]+)/app/discover", url)
    if m:
        result["space"] = m.group(1)

    # fragment(_g, _a) 파싱 - URL 디코딩 후 처리
    decoded = urllib.parse.unquote(url)

    # index pattern 추출
    m = re.search(r"index:([a-f0-9-]+)", decoded)
    if m:
        result["index_pattern"] = m.group(1)

    # KQL 쿼리 추출 - _a 섹션의 query
    m = re.search(r"_a=.*?query:\(language:kuery,query:'([^']*)'\)", decoded)
    if m:
        result["kql"] = urllib.parse.unquote(m.group(1))

    # 시간 범위 추출
    m_from = re.search(r"time:\(from:([^,)]+)", decoded)
    m_to = re.search(r"time:\(from:[^,]+,to:([^)]+)\)", decoded)
    if m_from:
        result["time_from"] = m_from.group(1)
    if m_to:
        result["time_to"] = m_to.group(1)

    return result if result else None


# ---------------------------------------------------------------------------
# Elasticsearch 쿼리 빌더
# ---------------------------------------------------------------------------

def _resolve_index_title(space: str, index_pattern_id: str) -> str:
    """인덱스 패턴 ID에서 실제 인덱스 제목(예: filebeat-*)을 조회."""
    url = f"{_kibana_base()}/s/{space}/api/saved_objects/index-pattern/{index_pattern_id}"
    try:
        data = _http_json("GET", url)
        if isinstance(data, dict):
            return data.get("attributes", {}).get("title", index_pattern_id)
    except SystemExit:
        pass
    return index_pattern_id


def _build_es_query(
    kql: str | None = None,
    time_from: str = "now-24h",
    time_to: str = "now",
    timestamp_field: str = "@timestamp",
) -> dict:
    """KQL 문자열을 Elasticsearch 쿼리 DSL로 변환.

    간단한 KQL만 지원:
      - field : "value"       → match_phrase
      - field : *value*       → wildcard (keyword 서브필드 자동 사용)
      - field : value         → match
      - AND / OR 조합
    """
    gte, lte = _parse_time_range(time_from, time_to)

    time_filter = {
        "range": {
            timestamp_field: {
                "gte": gte,
                "lte": lte,
                "format": "strict_date_optional_time",
            }
        }
    }

    if not kql or kql.strip() == "":
        return {"bool": {"filter": [time_filter]}}

    must_clauses = []

    # 간단한 KQL 파서: field : "value" 또는 field : value
    parts = re.split(r"\s+(?:AND|and)\s+", kql.strip())

    for part in parts:
        part = part.strip()
        if not part:
            continue

        # field : "quoted value" (exact match)
        m = re.match(r'^([\w.@-]+)\s*:\s*"([^"]*)"$', part)
        if m:
            field, value = m.group(1), m.group(2)
            if "*" in value:
                # wildcard 쿼리는 keyword 서브필드 사용
                must_clauses.append({"wildcard": {f"{field}.keyword": {"value": value}}})
            else:
                must_clauses.append({"match_phrase": {field: value}})
            continue

        # field : *value* (wildcard)
        m = re.match(r"^([\w.@-]+)\s*:\s*(\S+)$", part)
        if m:
            field, value = m.group(1), m.group(2)
            if "*" in value:
                must_clauses.append({"wildcard": {f"{field}.keyword": {"value": value}}})
            else:
                must_clauses.append({"match_phrase": {field: value}})
            continue

        # 기타: 전체 텍스트 검색
        must_clauses.append({"query_string": {"query": part}})

    return {
        "bool": {
            "must": must_clauses,
            "filter": [time_filter],
        }
    }


# ---------------------------------------------------------------------------
# 서브커맨드 핸들러
# ---------------------------------------------------------------------------

def cmd_search(args: argparse.Namespace) -> None:
    """로그 검색 - Kibana console proxy를 통한 Elasticsearch 쿼리 실행."""
    space = args.space or _default_space()
    index_pattern = args.index_pattern or _default_index_pattern()
    kql = args.kql or ""
    time_from = args.time_from or "now-24h"
    time_to = args.time_to or "now"
    size = args.size or 50
    sort_field = args.sort_field or "@timestamp"
    sort_order = args.sort_order or "desc"
    fields = args.fields

    # 인덱스 패턴 ID → 실제 인덱스 이름 변환
    index_title = _resolve_index_title(space, index_pattern)

    query = _build_es_query(kql, time_from, time_to)

    es_body: dict = {
        "query": query,
        "sort": [{sort_field: {"order": sort_order, "unmapped_type": "boolean"}}],
        "size": size,
        "_source": True,
    }

    # 특정 필드만 요청
    if fields:
        field_list = [f.strip() for f in fields.split(",")]
        es_body["_source"] = field_list

    # Kibana console proxy를 통한 ES 쿼리
    encoded_path = urllib.parse.quote(f"{index_title}/_search", safe="/-_*")
    url = f"{_kibana_base()}/api/console/proxy?path={encoded_path}&method=POST"

    result = _http_json("POST", url, body=es_body)

    # 결과 파싱
    if isinstance(result, dict):
        hits = result.get("hits", {})

        output = {
            "total": hits.get("total", {}).get("value", 0) if isinstance(hits.get("total"), dict) else hits.get("total", 0),
            "returned": len(hits.get("hits", [])),
            "hits": [],
        }

        for hit in hits.get("hits", []):
            entry = {
                "_index": hit.get("_index", ""),
                "_id": hit.get("_id", ""),
                "_source": hit.get("_source", {}),
            }
            output["hits"].append(entry)

        # --compact 모드: _source만 출력
        if args.compact:
            output = {
                "total": output["total"],
                "returned": output["returned"],
                "logs": [h["_source"] for h in output["hits"]],
            }

        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_service_logs(args: argparse.Namespace) -> None:
    """서비스 로그 조회 - kubernetes.service-name 기준 간편 검색."""
    service = args.service_name
    kql = f'kubernetes.service-name : "*{service}*"'

    if args.extra_kql:
        kql = f'{kql} AND {args.extra_kql}'

    # args를 재구성하여 cmd_search 호출
    args.kql = kql
    args.space = args.space or _default_space()
    args.index_pattern = args.index_pattern or _default_index_pattern()
    args.time_from = args.time_from or "now-24h"
    args.time_to = args.time_to or "now"
    args.size = args.size or 50
    args.sort_field = args.sort_field or "@timestamp"
    args.sort_order = args.sort_order or "desc"
    if not hasattr(args, "compact"):
        args.compact = False

    cmd_search(args)


def cmd_url_search(args: argparse.Namespace) -> None:
    """Kibana URL에서 쿼리 조건을 자동 추출하여 로그 검색."""
    parsed = _parse_kibana_url(args.url)
    if not parsed:
        raise SystemExit(f"[ERROR] Kibana Discover URL을 파싱할 수 없습니다: {args.url}")

    # 추출된 정보로 args 구성
    args.space = parsed.get("space", _default_space())
    args.index_pattern = parsed.get("index_pattern", _default_index_pattern())
    args.kql = parsed.get("kql", "")
    args.time_from = parsed.get("time_from", "now-24h")
    args.time_to = parsed.get("time_to", "now")
    args.size = args.size or 50
    args.sort_field = args.sort_field or "@timestamp"
    args.sort_order = args.sort_order or "desc"
    if not hasattr(args, "compact"):
        args.compact = False
    if not hasattr(args, "fields"):
        args.fields = None

    # 파싱된 정보 출력
    sys.stderr.write(f"[INFO] Parsed URL:\n")
    sys.stderr.write(f"  Space: {args.space}\n")
    sys.stderr.write(f"  Index Pattern: {args.index_pattern}\n")
    sys.stderr.write(f"  KQL: {args.kql}\n")
    sys.stderr.write(f"  Time: {args.time_from} ~ {args.time_to}\n")

    cmd_search(args)


def cmd_index_patterns(args: argparse.Namespace) -> None:
    """Kibana space의 인덱스 패턴 목록 조회."""
    space = args.space or _default_space()
    url = f"{_kibana_base()}/s/{space}/api/saved_objects/_find"
    params = {
        "type": "index-pattern",
        "per_page": str(args.limit or 100),
    }
    if args.search:
        params["search"] = args.search

    data = _http_json("GET", url, params=params)
    saved_objects = data.get("saved_objects", []) if isinstance(data, dict) else []

    output = []
    for obj in saved_objects:
        attrs = obj.get("attributes", {})
        output.append({
            "id": obj.get("id", ""),
            "title": attrs.get("title", ""),
            "timeFieldName": attrs.get("timeFieldName", ""),
        })

    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_spaces(args: argparse.Namespace) -> None:
    """Kibana space 목록 조회."""
    url = f"{_kibana_base()}/api/spaces/space"
    data = _http_json("GET", url)

    if isinstance(data, list):
        output = [{"id": s.get("id", ""), "name": s.get("name", "")} for s in data]
    else:
        output = data

    print(json.dumps(output, ensure_ascii=False, indent=2))


def cmd_fields(args: argparse.Namespace) -> None:
    """인덱스 패턴의 필드 목록 조회."""
    space = args.space or _default_space()
    index_pattern = args.index_pattern or _default_index_pattern()

    url = f"{_kibana_base()}/s/{space}/api/saved_objects/index-pattern/{index_pattern}"
    data = _http_json("GET", url)

    if isinstance(data, dict):
        attrs = data.get("attributes", {})
        fields_str = attrs.get("fields", "[]")
        try:
            fields_list = json.loads(fields_str) if isinstance(fields_str, str) else fields_str
        except json.JSONDecodeError:
            fields_list = []

        # 필터링
        if args.filter:
            pattern = args.filter.lower()
            fields_list = [f for f in fields_list if pattern in f.get("name", "").lower()]

        # 간결한 출력
        output = []
        for f in fields_list:
            output.append({
                "name": f.get("name", ""),
                "type": f.get("type", ""),
                "searchable": f.get("searchable", False),
                "aggregatable": f.get("aggregatable", False),
            })

        # 이름순 정렬
        output.sort(key=lambda x: x["name"])

        if args.names_only:
            print(json.dumps([f["name"] for f in output], ensure_ascii=False, indent=2))
        else:
            print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(data, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# CLI 파서
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="elasticsearch_cli",
        description="Elasticsearch/Kibana 로그 조회 CLI - Kibana API 통한 로그 검색",
    )
    sub = p.add_subparsers(dest="command", required=True)

    # search - 일반 검색
    sp = sub.add_parser("search", help="KQL 쿼리로 로그 검색")
    sp.add_argument("--kql", "-q", help="KQL 쿼리 (예: 'kubernetes.service-name : \"*gsecu-api*\"')")
    sp.add_argument("--space", "-s", help=f"Kibana space (기본: KIBANA_SPACE 또는 kubernetes)")
    sp.add_argument("--index-pattern", "-i", help="인덱스 패턴 ID (기본: KIBANA_INDEX_PATTERN)")
    sp.add_argument("--time-from", default="now-24h", help="시작 시간 (기본: now-24h)")
    sp.add_argument("--time-to", default="now", help="종료 시간 (기본: now)")
    sp.add_argument("--size", "-n", type=int, default=50, help="결과 수 (기본: 50, 최대: 10000)")
    sp.add_argument("--sort-field", default="@timestamp", help="정렬 필드 (기본: @timestamp)")
    sp.add_argument("--sort-order", choices=["asc", "desc"], default="desc", help="정렬 순서 (기본: desc)")
    sp.add_argument("--fields", help="조회할 필드 (쉼표 구분, 예: '@timestamp,message,level')")
    sp.add_argument("--compact", action="store_true", help="_source만 간결하게 출력")

    # service-logs - 서비스별 간편 검색
    sp = sub.add_parser("service-logs", help="kubernetes 서비스명으로 로그 간편 검색")
    sp.add_argument("service_name", help="서비스명 (예: gsecu-api-stage)")
    sp.add_argument("--extra-kql", help="추가 KQL 조건 (AND로 결합)")
    sp.add_argument("--space", "-s", help="Kibana space")
    sp.add_argument("--index-pattern", "-i", help="인덱스 패턴 ID")
    sp.add_argument("--time-from", default="now-24h", help="시작 시간")
    sp.add_argument("--time-to", default="now", help="종료 시간")
    sp.add_argument("--size", "-n", type=int, default=50, help="결과 수")
    sp.add_argument("--sort-field", default="@timestamp", help="정렬 필드")
    sp.add_argument("--sort-order", choices=["asc", "desc"], default="desc", help="정렬 순서")
    sp.add_argument("--fields", help="조회할 필드 (쉼표 구분)")
    sp.add_argument("--compact", action="store_true", help="_source만 간결하게 출력")

    # url-search - Kibana URL로 검색
    sp = sub.add_parser("url-search", help="Kibana Discover URL에서 조건 추출 후 검색")
    sp.add_argument("url", help="Kibana Discover URL")
    sp.add_argument("--size", "-n", type=int, default=50, help="결과 수")
    sp.add_argument("--sort-field", default="@timestamp", help="정렬 필드")
    sp.add_argument("--sort-order", choices=["asc", "desc"], default="desc", help="정렬 순서")
    sp.add_argument("--fields", help="조회할 필드 (쉼표 구분)")
    sp.add_argument("--compact", action="store_true", help="_source만 간결하게 출력")

    # index-patterns - 인덱스 패턴 목록
    sp = sub.add_parser("index-patterns", help="Kibana 인덱스 패턴 목록 조회")
    sp.add_argument("--space", "-s", help="Kibana space")
    sp.add_argument("--search", help="검색 키워드")
    sp.add_argument("--limit", type=int, default=100, help="최대 결과 수")

    # spaces - Kibana space 목록
    sub.add_parser("spaces", help="Kibana space 목록 조회")

    # fields - 필드 목록
    sp = sub.add_parser("fields", help="인덱스 패턴의 필드 목록 조회")
    sp.add_argument("--space", "-s", help="Kibana space")
    sp.add_argument("--index-pattern", "-i", help="인덱스 패턴 ID")
    sp.add_argument("--filter", help="필드명 필터 (부분 일치)")
    sp.add_argument("--names-only", action="store_true", help="필드명만 출력")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    handlers = {
        "search": cmd_search,
        "service-logs": cmd_service_logs,
        "url-search": cmd_url_search,
        "index-patterns": cmd_index_patterns,
        "spaces": cmd_spaces,
        "fields": cmd_fields,
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
