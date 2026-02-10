#!/usr/bin/env python3
"""
Figma 프레임을 이미지로 추출하여 Markdown 문서로 생성하는 스크립트.

사용법:
    python3 figma_doc.py export --file-key <KEY> --output <DIR> [OPTIONS]
    python3 figma_doc.py list --file-key <KEY> [--node-id <ID>]

환경변수:
    FIGMA_API_KEY 또는 FIGMA_OAUTH_TOKEN

의존성:
    pip install Pillow (이미지 리사이징 시 필요)
"""
import argparse
import io
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# SSL 검증 비활성화 컨텍스트 (회사 프록시 등 환경용)
_SSL_CONTEXT: ssl.SSLContext | None = None


def _get_ssl_context() -> ssl.SSLContext | None:
    """SSL 컨텍스트 반환. --insecure 모드일 때 검증 비활성화."""
    return _SSL_CONTEXT

# Pillow는 선택적 의존성
try:
    from PIL import Image

    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

# 모델별 이미지 최대 크기 (긴 변 기준, pixels)
# https://docs.anthropic.com/en/docs/build-with-claude/vision
MODEL_MAX_IMAGE_SIZE: dict[str, int] = {
    "claude": 1568,  # Claude 모델 권장 최대 크기
    "gpt4": 2048,  # GPT-4 Vision
    "gemini": 3072,  # Gemini Pro Vision
    "default": 1568,  # 기본값 (Claude 기준)
}


@dataclass
class FrameInfo:
    """프레임 정보를 담는 클래스."""

    node_id: str
    name: str
    width: float
    height: float
    parent_name: str | None = None


def _env(name: str) -> str | None:
    v = os.getenv(name)
    if v is None:
        return None
    v = v.strip()
    return v or None


def _auth_headers() -> dict[str, str]:
    oauth = _env("FIGMA_OAUTH_TOKEN")
    api_key = _env("FIGMA_API_KEY")
    if not oauth and not api_key:
        raise SystemExit("[ERROR] Missing Figma auth. Set FIGMA_OAUTH_TOKEN or FIGMA_API_KEY.")

    headers: dict[str, str] = {"Accept": "application/json"}
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
    max_retries: int = 3,
) -> object:
    if params:
        qs = urllib.parse.urlencode(params, doseq=True)
        sep = "&" if ("?" in url) else "?"
        url = f"{url}{sep}{qs}"

    retries = 0
    while True:
        req = urllib.request.Request(url, headers=_auth_headers(), method=method.upper())
        try:
            with urllib.request.urlopen(req, timeout=180, context=_get_ssl_context()) as resp:
                raw = resp.read()
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and retries < max_retries:
                retry_after = int(e.headers.get("Retry-After", "60"))
                if retry_after > 300:  # 5분 이상이면 중단
                    hours = retry_after / 3600
                    raise SystemExit(
                        f"[ERROR] Rate limit exceeded. Retry after {hours:.1f} hours.\n"
                        "해결책: 1) 다른 Figma API 토큰 사용  2) Dev/Full 좌석 업그레이드  3) 시간 후 재시도"
                    ) from None
                retries += 1
                rate_type = e.headers.get("X-Figma-Rate-Limit-Type", "unknown")
                plan_tier = e.headers.get("X-Figma-Plan-Tier", "unknown")
                print(f"[WARN] Rate limit hit (seat: {rate_type}, plan: {plan_tier}). Waiting {retry_after}s... ({retries}/{max_retries})", file=sys.stderr)
                time.sleep(retry_after)
                continue
            err_body = e.read().decode("utf-8", errors="replace")
            raise SystemExit(f"[ERROR] Figma API error: {e.code} {e.reason}\n{err_body}") from None
        except urllib.error.URLError as e:
            raise SystemExit(f"[ERROR] Network error: {e}") from None


def _download_bytes(url: str, *, max_retries: int = 3) -> bytes:
    retries = 0
    while True:
        req = urllib.request.Request(url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=120, context=_get_ssl_context()) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and retries < max_retries:
                retry_after = int(e.headers.get("Retry-After", "60"))
                if retry_after > 300:  # 5분 이상이면 중단
                    hours = retry_after / 3600
                    raise SystemExit(
                        f"[ERROR] Rate limit exceeded. Retry after {hours:.1f} hours.\n"
                        "해결책: 1) 다른 Figma API 토큰 사용  2) Dev/Full 좌석 업그레이드  3) 시간 후 재시도"
                    ) from None
                retries += 1
                rate_type = e.headers.get("X-Figma-Rate-Limit-Type", "unknown")
                plan_tier = e.headers.get("X-Figma-Plan-Tier", "unknown")
                print(f"[WARN] Rate limit on download (seat: {rate_type}, plan: {plan_tier}). Waiting {retry_after}s... ({retries}/{max_retries})", file=sys.stderr)
                time.sleep(retry_after)
                continue
            err_body = e.read().decode("utf-8", errors="replace")
            raise SystemExit(f"[ERROR] Download error: {e.code} {e.reason}\n{err_body}") from None
        except urllib.error.URLError as e:
            raise SystemExit(f"[ERROR] Network error: {e}") from None


def _collect_frames(node: dict, parent_name: str | None = None, depth: int = 0, max_depth: int = 2) -> list[FrameInfo]:
    """노드 트리에서 FRAME 타입 노드들을 수집."""
    frames: list[FrameInfo] = []
    node_type = node.get("type", "")
    node_name = node.get("name", "Untitled")

    # FRAME, COMPONENT, COMPONENT_SET 타입만 수집 (depth 0은 페이지이므로 제외)
    if node_type in ("FRAME", "COMPONENT", "COMPONENT_SET") and depth > 0:
        bbox = node.get("absoluteBoundingBox", {})
        frames.append(
            FrameInfo(
                node_id=node.get("id", ""),
                name=node_name,
                width=bbox.get("width", 0),
                height=bbox.get("height", 0),
                parent_name=parent_name,
            )
        )
        # 프레임 내부의 프레임은 기본적으로 수집하지 않음 (최상위 프레임만)
        if depth >= max_depth:
            return frames

    # 자식 노드 탐색
    children = node.get("children", [])
    for child in children:
        frames.extend(_collect_frames(child, node_name if node_type == "CANVAS" else parent_name, depth + 1, max_depth))

    return frames


def _sanitize_filename(name: str) -> str:
    """파일명으로 사용할 수 있도록 특수문자 및 공백 제거."""
    # 특수문자와 공백을 언더스코어로 변환
    name = re.sub(r'[<>:"/\\|?*\s]+', '_', name)
    # 연속 언더스코어 정리
    name = re.sub(r'_+', '_', name)
    return name.strip("_")


def _resize_image(img_data: bytes, max_size: int) -> bytes:
    """
    이미지를 최대 크기에 맞게 리사이징.

    Args:
        img_data: 원본 이미지 바이트 데이터
        max_size: 긴 변의 최대 픽셀 크기

    Returns:
        리사이징된 이미지 바이트 데이터 (PNG)
    """
    if not HAS_PILLOW:
        print("[WARN] Pillow not installed. Skipping resize. Install with: pip install Pillow", file=sys.stderr)
        return img_data

    img = Image.open(io.BytesIO(img_data))
    width, height = img.size

    # 긴 변이 max_size 이하면 리사이징 불필요
    if max(width, height) <= max_size:
        return img_data

    # 비율 유지하며 리사이징
    if width > height:
        new_width = max_size
        new_height = int(height * (max_size / width))
    else:
        new_height = max_size
        new_width = int(width * (max_size / height))

    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # PNG로 저장
    output = io.BytesIO()
    img_resized.save(output, format="PNG", optimize=True)
    return output.getvalue()


def _filter_frames(frames: list[FrameInfo], pattern: str) -> list[FrameInfo]:
    """프레임 이름으로 필터링 (정규식 지원)."""
    try:
        regex = re.compile(pattern, re.IGNORECASE)
        return [f for f in frames if regex.search(f.name)]
    except re.error:
        # 정규식 오류 시 단순 문자열 포함 검색
        pattern_lower = pattern.lower()
        return [f for f in frames if pattern_lower in f.name.lower()]


def cmd_list(args: argparse.Namespace) -> None:
    """Figma 파일의 프레임 목록을 출력."""
    base = "https://api.figma.com/v1"
    # API depth는 max_depth + 2 (document -> page -> frames)
    api_depth = args.max_depth + 2

    if args.node_id:
        data = _http_json("GET", f"{base}/files/{args.file_key}/nodes", params={"ids": args.node_id, "depth": api_depth})
        nodes = data.get("nodes", {}) if isinstance(data, dict) else {}
        frames: list[FrameInfo] = []
        for node_data in nodes.values():
            if isinstance(node_data, dict) and node_data.get("document"):
                frames.extend(_collect_frames(node_data["document"], max_depth=args.max_depth))
    else:
        data = _http_json("GET", f"{base}/files/{args.file_key}", params={"depth": api_depth})
        doc = data.get("document", {}) if isinstance(data, dict) else {}
        frames = _collect_frames(doc, max_depth=args.max_depth)

    # 필터 적용
    if args.filter:
        frames = _filter_frames(frames, args.filter)

    result = {
        "file_key": args.file_key,
        "frame_count": len(frames),
        "frames": [
            {
                "node_id": f.node_id,
                "name": f.name,
                "width": f.width,
                "height": f.height,
                "parent": f.parent_name,
            }
            for f in frames
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_export(args: argparse.Namespace) -> None:
    """프레임을 이미지로 추출하고 Markdown 문서 생성."""
    base = "https://api.figma.com/v1"
    output_dir = Path(args.output).expanduser().resolve()
    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    # API depth는 max_depth + 2 (document -> page -> frames)
    api_depth = args.max_depth + 2

    # 1. 프레임 목록 수집
    # --frames-json: 캐시된 프레임 목록 사용 (파일 구조 API 호출 건너뛰기)
    if args.frames_json:
        frames_path = Path(args.frames_json).expanduser().resolve()
        if not frames_path.exists():
            raise SystemExit(f"[ERROR] Frames JSON not found: {frames_path}")
        cached = json.loads(frames_path.read_text(encoding="utf-8"))
        cached_frames = cached.get("frames", []) if isinstance(cached, dict) else cached
        frames: list[FrameInfo] = [
            FrameInfo(
                node_id=f["node_id"],
                name=f["name"],
                width=f.get("width", 0),
                height=f.get("height", 0),
                parent_name=f.get("parent"),
            )
            for f in cached_frames
        ]
        file_name = cached.get("file_name", "Figma Document") if isinstance(cached, dict) else "Figma Document"
        print(f"[INFO] Loaded {len(frames)} frames from cache: {frames_path}", file=sys.stderr)
    elif args.single and args.node_id:
        print("[INFO] Fetching Figma file structure...", file=sys.stderr)
        data = _http_json("GET", f"{base}/files/{args.file_key}/nodes", params={"ids": args.node_id, "depth": 1})
        nodes = data.get("nodes", {}) if isinstance(data, dict) else {}
        frames: list[FrameInfo] = []
        for node_id, node_data in nodes.items():
            if isinstance(node_data, dict) and node_data.get("document"):
                doc = node_data["document"]
                bbox = doc.get("absoluteBoundingBox", {})
                frames.append(
                    FrameInfo(
                        node_id=doc.get("id", node_id),
                        name=doc.get("name", "Untitled"),
                        width=bbox.get("width", 0),
                        height=bbox.get("height", 0),
                        parent_name=None,
                    )
                )
        file_name = frames[0].name if frames else "Figma Document"
    elif args.node_id:
        print("[INFO] Fetching Figma file structure...", file=sys.stderr)
        data = _http_json("GET", f"{base}/files/{args.file_key}/nodes", params={"ids": args.node_id, "depth": api_depth})
        nodes = data.get("nodes", {}) if isinstance(data, dict) else {}
        frames = []
        for node_data in nodes.values():
            if isinstance(node_data, dict) and node_data.get("document"):
                frames.extend(_collect_frames(node_data["document"], max_depth=args.max_depth))
        file_name = "Figma Document"
    else:
        print("[INFO] Fetching Figma file structure...", file=sys.stderr)
        data = _http_json("GET", f"{base}/files/{args.file_key}", params={"depth": api_depth})
        doc = data.get("document", {}) if isinstance(data, dict) else {}
        file_name = data.get("name", "Figma Document") if isinstance(data, dict) else "Figma Document"
        frames = _collect_frames(doc, max_depth=args.max_depth)

    # --filter 적용
    if args.filter:
        frames = _filter_frames(frames, args.filter)

    if not frames:
        raise SystemExit("[ERROR] No frames found in the specified file/node.")

    print(f"[INFO] Found {len(frames)} frames", file=sys.stderr)

    # 2. 이미지 렌더링 URL 가져오기
    node_ids = [f.node_id for f in frames]
    print("[INFO] Requesting image renders...", file=sys.stderr)

    # Figma API는 한 번에 많은 노드를 처리할 수 없으므로 배치로 나눔
    batch_size = args.batch_size
    all_urls: dict[str, str] = {}

    total_batches = (len(node_ids) + batch_size - 1) // batch_size
    for batch_idx, i in enumerate(range(0, len(node_ids), batch_size)):
        batch = node_ids[i : i + batch_size]
        print(f"[INFO] Rendering batch {batch_idx + 1}/{total_batches} ({len(batch)} frames)...", file=sys.stderr)
        resp = _http_json(
            "GET",
            f"{base}/images/{args.file_key}",
            params={"ids": ",".join(batch), "format": "png", "scale": str(args.scale)},
        )
        if isinstance(resp, dict):
            images = resp.get("images", {})
            if isinstance(images, dict):
                all_urls.update(images)
        if i + batch_size < len(node_ids):
            delay = getattr(args, 'delay', 12)
            remaining_batches = total_batches - batch_idx - 1
            eta_seconds = remaining_batches * delay
            print(f"[INFO] Waiting {delay}s for rate limit... (ETA: ~{eta_seconds}s remaining)", file=sys.stderr)
            time.sleep(delay)  # Rate limit 방지 (View/Collab: 5/min → 12s 간격)

    # 3. 이미지 다운로드 (리사이징 포함)
    print(f"[INFO] Downloading {len(frames)} images...", file=sys.stderr)
    frame_images: dict[str, str] = {}  # node_id -> image_filename
    skipped = 0
    downloaded = 0
    download_start = time.time()

    # 리사이징 설정
    max_image_size = MODEL_MAX_IMAGE_SIZE.get(args.model, MODEL_MAX_IMAGE_SIZE["default"]) if args.resize else None
    if max_image_size and not HAS_PILLOW:
        print("[WARN] --resize requires Pillow. Install with: pip install Pillow", file=sys.stderr)
        max_image_size = None

    if max_image_size:
        print(f"[INFO] Resizing images to max {max_image_size}px (model: {args.model})", file=sys.stderr)

    for idx, frame in enumerate(frames):
        url = all_urls.get(frame.node_id)
        if not url:
            print(f"[WARN] No image URL for frame: {frame.name}", file=sys.stderr)
            continue

        safe_name = _sanitize_filename(frame.name)
        img_filename = f"{idx + 1:03d}_{safe_name}.png"
        img_path = images_dir / img_filename

        # Resume: 이미 다운로드된 이미지 건너뛰기
        if args.resume and img_path.exists() and img_path.stat().st_size > 0:
            frame_images[frame.node_id] = img_filename
            skipped += 1
            continue

        try:
            img_data = _download_bytes(url)

            # 리사이징 적용
            if max_image_size:
                img_data = _resize_image(img_data, max_image_size)

            img_path.write_bytes(img_data)
            frame_images[frame.node_id] = img_filename
            downloaded += 1

            # 진행률 + ETA
            elapsed = time.time() - download_start
            avg = elapsed / downloaded
            remaining = len(frames) - (idx + 1)
            eta = int(avg * remaining)
            eta_str = f"{eta // 60}m{eta % 60:02d}s" if eta >= 60 else f"{eta}s"
            print(f"  [{idx + 1}/{len(frames)}] {frame.name} (ETA ~{eta_str})", file=sys.stderr)
        except SystemExit as e:
            print(f"[WARN] Failed to download {frame.name}: {e}", file=sys.stderr)

    if skipped > 0:
        print(f"[INFO] Skipped {skipped} already downloaded images (--resume)", file=sys.stderr)

    # 4. Markdown 문서 생성
    print("[INFO] Generating Markdown document...", file=sys.stderr)
    doc_title = args.title or file_name
    md_lines: list[str] = [
        f"# {doc_title}",
        "",
        f"> Generated from Figma on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> File Key: `{args.file_key}`",
        "",
        "---",
        "",
        "## Table of Contents",
        "",
    ]

    # TOC 생성
    current_parent: str | None = None
    for idx, frame in enumerate(frames):
        if frame.node_id not in frame_images:
            continue
        anchor = f"frame-{idx + 1}"
        if frame.parent_name and frame.parent_name != current_parent:
            md_lines.append(f"- **{frame.parent_name}**")
            current_parent = frame.parent_name
        md_lines.append(f"  - [{frame.name}](#{anchor})")

    md_lines.extend(["", "---", ""])

    # 프레임 섹션 생성
    current_parent = None
    for idx, frame in enumerate(frames):
        if frame.node_id not in frame_images:
            continue

        # 부모(페이지) 헤더
        if frame.parent_name and frame.parent_name != current_parent:
            current_parent = frame.parent_name
            md_lines.extend([f"## {frame.parent_name}", ""])

        anchor = f"frame-{idx + 1}"
        img_filename = frame_images[frame.node_id]

        md_lines.extend(
            [
                f"### {frame.name} {{#{anchor}}}",
                "",
                f"![{frame.name}](images/{img_filename})",
                "",
                f"- **Size**: {int(frame.width)} x {int(frame.height)}px",
                f"- **Node ID**: `{frame.node_id}`",
                "",
            ]
        )

        # AI 설명 플레이스홀더
        if args.with_description:
            md_lines.extend(
                [
                    "#### Description",
                    "",
                    "<!-- AI_DESCRIPTION_START -->",
                    "_Description will be generated by AI._",
                    "<!-- AI_DESCRIPTION_END -->",
                    "",
                ]
            )

        md_lines.append("---")
        md_lines.append("")

    # Markdown 파일 저장
    md_filename = _sanitize_filename(doc_title) + ".md"
    md_path = output_dir / md_filename
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    result = {
        "success": True,
        "output_dir": str(output_dir),
        "markdown_file": str(md_path),
        "images_dir": str(images_dir),
        "frame_count": len(frame_images),
        "total_frames": len(frames),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_describe(args: argparse.Namespace) -> None:
    """Markdown 파일에서 이미지와 플레이스홀더 정보를 추출."""
    md_path = Path(args.markdown).expanduser().resolve()
    if not md_path.exists():
        raise SystemExit(f"[ERROR] Markdown file not found: {md_path}")

    content = md_path.read_text(encoding="utf-8")
    images_dir = md_path.parent / "images"

    # 이미지와 플레이스홀더 파싱
    items: list[dict] = []
    sections = content.split("### ")

    for section in sections[1:]:  # 첫 번째는 헤더 이전 내용
        lines = section.split("\n")
        title = lines[0].split(" {#")[0] if " {#" in lines[0] else lines[0]

        # 이미지 경로 찾기
        img_match = re.search(r"!\[.*?\]\((images/[^)]+)\)", section)
        if not img_match:
            continue

        img_rel_path = img_match.group(1)
        img_abs_path = md_path.parent / img_rel_path

        # 플레이스홀더 확인
        has_placeholder = "<!-- AI_DESCRIPTION_START -->" in section
        placeholder_filled = has_placeholder and "_Description will be generated by AI._" not in section

        items.append({
            "title": title,
            "image_path": str(img_abs_path),
            "has_placeholder": has_placeholder,
            "placeholder_filled": placeholder_filled,
        })

    result = {
        "markdown_file": str(md_path),
        "images_dir": str(images_dir),
        "total_items": len(items),
        "pending_descriptions": len([i for i in items if i["has_placeholder"] and not i["placeholder_filled"]]),
        "items": items,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_build(args: argparse.Namespace) -> None:
    """수동 내보내기한 이미지 폴더로 Markdown 문서 생성."""
    images_dir = Path(args.images_dir).expanduser().resolve()
    if not images_dir.is_dir():
        raise SystemExit(f"[ERROR] Images directory not found: {images_dir}")

    # 이미지 파일 수집 (PNG, JPG, JPEG, WEBP)
    image_exts = {".png", ".jpg", ".jpeg", ".webp"}
    image_files = sorted(
        [f for f in images_dir.iterdir() if f.suffix.lower() in image_exts],
        key=lambda f: f.name,
    )

    if not image_files:
        raise SystemExit(f"[ERROR] No images found in: {images_dir}")

    print(f"[INFO] Found {len(image_files)} images in {images_dir}", file=sys.stderr)

    # 출력 디렉토리 결정
    output_dir = Path(args.output).expanduser().resolve() if args.output else images_dir.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # 이미지를 output/images/로 복사 (필요 시 리사이징)
    out_images_dir = output_dir / "images"
    out_images_dir.mkdir(parents=True, exist_ok=True)

    max_image_size = MODEL_MAX_IMAGE_SIZE.get(args.model, MODEL_MAX_IMAGE_SIZE["default"]) if args.resize else None
    if max_image_size and not HAS_PILLOW:
        print("[WARN] --resize requires Pillow. Install with: pip install Pillow", file=sys.stderr)
        max_image_size = None

    processed_images: list[tuple[str, str]] = []  # (display_name, filename)
    for idx, img_file in enumerate(image_files):
        # 파일명에서 표시 이름 추출 (확장자 제거, 번호 prefix 제거)
        stem = img_file.stem
        display_name = re.sub(r"^\d+[_\-.\s]*", "", stem) or stem
        display_name = display_name.replace("_", " ").strip()

        # 정렬된 파일명으로 복사
        out_filename = f"{idx + 1:03d}_{_sanitize_filename(display_name)}{img_file.suffix.lower()}"
        out_path = out_images_dir / out_filename

        if img_file.parent.resolve() == out_images_dir.resolve() and img_file.name == out_filename:
            # 이미 같은 위치에 같은 이름이면 스킵
            pass
        else:
            img_data = img_file.read_bytes()
            if max_image_size:
                img_data = _resize_image(img_data, max_image_size)
            out_path.write_bytes(img_data)

        processed_images.append((display_name, out_filename))
        print(f"  [{idx + 1}/{len(image_files)}] {display_name}", file=sys.stderr)

    # Markdown 문서 생성
    print("[INFO] Generating Markdown document...", file=sys.stderr)
    doc_title = args.title or images_dir.name
    md_lines: list[str] = [
        f"# {doc_title}",
        "",
        f"> Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "---",
        "",
        "## Table of Contents",
        "",
    ]

    # TOC
    for idx, (name, _) in enumerate(processed_images):
        anchor = f"frame-{idx + 1}"
        md_lines.append(f"- [{name}](#{anchor})")

    md_lines.extend(["", "---", ""])

    # 프레임 섹션
    for idx, (name, filename) in enumerate(processed_images):
        anchor = f"frame-{idx + 1}"
        md_lines.extend(
            [
                f"### {name} {{#{anchor}}}",
                "",
                f"![{name}](images/{filename})",
                "",
            ]
        )

        # AI 설명 플레이스홀더 (기본 활성화)
        if not args.no_description:
            md_lines.extend(
                [
                    "#### Description",
                    "",
                    "<!-- AI_DESCRIPTION_START -->",
                    "_Description will be generated by AI._",
                    "<!-- AI_DESCRIPTION_END -->",
                    "",
                ]
            )

        md_lines.append("---")
        md_lines.append("")

    md_filename = _sanitize_filename(doc_title) + ".md"
    md_path = output_dir / md_filename
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    result = {
        "success": True,
        "output_dir": str(output_dir),
        "markdown_file": str(md_path),
        "images_dir": str(out_images_dir),
        "image_count": len(processed_images),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Figma 프레임을 이미지로 추출하여 Markdown 문서 생성",
    )
    p.add_argument(
        "--insecure",
        action="store_true",
        help="SSL 인증서 검증 비활성화 (회사 프록시 환경용)",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # list 명령
    ls = sub.add_parser("list", help="Figma 파일의 프레임 목록 출력")
    ls.add_argument("--file-key", required=True, help="Figma 파일 키")
    ls.add_argument("--node-id", help="특정 노드 ID만 조회")
    ls.add_argument("--filter", help="프레임 이름 필터 (정규식 지원)")
    ls.add_argument("--max-depth", type=int, default=2, help="프레임 탐색 깊이 (기본값: 2)")
    ls.set_defaults(func=cmd_list)

    # export 명령
    ex = sub.add_parser("export", help="프레임을 이미지로 추출하고 Markdown 문서 생성")
    ex.add_argument("--file-key", required=True, help="Figma 파일 키")
    ex.add_argument("--output", required=True, help="출력 디렉토리")
    ex.add_argument("--node-id", help="특정 노드 ID만 추출")
    ex.add_argument("--single", action="store_true", help="node-id로 지정한 프레임 자체를 1장으로 렌더링")
    ex.add_argument("--filter", help="프레임 이름 필터 (정규식 지원)")
    ex.add_argument("--title", help="문서 제목 (기본값: Figma 파일명)")
    ex.add_argument("--scale", type=int, default=2, help="이미지 스케일 (기본값: 2)")
    ex.add_argument("--max-depth", type=int, default=2, help="프레임 탐색 깊이 (기본값: 2)")
    ex.add_argument(
        "--with-description",
        action="store_true",
        help="AI 설명 플레이스홀더 추가",
    )
    ex.add_argument(
        "--resize",
        action="store_true",
        help="AI 모델 입력 크기에 맞게 이미지 리사이징",
    )
    ex.add_argument(
        "--model",
        choices=["claude", "gpt4", "gemini"],
        default="claude",
        help="리사이징 기준 모델 (기본값: claude)",
    )
    ex.add_argument(
        "--delay",
        type=int,
        default=12,
        help="배치 요청 간 딜레이 초 (기본값: 12, View좌석은 5회/분 제한)",
    )
    ex.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="렌더 요청 배치 크기 (기본값: 500, 한 번에 전체 요청하여 API 호출 최소화)",
    )
    ex.add_argument(
        "--resume",
        action="store_true",
        help="이미 다운로드된 이미지 건너뛰기 (중단 후 재시작 시 사용)",
    )
    ex.add_argument(
        "--frames-json",
        help="캐시된 프레임 목록 JSON 파일 경로 (파일 구조 API 호출 건너뛰기)",
    )
    ex.set_defaults(func=cmd_export)

    # build 명령 (수동 내보내기 이미지 → Markdown)
    bd = sub.add_parser("build", help="수동 내보내기한 이미지 폴더로 Markdown 문서 생성")
    bd.add_argument("--images-dir", required=True, help="이미지 폴더 경로")
    bd.add_argument("--output", help="출력 디렉토리 (기본값: 이미지 폴더 상위)")
    bd.add_argument("--title", help="문서 제목 (기본값: 폴더명)")
    bd.add_argument(
        "--resize",
        action="store_true",
        help="AI 모델 입력 크기에 맞게 이미지 리사이징",
    )
    bd.add_argument(
        "--model",
        choices=["claude", "gpt4", "gemini"],
        default="claude",
        help="리사이징 기준 모델 (기본값: claude)",
    )
    bd.add_argument(
        "--no-description",
        action="store_true",
        help="AI 설명 플레이스홀더 생략",
    )
    bd.set_defaults(func=cmd_build)

    # describe 명령
    desc = sub.add_parser("describe", help="Markdown 파일의 이미지/플레이스홀더 정보 추출")
    desc.add_argument("--markdown", required=True, help="분석할 Markdown 파일 경로")
    desc.set_defaults(func=cmd_describe)

    return p


def main() -> None:
    global _SSL_CONTEXT
    parser = build_parser()
    args = parser.parse_args()

    # --insecure 옵션 처리
    if args.insecure:
        _SSL_CONTEXT = ssl.create_default_context()
        _SSL_CONTEXT.check_hostname = False
        _SSL_CONTEXT.verify_mode = ssl.CERT_NONE

    args.func(args)


if __name__ == "__main__":
    main()
