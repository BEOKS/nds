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


def cmd_create(args: argparse.Namespace) -> None:
    base = _api_base()
    project = _encode_project_id(args.project_id)

    description = _read_text_argument(args.description, args.description_file)

    payload: dict = {"title": args.title}
    if description is not None:
        payload["description"] = description
    if args.assignee_ids:
        payload["assignee_ids"] = args.assignee_ids
    if args.milestone_id is not None:
        payload["milestone_id"] = args.milestone_id
    if args.labels:
        payload["labels"] = ",".join(args.labels)
    if args.issue_type:
        payload["issue_type"] = args.issue_type

    raw, _ = _http("POST", f"{base}/projects/{project}/issues", body=payload)
    print(json.dumps(_json(raw), ensure_ascii=False))


def cmd_list(args: argparse.Namespace) -> None:
    base = _api_base()

    params: list[tuple[str, str]] = []

    def add(name: str, value: object | None):
        if value is None:
            return
        params.append((name, str(value)))

    if args.project_id:
        project = _encode_project_id(args.project_id)
        url = f"{base}/projects/{project}/issues"
    else:
        url = f"{base}/issues"

    add("assignee_id", args.assignee_id)
    for u in args.assignee_username or []:
        params.append(("assignee_username[]", u))
    add("author_id", args.author_id)
    add("author_username", args.author_username)
    if args.confidential is not None:
        add("confidential", str(bool(args.confidential)).lower())
    add("created_after", args.created_after)
    add("created_before", args.created_before)
    add("due_date", args.due_date)
    if args.labels:
        add("labels", ",".join(args.labels))
    add("milestone", args.milestone)
    add("issue_type", args.issue_type)
    add("iteration_id", args.iteration_id)
    add("scope", args.scope)
    add("search", args.search)
    add("state", args.state)
    add("updated_after", args.updated_after)
    add("updated_before", args.updated_before)
    add("weight", args.weight)
    add("my_reaction_emoji", args.my_reaction_emoji)
    add("order_by", args.order_by)
    add("sort", args.sort)
    if args.with_labels_details is not None:
        add("with_labels_details", str(bool(args.with_labels_details)).lower())
    add("page", args.page)
    add("per_page", args.per_page)

    for p in args.param or []:
        if "=" not in p:
            raise SystemExit(f"[ERROR] Invalid --param: {p!r} (expected key=value)")
        k, v = p.split("=", 1)
        if not k:
            raise SystemExit(f"[ERROR] Invalid --param: {p!r} (empty key)")
        params.append((k, v))

    raw, headers = _http("GET", url, params=params or None)
    items = _json(raw)
    out = {"items": items, "pagination": _pagination(headers)}
    print(json.dumps(out, ensure_ascii=False))


def cmd_get(args: argparse.Namespace) -> None:
    base = _api_base()
    project = _encode_project_id(args.project_id)
    raw, _ = _http("GET", f"{base}/projects/{project}/issues/{args.issue_iid}")
    print(json.dumps(_json(raw), ensure_ascii=False))


def cmd_update(args: argparse.Namespace) -> None:
    base = _api_base()
    project = _encode_project_id(args.project_id)

    description = _read_text_argument(args.description, args.description_file)

    payload: dict = {}
    if args.title is not None:
        payload["title"] = args.title
    if description is not None:
        payload["description"] = description
    if args.assignee_ids is not None:
        payload["assignee_ids"] = args.assignee_ids
    if args.confidential is not None:
        payload["confidential"] = bool(args.confidential)
    if args.discussion_locked is not None:
        payload["discussion_locked"] = bool(args.discussion_locked)
    if args.due_date is not None:
        payload["due_date"] = args.due_date
    if args.labels is not None:
        payload["labels"] = ",".join(args.labels)
    if args.milestone_id is not None:
        payload["milestone_id"] = args.milestone_id
    if args.state_event is not None:
        payload["state_event"] = args.state_event
    if args.weight is not None:
        payload["weight"] = args.weight
    if args.issue_type is not None:
        payload["issue_type"] = args.issue_type

    raw, _ = _http("PUT", f"{base}/projects/{project}/issues/{args.issue_iid}", body=payload)
    print(json.dumps(_json(raw), ensure_ascii=False))


def cmd_delete(args: argparse.Namespace) -> None:
    base = _api_base()
    project = _encode_project_id(args.project_id)
    _http("DELETE", f"{base}/projects/{project}/issues/{args.issue_iid}")
    print(json.dumps({"message": "Issue deleted successfully"}, ensure_ascii=False))


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
        f"{base}/projects/{project}/issues/{args.issue_iid}/discussions",
        params=params or None,
    )
    items = _json(raw)
    out = {"items": items, "pagination": _pagination(headers)}
    print(json.dumps(out, ensure_ascii=False))


def cmd_create_note(args: argparse.Namespace) -> None:
    base = _api_base()
    project = _encode_project_id(args.project_id)

    payload: dict = {"body": args.body}
    if args.created_at:
        payload["created_at"] = args.created_at

    raw, _ = _http(
        "POST",
        f"{base}/projects/{project}/issues/{args.issue_iid}/discussions/{args.discussion_id}/notes",
        body=payload,
    )
    print(json.dumps(_json(raw), ensure_ascii=False))


def cmd_update_note(args: argparse.Namespace) -> None:
    base = _api_base()
    project = _encode_project_id(args.project_id)

    payload: dict = {"body": args.body}
    raw, _ = _http(
        "PUT",
        f"{base}/projects/{project}/issues/{args.issue_iid}/discussions/{args.discussion_id}/notes/{args.note_id}",
        body=payload,
    )
    print(json.dumps(_json(raw), ensure_ascii=False))


def cmd_list_links(args: argparse.Namespace) -> None:
    base = _api_base()
    project = _encode_project_id(args.project_id)

    raw, _ = _http("GET", f"{base}/projects/{project}/issues/{args.issue_iid}/links")
    print(json.dumps(_json(raw), ensure_ascii=False))


def cmd_get_link(args: argparse.Namespace) -> None:
    base = _api_base()
    project = _encode_project_id(args.project_id)

    raw, _ = _http("GET", f"{base}/projects/{project}/issues/{args.issue_iid}/links/{args.issue_link_id}")
    print(json.dumps(_json(raw), ensure_ascii=False))


def cmd_create_link(args: argparse.Namespace) -> None:
    base = _api_base()
    project = _encode_project_id(args.project_id)

    payload: dict = {
        "target_project_id": args.target_project_id,
        "target_issue_iid": args.target_issue_iid,
    }
    if args.link_type:
        payload["link_type"] = args.link_type

    raw, _ = _http("POST", f"{base}/projects/{project}/issues/{args.issue_iid}/links", body=payload)
    print(json.dumps(_json(raw), ensure_ascii=False))


def cmd_delete_link(args: argparse.Namespace) -> None:
    base = _api_base()
    project = _encode_project_id(args.project_id)
    _http("DELETE", f"{base}/projects/{project}/issues/{args.issue_iid}/links/{args.issue_link_id}")
    print(json.dumps({"message": "Issue link deleted successfully"}, ensure_ascii=False))


def cmd_list_milestones(args: argparse.Namespace) -> None:
    base = _api_base()
    project = _encode_project_id(args.project_id)

    params: list[tuple[str, str]] = []

    def add(name: str, value: object | None):
        if value is None:
            return
        params.append((name, str(value)))

    for iid in args.iids or []:
        params.append(("iids[]", str(iid)))
    add("state", args.state)
    add("title", args.title)
    add("search", args.search)
    if args.include_parent_milestones is not None:
        add("include_parent_milestones", str(bool(args.include_parent_milestones)).lower())
    add("page", args.page)
    add("per_page", args.per_page)

    raw, headers = _http("GET", f"{base}/projects/{project}/milestones", params=params or None)
    items = _json(raw)
    out = {"items": items, "pagination": _pagination(headers)}
    print(json.dumps(out, ensure_ascii=False))


def cmd_get_milestone(args: argparse.Namespace) -> None:
    base = _api_base()
    project = _encode_project_id(args.project_id)
    raw, _ = _http("GET", f"{base}/projects/{project}/milestones/{args.milestone_id}")
    print(json.dumps(_json(raw), ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="GitLab Issues CLI (no MCP required)")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("create", help="Create an issue")
    c.add_argument("--project-id", required=True)
    c.add_argument("--title", required=True)
    c.add_argument("--description")
    c.add_argument("--description-file")
    c.add_argument("--assignee-ids", type=int, action="append")
    c.add_argument("--milestone-id")
    c.add_argument("--labels", action="append")
    c.add_argument("--issue-type", choices=["issue", "incident", "test_case", "task"])
    c.set_defaults(func=cmd_create)

    l = sub.add_parser("list", help="List issues (project scoped or global)")
    l.add_argument("--project-id")
    l.add_argument("--assignee-id")
    l.add_argument("--assignee-username", action="append")
    l.add_argument("--author-id")
    l.add_argument("--author-username")
    l.add_argument("--confidential", action=argparse.BooleanOptionalAction, default=None)
    l.add_argument("--created-after")
    l.add_argument("--created-before")
    l.add_argument("--due-date")
    l.add_argument("--labels", action="append")
    l.add_argument("--milestone")
    l.add_argument("--issue-type")
    l.add_argument("--iteration-id")
    l.add_argument("--scope", choices=["created_by_me", "assigned_to_me", "all"])
    l.add_argument("--search")
    l.add_argument("--state", choices=["opened", "closed", "all"])
    l.add_argument("--updated-after")
    l.add_argument("--updated-before")
    l.add_argument("--weight", type=int)
    l.add_argument("--my-reaction-emoji")
    l.add_argument("--order-by")
    l.add_argument("--sort", choices=["asc", "desc"])
    l.add_argument("--with-labels-details", action=argparse.BooleanOptionalAction, default=None)
    l.add_argument("--page", type=int)
    l.add_argument("--per-page", type=int)
    l.add_argument("--param", action="append", help="Extra query params (key=value)")
    l.set_defaults(func=cmd_list)

    g = sub.add_parser("get", help="Get an issue by IID")
    g.add_argument("--project-id", required=True)
    g.add_argument("--issue-iid", required=True)
    g.set_defaults(func=cmd_get)

    u = sub.add_parser("update", help="Update an issue by IID")
    u.add_argument("--project-id", required=True)
    u.add_argument("--issue-iid", required=True)
    u.add_argument("--title")
    u.add_argument("--description")
    u.add_argument("--description-file")
    u.add_argument("--assignee-ids", type=int, action="append")
    u.add_argument("--confidential", action=argparse.BooleanOptionalAction, default=None)
    u.add_argument("--discussion-locked", action=argparse.BooleanOptionalAction, default=None)
    u.add_argument("--due-date")
    u.add_argument("--labels", action="append")
    u.add_argument("--milestone-id")
    u.add_argument("--state-event")
    u.add_argument("--weight", type=int)
    u.add_argument("--issue-type")
    u.set_defaults(func=cmd_update)

    d = sub.add_parser("delete", help="Delete an issue by IID")
    d.add_argument("--project-id", required=True)
    d.add_argument("--issue-iid", required=True)
    d.set_defaults(func=cmd_delete)

    ds = sub.add_parser("discussions", help="List issue discussions")
    ds.add_argument("--project-id", required=True)
    ds.add_argument("--issue-iid", required=True)
    ds.add_argument("--page", type=int)
    ds.add_argument("--per-page", type=int)
    ds.set_defaults(func=cmd_discussions)

    cn = sub.add_parser("create-note", help="Add a note to an existing issue discussion thread")
    cn.add_argument("--project-id", required=True)
    cn.add_argument("--issue-iid", required=True)
    cn.add_argument("--discussion-id", required=True)
    cn.add_argument("--body", required=True)
    cn.add_argument("--created-at")
    cn.set_defaults(func=cmd_create_note)

    un = sub.add_parser("update-note", help="Update an existing note in an issue discussion thread")
    un.add_argument("--project-id", required=True)
    un.add_argument("--issue-iid", required=True)
    un.add_argument("--discussion-id", required=True)
    un.add_argument("--note-id", required=True)
    un.add_argument("--body", required=True)
    un.set_defaults(func=cmd_update_note)

    ll = sub.add_parser("list-links", help="List issue links")
    ll.add_argument("--project-id", required=True)
    ll.add_argument("--issue-iid", required=True)
    ll.set_defaults(func=cmd_list_links)

    gl = sub.add_parser("get-link", help="Get an issue link")
    gl.add_argument("--project-id", required=True)
    gl.add_argument("--issue-iid", required=True)
    gl.add_argument("--issue-link-id", required=True)
    gl.set_defaults(func=cmd_get_link)

    cl = sub.add_parser("create-link", help="Create an issue link")
    cl.add_argument("--project-id", required=True)
    cl.add_argument("--issue-iid", required=True)
    cl.add_argument("--target-project-id", required=True)
    cl.add_argument("--target-issue-iid", required=True)
    cl.add_argument("--link-type", choices=["relates_to", "blocks", "is_blocked_by"])
    cl.set_defaults(func=cmd_create_link)

    dl = sub.add_parser("delete-link", help="Delete an issue link")
    dl.add_argument("--project-id", required=True)
    dl.add_argument("--issue-iid", required=True)
    dl.add_argument("--issue-link-id", required=True)
    dl.set_defaults(func=cmd_delete_link)

    lm = sub.add_parser("list-milestones", help="List project milestones")
    lm.add_argument("--project-id", required=True)
    lm.add_argument("--iids", type=int, action="append", help="Filter by milestone IIDs")
    lm.add_argument("--state", choices=["active", "closed"])
    lm.add_argument("--title")
    lm.add_argument("--search")
    lm.add_argument("--include-parent-milestones", action=argparse.BooleanOptionalAction, default=None)
    lm.add_argument("--page", type=int)
    lm.add_argument("--per-page", type=int)
    lm.set_defaults(func=cmd_list_milestones)

    gm = sub.add_parser("get-milestone", help="Get a milestone by ID")
    gm.add_argument("--project-id", required=True)
    gm.add_argument("--milestone-id", required=True)
    gm.set_defaults(func=cmd_get_milestone)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
