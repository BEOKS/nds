#!/usr/bin/env python3
"""Board Resolver GSAP 페이지를 녹화해 webm 파일로 저장한다."""

from __future__ import annotations

import argparse
import functools
import shutil
import subprocess
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright


class SilentHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Board Resolver 애니메이션을 webm으로 녹화합니다.")
    parser.add_argument(
        "--html",
        default="board-resolver-process.html",
        help="녹화할 HTML 파일 경로 (기본값: board-resolver-process.html)",
    )
    parser.add_argument(
        "--output",
        default="board-resolver-process.mp4",
        help="출력 비디오 경로 (기본값: board-resolver-process.mp4)",
    )
    return parser


def start_server(directory: Path) -> ThreadingHTTPServer:
    handler = functools.partial(SilentHandler, directory=str(directory))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def record(html_path: Path, output_path: Path) -> None:
    httpd = start_server(html_path.parent)
    port = httpd.server_address[1]
    url = f"http://127.0.0.1:{port}/{html_path.name}"

    with tempfile.TemporaryDirectory(prefix="board-resolver-video-") as temp_dir:
        video_dir = Path(temp_dir) / "video"
        video_dir.mkdir(parents=True, exist_ok=True)
        raw_video_path = Path(temp_dir) / "raw.webm"

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                device_scale_factor=1,
                record_video_dir=str(video_dir),
                record_video_size={"width": 1280, "height": 720},
            )

            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_function("window.__animationReady === true", timeout=30000)
            page.evaluate("window.startBoardResolverAnimation()")

            duration_sec = float(page.evaluate("window.__captureLengthSec"))
            page.wait_for_timeout(int(duration_sec * 1000) + 300)

            video = page.video
            context.close()
            shutil.copy2(video.path(), raw_video_path)
            browser.close()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            output_path.unlink()

        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(raw_video_path),
                "-t",
                str(duration_sec),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-y",
                str(output_path),
            ],
            check=True,
        )

    httpd.shutdown()
    httpd.server_close()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    html_path = Path(args.html).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not html_path.exists():
        raise SystemExit(f"[ERROR] HTML 파일이 없습니다: {html_path}")

    record(html_path, output_path)
    print(f"[OK] 비디오 생성 완료: {output_path}")


if __name__ == "__main__":
    main()
