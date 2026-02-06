"""
create_validation_image.py에 대한 단위 테스트

테스트 범위:
- create_validation_image: 검증 이미지 생성 함수
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# 테스트 대상 모듈 import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from create_validation_image import create_validation_image


class TestCreateValidationImage:
    """검증 이미지 생성 함수 테스트"""

    @patch("create_validation_image.ImageDraw")
    @patch("create_validation_image.Image")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_validation_image_single_field(self, mock_file, mock_image_class, mock_imagedraw):
        """정상 케이스: 단일 필드에 대한 검증 이미지 생성"""
        # Mock 데이터 준비
        fields_data = {
            "form_fields": [
                {
                    "page_number": 1,
                    "entry_bounding_box": [10, 20, 110, 70],
                    "label_bounding_box": [10, 80, 110, 130],
                }
            ]
        }

        # Mock 이미지 설정
        mock_img = MagicMock()
        mock_draw = MagicMock()
        mock_image_class.open.return_value = mock_img
        mock_imagedraw.Draw.return_value = mock_draw

        # Mock open for JSON
        json_content = json.dumps(fields_data)
        with patch("builtins.open", mock_open(read_data=json_content)):
            # 실행
            create_validation_image(1, "fields.json", "input.png", "output.png")

        # 검증: 사각형이 2개 그려졌는지 확인 (entry + label)
        assert mock_draw.rectangle.call_count == 2

        # 검증: 이미지가 저장되었는지 확인
        mock_img.save.assert_called_once_with("output.png")

    @patch("create_validation_image.ImageDraw")
    @patch("create_validation_image.Image")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_validation_image_multiple_fields(self, mock_file, mock_image_class, mock_imagedraw):
        """정상 케이스: 여러 필드에 대한 검증 이미지 생성"""
        # Mock 데이터 준비 (3개 필드)
        fields_data = {
            "form_fields": [
                {
                    "page_number": 1,
                    "entry_bounding_box": [10, 20, 110, 70],
                    "label_bounding_box": [10, 80, 110, 130],
                },
                {
                    "page_number": 1,
                    "entry_bounding_box": [120, 20, 220, 70],
                    "label_bounding_box": [120, 80, 220, 130],
                },
                {
                    "page_number": 1,
                    "entry_bounding_box": [230, 20, 330, 70],
                    "label_bounding_box": [230, 80, 330, 130],
                },
            ]
        }

        # Mock 이미지 설정
        mock_img = MagicMock()
        mock_draw = MagicMock()
        mock_image_class.open.return_value = mock_img
        mock_imagedraw.Draw.return_value = mock_draw

        # Mock open for JSON
        json_content = json.dumps(fields_data)
        with patch("builtins.open", mock_open(read_data=json_content)):
            # 실행
            create_validation_image(1, "fields.json", "input.png", "output.png")

        # 검증: 사각형이 6개 그려졌는지 확인 (3 fields × 2 boxes)
        assert mock_draw.rectangle.call_count == 6

    @patch("create_validation_image.ImageDraw")
    @patch("create_validation_image.Image")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_validation_image_filter_by_page(self, mock_file, mock_image_class, mock_imagedraw):
        """정상 케이스: 특정 페이지만 필터링"""
        # Mock 데이터 준비 (페이지 1, 2 혼재)
        fields_data = {
            "form_fields": [
                {
                    "page_number": 1,
                    "entry_bounding_box": [10, 20, 110, 70],
                    "label_bounding_box": [10, 80, 110, 130],
                },
                {
                    "page_number": 2,
                    "entry_bounding_box": [10, 20, 110, 70],
                    "label_bounding_box": [10, 80, 110, 130],
                },
                {
                    "page_number": 1,
                    "entry_bounding_box": [120, 20, 220, 70],
                    "label_bounding_box": [120, 80, 220, 130],
                },
            ]
        }

        # Mock 이미지 설정
        mock_img = MagicMock()
        mock_draw = MagicMock()
        mock_image_class.open.return_value = mock_img
        mock_imagedraw.Draw.return_value = mock_draw

        # Mock open for JSON
        json_content = json.dumps(fields_data)
        with patch("builtins.open", mock_open(read_data=json_content)):
            # 실행: 페이지 1만 요청
            create_validation_image(1, "fields.json", "input.png", "output.png")

        # 검증: 페이지 1의 2개 필드만 처리 = 4개 사각형
        assert mock_draw.rectangle.call_count == 4

    @patch("create_validation_image.ImageDraw")
    @patch("create_validation_image.Image")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_validation_image_no_fields_on_page(
        self, mock_file, mock_image_class, mock_imagedraw
    ):
        """경계 케이스: 요청한 페이지에 필드가 없음"""
        # Mock 데이터 준비 (페이지 1만 있음)
        fields_data = {
            "form_fields": [
                {
                    "page_number": 1,
                    "entry_bounding_box": [10, 20, 110, 70],
                    "label_bounding_box": [10, 80, 110, 130],
                }
            ]
        }

        # Mock 이미지 설정
        mock_img = MagicMock()
        mock_draw = MagicMock()
        mock_image_class.open.return_value = mock_img
        mock_imagedraw.Draw.return_value = mock_draw

        # Mock open for JSON
        json_content = json.dumps(fields_data)
        with patch("builtins.open", mock_open(read_data=json_content)):
            # 실행: 페이지 2 요청 (존재하지 않음)
            create_validation_image(2, "fields.json", "input.png", "output.png")

        # 검증: 사각형이 그려지지 않음
        assert mock_draw.rectangle.call_count == 0
        # 이미지는 저장됨
        mock_img.save.assert_called_once()

    @patch("create_validation_image.ImageDraw")
    @patch("create_validation_image.Image")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_validation_image_rectangle_colors(
        self, mock_file, mock_image_class, mock_imagedraw
    ):
        """정상 케이스: 사각형 색상 확인 (entry=빨강, label=파랑)"""
        # Mock 데이터 준비
        fields_data = {
            "form_fields": [
                {
                    "page_number": 1,
                    "entry_bounding_box": [10, 20, 110, 70],
                    "label_bounding_box": [10, 80, 110, 130],
                }
            ]
        }

        # Mock 이미지 설정
        mock_img = MagicMock()
        mock_draw = MagicMock()
        mock_image_class.open.return_value = mock_img
        mock_imagedraw.Draw.return_value = mock_draw

        # Mock open for JSON
        json_content = json.dumps(fields_data)
        with patch("builtins.open", mock_open(read_data=json_content)):
            # 실행
            create_validation_image(1, "fields.json", "input.png", "output.png")

        # 검증: 색상이 올바른지 확인
        calls = mock_draw.rectangle.call_args_list
        # 첫 번째 호출은 entry (빨강)
        assert calls[0][1]["outline"] == "red"
        # 두 번째 호출은 label (파랑)
        assert calls[1][1]["outline"] == "blue"

    @patch("create_validation_image.ImageDraw")
    @patch("create_validation_image.Image")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_validation_image_rectangle_width(
        self, mock_file, mock_image_class, mock_imagedraw
    ):
        """정상 케이스: 사각형 선 두께 확인"""
        # Mock 데이터 준비
        fields_data = {
            "form_fields": [
                {
                    "page_number": 1,
                    "entry_bounding_box": [10, 20, 110, 70],
                    "label_bounding_box": [10, 80, 110, 130],
                }
            ]
        }

        # Mock 이미지 설정
        mock_img = MagicMock()
        mock_draw = MagicMock()
        mock_image_class.open.return_value = mock_img
        mock_imagedraw.Draw.return_value = mock_draw

        # Mock open for JSON
        json_content = json.dumps(fields_data)
        with patch("builtins.open", mock_open(read_data=json_content)):
            # 실행
            create_validation_image(1, "fields.json", "input.png", "output.png")

        # 검증: 선 두께가 2인지 확인
        calls = mock_draw.rectangle.call_args_list
        for call in calls:
            assert call[1]["width"] == 2

    @patch("create_validation_image.ImageDraw")
    @patch("create_validation_image.Image")
    @patch("builtins.open", new_callable=mock_open)
    def test_create_validation_image_empty_fields(self, mock_file, mock_image_class, mock_imagedraw):
        """경계 케이스: 필드가 전혀 없는 경우"""
        # Mock 데이터 준비
        fields_data = {"form_fields": []}

        # Mock 이미지 설정
        mock_img = MagicMock()
        mock_draw = MagicMock()
        mock_image_class.open.return_value = mock_img
        mock_imagedraw.Draw.return_value = mock_draw

        # Mock open for JSON
        json_content = json.dumps(fields_data)
        with patch("builtins.open", mock_open(read_data=json_content)):
            # 실행
            create_validation_image(1, "fields.json", "input.png", "output.png")

        # 검증: 사각형이 그려지지 않음
        assert mock_draw.rectangle.call_count == 0
        # 이미지는 저장됨
        mock_img.save.assert_called_once()
