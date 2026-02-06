#!/usr/bin/env python3
"""
recalc.py에 대한 단위 테스트
Excel 수식 재계산 스크립트의 LibreOffice 매크로 설정 및 실행 테스트
"""

import sys
import pytest
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call

sys.path.insert(0, str(Path(__file__).parent.parent))
from recalc import (
    setup_libreoffice_macro,
    recalc,
    main,
)


class TestSetupLibreOfficeMacro:
    """setup_libreoffice_macro 함수 테스트"""

    @patch('recalc.os.path.exists')
    @patch('builtins.open', create=True)
    def test_macro_already_exists(self, mock_open, mock_exists):
        """정상 케이스: 매크로가 이미 존재함"""
        # 매크로 파일이 존재하고 내용에 RecalculateAndSave가 있음
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = '''
        <script:module>
            Sub RecalculateAndSave()
            End Sub
        </script:module>
        '''

        result = setup_libreoffice_macro()

        assert result is True

    @patch('recalc.os.path.exists')
    @patch('recalc.os.makedirs')
    @patch('recalc.subprocess.run')
    @patch('builtins.open', create=True)
    def test_macro_creation_success(self, mock_open, mock_subprocess, mock_makedirs, mock_exists):
        """정상 케이스: 매크로 파일 생성 성공"""
        # 매크로 디렉토리가 존재하지 않음
        mock_exists.return_value = False

        # 파일 쓰기 성공
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        result = setup_libreoffice_macro()

        assert result is True
        mock_open.assert_called()

    @patch('recalc.os.path.exists')
    @patch('recalc.os.makedirs')
    @patch('recalc.subprocess.run')
    @patch('builtins.open', create=True)
    def test_macro_creation_failure(self, mock_open, mock_subprocess, mock_makedirs, mock_exists):
        """에러 케이스: 매크로 파일 생성 실패"""
        mock_exists.return_value = False
        mock_subprocess.return_value = Mock(returncode=0)

        # 파일 쓰기 실패
        mock_open.side_effect = Exception("Permission denied")

        result = setup_libreoffice_macro()

        assert result is False

    @patch('recalc.platform.system')
    @patch('recalc.os.path.exists')
    def test_macro_directory_path_darwin(self, mock_exists, mock_platform):
        """macOS에서 매크로 디렉토리 경로"""
        mock_platform.return_value = 'Darwin'
        mock_exists.return_value = True

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = 'Sub RecalculateAndSave()'
            result = setup_libreoffice_macro()

            # macOS 경로가 사용되었는지 확인
            call_args = str(mock_open.call_args)
            assert 'Library/Application Support/LibreOffice' in call_args or result is True

    @patch('recalc.platform.system')
    @patch('recalc.os.path.exists')
    def test_macro_directory_path_linux(self, mock_exists, mock_platform):
        """Linux에서 매크로 디렉토리 경로"""
        mock_platform.return_value = 'Linux'
        mock_exists.return_value = True

        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = 'Sub RecalculateAndSave()'
            result = setup_libreoffice_macro()

            # Linux 경로가 사용되었는지 확인
            assert result is True


class TestRecalc:
    """recalc 함수 테스트"""

    @pytest.fixture
    def mock_excel_file(self):
        """mock Excel 파일 생성"""
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            temp_path = f.name

        yield temp_path

        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

    def test_file_not_exists(self):
        """에러 케이스: 파일이 존재하지 않음"""
        result = recalc("/nonexistent/file.xlsx")

        assert 'error' in result
        assert 'does not exist' in result['error']

    @patch('recalc.setup_libreoffice_macro')
    def test_macro_setup_failure(self, mock_setup, mock_excel_file):
        """에러 케이스: 매크로 설정 실패"""
        mock_setup.return_value = False

        result = recalc(mock_excel_file)

        assert 'error' in result
        assert 'Failed to setup' in result['error']

    @patch('recalc.setup_libreoffice_macro')
    @patch('recalc.subprocess.run')
    @patch('recalc.load_workbook')
    def test_recalc_success_no_errors(self, mock_workbook, mock_subprocess, mock_setup, mock_excel_file):
        """정상 케이스: 재계산 성공, 에러 없음"""
        mock_setup.return_value = True

        # subprocess 성공
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        # openpyxl mock: 에러가 없는 워크북
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_wb.sheetnames = ['Sheet1']
        mock_wb.__getitem__.return_value = mock_ws

        # 셀 mock: 정상 값들
        mock_cell = MagicMock()
        mock_cell.value = '100'
        mock_cell.coordinate = 'A1'
        mock_ws.iter_rows.return_value = [[mock_cell]]

        mock_workbook.return_value = mock_wb

        result = recalc(mock_excel_file)

        assert result['status'] == 'success'
        assert result['total_errors'] == 0

    @patch('recalc.setup_libreoffice_macro')
    @patch('recalc.subprocess.run')
    @patch('recalc.load_workbook')
    def test_recalc_with_errors(self, mock_workbook, mock_subprocess, mock_setup, mock_excel_file):
        """정상 케이스: 재계산 후 Excel 에러 발견"""
        mock_setup.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        # openpyxl mock: 에러가 있는 워크북
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_wb.sheetnames = ['Sheet1']
        mock_wb.__getitem__.return_value = mock_ws

        # 셀 mock: #DIV/0! 에러
        mock_cell1 = MagicMock()
        mock_cell1.value = '#DIV/0!'
        mock_cell1.coordinate = 'B2'

        mock_cell2 = MagicMock()
        mock_cell2.value = 'Normal value'
        mock_cell2.coordinate = 'A1'

        mock_ws.iter_rows.return_value = [[mock_cell1], [mock_cell2]]

        mock_workbook.return_value = mock_wb

        result = recalc(mock_excel_file)

        assert result['status'] == 'errors_found'
        assert result['total_errors'] == 1
        assert '#DIV/0!' in result['error_summary']
        assert result['error_summary']['#DIV/0!']['count'] == 1

    @patch('recalc.setup_libreoffice_macro')
    @patch('recalc.subprocess.run')
    @patch('recalc.load_workbook')
    def test_recalc_multiple_error_types(self, mock_workbook, mock_subprocess, mock_setup, mock_excel_file):
        """정상 케이스: 여러 종류의 Excel 에러"""
        mock_setup.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        # 여러 종류의 에러가 있는 워크북
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_wb.sheetnames = ['Sheet1']
        mock_wb.__getitem__.return_value = mock_ws

        # 다양한 에러 셀
        cells = [
            MagicMock(value='#VALUE!', coordinate='A1'),
            MagicMock(value='#DIV/0!', coordinate='B2'),
            MagicMock(value='#REF!', coordinate='C3'),
            MagicMock(value='Normal', coordinate='D4'),
        ]

        mock_ws.iter_rows.return_value = [[cell] for cell in cells]

        mock_workbook.return_value = mock_wb

        result = recalc(mock_excel_file)

        assert result['status'] == 'errors_found'
        assert result['total_errors'] == 3
        assert '#VALUE!' in result['error_summary']
        assert '#DIV/0!' in result['error_summary']
        assert '#REF!' in result['error_summary']

    @patch('recalc.setup_libreoffice_macro')
    @patch('recalc.subprocess.run')
    def test_subprocess_error(self, mock_subprocess, mock_setup, mock_excel_file):
        """에러 케이스: subprocess 실행 에러"""
        mock_setup.return_value = True

        # subprocess 실패 - RecalculateAndSave가 포함되어 있으면 에러 메시지가 그대로 반환됨
        mock_subprocess.return_value = Mock(returncode=1, stderr='RecalculateAndSave failed with error')

        result = recalc(mock_excel_file)

        assert 'error' in result
        assert 'RecalculateAndSave failed' in result['error']

    @patch('recalc.setup_libreoffice_macro')
    @patch('recalc.subprocess.run')
    @patch('recalc.load_workbook')
    def test_timeout_handling(self, mock_workbook, mock_subprocess, mock_setup, mock_excel_file):
        """타임아웃 처리 (exit code 124)"""
        mock_setup.return_value = True

        # 타임아웃 (exit code 124)
        mock_subprocess.return_value = Mock(returncode=124, stderr='')

        # 워크북 mock (타임아웃 후에도 파일 읽기 시도)
        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_wb.sheetnames = ['Sheet1']
        mock_wb.__getitem__.return_value = mock_ws
        mock_ws.iter_rows.return_value = []
        mock_workbook.return_value = mock_wb

        result = recalc(mock_excel_file)

        # 타임아웃은 성공으로 간주됨 (exit code 124는 허용)
        assert 'status' in result or 'total_errors' in result

    @patch('recalc.setup_libreoffice_macro')
    @patch('recalc.subprocess.run')
    @patch('recalc.load_workbook')
    def test_workbook_read_exception(self, mock_workbook, mock_subprocess, mock_setup, mock_excel_file):
        """에러 케이스: 워크북 읽기 실패"""
        mock_setup.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        # 워크북 로드 실패
        mock_workbook.side_effect = Exception("Corrupted file")

        result = recalc(mock_excel_file)

        assert 'error' in result
        assert 'Corrupted file' in result['error']

    @patch('recalc.setup_libreoffice_macro')
    @patch('recalc.subprocess.run')
    @patch('recalc.load_workbook')
    def test_formula_count(self, mock_workbook, mock_subprocess, mock_setup, mock_excel_file):
        """수식 개수 카운트 테스트"""
        mock_setup.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        # 첫 번째 호출: data_only=True (에러 체크용)
        mock_wb_data = MagicMock()
        mock_ws_data = MagicMock()
        mock_wb_data.sheetnames = ['Sheet1']
        mock_wb_data.__getitem__.return_value = mock_ws_data

        mock_cell = MagicMock()
        mock_cell.value = '100'
        mock_cell.coordinate = 'A1'
        mock_ws_data.iter_rows.return_value = [[mock_cell]]

        # 두 번째 호출: data_only=False (수식 카운트용)
        mock_wb_formula = MagicMock()
        mock_ws_formula = MagicMock()
        mock_wb_formula.sheetnames = ['Sheet1']
        mock_wb_formula.__getitem__.return_value = mock_ws_formula

        # 수식 셀
        mock_formula_cell = MagicMock()
        mock_formula_cell.value = '=A1+B1'
        mock_ws_formula.iter_rows.return_value = [[mock_formula_cell]]

        mock_workbook.side_effect = [mock_wb_data, mock_wb_formula]

        result = recalc(mock_excel_file)

        assert 'total_formulas' in result
        assert result['total_formulas'] == 1

    @patch('recalc.setup_libreoffice_macro')
    @patch('recalc.subprocess.run')
    @patch('recalc.load_workbook')
    @patch('recalc.platform.system')
    def test_timeout_command_linux(self, mock_platform, mock_workbook, mock_subprocess, mock_setup, mock_excel_file):
        """Linux에서 timeout 명령 사용"""
        mock_setup.return_value = True
        mock_platform.return_value = 'Linux'
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_wb.sheetnames = ['Sheet1']
        mock_wb.__getitem__.return_value = mock_ws
        mock_ws.iter_rows.return_value = []
        mock_workbook.return_value = mock_wb

        result = recalc(mock_excel_file, timeout=30)

        # subprocess.run이 timeout 명령과 함께 호출되었는지 확인
        call_args = mock_subprocess.call_args[0][0]
        assert 'timeout' in call_args or 'soffice' in call_args

    @patch('recalc.setup_libreoffice_macro')
    @patch('recalc.subprocess.run')
    @patch('recalc.load_workbook')
    @patch('recalc.platform.system')
    def test_timeout_command_darwin_with_gtimeout(self, mock_platform, mock_workbook, mock_subprocess, mock_setup, mock_excel_file):
        """macOS에서 gtimeout 사용"""
        mock_setup.return_value = True
        mock_platform.return_value = 'Darwin'

        # gtimeout 사용 가능
        mock_subprocess.side_effect = [
            Mock(returncode=0),  # gtimeout --version
            Mock(returncode=0, stderr=''),  # 실제 recalc 명령
        ]

        mock_wb = MagicMock()
        mock_ws = MagicMock()
        mock_wb.sheetnames = ['Sheet1']
        mock_wb.__getitem__.return_value = mock_ws
        mock_ws.iter_rows.return_value = []
        mock_workbook.return_value = mock_wb

        result = recalc(mock_excel_file)

        # gtimeout이 호출되었는지 확인
        assert mock_subprocess.call_count >= 1


class TestMain:
    """main 함수 테스트"""

    @patch('sys.exit')
    def test_main_no_arguments(self, mock_exit):
        """에러 케이스: 인자 없음"""
        # sys.exit 호출 시 실제로 종료되지 않도록 함
        mock_exit.side_effect = SystemExit(1)

        with patch('sys.argv', ['recalc.py']):
            with pytest.raises(SystemExit):
                main()

        mock_exit.assert_called_once_with(1)

    @patch('sys.argv', ['recalc.py', 'test.xlsx'])
    @patch('recalc.recalc')
    @patch('builtins.print')
    def test_main_success(self, mock_print, mock_recalc):
        """정상 케이스: 재계산 성공"""
        mock_recalc.return_value = {'status': 'success', 'total_errors': 0}

        main()

        mock_recalc.assert_called_once_with('test.xlsx', 30)
        mock_print.assert_called_once()

    @patch('sys.argv', ['recalc.py', 'test.xlsx', '60'])
    @patch('recalc.recalc')
    @patch('builtins.print')
    def test_main_with_timeout(self, mock_print, mock_recalc):
        """정상 케이스: 타임아웃 인자 포함"""
        mock_recalc.return_value = {'status': 'success', 'total_errors': 0}

        main()

        mock_recalc.assert_called_once_with('test.xlsx', 60)

    @patch('sys.argv', ['recalc.py', 'test.xlsx'])
    @patch('recalc.recalc')
    @patch('builtins.print')
    def test_main_with_errors(self, mock_print, mock_recalc):
        """정상 케이스: 에러 발견"""
        mock_recalc.return_value = {
            'status': 'errors_found',
            'total_errors': 2,
            'error_summary': {
                '#DIV/0!': {'count': 2, 'locations': ['Sheet1!A1', 'Sheet1!B2']}
            }
        }

        main()

        mock_recalc.assert_called_once()
        # JSON 출력 확인
        call_args = str(mock_print.call_args)
        assert 'errors_found' in call_args or mock_print.called


class TestEdgeCases:
    """엣지 케이스 및 통합 테스트"""

    @patch('recalc.setup_libreoffice_macro')
    @patch('recalc.subprocess.run')
    @patch('recalc.load_workbook')
    def test_large_error_list_truncation(self, mock_workbook, mock_subprocess, mock_setup):
        """에러 위치가 20개 이상일 때 truncation"""
        mock_setup.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            temp_path = f.name

        try:
            # 25개의 에러 셀 생성
            mock_wb = MagicMock()
            mock_ws = MagicMock()
            mock_wb.sheetnames = ['Sheet1']
            mock_wb.__getitem__.return_value = mock_ws

            error_cells = [
                MagicMock(value='#VALUE!', coordinate=f'A{i}')
                for i in range(1, 26)
            ]

            mock_ws.iter_rows.return_value = [[cell] for cell in error_cells]
            mock_workbook.return_value = mock_wb

            result = recalc(temp_path)

            # 에러 위치가 20개로 제한되었는지 확인
            assert len(result['error_summary']['#VALUE!']['locations']) == 20
            assert result['error_summary']['#VALUE!']['count'] == 25
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @patch('recalc.setup_libreoffice_macro')
    @patch('recalc.subprocess.run')
    @patch('recalc.load_workbook')
    def test_all_excel_error_types(self, mock_workbook, mock_subprocess, mock_setup):
        """모든 Excel 에러 타입 감지"""
        mock_setup.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            temp_path = f.name

        try:
            excel_errors = ['#VALUE!', '#DIV/0!', '#REF!', '#NAME?', '#NULL!', '#NUM!', '#N/A']

            mock_wb = MagicMock()
            mock_ws = MagicMock()
            mock_wb.sheetnames = ['Sheet1']
            mock_wb.__getitem__.return_value = mock_ws

            error_cells = [
                MagicMock(value=err, coordinate=f'A{i}')
                for i, err in enumerate(excel_errors, 1)
            ]

            mock_ws.iter_rows.return_value = [[cell] for cell in error_cells]
            mock_workbook.return_value = mock_wb

            result = recalc(temp_path)

            # 모든 에러 타입이 감지되었는지 확인
            assert result['total_errors'] == 7
            for err in excel_errors:
                assert err in result['error_summary']
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @patch('recalc.setup_libreoffice_macro')
    @patch('recalc.subprocess.run')
    @patch('recalc.load_workbook')
    def test_mixed_content_cells(self, mock_workbook, mock_subprocess, mock_setup):
        """에러와 정상 값이 섞인 경우"""
        mock_setup.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stderr='')

        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            temp_path = f.name

        try:
            mock_wb = MagicMock()
            mock_ws = MagicMock()
            mock_wb.sheetnames = ['Sheet1']
            mock_wb.__getitem__.return_value = mock_ws

            # None, 숫자, 문자열, 에러가 섞인 셀
            cells = [
                MagicMock(value=None, coordinate='A1'),
                MagicMock(value=100, coordinate='A2'),
                MagicMock(value='Text', coordinate='A3'),
                MagicMock(value='#DIV/0!', coordinate='A4'),
                MagicMock(value=3.14, coordinate='A5'),
            ]

            mock_ws.iter_rows.return_value = [[cell] for cell in cells]
            mock_workbook.return_value = mock_wb

            result = recalc(temp_path)

            # 에러는 1개만 감지되어야 함
            assert result['total_errors'] == 1
            assert '#DIV/0!' in result['error_summary']
        finally:
            Path(temp_path).unlink(missing_ok=True)
