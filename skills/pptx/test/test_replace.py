"""
replace.py에 대한 단위 테스트

테스트 범위:
- clear_paragraph_bullets: 단락 불릿 제거
- apply_paragraph_properties: 단락 속성 적용
- apply_font_properties: 폰트 속성 적용
- detect_frame_overflow: 프레임 오버플로우 감지
- validate_replacements: 교체 데이터 검증
- apply_replacements: 교체 적용
"""

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# 테스트 대상 모듈 import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from replace import (
    apply_font_properties,
    apply_paragraph_properties,
    apply_replacements,
    clear_paragraph_bullets,
    detect_frame_overflow,
    validate_replacements,
)


class TestClearParagraphBullets:
    """단락 불릿 제거 함수 테스트"""

    def test_clear_paragraph_bullets_basic(self):
        """정상 케이스: 불릿 제거"""
        mock_para = MagicMock()
        mock_pPr = MagicMock()
        mock_para._element.get_or_add_pPr.return_value = mock_pPr

        # Mock bullet elements
        mock_buChar = MagicMock()
        mock_buChar.tag = "buChar"
        mock_pPr.__iter__ = lambda self: iter([mock_buChar])
        mock_pPr.remove = MagicMock()

        result = clear_paragraph_bullets(mock_para)

        # 검증: get_or_add_pPr 호출됨
        mock_para._element.get_or_add_pPr.assert_called_once()


class TestApplyFontProperties:
    """폰트 속성 적용 함수 테스트"""

    def test_apply_font_properties_basic(self):
        """정상 케이스: 기본 폰트 속성"""
        mock_run = MagicMock()
        mock_font = MagicMock()
        mock_run.font = mock_font

        para_data = {
            "bold": True,
            "italic": False,
            "font_size": 14,
            "font_name": "Arial",
        }

        apply_font_properties(mock_run, para_data)

        # 검증
        assert mock_font.bold == True
        assert mock_font.italic == False

    def test_apply_font_properties_with_color(self):
        """정상 케이스: 색상 적용"""
        mock_run = MagicMock()
        mock_font = MagicMock()
        mock_run.font = mock_font

        para_data = {"color": "#FF0000"}  # 빨강

        apply_font_properties(mock_run, para_data)

        # 검증: color.rgb 호출됨
        assert mock_font.color.rgb is not None


class TestApplyParagraphProperties:
    """단락 속성 적용 함수 테스트"""

    @patch("replace.clear_paragraph_bullets")
    @patch("replace.apply_font_properties")
    def test_apply_paragraph_properties_basic(
        self, mock_apply_font, mock_clear_bullets
    ):
        """정상 케이스: 기본 단락 속성"""
        mock_para = MagicMock()
        mock_pPr = MagicMock()
        mock_clear_bullets.return_value = mock_pPr
        mock_para.runs = []
        mock_para.add_run.return_value = MagicMock()

        para_data = {"text": "Test paragraph"}

        apply_paragraph_properties(mock_para, para_data)

        # 검증
        mock_clear_bullets.assert_called_once()
        mock_para.add_run.assert_called_once()

    @patch("replace.clear_paragraph_bullets")
    @patch("replace.apply_font_properties")
    def test_apply_paragraph_properties_with_bullet(
        self, mock_apply_font, mock_clear_bullets
    ):
        """정상 케이스: 불릿 포인트 적용"""
        mock_para = MagicMock()
        mock_pPr = MagicMock()
        mock_pPr.attrib = {}
        mock_pPr.append = MagicMock()
        mock_clear_bullets.return_value = mock_pPr
        mock_para.runs = []
        mock_para.add_run.return_value = MagicMock()

        para_data = {"text": "Bullet item", "bullet": True, "level": 0, "font_size": 12}

        with patch("replace.OxmlElement") as mock_oxml:
            mock_buChar = MagicMock()
            mock_oxml.return_value = mock_buChar

            apply_paragraph_properties(mock_para, para_data)

            # 검증: buChar element 추가됨
            mock_pPr.append.assert_called()


class TestDetectFrameOverflow:
    """프레임 오버플로우 감지 함수 테스트"""

    def test_detect_frame_overflow_basic(self):
        """정상 케이스: 오버플로우 감지"""
        # Mock inventory
        mock_shape1 = MagicMock()
        mock_shape1.frame_overflow_bottom = 0.5

        mock_shape2 = MagicMock()
        mock_shape2.frame_overflow_bottom = None

        inventory = {
            "slide-0": {"shape-0": mock_shape1, "shape-1": mock_shape2},
        }

        result = detect_frame_overflow(inventory)

        # 검증: shape-0만 포함
        assert "slide-0" in result
        assert "shape-0" in result["slide-0"]
        assert "shape-1" not in result["slide-0"]

    def test_detect_frame_overflow_no_overflow(self):
        """정상 케이스: 오버플로우 없음"""
        # Mock inventory
        mock_shape = MagicMock()
        mock_shape.frame_overflow_bottom = None

        inventory = {"slide-0": {"shape-0": mock_shape}}

        result = detect_frame_overflow(inventory)

        # 검증: 빈 결과
        assert len(result) == 0


class TestValidateReplacements:
    """교체 데이터 검증 함수 테스트"""

    def test_validate_replacements_valid(self):
        """정상 케이스: 유효한 교체 데이터"""
        # Mock inventory
        mock_shape = MagicMock()
        mock_shape.paragraphs = []
        inventory = {"slide-0": {"shape-0": mock_shape}}

        replacements = {"slide-0": {"shape-0": {"paragraphs": []}}}

        errors = validate_replacements(inventory, replacements)

        # 검증: 에러 없음
        assert len(errors) == 0

    def test_validate_replacements_invalid_slide(self):
        """에러 케이스: 존재하지 않는 슬라이드"""
        inventory = {"slide-0": {}}
        replacements = {"slide-1": {"shape-0": {}}}

        errors = validate_replacements(inventory, replacements)

        # 검증: 에러 있음
        assert len(errors) > 0
        assert "slide-1" in errors[0]

    def test_validate_replacements_invalid_shape(self):
        """에러 케이스: 존재하지 않는 도형"""
        mock_shape = MagicMock()
        mock_shape.paragraphs = [MagicMock(text="test")]
        inventory = {"slide-0": {"shape-0": mock_shape}}

        replacements = {"slide-0": {"shape-1": {}}}

        errors = validate_replacements(inventory, replacements)

        # 검증: 에러 있음
        assert len(errors) > 0
        assert "shape-1" in errors[0]


class TestApplyReplacements:
    """교체 적용 함수 테스트"""

    @patch("replace.Presentation")
    @patch("replace.extract_text_inventory")
    @patch("replace.detect_frame_overflow")
    @patch("replace.validate_replacements")
    @patch("replace.apply_paragraph_properties")
    @patch("builtins.open", new_callable=mock_open)
    @patch("tempfile.NamedTemporaryFile")
    def test_apply_replacements_basic(
        self,
        mock_tempfile,
        mock_file,
        mock_apply_para,
        mock_validate,
        mock_detect_overflow,
        mock_extract,
        mock_prs_class,
    ):
        """정상 케이스: 기본 교체 적용"""
        # Mock presentation
        mock_prs = MagicMock()
        mock_slide = MagicMock()
        mock_prs.slides = [mock_slide]
        mock_prs_class.return_value = mock_prs

        # Mock shape
        mock_shape = MagicMock()
        mock_shape.text_frame = MagicMock()
        mock_shape.text_frame.paragraphs = [MagicMock()]
        mock_shape.text_frame.clear = MagicMock()
        mock_shape.text_frame.add_paragraph = MagicMock(return_value=MagicMock())

        # Mock inventory
        mock_shape_data = MagicMock()
        mock_shape_data.shape = mock_shape
        mock_shape_data.paragraphs = []
        inventory = {"slide-0": {"shape-0": mock_shape_data}}

        # Mock 설정
        mock_extract.return_value = inventory
        mock_validate.return_value = []
        mock_detect_overflow.return_value = {}

        # Mock replacements
        replacements = {
            "slide-0": {"shape-0": {"paragraphs": [{"text": "New text"}]}}
        }
        json_content = json.dumps(replacements)

        # Mock temp file
        mock_temp = MagicMock()
        mock_temp.name = "/tmp/test.pptx"
        mock_temp.__enter__ = MagicMock(return_value=mock_temp)
        mock_temp.__exit__ = MagicMock(return_value=False)
        mock_tempfile.return_value = mock_temp

        # Mock Path.unlink
        with patch("replace.Path") as mock_path_class:
            mock_path_instance = MagicMock()
            mock_path_class.return_value = mock_path_instance

            with patch("builtins.open", mock_open(read_data=json_content)):
                apply_replacements("input.pptx", "replacements.json", "output.pptx")

        # 검증
        mock_prs.save.assert_called()

    @patch("replace.Presentation")
    @patch("replace.extract_text_inventory")
    @patch("replace.validate_replacements")
    @patch("builtins.open", new_callable=mock_open)
    def test_apply_replacements_validation_error(
        self, mock_file, mock_validate, mock_extract, mock_prs_class
    ):
        """에러 케이스: 검증 실패"""
        # Mock presentation
        mock_prs = MagicMock()
        mock_prs_class.return_value = mock_prs

        # Mock inventory
        inventory = {}
        mock_extract.return_value = inventory

        # Mock validation error
        mock_validate.return_value = ["Error: Invalid shape"]

        # Mock replacements
        replacements = {}
        json_content = json.dumps(replacements)

        # 실행
        with patch("builtins.open", mock_open(read_data=json_content)):
            with pytest.raises(ValueError) as exc_info:
                apply_replacements("input.pptx", "replacements.json", "output.pptx")

        # 검증
        assert "validation error" in str(exc_info.value)
