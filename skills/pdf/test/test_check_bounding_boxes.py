"""
check_bounding_boxes.py에 대한 단위 테스트

테스트 범위:
- get_bounding_box_messages: 경계 박스 검증 메시지 생성
- rects_intersect: 사각형 교차 검사 (내부 함수, 간접 테스트)
"""

import json
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# 테스트 대상 모듈 import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from check_bounding_boxes import get_bounding_box_messages


class TestGetBoundingBoxMessages:
    """경계 박스 검증 함수 테스트"""

    def test_valid_non_overlapping_boxes(self):
        """정상 케이스: 겹치지 않는 경계 박스"""
        fields_data = {
            "form_fields": [
                {
                    "description": "Field 1",
                    "page_number": 1,
                    "label_bounding_box": [0, 0, 100, 50],
                    "entry_bounding_box": [0, 60, 100, 110],
                },
                {
                    "description": "Field 2",
                    "page_number": 1,
                    "label_bounding_box": [120, 0, 220, 50],
                    "entry_bounding_box": [120, 60, 220, 110],
                },
            ]
        }
        json_stream = StringIO(json.dumps(fields_data))

        messages = get_bounding_box_messages(json_stream)

        # 성공 메시지 확인
        assert any("SUCCESS" in msg for msg in messages)
        assert any("All bounding boxes are valid" in msg for msg in messages)

    def test_label_and_entry_intersection(self):
        """에러 케이스: 같은 필드의 label과 entry 박스가 겹침"""
        fields_data = {
            "form_fields": [
                {
                    "description": "Field 1",
                    "page_number": 1,
                    "label_bounding_box": [0, 0, 100, 100],
                    "entry_bounding_box": [50, 50, 150, 150],  # 겹침
                }
            ]
        }
        json_stream = StringIO(json.dumps(fields_data))

        messages = get_bounding_box_messages(json_stream)

        # 실패 메시지 확인
        assert any("FAILURE" in msg for msg in messages)
        assert any(
            "intersection between label and entry bounding boxes" in msg
            for msg in messages
        )

    def test_different_fields_intersection(self):
        """에러 케이스: 다른 필드의 박스가 겹침"""
        fields_data = {
            "form_fields": [
                {
                    "description": "Field 1",
                    "page_number": 1,
                    "label_bounding_box": [0, 0, 100, 50],
                    "entry_bounding_box": [0, 60, 100, 110],
                },
                {
                    "description": "Field 2",
                    "page_number": 1,
                    "label_bounding_box": [50, 20, 150, 70],  # Field 1의 entry와 겹침
                    "entry_bounding_box": [50, 80, 150, 130],
                },
            ]
        }
        json_stream = StringIO(json.dumps(fields_data))

        messages = get_bounding_box_messages(json_stream)

        # 실패 메시지 확인
        assert any("FAILURE" in msg for msg in messages)
        assert any("Field 1" in msg and "Field 2" in msg for msg in messages)

    def test_entry_height_too_small_for_font(self):
        """에러 케이스: entry 박스 높이가 폰트 크기보다 작음"""
        fields_data = {
            "form_fields": [
                {
                    "description": "Field 1",
                    "page_number": 1,
                    "label_bounding_box": [0, 0, 100, 20],
                    "entry_bounding_box": [0, 30, 100, 40],  # 높이 10, 폰트 크기 14
                    "entry_text": {"font_size": 14},
                }
            ]
        }
        json_stream = StringIO(json.dumps(fields_data))

        messages = get_bounding_box_messages(json_stream)

        # 실패 메시지 확인
        assert any("FAILURE" in msg for msg in messages)
        assert any("entry bounding box height" in msg for msg in messages)
        assert any("too short for the text content" in msg for msg in messages)

    def test_different_pages_no_intersection(self):
        """정상 케이스: 다른 페이지의 필드는 겹쳐도 문제 없음"""
        fields_data = {
            "form_fields": [
                {
                    "description": "Field 1",
                    "page_number": 1,
                    "label_bounding_box": [0, 0, 100, 50],
                    "entry_bounding_box": [0, 60, 100, 110],
                },
                {
                    "description": "Field 2",
                    "page_number": 2,  # 다른 페이지
                    "label_bounding_box": [0, 0, 100, 50],  # 같은 좌표지만 다른 페이지
                    "entry_bounding_box": [0, 60, 100, 110],
                },
            ]
        }
        json_stream = StringIO(json.dumps(fields_data))

        messages = get_bounding_box_messages(json_stream)

        # 성공 메시지 확인
        assert any("SUCCESS" in msg for msg in messages)

    def test_edge_touching_boxes(self):
        """경계 케이스: 박스가 모서리만 닿는 경우 (겹침 아님)"""
        fields_data = {
            "form_fields": [
                {
                    "description": "Field 1",
                    "page_number": 1,
                    "label_bounding_box": [0, 0, 100, 50],
                    "entry_bounding_box": [0, 50, 100, 100],  # Y=50에서 정확히 닿음
                }
            ]
        }
        json_stream = StringIO(json.dumps(fields_data))

        messages = get_bounding_box_messages(json_stream)

        # 성공 메시지 확인 (모서리만 닿는 것은 겹침이 아님)
        assert any("SUCCESS" in msg for msg in messages)

    def test_many_errors_abort(self):
        """경계 케이스: 에러가 20개 이상이면 중단"""
        # 25개의 겹치는 필드 생성
        form_fields = []
        for i in range(25):
            form_fields.append(
                {
                    "description": f"Field {i}",
                    "page_number": 1,
                    "label_bounding_box": [0, i * 10, 100, i * 10 + 60],  # 모두 겹침
                    "entry_bounding_box": [0, i * 10 + 70, 100, i * 10 + 120],
                }
            )

        fields_data = {"form_fields": form_fields}
        json_stream = StringIO(json.dumps(fields_data))

        messages = get_bounding_box_messages(json_stream)

        # 중단 메시지 확인
        assert any("Aborting further checks" in msg for msg in messages)

    def test_empty_fields(self):
        """경계 케이스: 필드가 없는 경우"""
        fields_data = {"form_fields": []}
        json_stream = StringIO(json.dumps(fields_data))

        messages = get_bounding_box_messages(json_stream)

        # 메시지 확인
        assert len(messages) >= 1
        assert "Read 0 fields" in messages[0]

    def test_entry_height_exactly_font_size(self):
        """경계 케이스: entry 높이가 정확히 폰트 크기와 같음"""
        fields_data = {
            "form_fields": [
                {
                    "description": "Field 1",
                    "page_number": 1,
                    "label_bounding_box": [0, 0, 100, 20],
                    "entry_bounding_box": [0, 30, 100, 44],  # 높이 14, 폰트 크기 14
                    "entry_text": {"font_size": 14},
                }
            ]
        }
        json_stream = StringIO(json.dumps(fields_data))

        messages = get_bounding_box_messages(json_stream)

        # 성공 메시지 확인 (같으면 문제 없음)
        assert any("SUCCESS" in msg for msg in messages)

    def test_entry_without_text_no_font_check(self):
        """정상 케이스: entry_text가 없으면 폰트 크기 검사 안 함"""
        fields_data = {
            "form_fields": [
                {
                    "description": "Field 1",
                    "page_number": 1,
                    "label_bounding_box": [0, 0, 100, 20],
                    "entry_bounding_box": [0, 30, 100, 35],  # 높이 5
                    # entry_text 없음
                }
            ]
        }
        json_stream = StringIO(json.dumps(fields_data))

        messages = get_bounding_box_messages(json_stream)

        # 성공 메시지 확인
        assert any("SUCCESS" in msg for msg in messages)

    def test_partial_overlap(self):
        """에러 케이스: 박스가 부분적으로 겹침"""
        fields_data = {
            "form_fields": [
                {
                    "description": "Field 1",
                    "page_number": 1,
                    "label_bounding_box": [0, 0, 100, 50],
                    "entry_bounding_box": [50, 40, 150, 90],  # label과 부분 겹침
                }
            ]
        }
        json_stream = StringIO(json.dumps(fields_data))

        messages = get_bounding_box_messages(json_stream)

        # 실패 메시지 확인
        assert any("FAILURE" in msg for msg in messages)
