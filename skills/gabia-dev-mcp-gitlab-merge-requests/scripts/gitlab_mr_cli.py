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
    return (_env("GITLAB_API_URL") or "https://gitlab.gabia.com/api/v4").rstrip("/")


def _auth_headers() -> dict[str, str]:
    token = _require_env("GITLAB_TOKEN")
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "PRIVATE-TOKEN": token,
    }


def _encode_project_id(project_id: str) -> str:
    decoded = urllib.parse.unquote(project_id)
    return urllib.parse.quote(decoded, safe="")


def _http(method: str, url: str, *, params: list[tuple[str, str]] | None = None, body: dict | None = None) -> tuple[bytes, dict[str, str]]:
    if params:
        qs = urllib.parse.urlencode(params, doseq=True)
        sep = "&" if ("?" in url) else "?"
        url = f"{url}{sep}{qs}"

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=_auth_headers(), method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            headers = {k.lower(): v for k, v in resp.headers.items()}
            return raw, headers
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"[ERROR] GitLab API error: {e.code} {e.reason}\n{err_body}") from None
    except urllib.error.URLError as e:
        raise SystemExit(f"[ERROR] Network error: {e}") from None


def _json(raw: bytes) -> object:
    return json.loads(raw.decode("utf-8"))


def _pagination(headers: dict[str, str]) -> dict:
    def to_int(name: str, default: int) -> int:
        v = headers.get(name)
        try:
            return int(v) if v is not None else default
        except ValueError:
            return default

    return {
        "page": to_int("x-page", 1),
        "per_page": to_int("x-per-page", 20),
        "total": to_int("x-total", 0),
        "total_pages": to_int("x-total-pages", 0),
    }


def _read_text_argument(value: str | None, file_path: str | None) -> str | None:
    if value is not None:
        return value
    if file_path is not None:
        return open(file_path, "r", encoding="utf-8").read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return None


def cmd_get(args: argparse.Namespace) -> None:
    base = _api_base()
    project = _encode_project_id(args.project_id)

    if not args.merge_request_id and not args.source_branch:
        raise SystemExit("[ERROR] Provide --merge-request-id or --source-branch.")

    if args.merge_request_id:
        raw, _ = _http("GET", f"{base}/projects/{project}/merge_requests/{args.merge_request_id}")
        print(json.dumps(_json(raw), ensure_ascii=False))
        return

    # Search by source branch
    raw, _ = _http(
        "GET",
        f"{base}/projects/{project}/merge_requests",
        params=[("source_branch", args.source_branch)],
    )
    data = _json(raw)
    if isinstance(data, list) and data:
        print(json.dumps(data[0], ensure_ascii=False))
        return
    print(json.dumps(None, ensure_ascii=False))


def cmd_diffs(args: argparse.Namespace) -> None:
    base = _api_base()
    project = _encode_project_id(args.project_id)

    iid = args.merge_request_id
    if not iid:
        # resolve iid by source_branch
        raw, _ = _http("GET", f"{base}/projects/{project}/merge_requests", params=[("source_branch", args.source_branch)])
        data = _json(raw)
        if not (isinstance(data, list) and data):
            raise SystemExit("[ERROR] No merge request found for the given --source-branch.")
        iid = str(data[0].get("iid"))

    params: list[tuple[str, str]] = []
    if args.view:
        params.append(("view", args.view))
    raw, _ = _http("GET", f"{base}/projects/{project}/merge_requests/{iid}/changes", params=params or None)
    obj = _json(raw)
    if isinstance(obj, dict) and "changes" in obj:
        print(json.dumps(obj["changes"], ensure_ascii=False))
    else:
        print(json.dumps(obj, ensure_ascii=False))


def cmd_discussions(args: argparse.Namespace) -> None:
    base = _api_base()
    project = _encode_project_id(args.project_id)

    params: list[tuple[str, str]] = []
    if args.page is not None:
        params.append(("page", str(args.page)))
    if args.per_page is not None:
        params.append(("per_page", str(args.per_page)))

    raw, headers = _http(
        "GET",
        f"{base}/projects/{project}/merge_requests/{args.merge_request_id}/discussions",
        params=params or None,
    )
    items = _json(raw)
    out = {"items": items, "pagination": _pagination(headers)}
    print(json.dumps(out, ensure_ascii=False))


def cmd_create(args: argparse.Namespace) -> None:
    base = _api_base()
    project = _encode_project_id(args.project_id)

    description = _read_text_argument(args.description, args.description_file)

    payload: dict = {
        "title": args.title,
        "source_branch": args.source_branch,
        "target_branch": args.target_branch,
    }
    if description is not None:
        payload["description"] = description
    if args.target_project_id is not None:
        payload["target_project_id"] = args.target_project_id
    if args.assignee_ids:
        payload["assignee_ids"] = args.assignee_ids
    if args.reviewer_ids:
        payload["reviewer_ids"] = args.reviewer_ids
    if args.labels:
        payload["labels"] = ",".join(args.labels)
    if args.draft is not None:
        payload["draft"] = bool(args.draft)
    if args.allow_collaboration is not None:
        payload["allow_collaboration"] = bool(args.allow_collaboration)
    if args.remove_source_branch is not None:
        payload["remove_source_branch"] = bool(args.remove_source_branch)
    if args.squash is not None:
        payload["squash"] = bool(args.squash)

    raw, _ = _http("POST", f"{base}/projects/{project}/merge_requests", body=payload)
    print(json.dumps(_json(raw), ensure_ascii=False))


def cmd_list(args: argparse.Namespace) -> None:
    base = _api_base()
    project = _encode_project_id(args.project_id)

    params: list[tuple[str, str]] = []

    def add(name: str, value: object | None):
        if value is None:
            return
        params.append((name, str(value)))

    add("assignee_id", args.assignee_id)
    add("assignee_username", args.assignee_username)
    add("author_id", args.author_id)
    add("author_username", args.author_username)
    add("reviewer_id", args.reviewer_id)
    add("reviewer_username", args.reviewer_username)
    add("created_after", args.created_after)
    add("created_before", args.created_before)
    add("updated_after", args.updated_after)
    add("updated_before", args.updated_before)
    if args.labels:
        add("labels", ",".join(args.labels))
    add("milestone", args.milestone)
    add("scope", args.scope)
    add("search", args.search)
    add("state", args.state)
    add("wip", args.wip)
    add("with_merge_status_recheck", args.with_merge_status_recheck)
    add("order_by", args.order_by)
    add("sort", args.sort)
    add("view", args.view)
    add("my_reaction_emoji", args.my_reaction_emoji)
    add("source_branch", args.source_branch)
    add("target_branch", args.target_branch)
    add("page", args.page)
    add("per_page", args.per_page)

    for p in args.param or []:
        if "=" not in p:
            raise SystemExit(f"[ERROR] Invalid --param: {p!r} (expected key=value)")
        k, v = p.split("=", 1)
        if not k:
            raise SystemExit(f"[ERROR] Invalid --param: {p!r} (empty key)")
        params.append((k, v))

    raw, headers = _http("GET", f"{base}/projects/{project}/merge_requests", params=params or None)
    items = _json(raw)
    out = {"items": items, "pagination": _pagination(headers)}
    print(json.dumps(out, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="GitLab Merge Requests CLI (no MCP required)")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("get", help="Get merge request details")
    g.add_argument("--project-id", required=True)
    g.add_argument("--merge-request-id")
    g.add_argument("--source-branch")
    g.set_defaults(func=cmd_get)

    d = sub.add_parser("diffs", help="Get merge request diffs/changes")
    d.add_argument("--project-id", required=True)
    d.add_argument("--merge-request-id")
    d.add_argument("--source-branch")
    d.add_argument("--view", choices=["inline", "parallel"])
    d.set_defaults(func=cmd_diffs)

    ds = sub.add_parser("discussions", help="List merge request discussions")
    ds.add_argument("--project-id", required=True)
    ds.add_argument("--merge-request-id", required=True)
    ds.add_argument("--page", type=int)
    ds.add_argument("--per-page", type=int)
    ds.set_defaults(func=cmd_discussions)

    c = sub.add_parser("create", help="Create a merge request")
    c.add_argument("--project-id", required=True)
    c.add_argument("--source-branch", required=True)
    c.add_argument("--target-branch", required=True)
    c.add_argument("--title", required=True)
    c.add_argument("--description")
    c.add_argument("--description-file")
    c.add_argument("--target-project-id", type=int)
    c.add_argument("--assignee-ids", type=int, action="append")
    c.add_argument("--reviewer-ids", type=int, action="append")
    c.add_argument("--labels", action="append")
    c.add_argument("--draft", action=argparse.BooleanOptionalAction, default=None)
    c.add_argument("--allow-collaboration", action=argparse.BooleanOptionalAction, default=None)
    c.add_argument("--remove-source-branch", action=argparse.BooleanOptionalAction, default=None)
    c.add_argument("--squash", action=argparse.BooleanOptionalAction, default=None)
    c.set_defaults(func=cmd_create)

    l = sub.add_parser("list", help="List merge requests with filtering options")
    l.add_argument("--project-id", required=True)
    l.add_argument("--assignee-id")
    l.add_argument("--assignee-username")
    l.add_argument("--author-id")
    l.add_argument("--author-username")
    l.add_argument("--reviewer-id")
    l.add_argument("--reviewer-username")
    l.add_argument("--created-after")
    l.add_argument("--created-before")
    l.add_argument("--updated-after")
    l.add_argument("--updated-before")
    l.add_argument("--labels", action="append")
    l.add_argument("--milestone")
    l.add_argument("--scope")
    l.add_argument("--search")
    l.add_argument("--state")
    l.add_argument("--wip")
    l.add_argument("--with-merge-status-recheck")
    l.add_argument("--order-by")
    l.add_argument("--sort")
    l.add_argument("--view")
    l.add_argument("--my-reaction-emoji")
    l.add_argument("--source-branch")
    l.add_argument("--target-branch")
    l.add_argument("--page", type=int)
    l.add_argument("--per-page", type=int)
    l.add_argument("--param", action="append", help="Extra query params (key=value)")
    l.set_defaults(func=cmd_list)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

