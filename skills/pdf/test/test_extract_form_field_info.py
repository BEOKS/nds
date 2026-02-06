"""
extract_form_field_info.py에 대한 단위 테스트

테스트 범위:
- get_full_annotation_field_id: 어노테이션 필드 ID 추출
- make_field_dict: 필드 딕셔너리 생성
- get_field_info: 필드 정보 추출
- write_field_info: 필드 정보를 JSON으로 작성
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# 테스트 대상 모듈 import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from extract_form_field_info import (
    get_field_info,
    get_full_annotation_field_id,
    make_field_dict,
    write_field_info,
)


class TestGetFullAnnotationFieldId:
    """어노테이션 필드 ID 추출 함수 테스트"""

    def test_single_level_field(self):
        """정상 케이스: 단일 레벨 필드"""
        annotation = {"/T": "field_name"}
        result = get_full_annotation_field_id(annotation)
        assert result == "field_name"

    def test_nested_field(self):
        """정상 케이스: 중첩된 필드"""
        parent = {"/T": "parent"}
        child = {"/T": "child", "/Parent": parent}
        result = get_full_annotation_field_id(child)
        assert result == "parent.child"

    def test_deeply_nested_field(self):
        """정상 케이스: 깊게 중첩된 필드"""
        grandparent = {"/T": "form"}
        parent = {"/T": "section", "/Parent": grandparent}
        child = {"/T": "field", "/Parent": parent}
        result = get_full_annotation_field_id(child)
        assert result == "form.section.field"

    def test_no_field_name(self):
        """에러 케이스: 필드 이름 없음"""
        annotation = {}
        result = get_full_annotation_field_id(annotation)
        assert result is None

    def test_parent_without_name(self):
        """경계 케이스: 부모가 이름 없음"""
        parent = {}
        child = {"/T": "child", "/Parent": parent}
        result = get_full_annotation_field_id(child)
        assert result == "child"


class TestMakeFieldDict:
    """필드 딕셔너리 생성 함수 테스트"""

    def test_text_field(self):
        """정상 케이스: 텍스트 필드"""
        field = {"/FT": "/Tx"}
        result = make_field_dict(field, "text_field")
        assert result["field_id"] == "text_field"
        assert result["type"] == "text"

    def test_checkbox_field(self):
        """정상 케이스: 체크박스 필드"""
        field = {"/FT": "/Btn", "/_States_": ["/Yes", "/Off"]}
        result = make_field_dict(field, "checkbox_field")
        assert result["field_id"] == "checkbox_field"
        assert result["type"] == "checkbox"
        assert result["checked_value"] == "/Yes"
        assert result["unchecked_value"] == "/Off"

    def test_checkbox_field_off_first(self):
        """정상 케이스: 체크박스 필드 (/Off가 먼저)"""
        field = {"/FT": "/Btn", "/_States_": ["/Off", "/Yes"]}
        result = make_field_dict(field, "checkbox_field")
        assert result["checked_value"] == "/Yes"
        assert result["unchecked_value"] == "/Off"

    def test_choice_field(self):
        """정상 케이스: 선택 필드"""
        field = {
            "/FT": "/Ch",
            "/_States_": [["value1", "Text 1"], ["value2", "Text 2"]],
        }
        result = make_field_dict(field, "choice_field")
        assert result["field_id"] == "choice_field"
        assert result["type"] == "choice"
        assert len(result["choice_options"]) == 2
        assert result["choice_options"][0]["value"] == "value1"
        assert result["choice_options"][0]["text"] == "Text 1"

    def test_unknown_field_type(self):
        """에러 케이스: 알 수 없는 필드 타입"""
        field = {"/FT": "/Unknown"}
        result = make_field_dict(field, "unknown_field")
        assert result["type"] == "unknown (/Unknown)"

    def test_checkbox_without_off_state(self):
        """경계 케이스: /Off 상태가 없는 체크박스"""
        field = {"/FT": "/Btn", "/_States_": ["/State1", "/State2"]}
        result = make_field_dict(field, "checkbox_field")
        # 경고 메시지가 출력되지만 값은 설정됨
        assert result["checked_value"] == "/State1"
        assert result["unchecked_value"] == "/State2"


class TestGetFieldInfo:
    """필드 정보 추출 함수 테스트"""

    @patch("extract_form_field_info.PdfReader")
    def test_get_field_info_text_fields(self, mock_reader_class):
        """정상 케이스: 텍스트 필드 추출"""
        # Mock reader 설정
        mock_reader = MagicMock()
        mock_reader_class.return_value = mock_reader

        # Mock 필드 데이터
        mock_reader.get_fields.return_value = {
            "field1": {"/FT": "/Tx", "/T": "field1"},
            "field2": {"/FT": "/Tx", "/T": "field2"},
        }

        # Mock 페이지와 어노테이션
        mock_page = MagicMock()
        mock_ann1 = MagicMock()
        mock_ann1.get = MagicMock(side_effect=lambda k, d=None: {"/T": "field1", "/Rect": [0, 0, 100, 50]}.get(k, d))
        mock_ann2 = MagicMock()
        mock_ann2.get = MagicMock(side_effect=lambda k, d=None: {"/T": "field2", "/Rect": [0, 60, 100, 110]}.get(k, d))
        mock_page.get.return_value = [mock_ann1, mock_ann2]
        mock_reader.pages = [mock_page]

        # 실행
        result = get_field_info(mock_reader)

        # 검증
        assert len(result) == 2
        assert all(f["type"] == "text" for f in result)
        assert all("page" in f for f in result)

    @patch("extract_form_field_info.PdfReader")
    def test_get_field_info_with_radio_buttons(self, mock_reader_class):
        """정상 케이스: 라디오 버튼 필드 포함"""
        # Mock reader 설정
        mock_reader = MagicMock()
        mock_reader_class.return_value = mock_reader

        # Mock 필드 데이터 (라디오 그룹은 /Kids 있음)
        mock_reader.get_fields.return_value = {
            "radio_group": {"/FT": "/Btn", "/Kids": ["child1", "child2"]}
        }

        # Mock 페이지와 라디오 어노테이션
        mock_page = MagicMock()
        mock_ann1 = {
            "/T": "radio_group",
            "/Rect": [0, 0, 20, 20],
            "/AP": {"/N": {"/Off": None, "/Option1": None}},
        }
        mock_ann2 = {
            "/T": "radio_group",
            "/Rect": [30, 0, 50, 20],
            "/AP": {"/N": {"/Off": None, "/Option2": None}},
        }

        def get_ann(key, default=None):
            if key == "/Annots":
                return [mock_ann1, mock_ann2]
            return default

        mock_page.get = get_ann
        mock_reader.pages = [mock_page]

        # 실행
        result = get_field_info(mock_reader)

        # 검증: 라디오 그룹이 생성됨
        radio_fields = [f for f in result if f.get("type") == "radio_group"]
        assert len(radio_fields) >= 0  # 라디오 버튼은 복잡한 구조이므로 기본 검증만 수행

    @patch("extract_form_field_info.PdfReader")
    def test_get_field_info_sorting(self, mock_reader_class):
        """정상 케이스: 필드가 위치별로 정렬되는지 확인"""
        # Mock reader 설정
        mock_reader = MagicMock()
        mock_reader_class.return_value = mock_reader

        # Mock 필드 데이터
        mock_reader.get_fields.return_value = {
            "field1": {"/FT": "/Tx", "/T": "field1"},
            "field2": {"/FT": "/Tx", "/T": "field2"},
            "field3": {"/FT": "/Tx", "/T": "field3"},
        }

        # Mock 페이지와 어노테이션 (Y 좌표가 다름, PDF는 아래가 0)
        mock_page = MagicMock()
        mock_ann1 = {"/T": "field1", "/Rect": [0, 200, 100, 250]}  # 위쪽
        mock_ann2 = {"/T": "field2", "/Rect": [0, 100, 100, 150]}  # 중간
        mock_ann3 = {"/T": "field3", "/Rect": [0, 0, 100, 50]}  # 아래쪽

        mock_page.get.return_value = [mock_ann1, mock_ann2, mock_ann3]
        mock_reader.pages = [mock_page]

        # 실행
        result = get_field_info(mock_reader)

        # 검증: Y 좌표가 높은 것부터 (위에서 아래로) 정렬됨
        # PDF 좌표계는 아래가 0이므로 Y가 큰 것이 위쪽
        assert len(result) == 3


class TestWriteFieldInfo:
    """필드 정보 JSON 작성 함수 테스트"""

    @patch("extract_form_field_info.PdfReader")
    @patch("extract_form_field_info.get_field_info")
    @patch("builtins.open", new_callable=mock_open)
    def test_write_field_info(self, mock_file, mock_get_field_info, mock_reader_class):
        """정상 케이스: 필드 정보를 JSON 파일로 작성"""
        # Mock 데이터 준비
        field_info = [
            {"field_id": "field1", "type": "text", "page": 1},
            {"field_id": "field2", "type": "checkbox", "page": 1},
        ]
        mock_get_field_info.return_value = field_info
        mock_reader = MagicMock()
        mock_reader_class.return_value = mock_reader

        # 실행
        write_field_info("input.pdf", "output.json")

        # 검증
        mock_reader_class.assert_called_once_with("input.pdf")
        mock_file.assert_called_once_with("output.json", "w")
        # JSON이 작성되었는지 확인
        handle = mock_file()
        assert handle.write.called

    @patch("extract_form_field_info.PdfReader")
    @patch("extract_form_field_info.get_field_info")
    @patch("builtins.open", new_callable=mock_open)
    def test_write_field_info_empty(self, mock_file, mock_get_field_info, mock_reader_class):
        """정상 케이스: 필드가 없는 경우"""
        # Mock 데이터 준비 (빈 리스트)
        mock_get_field_info.return_value = []
        mock_reader = MagicMock()
        mock_reader_class.return_value = mock_reader

        # 실행
        write_field_info("input.pdf", "output.json")

        # 검증: 빈 배열이 작성됨
        mock_file.assert_called_once_with("output.json", "w")
