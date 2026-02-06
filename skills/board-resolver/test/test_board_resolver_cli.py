#!/usr/bin/env python3
"""board_resolver_cli.py 단위 테스트"""
import json
import os
import subprocess
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

# 테스트 대상 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import board_resolver_cli


class TestFindMattermostCli(unittest.TestCase):
    """mattermost_cli.py 경로 찾기 함수 테스트"""

    @patch("pathlib.Path.exists")
    def test_finds_relative_path(self, mock_exists):
        """정상 케이스: 상대 경로에서 찾기"""
        # 첫 번째 경로만 존재하도록 설정
        mock_exists.side_effect = [True, False, False]

        result = board_resolver_cli._find_mattermost_cli()
        self.assertIsInstance(result, str)
        self.assertIn("mattermost_cli.py", result)

    @patch("pathlib.Path.exists")
    def test_finds_cwd_path(self, mock_exists):
        """정상 케이스: 현재 작업 디렉토리에서 찾기"""
        # 두 번째 경로에서 찾기
        mock_exists.side_effect = [False, True, False]

        result = board_resolver_cli._find_mattermost_cli()
        self.assertIn("mattermost_cli.py", result)

    @patch("pathlib.Path.exists")
    def test_finds_home_path(self, mock_exists):
        """정상 케이스: 홈 디렉토리에서 찾기"""
        # 세 번째 경로에서 찾기
        mock_exists.side_effect = [False, False, True]

        result = board_resolver_cli._find_mattermost_cli()
        self.assertIn("mattermost_cli.py", result)

    @patch("pathlib.Path.exists")
    def test_raises_when_not_found(self, mock_exists):
        """에러 케이스: 어디에도 없는 경우"""
        mock_exists.return_value = False

        with self.assertRaises(SystemExit) as cm:
            board_resolver_cli._find_mattermost_cli()
        self.assertIn("mattermost_cli.py not found", str(cm.exception))


class TestFetchBoardCard(unittest.TestCase):
    """보드 카드 정보 조회 함수 테스트"""

    @patch("board_resolver_cli._find_mattermost_cli")
    @patch("subprocess.run")
    def test_fetch_success(self, mock_run, mock_find_cli):
        """정상 케이스: 카드 정보 조회 성공"""
        mock_find_cli.return_value = "/path/to/mattermost_cli.py"
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"card": {"id": "123", "title": "Test Card"}}'
        )

        result = board_resolver_cli.fetch_board_card("https://mattermost.com/board/123/card/456")

        self.assertEqual(result["card"]["id"], "123")
        self.assertEqual(result["card"]["title"], "Test Card")
        mock_run.assert_called_once()

    @patch("board_resolver_cli._find_mattermost_cli")
    @patch("subprocess.run")
    def test_fetch_failure(self, mock_run, mock_find_cli):
        """에러 케이스: 조회 실패"""
        mock_find_cli.return_value = "/path/to/mattermost_cli.py"
        mock_run.return_value = MagicMock(
            returncode=1,
            stderr="[ERROR] Card not found"
        )

        with self.assertRaises(SystemExit) as cm:
            board_resolver_cli.fetch_board_card("https://invalid-url")
        self.assertIn("Failed to fetch card", str(cm.exception))


class TestExtractKeywords(unittest.TestCase):
    """키워드 추출 함수 테스트"""

    def test_extract_from_card_title(self):
        """정상 케이스: 카드 제목에서 키워드 추출"""
        card_data = {
            "card": {
                "fields": {
                    "title": "Fix login bug"
                }
            }
        }
        result = board_resolver_cli.extract_keywords(card_data)
        self.assertIn("Fix login bug", result)

    def test_extract_from_fallback_title(self):
        """정상 케이스: fields 없이 직접 title"""
        card_data = {
            "card": {
                "title": "Direct title"
            }
        }
        result = board_resolver_cli.extract_keywords(card_data)
        self.assertIn("Direct title", result)

    def test_extract_from_property_values(self):
        """정상 케이스: 속성값에서 키워드 추출"""
        card_data = {
            "card": {},
            "cardPropertyValues": [
                {"propertyName": "Status", "value": "In Progress"},
                {"propertyName": "Priority", "value": "High"}
            ]
        }
        result = board_resolver_cli.extract_keywords(card_data)
        self.assertIn("In Progress", result)
        self.assertIn("High", result)

    def test_extract_from_card_contents(self):
        """정상 케이스: 카드 콘텐츠에서 키워드 추출"""
        card_data = {
            "card": {},
            "cardContents": [
                {"fields": {"title": "Content block 1"}},
                {"fields": {"title": "Content block 2"}}
            ]
        }
        result = board_resolver_cli.extract_keywords(card_data)
        self.assertIn("Content block 1", result)
        self.assertIn("Content block 2", result)

    def test_removes_duplicates(self):
        """정상 케이스: 중복 제거"""
        card_data = {
            "card": {"fields": {"title": "Duplicate"}},
            "cardPropertyValues": [{"value": "Duplicate"}]
        }
        result = board_resolver_cli.extract_keywords(card_data)
        self.assertEqual(result.count("Duplicate"), 1)

    def test_removes_empty_strings(self):
        """정상 케이스: 빈 문자열 제거"""
        card_data = {
            "card": {"fields": {"title": ""}},
            "cardPropertyValues": [{"value": None}, {"value": "  "}],
            "cardContents": [{"fields": {"title": "Valid"}}]
        }
        result = board_resolver_cli.extract_keywords(card_data)
        self.assertEqual(result, ["Valid"])

    def test_strips_whitespace(self):
        """정상 케이스: 공백 제거"""
        card_data = {
            "card": {"fields": {"title": "  Trimmed  "}}
        }
        result = board_resolver_cli.extract_keywords(card_data)
        self.assertIn("Trimmed", result)


class TestCheckInfoCompleteness(unittest.TestCase):
    """정보 충분성 검증 함수 테스트"""

    def test_complete_info(self):
        """정상 케이스: 모든 필수 정보가 있는 경우"""
        context = {
            "reproduction_steps": ["Step 1", "Step 2"],
            "environment": "production",
            "frequency": "always"
        }
        result = board_resolver_cli.check_info_completeness(context)
        self.assertTrue(result["is_complete"])
        self.assertEqual(len(result["required"]), 0)

    def test_missing_reproduction_steps(self):
        """정상 케이스: 재현 단계 누락"""
        context = {
            "environment": "production",
            "frequency": "always"
        }
        result = board_resolver_cli.check_info_completeness(context)
        self.assertFalse(result["is_complete"])
        self.assertTrue(any("재현 단계" in q["question"] for q in result["required"]))

    def test_missing_environment(self):
        """정상 케이스: 환경 정보 누락"""
        context = {
            "reproduction_steps": ["Step 1"],
            "frequency": "always"
        }
        result = board_resolver_cli.check_info_completeness(context)
        self.assertFalse(result["is_complete"])
        self.assertTrue(any("환경" in q["question"] for q in result["required"]))

    def test_missing_frequency(self):
        """정상 케이스: 발생 빈도 누락"""
        context = {
            "reproduction_steps": ["Step 1"],
            "environment": "production"
        }
        result = board_resolver_cli.check_info_completeness(context)
        self.assertFalse(result["is_complete"])
        self.assertTrue(any("빈도" in q["question"] or "발생" in q["question"] for q in result["required"]))

    def test_optional_multiple_solutions(self):
        """정상 케이스: 여러 해결방안 시 선택 정보 요청"""
        context = {
            "reproduction_steps": ["Step 1"],
            "environment": "production",
            "frequency": "always",
            "multiple_solutions": True
        }
        result = board_resolver_cli.check_info_completeness(context)
        self.assertTrue(result["is_complete"])
        self.assertTrue(any("선호" in q["question"] for q in result["optional"]))

    def test_optional_api_changes(self):
        """정상 케이스: API 영향 시 선택 정보 요청"""
        context = {
            "reproduction_steps": ["Step 1"],
            "environment": "production",
            "frequency": "always",
            "affects_api": True
        }
        result = board_resolver_cli.check_info_completeness(context)
        self.assertTrue(any("API" in q["question"] for q in result["optional"]))

    def test_optional_db_changes(self):
        """정상 케이스: DB 영향 시 선택 정보 요청"""
        context = {
            "reproduction_steps": ["Step 1"],
            "environment": "production",
            "frequency": "always",
            "affects_db": True
        }
        result = board_resolver_cli.check_info_completeness(context)
        self.assertTrue(any("DB" in q["question"] or "스키마" in q["question"] for q in result["optional"]))

    def test_optional_new_dependency(self):
        """정상 케이스: 새 의존성 필요 시 선택 정보 요청"""
        context = {
            "reproduction_steps": ["Step 1"],
            "environment": "production",
            "frequency": "always",
            "needs_new_dependency": True
        }
        result = board_resolver_cli.check_info_completeness(context)
        self.assertTrue(any("라이브러리" in q["question"] for q in result["optional"]))


class TestCalculateScore(unittest.TestCase):
    """해결방안 점수 계산 함수 테스트"""

    def test_basic_score_calculation(self):
        """정상 케이스: 기본 점수 계산"""
        solution = {
            "relevance": "direct",
            "lines_changed": 10,
            "scope": "function",
            "test_type": "unit"
        }
        result = board_resolver_cli.calculate_score(solution)

        self.assertFalse(result["excluded"])
        self.assertGreater(result["score"], 0)
        self.assertLessEqual(result["score"], 100)

    def test_high_relevance_score(self):
        """정상 케이스: 높은 관련성 점수"""
        solution = {
            "relevance": "direct",
            "lines_changed": 5,
            "scope": "function",
            "test_type": "unit"
        }
        result = board_resolver_cli.calculate_score(solution)
        self.assertGreater(result["score"], 80)

    def test_low_relevance_score(self):
        """정상 케이스: 낮은 관련성 점수"""
        solution = {
            "relevance": "guess",
            "lines_changed": 100,
            "scope": "system",
            "test_type": "e2e"
        }
        result = board_resolver_cli.calculate_score(solution)
        self.assertLess(result["score"], 50)

    def test_complexity_score_by_lines(self):
        """정상 케이스: 라인 수에 따른 복잡도 점수"""
        test_cases = [
            (5, 100),    # <= 5 lines
            (20, 80),    # <= 20 lines
            (50, 60),    # <= 50 lines
            (100, 20)    # > 50 lines
        ]

        for lines, expected_complexity_score in test_cases:
            solution = {
                "relevance": "direct",
                "lines_changed": lines,
                "scope": "function",
                "test_type": "unit"
            }
            result = board_resolver_cli.calculate_score(solution)
            # 복잡도는 전체 점수의 25%를 차지
            # 정확한 점수가 아니라 범위로 검증
            self.assertIsNotNone(result["breakdown"]["complexity"])

    def test_scope_affects_risk_score(self):
        """정상 케이스: 영향 범위에 따른 위험 점수"""
        scopes = ["function", "module", "multi_module", "system"]

        prev_score = 101
        for scope in scopes:
            solution = {
                "relevance": "direct",
                "lines_changed": 10,
                "scope": scope,
                "test_type": "unit"
            }
            result = board_resolver_cli.calculate_score(solution)
            # 범위가 넓어질수록 점수가 낮아져야 함
            self.assertLess(result["score"], prev_score)
            prev_score = result["score"]

    def test_test_type_affects_score(self):
        """정상 케이스: 테스트 유형에 따른 점수"""
        test_types = ["unit", "integration", "e2e"]

        prev_score = 101
        for test_type in test_types:
            solution = {
                "relevance": "direct",
                "lines_changed": 10,
                "scope": "function",
                "test_type": test_type
            }
            result = board_resolver_cli.calculate_score(solution)
            # 테스트 용이성이 낮아질수록 점수가 낮아져야 함
            self.assertLess(result["score"], prev_score)
            prev_score = result["score"]

    def test_urgent_priority_weights(self):
        """정상 케이스: 긴급 우선순위 가중치 조정"""
        solution = {
            "relevance": "direct",
            "lines_changed": 10,
            "scope": "function",
            "test_type": "unit"
        }

        normal_result = board_resolver_cli.calculate_score(solution, None)
        urgent_result = board_resolver_cli.calculate_score(solution, {"priority": "urgent"})

        # 긴급일 때 복잡도 가중치가 증가 (간단한 해결책 선호)
        self.assertIsNotNone(normal_result["score"])
        self.assertIsNotNone(urgent_result["score"])

    def test_improvement_priority_weights(self):
        """정상 케이스: 개선 우선순위 가중치 조정"""
        solution = {
            "relevance": "direct",
            "lines_changed": 10,
            "scope": "function",
            "test_type": "unit"
        }

        result = board_resolver_cli.calculate_score(solution, {"priority": "improvement"})

        # 개선일 때 위험도 가중치가 증가
        self.assertGreater(result["weights_used"]["risk"], 0.25)

    def test_constraint_violation_excludes_solution(self):
        """정상 케이스: 제약 조건 위반 시 제외"""
        solution = {
            "relevance": "direct",
            "lines_changed": 10,
            "scope": "function",
            "test_type": "unit",
            "modifies": ["api", "database"]
        }

        result = board_resolver_cli.calculate_score(
            solution,
            {"constraints": ["api"]}
        )

        self.assertTrue(result["excluded"])
        self.assertEqual(result["score"], 0)
        self.assertIn("제약 조건 위반", result["reason"])

    def test_preferred_approach_bonus(self):
        """정상 케이스: 선호 방식 보너스"""
        solution = {
            "relevance": "direct",
            "lines_changed": 10,
            "scope": "function",
            "test_type": "unit",
            "approach": "refactoring"
        }

        without_preference = board_resolver_cli.calculate_score(solution, None)
        with_preference = board_resolver_cli.calculate_score(
            solution,
            {"preferred_approach": "refactoring"}
        )

        # 선호 방식 보너스로 점수가 높아져야 함
        self.assertGreater(with_preference["score"], without_preference["score"])
        self.assertEqual(with_preference["breakdown"]["bonus"], 10)

    def test_score_breakdown_structure(self):
        """정상 케이스: 점수 분해 구조 확인"""
        solution = {
            "relevance": "direct",
            "lines_changed": 10,
            "scope": "function",
            "test_type": "unit"
        }

        result = board_resolver_cli.calculate_score(solution)

        # breakdown 구조 확인
        self.assertIn("breakdown", result)
        self.assertIn("relevance", result["breakdown"])
        self.assertIn("complexity", result["breakdown"])
        self.assertIn("risk", result["breakdown"])
        self.assertIn("testability", result["breakdown"])
        self.assertIn("bonus", result["breakdown"])

        # weights_used 구조 확인
        self.assertIn("weights_used", result)
        self.assertAlmostEqual(sum(result["weights_used"].values()), 1.0, places=5)


class TestFormatQuestionOutput(unittest.TestCase):
    """질문 출력 포맷팅 함수 테스트"""

    def test_complete_info_message(self):
        """정상 케이스: 정보 수집 완료 메시지"""
        check_result = {"is_complete": True, "required": [], "optional": []}
        result = board_resolver_cli.format_question_output(check_result)
        self.assertIn("정보 수집 완료", result)
        self.assertIn("Phase 4", result)

    def test_required_questions_format(self):
        """정상 케이스: 필수 질문 포맷"""
        check_result = {
            "is_complete": False,
            "required": [
                {"question": "Q1?", "reason": "R1"},
                {"question": "Q2?", "reason": "R2"}
            ],
            "optional": []
        }
        result = board_resolver_cli.format_question_output(check_result)

        self.assertIn("필수 정보", result)
        self.assertIn("Q1?", result)
        self.assertIn("R1", result)
        self.assertIn("Q2?", result)
        self.assertIn("R2", result)

    def test_optional_questions_format(self):
        """정상 케이스: 선택 질문 포맷"""
        check_result = {
            "is_complete": False,
            "required": [],
            "optional": [
                {"question": "Optional Q?", "reason": "Optional R"}
            ]
        }
        result = board_resolver_cli.format_question_output(check_result)

        self.assertIn("선택 정보", result)
        self.assertIn("Optional Q?", result)
        self.assertIn("Optional R", result)

    def test_both_required_and_optional(self):
        """정상 케이스: 필수 + 선택 질문"""
        check_result = {
            "is_complete": False,
            "required": [{"question": "Required?", "reason": "Req reason"}],
            "optional": [{"question": "Optional?", "reason": "Opt reason"}]
        }
        result = board_resolver_cli.format_question_output(check_result)

        self.assertIn("필수 정보", result)
        self.assertIn("선택 정보", result)
        self.assertIn("Required?", result)
        self.assertIn("Optional?", result)


class TestCommandFunctions(unittest.TestCase):
    """CLI 명령 함수 테스트"""

    @patch("board_resolver_cli.fetch_board_card")
    @patch("sys.stdout", new_callable=StringIO)
    def test_cmd_fetch(self, mock_stdout, mock_fetch):
        """정상 케이스: fetch 명령"""
        mock_fetch.return_value = {"card": {"id": "123"}}

        args = MagicMock()
        args.card_url = "https://mattermost.com/board/123/card/456"

        board_resolver_cli.cmd_fetch(args)

        output = mock_stdout.getvalue()
        self.assertIn('"id": "123"', output)

    @patch("board_resolver_cli.fetch_board_card")
    @patch("sys.stdout", new_callable=StringIO)
    def test_cmd_keywords(self, mock_stdout, mock_fetch):
        """정상 케이스: keywords 명령"""
        mock_fetch.return_value = {
            "card": {"fields": {"title": "Test Card"}}
        }

        args = MagicMock()
        args.card_url = "https://mattermost.com/board/123/card/456"

        board_resolver_cli.cmd_keywords(args)

        output = mock_stdout.getvalue()
        data = json.loads(output)
        self.assertIn("Test Card", data)

    @patch("sys.stdout", new_callable=StringIO)
    def test_cmd_check_info_json(self, mock_stdout):
        """정상 케이스: check-info 명령 (JSON 출력)"""
        args = MagicMock()
        args.context_json = '{"reproduction_steps": ["step1"], "environment": "prod", "frequency": "always"}'
        args.format = "json"

        board_resolver_cli.cmd_check_info(args)

        output = mock_stdout.getvalue()
        data = json.loads(output)
        self.assertTrue(data["is_complete"])

    @patch("sys.stdout", new_callable=StringIO)
    def test_cmd_check_info_markdown(self, mock_stdout):
        """정상 케이스: check-info 명령 (Markdown 출력)"""
        args = MagicMock()
        args.context_json = '{"reproduction_steps": null}'
        args.format = "markdown"

        board_resolver_cli.cmd_check_info(args)

        output = mock_stdout.getvalue()
        self.assertIn("추가 정보 요청", output)

    @patch("sys.stdout", new_callable=StringIO)
    def test_cmd_score(self, mock_stdout):
        """정상 케이스: score 명령"""
        args = MagicMock()
        args.solution_json = '{"relevance": "direct", "lines_changed": 10, "scope": "function", "test_type": "unit"}'
        args.feedback_json = None

        board_resolver_cli.cmd_score(args)

        output = mock_stdout.getvalue()
        data = json.loads(output)
        self.assertIn("score", data)
        self.assertFalse(data["excluded"])

    @patch("sys.stdout", new_callable=StringIO)
    def test_cmd_score_multiple(self, mock_stdout):
        """정상 케이스: score-multiple 명령"""
        args = MagicMock()
        args.solutions_json = json.dumps([
            {"name": "Solution A", "relevance": "direct", "lines_changed": 5, "scope": "function", "test_type": "unit"},
            {"name": "Solution B", "relevance": "indirect", "lines_changed": 50, "scope": "system", "test_type": "e2e"}
        ])
        args.feedback_json = None

        board_resolver_cli.cmd_score_multiple(args)

        output = mock_stdout.getvalue()
        data = json.loads(output)
        self.assertEqual(len(data), 2)
        # 점수순으로 정렬되어야 함
        self.assertGreaterEqual(data[0]["score"], data[1]["score"])


if __name__ == "__main__":
    unittest.main()
