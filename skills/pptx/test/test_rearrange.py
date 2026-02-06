"""
rearrange.py에 대한 단위 테스트

테스트 범위:
- duplicate_slide: 슬라이드 복제
- delete_slide: 슬라이드 삭제
- reorder_slides: 슬라이드 재정렬
- rearrange_presentation: 프레젠테이션 재배치
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 테스트 대상 모듈 import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from rearrange import delete_slide, duplicate_slide, rearrange_presentation, reorder_slides


class TestDuplicateSlide:
    """슬라이드 복제 함수 테스트"""

    def test_duplicate_slide_basic(self):
        """정상 케이스: 기본 슬라이드 복제"""
        # Mock presentation
        mock_prs = MagicMock()
        mock_source_slide = MagicMock()
        mock_source_slide.slide_layout = MagicMock()
        mock_source_slide.shapes = []
        mock_source_slide.part.rels = {}

        mock_new_slide = MagicMock()
        mock_new_slide.shapes = MagicMock()
        mock_new_slide.shapes._spTree = MagicMock()
        mock_new_slide.part.rels = MagicMock()
        mock_new_slide.part.rels.get_or_add = MagicMock(return_value="rId1")

        # Mock slides as MagicMock with list-like behavior
        mock_slides = MagicMock()
        mock_slides.__getitem__ = lambda self, idx: mock_source_slide
        mock_slides.add_slide = MagicMock(return_value=mock_new_slide)
        mock_prs.slides = mock_slides

        # 실행
        result = duplicate_slide(mock_prs, 0)

        # 검증
        assert result == mock_new_slide
        mock_slides.add_slide.assert_called_once()

    def test_duplicate_slide_with_shapes(self):
        """정상 케이스: 도형이 있는 슬라이드 복제"""
        # Mock presentation
        mock_prs = MagicMock()
        mock_source_slide = MagicMock()
        mock_source_slide.slide_layout = MagicMock()

        # Mock shape
        mock_shape = MagicMock()
        mock_shape.element = MagicMock()
        mock_source_slide.shapes = [mock_shape]
        mock_source_slide.part.rels = {}

        mock_new_slide = MagicMock()
        mock_new_slide.shapes = MagicMock()
        mock_new_slide.shapes._spTree = MagicMock()
        mock_new_slide.shapes._spTree.insert_element_before = MagicMock()
        mock_new_slide.part.rels = MagicMock()
        mock_new_slide.part.rels.get_or_add = MagicMock(return_value="rId1")

        # Mock slides as MagicMock with list-like behavior
        mock_slides = MagicMock()
        mock_slides.__getitem__ = lambda self, idx: mock_source_slide
        mock_slides.add_slide = MagicMock(return_value=mock_new_slide)
        mock_prs.slides = mock_slides

        # 실행
        result = duplicate_slide(mock_prs, 0)

        # 검증
        mock_new_slide.shapes._spTree.insert_element_before.assert_called()


class TestDeleteSlide:
    """슬라이드 삭제 함수 테스트"""

    def test_delete_slide_basic(self):
        """정상 케이스: 슬라이드 삭제"""
        # Mock presentation
        mock_prs = MagicMock()
        mock_prs.slides = MagicMock()
        mock_prs.slides._sldIdLst = [MagicMock(rId="rId1"), MagicMock(rId="rId2")]
        mock_prs.part.drop_rel = MagicMock()

        # 실행
        delete_slide(mock_prs, 0)

        # 검증
        mock_prs.part.drop_rel.assert_called_once_with("rId1")
        assert len(mock_prs.slides._sldIdLst) == 1

    def test_delete_slide_middle(self):
        """정상 케이스: 중간 슬라이드 삭제"""
        # Mock presentation
        mock_prs = MagicMock()
        mock_prs.slides = MagicMock()
        mock_prs.slides._sldIdLst = [
            MagicMock(rId="rId1"),
            MagicMock(rId="rId2"),
            MagicMock(rId="rId3"),
        ]
        mock_prs.part.drop_rel = MagicMock()

        # 실행: 인덱스 1 삭제
        delete_slide(mock_prs, 1)

        # 검증
        mock_prs.part.drop_rel.assert_called_once_with("rId2")
        assert len(mock_prs.slides._sldIdLst) == 2


class TestReorderSlides:
    """슬라이드 재정렬 함수 테스트"""

    def test_reorder_slides_basic(self):
        """정상 케이스: 슬라이드 순서 변경"""
        # Mock presentation
        mock_prs = MagicMock()
        mock_slides = [MagicMock(), MagicMock(), MagicMock()]
        mock_prs.slides = MagicMock()
        mock_prs.slides._sldIdLst = mock_slides

        # 실행: 인덱스 0을 2로 이동
        reorder_slides(mock_prs, 0, 2)

        # 검증: remove와 insert 호출됨
        assert len(mock_prs.slides._sldIdLst) == 3

    def test_reorder_slides_forward(self):
        """정상 케이스: 뒤로 이동"""
        # Mock presentation
        mock_prs = MagicMock()
        mock_slide1 = MagicMock(name="slide1")
        mock_slide2 = MagicMock(name="slide2")
        mock_slide3 = MagicMock(name="slide3")
        mock_prs.slides = MagicMock()
        mock_prs.slides._sldIdLst = [mock_slide1, mock_slide2, mock_slide3]

        # 실행
        reorder_slides(mock_prs, 0, 1)

        # 검증
        assert len(mock_prs.slides._sldIdLst) == 3


class TestRearrangePresentation:
    """프레젠테이션 재배치 함수 테스트"""

    @patch("rearrange.Presentation")
    @patch("rearrange.shutil.copy2")
    def test_rearrange_presentation_simple(self, mock_copy, mock_prs_class):
        """정상 케이스: 간단한 재배치"""
        # Mock presentation
        mock_prs = MagicMock()

        # Mock slides with proper attributes
        mock_slides = MagicMock()
        mock_slides.__len__ = lambda self: 3
        mock_slides.__getitem__ = lambda self, idx: MagicMock()
        mock_slides._sldIdLst = [MagicMock(), MagicMock(), MagicMock()]
        mock_prs.slides = mock_slides
        mock_prs_class.return_value = mock_prs

        # 실행: 슬라이드 0, 2, 1 순서로
        rearrange_presentation(
            Path("input.pptx"), Path("output.pptx"), [0, 2, 1]
        )

        # 검증
        mock_copy.assert_called_once()
        mock_prs.save.assert_called_once()

    @patch("rearrange.Presentation")
    @patch("rearrange.shutil.copy2")
    @patch("rearrange.duplicate_slide")
    def test_rearrange_presentation_with_duplicates(
        self, mock_duplicate, mock_copy, mock_prs_class
    ):
        """정상 케이스: 중복 슬라이드 포함"""
        # Mock presentation
        mock_prs = MagicMock()

        # Mock slides with proper attributes
        mock_slides_obj = MagicMock()
        mock_slides_obj.__len__ = lambda self: 2
        mock_slides_obj.__getitem__ = lambda self, idx: MagicMock()
        mock_slides_obj._sldIdLst = [MagicMock(), MagicMock()]
        mock_prs.slides = mock_slides_obj
        mock_prs_class.return_value = mock_prs

        # Mock duplicate_slide
        mock_duplicate.return_value = MagicMock()

        # 실행: 슬라이드 0을 두 번 사용
        rearrange_presentation(
            Path("input.pptx"), Path("output.pptx"), [0, 0, 1]
        )

        # 검증: duplicate_slide 호출됨
        mock_duplicate.assert_called()

    @patch("rearrange.Presentation")
    @patch("rearrange.shutil.copy2")
    def test_rearrange_presentation_invalid_index(self, mock_copy, mock_prs_class):
        """에러 케이스: 유효하지 않은 인덱스"""
        # Mock presentation
        mock_prs = MagicMock()

        # Mock slides with proper attributes
        mock_slides_obj = MagicMock()
        mock_slides_obj.__len__ = lambda self: 2
        mock_slides_obj._sldIdLst = [MagicMock(), MagicMock()]
        mock_prs.slides = mock_slides_obj
        mock_prs_class.return_value = mock_prs

        # 실행: 인덱스 5는 범위 밖
        with pytest.raises(ValueError) as exc_info:
            rearrange_presentation(
                Path("input.pptx"), Path("output.pptx"), [0, 5, 1]
            )

        # 검증
        assert "out of range" in str(exc_info.value)

    @patch("rearrange.Presentation")
    @patch("rearrange.shutil.copy2")
    def test_rearrange_presentation_negative_index(self, mock_copy, mock_prs_class):
        """에러 케이스: 음수 인덱스"""
        # Mock presentation
        mock_prs = MagicMock()

        # Mock slides with proper attributes
        mock_slides_obj = MagicMock()
        mock_slides_obj.__len__ = lambda self: 2
        mock_slides_obj._sldIdLst = [MagicMock(), MagicMock()]
        mock_prs.slides = mock_slides_obj
        mock_prs_class.return_value = mock_prs

        # 실행
        with pytest.raises(ValueError) as exc_info:
            rearrange_presentation(
                Path("input.pptx"), Path("output.pptx"), [0, -1, 1]
            )

        # 검증
        assert "out of range" in str(exc_info.value)

    @patch("rearrange.Presentation")
    @patch("rearrange.shutil.copy2")
    def test_rearrange_presentation_single_slide(self, mock_copy, mock_prs_class):
        """정상 케이스: 단일 슬라이드"""
        # Mock presentation
        mock_prs = MagicMock()

        # Mock slides with proper attributes
        mock_slides_obj = MagicMock()
        mock_slides_obj.__len__ = lambda self: 1
        mock_slides_obj._sldIdLst = [MagicMock()]
        mock_prs.slides = mock_slides_obj
        mock_prs_class.return_value = mock_prs

        # 실행
        rearrange_presentation(
            Path("input.pptx"), Path("output.pptx"), [0]
        )

        # 검증
        mock_prs.save.assert_called_once()
