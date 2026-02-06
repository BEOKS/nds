#!/usr/bin/env python3
"""
init_skill.py 단위 테스트
pytest로 스킬 초기화 기능 검증
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# 테스트 대상 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from init_skill import title_case_skill_name, init_skill, main


class TestTitleCaseSkillName:
    """title_case_skill_name 함수 테스트"""

    def test_single_word(self):
        """단일 단어 변환 테스트"""
        assert title_case_skill_name("test") == "Test"

    def test_hyphenated_words(self):
        """하이픈으로 연결된 단어 변환 테스트"""
        assert title_case_skill_name("my-new-skill") == "My New Skill"

    def test_with_numbers(self):
        """숫자가 포함된 경우 테스트"""
        assert title_case_skill_name("skill-v2") == "Skill V2"

    def test_empty_string(self):
        """빈 문자열 처리 테스트"""
        assert title_case_skill_name("") == ""


class TestInitSkill:
    """init_skill 함수 테스트"""

    def test_successful_creation(self, tmp_path):
        """정상적인 스킬 생성 테스트"""
        skill_name = "test-skill"
        result = init_skill(skill_name, tmp_path)

        # 반환값 확인
        assert result is not None
        assert result == tmp_path / skill_name

        # 디렉토리 생성 확인
        assert result.exists()
        assert result.is_dir()

        # SKILL.md 생성 확인
        skill_md = result / "SKILL.md"
        assert skill_md.exists()
        content = skill_md.read_text()
        assert "name: test-skill" in content
        assert "# Test Skill" in content

        # 리소스 디렉토리 확인
        assert (result / "scripts").exists()
        assert (result / "scripts" / "example.py").exists()
        assert (result / "references").exists()
        assert (result / "references" / "api_reference.md").exists()
        assert (result / "assets").exists()
        assert (result / "assets" / "example_asset.txt").exists()

    def test_directory_already_exists(self, tmp_path):
        """이미 존재하는 디렉토리 처리 테스트"""
        skill_name = "existing-skill"
        skill_dir = tmp_path / skill_name
        skill_dir.mkdir()

        result = init_skill(skill_name, tmp_path)

        # 에러로 None 반환 확인
        assert result is None

    def test_parent_directory_not_exists(self, tmp_path):
        """부모 디렉토리가 없을 때 생성 테스트"""
        skill_name = "nested-skill"
        nested_path = tmp_path / "nonexistent" / "path"

        result = init_skill(skill_name, nested_path)

        # 부모 디렉토리가 자동 생성되어야 함
        assert result is not None
        assert result.exists()

    def test_script_executable(self, tmp_path):
        """생성된 스크립트의 실행 권한 확인 테스트"""
        skill_name = "exec-test"
        result = init_skill(skill_name, tmp_path)

        script_file = result / "scripts" / "example.py"
        assert script_file.exists()

        # 실행 권한 확인 (owner execute bit)
        import os
        stat_info = os.stat(script_file)
        assert stat_info.st_mode & 0o100  # owner execute

    @patch('init_skill.Path.mkdir')
    def test_mkdir_exception(self, mock_mkdir, tmp_path):
        """디렉토리 생성 중 예외 발생 테스트"""
        mock_mkdir.side_effect = PermissionError("Permission denied")

        skill_name = "error-skill"
        result = init_skill(skill_name, tmp_path)

        assert result is None

    @patch('init_skill.Path.write_text')
    def test_skill_md_write_error(self, mock_write, tmp_path):
        """SKILL.md 작성 중 예외 발생 테스트"""
        skill_name = "write-error"
        skill_dir = tmp_path / skill_name

        # mkdir는 성공하지만 write_text에서 실패
        mock_write.side_effect = IOError("Disk full")

        with patch('init_skill.Path.mkdir'):
            result = init_skill(skill_name, tmp_path)

        assert result is None


class TestMain:
    """main 함수 테스트"""

    def test_missing_arguments(self):
        """인자 없이 실행 시 종료 테스트"""
        with patch('sys.argv', ['init_skill.py']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_missing_path_flag(self):
        """--path 플래그 없이 실행 시 종료 테스트"""
        with patch('sys.argv', ['init_skill.py', 'my-skill']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_successful_execution(self, tmp_path):
        """정상 실행 테스트"""
        with patch('sys.argv', ['init_skill.py', 'test-skill', '--path', str(tmp_path)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

        # 결과 확인
        skill_dir = tmp_path / "test-skill"
        assert skill_dir.exists()

    def test_failed_execution(self, tmp_path):
        """실패 시 종료 코드 테스트"""
        # 이미 존재하는 디렉토리
        skill_dir = tmp_path / "existing"
        skill_dir.mkdir()

        with patch('sys.argv', ['init_skill.py', 'existing', '--path', str(tmp_path)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_template_content_in_files(self, tmp_path):
        """생성된 파일들의 템플릿 내용 확인 테스트"""
        skill_name = "content-test"
        result = init_skill(skill_name, tmp_path)

        # SKILL.md 내용 확인
        skill_md = result / "SKILL.md"
        content = skill_md.read_text()
        assert "TODO" in content
        assert "## Overview" in content
        assert "## Resources" in content

        # example.py 내용 확인
        example_script = result / "scripts" / "example.py"
        script_content = example_script.read_text()
        assert skill_name in script_content
        assert "#!/usr/bin/env python3" in script_content

        # reference 내용 확인
        reference = result / "references" / "api_reference.md"
        ref_content = reference.read_text()
        assert "Reference Documentation" in ref_content


class TestEdgeCases:
    """경계 케이스 테스트"""

    def test_special_characters_in_name(self, tmp_path):
        """특수 문자가 포함된 스킬명 테스트"""
        # 하이픈과 숫자는 허용
        skill_name = "my-skill-123"
        result = init_skill(skill_name, tmp_path)
        assert result is not None

    def test_very_long_path(self, tmp_path):
        """매우 긴 경로 테스트"""
        long_path = tmp_path / "a" / "b" / "c" / "d" / "e" / "f"
        skill_name = "deep-skill"
        result = init_skill(skill_name, long_path)

        assert result is not None
        assert result.exists()

    def test_unicode_in_path(self, tmp_path):
        """유니코드 경로 테스트"""
        unicode_path = tmp_path / "한글경로"
        unicode_path.mkdir()
        skill_name = "unicode-skill"
        result = init_skill(skill_name, unicode_path)

        assert result is not None
        assert result.exists()
