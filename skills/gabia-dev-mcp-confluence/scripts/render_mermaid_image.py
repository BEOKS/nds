#!/usr/bin/env python3
"""Mermaid 텍스트를 이미지로 렌더링하는 간단한 유틸리티."""

from __future__ import annotations

import argparse
import pathlib
import sys

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render Mermaid text to PNG or SVG via Kroki."
    )
    parser.add_argument(
        "--input-file",
        help="Mermaid source file path. Omit to read from stdin.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output file path. Extension should match --format.",
    )
    parser.add_argument(
        "--format",
        choices=("png", "svg"),
        default="png",
        help="Output image format.",
    )
    parser.add_argument(
        "--server",
        default="https://kroki.io",
        help="Kroki server base URL.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout in seconds.",
    )
    return parser.parse_args()


def read_source(args: argparse.Namespace) -> str:
    if args.input_file:
        return pathlib.Path(args.input_file).read_text(encoding="utf-8")
    return sys.stdin.read()


def main() -> int:
    args = parse_args()
    source = read_source(args).strip()
    if not source:
        raise SystemExit("[ERROR] Mermaid source is empty")

    output_path = pathlib.Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    url = f"{args.server.rstrip('/')}/mermaid/{args.format}"
    response = requests.post(
        url,
        data=source.encode("utf-8"),
        headers={"Content-Type": "text/plain; charset=utf-8"},
        timeout=args.timeout,
    )
    response.raise_for_status()
    output_path.write_bytes(response.content)

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
