#!/usr/bin/env python3
"""
document.py에 대한 단위 테스트
Document 클래스와 DocxXMLEditor 클래스의 주석 추가, 변경 사항 추적 기능 테스트
"""

import sys
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# test_utilities.py와 동일한 패턴으로 import
_scripts_dir = str(Path(__file__).parent.parent / "scripts")
sys.path.insert(0, _scripts_dir)

# ooxml 패키지만 mock (defusedxml은 실제 사용)
mock_ooxml = MagicMock()
mock_ooxml.scripts.pack.pack_document = MagicMock()
mock_ooxml.scripts.validation.docx.DOCXSchemaValidator = MagicMock()
mock_ooxml.scripts.validation.redlining.RedliningValidator = MagicMock()
sys.modules['ooxml'] = mock_ooxml
sys.modules['ooxml.scripts'] = mock_ooxml.scripts
sys.modules['ooxml.scripts.pack'] = mock_ooxml.scripts.pack
sys.modules['ooxml.scripts.validation'] = mock_ooxml.scripts.validation
sys.modules['ooxml.scripts.validation.docx'] = mock_ooxml.scripts.validation.docx
sys.modules['ooxml.scripts.validation.redlining'] = mock_ooxml.scripts.validation.redlining

# utilities를 먼저 import
from utilities import XMLEditor

# document.py가 "from .utilities import XMLEditor"를 할 때를 대비하여
# scripts 패키지를 만들고 utilities를 등록
import types
_scripts_package = types.ModuleType('scripts')
_scripts_package.__path__ = [_scripts_dir]
_scripts_package.utilities = sys.modules['utilities']
sys.modules['scripts'] = _scripts_package
sys.modules['scripts.utilities'] = sys.modules['utilities']

# 이제 document를 import (상대 import가 동작함)
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "scripts.document",
    Path(_scripts_dir) / "document.py",
    submodule_search_locations=[]
)
_document_module = importlib.util.module_from_spec(_spec)
_document_module.__package__ = "scripts"
sys.modules['scripts.document'] = _document_module
_spec.loader.exec_module(_document_module)

Document = _document_module.Document
DocxXMLEditor = _document_module.DocxXMLEditor
_generate_hex_id = _document_module._generate_hex_id
_generate_rsid = _document_module._generate_rsid


class TestGenerators:
    """헬퍼 함수 테스트"""

    def test_generate_hex_id(self):
        """8자리 hex ID 생성"""
        hex_id = _generate_hex_id()

        assert len(hex_id) == 8
        assert all(c in '0123456789ABCDEF' for c in hex_id)
        # 범위 확인: 0x7FFFFFFF 이하
        assert int(hex_id, 16) <= 0x7FFFFFFF
        assert int(hex_id, 16) >= 1

    def test_generate_rsid(self):
        """8자리 RSID 생성"""
        rsid = _generate_rsid()

        assert len(rsid) == 8
        assert all(c in '0123456789ABCDEF' for c in rsid)

    def test_generate_hex_id_uniqueness(self):
        """생성된 ID가 충분히 고유한지 확인"""
        ids = [_generate_hex_id() for _ in range(100)]
        # 100개 중 최소 95개는 고유해야 함 (충돌 가능성은 낮음)
        assert len(set(ids)) >= 95

    def test_generate_rsid_uniqueness(self):
        """생성된 RSID가 충분히 고유한지 확인"""
        rsids = [_generate_rsid() for _ in range(100)]
        assert len(set(rsids)) >= 95


class TestDocxXMLEditor:
    """DocxXMLEditor 클래스 테스트"""

    @pytest.fixture
    def sample_xml_file(self):
        """테스트용 샘플 XML 파일"""
        content = '''<?xml version="1.0" encoding="utf-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml">
  <w:body>
    <w:p w14:paraId="12345678">
      <w:r w:rsidR="00A1B2C3">
        <w:t>Test text</w:t>
      </w:r>
    </w:p>
    <w:ins w:id="1" w:author="Author1" w:date="2024-01-01T00:00:00Z">
      <w:r>
        <w:t>Inserted text</w:t>
      </w:r>
    </w:ins>
  </w:body>
</w:document>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        yield temp_path
        Path(temp_path).unlink(missing_ok=True)

    def test_init(self, sample_xml_file):
        """정상 초기화"""
        editor = DocxXMLEditor(sample_xml_file, rsid="TESTRSID", author="TestAuthor", initials="TA")

        assert editor.rsid == "TESTRSID"
        assert editor.author == "TestAuthor"
        assert editor.initials == "TA"

    def test_get_next_change_id(self, sample_xml_file):
        """다음 변경 ID 가져오기"""
        editor = DocxXMLEditor(sample_xml_file, rsid="TESTRSID")

        next_id = editor._get_next_change_id()

        # 기존 w:ins w:id="1" 이 있으므로 다음은 2
        assert next_id == 2

    def test_get_next_change_id_no_existing(self):
        """기존 변경 사항이 없을 때"""
        content = '''<?xml version="1.0" encoding="utf-8"?>
<w:document xmlns:w="http://example.com"><w:body></w:body></w:document>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        try:
            editor = DocxXMLEditor(temp_path, rsid="TESTRSID")
            next_id = editor._get_next_change_id()

            assert next_id == 0
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_ensure_w16du_namespace(self, sample_xml_file):
        """w16du 네임스페이스 추가"""
        editor = DocxXMLEditor(sample_xml_file, rsid="TESTRSID")

        editor._ensure_w16du_namespace()

        root = editor.dom.documentElement
        assert root.hasAttribute("xmlns:w16du")
        assert "word16du" in root.getAttribute("xmlns:w16du")

    def test_ensure_w16cex_namespace(self, sample_xml_file):
        """w16cex 네임스페이스 추가"""
        editor = DocxXMLEditor(sample_xml_file, rsid="TESTRSID")

        editor._ensure_w16cex_namespace()

        root = editor.dom.documentElement
        assert root.hasAttribute("xmlns:w16cex")
        assert "cex" in root.getAttribute("xmlns:w16cex")

    def test_ensure_w14_namespace(self, sample_xml_file):
        """w14 네임스페이스 추가"""
        editor = DocxXMLEditor(sample_xml_file, rsid="TESTRSID")

        editor._ensure_w14_namespace()

        root = editor.dom.documentElement
        assert root.hasAttribute("xmlns:w14")
        assert "2010/wordml" in root.getAttribute("xmlns:w14")

    def test_inject_attributes_to_paragraph(self, sample_xml_file):
        """w:p 요소에 속성 주입"""
        editor = DocxXMLEditor(sample_xml_file, rsid="TESTRSID")

        # 새로운 w:p 생성
        p_elem = editor.dom.createElement("w:p")

        editor._inject_attributes_to_nodes([p_elem])

        # RSID 속성들이 추가되었는지 확인
        assert p_elem.hasAttribute("w:rsidR")
        assert p_elem.hasAttribute("w:rsidRDefault")
        assert p_elem.hasAttribute("w:rsidP")
        assert p_elem.getAttribute("w:rsidR") == "TESTRSID"

    def test_inject_attributes_to_run(self, sample_xml_file):
        """w:r 요소에 속성 주입"""
        editor = DocxXMLEditor(sample_xml_file, rsid="TESTRSID")

        # 새로운 w:r 생성
        r_elem = editor.dom.createElement("w:r")

        editor._inject_attributes_to_nodes([r_elem])

        # w:rsidR이 추가되었는지 확인
        assert r_elem.hasAttribute("w:rsidR")
        assert r_elem.getAttribute("w:rsidR") == "TESTRSID"

    def test_inject_attributes_to_tracked_change(self, sample_xml_file):
        """w:ins/w:del 요소에 속성 주입"""
        editor = DocxXMLEditor(sample_xml_file, rsid="TESTRSID", author="TestAuthor")

        # 새로운 w:ins 생성
        ins_elem = editor.dom.createElement("w:ins")

        editor._inject_attributes_to_nodes([ins_elem])

        # 변경 추적 속성들이 추가되었는지 확인
        assert ins_elem.hasAttribute("w:id")
        assert ins_elem.hasAttribute("w:author")
        assert ins_elem.hasAttribute("w:date")
        assert ins_elem.getAttribute("w:author") == "TestAuthor"

    def test_replace_node_with_injection(self, sample_xml_file):
        """노드 교체 시 속성 자동 주입"""
        editor = DocxXMLEditor(sample_xml_file, rsid="TESTRSID")

        # 기존 w:p 찾기
        p_elem = editor.dom.getElementsByTagName("w:p")[0]

        # 새로운 w:p로 교체
        new_nodes = editor.replace_node(p_elem, '<w:p><w:r><w:t>New text</w:t></w:r></w:p>')

        # 주입된 속성 확인
        new_p = new_nodes[0]
        assert new_p.hasAttribute("w:rsidR")

    def test_revert_insertion(self, sample_xml_file):
        """삽입 거부 (insertion을 deletion으로 변환)"""
        editor = DocxXMLEditor(sample_xml_file, rsid="TESTRSID")

        # w:ins 요소 찾기
        ins_elem = editor.get_node(tag="w:ins", attrs={"w:id": "1"})

        # 삽입 거부
        result = editor.revert_insertion(ins_elem)

        # w:del 요소가 생성되었는지 확인
        assert ins_elem.getElementsByTagName("w:del")

    def test_revert_insertion_no_ins_error(self, sample_xml_file):
        """에러 케이스: w:ins가 없는 요소에 revert_insertion 호출"""
        editor = DocxXMLEditor(sample_xml_file, rsid="TESTRSID")

        # w:body 요소는 w:ins를 포함하지 않음
        body = editor.dom.getElementsByTagName("w:body")[0]

        # w:ins를 제거하여 에러 조건 생성
        for ins in list(body.getElementsByTagName("w:ins")):
            ins.parentNode.removeChild(ins)

        with pytest.raises(ValueError, match="contains no insertions"):
            editor.revert_insertion(body)

    def test_revert_deletion(self):
        """삭제 거부 (deletion을 insertion으로 변환)"""
        # w:del이 포함된 XML 생성
        content = '''<?xml version="1.0" encoding="utf-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:del w:id="1">
      <w:r w:rsidDel="00A1B2C3">
        <w:delText>Deleted text</w:delText>
      </w:r>
    </w:del>
  </w:body>
</w:document>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        try:
            editor = DocxXMLEditor(temp_path, rsid="TESTRSID")

            # w:del 요소 찾기
            del_elem = editor.get_node(tag="w:del", attrs={"w:id": "1"})

            # 삭제 거부
            result = editor.revert_deletion(del_elem)

            # w:ins 요소가 생성되었는지 확인 (w:del 다음에)
            assert len(result) == 2  # [del_elem, created_insertion]
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_revert_deletion_no_del_error(self, sample_xml_file):
        """에러 케이스: w:del이 없는 요소에 revert_deletion 호출"""
        editor = DocxXMLEditor(sample_xml_file, rsid="TESTRSID")

        # w:p 요소는 w:del을 포함하지 않음
        p_elem = editor.dom.getElementsByTagName("w:p")[0]

        with pytest.raises(ValueError, match="contains no deletions"):
            editor.revert_deletion(p_elem)

    def test_suggest_paragraph(self):
        """단락을 tracked change로 변환"""
        xml_content = '<w:p xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:r><w:t>Test</w:t></w:r></w:p>'

        result = DocxXMLEditor.suggest_paragraph(xml_content)

        # w:ins 래퍼가 생성되었는지 확인
        assert '<w:ins>' in result
        assert '<w:pPr>' in result
        assert '<w:rPr>' in result

    def test_suggest_deletion_for_run(self):
        """w:r 요소를 삭제로 표시"""
        content = '''<?xml version="1.0" encoding="utf-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:r w:rsidR="00A1B2C3">
        <w:t>Text to delete</w:t>
      </w:r>
    </w:p>
  </w:body>
</w:document>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        try:
            editor = DocxXMLEditor(temp_path, rsid="TESTRSID")

            # w:r 요소 찾기
            r_elem = editor.dom.getElementsByTagName("w:r")[0]

            # 삭제 제안
            result = editor.suggest_deletion(r_elem)

            # w:del 래퍼가 생성되었는지 확인
            assert result.tagName == "w:del"
            # w:delText로 변환되었는지 확인
            assert result.getElementsByTagName("w:delText")
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_suggest_deletion_for_paragraph(self):
        """w:p 요소를 삭제로 표시"""
        content = '''<?xml version="1.0" encoding="utf-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:r w:rsidR="00A1B2C3">
        <w:t>Paragraph to delete</w:t>
      </w:r>
    </w:p>
  </w:body>
</w:document>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        try:
            editor = DocxXMLEditor(temp_path, rsid="TESTRSID")

            # w:p 요소 찾기
            p_elem = editor.dom.getElementsByTagName("w:p")[0]

            # 삭제 제안
            result = editor.suggest_deletion(p_elem)

            # w:del 래퍼가 생성되었는지 확인
            assert result.getElementsByTagName("w:del")
            # w:delText로 변환되었는지 확인
            assert result.getElementsByTagName("w:delText")
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_suggest_deletion_error_existing_deltext(self):
        """에러 케이스: 이미 w:delText가 있는 w:r"""
        content = '''<?xml version="1.0" encoding="utf-8"?>
<w:document xmlns:w="http://example.com">
  <w:body>
    <w:p>
      <w:r>
        <w:delText>Already deleted</w:delText>
      </w:r>
    </w:p>
  </w:body>
</w:document>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        try:
            editor = DocxXMLEditor(temp_path, rsid="TESTRSID")

            r_elem = editor.dom.getElementsByTagName("w:r")[0]

            with pytest.raises(ValueError, match="already contains w:delText"):
                editor.suggest_deletion(r_elem)
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestDocument:
    """Document 클래스 테스트"""

    @pytest.fixture
    def mock_unpacked_dir(self):
        """mock 언팩 디렉토리 생성"""
        temp_dir = tempfile.mkdtemp()
        word_dir = Path(temp_dir) / "word"
        word_dir.mkdir()
        rels_dir = word_dir / "_rels"
        rels_dir.mkdir()

        # 필수 XML 파일들 생성
        (word_dir / "document.xml").write_text('''<?xml version="1.0" encoding="utf-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>Test</w:t></w:r></w:p></w:body>
</w:document>''')

        (word_dir / "settings.xml").write_text('''<?xml version="1.0" encoding="utf-8"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
</w:settings>''')

        (rels_dir / "document.xml.rels").write_text('''<?xml version="1.0" encoding="utf-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>''')

        (Path(temp_dir) / "[Content_Types].xml").write_text('''<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
</Types>''')

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_document_init(self, mock_unpacked_dir):
        """Document 초기화 테스트"""
        doc = Document(mock_unpacked_dir, author="TestAuthor", initials="TA")

        assert doc.author == "TestAuthor"
        assert doc.initials == "TA"
        assert doc.rsid is not None
        assert len(doc.rsid) == 8
        assert doc.next_comment_id == 0

    def test_document_init_with_rsid(self, mock_unpacked_dir):
        """사용자 지정 RSID로 초기화"""
        doc = Document(mock_unpacked_dir, rsid="CUSTOM12")

        assert doc.rsid == "CUSTOM12"

    def test_document_init_invalid_directory(self):
        """에러 케이스: 유효하지 않은 디렉토리"""
        with pytest.raises(ValueError, match="Directory not found"):
            Document("/nonexistent/directory")

    def test_getitem_editor(self, mock_unpacked_dir):
        """[] 연산자로 에디터 가져오기"""
        doc = Document(mock_unpacked_dir)

        editor = doc["word/document.xml"]

        assert isinstance(editor, DocxXMLEditor)
        assert editor.rsid == doc.rsid

    def test_getitem_nonexistent_file(self, mock_unpacked_dir):
        """에러 케이스: 존재하지 않는 XML 파일"""
        doc = Document(mock_unpacked_dir)

        with pytest.raises(ValueError, match="XML file not found"):
            doc["word/nonexistent.xml"]

    def test_add_comment(self, mock_unpacked_dir):
        """주석 추가 테스트"""
        doc = Document(mock_unpacked_dir)

        # 시작/종료 노드 찾기
        start_node = doc._document.dom.getElementsByTagName("w:p")[0]
        end_node = start_node

        comment_id = doc.add_comment(start=start_node, end=end_node, text="Test comment")

        assert comment_id == 0
        assert doc.next_comment_id == 1

    def test_reply_to_comment(self, mock_unpacked_dir):
        """주석에 답글 추가"""
        doc = Document(mock_unpacked_dir)

        # 먼저 주석 추가
        start_node = doc._document.dom.getElementsByTagName("w:p")[0]
        parent_id = doc.add_comment(start=start_node, end=start_node, text="Parent comment")

        # 답글 추가
        reply_id = doc.reply_to_comment(parent_comment_id=parent_id, text="Reply comment")

        assert reply_id == 1
        assert doc.next_comment_id == 2

    def test_reply_to_nonexistent_comment(self, mock_unpacked_dir):
        """에러 케이스: 존재하지 않는 주석에 답글"""
        doc = Document(mock_unpacked_dir)

        with pytest.raises(ValueError, match="Parent comment.*not found"):
            doc.reply_to_comment(parent_comment_id=999, text="Reply")

    def test_validate_success(self, mock_unpacked_dir):
        """유효성 검사 성공"""
        # Mock validators to return True
        mock_ooxml.scripts.validation.docx.DOCXSchemaValidator.return_value.validate.return_value = True
        mock_ooxml.scripts.validation.redlining.RedliningValidator.return_value.validate.return_value = True

        doc = Document(mock_unpacked_dir)
        doc.validate()  # 에러가 발생하지 않아야 함

    def test_validate_schema_failure(self, mock_unpacked_dir):
        """유효성 검사 실패: 스키마 오류"""
        # Mock schema validator to return False
        mock_ooxml.scripts.validation.docx.DOCXSchemaValidator.return_value.validate.return_value = False

        doc = Document(mock_unpacked_dir)

        with pytest.raises(ValueError, match="Schema validation failed"):
            doc.validate()

    def test_save(self, mock_unpacked_dir):
        """문서 저장"""
        # Mock validators to return True
        mock_ooxml.scripts.validation.docx.DOCXSchemaValidator.return_value.validate.return_value = True
        mock_ooxml.scripts.validation.redlining.RedliningValidator.return_value.validate.return_value = True

        doc = Document(mock_unpacked_dir)

        # 임시 대상 디렉토리 생성
        dest_dir = tempfile.mkdtemp()

        try:
            doc.save(destination=dest_dir, validate=True)

            # 파일이 복사되었는지 확인
            assert (Path(dest_dir) / "word" / "document.xml").exists()
        finally:
            shutil.rmtree(dest_dir, ignore_errors=True)

    def test_cleanup_on_deletion(self, mock_unpacked_dir):
        """Document 삭제 시 임시 디렉토리 정리"""
        doc = Document(mock_unpacked_dir)
        temp_dir = doc.temp_dir

        # temp_dir이 존재하는지 확인
        assert Path(temp_dir).exists()

        # Document 삭제
        del doc

        # temp_dir이 삭제되었는지 확인
        assert not Path(temp_dir).exists()
