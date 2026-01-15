#!/usr/bin/env python3
"""
Mac launchd 기반 크론 작업 관리 스크립트
등록, 조회, 수정, 삭제, 실행 기능 제공
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 설정
CRON_DIR = Path.home() / ".claude" / "cron"
PLIST_DIR = Path.home() / "Library" / "LaunchAgents"
LOG_DIR = CRON_DIR / "logs"
DATA_FILE = CRON_DIR / "jobs.json"
PREFIX = "com.claude.cron"


def init_dirs():
    """필요한 디렉토리 생성"""
    CRON_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PLIST_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("{}")


def load_jobs() -> dict:
    """저장된 작업 목록 로드"""
    init_dirs()
    try:
        return json.loads(DATA_FILE.read_text())
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_jobs(jobs: dict):
    """작업 목록 저장"""
    DATA_FILE.write_text(json.dumps(jobs, indent=2, ensure_ascii=False))


def get_plist_path(job_id: str) -> Path:
    """plist 파일 경로 반환"""
    return PLIST_DIR / f"{PREFIX}.{job_id}.plist"


def generate_plist(job_id: str, command: str, workdir: str, schedule: dict, notify: bool = True) -> str:
    """launchd plist XML 생성"""
    label = f"{PREFIX}.{job_id}"
    log_out = LOG_DIR / f"{job_id}.log"
    log_err = LOG_DIR / f"{job_id}-error.log"

    # 알림 포함 스크립트 래퍼
    if notify:
        script = f'''#!/bin/bash
export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
cd "{workdir}"
echo "=== $(date) ===" >> "{log_out}"
if {command} >> "{log_out}" 2>&1; then
    osascript -e 'display notification "작업 완료: {job_id}" with title "✅ Cron" sound name "Glass"'
else
    osascript -e 'display notification "작업 실패: {job_id}" with title "❌ Cron 에러" sound name "Basso"'
fi
'''
        script_path = CRON_DIR / f"{job_id}.sh"
        script_path.write_text(script)
        script_path.chmod(0o755)
        program_args = f'''<array>
        <string>/bin/bash</string>
        <string>{script_path}</string>
    </array>'''
    else:
        program_args = f'''<array>
        <string>/bin/bash</string>
        <string>-c</string>
        <string>cd "{workdir}" &amp;&amp; {command}</string>
    </array>'''

    # 스케줄 설정
    schedule_xml = "<dict>"
    if "hour" in schedule:
        schedule_xml += f"\n        <key>Hour</key>\n        <integer>{schedule['hour']}</integer>"
    if "minute" in schedule:
        schedule_xml += f"\n        <key>Minute</key>\n        <integer>{schedule['minute']}</integer>"
    if "weekday" in schedule:
        schedule_xml += f"\n        <key>Weekday</key>\n        <integer>{schedule['weekday']}</integer>"
    if "day" in schedule:
        schedule_xml += f"\n        <key>Day</key>\n        <integer>{schedule['day']}</integer>"
    if "month" in schedule:
        schedule_xml += f"\n        <key>Month</key>\n        <integer>{schedule['month']}</integer>"
    schedule_xml += "\n    </dict>"

    # interval 모드
    if "interval" in schedule:
        interval_xml = f'''<key>StartInterval</key>
    <integer>{schedule['interval']}</integer>'''
    else:
        interval_xml = f'''<key>StartCalendarInterval</key>
    {schedule_xml}'''

    plist = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>

    <key>ProgramArguments</key>
    {program_args}

    <key>WorkingDirectory</key>
    <string>{workdir}</string>

    {interval_xml}

    <key>StandardOutPath</key>
    <string>{log_out}</string>
    <key>StandardErrorPath</key>
    <string>{log_err}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string>
        <key>HOME</key>
        <string>{Path.home()}</string>
    </dict>
</dict>
</plist>'''
    return plist


def add_job(job_id: str, command: str, workdir: str, schedule: dict,
            description: str = "", notify: bool = True):
    """새 크론 작업 등록"""
    init_dirs()
    jobs = load_jobs()

    if job_id in jobs:
        print(f"❌ 이미 존재하는 작업: {job_id}")
        sys.exit(1)

    plist_path = get_plist_path(job_id)
    plist_content = generate_plist(job_id, command, workdir, schedule, notify)
    plist_path.write_text(plist_content)

    # launchctl에 등록
    result = subprocess.run(["launchctl", "load", str(plist_path)], capture_output=True)
    if result.returncode != 0:
        print(f"❌ launchctl 등록 실패: {result.stderr.decode()}")
        plist_path.unlink(missing_ok=True)
        sys.exit(1)

    # 메타데이터 저장
    jobs[job_id] = {
        "command": command,
        "workdir": workdir,
        "schedule": schedule,
        "description": description,
        "notify": notify,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    save_jobs(jobs)

    print(f"✅ 작업 등록 완료: {job_id}")
    print(f"   명령어: {command}")
    print(f"   디렉토리: {workdir}")
    print(f"   스케줄: {schedule}")


def list_jobs():
    """등록된 작업 목록 조회"""
    jobs = load_jobs()

    if not jobs:
        print("등록된 크론 작업이 없습니다.")
        return

    print(f"{'ID':<20} {'스케줄':<25} {'명령어':<40} {'설명'}")
    print("-" * 100)

    for job_id, info in jobs.items():
        schedule_str = format_schedule(info.get("schedule", {}))
        cmd = info.get("command", "")[:38]
        desc = info.get("description", "")[:30]
        print(f"{job_id:<20} {schedule_str:<25} {cmd:<40} {desc}")


def format_schedule(schedule: dict) -> str:
    """스케줄을 읽기 쉬운 형식으로 변환"""
    if "interval" in schedule:
        return f"매 {schedule['interval']}초"

    parts = []
    if "month" in schedule:
        parts.append(f"{schedule['month']}월")
    if "day" in schedule:
        parts.append(f"{schedule['day']}일")
    if "weekday" in schedule:
        weekdays = ["일", "월", "화", "수", "목", "금", "토"]
        parts.append(f"{weekdays[schedule['weekday']]}요일")
    if "hour" in schedule:
        parts.append(f"{schedule['hour']:02d}시")
    if "minute" in schedule:
        parts.append(f"{schedule['minute']:02d}분")

    return " ".join(parts) if parts else "설정 없음"


def get_job(job_id: str):
    """특정 작업 상세 조회"""
    jobs = load_jobs()

    if job_id not in jobs:
        print(f"❌ 존재하지 않는 작업: {job_id}")
        sys.exit(1)

    info = jobs[job_id]
    print(f"작업 ID: {job_id}")
    print(f"명령어: {info.get('command')}")
    print(f"디렉토리: {info.get('workdir')}")
    print(f"스케줄: {format_schedule(info.get('schedule', {}))}")
    print(f"설명: {info.get('description', '없음')}")
    print(f"알림: {'활성' if info.get('notify', True) else '비활성'}")
    print(f"생성일: {info.get('created_at')}")
    print(f"수정일: {info.get('updated_at')}")

    # 로그 파일 확인
    log_file = LOG_DIR / f"{job_id}.log"
    if log_file.exists():
        print(f"\n최근 로그 (마지막 10줄):")
        print("-" * 50)
        lines = log_file.read_text().strip().split("\n")[-10:]
        for line in lines:
            print(line)


def remove_job(job_id: str):
    """크론 작업 삭제"""
    jobs = load_jobs()

    if job_id not in jobs:
        print(f"❌ 존재하지 않는 작업: {job_id}")
        sys.exit(1)

    plist_path = get_plist_path(job_id)

    # launchctl에서 해제
    if plist_path.exists():
        subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)
        plist_path.unlink(missing_ok=True)

    # 스크립트 파일 삭제
    script_path = CRON_DIR / f"{job_id}.sh"
    script_path.unlink(missing_ok=True)

    # 메타데이터 삭제
    del jobs[job_id]
    save_jobs(jobs)

    print(f"✅ 작업 삭제 완료: {job_id}")


def update_job(job_id: str, command: str = None, workdir: str = None,
               schedule: dict = None, description: str = None, notify: bool = None):
    """크론 작업 수정"""
    jobs = load_jobs()

    if job_id not in jobs:
        print(f"❌ 존재하지 않는 작업: {job_id}")
        sys.exit(1)

    info = jobs[job_id]

    # 업데이트할 필드만 변경
    if command is not None:
        info["command"] = command
    if workdir is not None:
        info["workdir"] = workdir
    if schedule is not None:
        info["schedule"] = schedule
    if description is not None:
        info["description"] = description
    if notify is not None:
        info["notify"] = notify

    info["updated_at"] = datetime.now().isoformat()

    # 기존 작업 해제
    plist_path = get_plist_path(job_id)
    if plist_path.exists():
        subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True)

    # 새 plist 생성
    plist_content = generate_plist(
        job_id,
        info["command"],
        info["workdir"],
        info["schedule"],
        info.get("notify", True)
    )
    plist_path.write_text(plist_content)

    # 다시 등록
    result = subprocess.run(["launchctl", "load", str(plist_path)], capture_output=True)
    if result.returncode != 0:
        print(f"❌ launchctl 등록 실패: {result.stderr.decode()}")
        sys.exit(1)

    jobs[job_id] = info
    save_jobs(jobs)

    print(f"✅ 작업 수정 완료: {job_id}")


def run_job(job_id: str):
    """작업 즉시 실행"""
    jobs = load_jobs()

    if job_id not in jobs:
        print(f"❌ 존재하지 않는 작업: {job_id}")
        sys.exit(1)

    label = f"{PREFIX}.{job_id}"
    result = subprocess.run(["launchctl", "start", label], capture_output=True)

    if result.returncode == 0:
        print(f"✅ 작업 실행 시작: {job_id}")
    else:
        print(f"❌ 실행 실패: {result.stderr.decode()}")


def view_logs(job_id: str, lines: int = 50):
    """작업 로그 조회"""
    log_file = LOG_DIR / f"{job_id}.log"
    error_file = LOG_DIR / f"{job_id}-error.log"

    if log_file.exists():
        print(f"=== 출력 로그 (마지막 {lines}줄) ===")
        content = log_file.read_text().strip().split("\n")[-lines:]
        for line in content:
            print(line)
    else:
        print("출력 로그 없음")

    if error_file.exists() and error_file.stat().st_size > 0:
        print(f"\n=== 에러 로그 ===")
        content = error_file.read_text().strip().split("\n")[-lines:]
        for line in content:
            print(line)


def parse_schedule(schedule_str: str) -> dict:
    """스케줄 문자열을 dict로 파싱

    형식:
    - "10:30" -> 매일 10시 30분
    - "mon 10:30" -> 매주 월요일 10시 30분
    - "15 10:30" -> 매월 15일 10시 30분
    - "interval:300" -> 300초마다
    """
    schedule = {}

    if schedule_str.startswith("interval:"):
        schedule["interval"] = int(schedule_str.split(":")[1])
        return schedule

    parts = schedule_str.lower().split()

    weekday_map = {"sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6}

    for part in parts:
        if part in weekday_map:
            schedule["weekday"] = weekday_map[part]
        elif ":" in part:
            hour, minute = part.split(":")
            schedule["hour"] = int(hour)
            schedule["minute"] = int(minute)
        elif part.isdigit():
            schedule["day"] = int(part)

    return schedule


def main():
    parser = argparse.ArgumentParser(description="Mac launchd 크론 관리")
    subparsers = parser.add_subparsers(dest="command", help="명령어")

    # add
    add_parser = subparsers.add_parser("add", help="작업 등록")
    add_parser.add_argument("job_id", help="작업 ID")
    add_parser.add_argument("--cmd", required=True, help="실행할 명령어")
    add_parser.add_argument("--workdir", default=str(Path.home()), help="작업 디렉토리")
    add_parser.add_argument("--schedule", required=True, help="스케줄 (예: '10:30', 'mon 09:00', 'interval:300')")
    add_parser.add_argument("--desc", default="", help="설명")
    add_parser.add_argument("--no-notify", action="store_true", help="알림 비활성화")

    # list
    subparsers.add_parser("list", help="작업 목록 조회")

    # get
    get_parser = subparsers.add_parser("get", help="작업 상세 조회")
    get_parser.add_argument("job_id", help="작업 ID")

    # remove
    remove_parser = subparsers.add_parser("remove", help="작업 삭제")
    remove_parser.add_argument("job_id", help="작업 ID")

    # update
    update_parser = subparsers.add_parser("update", help="작업 수정")
    update_parser.add_argument("job_id", help="작업 ID")
    update_parser.add_argument("--cmd", help="실행할 명령어")
    update_parser.add_argument("--workdir", help="작업 디렉토리")
    update_parser.add_argument("--schedule", help="스케줄")
    update_parser.add_argument("--desc", help="설명")
    update_parser.add_argument("--notify", choices=["on", "off"], help="알림 설정")

    # run
    run_parser = subparsers.add_parser("run", help="작업 즉시 실행")
    run_parser.add_argument("job_id", help="작업 ID")

    # logs
    logs_parser = subparsers.add_parser("logs", help="로그 조회")
    logs_parser.add_argument("job_id", help="작업 ID")
    logs_parser.add_argument("-n", "--lines", type=int, default=50, help="출력할 줄 수")

    args = parser.parse_args()

    if args.command == "add":
        schedule = parse_schedule(args.schedule)
        add_job(args.job_id, args.cmd, args.workdir, schedule, args.desc, not args.no_notify)
    elif args.command == "list":
        list_jobs()
    elif args.command == "get":
        get_job(args.job_id)
    elif args.command == "remove":
        remove_job(args.job_id)
    elif args.command == "update":
        schedule = parse_schedule(args.schedule) if args.schedule else None
        notify = None
        if args.notify:
            notify = args.notify == "on"
        update_job(args.job_id, args.cmd, args.workdir, schedule, args.desc, notify)
    elif args.command == "run":
        run_job(args.job_id)
    elif args.command == "logs":
        view_logs(args.job_id, args.lines)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
