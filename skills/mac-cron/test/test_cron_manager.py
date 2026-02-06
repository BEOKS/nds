#!/usr/bin/env python3
"""
cron_manager.py 단위 테스트
pytest로 Mac launchd 크론 관리 기능 검증
"""

import sys
import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest

# 테스트 대상 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from cron_manager import (
    init_dirs,
    load_jobs,
    save_jobs,
    get_plist_path,
    generate_plist,
    add_job,
    list_jobs,
    get_job,
    remove_job,
    update_job,
    run_job,
    view_logs,
    parse_schedule,
    format_schedule,
)


class TestInitDirs:
    """init_dirs 함수 테스트"""

    def test_directories_created(self, tmp_path):
        """디렉토리 생성 테스트"""
        with patch('cron_manager.CRON_DIR', tmp_path / ".claude" / "cron"), \
             patch('cron_manager.LOG_DIR', tmp_path / ".claude" / "cron" / "logs"), \
             patch('cron_manager.PLIST_DIR', tmp_path / "Library" / "LaunchAgents"), \
             patch('cron_manager.DATA_FILE', tmp_path / ".claude" / "cron" / "jobs.json"):

            init_dirs()

            assert (tmp_path / ".claude" / "cron").exists()
            assert (tmp_path / ".claude" / "cron" / "logs").exists()
            assert (tmp_path / "Library" / "LaunchAgents").exists()
            assert (tmp_path / ".claude" / "cron" / "jobs.json").exists()


class TestLoadSaveJobs:
    """load_jobs, save_jobs 함수 테스트"""

    def test_load_jobs_empty(self, tmp_path):
        """빈 jobs 로드 테스트"""
        data_file = tmp_path / "jobs.json"
        data_file.write_text("{}")

        with patch('cron_manager.DATA_FILE', data_file), \
             patch('cron_manager.init_dirs'):
            result = load_jobs()

            assert result == {}

    def test_load_jobs_with_data(self, tmp_path):
        """데이터가 있는 jobs 로드 테스트"""
        jobs_data = {
            "test-job": {
                "command": "echo test",
                "workdir": "/tmp",
                "schedule": {"hour": 10, "minute": 30}
            }
        }
        data_file = tmp_path / "jobs.json"
        data_file.write_text(json.dumps(jobs_data))

        with patch('cron_manager.DATA_FILE', data_file), \
             patch('cron_manager.init_dirs'):
            result = load_jobs()

            assert "test-job" in result
            assert result["test-job"]["command"] == "echo test"

    def test_load_jobs_invalid_json(self, tmp_path):
        """잘못된 JSON 로드 테스트"""
        data_file = tmp_path / "jobs.json"
        data_file.write_text("invalid json")

        with patch('cron_manager.DATA_FILE', data_file), \
             patch('cron_manager.init_dirs'):
            result = load_jobs()

            # 에러 시 빈 딕셔너리 반환
            assert result == {}

    def test_save_jobs(self, tmp_path):
        """jobs 저장 테스트"""
        jobs_data = {
            "test-job": {
                "command": "echo test",
                "workdir": "/tmp"
            }
        }
        data_file = tmp_path / "jobs.json"

        with patch('cron_manager.DATA_FILE', data_file):
            save_jobs(jobs_data)

            # 저장된 내용 확인
            saved_data = json.loads(data_file.read_text())
            assert saved_data == jobs_data


class TestGetPlistPath:
    """get_plist_path 함수 테스트"""

    def test_plist_path_generation(self, tmp_path):
        """plist 경로 생성 테스트"""
        with patch('cron_manager.PLIST_DIR', tmp_path):
            result = get_plist_path("test-job")

            assert result == tmp_path / "com.claude.cron.test-job.plist"


class TestGeneratePlist:
    """generate_plist 함수 테스트"""

    def test_basic_plist_generation(self, tmp_path):
        """기본 plist 생성 테스트"""
        schedule = {"hour": 10, "minute": 30}

        with patch('cron_manager.LOG_DIR', tmp_path / "logs"), \
             patch('cron_manager.CRON_DIR', tmp_path):

            result = generate_plist(
                "test-job",
                "echo test",
                "/tmp",
                schedule,
                notify=False
            )

            # XML 형식 확인
            assert "<?xml version=" in result
            assert "com.claude.cron.test-job" in result
            assert "echo test" in result
            assert "<integer>10</integer>" in result
            assert "<integer>30</integer>" in result

    def test_plist_with_notification(self, tmp_path):
        """알림이 포함된 plist 생성 테스트"""
        schedule = {"hour": 10, "minute": 30}

        with patch('cron_manager.LOG_DIR', tmp_path / "logs"), \
             patch('cron_manager.CRON_DIR', tmp_path):

            result = generate_plist(
                "notify-job",
                "echo test",
                "/tmp",
                schedule,
                notify=True
            )

            # 스크립트 래퍼 생성 확인
            assert "/bin/bash" in result
            assert "notify-job.sh" in result

    def test_plist_with_interval(self, tmp_path):
        """interval 스케줄 plist 생성 테스트"""
        schedule = {"interval": 300}

        with patch('cron_manager.LOG_DIR', tmp_path / "logs"), \
             patch('cron_manager.CRON_DIR', tmp_path):

            result = generate_plist(
                "interval-job",
                "echo test",
                "/tmp",
                schedule,
                notify=False
            )

            # StartInterval 확인
            assert "StartInterval" in result
            assert "<integer>300</integer>" in result

    def test_plist_with_weekday(self, tmp_path):
        """요일 스케줄 plist 생성 테스트"""
        schedule = {"weekday": 1, "hour": 9, "minute": 0}

        with patch('cron_manager.LOG_DIR', tmp_path / "logs"), \
             patch('cron_manager.CRON_DIR', tmp_path):

            result = generate_plist(
                "weekday-job",
                "echo monday",
                "/tmp",
                schedule,
                notify=False
            )

            assert "<key>Weekday</key>" in result
            assert "<integer>1</integer>" in result


class TestParseSchedule:
    """parse_schedule 함수 테스트"""

    def test_parse_time_only(self):
        """시간만 파싱 테스트"""
        result = parse_schedule("10:30")

        assert result == {"hour": 10, "minute": 30}

    def test_parse_weekday_and_time(self):
        """요일과 시간 파싱 테스트"""
        result = parse_schedule("mon 09:00")

        assert result == {"weekday": 1, "hour": 9, "minute": 0}

    def test_parse_day_and_time(self):
        """날짜와 시간 파싱 테스트"""
        result = parse_schedule("15 10:30")

        assert result == {"day": 15, "hour": 10, "minute": 30}

    def test_parse_interval(self):
        """interval 파싱 테스트"""
        result = parse_schedule("interval:300")

        assert result == {"interval": 300}

    def test_parse_all_weekdays(self):
        """모든 요일 파싱 테스트"""
        weekdays = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
        expected = [0, 1, 2, 3, 4, 5, 6]

        for day, expected_num in zip(weekdays, expected):
            result = parse_schedule(f"{day} 10:00")
            assert result["weekday"] == expected_num


class TestFormatSchedule:
    """format_schedule 함수 테스트"""

    def test_format_interval(self):
        """interval 형식화 테스트"""
        result = format_schedule({"interval": 300})

        assert "300초" in result

    def test_format_time(self):
        """시간 형식화 테스트"""
        result = format_schedule({"hour": 10, "minute": 30})

        assert "10시" in result
        assert "30분" in result

    def test_format_weekday(self):
        """요일 형식화 테스트"""
        result = format_schedule({"weekday": 1, "hour": 9, "minute": 0})

        assert "월요일" in result
        assert "09시" in result

    def test_format_monthly(self):
        """월간 형식화 테스트"""
        result = format_schedule({"month": 12, "day": 25, "hour": 0, "minute": 0})

        assert "12월" in result
        assert "25일" in result

    def test_format_empty(self):
        """빈 스케줄 형식화 테스트"""
        result = format_schedule({})

        assert "설정 없음" in result


class TestAddJob:
    """add_job 함수 테스트"""

    def test_add_job_success(self, tmp_path):
        """작업 추가 성공 테스트"""
        data_file = tmp_path / "jobs.json"
        data_file.write_text("{}")
        plist_dir = tmp_path / "plist"
        plist_dir.mkdir()

        schedule = {"hour": 10, "minute": 30}

        with patch('cron_manager.DATA_FILE', data_file), \
             patch('cron_manager.PLIST_DIR', plist_dir), \
             patch('cron_manager.LOG_DIR', tmp_path / "logs"), \
             patch('cron_manager.CRON_DIR', tmp_path), \
             patch('cron_manager.init_dirs'), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = MagicMock(returncode=0)

            add_job("test-job", "echo test", "/tmp", schedule, "Test description")

            # jobs.json에 추가되었는지 확인
            jobs = json.loads(data_file.read_text())
            assert "test-job" in jobs
            assert jobs["test-job"]["command"] == "echo test"

            # plist 파일 생성 확인
            plist_file = plist_dir / "com.claude.cron.test-job.plist"
            assert plist_file.exists()

    def test_add_job_already_exists(self, tmp_path):
        """이미 존재하는 작업 추가 테스트"""
        jobs_data = {"existing-job": {}}
        data_file = tmp_path / "jobs.json"
        data_file.write_text(json.dumps(jobs_data))

        schedule = {"hour": 10, "minute": 30}

        with patch('cron_manager.DATA_FILE', data_file), \
             patch('cron_manager.init_dirs'):

            with pytest.raises(SystemExit):
                add_job("existing-job", "echo test", "/tmp", schedule)

    def test_add_job_launchctl_failure(self, tmp_path):
        """launchctl 등록 실패 테스트"""
        data_file = tmp_path / "jobs.json"
        data_file.write_text("{}")
        plist_dir = tmp_path / "plist"
        plist_dir.mkdir()

        schedule = {"hour": 10, "minute": 30}

        with patch('cron_manager.DATA_FILE', data_file), \
             patch('cron_manager.PLIST_DIR', plist_dir), \
             patch('cron_manager.LOG_DIR', tmp_path / "logs"), \
             patch('cron_manager.CRON_DIR', tmp_path), \
             patch('cron_manager.init_dirs'), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = MagicMock(
                returncode=1,
                stderr=b"launchctl error"
            )

            with pytest.raises(SystemExit):
                add_job("fail-job", "echo test", "/tmp", schedule)

            # plist 파일이 삭제되었는지 확인
            plist_file = plist_dir / "com.claude.cron.fail-job.plist"
            assert not plist_file.exists()


class TestRemoveJob:
    """remove_job 함수 테스트"""

    def test_remove_job_success(self, tmp_path):
        """작업 삭제 성공 테스트"""
        jobs_data = {"test-job": {"command": "echo test"}}
        data_file = tmp_path / "jobs.json"
        data_file.write_text(json.dumps(jobs_data))

        plist_dir = tmp_path / "plist"
        plist_dir.mkdir()
        plist_file = plist_dir / "com.claude.cron.test-job.plist"
        plist_file.write_text("plist content")

        with patch('cron_manager.DATA_FILE', data_file), \
             patch('cron_manager.PLIST_DIR', plist_dir), \
             patch('cron_manager.CRON_DIR', tmp_path), \
             patch('subprocess.run'):

            remove_job("test-job")

            # jobs.json에서 삭제되었는지 확인
            jobs = json.loads(data_file.read_text())
            assert "test-job" not in jobs

            # plist 파일 삭제 확인
            assert not plist_file.exists()

    def test_remove_nonexistent_job(self, tmp_path):
        """존재하지 않는 작업 삭제 테스트"""
        data_file = tmp_path / "jobs.json"
        data_file.write_text("{}")

        with patch('cron_manager.DATA_FILE', data_file), \
             patch('cron_manager.init_dirs'):

            with pytest.raises(SystemExit):
                remove_job("nonexistent")


class TestUpdateJob:
    """update_job 함수 테스트"""

    def test_update_command(self, tmp_path):
        """명령어 업데이트 테스트"""
        jobs_data = {
            "test-job": {
                "command": "echo old",
                "workdir": "/tmp",
                "schedule": {"hour": 10, "minute": 30},
                "notify": True
            }
        }
        data_file = tmp_path / "jobs.json"
        data_file.write_text(json.dumps(jobs_data))

        plist_dir = tmp_path / "plist"
        plist_dir.mkdir()

        with patch('cron_manager.DATA_FILE', data_file), \
             patch('cron_manager.PLIST_DIR', plist_dir), \
             patch('cron_manager.LOG_DIR', tmp_path / "logs"), \
             patch('cron_manager.CRON_DIR', tmp_path), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = MagicMock(returncode=0)

            update_job("test-job", command="echo new")

            # 업데이트 확인
            jobs = json.loads(data_file.read_text())
            assert jobs["test-job"]["command"] == "echo new"

    def test_update_nonexistent_job(self, tmp_path):
        """존재하지 않는 작업 업데이트 테스트"""
        data_file = tmp_path / "jobs.json"
        data_file.write_text("{}")

        with patch('cron_manager.DATA_FILE', data_file), \
             patch('cron_manager.init_dirs'):

            with pytest.raises(SystemExit):
                update_job("nonexistent", command="echo test")


class TestRunJob:
    """run_job 함수 테스트"""

    def test_run_job_success(self, tmp_path):
        """작업 실행 성공 테스트"""
        jobs_data = {"test-job": {}}
        data_file = tmp_path / "jobs.json"
        data_file.write_text(json.dumps(jobs_data))

        with patch('cron_manager.DATA_FILE', data_file), \
             patch('cron_manager.init_dirs'), \
             patch('subprocess.run') as mock_run:

            mock_run.return_value = MagicMock(returncode=0)

            run_job("test-job")

            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            assert "launchctl" in call_args
            assert "start" in call_args

    def test_run_nonexistent_job(self, tmp_path):
        """존재하지 않는 작업 실행 테스트"""
        data_file = tmp_path / "jobs.json"
        data_file.write_text("{}")

        with patch('cron_manager.DATA_FILE', data_file), \
             patch('cron_manager.init_dirs'):

            with pytest.raises(SystemExit):
                run_job("nonexistent")


class TestViewLogs:
    """view_logs 함수 테스트"""

    def test_view_logs_existing(self, tmp_path):
        """로그 조회 테스트"""
        log_file = tmp_path / "test-job.log"
        log_file.write_text("\n".join([f"line {i}" for i in range(100)]))

        with patch('cron_manager.LOG_DIR', tmp_path):
            # 에러 없이 실행되는지 확인
            view_logs("test-job", lines=10)

    def test_view_logs_nonexistent(self, tmp_path):
        """존재하지 않는 로그 조회 테스트"""
        with patch('cron_manager.LOG_DIR', tmp_path):
            # 에러 없이 실행되는지 확인
            view_logs("nonexistent")


class TestEdgeCases:
    """경계 케이스 테스트"""

    def test_parse_schedule_uppercase(self):
        """대문자 스케줄 파싱 테스트"""
        result = parse_schedule("MON 10:30")

        assert result["weekday"] == 1

    def test_generate_plist_special_characters(self, tmp_path):
        """특수문자가 포함된 명령어 plist 생성 테스트"""
        schedule = {"hour": 10, "minute": 30}

        with patch('cron_manager.LOG_DIR', tmp_path / "logs"), \
             patch('cron_manager.CRON_DIR', tmp_path):

            result = generate_plist(
                "special-job",
                "echo 'test & <xml>'",
                "/tmp",
                schedule,
                notify=False
            )

            # XML 이스케이프 확인
            assert "&amp;" in result

    def test_format_schedule_all_fields(self):
        """모든 필드가 있는 스케줄 형식화 테스트"""
        schedule = {
            "month": 12,
            "day": 25,
            "weekday": 5,
            "hour": 23,
            "minute": 59
        }
        result = format_schedule(schedule)

        assert "12월" in result
        assert "25일" in result
        assert "금요일" in result
        assert "23시" in result
        assert "59분" in result
