#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RateLimitInfo:
    """Figma API rate limit 정보를 담는 클래스."""

    retry_after: int  # 재시도까지 대기할 시간(초)
    plan_tier: str | None  # 리소스의 요금제 계층
    rate_limit_type: str | None  # 좌석 유형별 제한 종류
    upgrade_link: str | None  # 요금제 업그레이드 링크

    def to_dict(self) -> dict:
        return {
            "retry_after_seconds": self.retry_after,
            "plan_tier": self.plan_tier,
            "rate_limit_type": self.rate_limit_type,
            "upgrade_link": self.upgrade_link,
        }

    def __str__(self) -> str:
        parts = [f"Rate limit exceeded. Retry after {self.retry_after} seconds."]
        if self.plan_tier:
            parts.append(f"Plan tier: {self.plan_tier}")
        if self.rate_limit_type:
            limit_desc = "View/Collaborator seat" if self.rate_limit_type == "low" else "Dev/Full seat"
            parts.append(f"Rate limit type: {self.rate_limit_type} ({limit_desc})")
        if self.upgrade_link:
            parts.append(f"Upgrade: {self.upgrade_link}")
        return " | ".join(parts)


class RateLimitError(Exception):
    """Figma API rate limit 초과 시 발생하는 예외."""

    def __init__(self, info: RateLimitInfo):
        self.info = info
        super().__init__(str(info))


def _parse_rate_limit_headers(headers: dict) -> RateLimitInfo:
    """HTTP 응답 헤더에서 rate limit 정보를 추출."""

    def get_header(name: str) -> str | None:
        # headers는 대소문자 구분 없이 접근 가능
        for key in headers:
            if key.lower() == name.lower():
                return headers[key]
        return None

    retry_after = int(get_header("Retry-After") or "60")
    plan_tier = get_header("X-Figma-Plan-Tier")
    rate_limit_type = get_header("X-Figma-Rate-Limit-Type")
    upgrade_link = get_header("X-Figma-Upgrade-Link")

    return RateLimitInfo(
        retry_after=retry_after,
        plan_tier=plan_tier,
        rate_limit_type=rate_limit_type,
        upgrade_link=upgrade_link,
    )


def _env(name: str) -> str | None:
    v = os.getenv(name)
    if v is None:
        return None
    v = v.strip()
    return v or None


def _auth_headers(*, json_body: bool = False) -> dict[str, str]:
    oauth = _env("FIGMA_OAUTH_TOKEN")
    api_key = _env("FIGMA_API_KEY")
    if not oauth and not api_key:
        raise SystemExit("[ERROR] Missing Figma auth. Set FIGMA_OAUTH_TOKEN or FIGMA_API_KEY.")

    headers: dict[str, str] = {"Accept": "application/json"}
    if json_body:
        headers["Content-Type"] = "application/json"
    if oauth:
        headers["Authorization"] = f"Bearer {oauth}"
    else:
        headers["X-Figma-Token"] = api_key  # type: ignore[assignment]
    return headers


def _http_json(
    method: str,
    url: str,
    *,
    params: dict | None = None,
    max_retries: int = 0,
    auto_retry: bool = False,
) -> object:
    """
    HTTP 요청을 수행하고 JSON 응답을 반환.

    Args:
        method: HTTP 메서드
        url: 요청 URL
        params: 쿼리 파라미터
        max_retries: 429 에러 시 최대 재시도 횟수 (auto_retry=True일 때만 적용)
        auto_retry: True면 429 에러 시 자동으로 대기 후 재시도

    Returns:
        JSON 응답 객체

    Raises:
        RateLimitError: rate limit 초과 시 (auto_retry=False이거나 재시도 초과 시)
        SystemExit: 기타 API 에러 시
    """
    if params:
        qs = urllib.parse.urlencode(params, doseq=True)
        sep = "&" if ("?" in url) else "?"
        url = f"{url}{sep}{qs}"

    retries = 0
    while True:
        req = urllib.request.Request(url, headers=_auth_headers(), method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429:
                # Rate limit 초과
                rate_info = _parse_rate_limit_headers(dict(e.headers))
                err_body = e.read().decode("utf-8", errors="replace")

                if auto_retry and retries < max_retries:
                    retries += 1
                    wait_time = rate_info.retry_after
                    print(
                        f"[WARN] Rate limit hit. Waiting {wait_time}s before retry ({retries}/{max_retries})...",
                        file=sys.stderr,
                    )
                    time.sleep(wait_time)
                    continue

                # 자동 재시도하지 않거나 재시도 횟수 초과
                error_output = {
                    "error": "rate_limit_exceeded",
                    "message": str(rate_info),
                    "rate_limit": rate_info.to_dict(),
                    "response_body": err_body if err_body else None,
                }
                raise SystemExit(f"[RATE_LIMIT] {json.dumps(error_output, ensure_ascii=False)}") from None

            err_body = e.read().decode("utf-8", errors="replace")
            raise SystemExit(f"[ERROR] Figma API error: {e.code} {e.reason}\n{err_body}") from None
        except urllib.error.URLError as e:
            raise SystemExit(f"[ERROR] Network error: {e}") from None


def _download_bytes(
    url: str,
    *,
    max_retries: int = 0,
    auto_retry: bool = False,
) -> bytes:
    """
    URL에서 바이트 데이터를 다운로드.

    Args:
        url: 다운로드 URL
        max_retries: 429 에러 시 최대 재시도 횟수 (auto_retry=True일 때만 적용)
        auto_retry: True면 429 에러 시 자동으로 대기 후 재시도

    Returns:
        다운로드된 바이트 데이터

    Raises:
        SystemExit: 다운로드 실패 시 (rate limit 포함)
    """
    retries = 0
    while True:
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 429:
                # Rate limit 초과
                rate_info = _parse_rate_limit_headers(dict(e.headers))
                err_body = e.read().decode("utf-8", errors="replace")

                if auto_retry and retries < max_retries:
                    retries += 1
                    wait_time = rate_info.retry_after
                    print(
                        f"[WARN] Rate limit hit on download. Waiting {wait_time}s before retry ({retries}/{max_retries})...",
                        file=sys.stderr,
                    )
                    time.sleep(wait_time)
                    continue

                error_output = {
                    "error": "rate_limit_exceeded",
                    "message": str(rate_info),
                    "rate_limit": rate_info.to_dict(),
                    "response_body": err_body if err_body else None,
                }
                raise SystemExit(f"[RATE_LIMIT] {json.dumps(error_output, ensure_ascii=False)}") from None

            err_body = e.read().decode("utf-8", errors="replace")
            raise SystemExit(f"[ERROR] Download error: {e.code} {e.reason}\n{err_body}") from None
        except urllib.error.URLError as e:
            raise SystemExit(f"[ERROR] Network error: {e}") from None


def cmd_get(args: argparse.Namespace) -> None:
    base = "https://api.figma.com/v1"
    retry_opts = {
        "auto_retry": args.auto_retry,
        "max_retries": args.max_retries,
    }

    if args.node_id:
        data = _http_json(
            "GET",
            f"{base}/files/{args.file_key}/nodes",
            params={k: v for k, v in {"ids": args.node_id, "depth": args.depth}.items() if v is not None},
            **retry_opts,
        )
    else:
        data = _http_json(
            "GET",
            f"{base}/files/{args.file_key}",
            params={k: v for k, v in {"depth": args.depth}.items() if v is not None},
            **retry_opts,
        )
    print(json.dumps(data, ensure_ascii=False))


def _apply_suffix(base_name: str, suffix: str | None) -> str:
    if not suffix:
        return base_name
    if suffix in base_name:
        return base_name
    idx = base_name.rfind(".")
    if idx > 0:
        return base_name[:idx] + "-" + suffix + base_name[idx:]
    return base_name + "-" + suffix


def _read_nodes(nodes_json: str | None) -> list[dict]:
    if nodes_json is None:
        raise SystemExit("[ERROR] Provide --nodes-json (path to JSON array).")
    data = json.loads(Path(nodes_json).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("[ERROR] nodes JSON must be an array of objects.")
    out: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        file_name = item.get("fileName")
        if not isinstance(file_name, str) or not file_name:
            continue
        out.append(item)
    if not out:
        raise SystemExit("[ERROR] nodes JSON contained no valid items (need at least fileName).")
    return out


def cmd_download(args: argparse.Namespace) -> None:
    base = "https://api.figma.com/v1"
    target = Path(args.local_path).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)

    retry_opts = {
        "auto_retry": args.auto_retry,
        "max_retries": args.max_retries,
    }

    nodes = _read_nodes(args.nodes_json)
    items: list[dict] = []
    for obj in nodes:
        base_name = obj.get("fileName")
        suffix = obj.get("filenameSuffix")
        file_name = _apply_suffix(base_name, suffix) if isinstance(base_name, str) else None
        if not file_name:
            continue
        items.append(
            {
                "fileName": file_name,
                "nodeId": obj.get("nodeId"),
                "imageRef": obj.get("imageRef"),
            }
        )

    # 1) Resolve image fill URLs
    fills = _http_json("GET", f"{base}/files/{args.file_key}/images", **retry_opts)
    fill_map = {}
    if isinstance(fills, dict):
        meta = fills.get("meta") or {}
        if isinstance(meta, dict):
            images = meta.get("images") or {}
            if isinstance(images, dict):
                fill_map = images

    downloaded: list[str] = []

    # 2) Download fills (imageRef)
    for it in [x for x in items if x.get("imageRef")]:
        url = fill_map.get(it["imageRef"])
        if isinstance(url, str) and url:
            data = _download_bytes(url, **retry_opts)
            (target / it["fileName"]).write_bytes(data)
            downloaded.append(it["fileName"])

    # 3) Render PNGs and SVGs by nodeId
    render_items = [x for x in items if x.get("nodeId")]

    def render(node_ids: list[str], fmt: str, extra: dict[str, str] | None = None) -> dict:
        if not node_ids:
            return {}
        params = {"ids": ",".join(node_ids), "format": fmt}
        if fmt == "png":
            params["scale"] = str(args.png_scale)
        if extra:
            params.update(extra)
        resp = _http_json("GET", f"{base}/images/{args.file_key}", params=params, **retry_opts)
        if isinstance(resp, dict):
            images = resp.get("images")
            return images if isinstance(images, dict) else {}
        return {}

    png_nodes = [x["nodeId"] for x in render_items if isinstance(x.get("nodeId"), str) and not str(x["fileName"]).lower().endswith(".svg")]
    svg_nodes = [x["nodeId"] for x in render_items if isinstance(x.get("nodeId"), str) and str(x["fileName"]).lower().endswith(".svg")]

    png_urls = render(png_nodes, "png")
    for it in render_items:
        node_id = it.get("nodeId")
        if node_id in png_urls and isinstance(png_urls[node_id], str):
            data = _download_bytes(png_urls[node_id], **retry_opts)
            (target / it["fileName"]).write_bytes(data)
            downloaded.append(it["fileName"])

    svg_urls = render(
        svg_nodes,
        "svg",
        extra={"svg_outline_text": "true", "svg_include_id": "false", "svg_simplify_stroke": "true"},
    )
    for it in render_items:
        node_id = it.get("nodeId")
        if node_id in svg_urls and isinstance(svg_urls[node_id], str):
            data = _download_bytes(svg_urls[node_id], **retry_opts)
            (target / it["fileName"]).write_bytes(data)
            downloaded.append(it["fileName"])

    out = {"localPath": str(target), "downloaded": downloaded}
    print(json.dumps(out, ensure_ascii=False))


def _add_retry_args(parser: argparse.ArgumentParser) -> None:
    """Rate limit 관련 공통 옵션을 파서에 추가."""
    parser.add_argument(
        "--auto-retry",
        action="store_true",
        help="Rate limit 발생 시 자동으로 대기 후 재시도",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Rate limit 발생 시 최대 재시도 횟수 (기본값: 3)",
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Figma CLI (no MCP required)",
        epilog="""
Rate Limit 처리:
  429 에러 발생 시 JSON 형식으로 rate limit 정보를 출력합니다.
  출력 형식: [RATE_LIMIT] {"error": "rate_limit_exceeded", "rate_limit": {...}}

  rate_limit 객체 필드:
    - retry_after_seconds: 재시도까지 대기할 시간(초)
    - plan_tier: 리소스의 요금제 계층 (enterprise, org, pro, starter, student)
    - rate_limit_type: 좌석 유형 (low=View/Collab, high=Dev/Full)
    - upgrade_link: 요금제 업그레이드 또는 설정 페이지 링크
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("get", help="Fetch Figma file data or node data")
    g.add_argument("--file-key", required=True)
    g.add_argument("--node-id")
    g.add_argument("--depth", type=int)
    _add_retry_args(g)
    g.set_defaults(func=cmd_get)

    d = sub.add_parser("download", help="Download images (PNG/SVG) or fills from Figma")
    d.add_argument("--file-key", required=True)
    d.add_argument("--local-path", required=True)
    d.add_argument("--nodes-json", required=True, help="Path to JSON array of node specs (fileName + nodeId/imageRef)")
    d.add_argument("--png-scale", type=int, default=2)
    _add_retry_args(d)
    d.set_defaults(func=cmd_download)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

