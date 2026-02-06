"""
inventory.py에 대한 단위 테스트

테스트 범위:
- ParagraphData: 단락 데이터 클래스
- ShapeData: 도형 데이터 클래스
- is_valid_shape: 유효한 도형 검사
- collect_shapes_with_absolute_positions: 절대 위치 계산
- sort_shapes_by_position: 위치별 정렬
- calculate_overlap: 겹침 계산
- detect_overlaps: 겹침 감지
- extract_text_inventory: 텍스트 인벤토리 추출
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 테스트 대상 모듈 import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from inventory import (
    ParagraphData,
    ShapeData,
    calculate_overlap,
    collect_shapes_with_absolute_positions,
    detect_overlaps,
    extract_text_inventory,
    is_valid_shape,
    sort_shapes_by_position,
)


class TestParagraphData:
    """단락 데이터 클래스 테스트"""

    def test_paragraph_data_basic_text(self):
        """정상 케이스: 기본 텍스트 단락"""
        mock_para = MagicMock()
        mock_para.text = "  Test paragraph  "
        mock_para._p = None
        mock_para.alignment = None
        mock_para.runs = []

        para_data = ParagraphData(mock_para)

        assert para_data.text == "Test paragraph"
        assert para_data.bullet is False

    def test_paragraph_data_with_bullet(self):
        """정상 케이스: 불릿 포인트 단락"""
        mock_para = MagicMock()
        mock_para.text = "Bullet item"
        mock_para.level = 0
        mock_para.alignment = None
        mock_para.runs = []

        # Mock bullet formatting
        mock_pPr = MagicMock()
        ns = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
        mock_pPr.find.return_value = MagicMock()  # buChar exists
        mock_para._p = MagicMock()
        mock_para._p.pPr = mock_pPr

        para_data = ParagraphData(mock_para)

        assert para_data.bullet is True
        assert para_data.level == 0

    def test_paragraph_data_to_dict(self):
        """정상 케이스: 딕셔너리 변환"""
        mock_para = MagicMock()
        mock_para.text = "Test"
        mock_para._p = None
        mock_para.alignment = None
        mock_para.runs = []

        para_data = ParagraphData(mock_para)
        result = para_data.to_dict()

        assert "text" in result
        assert result["text"] == "Test"

    def test_paragraph_data_with_font_properties(self):
        """정상 케이스: 폰트 속성 포함"""
        mock_para = MagicMock()
        mock_para.text = "Formatted text"
        mock_para._p = None
        mock_para.alignment = None

        # Mock run with font
        mock_run = MagicMock()
        mock_font = MagicMock()
        mock_font.name = "Arial"
        mock_font.size = MagicMock()
        mock_font.size.pt = 12.0
        mock_font.bold = True
        mock_run.font = mock_font
        mock_para.runs = [mock_run]

        para_data = ParagraphData(mock_para)

        assert para_data.font_name == "Arial"
        assert para_data.font_size == 12.0
        assert para_data.bold is True


class TestShapeData:
    """도형 데이터 클래스 테스트"""

    def test_shape_data_basic(self):
        """정상 케이스: 기본 도형 데이터"""
        mock_shape = MagicMock()
        mock_shape.left = 914400  # 1 inch in EMU
        mock_shape.top = 914400
        mock_shape.width = 1828800  # 2 inches
        mock_shape.height = 914400  # 1 inch
        mock_shape.text_frame = MagicMock()
        mock_shape.text_frame.paragraphs = []

        shape_data = ShapeData(mock_shape)

        assert shape_data.left == 1.0
        assert shape_data.top == 1.0
        assert shape_data.width == 2.0
        assert shape_data.height == 1.0

    def test_shape_data_emu_to_inches(self):
        """정상 케이스: EMU to inches 변환"""
        assert ShapeData.emu_to_inches(914400) == 1.0
        assert ShapeData.emu_to_inches(1828800) == 2.0

    def test_shape_data_to_dict(self):
        """정상 케이스: 딕셔너리 변환"""
        mock_shape = MagicMock()
        mock_shape.left = 914400
        mock_shape.top = 914400
        mock_shape.width = 914400
        mock_shape.height = 914400
        mock_shape.text_frame = MagicMock()
        mock_shape.text_frame.paragraphs = []

        shape_data = ShapeData(mock_shape)
        result = shape_data.to_dict()

        assert "left" in result
        assert "top" in result
        assert "width" in result
        assert "height" in result
        assert "paragraphs" in result


class TestIsValidShape:
    """유효한 도형 검사 함수 테스트"""

    def test_is_valid_shape_with_text(self):
        """정상 케이스: 텍스트가 있는 도형"""
        mock_shape = MagicMock()
        mock_shape.text_frame = MagicMock()
        mock_shape.text_frame.text = "Some text"
        mock_shape.is_placeholder = False

        assert is_valid_shape(mock_shape) is True

    def test_is_valid_shape_no_text_frame(self):
        """에러 케이스: 텍스트 프레임 없음"""
        mock_shape = MagicMock()
        mock_shape.text_frame = None

        assert is_valid_shape(mock_shape) is False

    def test_is_valid_shape_empty_text(self):
        """에러 케이스: 빈 텍스트"""
        mock_shape = MagicMock()
        mock_shape.text_frame = MagicMock()
        mock_shape.text_frame.text = "   "

        assert is_valid_shape(mock_shape) is False

    def test_is_valid_shape_slide_number_placeholder(self):
        """에러 케이스: 슬라이드 번호 플레이스홀더"""
        mock_shape = MagicMock()
        mock_shape.text_frame = MagicMock()
        mock_shape.text_frame.text = "1"
        mock_shape.is_placeholder = True
        mock_shape.placeholder_format = MagicMock()
        mock_shape.placeholder_format.type = MagicMock()
        type(mock_shape.placeholder_format.type).__str__ = lambda x: "SLIDE_NUMBER (17)"

        assert is_valid_shape(mock_shape) is False


class TestCollectShapesWithAbsolutePositions:
    """절대 위치 계산 함수 테스트"""

    def test_collect_single_shape(self):
        """정상 케이스: 단일 도형"""
        mock_shape = MagicMock()
        mock_shape.left = 100
        mock_shape.top = 200
        mock_shape.text_frame = MagicMock()
        mock_shape.text_frame.text = "Test"
        mock_shape.is_placeholder = False
        # Remove shapes attribute so hasattr check fails
        del mock_shape.shapes

        with patch("inventory.is_valid_shape", return_value=True):
            result = collect_shapes_with_absolute_positions(mock_shape)

        assert len(result) == 1
        assert result[0].absolute_left == 100
        assert result[0].absolute_top == 200

    def test_collect_group_shape(self):
        """정상 케이스: 그룹 도형"""
        # Parent group
        mock_group = MagicMock()
        mock_group.left = 100
        mock_group.top = 100

        # Child shape
        mock_child = MagicMock()
        mock_child.left = 50
        mock_child.top = 50
        mock_child.text_frame = MagicMock()
        mock_child.text_frame.text = "Child text"
        mock_child.is_placeholder = False
        # Remove shapes attribute so hasattr check fails
        del mock_child.shapes

        mock_group.shapes = [mock_child]

        with patch("inventory.is_valid_shape", return_value=True):
            result = collect_shapes_with_absolute_positions(mock_group)

        # 검증: 절대 위치는 100 + 50 = 150
        assert len(result) == 1
        assert result[0].absolute_left == 150
        assert result[0].absolute_top == 150


class TestSortShapesByPosition:
    """위치별 정렬 함수 테스트"""

    def test_sort_shapes_by_position_basic(self):
        """정상 케이스: 기본 정렬"""
        mock_shape1 = MagicMock()
        mock_shape1.left = 0
        mock_shape1.top = 0
        mock_shape1.width = 100
        mock_shape1.height = 100
        mock_shape1.text_frame = MagicMock()
        mock_shape1.text_frame.paragraphs = []

        mock_shape2 = MagicMock()
        mock_shape2.left = 0
        mock_shape2.top = 200
        mock_shape2.width = 100
        mock_shape2.height = 100
        mock_shape2.text_frame = MagicMock()
        mock_shape2.text_frame.paragraphs = []

        shape1 = ShapeData(mock_shape1)
        shape1.top = 2.0
        shape1.left = 0.0

        shape2 = ShapeData(mock_shape2)
        shape2.top = 0.0
        shape2.left = 0.0

        shapes = [shape1, shape2]
        result = sort_shapes_by_position(shapes)

        # 검증: top이 작은 것이 먼저 (위에서 아래로)
        assert result[0].top < result[1].top


class TestCalculateOverlap:
    """겹침 계산 함수 테스트"""

    def test_calculate_overlap_no_overlap(self):
        """정상 케이스: 겹치지 않음"""
        rect1 = (0, 0, 100, 100)
        rect2 = (110, 0, 210, 100)

        overlaps, area = calculate_overlap(rect1, rect2)

        assert overlaps is False
        assert area == 0

    def test_calculate_overlap_partial_overlap(self):
        """정상 케이스: 부분 겹침"""
        rect1 = (0, 0, 100, 100)
        rect2 = (50, 50, 150, 150)

        overlaps, area = calculate_overlap(rect1, rect2)

        assert overlaps is True
        assert area > 0

    def test_calculate_overlap_complete_overlap(self):
        """정상 케이스: 완전 겹침"""
        rect1 = (0, 0, 100, 100)
        rect2 = (0, 0, 100, 100)

        overlaps, area = calculate_overlap(rect1, rect2)

        assert overlaps is True
        assert area == 100 * 100  # 10000

    def test_calculate_overlap_edge_touching(self):
        """경계 케이스: 모서리만 닿음"""
        rect1 = (0, 0, 100, 100)
        rect2 = (100, 0, 200, 100)

        overlaps, area = calculate_overlap(rect1, rect2)

        # tolerance=0.05이므로 겹치지 않음으로 간주
        assert overlaps is False


class TestDetectOverlaps:
    """겹침 감지 함수 테스트"""

    def test_detect_overlaps_no_overlap(self):
        """정상 케이스: 겹침 없음"""
        mock_shape1 = MagicMock()
        mock_shape1.left = 0
        mock_shape1.top = 0
        mock_shape1.width = 100
        mock_shape1.height = 100
        mock_shape1.text_frame = MagicMock()
        mock_shape1.text_frame.paragraphs = []

        mock_shape2 = MagicMock()
        mock_shape2.left = 0
        mock_shape2.top = 200
        mock_shape2.width = 100
        mock_shape2.height = 100
        mock_shape2.text_frame = MagicMock()
        mock_shape2.text_frame.paragraphs = []

        shape1 = ShapeData(mock_shape1)
        shape1.shape_id = "shape-0"
        shape1.left = 0.0
        shape1.top = 0.0
        shape1.width = 1.0
        shape1.height = 1.0

        shape2 = ShapeData(mock_shape2)
        shape2.shape_id = "shape-1"
        shape2.left = 0.0
        shape2.top = 2.0
        shape2.width = 1.0
        shape2.height = 1.0

        shapes = [shape1, shape2]
        detect_overlaps(shapes)

        # 검증: 겹침 없음
        assert len(shape1.overlapping_shapes) == 0
        assert len(shape2.overlapping_shapes) == 0


class TestExtractTextInventory:
    """텍스트 인벤토리 추출 함수 테스트"""

    @patch("inventory.Presentation")
    def test_extract_text_inventory_basic(self, mock_prs_class):
        """정상 케이스: 기본 인벤토리 추출"""
        # Mock presentation
        mock_prs = MagicMock()
        mock_prs.slide_width = 9144000  # Standard slide width in EMU
        mock_prs.slide_height = 6858000  # Standard slide height in EMU

        # Mock slide with shape
        mock_slide = MagicMock()

        # Mock slide.part.package.presentation_part.presentation to return mock_prs
        mock_presentation_part = MagicMock()
        mock_presentation_part.presentation = mock_prs
        mock_package = MagicMock()
        mock_package.presentation_part = mock_presentation_part
        mock_part = MagicMock()
        mock_part.package = mock_package
        mock_slide.part = mock_part

        mock_shape = MagicMock()
        mock_shape.left = 914400
        mock_shape.top = 914400
        mock_shape.width = 914400
        mock_shape.height = 914400
        mock_shape.text_frame = MagicMock()
        mock_shape.text_frame.text = "Test text"
        mock_shape.text_frame.paragraphs = []
        mock_shape.is_placeholder = False
        # Remove shapes attribute so hasattr check fails
        del mock_shape.shapes

        mock_slide.shapes = [mock_shape]
        mock_prs.slides = [mock_slide]
        mock_prs_class.return_value = mock_prs

        with patch("inventory.is_valid_shape", return_value=True):
            result = extract_text_inventory(Path("test.pptx"), mock_prs)

        # 검증
        assert "slide-0" in result

    @patch("inventory.Presentation")
    def test_extract_text_inventory_empty(self, mock_prs_class):
        """정상 케이스: 텍스트 없는 프레젠테이션"""
        # Mock presentation
        mock_prs = MagicMock()
        mock_slide = MagicMock()
        mock_slide.shapes = []
        mock_prs.slides = [mock_slide]
        mock_prs_class.return_value = mock_prs

        result = extract_text_inventory(Path("test.pptx"), mock_prs)

        # 검증: 빈 인벤토리
        assert len(result) == 0
