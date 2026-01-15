#!/usr/bin/env python3
"""보드 이슈 분석 지원 유틸리티"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def _find_mattermost_cli() -> str:
    """mattermost_cli.py 경로 찾기"""
    # 현재 스크립트 기준 상대 경로
    script_dir = Path(__file__).parent

    # 가능한 경로들
    possible_paths = [
        script_dir.parent.parent / "gabia-dev-mcp-mattermost" / "scripts" / "mattermost_cli.py",
        Path.cwd() / "scripts" / "mattermost_cli.py",
        Path.home() / ".claude" / "skills" / "gabia-dev-mcp-mattermost" / "scripts" / "mattermost_cli.py",
    ]

    for path in possible_paths:
        if path.exists():
            return str(path)

    raise SystemExit("[ERROR] mattermost_cli.py not found. Please ensure gabia-dev-mcp-mattermost skill is installed.")


def fetch_board_card(card_url: str) -> dict:
    """Mattermost 보드 카드 정보 조회"""
    cli_path = _find_mattermost_cli()
    result = subprocess.run(
        ["python3", cli_path, "board-card", "--card-url", card_url],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        raise SystemExit(f"[ERROR] Failed to fetch card: {result.stderr}")
    return json.loads(result.stdout)


def extract_keywords(card_data: dict) -> list[str]:
    """카드에서 검색 키워드 추출"""
    keywords = []

    # 카드 제목
    card = card_data.get("card", {})
    fields = card.get("fields", {})
    title = fields.get("title", "") or card.get("title", "")
    if title:
        keywords.append(title)

    # 속성값
    for prop in card_data.get("cardPropertyValues", []):
        value = prop.get("value")
        if value and isinstance(value, str):
            keywords.append(value)

    # 콘텐츠 블록
    for content in card_data.get("cardContents", []):
        content_fields = content.get("fields", {})
        text = content_fields.get("title", "")
        if text:
            keywords.append(text)

    # 중복 제거 및 빈 문자열 제거
    return list(set(k.strip() for k in keywords if k and k.strip()))


def check_info_completeness(context: dict) -> dict:
    """정보 충분성 검증 및 필요 질문 생성"""
    required = []
    optional = []

    # 필수 정보 체크
    if not context.get("reproduction_steps"):
        required.append({
            "question": "이슈가 발생하는 구체적인 재현 단계를 알려주세요",
            "reason": "정확한 원인 파악을 위해 재현 조건이 필요합니다"
        })

    if not context.get("environment"):
        required.append({
            "question": "어떤 환경에서 발생하나요? (개발/스테이징/운영)",
            "reason": "환경별로 원인이 다를 수 있습니다"
        })

    if not context.get("frequency"):
        required.append({
            "question": "항상 발생하나요, 아니면 간헐적으로 발생하나요?",
            "reason": "발생 빈도에 따라 원인 유형이 달라집니다"
        })

    # 선택 정보 체크 (상황에 따라)
    if context.get("multiple_solutions"):
        optional.append({
            "question": "선호하는 해결 방식이 있나요?",
            "reason": "여러 해결방안이 가능하여 선호도 확인이 도움됩니다"
        })

    if context.get("affects_api"):
        optional.append({
            "question": "API 시그니처 변경이 가능한가요?",
            "reason": "하위 호환성 영향을 판단하기 위해 필요합니다"
        })

    if context.get("affects_db"):
        optional.append({
            "question": "DB 스키마 변경이 허용되나요?",
            "reason": "근본적 해결을 위해 스키마 변경이 필요할 수 있습니다"
        })

    if context.get("needs_new_dependency"):
        optional.append({
            "question": "새로운 라이브러리 추가가 가능한가요?",
            "reason": "일부 해결방안에서 외부 라이브러리가 필요할 수 있습니다"
        })

    return {
        "is_complete": len(required) == 0,
        "required": required,
        "optional": optional
    }


def calculate_score(solution: dict, user_feedback: dict | None = None) -> dict:
    """해결방안 적합도 점수 계산 (사용자 피드백 반영)"""

    # 기본 가중치
    weights = {
        "relevance": 0.40,
        "complexity": 0.25,
        "risk": 0.20,
        "testability": 0.15
    }

    # 우선순위에 따른 가중치 조정
    if user_feedback:
        priority = user_feedback.get("priority", "normal")
        if priority == "urgent":
            weights = {
                "relevance": 0.35,
                "complexity": 0.35,
                "risk": 0.15,
                "testability": 0.15
            }
        elif priority == "improvement":
            weights = {
                "relevance": 0.35,
                "complexity": 0.20,
                "risk": 0.30,
                "testability": 0.15
            }

    # 제약 조건 위반 체크
    if user_feedback:
        constraints = user_feedback.get("constraints", [])
        modifies = solution.get("modifies", [])
        for constraint in constraints:
            if constraint in modifies:
                return {
                    "score": 0,
                    "excluded": True,
                    "reason": f"제약 조건 위반: {constraint} 수정 불가"
                }

    scores = {}

    # 원인 적합도 (40점 만점 → 100점 스케일)
    relevance = solution.get("relevance", "indirect")
    relevance_map = {"direct": 100, "indirect": 62.5, "guess": 25}
    scores["relevance"] = relevance_map.get(relevance, 25)

    # 구현 복잡도 (25점 만점 → 100점 스케일)
    lines = solution.get("lines_changed", 50)
    if lines <= 5:
        scores["complexity"] = 100
    elif lines <= 20:
        scores["complexity"] = 80
    elif lines <= 50:
        scores["complexity"] = 60
    else:
        scores["complexity"] = 20

    # 부작용 위험 (20점 만점 → 100점 스케일)
    scope = solution.get("scope", "system")
    scope_map = {"function": 100, "module": 75, "multi_module": 50, "system": 25}
    scores["risk"] = scope_map.get(scope, 25)

    # 테스트 용이성 (15점 만점 → 100점 스케일)
    test_type = solution.get("test_type", "e2e")
    test_map = {"unit": 100, "integration": 67, "e2e": 33}
    scores["testability"] = test_map.get(test_type, 33)

    # 가중 평균 계산
    total = sum(scores[k] * weights[k] for k in weights)

    # 사용자 선호도 보너스
    bonus = 0
    if user_feedback:
        preferred = user_feedback.get("preferred_approach")
        if preferred and solution.get("approach") == preferred:
            bonus = 10

    final_score = min(100, int(total + bonus))

    return {
        "score": final_score,
        "excluded": False,
        "breakdown": {
            "relevance": int(scores["relevance"] * weights["relevance"]),
            "complexity": int(scores["complexity"] * weights["complexity"]),
            "risk": int(scores["risk"] * weights["risk"]),
            "testability": int(scores["testability"] * weights["testability"]),
            "bonus": bonus
        },
        "weights_used": weights
    }


def format_question_output(check_result: dict) -> str:
    """질문 결과를 포맷팅하여 출력"""
    if check_result["is_complete"]:
        return "정보 수집 완료. Phase 4로 진행 가능합니다."

    lines = ["## 추가 정보 요청\n"]
    lines.append("해결방안을 정확히 도출하기 위해 다음 정보가 필요합니다:\n")

    if check_result["required"]:
        lines.append("### 필수 정보")
        for i, item in enumerate(check_result["required"], 1):
            lines.append(f"{i}. {item['question']}")
            lines.append(f"   - 필요 이유: {item['reason']}")
        lines.append("")

    if check_result["optional"]:
        lines.append("### 선택 정보 (있으면 도움됨)")
        start_num = len(check_result["required"]) + 1
        for i, item in enumerate(check_result["optional"], start_num):
            lines.append(f"{i}. {item['question']}")
            lines.append(f"   - 필요 이유: {item['reason']}")
        lines.append("")

    lines.append("위 정보를 제공해 주시면 더 정확한 해결방안을 제시할 수 있습니다.")

    return "\n".join(lines)


def cmd_fetch(args: argparse.Namespace) -> None:
    """보드 카드 정보 조회"""
    data = fetch_board_card(args.card_url)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_keywords(args: argparse.Namespace) -> None:
    """카드에서 키워드 추출"""
    data = fetch_board_card(args.card_url)
    keywords = extract_keywords(data)
    print(json.dumps(keywords, ensure_ascii=False))


def cmd_check_info(args: argparse.Namespace) -> None:
    """정보 충분성 검증"""
    context = json.loads(args.context_json)
    result = check_info_completeness(context)

    if args.format == "markdown":
        print(format_question_output(result))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_score(args: argparse.Namespace) -> None:
    """해결방안 점수 계산"""
    solution = json.loads(args.solution_json)
    feedback = json.loads(args.feedback_json) if args.feedback_json else None
    result = calculate_score(solution, feedback)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_score_multiple(args: argparse.Namespace) -> None:
    """여러 해결방안 점수 계산 및 정렬"""
    solutions = json.loads(args.solutions_json)
    feedback = json.loads(args.feedback_json) if args.feedback_json else None

    results = []
    for i, solution in enumerate(solutions):
        score_result = calculate_score(solution, feedback)
        score_result["solution_index"] = i
        score_result["solution_name"] = solution.get("name", f"Solution #{i+1}")
        results.append(score_result)

    # 점수순 정렬 (제외된 것은 맨 뒤로)
    results.sort(key=lambda x: (x.get("excluded", False), -x.get("score", 0)))

    print(json.dumps(results, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Board Resolver CLI - 보드 이슈 분석 지원 유틸리티"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # fetch 명령
    fetch = sub.add_parser("fetch", help="보드 카드 정보 조회")
    fetch.add_argument("--card-url", required=True, help="Mattermost Boards 카드 URL")
    fetch.set_defaults(func=cmd_fetch)

    # keywords 명령
    kw = sub.add_parser("keywords", help="카드에서 검색 키워드 추출")
    kw.add_argument("--card-url", required=True, help="Mattermost Boards 카드 URL")
    kw.set_defaults(func=cmd_keywords)

    # check-info 명령
    check = sub.add_parser("check-info", help="정보 충분성 검증")
    check.add_argument("--context-json", required=True, help="현재 수집된 정보 (JSON)")
    check.add_argument("--format", choices=["json", "markdown"], default="json", help="출력 형식")
    check.set_defaults(func=cmd_check_info)

    # score 명령
    sc = sub.add_parser("score", help="해결방안 점수 계산")
    sc.add_argument("--solution-json", required=True, help="해결방안 정보 (JSON)")
    sc.add_argument("--feedback-json", help="사용자 피드백 (JSON)")
    sc.set_defaults(func=cmd_score)

    # score-multiple 명령
    scm = sub.add_parser("score-multiple", help="여러 해결방안 점수 계산 및 정렬")
    scm.add_argument("--solutions-json", required=True, help="해결방안 목록 (JSON 배열)")
    scm.add_argument("--feedback-json", help="사용자 피드백 (JSON)")
    scm.set_defaults(func=cmd_score_multiple)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
