"""
convert_pdf_to_images.py에 대한 단위 테스트

테스트 범위:
- convert: PDF를 이미지로 변환하는 함수
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# 테스트 대상 모듈 import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from convert_pdf_to_images import convert


class TestConvert:
    """PDF 이미지 변환 함수 테스트"""

    @patch("convert_pdf_to_images.convert_from_path")
    def test_convert_single_page_no_scaling(self, mock_convert_from_path):
        """정상 케이스: 단일 페이지, 스케일링 불필요"""
        # Mock 이미지 생성 (800x600)
        mock_image = MagicMock()
        mock_image.size = (800, 600)
        mock_convert_from_path.return_value = [mock_image]

        # 실행
        convert("test.pdf", "/tmp/output", max_dim=1000)

        # 검증
        mock_convert_from_path.assert_called_once_with("test.pdf", dpi=200)
        mock_image.resize.assert_not_called()  # 스케일링 불필요
        mock_image.save.assert_called_once()
        assert "/tmp/output/page_1.png" in mock_image.save.call_args[0][0]

    @patch("convert_pdf_to_images.convert_from_path")
    def test_convert_multiple_pages(self, mock_convert_from_path):
        """정상 케이스: 여러 페이지 변환"""
        # Mock 이미지 생성 (3페이지)
        mock_images = [MagicMock() for _ in range(3)]
        for i, img in enumerate(mock_images):
            img.size = (800, 600)
        mock_convert_from_path.return_value = mock_images

        # 실행
        convert("test.pdf", "/tmp/output", max_dim=1000)

        # 검증
        assert len(mock_images) == 3
        for i, img in enumerate(mock_images):
            img.save.assert_called_once()
            assert f"/tmp/output/page_{i+1}.png" in img.save.call_args[0][0]

    @patch("convert_pdf_to_images.convert_from_path")
    def test_convert_with_width_scaling(self, mock_convert_from_path):
        """정상 케이스: 너비 기준 스케일링"""
        # Mock 이미지 생성 (1200x800, max_dim=1000이므로 스케일링 필요)
        mock_image = MagicMock()
        mock_image.size = (1200, 800)
        scaled_image = MagicMock()
        scaled_image.size = (1000, 667)
        mock_image.resize.return_value = scaled_image
        mock_convert_from_path.return_value = [mock_image]

        # 실행
        convert("test.pdf", "/tmp/output", max_dim=1000)

        # 검증
        mock_image.resize.assert_called_once()
        # 스케일 팩터: 1000/1200 = 0.833...
        # 새 크기: (1000, 666)
        resize_args = mock_image.resize.call_args[0][0]
        assert resize_args[0] == 1000  # width
        assert 666 <= resize_args[1] <= 667  # height (반올림 오차 허용)

    @patch("convert_pdf_to_images.convert_from_path")
    def test_convert_with_height_scaling(self, mock_convert_from_path):
        """정상 케이스: 높이 기준 스케일링"""
        # Mock 이미지 생성 (800x1200, max_dim=1000이므로 스케일링 필요)
        mock_image = MagicMock()
        mock_image.size = (800, 1200)
        scaled_image = MagicMock()
        scaled_image.size = (667, 1000)
        mock_image.resize.return_value = scaled_image
        mock_convert_from_path.return_value = [mock_image]

        # 실행
        convert("test.pdf", "/tmp/output", max_dim=1000)

        # 검증
        mock_image.resize.assert_called_once()
        # 스케일 팩터: 1000/1200 = 0.833...
        # 새 크기: (666, 1000)
        resize_args = mock_image.resize.call_args[0][0]
        assert 666 <= resize_args[0] <= 667  # width (반올림 오차 허용)
        assert resize_args[1] == 1000  # height

    @patch("convert_pdf_to_images.convert_from_path")
    def test_convert_exact_max_dim(self, mock_convert_from_path):
        """경계 케이스: 정확히 max_dim 크기"""
        # Mock 이미지 생성 (1000x1000)
        mock_image = MagicMock()
        mock_image.size = (1000, 1000)
        mock_convert_from_path.return_value = [mock_image]

        # 실행
        convert("test.pdf", "/tmp/output", max_dim=1000)

        # 검증: 스케일링 불필요
        mock_image.resize.assert_not_called()

    @patch("convert_pdf_to_images.convert_from_path")
    def test_convert_small_image(self, mock_convert_from_path):
        """정상 케이스: max_dim보다 작은 이미지"""
        # Mock 이미지 생성 (500x400)
        mock_image = MagicMock()
        mock_image.size = (500, 400)
        mock_convert_from_path.return_value = [mock_image]

        # 실행
        convert("test.pdf", "/tmp/output", max_dim=1000)

        # 검증: 스케일링 불필요
        mock_image.resize.assert_not_called()
        mock_image.save.assert_called_once()

    @patch("convert_pdf_to_images.convert_from_path")
    def test_convert_custom_max_dim(self, mock_convert_from_path):
        """정상 케이스: 커스텀 max_dim 값"""
        # Mock 이미지 생성 (1000x800)
        mock_image = MagicMock()
        mock_image.size = (1000, 800)
        scaled_image = MagicMock()
        scaled_image.size = (500, 400)
        mock_image.resize.return_value = scaled_image
        mock_convert_from_path.return_value = [mock_image]

        # 실행 (max_dim=500)
        convert("test.pdf", "/tmp/output", max_dim=500)

        # 검증
        mock_image.resize.assert_called_once()
        resize_args = mock_image.resize.call_args[0][0]
        assert resize_args[0] == 500  # width
        assert resize_args[1] == 400  # height

    @patch("convert_pdf_to_images.convert_from_path")
    def test_convert_saves_with_correct_filenames(self, mock_convert_from_path):
        """정상 케이스: 파일명이 올바르게 생성되는지 확인"""
        # Mock 이미지 생성 (5페이지)
        mock_images = [MagicMock() for _ in range(5)]
        for img in mock_images:
            img.size = (800, 600)
        mock_convert_from_path.return_value = mock_images

        # 실행
        convert("test.pdf", "/output/dir", max_dim=1000)

        # 검증: 각 페이지가 올바른 번호로 저장되는지 확인
        expected_paths = [
            "/output/dir/page_1.png",
            "/output/dir/page_2.png",
            "/output/dir/page_3.png",
            "/output/dir/page_4.png",
            "/output/dir/page_5.png",
        ]
        for i, img in enumerate(mock_images):
            img.save.assert_called_once()
            assert expected_paths[i] in img.save.call_args[0][0]

    @patch("convert_pdf_to_images.convert_from_path")
    def test_convert_empty_pdf(self, mock_convert_from_path):
        """에러 케이스: 페이지가 없는 PDF"""
        # 빈 리스트 반환
        mock_convert_from_path.return_value = []

        # 실행 (에러 발생하지 않아야 함)
        convert("test.pdf", "/tmp/output", max_dim=1000)

        # 검증
        mock_convert_from_path.assert_called_once()

    @patch("convert_pdf_to_images.convert_from_path")
    def test_convert_very_large_image(self, mock_convert_from_path):
        """경계 케이스: 매우 큰 이미지"""
        # Mock 이미지 생성 (10000x8000)
        mock_image = MagicMock()
        mock_image.size = (10000, 8000)
        scaled_image = MagicMock()
        scaled_image.size = (1000, 800)
        mock_image.resize.return_value = scaled_image
        mock_convert_from_path.return_value = [mock_image]

        # 실행
        convert("test.pdf", "/tmp/output", max_dim=1000)

        # 검증: 스케일링 수행
        mock_image.resize.assert_called_once()
        resize_args = mock_image.resize.call_args[0][0]
        assert resize_args[0] == 1000
        assert resize_args[1] == 800
