#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


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


def _http_json(method: str, url: str, *, params: dict | None = None) -> object:
    if params:
        qs = urllib.parse.urlencode(params, doseq=True)
        sep = "&" if ("?" in url) else "?"
        url = f"{url}{sep}{qs}"

    req = urllib.request.Request(url, headers=_auth_headers(), method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"[ERROR] Figma API error: {e.code} {e.reason}\n{err_body}") from None
    except urllib.error.URLError as e:
        raise SystemExit(f"[ERROR] Network error: {e}") from None


def _download_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"[ERROR] Download error: {e.code} {e.reason}\n{err_body}") from None
    except urllib.error.URLError as e:
        raise SystemExit(f"[ERROR] Network error: {e}") from None


def cmd_get(args: argparse.Namespace) -> None:
    base = "https://api.figma.com/v1"
    if args.node_id:
        data = _http_json(
            "GET",
            f"{base}/files/{args.file_key}/nodes",
            params={k: v for k, v in {"ids": args.node_id, "depth": args.depth}.items() if v is not None},
        )
    else:
        data = _http_json(
            "GET",
            f"{base}/files/{args.file_key}",
            params={k: v for k, v in {"depth": args.depth}.items() if v is not None},
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
    fills = _http_json("GET", f"{base}/files/{args.file_key}/images")
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
            data = _download_bytes(url)
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
        resp = _http_json("GET", f"{base}/images/{args.file_key}", params=params)
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
            data = _download_bytes(png_urls[node_id])
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
            data = _download_bytes(svg_urls[node_id])
            (target / it["fileName"]).write_bytes(data)
            downloaded.append(it["fileName"])

    out = {"localPath": str(target), "downloaded": downloaded}
    print(json.dumps(out, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Figma CLI (no MCP required)")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("get", help="Fetch Figma file data or node data")
    g.add_argument("--file-key", required=True)
    g.add_argument("--node-id")
    g.add_argument("--depth", type=int)
    g.set_defaults(func=cmd_get)

    d = sub.add_parser("download", help="Download images (PNG/SVG) or fills from Figma")
    d.add_argument("--file-key", required=True)
    d.add_argument("--local-path", required=True)
    d.add_argument("--nodes-json", required=True, help="Path to JSON array of node specs (fileName + nodeId/imageRef)")
    d.add_argument("--png-scale", type=int, default=2)
    d.set_defaults(func=cmd_download)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

