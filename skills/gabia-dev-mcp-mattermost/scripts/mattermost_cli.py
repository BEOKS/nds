#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def _env(name: str) -> str | None:
    v = os.getenv(name)
    if v is None:
        return None
    v = v.strip()
    return v or None


def _require_env(name: str) -> str:
    v = _env(name)
    if not v:
        raise SystemExit(f"[ERROR] Missing required env: {name}")
    return v


def _api_base() -> str:
    return (_env("MATTERMOST_API_URL") or "https://mattermost.gabia.com/api/v4").rstrip("/")


def _boards_api_base() -> str:
    return (_env("MATTERMOST_BOARDS_API_URL") or "https://mattermost.gabia.com/plugins/focalboard/api/v2").rstrip("/")


def _auth_headers(*, json_body: bool = False, extra: dict[str, str] | None = None) -> dict[str, str]:
    token = _require_env("MATTERMOST_TOKEN")
    headers: dict[str, str] = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
    if json_body:
        headers["Content-Type"] = "application/json"
    if extra:
        headers.update(extra)
    return headers


def _http_json(method: str, url: str, *, params: dict | None = None, body: dict | None = None, headers: dict[str, str] | None = None) -> object:
    if params:
        qs = urllib.parse.urlencode(params, doseq=True)
        sep = "&" if ("?" in url) else "?"
        url = f"{url}{sep}{qs}"

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"[ERROR] Mattermost API error: {e.code} {e.reason}\n{err_body}") from None
    except urllib.error.URLError as e:
        raise SystemExit(f"[ERROR] Network error: {e}") from None


def cmd_search_posts(args: argparse.Namespace) -> None:
    api = _api_base()
    route = f"{api}/teams/{args.team_id}/posts/search" if args.team_id else f"{api}/posts/search"
    payload: dict = {
        "terms": args.terms,
        "is_or_search": bool(args.is_or_search),
        "page": args.page,
        "per_page": args.per_page,
        "include_deleted_channels": bool(args.include_deleted_channels),
    }
    if args.time_zone_offset is not None:
        payload["time_zone_offset"] = args.time_zone_offset
    data = _http_json("POST", route, body=payload, headers=_auth_headers(json_body=True))
    print(json.dumps(data, ensure_ascii=False))


def cmd_search_files(args: argparse.Namespace) -> None:
    api = _api_base()
    route = f"{api}/teams/{args.team_id}/files/search" if args.team_id else f"{api}/files/search"
    payload: dict = {
        "terms": args.terms,
        "is_or_search": bool(args.is_or_search),
        "page": args.page,
        "per_page": args.per_page,
        "include_deleted_channels": bool(args.include_deleted_channels),
    }
    if args.time_zone_offset is not None:
        payload["time_zone_offset"] = args.time_zone_offset
    data = _http_json("POST", route, body=payload, headers=_auth_headers(json_body=True))
    print(json.dumps(data, ensure_ascii=False))


def cmd_get_teams(args: argparse.Namespace) -> None:
    api = _api_base()
    data = _http_json(
        "GET",
        f"{api}/users/me/teams",
        params={"page": args.page, "per_page": args.per_page},
        headers=_auth_headers(),
    )
    print(json.dumps(data, ensure_ascii=False))


def cmd_get_channels(args: argparse.Namespace) -> None:
    api = _api_base()
    data = _http_json(
        "GET",
        f"{api}/teams/{args.team_id}/channels",
        params={"page": args.page, "per_page": args.per_page},
        headers=_auth_headers(),
    )
    print(json.dumps(data, ensure_ascii=False))


def cmd_get_users(args: argparse.Namespace) -> None:
    api = _api_base()
    data = _http_json(
        "GET",
        f"{api}/users",
        params={"page": args.page, "per_page": args.per_page},
        headers=_auth_headers(),
    )
    print(json.dumps(data, ensure_ascii=False))


def _parse_board_card_url(card_url: str) -> dict | None:
    try:
        uri = urllib.parse.urlparse(card_url)
        raw_segments = [s for s in uri.path.split("/") if s]
        if not raw_segments:
            return None
        keywords = {"team", "board", "shared", "workspace"}
        start_idx = next((i for i, s in enumerate(raw_segments) if s.lower() in keywords), -1)
        segments = raw_segments if start_idx == -1 else raw_segments[start_idx:]
        if not segments:
            return None

        def parse_team(seg: list[str]) -> dict | None:
            team_id = seg[1] if len(seg) > 1 else None
            third = seg[2] if len(seg) > 2 else None
            if not team_id or not third:
                return None
            if third.lower() == "shared":
                board_id = seg[3] if len(seg) > 3 else None
                view_id = seg[4] if len(seg) > 4 else None
                card_id = seg[5] if len(seg) > 5 else None
                if not board_id or not card_id:
                    return None
                return {"boardId": board_id, "cardId": card_id, "viewId": view_id, "teamId": team_id}
            board_id = third
            view_id = seg[3] if len(seg) > 3 else None
            card_id = seg[4] if len(seg) > 4 else None
            if not card_id:
                return None
            return {"boardId": board_id, "cardId": card_id, "viewId": view_id, "teamId": team_id}

        def parse_board(seg: list[str]) -> dict | None:
            board_id = seg[1] if len(seg) > 1 else None
            view_id = seg[2] if len(seg) > 2 else None
            card_id = seg[3] if len(seg) > 3 else None
            if not board_id or not card_id:
                return None
            return {"boardId": board_id, "cardId": card_id, "viewId": view_id, "teamId": None}

        def parse_shared(seg: list[str]) -> dict | None:
            board_id = seg[1] if len(seg) > 1 else None
            view_id = seg[2] if len(seg) > 2 else None
            card_id = seg[3] if len(seg) > 3 else None
            if not board_id or not card_id:
                return None
            return {"boardId": board_id, "cardId": card_id, "viewId": view_id, "teamId": None}

        def parse_workspace(seg: list[str]) -> dict | None:
            nxt = seg[2] if len(seg) > 2 else None
            if not nxt:
                return None
            if nxt.lower() == "shared":
                board_id = seg[3] if len(seg) > 3 else None
                view_id = seg[4] if len(seg) > 4 else None
                card_id = seg[5] if len(seg) > 5 else None
                if not board_id or not card_id:
                    return None
                return {"boardId": board_id, "cardId": card_id, "viewId": view_id, "teamId": None}
            board_id = nxt
            view_id = seg[3] if len(seg) > 3 else None
            card_id = seg[4] if len(seg) > 4 else None
            if not card_id:
                return None
            return {"boardId": board_id, "cardId": card_id, "viewId": view_id, "teamId": None}

        head = segments[0].lower()
        if head == "team":
            return parse_team(segments)
        if head == "board":
            return parse_board(segments)
        if head == "shared":
            return parse_shared(segments)
        if head == "workspace":
            return parse_workspace(segments)
        return None
    except Exception:
        return None


def _boards_get_json(path: str, *, params: dict | None = None) -> object:
    base = _boards_api_base()
    return _http_json(
        "GET",
        f"{base}{path}",
        params=params,
        headers=_auth_headers(extra={"X-Requested-With": "XMLHttpRequest"}),
    )


def _fetch_board(board_id: str) -> dict | None:
    try:
        data = _boards_get_json(f"/boards/{board_id}")
        return data if isinstance(data, dict) else None
    except SystemExit as e:
        if " 404 " in str(e):
            return None
        raise


def _fetch_block_by_id(board_id: str, block_id: str) -> dict | None:
    data = _boards_get_json(f"/boards/{board_id}/blocks", params={"block_id": block_id})
    if isinstance(data, list) and data:
        first = data[0]
        return first if isinstance(first, dict) else None
    return None


def _fetch_blocks_by_parent_id(board_id: str, parent_id: str) -> list[dict]:
    data = _boards_get_json(f"/boards/{board_id}/blocks", params={"parent_id": parent_id})
    if isinstance(data, list):
        return [b for b in data if isinstance(b, dict)]
    return []


def _collect_content_order_ids(element: object, collector: list[str]) -> None:
    if isinstance(element, str):
        collector.append(element)
    elif isinstance(element, list):
        for el in element:
            _collect_content_order_ids(el, collector)


def _extract_content_order(card: dict | None) -> list[str]:
    if not card:
        return []
    fields = card.get("fields")
    if not isinstance(fields, dict):
        return []
    content_order = fields.get("contentOrder")
    if not isinstance(content_order, list):
        return []
    out: list[str] = []
    for el in content_order:
        _collect_content_order_ids(el, out)
    return out


def _fetch_card_contents(board_id: str, card_id: str, content_order: list[str]) -> list[dict]:
    blocks = _fetch_blocks_by_parent_id(board_id, card_id)
    if not blocks:
        return []
    if not content_order:
        return sorted(blocks, key=lambda b: b.get("createAt") or 0)

    by_id = {b.get("id"): b for b in blocks if b.get("id")}
    ordered: list[dict] = []
    seen: set[str] = set()
    for bid in content_order:
        blk = by_id.get(bid)
        if blk is not None:
            ordered.append(blk)
            seen.add(bid)

    for blk in sorted([b for b in blocks if b.get("id") not in seen], key=lambda b: b.get("createAt") or 0):
        ordered.append(blk)
    return ordered


def _build_card_property_values(board: dict | None, card: dict | None) -> list[dict]:
    if not board or not card:
        return []

    fields = card.get("fields")
    if not isinstance(fields, dict):
        return []
    properties_element = fields.get("properties")
    if not isinstance(properties_element, dict) or not properties_element:
        return []

    card_props = board.get("cardProperties")
    if not isinstance(card_props, list):
        card_props = []
    lookup = {p.get("id"): p for p in card_props if isinstance(p, dict) and p.get("id")}

    out: list[dict] = []
    for property_id, value in properties_element.items():
        template = lookup.get(property_id) or {}
        out.append(
            {
                "propertyId": property_id,
                "propertyName": template.get("name"),
                "type": template.get("type"),
                "value": value,
            }
        )
    return out


def cmd_board_card(args: argparse.Namespace) -> None:
    parsed = _parse_board_card_url(args.card_url)
    if not parsed:
        raise SystemExit("[ERROR] Invalid Mattermost Boards card URL.")

    board_id = parsed["boardId"]
    card_id = parsed["cardId"]
    view_id = parsed.get("viewId")

    board = _fetch_board(board_id)
    if not board:
        raise SystemExit("[ERROR] Board not found.")

    card_block = _fetch_block_by_id(board_id, card_id)
    if not card_block:
        raise SystemExit("[ERROR] Card not found.")

    content_order = _extract_content_order(card_block)
    card_contents = _fetch_card_contents(board_id, card_id, content_order)
    view_block = _fetch_block_by_id(board_id, view_id) if view_id else None

    out = {
        "link": {
            "url": args.card_url,
            "boardId": board_id,
            "cardId": card_id,
            "viewId": view_id,
            "teamId": parsed.get("teamId"),
        },
        "board": board,
        "card": card_block,
        "view": view_block,
        "cardContents": card_contents,
        "cardPropertyValues": _build_card_property_values(board, card_block),
    }
    print(json.dumps(out, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Mattermost CLI (no MCP required)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("search-posts", help="Search posts")
    sp.add_argument("--terms", required=True)
    sp.add_argument("--team-id")
    sp.add_argument("--is-or-search", action="store_true", default=False)
    sp.add_argument("--page", type=int, default=0)
    sp.add_argument("--per-page", type=int, default=20)
    sp.add_argument("--include-deleted-channels", action="store_true", default=False)
    sp.add_argument("--time-zone-offset", type=int)
    sp.set_defaults(func=cmd_search_posts)

    sf = sub.add_parser("search-files", help="Search files")
    sf.add_argument("--terms", required=True)
    sf.add_argument("--team-id")
    sf.add_argument("--is-or-search", action="store_true", default=False)
    sf.add_argument("--page", type=int, default=0)
    sf.add_argument("--per-page", type=int, default=20)
    sf.add_argument("--include-deleted-channels", action="store_true", default=False)
    sf.add_argument("--time-zone-offset", type=int)
    sf.set_defaults(func=cmd_search_files)

    t = sub.add_parser("teams", help="Get teams (for current user)")
    t.add_argument("--page", type=int, default=0)
    t.add_argument("--per-page", type=int, default=20)
    t.set_defaults(func=cmd_get_teams)

    ch = sub.add_parser("channels", help="Get channels for a team")
    ch.add_argument("--team-id", required=True)
    ch.add_argument("--page", type=int, default=0)
    ch.add_argument("--per-page", type=int, default=20)
    ch.set_defaults(func=cmd_get_channels)

    u = sub.add_parser("users", help="Get users list")
    u.add_argument("--page", type=int, default=0)
    u.add_argument("--per-page", type=int, default=20)
    u.set_defaults(func=cmd_get_users)

    bc = sub.add_parser("board-card", help="Get Boards card details by URL")
    bc.add_argument("--card-url", required=True)
    bc.set_defaults(func=cmd_board_card)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

