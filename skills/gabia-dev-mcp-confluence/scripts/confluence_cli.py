#!/usr/bin/env python3
import argparse
import base64
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request


def _env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _require_env(name: str) -> str:
    value = _env(name)
    if not value:
        raise SystemExit(f"[ERROR] Missing required env: {name}")
    return value


def _build_auth_header() -> str:
    bearer = _env("ATLASSIAN_OAUTH_ACCESS_TOKEN")
    if bearer:
        return f"Bearer {bearer}"

    user = _env("CONFLUENCE_USERNAME") or _env("ATLASSIAN_EMAIL")
    token = _env("CONFLUENCE_API_TOKEN") or _env("ATLASSIAN_API_TOKEN")
    if user and token:
        raw = f"{user}:{token}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")

    raise SystemExit(
        "[ERROR] Missing Confluence auth. Set one of:\n"
        "  - ATLASSIAN_OAUTH_ACCESS_TOKEN\n"
        "  - CONFLUENCE_USERNAME + CONFLUENCE_API_TOKEN\n"
        "  - ATLASSIAN_EMAIL + ATLASSIAN_API_TOKEN"
    )


def _http_json(method: str, url: str, *, params: dict | None = None, body: dict | None = None) -> dict:
    if params:
        qs = urllib.parse.urlencode(params, doseq=True)
        sep = "&" if ("?" in url) else "?"
        url = f"{url}{sep}{qs}"

    headers = {
        "Accept": "application/json",
        "Authorization": _build_auth_header(),
    }

    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"[ERROR] Confluence API error: {e.code} {e.reason}\n{err_body}") from None
    except urllib.error.URLError as e:
        raise SystemExit(f"[ERROR] Network error: {e}") from None


def wrap_simple_query_to_cql(query: str) -> str:
    is_cql = any(x in query for x in ["=", "~", ">", "<", " AND ", " OR ", "currentUser()"])
    if is_cql:
        return query
    term = query.replace('"', '\\"')
    return f'siteSearch ~ "{term}"'


def apply_spaces_filter(cql: str, spaces_filter: str | None) -> str:
    if not spaces_filter:
        return cql
    keys = [k.strip() for k in spaces_filter.split(",") if k.strip()]
    if not keys:
        return cql
    clause = " OR ".join([f'space = "{k}"' for k in keys])
    return f"({clause}) AND ({cql})"


def to_simple_results(payload: dict, base_url: str | None) -> list[dict]:
    results = payload.get("results") or []
    simplified: list[dict] = []
    for item in results:
        title = item.get("title") or (item.get("content") or {}).get("title")
        content_id = item.get("id") or (item.get("content") or {}).get("id") or (item.get("content") or {}).get("_id")
        excerpt = item.get("excerpt") or (item.get("content") or {}).get("excerpt")
        space_key = (item.get("space") or {}).get("key") or ((item.get("content") or {}).get("space") or {}).get("key")

        url = None
        if base_url and content_id and space_key:
            url = f"{base_url}/spaces/{space_key}/pages/{content_id}"

        simplified.append(
            {
                "id": content_id,
                "title": title,
                "spaceKey": space_key,
                "url": url,
                "excerpt": excerpt,
            }
        )
    return simplified


def markdown_to_storage(markdown: str) -> str:
    def escape_html(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def render_inline(raw: str) -> str:
        s = escape_html(raw)
        s = re.sub(
            r"\[([^]]+)\]\(([^)]+)\)",
            lambda m: f'<a href="{escape_html(m.group(2))}">{m.group(1)}</a>',
            s,
        )
        s = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", s)
        s = re.sub(r"\*\*([^*]+)\*\*", lambda m: f"<strong>{m.group(1)}</strong>", s)
        s = re.sub(r"__([^_]+)__", lambda m: f"<strong>{m.group(1)}</strong>", s)
        s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", lambda m: f"<em>{m.group(1)}</em>", s)
        s = re.sub(r"(?<!_)_([^_]+)_(?!_ )", lambda m: f"<em>{m.group(1)}</em>", s)
        return s

    lines = markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []

    i = 0
    in_ul = False
    in_ol = False
    in_para = False
    in_quote = False
    in_code = False

    def close_para():
        nonlocal in_para
        if in_para:
            out.append("</p>")
            in_para = False

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    def close_quote():
        nonlocal in_quote
        if in_quote:
            out.append("</blockquote>")
            in_quote = False

    def is_separator_row(s: str) -> bool:
        return bool(re.match(r"^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$", s.strip()))

    def parse_cells(s: str) -> list[str]:
        return [c.strip() for c in s.strip().strip("|").split("|")]

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip("\n").rstrip()

        if not in_code and re.match(r"^```.*$", line):
            close_para()
            close_lists()
            close_quote()
            in_code = True
            out.append("<pre><code>")
            i += 1
            continue

        if in_code:
            if line == "```":
                out.append("</code></pre>")
                in_code = False
            else:
                out.append(escape_html(raw))
            i += 1
            continue

        if not line.strip():
            close_para()
            close_lists()
            close_quote()
            i += 1
            continue

        # Table: header + separator
        if "|" in line and i + 1 < len(lines) and is_separator_row(lines[i + 1]):
            close_para()
            close_lists()
            close_quote()
            header = parse_cells(line)
            i += 2
            rows: list[list[str]] = []
            while i < len(lines) and ("|" in lines[i]) and (not lines[i].lstrip().startswith("#")):
                rows.append(parse_cells(lines[i]))
                i += 1
            out.append("<table>")
            out.append("<thead><tr>" + "".join(f"<th>{render_inline(h)}</th>" for h in header) + "</tr></thead>")
            out.append("<tbody>")
            for r in rows:
                out.append("<tr>" + "".join(f"<td>{render_inline(c)}</td>" for c in r) + "</tr>")
            out.append("</tbody>")
            out.append("</table>")
            continue

        # Horizontal rule
        if re.match(r"^\s*(\*{3,}|-{3,}|_{3,})\s*$", line):
            close_para()
            close_lists()
            close_quote()
            out.append("<hr/>")
            i += 1
            continue

        # Headings
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            close_para()
            close_lists()
            close_quote()
            level = len(m.group(1))
            text = m.group(2)
            out.append(f"<h{level}>{render_inline(text)}</h{level}>")
            i += 1
            continue

        # Blockquote
        if line.startswith(">"):
            if not in_quote:
                close_para()
                close_lists()
                out.append("<blockquote>")
                in_quote = True
            quote_text = line[1:].lstrip()
            if not in_para:
                out.append("<p>")
                in_para = True
            out.append(render_inline(quote_text) + " ")
            i += 1
            continue
        else:
            close_quote()

        # Lists
        m_ul = re.match(r"^[-*]\s+(.+)$", line)
        m_ol = re.match(r"^\d+\.\s+(.+)$", line)
        if m_ul:
            if not in_ul:
                close_para()
                if in_ol:
                    out.append("</ol>")
                    in_ol = False
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{render_inline(m_ul.group(1))}</li>")
            i += 1
            continue
        if m_ol:
            if not in_ol:
                close_para()
                if in_ul:
                    out.append("</ul>")
                    in_ul = False
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{render_inline(m_ol.group(1))}</li>")
            i += 1
            continue

        if not in_para:
            out.append("<p>")
            in_para = True
        out.append(render_inline(line) + " ")
        i += 1

    close_para()
    close_lists()
    close_quote()
    return "\n".join(out).strip()


def html_to_markdown_light(html: str) -> str:
    text = html
    flags = re.IGNORECASE | re.DOTALL
    text = re.sub(r"<h1[^>]*>(.*?)</h1>", r"# \1\n\n", text, flags=flags)
    text = re.sub(r"<h2[^>]*>(.*?)</h2>", r"## \1\n\n", text, flags=flags)
    text = re.sub(r"<h3[^>]*>(.*?)</h3>", r"### \1\n\n", text, flags=flags)
    text = re.sub(r"<p[^>]*>(.*?)</p>", r"\1\n\n", text, flags=flags)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", text, flags=flags)
    text = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", text, flags=flags)
    text = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", text, flags=flags)
    text = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", text, flags=flags)
    text = re.sub(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"[\2](\1)", text, flags=flags)
    text = re.sub(r"<li[^>]*>(.*?)</li>", r"- \1\n", text, flags=flags)
    text = re.sub(r"</?ul[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?ol[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<pre[^>]*><code[^>]*>(.*?)</code></pre>", r"```\n\1\n```", text, flags=flags)
    text = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", text, flags=flags)
    text = re.sub(r"<[^>]+>", "", text, flags=re.DOTALL)
    return text.strip()


def _resolve_page_id(raw: str) -> str:
    """Extract page_id from a raw string that may be an ID or a Confluence URL."""
    if raw.isdigit():
        return raw
    m = re.search(r"/pages/(\d+)", raw)
    if m:
        return m.group(1)
    return raw


def _read_text_argument(value: str | None, file_path: str | None) -> str:
    if value is not None:
        return value
    if file_path is not None:
        return open(file_path, "r", encoding="utf-8").read()
    if not sys.stdin.isatty():
        return sys.stdin.read()
    raise SystemExit("[ERROR] Provide --content/--content-file or pipe content via stdin.")


def cmd_search(args: argparse.Namespace) -> None:
    base_url = _require_env("CONFLUENCE_BASE_URL").rstrip("/")
    query = args.query
    limit = max(1, min(50, args.limit))

    env_spaces = _env("CONFLUENCE_SPACES_FILTER")
    if args.spaces_filter is None:
        effective_spaces = env_spaces
    elif args.spaces_filter == "":
        effective_spaces = None
    else:
        effective_spaces = args.spaces_filter

    cql = apply_spaces_filter(wrap_simple_query_to_cql(query), effective_spaces)
    payload = _http_json("GET", f"{base_url}/rest/api/search", params={"cql": cql, "limit": str(limit)})
    print(json.dumps(to_simple_results(payload, base_url), ensure_ascii=False))


def _get_page_by_id(base_url: str, page_id: str, expand: str | None) -> dict:
    params = {"expand": expand} if expand else None
    return _http_json("GET", f"{base_url}/rest/api/content/{page_id}", params=params)


def _get_page_by_title(base_url: str, space_key: str, title: str, expand: str | None) -> dict:
    params = {"spaceKey": space_key, "title": title}
    if expand:
        params["expand"] = expand
    obj = _http_json("GET", f"{base_url}/rest/api/content", params=params)
    results = obj.get("results") or []
    if not results:
        raise SystemExit("[ERROR] Page not found by title + space_key.")
    return results[0]


def _get_labels(base_url: str, page_id: str) -> list[str]:
    obj = _http_json("GET", f"{base_url}/rest/api/content/{page_id}/label")
    results = obj.get("results") or []
    out: list[str] = []
    for r in results:
        name = r.get("name")
        if name:
            out.append(name)
    return out


def _extract_body(page_obj: dict, *, output_format: str) -> tuple[str, str]:
    """Extract body content in the requested format.

    Args:
        page_obj: The page object from Confluence API
        output_format: One of 'storage', 'html', 'markdown'

    Returns:
        Tuple of (format_name, body_content)
    """
    body = page_obj.get("body") or {}
    export_view = ((body.get("export_view") or {}) if isinstance(body, dict) else {}).get("value")
    storage = ((body.get("storage") or {}) if isinstance(body, dict) else {}).get("value")

    if output_format == "storage":
        return "storage", storage or ""
    elif output_format == "markdown":
        html = export_view or storage or ""
        return "markdown", html_to_markdown_light(html)
    else:  # html (default)
        return "html", export_view or storage or ""


def _build_page_url(base_url: str, space_key: str | None, page_id: str | None) -> str | None:
    if not (base_url and space_key and page_id):
        return None
    return f"{base_url}/spaces/{space_key}/pages/{page_id}"


def cmd_get(args: argparse.Namespace) -> None:
    base_url = _require_env("CONFLUENCE_BASE_URL").rstrip("/")

    if not args.page_id and not (args.title and args.space_key):
        raise SystemExit("[ERROR] Provide --page-id or (--title and --space-key).")

    include_metadata = args.include_metadata

    # Determine output format (priority: --output-format > --convert-to-markdown > default html)
    if args.output_format:
        output_format = args.output_format
    elif args.convert_to_markdown:
        output_format = "markdown"
    else:
        output_format = "html"

    expand_with_meta = "body.export_view,body.storage,version,space,history"
    expand_no_meta = "body.export_view,body.storage"
    expand = expand_with_meta if include_metadata else expand_no_meta

    if args.page_id:
        page_obj = _get_page_by_id(base_url, _resolve_page_id(args.page_id), expand)
    else:
        page_obj = _get_page_by_title(base_url, args.space_key, args.title, expand)

    page_id = page_obj.get("id")
    space_key = ((page_obj.get("space") or {}) if isinstance(page_obj.get("space"), dict) else {}).get("key")
    title = page_obj.get("title")

    labels: list[str] = []
    if include_metadata and page_id:
        labels = _get_labels(base_url, str(page_id))

    fmt, body_text = _extract_body(page_obj, output_format=output_format)
    url = _build_page_url(base_url, space_key, str(page_id) if page_id is not None else None)

    version = page_obj.get("version") or {}
    history = page_obj.get("history") or {}
    created_at = history.get("createdDate") if isinstance(history, dict) else None
    last_updated_at = None
    if isinstance(history, dict):
        last_updated = history.get("lastUpdated") or {}
        if isinstance(last_updated, dict):
            last_updated_at = last_updated.get("when")

    out = {
        "id": str(page_id) if page_id is not None else None,
        "title": title,
        "spaceKey": space_key,
        "url": url,
        "format": fmt,
        "body": body_text,
        "version": {
            "number": (version.get("number") if isinstance(version, dict) else None),
            "when": (version.get("when") if isinstance(version, dict) else None),
            "by": (((version.get("by") or {}) if isinstance(version, dict) else {}).get("displayName")),
        },
        "labels": labels,
        "createdAt": created_at,
        "lastUpdatedAt": last_updated_at,
    }
    print(json.dumps(out, ensure_ascii=False))


def _normalize_body(content: str, fmt: str) -> tuple[str, str]:
    f = (fmt or "markdown").lower()
    if f == "storage":
        return content, "storage"
    if f == "wiki":
        return content, "wiki"
    return markdown_to_storage(content), "storage"


def cmd_create(args: argparse.Namespace) -> None:
    base_url = _require_env("CONFLUENCE_BASE_URL").rstrip("/")
    content = _read_text_argument(args.content, args.content_file)
    body_value, representation = _normalize_body(content, args.format)

    payload = {
        "type": "page",
        "title": args.title,
        "space": {"key": args.space},
        "body": {"storage": {"value": body_value, "representation": representation}},
    }
    if args.parent_id:
        payload["ancestors"] = [{"id": args.parent_id}]

    created = _http_json("POST", f"{base_url}/rest/api/content", body=payload)
    print(json.dumps(created, ensure_ascii=False))


def cmd_update(args: argparse.Namespace) -> None:
    base_url = _require_env("CONFLUENCE_BASE_URL").rstrip("/")
    content = _read_text_argument(args.content, args.content_file)
    body_value, representation = _normalize_body(content, args.format)

    current = _get_page_by_id(base_url, _resolve_page_id(args.page_id), "version,ancestors")
    current_version = ((current.get("version") or {}) if isinstance(current.get("version"), dict) else {}).get("number") or 1
    new_version = int(current_version) + 1

    payload = {
        "id": args.page_id,
        "type": "page",
        "title": args.title,
        "body": {"storage": {"value": body_value, "representation": representation}},
        "version": {"number": new_version, "minorEdit": bool(args.minor_edit)},
    }
    if args.version_comment:
        payload["version"]["message"] = args.version_comment
    if args.parent_id:
        payload["ancestors"] = [{"id": args.parent_id}]

    page_id = _resolve_page_id(args.page_id)
    updated = _http_json("PUT", f"{base_url}/rest/api/content/{page_id}", body=payload)
    print(json.dumps(updated, ensure_ascii=False))


def cmd_delete(args: argparse.Namespace) -> None:
    base_url = _require_env("CONFLUENCE_BASE_URL").rstrip("/")
    page_id = _resolve_page_id(args.page_id)
    _http_json("DELETE", f"{base_url}/rest/api/content/{page_id}")
    print(json.dumps({"success": True, "page_id": page_id}, ensure_ascii=False))


def cmd_comments(args: argparse.Namespace) -> None:
    """List comments on a Confluence page."""
    base_url = _require_env("CONFLUENCE_BASE_URL").rstrip("/")
    page_id = _resolve_page_id(args.page_id)
    limit = max(1, min(100, args.limit))

    url = f"{base_url}/rest/api/content/{page_id}/child/comment"
    params = {
        "expand": "body.storage,version",
        "limit": str(limit),
    }
    payload = _http_json("GET", url, params=params)

    comments: list[dict] = []
    for c in payload.get("results") or []:
        version = c.get("version") or {}
        by = version.get("by") or {}
        comments.append({
            "id": c.get("id"),
            "body": (c.get("body") or {}).get("storage", {}).get("value", ""),
            "version": version.get("number"),
            "author": by.get("displayName"),
            "authorUsername": by.get("username"),
            "createdAt": version.get("when"),
        })

    print(json.dumps(comments, ensure_ascii=False))


def cmd_comment(args: argparse.Namespace) -> None:
    base_url = _require_env("CONFLUENCE_BASE_URL").rstrip("/")
    page_id = _resolve_page_id(args.page_id)
    content = _read_text_argument(args.content, args.content_file)
    body_value, representation = _normalize_body(content, args.format)

    payload = {
        "type": "comment",
        "container": {"type": "page", "id": page_id},
        "body": {"storage": {"value": body_value, "representation": representation}},
    }
    created = _http_json("POST", f"{base_url}/rest/api/content", body=payload)
    print(json.dumps(created, ensure_ascii=False))


def cmd_comment_update(args: argparse.Namespace) -> None:
    """Update an existing comment."""
    base_url = _require_env("CONFLUENCE_BASE_URL").rstrip("/")
    content = _read_text_argument(args.content, args.content_file)
    body_value, representation = _normalize_body(content, args.format)

    # Get current comment version
    current = _http_json("GET", f"{base_url}/rest/api/content/{args.comment_id}", params={"expand": "version"})
    current_version = ((current.get("version") or {}) if isinstance(current.get("version"), dict) else {}).get("number") or 1

    payload = {
        "id": args.comment_id,
        "type": "comment",
        "version": {"number": int(current_version) + 1},
        "body": {"storage": {"value": body_value, "representation": representation}},
    }
    updated = _http_json("PUT", f"{base_url}/rest/api/content/{args.comment_id}", body=payload)
    print(json.dumps(updated, ensure_ascii=False))


def cmd_comment_delete(args: argparse.Namespace) -> None:
    """Delete a comment."""
    base_url = _require_env("CONFLUENCE_BASE_URL").rstrip("/")
    _http_json("DELETE", f"{base_url}/rest/api/content/{args.comment_id}")
    print(json.dumps({"success": True, "comment_id": args.comment_id}, ensure_ascii=False))


def cmd_attachments(args: argparse.Namespace) -> None:
    """List attachments for a Confluence page."""
    base_url = _require_env("CONFLUENCE_BASE_URL").rstrip("/")

    if not args.page_id:
        raise SystemExit("[ERROR] Provide --page-id.")

    page_id = _resolve_page_id(args.page_id)
    url = f"{base_url}/rest/api/content/{page_id}/child/attachment"
    params = {"limit": str(args.limit)} if args.limit else None
    payload = _http_json("GET", url, params=params)

    results = payload.get("results") or []
    attachments: list[dict] = []
    for att in results:
        att_id = att.get("id")
        title = att.get("title")
        media_type = att.get("metadata", {}).get("mediaType") or att.get("extensions", {}).get("mediaType")
        file_size = att.get("extensions", {}).get("fileSize")
        download_link = att.get("_links", {}).get("download")

        attachments.append({
            "id": att_id,
            "title": title,
            "mediaType": media_type,
            "fileSize": file_size,
            "downloadPath": download_link,
            "downloadUrl": f"{base_url}{download_link}" if download_link else None,
        })

    print(json.dumps(attachments, ensure_ascii=False))


def _http_download(url: str, output_path: str) -> int:
    """Download a file from URL to output_path. Returns bytes written."""
    headers = {
        "Authorization": _build_auth_header(),
    }
    req = urllib.request.Request(url, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            with open(output_path, "wb") as f:
                total = 0
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    total += len(chunk)
                return total
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise SystemExit(f"[ERROR] Download failed: {e.code} {e.reason}\n{err_body}") from None
    except urllib.error.URLError as e:
        raise SystemExit(f"[ERROR] Network error during download: {e}") from None


def cmd_download(args: argparse.Namespace) -> None:
    """Download attachment(s) from a Confluence page."""
    base_url = _require_env("CONFLUENCE_BASE_URL").rstrip("/")

    if not args.page_id:
        raise SystemExit("[ERROR] Provide --page-id.")

    # Get attachments list
    page_id = _resolve_page_id(args.page_id)
    url = f"{base_url}/rest/api/content/{page_id}/child/attachment"
    payload = _http_json("GET", url, params={"limit": "100"})
    results = payload.get("results") or []

    if not results:
        raise SystemExit("[ERROR] No attachments found for this page.")

    # Filter by filename if specified (case-insensitive, partial match supported)
    # Unicode normalization for Korean filenames (NFC vs NFD)
    def normalize(s: str) -> str:
        return unicodedata.normalize("NFC", s) if s else ""

    if args.filename:
        search_term = normalize(args.filename.lower())
        filtered = [att for att in results if att.get("title") and search_term in normalize(att.get("title", "").lower())]
        # Try exact match first
        exact = [att for att in results if normalize(att.get("title") or "") == normalize(args.filename)]
        results = exact if exact else filtered
        if not results:
            available = [att.get("title") for att in payload.get("results") or []]
            raise SystemExit(f"[ERROR] Attachment not found: {args.filename}\nAvailable: {available}")

    # Determine output directory
    output_dir = args.output_dir or "."
    os.makedirs(output_dir, exist_ok=True)

    downloaded: list[dict] = []
    for att in results:
        title = att.get("title")
        download_link = att.get("_links", {}).get("download")
        if not download_link:
            continue

        download_url = f"{base_url}{download_link}"
        output_path = os.path.join(output_dir, title)

        # Handle filename conflicts
        if os.path.exists(output_path) and not args.overwrite:
            base_name, ext = os.path.splitext(title)
            counter = 1
            while os.path.exists(output_path):
                output_path = os.path.join(output_dir, f"{base_name}_{counter}{ext}")
                counter += 1

        bytes_written = _http_download(download_url, output_path)
        downloaded.append({
            "filename": title,
            "savedAs": output_path,
            "size": bytes_written,
        })

    print(json.dumps({"success": True, "downloaded": downloaded}, ensure_ascii=False))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Confluence CLI (no MCP required)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="Search Confluence (simple text or CQL)")
    s.add_argument("--query", required=True)
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--spaces-filter", default=None, help="Comma-separated space keys. Use empty string to disable.")
    s.set_defaults(func=cmd_search)

    g = sub.add_parser("get", help="Get a Confluence page by page_id or (title + space_key)")
    g.add_argument("--page-id")
    g.add_argument("--title")
    g.add_argument("--space-key")
    g.add_argument("--include-metadata", action=argparse.BooleanOptionalAction, default=True)
    g.add_argument("--output-format", choices=["html", "storage", "markdown"],
                   help="Output format: html (rendered), storage (raw XML with macros), markdown")
    g.add_argument("--convert-to-markdown", action=argparse.BooleanOptionalAction, default=False,
                   help="(Deprecated) Use --output-format markdown instead")
    g.set_defaults(func=cmd_get)

    c = sub.add_parser("create", help="Create a Confluence page")
    c.add_argument("--space", required=True)
    c.add_argument("--title", required=True)
    c.add_argument("--parent-id")
    c.add_argument("--format", default="storage", choices=["markdown", "wiki", "storage"])
    c.add_argument("--content")
    c.add_argument("--content-file")
    c.set_defaults(func=cmd_create)

    u = sub.add_parser("update", help="Update a Confluence page by page_id")
    u.add_argument("--page-id", required=True)
    u.add_argument("--title", required=True)
    u.add_argument("--minor-edit", action="store_true", default=False)
    u.add_argument("--version-comment")
    u.add_argument("--parent-id")
    u.add_argument("--format", default="storage", choices=["markdown", "wiki", "storage"])
    u.add_argument("--content")
    u.add_argument("--content-file")
    u.set_defaults(func=cmd_update)

    d = sub.add_parser("delete", help="Delete a Confluence page by page_id")
    d.add_argument("--page-id", required=True)
    d.set_defaults(func=cmd_delete)

    cms = sub.add_parser("comments", help="List comments on a Confluence page")
    cms.add_argument("--page-id", required=True, help="Page ID or Confluence URL")
    cms.add_argument("--limit", type=int, default=25, help="Max number of comments to return")
    cms.set_defaults(func=cmd_comments)

    cm = sub.add_parser("comment", help="Add a comment to a Confluence page")
    cm.add_argument("--page-id", required=True, help="Page ID or Confluence URL")
    cm.add_argument("--format", default="storage", choices=["markdown", "wiki", "storage"])
    cm.add_argument("--content")
    cm.add_argument("--content-file")
    cm.set_defaults(func=cmd_comment)

    cu = sub.add_parser("comment-update", help="Update an existing comment")
    cu.add_argument("--comment-id", required=True)
    cu.add_argument("--format", default="storage", choices=["markdown", "wiki", "storage"])
    cu.add_argument("--content")
    cu.add_argument("--content-file")
    cu.set_defaults(func=cmd_comment_update)

    cd = sub.add_parser("comment-delete", help="Delete a comment")
    cd.add_argument("--comment-id", required=True)
    cd.set_defaults(func=cmd_comment_delete)

    att = sub.add_parser("attachments", help="List attachments for a Confluence page")
    att.add_argument("--page-id", required=True)
    att.add_argument("--limit", type=int, default=50, help="Max number of attachments to return")
    att.set_defaults(func=cmd_attachments)

    dl = sub.add_parser("download", help="Download attachment(s) from a Confluence page")
    dl.add_argument("--page-id", required=True)
    dl.add_argument("--filename", help="Specific attachment filename to download (downloads all if not specified)")
    dl.add_argument("--output-dir", "-o", default=".", help="Directory to save downloaded files")
    dl.add_argument("--overwrite", action="store_true", default=False, help="Overwrite existing files")
    dl.set_defaults(func=cmd_download)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

