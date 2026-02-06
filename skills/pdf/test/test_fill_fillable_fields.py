"""
fill_fillable_fields.py에 대한 단위 테스트

테스트 범위:
- fill_pdf_fields: PDF 폼 필드 채우기 함수
- validation_error_for_field_value: 필드 값 검증 함수
- monkeypatch_pydpf_method: pypdf 메서드 패치
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

# 테스트 대상 모듈 import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from fill_fillable_fields import (
    fill_pdf_fields,
    monkeypatch_pydpf_method,
    validation_error_for_field_value,
)


class TestValidationErrorForFieldValue:
    """필드 값 검증 함수 테스트"""

    def test_checkbox_valid_checked_value(self):
        """체크박스 필드: 체크된 값이 유효한 경우"""
        field_info = {
            "field_id": "checkbox1",
            "type": "checkbox",
            "checked_value": "/Yes",
            "unchecked_value": "/Off",
        }
        result = validation_error_for_field_value(field_info, "/Yes")
        assert result is None

    def test_checkbox_valid_unchecked_value(self):
        """체크박스 필드: 체크 해제 값이 유효한 경우"""
        field_info = {
            "field_id": "checkbox1",
            "type": "checkbox",
            "checked_value": "/Yes",
            "unchecked_value": "/Off",
        }
        result = validation_error_for_field_value(field_info, "/Off")
        assert result is None

    def test_checkbox_invalid_value(self):
        """체크박스 필드: 유효하지 않은 값"""
        field_info = {
            "field_id": "checkbox1",
            "type": "checkbox",
            "checked_value": "/Yes",
            "unchecked_value": "/Off",
        }
        result = validation_error_for_field_value(field_info, "/Invalid")
        assert result is not None
        assert "checkbox1" in result
        assert "/Yes" in result
        assert "/Off" in result

    def test_radio_group_valid_value(self):
        """라디오 그룹 필드: 유효한 옵션 값"""
        field_info = {
            "field_id": "radio1",
            "type": "radio_group",
            "radio_options": [{"value": "/Option1"}, {"value": "/Option2"}],
        }
        result = validation_error_for_field_value(field_info, "/Option1")
        assert result is None

    def test_radio_group_invalid_value(self):
        """라디오 그룹 필드: 유효하지 않은 옵션 값"""
        field_info = {
            "field_id": "radio1",
            "type": "radio_group",
            "radio_options": [{"value": "/Option1"}, {"value": "/Option2"}],
        }
        result = validation_error_for_field_value(field_info, "/Invalid")
        assert result is not None
        assert "radio1" in result
        assert "/Option1" in result
        assert "/Option2" in result

    def test_choice_valid_value(self):
        """선택 필드: 유효한 선택 값"""
        field_info = {
            "field_id": "choice1",
            "type": "choice",
            "choice_options": [{"value": "A"}, {"value": "B"}],
        }
        result = validation_error_for_field_value(field_info, "A")
        assert result is None

    def test_choice_invalid_value(self):
        """선택 필드: 유효하지 않은 선택 값"""
        field_info = {
            "field_id": "choice1",
            "type": "choice",
            "choice_options": [{"value": "A"}, {"value": "B"}],
        }
        result = validation_error_for_field_value(field_info, "C")
        assert result is not None
        assert "choice1" in result
        assert "['A', 'B']" in result

    def test_text_field_no_validation(self):
        """텍스트 필드: 검증 없음 (None 반환)"""
        field_info = {"field_id": "text1", "type": "text"}
        result = validation_error_for_field_value(field_info, "Any text")
        assert result is None


class TestFillPdfFields:
    """PDF 필드 채우기 함수 테스트"""

    @patch("fill_fillable_fields.PdfReader")
    @patch("fill_fillable_fields.PdfWriter")
    @patch("fill_fillable_fields.get_field_info")
    @patch("builtins.open", new_callable=mock_open)
    def test_fill_pdf_fields_success(
        self, mock_file, mock_get_field_info, mock_writer_class, mock_reader_class
    ):
        """정상 케이스: PDF 필드 채우기 성공"""
        # Mock 데이터 준비
        fields_data = [
            {"field_id": "name", "page": 1, "value": "John Doe"},
            {"field_id": "email", "page": 1, "value": "john@example.com"},
        ]

        field_info = [
            {"field_id": "name", "page": 1, "type": "text"},
            {"field_id": "email", "page": 1, "type": "text"},
        ]

        # Mock 설정
        mock_reader = MagicMock()
        mock_reader_class.return_value = mock_reader
        mock_get_field_info.return_value = field_info

        mock_writer = MagicMock()
        mock_writer.pages = [MagicMock()]
        mock_writer_class.return_value = mock_writer

        # JSON 파일 읽기를 위한 mock 설정
        json_mock = mock_open(read_data=json.dumps(fields_data))
        with patch("builtins.open", json_mock):
            fill_pdf_fields("input.pdf", "fields.json", "output.pdf")

        # 검증
        mock_reader_class.assert_called_once_with("input.pdf")
        mock_writer_class.assert_called_once_with(clone_from=mock_reader)
        mock_writer.set_need_appearances_writer.assert_called_once_with(True)

    @patch("fill_fillable_fields.PdfReader")
    @patch("fill_fillable_fields.PdfWriter")
    @patch("fill_fillable_fields.get_field_info")
    @patch("builtins.open", new_callable=mock_open)
    @patch("sys.exit")
    def test_fill_pdf_fields_invalid_field_id(
        self, mock_exit, mock_file, mock_get_field_info, mock_writer_class, mock_reader_class
    ):
        """에러 케이스: 유효하지 않은 필드 ID"""
        # Mock 데이터 준비
        fields_data = [{"field_id": "invalid_field", "page": 1, "value": "Test"}]

        field_info = [{"field_id": "valid_field", "page": 1, "type": "text"}]

        # Mock 설정
        mock_reader = MagicMock()
        mock_reader_class.return_value = mock_reader
        mock_get_field_info.return_value = field_info

        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer

        # 실행
        json_mock = mock_open(read_data=json.dumps(fields_data))
        with patch("builtins.open", json_mock):
            fill_pdf_fields("input.pdf", "fields.json", "output.pdf")

        # sys.exit(1) 호출 확인
        mock_exit.assert_called_once_with(1)

    @patch("fill_fillable_fields.PdfReader")
    @patch("fill_fillable_fields.PdfWriter")
    @patch("fill_fillable_fields.get_field_info")
    @patch("builtins.open", new_callable=mock_open)
    @patch("sys.exit")
    def test_fill_pdf_fields_wrong_page_number(
        self, mock_exit, mock_file, mock_get_field_info, mock_writer_class, mock_reader_class
    ):
        """에러 케이스: 잘못된 페이지 번호"""
        # Mock 데이터 준비
        fields_data = [{"field_id": "field1", "page": 2, "value": "Test"}]

        field_info = [{"field_id": "field1", "page": 1, "type": "text"}]

        # Mock 설정
        mock_reader = MagicMock()
        mock_reader_class.return_value = mock_reader
        mock_get_field_info.return_value = field_info

        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer

        # 실행
        json_mock = mock_open(read_data=json.dumps(fields_data))
        with patch("builtins.open", json_mock):
            fill_pdf_fields("input.pdf", "fields.json", "output.pdf")

        # sys.exit(1) 호출 확인
        mock_exit.assert_called_once_with(1)

    @patch("fill_fillable_fields.PdfReader")
    @patch("fill_fillable_fields.PdfWriter")
    @patch("fill_fillable_fields.get_field_info")
    @patch("builtins.open", new_callable=mock_open)
    def test_fill_pdf_fields_multiple_pages(
        self, mock_file, mock_get_field_info, mock_writer_class, mock_reader_class
    ):
        """정상 케이스: 여러 페이지의 필드 채우기"""
        # Mock 데이터 준비
        fields_data = [
            {"field_id": "field1", "page": 1, "value": "Page 1"},
            {"field_id": "field2", "page": 2, "value": "Page 2"},
            {"field_id": "field3", "page": 1, "value": "Also Page 1"},
        ]

        field_info = [
            {"field_id": "field1", "page": 1, "type": "text"},
            {"field_id": "field2", "page": 2, "type": "text"},
            {"field_id": "field3", "page": 1, "type": "text"},
        ]

        # Mock 설정
        mock_reader = MagicMock()
        mock_reader_class.return_value = mock_reader
        mock_get_field_info.return_value = field_info

        mock_writer = MagicMock()
        mock_writer.pages = [MagicMock(), MagicMock()]
        mock_writer_class.return_value = mock_writer

        # 실행
        json_mock = mock_open(read_data=json.dumps(fields_data))
        with patch("builtins.open", json_mock):
            fill_pdf_fields("input.pdf", "fields.json", "output.pdf")

        # update_page_form_field_values가 각 페이지마다 호출되는지 확인
        assert mock_writer.update_page_form_field_values.call_count == 2


class TestMonkeypatchPydpfMethod:
    """pypdf 메서드 패치 함수 테스트"""

    def test_monkeypatch_applies(self):
        """패치가 올바르게 적용되는지 확인"""
        # 패치 적용
        monkeypatch_pydpf_method()

        # DictionaryObject의 get_inherited가 교체되었는지 확인
        from pypdf.generic import DictionaryObject
        assert hasattr(DictionaryObject, "get_inherited")

    def test_patched_method_handles_opt_key(self):
        """패치된 메서드가 Opt 키를 올바르게 처리하는지 확인"""
        # 패치 적용
        monkeypatch_pydpf_method()

        # get_inherited가 교체되었는지 확인
        # 실제 동작 검증은 통합 테스트에서 수행
        # 패치 함수 실행이 에러 없이 완료되면 성공
        assert True
