"""
fill_pdf_form_with_annotations.py에 대한 단위 테스트

테스트 범위:
- transform_coordinates: 이미지 좌표를 PDF 좌표로 변환
- fill_pdf_form: PDF 폼을 어노테이션으로 채우기
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# 테스트 대상 모듈 import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from fill_pdf_form_with_annotations import fill_pdf_form, transform_coordinates


class TestTransformCoordinates:
    """좌표 변환 함수 테스트"""

    def test_transform_coordinates_simple(self):
        """정상 케이스: 기본 좌표 변환"""
        # 이미지: 1000x800, PDF: 500x400
        # bbox: [100, 200, 300, 400] (left, top, right, bottom)
        bbox = [100, 200, 300, 400]
        result = transform_coordinates(bbox, 1000, 800, 500, 400)

        # X 스케일: 500/1000 = 0.5
        # Y 스케일: 400/800 = 0.5
        # left = 100 * 0.5 = 50
        # right = 300 * 0.5 = 150
        # top_pdf = 400 - (200 * 0.5) = 300
        # bottom_pdf = 400 - (400 * 0.5) = 200
        left, bottom, right, top = result
        assert left == 50
        assert right == 150
        assert bottom == 200
        assert top == 300

    def test_transform_coordinates_y_flip(self):
        """정상 케이스: Y 좌표 반전 확인"""
        # Y 좌표는 이미지(위=0)와 PDF(아래=0)가 반대
        bbox = [0, 0, 100, 100]
        result = transform_coordinates(bbox, 200, 200, 200, 200)

        left, bottom, right, top = result
        # 스케일 1:1
        assert left == 0
        assert right == 100
        # Y 반전: top_pdf = 200 - 0 = 200, bottom_pdf = 200 - 100 = 100
        assert bottom == 100
        assert top == 200

    def test_transform_coordinates_different_scales(self):
        """정상 케이스: X, Y 스케일이 다른 경우"""
        # 이미지: 1000x500, PDF: 500x1000 (비율이 반대)
        bbox = [100, 50, 200, 150]
        result = transform_coordinates(bbox, 1000, 500, 500, 1000)

        # X 스케일: 500/1000 = 0.5
        # Y 스케일: 1000/500 = 2.0
        left, bottom, right, top = result
        assert left == 50  # 100 * 0.5
        assert right == 100  # 200 * 0.5
        assert bottom == 700  # 1000 - (150 * 2.0) = 700
        assert top == 900  # 1000 - (50 * 2.0) = 900

    def test_transform_coordinates_zero_position(self):
        """경계 케이스: 원점(0,0) 위치"""
        bbox = [0, 0, 50, 50]
        result = transform_coordinates(bbox, 100, 100, 100, 100)

        left, bottom, right, top = result
        assert left == 0
        assert right == 50
        assert bottom == 50
        assert top == 100


class TestFillPdfForm:
    """PDF 폼 채우기 함수 테스트"""

    @patch("fill_pdf_form_with_annotations.PdfReader")
    @patch("fill_pdf_form_with_annotations.PdfWriter")
    @patch("fill_pdf_form_with_annotations.FreeText")
    @patch("builtins.open", new_callable=mock_open)
    def test_fill_pdf_form_single_field(
        self, mock_file, mock_freetext_class, mock_writer_class, mock_reader_class
    ):
        """정상 케이스: 단일 필드 채우기"""
        # Mock 데이터 준비
        fields_data = {
            "pages": [{"page_number": 1, "image_width": 1000, "image_height": 800}],
            "form_fields": [
                {
                    "page_number": 1,
                    "entry_bounding_box": [100, 200, 300, 250],
                    "entry_text": {
                        "text": "John Doe",
                        "font": "Arial",
                        "font_size": 12,
                        "font_color": "000000",
                    },
                }
            ],
        }

        # Mock 설정
        json_content = json.dumps(fields_data)
        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock()]
        mock_reader.pages[0].mediabox.width = 500
        mock_reader.pages[0].mediabox.height = 400
        mock_reader_class.return_value = mock_reader

        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer

        mock_annotation = MagicMock()
        mock_freetext_class.return_value = mock_annotation

        # 실행
        with patch("builtins.open", mock_open(read_data=json_content)):
            fill_pdf_form("input.pdf", "fields.json", "output.pdf")

        # 검증
        mock_reader_class.assert_called_once_with("input.pdf")
        mock_writer.append.assert_called_once_with(mock_reader)
        mock_freetext_class.assert_called_once()
        mock_writer.add_annotation.assert_called_once()

    @patch("fill_pdf_form_with_annotations.PdfReader")
    @patch("fill_pdf_form_with_annotations.PdfWriter")
    @patch("fill_pdf_form_with_annotations.FreeText")
    @patch("builtins.open", new_callable=mock_open)
    def test_fill_pdf_form_skip_empty_text(
        self, mock_file, mock_freetext_class, mock_writer_class, mock_reader_class
    ):
        """정상 케이스: 빈 텍스트 필드는 건너뛰기"""
        # Mock 데이터 준비
        fields_data = {
            "pages": [{"page_number": 1, "image_width": 1000, "image_height": 800}],
            "form_fields": [
                {
                    "page_number": 1,
                    "entry_bounding_box": [100, 200, 300, 250],
                    "entry_text": {"text": "", "font": "Arial"},  # 빈 텍스트
                }
            ],
        }

        # Mock 설정
        json_content = json.dumps(fields_data)
        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock()]
        mock_reader.pages[0].mediabox.width = 500
        mock_reader.pages[0].mediabox.height = 400
        mock_reader_class.return_value = mock_reader

        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer

        # 실행
        with patch("builtins.open", mock_open(read_data=json_content)):
            fill_pdf_form("input.pdf", "fields.json", "output.pdf")

        # 검증: FreeText 어노테이션이 생성되지 않음
        mock_freetext_class.assert_not_called()
        mock_writer.add_annotation.assert_not_called()

    @patch("fill_pdf_form_with_annotations.PdfReader")
    @patch("fill_pdf_form_with_annotations.PdfWriter")
    @patch("fill_pdf_form_with_annotations.FreeText")
    @patch("builtins.open", new_callable=mock_open)
    def test_fill_pdf_form_skip_no_entry_text(
        self, mock_file, mock_freetext_class, mock_writer_class, mock_reader_class
    ):
        """정상 케이스: entry_text가 없는 필드는 건너뛰기"""
        # Mock 데이터 준비
        fields_data = {
            "pages": [{"page_number": 1, "image_width": 1000, "image_height": 800}],
            "form_fields": [
                {
                    "page_number": 1,
                    "entry_bounding_box": [100, 200, 300, 250],
                    # entry_text 없음
                }
            ],
        }

        # Mock 설정
        json_content = json.dumps(fields_data)
        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock()]
        mock_reader.pages[0].mediabox.width = 500
        mock_reader.pages[0].mediabox.height = 400
        mock_reader_class.return_value = mock_reader

        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer

        # 실행
        with patch("builtins.open", mock_open(read_data=json_content)):
            fill_pdf_form("input.pdf", "fields.json", "output.pdf")

        # 검증: FreeText 어노테이션이 생성되지 않음
        mock_freetext_class.assert_not_called()

    @patch("fill_pdf_form_with_annotations.PdfReader")
    @patch("fill_pdf_form_with_annotations.PdfWriter")
    @patch("fill_pdf_form_with_annotations.FreeText")
    @patch("builtins.open", new_callable=mock_open)
    def test_fill_pdf_form_multiple_pages(
        self, mock_file, mock_freetext_class, mock_writer_class, mock_reader_class
    ):
        """정상 케이스: 여러 페이지에 필드 채우기"""
        # Mock 데이터 준비
        fields_data = {
            "pages": [
                {"page_number": 1, "image_width": 1000, "image_height": 800},
                {"page_number": 2, "image_width": 1000, "image_height": 800},
            ],
            "form_fields": [
                {
                    "page_number": 1,
                    "entry_bounding_box": [100, 200, 300, 250],
                    "entry_text": {"text": "Page 1"},
                },
                {
                    "page_number": 2,
                    "entry_bounding_box": [100, 200, 300, 250],
                    "entry_text": {"text": "Page 2"},
                },
            ],
        }

        # Mock 설정
        json_content = json.dumps(fields_data)
        mock_reader = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.mediabox.width = 500
        mock_page1.mediabox.height = 400
        mock_page2 = MagicMock()
        mock_page2.mediabox.width = 500
        mock_page2.mediabox.height = 400
        mock_reader.pages = [mock_page1, mock_page2]
        mock_reader_class.return_value = mock_reader

        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer

        mock_annotation = MagicMock()
        mock_freetext_class.return_value = mock_annotation

        # 실행
        with patch("builtins.open", mock_open(read_data=json_content)):
            fill_pdf_form("input.pdf", "fields.json", "output.pdf")

        # 검증: 2개의 어노테이션이 추가됨
        assert mock_freetext_class.call_count == 2
        assert mock_writer.add_annotation.call_count == 2

    @patch("fill_pdf_form_with_annotations.PdfReader")
    @patch("fill_pdf_form_with_annotations.PdfWriter")
    @patch("fill_pdf_form_with_annotations.FreeText")
    @patch("builtins.open", new_callable=mock_open)
    def test_fill_pdf_form_default_font_values(
        self, mock_file, mock_freetext_class, mock_writer_class, mock_reader_class
    ):
        """정상 케이스: 기본 폰트 값 사용"""
        # Mock 데이터 준비 (폰트 정보 일부 누락)
        fields_data = {
            "pages": [{"page_number": 1, "image_width": 1000, "image_height": 800}],
            "form_fields": [
                {
                    "page_number": 1,
                    "entry_bounding_box": [100, 200, 300, 250],
                    "entry_text": {
                        "text": "Test",
                        # font, font_size, font_color 누락
                    },
                }
            ],
        }

        # Mock 설정
        json_content = json.dumps(fields_data)
        mock_reader = MagicMock()
        mock_reader.pages = [MagicMock()]
        mock_reader.pages[0].mediabox.width = 500
        mock_reader.pages[0].mediabox.height = 400
        mock_reader_class.return_value = mock_reader

        mock_writer = MagicMock()
        mock_writer_class.return_value = mock_writer

        mock_annotation = MagicMock()
        mock_freetext_class.return_value = mock_annotation

        # 실행
        with patch("builtins.open", mock_open(read_data=json_content)):
            fill_pdf_form("input.pdf", "fields.json", "output.pdf")

        # 검증: FreeText가 기본값으로 호출됨
        call_kwargs = mock_freetext_class.call_args[1]
        assert call_kwargs["font"] == "Arial"  # 기본값
        assert call_kwargs["font_size"] == "14pt"  # 기본값
        assert call_kwargs["font_color"] == "000000"  # 기본값
