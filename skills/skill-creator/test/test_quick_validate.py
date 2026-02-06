#!/usr/bin/env python3
"""
quick_validate.py 단위 테스트
pytest로 스킬 검증 기능 검증
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# 테스트 대상 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from quick_validate import validate_skill


class TestValidateSkill:
    """validate_skill 함수 테스트"""

    def create_skill_md(self, skill_path, content):
        """테스트용 SKILL.md 생성"""
        skill_path.mkdir(parents=True, exist_ok=True)
        skill_md = skill_path / "SKILL.md"
        skill_md.write_text(content)

    def test_valid_skill(self, tmp_path):
        """정상적인 스킬 검증 테스트"""
        skill_content = """---
name: test-skill
description: This is a test skill
---
# Test Skill
Content here."""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is True
        assert "valid" in message.lower()

    def test_missing_skill_md(self, tmp_path):
        """SKILL.md가 없는 경우 테스트"""
        valid, message = validate_skill(tmp_path)

        assert valid is False
        assert "not found" in message.lower()

    def test_missing_frontmatter(self, tmp_path):
        """프론트매터가 없는 경우 테스트"""
        skill_content = """# Test Skill
No frontmatter here."""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is False
        assert "frontmatter" in message.lower()

    def test_invalid_frontmatter_format(self, tmp_path):
        """잘못된 프론트매터 형식 테스트"""
        skill_content = """---
name: test-skill
description: test
# Missing closing ---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is False
        assert "format" in message.lower()

    def test_invalid_yaml(self, tmp_path):
        """잘못된 YAML 문법 테스트"""
        skill_content = """---
name: [unclosed list
description: test
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is False
        assert "yaml" in message.lower()

    def test_missing_name_field(self, tmp_path):
        """name 필드가 없는 경우 테스트"""
        skill_content = """---
description: test skill
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is False
        assert "name" in message.lower()

    def test_missing_description_field(self, tmp_path):
        """description 필드가 없는 경우 테스트"""
        skill_content = """---
name: test-skill
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is False
        assert "description" in message.lower()

    def test_invalid_name_format(self, tmp_path):
        """잘못된 name 형식 테스트 (대문자 포함)"""
        skill_content = """---
name: Test-Skill
description: test
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is False
        assert "hyphen-case" in message.lower()

    def test_name_with_special_characters(self, tmp_path):
        """특수문자가 포함된 name 테스트"""
        skill_content = """---
name: test_skill@123
description: test
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is False
        assert "hyphen-case" in message.lower()

    def test_name_starting_with_hyphen(self, tmp_path):
        """하이픈으로 시작하는 name 테스트"""
        skill_content = """---
name: -test-skill
description: test
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is False
        assert "hyphen" in message.lower()

    def test_name_ending_with_hyphen(self, tmp_path):
        """하이픈으로 끝나는 name 테스트"""
        skill_content = """---
name: test-skill-
description: test
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is False
        assert "hyphen" in message.lower()

    def test_name_consecutive_hyphens(self, tmp_path):
        """연속된 하이픈이 있는 name 테스트"""
        skill_content = """---
name: test--skill
description: test
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is False
        assert "consecutive" in message.lower()

    def test_name_too_long(self, tmp_path):
        """너무 긴 name 테스트 (64자 초과)"""
        long_name = "a" * 65
        skill_content = f"""---
name: {long_name}
description: test
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is False
        assert "too long" in message.lower()

    def test_description_with_angle_brackets(self, tmp_path):
        """꺾쇠괄호가 포함된 description 테스트"""
        skill_content = """---
name: test-skill
description: This is a <test> skill
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is False
        assert "angle bracket" in message.lower()

    def test_description_too_long(self, tmp_path):
        """너무 긴 description 테스트 (1024자 초과)"""
        long_desc = "a" * 1025
        skill_content = f"""---
name: test-skill
description: {long_desc}
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is False
        assert "too long" in message.lower()

    def test_unexpected_frontmatter_keys(self, tmp_path):
        """허용되지 않은 프론트매터 키 테스트"""
        skill_content = """---
name: test-skill
description: test
unknown_field: value
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is False
        assert "unexpected" in message.lower()

    def test_allowed_optional_fields(self, tmp_path):
        """허용된 선택 필드 테스트"""
        skill_content = """---
name: test-skill
description: test skill
license: MIT
allowed-tools:
  - read
  - write
metadata:
  author: test
  version: 1.0
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is True

    def test_name_not_string(self, tmp_path):
        """name이 문자열이 아닌 경우 테스트"""
        skill_content = """---
name: 123
description: test
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        # YAML에서 숫자는 정수로 파싱됨
        assert valid is False
        assert "string" in message.lower()

    def test_description_not_string(self, tmp_path):
        """description이 문자열이 아닌 경우 테스트"""
        skill_content = """---
name: test-skill
description: ['list', 'value']
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is False
        assert "string" in message.lower()

    def test_frontmatter_not_dict(self, tmp_path):
        """프론트매터가 딕셔너리가 아닌 경우 테스트"""
        skill_content = """---
- list
- item
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is False
        assert "dictionary" in message.lower()

    def test_valid_name_with_numbers(self, tmp_path):
        """숫자가 포함된 정상적인 name 테스트"""
        skill_content = """---
name: skill-v2-test
description: test
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        assert valid is True

    def test_empty_name(self, tmp_path):
        """빈 name 테스트"""
        skill_content = """---
name: ""
description: test
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        # 빈 문자열은 검증 통과 (name 필드가 있으므로)
        assert valid is True

    def test_empty_description(self, tmp_path):
        """빈 description 테스트"""
        skill_content = """---
name: test-skill
description: ""
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        valid, message = validate_skill(tmp_path)

        # 빈 문자열은 검증 통과 (description 필드가 있으므로)
        assert valid is True


class TestMainScript:
    """메인 스크립트 동작 테스트"""

    def create_skill_md(self, skill_path, content):
        """테스트용 SKILL.md 생성"""
        skill_path.mkdir(parents=True, exist_ok=True)
        skill_md = skill_path / "SKILL.md"
        skill_md.write_text(content)

    def test_main_with_valid_skill(self, tmp_path):
        """정상 스킬로 스크립트 실행 테스트"""
        skill_content = """---
name: test-skill
description: test
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        # __main__ 블록을 직접 실행하는 것을 시뮬레이션
        with patch('sys.argv', ['quick_validate.py', str(tmp_path)]):
            valid, message = validate_skill(str(tmp_path))
            assert valid is True

    def test_main_with_invalid_skill(self, tmp_path):
        """잘못된 스킬로 스크립트 실행 테스트"""
        skill_content = """No frontmatter"""
        self.create_skill_md(tmp_path, skill_content)

        with patch('sys.argv', ['quick_validate.py', str(tmp_path)]):
            valid, message = validate_skill(str(tmp_path))
            assert valid is False

    def test_validate_with_subprocess(self, tmp_path):
        """subprocess로 실제 스크립트 실행 테스트"""
        skill_content = """---
name: test-skill
description: test
---
Content"""
        self.create_skill_md(tmp_path, skill_content)

        import subprocess
        script_path = Path(__file__).parent.parent / "scripts" / "quick_validate.py"
        result = subprocess.run(
            [sys.executable, str(script_path), str(tmp_path)],
            capture_output=True
        )

        assert result.returncode == 0
        assert b"valid" in result.stdout.lower()
