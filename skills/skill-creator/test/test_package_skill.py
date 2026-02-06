#!/usr/bin/env python3
"""
package_skill.py 단위 테스트
pytest로 스킬 패키징 기능 검증
"""

import sys
import zipfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# 테스트 대상 모듈 임포트
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from package_skill import package_skill, main


class TestPackageSkill:
    """package_skill 함수 테스트"""

    def setup_method(self):
        """각 테스트 전에 실행되는 설정"""
        # validate_skill을 항상 성공하도록 mock
        self.validate_patcher = patch('package_skill.validate_skill')
        self.mock_validate = self.validate_patcher.start()
        self.mock_validate.return_value = (True, "Skill is valid!")

    def teardown_method(self):
        """각 테스트 후 정리"""
        self.validate_patcher.stop()

    def create_sample_skill(self, skill_path):
        """테스트용 샘플 스킬 생성"""
        skill_path.mkdir(parents=True, exist_ok=True)

        # SKILL.md 생성
        skill_md = skill_path / "SKILL.md"
        skill_md.write_text("""---
name: test-skill
description: Test skill for testing
---
# Test Skill
This is a test skill.""")

        # scripts/ 디렉토리
        scripts_dir = skill_path / "scripts"
        scripts_dir.mkdir()
        (scripts_dir / "example.py").write_text("print('hello')")

        # references/ 디렉토리
        refs_dir = skill_path / "references"
        refs_dir.mkdir()
        (refs_dir / "doc.md").write_text("# Documentation")

    def test_successful_packaging(self, tmp_path):
        """정상적인 패키징 테스트"""
        skill_path = tmp_path / "my-skill"
        self.create_sample_skill(skill_path)

        result = package_skill(skill_path)

        # .skill 파일 생성 확인
        assert result is not None
        assert result.exists()
        assert result.suffix == ".skill"
        assert result.name == "my-skill.skill"

        # ZIP 파일로 열기 확인
        with zipfile.ZipFile(result, 'r') as zf:
            names = zf.namelist()
            assert "my-skill/SKILL.md" in names
            assert "my-skill/scripts/example.py" in names
            assert "my-skill/references/doc.md" in names

    def test_with_output_directory(self, tmp_path):
        """출력 디렉토리 지정 테스트"""
        skill_path = tmp_path / "my-skill"
        output_dir = tmp_path / "output"
        self.create_sample_skill(skill_path)

        result = package_skill(skill_path, output_dir)

        # 지정된 디렉토리에 생성 확인
        assert result is not None
        assert result.parent == output_dir.resolve()
        assert result.exists()

    def test_skill_path_not_exists(self, tmp_path):
        """존재하지 않는 스킬 경로 테스트"""
        skill_path = tmp_path / "nonexistent"

        result = package_skill(skill_path)

        assert result is None

    def test_skill_path_not_directory(self, tmp_path):
        """파일을 스킬 경로로 지정한 경우 테스트"""
        skill_file = tmp_path / "file.txt"
        skill_file.write_text("not a directory")

        result = package_skill(skill_file)

        assert result is None

    def test_missing_skill_md(self, tmp_path):
        """SKILL.md가 없는 경우 테스트"""
        skill_path = tmp_path / "invalid-skill"
        skill_path.mkdir()

        result = package_skill(skill_path)

        assert result is None

    def test_validation_failure(self, tmp_path):
        """스킬 검증 실패 테스트"""
        skill_path = tmp_path / "invalid-skill"
        self.create_sample_skill(skill_path)

        # validate_skill이 실패하도록 설정
        self.mock_validate.return_value = (False, "Invalid frontmatter")

        result = package_skill(skill_path)

        assert result is None

    def test_output_directory_created(self, tmp_path):
        """출력 디렉토리가 자동 생성되는지 테스트"""
        skill_path = tmp_path / "my-skill"
        output_dir = tmp_path / "new" / "nested" / "output"
        self.create_sample_skill(skill_path)

        result = package_skill(skill_path, output_dir)

        # 출력 디렉토리가 생성되었는지 확인
        assert output_dir.exists()
        assert result is not None

    def test_zip_file_content(self, tmp_path):
        """ZIP 파일 내용 검증 테스트"""
        skill_path = tmp_path / "content-test"
        self.create_sample_skill(skill_path)

        # 추가 파일 생성
        (skill_path / "assets").mkdir()
        (skill_path / "assets" / "logo.png").write_bytes(b"fake png data")

        result = package_skill(skill_path)

        # ZIP 내용 확인
        with zipfile.ZipFile(result, 'r') as zf:
            # 모든 파일 포함 확인
            names = zf.namelist()
            assert "content-test/SKILL.md" in names
            assert "content-test/scripts/example.py" in names
            assert "content-test/references/doc.md" in names
            assert "content-test/assets/logo.png" in names

            # 파일 내용 확인
            skill_md_content = zf.read("content-test/SKILL.md").decode()
            assert "test-skill" in skill_md_content

    @patch('package_skill.zipfile.ZipFile')
    def test_zip_creation_error(self, mock_zipfile, tmp_path):
        """ZIP 파일 생성 중 예외 발생 테스트"""
        skill_path = tmp_path / "error-skill"
        self.create_sample_skill(skill_path)

        mock_zipfile.side_effect = IOError("Disk full")

        result = package_skill(skill_path)

        assert result is None


class TestMain:
    """main 함수 테스트"""

    def setup_method(self):
        """각 테스트 전에 실행되는 설정"""
        self.validate_patcher = patch('package_skill.validate_skill')
        self.mock_validate = self.validate_patcher.start()
        self.mock_validate.return_value = (True, "Skill is valid!")

    def teardown_method(self):
        """각 테스트 후 정리"""
        self.validate_patcher.stop()

    def create_sample_skill(self, skill_path):
        """테스트용 샘플 스킬 생성"""
        skill_path.mkdir(parents=True, exist_ok=True)
        skill_md = skill_path / "SKILL.md"
        skill_md.write_text("---\nname: test\ndescription: test\n---\n# Test")

    def test_missing_arguments(self):
        """인자 없이 실행 시 종료 테스트"""
        with patch('sys.argv', ['package_skill.py']):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_successful_execution(self, tmp_path):
        """정상 실행 테스트"""
        skill_path = tmp_path / "my-skill"
        self.create_sample_skill(skill_path)

        with patch('sys.argv', ['package_skill.py', str(skill_path)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

        # .skill 파일 생성 확인
        skill_file = Path.cwd() / "my-skill.skill"
        assert skill_file.exists()
        skill_file.unlink()  # 정리

    def test_with_output_directory(self, tmp_path):
        """출력 디렉토리 지정 실행 테스트"""
        skill_path = tmp_path / "my-skill"
        output_dir = tmp_path / "output"
        self.create_sample_skill(skill_path)

        with patch('sys.argv', ['package_skill.py', str(skill_path), str(output_dir)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0

        # 지정된 디렉토리에 생성 확인
        skill_file = output_dir / "my-skill.skill"
        assert skill_file.exists()

    def test_failed_execution(self, tmp_path):
        """실패 시 종료 코드 테스트"""
        nonexistent = tmp_path / "nonexistent"

        with patch('sys.argv', ['package_skill.py', str(nonexistent)]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1


class TestEdgeCases:
    """경계 케이스 테스트"""

    def setup_method(self):
        """각 테스트 전에 실행되는 설정"""
        self.validate_patcher = patch('package_skill.validate_skill')
        self.mock_validate = self.validate_patcher.start()
        self.mock_validate.return_value = (True, "Skill is valid!")

    def teardown_method(self):
        """각 테스트 후 정리"""
        self.validate_patcher.stop()

    def create_sample_skill(self, skill_path):
        """테스트용 샘플 스킬 생성"""
        skill_path.mkdir(parents=True, exist_ok=True)
        skill_md = skill_path / "SKILL.md"
        skill_md.write_text("---\nname: test\ndescription: test\n---\n# Test")

    def test_empty_skill_directory(self, tmp_path):
        """파일이 하나도 없는 스킬 디렉토리 테스트"""
        skill_path = tmp_path / "empty-skill"
        skill_path.mkdir()
        (skill_path / "SKILL.md").write_text("---\nname: test\ndescription: test\n---\n")

        result = package_skill(skill_path)

        assert result is not None
        with zipfile.ZipFile(result, 'r') as zf:
            names = zf.namelist()
            assert "empty-skill/SKILL.md" in names

    def test_nested_directories(self, tmp_path):
        """중첩된 디렉토리 구조 테스트"""
        skill_path = tmp_path / "nested-skill"
        self.create_sample_skill(skill_path)

        # 깊은 중첩 구조 생성
        deep_dir = skill_path / "a" / "b" / "c"
        deep_dir.mkdir(parents=True)
        (deep_dir / "deep.txt").write_text("deep file")

        result = package_skill(skill_path)

        with zipfile.ZipFile(result, 'r') as zf:
            names = zf.namelist()
            assert "nested-skill/a/b/c/deep.txt" in names

    def test_unicode_filenames(self, tmp_path):
        """유니코드 파일명 테스트"""
        skill_path = tmp_path / "unicode-skill"
        self.create_sample_skill(skill_path)

        # 유니코드 파일 생성
        (skill_path / "한글파일.txt").write_text("한글 내용")

        result = package_skill(skill_path)

        with zipfile.ZipFile(result, 'r') as zf:
            names = zf.namelist()
            assert "unicode-skill/한글파일.txt" in names
