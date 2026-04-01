#!/usr/bin/env python3
"""MP4 같은 비디오 파일을 최적화된 GIF로 변환한다."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("0보다 큰 정수를 입력해야 합니다.")
    return parsed


def non_negative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("0 이상의 숫자를 입력해야 합니다.")
    return parsed


def build_scale_filter(width: int | None, height: int | None) -> str:
    if width is None and height is None:
        return "scale=iw:ih:flags=lanczos"
    if width is None:
        return f"scale=-1:{height}:flags=lanczos"
    if height is None:
        return f"scale={width}:-1:flags=lanczos"
    return f"scale={width}:{height}:flags=lanczos"


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="비디오 파일을 GIF로 변환합니다.")
    parser.add_argument("input", help="입력 비디오 파일 경로")
    parser.add_argument("output", help="출력 GIF 파일 경로")
    parser.add_argument("--fps", type=positive_int, default=15, help="출력 FPS (기본값: 15)")
    parser.add_argument("--width", type=positive_int, help="출력 가로 크기")
    parser.add_argument("--height", type=positive_int, help="출력 세로 크기")
    parser.add_argument(
        "--colors",
        type=positive_int,
        default=96,
        help="palette 색상 수 (2~256, 기본값: 96)",
    )
    parser.add_argument(
        "--loop",
        type=int,
        default=0,
        help="GIF loop 횟수. 0이면 무한 반복 (기본값: 0)",
    )
    parser.add_argument("--start", type=non_negative_float, help="시작 시각(초)")
    parser.add_argument("--duration", type=non_negative_float, help="변환 길이(초)")
    parser.add_argument(
        "--ffmpeg-bin",
        default="ffmpeg",
        help="ffmpeg 실행 파일 경로 또는 이름 (기본값: ffmpeg)",
    )
    parser.add_argument("--overwrite", action="store_true", help="출력 파일 덮어쓰기")
    args = parser.parse_args()

    if not 2 <= args.colors <= 256:
        parser.error("--colors는 2~256 사이여야 합니다.")
    if args.loop < 0:
        parser.error("--loop는 0 이상이어야 합니다.")

    return args


def main() -> None:
    args = parse_args()
    ffmpeg_bin = shutil.which(args.ffmpeg_bin) or args.ffmpeg_bin

    input_path = Path(args.input).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not input_path.exists():
        raise SystemExit(f"[ERROR] 입력 파일이 없습니다: {input_path}")

    if not shutil.which(ffmpeg_bin) and not Path(ffmpeg_bin).exists():
        raise SystemExit(f"[ERROR] ffmpeg를 찾을 수 없습니다: {args.ffmpeg_bin}")

    if output_path.exists() and not args.overwrite:
        raise SystemExit(f"[ERROR] 출력 파일이 이미 존재합니다: {output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    base_input_args: list[str] = []
    if args.start is not None:
        base_input_args.extend(["-ss", str(args.start)])
    if args.duration is not None:
        base_input_args.extend(["-t", str(args.duration)])
    base_input_args.extend(["-i", str(input_path)])

    scale_filter = build_scale_filter(args.width, args.height)
    palettegen_filter = f"fps={args.fps},{scale_filter},palettegen=max_colors={args.colors}:stats_mode=diff"
    paletteuse_filter = (
        f"fps={args.fps},{scale_filter}[x];[x][1:v]paletteuse=dither=sierra2_4a"
    )

    with tempfile.TemporaryDirectory(prefix="gsap-gif-creator-") as temp_dir:
        palette_path = Path(temp_dir) / "palette.png"

        palette_cmd = [
            ffmpeg_bin,
            "-hide_banner",
            "-loglevel",
            "error",
            *base_input_args,
            "-vf",
            palettegen_filter,
            "-y",
            str(palette_path),
        ]
        run(palette_cmd)

        gif_cmd = [
            ffmpeg_bin,
            "-hide_banner",
            "-loglevel",
            "error",
            *base_input_args,
            "-i",
            str(palette_path),
            "-lavfi",
            paletteuse_filter,
            "-loop",
            str(args.loop),
        ]
        if args.overwrite:
            gif_cmd.append("-y")
        gif_cmd.append(str(output_path))
        run(gif_cmd)

    print(f"[OK] GIF 생성 완료: {output_path}")


if __name__ == "__main__":
    main()
