#!/usr/bin/env python3
"""
with_server.py 단위 테스트
pytest로 서버 관리 기능 검증
"""

import sys
import socket
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

# 테스트 대상 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from with_server import is_server_ready, main


class TestIsServerReady:
    """is_server_ready 함수 테스트"""

    def test_server_ready_immediately(self):
        """서버가 즉시 준비된 경우 테스트"""
        with patch('socket.create_connection') as mock_conn:
            mock_conn.return_value.__enter__ = MagicMock()
            mock_conn.return_value.__exit__ = MagicMock()

            result = is_server_ready(8080, timeout=1)

            assert result is True
            mock_conn.assert_called_once_with(('localhost', 8080), timeout=1)

    def test_server_ready_after_retry(self):
        """서버가 재시도 후 준비된 경우 테스트"""
        with patch('socket.create_connection') as mock_conn, \
             patch('time.sleep'):
            # 처음 2번은 실패, 3번째는 성공
            mock_conn.side_effect = [
                ConnectionRefusedError(),
                ConnectionRefusedError(),
                MagicMock(__enter__=MagicMock(), __exit__=MagicMock())
            ]

            result = is_server_ready(8080, timeout=10)

            assert result is True
            assert mock_conn.call_count == 3

    def test_server_not_ready_timeout(self):
        """타임아웃까지 서버가 준비되지 않은 경우 테스트"""
        with patch('socket.create_connection') as mock_conn, \
             patch('time.sleep'), \
             patch('time.time') as mock_time:
            # 타임아웃 시뮬레이션
            mock_time.side_effect = [0, 1, 2, 35]  # 30초 타임아웃 초과
            mock_conn.side_effect = ConnectionRefusedError()

            result = is_server_ready(8080, timeout=30)

            assert result is False

    def test_socket_error(self):
        """소켓 에러 발생 테스트"""
        with patch('socket.create_connection') as mock_conn, \
             patch('time.sleep'), \
             patch('time.time') as mock_time:
            mock_time.side_effect = [0, 1, 35]
            mock_conn.side_effect = socket.error("Network unreachable")

            result = is_server_ready(8080, timeout=30)

            assert result is False

    def test_custom_timeout(self):
        """커스텀 타임아웃 테스트"""
        with patch('socket.create_connection') as mock_conn, \
             patch('time.sleep'), \
             patch('time.time') as mock_time:
            mock_time.side_effect = [0, 1, 6]  # 5초 타임아웃
            mock_conn.side_effect = ConnectionRefusedError()

            result = is_server_ready(8080, timeout=5)

            assert result is False


class TestMain:
    """main 함수 테스트"""

    def test_single_server_success(self):
        """단일 서버 성공 테스트"""
        test_args = [
            'with_server.py',
            '--server', 'python server.py',
            '--port', '8080',
            '--',
            'python', 'test.py'
        ]

        with patch('sys.argv', test_args), \
             patch('subprocess.Popen') as mock_popen, \
             patch('subprocess.run') as mock_run, \
             patch('with_server.is_server_ready', return_value=True):

            mock_process = MagicMock()
            mock_popen.return_value = mock_process
            mock_run.return_value = MagicMock(returncode=0)

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            mock_popen.assert_called_once()
            mock_run.assert_called_once_with(['python', 'test.py'])

            # 서버 프로세스가 종료되었는지 확인
            mock_process.terminate.assert_called_once()

    def test_multiple_servers_success(self):
        """여러 서버 성공 테스트"""
        test_args = [
            'with_server.py',
            '--server', 'python backend.py',
            '--port', '3000',
            '--server', 'npm run dev',
            '--port', '5173',
            '--',
            'python', 'test.py'
        ]

        with patch('sys.argv', test_args), \
             patch('subprocess.Popen') as mock_popen, \
             patch('subprocess.run') as mock_run, \
             patch('with_server.is_server_ready', return_value=True):

            mock_popen.return_value = MagicMock()
            mock_run.return_value = MagicMock(returncode=0)

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            assert mock_popen.call_count == 2

    def test_server_failed_to_start(self):
        """서버 시작 실패 테스트"""
        test_args = [
            'with_server.py',
            '--server', 'python server.py',
            '--port', '8080',
            '--',
            'python', 'test.py'
        ]

        with patch('sys.argv', test_args), \
             patch('subprocess.Popen') as mock_popen, \
             patch('with_server.is_server_ready', return_value=False):

            mock_popen.return_value = MagicMock()

            with pytest.raises(RuntimeError, match="Server failed to start"):
                main()

    def test_missing_command(self):
        """명령어 없이 실행 테스트"""
        test_args = [
            'with_server.py',
            '--server', 'python server.py',
            '--port', '8080',
            '--'
        ]

        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_mismatched_server_port_count(self):
        """서버와 포트 개수 불일치 테스트"""
        test_args = [
            'with_server.py',
            '--server', 'python server.py',
            '--port', '8080',
            '--port', '9090',
            '--',
            'python', 'test.py'
        ]

        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_command_execution_failure(self):
        """명령어 실행 실패 테스트"""
        test_args = [
            'with_server.py',
            '--server', 'python server.py',
            '--port', '8080',
            '--',
            'python', 'failing_test.py'
        ]

        with patch('sys.argv', test_args), \
             patch('subprocess.Popen') as mock_popen, \
             patch('subprocess.run') as mock_run, \
             patch('with_server.is_server_ready', return_value=True):

            mock_process = MagicMock()
            mock_popen.return_value = mock_process
            mock_run.return_value = MagicMock(returncode=1)

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1

    def test_server_cleanup_on_success(self):
        """성공 후 서버 정리 테스트"""
        test_args = [
            'with_server.py',
            '--server', 'python server.py',
            '--port', '8080',
            '--',
            'echo', 'test'
        ]

        with patch('sys.argv', test_args), \
             patch('subprocess.Popen') as mock_popen, \
             patch('subprocess.run') as mock_run, \
             patch('with_server.is_server_ready', return_value=True):

            mock_process = MagicMock()
            mock_popen.return_value = mock_process
            mock_run.return_value = MagicMock(returncode=0)

            with pytest.raises(SystemExit):
                main()

            # 서버가 정리되었는지 확인
            mock_process.terminate.assert_called_once()
            mock_process.wait.assert_called()

    def test_server_cleanup_on_failure(self):
        """실패 시 서버 정리 테스트"""
        test_args = [
            'with_server.py',
            '--server', 'python server.py',
            '--port', '8080',
            '--',
            'python', 'test.py'
        ]

        with patch('sys.argv', test_args), \
             patch('subprocess.Popen') as mock_popen, \
             patch('subprocess.run') as mock_run, \
             patch('with_server.is_server_ready', return_value=True):

            mock_process = MagicMock()
            mock_popen.return_value = mock_process
            mock_run.side_effect = KeyboardInterrupt()

            with pytest.raises(KeyboardInterrupt):
                main()

            # 예외 발생 시에도 서버가 정리되어야 함
            mock_process.terminate.assert_called_once()

    def test_process_kill_on_terminate_timeout(self):
        """terminate 타임아웃 시 kill 테스트"""
        test_args = [
            'with_server.py',
            '--server', 'python server.py',
            '--port', '8080',
            '--',
            'echo', 'test'
        ]

        with patch('sys.argv', test_args), \
             patch('subprocess.Popen') as mock_popen, \
             patch('subprocess.run') as mock_run, \
             patch('with_server.is_server_ready', return_value=True):

            mock_process = MagicMock()
            mock_process.wait.side_effect = [
                subprocess.TimeoutExpired('cmd', 5),
                None
            ]
            mock_popen.return_value = mock_process
            mock_run.return_value = MagicMock(returncode=0)

            with pytest.raises(SystemExit):
                main()

            # terminate 후 kill이 호출되어야 함
            mock_process.terminate.assert_called_once()
            mock_process.kill.assert_called_once()

    def test_custom_timeout(self):
        """커스텀 타임아웃 테스트"""
        test_args = [
            'with_server.py',
            '--server', 'python slow_server.py',
            '--port', '8080',
            '--timeout', '60',
            '--',
            'python', 'test.py'
        ]

        with patch('sys.argv', test_args), \
             patch('subprocess.Popen') as mock_popen, \
             patch('subprocess.run') as mock_run, \
             patch('with_server.is_server_ready') as mock_ready:

            mock_ready.return_value = True
            mock_popen.return_value = MagicMock()
            mock_run.return_value = MagicMock(returncode=0)

            with pytest.raises(SystemExit):
                main()

            # 커스텀 타임아웃이 전달되었는지 확인
            mock_ready.assert_called_with(8080, timeout=60)

    def test_shell_command_with_cd(self):
        """cd가 포함된 쉘 명령어 테스트"""
        test_args = [
            'with_server.py',
            '--server', 'cd backend && python server.py',
            '--port', '8080',
            '--',
            'python', 'test.py'
        ]

        with patch('sys.argv', test_args), \
             patch('subprocess.Popen') as mock_popen, \
             patch('subprocess.run') as mock_run, \
             patch('with_server.is_server_ready', return_value=True):

            mock_popen.return_value = MagicMock()
            mock_run.return_value = MagicMock(returncode=0)

            with pytest.raises(SystemExit):
                main()

            # shell=True로 호출되었는지 확인
            call_kwargs = mock_popen.call_args[1]
            assert call_kwargs['shell'] is True


class TestEdgeCases:
    """경계 케이스 테스트"""

    def test_port_zero(self):
        """포트 0 테스트"""
        test_args = [
            'with_server.py',
            '--server', 'python server.py',
            '--port', '0',
            '--',
            'python', 'test.py'
        ]

        with patch('sys.argv', test_args), \
             patch('subprocess.Popen') as mock_popen, \
             patch('subprocess.run') as mock_run, \
             patch('with_server.is_server_ready', return_value=True):

            mock_popen.return_value = MagicMock()
            mock_run.return_value = MagicMock(returncode=0)

            with pytest.raises(SystemExit):
                main()

    def test_very_high_port(self):
        """매우 높은 포트 번호 테스트"""
        test_args = [
            'with_server.py',
            '--server', 'python server.py',
            '--port', '65535',
            '--',
            'python', 'test.py'
        ]

        with patch('sys.argv', test_args), \
             patch('subprocess.Popen') as mock_popen, \
             patch('subprocess.run') as mock_run, \
             patch('with_server.is_server_ready', return_value=True):

            mock_popen.return_value = MagicMock()
            mock_run.return_value = MagicMock(returncode=0)

            with pytest.raises(SystemExit):
                main()

    def test_no_arguments(self):
        """인자 없이 실행 테스트"""
        test_args = ['with_server.py']

        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit):
                main()

    def test_empty_command_after_separator(self):
        """구분자 후 빈 명령어 테스트"""
        test_args = [
            'with_server.py',
            '--server', 'python server.py',
            '--port', '8080',
            '--'
        ]

        with patch('sys.argv', test_args):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_multiple_processes_cleanup(self):
        """여러 프로세스 정리 테스트"""
        test_args = [
            'with_server.py',
            '--server', 'python backend.py',
            '--port', '3000',
            '--server', 'npm run dev',
            '--port', '5173',
            '--server', 'python api.py',
            '--port', '8080',
            '--',
            'python', 'test.py'
        ]

        with patch('sys.argv', test_args), \
             patch('subprocess.Popen') as mock_popen, \
             patch('subprocess.run') as mock_run, \
             patch('with_server.is_server_ready', return_value=True):

            mock_processes = [MagicMock() for _ in range(3)]
            mock_popen.side_effect = mock_processes
            mock_run.return_value = MagicMock(returncode=0)

            with pytest.raises(SystemExit):
                main()

            # 모든 프로세스가 정리되었는지 확인
            for process in mock_processes:
                process.terminate.assert_called_once()
                process.wait.assert_called()

    def test_server_start_exception(self):
        """서버 시작 중 예외 발생 테스트"""
        test_args = [
            'with_server.py',
            '--server', 'python server.py',
            '--port', '8080',
            '--',
            'python', 'test.py'
        ]

        with patch('sys.argv', test_args), \
             patch('subprocess.Popen') as mock_popen:

            mock_popen.side_effect = OSError("Failed to start process")

            with pytest.raises(OSError):
                main()
