#!/usr/bin/env python3
"""gabiarequest 이슈 생성을 표준화하는 헬퍼 스크립트.

기존 GitLab skill의 CLI(`gitlab_issue_cli.py`)를 래핑하여 아래를 자동화한다.
- 템플릿 선택/로딩
- 초기 라벨 정책 적용
- DDL 요청 시간 제약 검증
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path


PROJECT_DEFAULT = "devops/gabiarequest"
TEMPLATE_ROOT_DEFAULT = "~/github/gabiarequest/.gitlab/issue_templates"
API_DEFAULT = "https://gitlab.gabia.com/api/v4"

TEMPLATE_MAP: dict[str, tuple[str, str]] = {
    "request": ("Request.md", "request.md"),
    "deploy": ("배포 요청.md", "deploy-request.md"),
    "db": ("DB 요청.md", "db-request.md"),
    "k8s": ("k8s배포구축.md", "k8s-deploy-setup.md"),
    "firewall": ("방화벽 정책 요청.md", "firewall-policy-request.md"),
    "new-server": ("신규서버구축.md", "new-server-setup.md"),
    "server-access": ("실서버 접속 티켓 요청.md", "server-access-ticket-request.md"),
    "oracle-sync": ("오라클 개발 DB 동기화 요청.md", "oracle-dev-db-sync-request.md"),
}


def _env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _require_env(name: str) -> str:
    value = _env(name)
    if value:
        return value
    raise SystemExit(f"[ERROR] 필수 환경변수 누락: {name}")


def _api_base() -> str:
    return (_env("GITLAB_API_URL") or API_DEFAULT).rstrip("/")


def _project_encoded(project_id: str) -> str:
    decoded = urllib.parse.unquote(project_id)
    return urllib.parse.quote(decoded, safe="")


def _load_project_labels(project_id: str) -> set[str]:
    token = _require_env("GITLAB_TOKEN")
    url = f"{_api_base()}/projects/{_project_encoded(project_id)}/labels?per_page=100&page=1"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "PRIVATE-TOKEN": token,
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        labels = json.loads(response.read().decode("utf-8"))
    return {item.get("name", "") for item in labels}


def _resolve_gitlab_cli(cli_arg: str | None) -> Path:
    candidates: list[Path] = []
    if cli_arg:
        candidates.append(Path(cli_arg).expanduser())

    env_path = _env("GABIA_GITLAB_ISSUE_CLI")
    if env_path:
        candidates.append(Path(env_path).expanduser())

    skill_dir = Path(__file__).resolve().parent
    candidates.append(skill_dir.parent.parent / "gabia-dev-mcp-gitlab-issues" / "scripts" / "gitlab_issue_cli.py")
    candidates.append(Path.cwd() / "skills" / "gabia-dev-mcp-gitlab-issues" / "scripts" / "gitlab_issue_cli.py")

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise SystemExit(
        "[ERROR] gitlab_issue_cli.py 경로를 찾지 못했습니다. "
        "--gitlab-cli 또는 GABIA_GITLAB_ISSUE_CLI를 지정하세요."
    )


def _resolve_template_file(template_key: str, template_root: str) -> Path:
    upstream_name, bundled_name = TEMPLATE_MAP[template_key]
    upstream = Path(template_root).expanduser() / upstream_name
    if upstream.is_file():
        return upstream

    bundled = Path(__file__).resolve().parent.parent / "references" / "templates" / bundled_name
    if bundled.is_file():
        return bundled

    raise SystemExit(
        "[ERROR] 템플릿 파일을 찾지 못했습니다. "
        f"upstream={upstream} bundled={bundled}"
    )


def _resolve_after_18_label(
    requested_label: str,
    fallback_label: str,
    project_labels: set[str],
) -> str:
    if requested_label in project_labels:
        return requested_label
    if fallback_label in project_labels:
        return fallback_label
    return requested_label


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="gabiarequest 이슈 생성 헬퍼")
    parser.add_argument("--project-id", default=PROJECT_DEFAULT)
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--template",
        required=True,
        choices=sorted(TEMPLATE_MAP),
        help="요청 유형 템플릿",
    )
    parser.add_argument("--description-file", help="직접 작성한 본문 파일 경로(있으면 템플릿 대신 사용)")
    parser.add_argument("--template-root", default=TEMPLATE_ROOT_DEFAULT)
    parser.add_argument("--deploy-hour", type=int, help="배포 시간(24h). 예: 11, 18, 23")
    parser.add_argument(
        "--db-kind",
        choices=["none", "ddl", "dml"],
        default="none",
        help="DB 요청인 경우 DDL/DML 구분",
    )
    parser.add_argument("--urgent", action="store_true")
    parser.add_argument("--extra-label", action="append", default=[])
    parser.add_argument("--assignee-id", type=int, action="append", default=[])
    parser.add_argument("--milestone-id")
    parser.add_argument("--issue-type", choices=["issue", "incident", "test_case", "task"])
    parser.add_argument("--gitlab-cli", help="gitlab_issue_cli.py 경로")
    parser.add_argument("--label-approval", default="1. 승인 중")
    parser.add_argument("--label-11", default="11시 배포")
    parser.add_argument("--label-urgent", default="긴급")
    parser.add_argument("--label-18", default="18시 배포")
    parser.add_argument("--label-18-fallback", default="18시 이후 요청")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    _require_env("GITLAB_TOKEN")

    if args.deploy_hour is not None and not (0 <= args.deploy_hour <= 23):
        raise SystemExit("[ERROR] --deploy-hour 는 0~23 범위여야 합니다.")

    if args.db_kind == "ddl":
        if args.deploy_hour is None or args.deploy_hour < 18:
            raise SystemExit("[ERROR] DDL 요청은 18시 이후 배포만 허용됩니다. (--deploy-hour 18 이상 필요)")

    if args.description_file:
        description_path = Path(args.description_file).expanduser()
        if not description_path.is_file():
            raise SystemExit(f"[ERROR] description 파일이 없습니다: {description_path}")
    else:
        description_path = _resolve_template_file(args.template, args.template_root)

    project_labels = _load_project_labels(args.project_id)

    labels: list[str] = [args.label_approval]
    if args.deploy_hour == 11:
        labels.append(args.label_11)
    if args.urgent:
        labels.append(args.label_urgent)

    need_after_18_label = args.deploy_hour is not None and args.deploy_hour >= 18
    if args.db_kind == "ddl":
        need_after_18_label = True
    if need_after_18_label:
        labels.append(_resolve_after_18_label(args.label_18, args.label_18_fallback, project_labels))

    labels.extend(args.extra_label or [])
    labels = _ordered_unique(labels)

    cli_path = _resolve_gitlab_cli(args.gitlab_cli)
    command = [
        sys.executable,
        str(cli_path),
        "create",
        "--project-id",
        args.project_id,
        "--title",
        args.title,
        "--description-file",
        str(description_path),
    ]
    for label in labels:
        command.extend(["--labels", label])
    for assignee_id in args.assignee_id:
        command.extend(["--assignee-ids", str(assignee_id)])
    if args.milestone_id:
        command.extend(["--milestone-id", args.milestone_id])
    if args.issue_type:
        command.extend(["--issue-type", args.issue_type])

    if args.dry_run:
        print(
            json.dumps(
                {
                    "command": command,
                    "labels": labels,
                    "description_file": str(description_path),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    result = subprocess.run(command, text=True, capture_output=True)
    if result.stdout:
        print(result.stdout.rstrip())
    if result.returncode != 0:
        if result.stderr:
            print(result.stderr.rstrip(), file=sys.stderr)
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
