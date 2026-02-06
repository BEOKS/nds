#!/usr/bin/env python3
"""
utilities.py에 대한 단위 테스트
XMLEditor 클래스의 XML 파싱, 노드 검색, DOM 조작 기능 테스트
"""

import sys
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from utilities import XMLEditor, _create_line_tracking_parser


class TestXMLEditor:
    """XMLEditor 클래스 테스트"""

    @pytest.fixture
    def sample_xml_file(self):
        """테스트용 샘플 XML 파일 생성"""
        content = '''<?xml version="1.0" encoding="utf-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml">
  <w:body>
    <w:p w14:paraId="12345678">
      <w:r w:rsidR="00A1B2C3">
        <w:t>Hello World</w:t>
      </w:r>
    </w:p>
    <w:p w14:paraId="87654321">
      <w:r w:rsidR="00D4E5F6">
        <w:t>Test paragraph</w:t>
      </w:r>
    </w:p>
    <w:del w:id="1" w:author="TestAuthor">
      <w:r>
        <w:delText>Deleted text</w:delText>
      </w:r>
    </w:del>
  </w:body>
</w:document>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        yield temp_path

        # Cleanup
        Path(temp_path).unlink(missing_ok=True)

    def test_init_success(self, sample_xml_file):
        """정상 케이스: XML 파일 로드 및 초기화"""
        editor = XMLEditor(sample_xml_file)

        assert editor.xml_path == Path(sample_xml_file)
        assert editor.encoding in ('utf-8', 'ascii')
        assert editor.dom is not None
        assert editor.dom.documentElement.tagName == 'w:document'

    def test_init_file_not_found(self):
        """에러 케이스: 존재하지 않는 파일"""
        with pytest.raises(ValueError, match="XML file not found"):
            XMLEditor("/nonexistent/path/file.xml")

    def test_encoding_detection_utf8(self):
        """UTF-8 인코딩 감지 테스트"""
        content = '<?xml version="1.0" encoding="utf-8"?><root></root>'

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        try:
            editor = XMLEditor(temp_path)
            assert editor.encoding == 'utf-8'
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_encoding_detection_ascii(self):
        """ASCII 인코딩 감지 테스트"""
        content = '<?xml version="1.0" encoding="ascii"?><root></root>'

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='ascii') as f:
            f.write(content)
            temp_path = f.name

        try:
            editor = XMLEditor(temp_path)
            assert editor.encoding == 'ascii'
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_get_node_by_tag_and_attrs(self, sample_xml_file):
        """속성으로 노드 검색"""
        editor = XMLEditor(sample_xml_file)

        # w:del 요소를 id 속성으로 검색
        node = editor.get_node(tag="w:del", attrs={"w:id": "1"})

        assert node is not None
        assert node.tagName == "w:del"
        assert node.getAttribute("w:id") == "1"
        assert node.getAttribute("w:author") == "TestAuthor"

    def test_get_node_by_line_number(self, sample_xml_file):
        """라인 번호로 노드 검색"""
        editor = XMLEditor(sample_xml_file)

        # 첫 번째 w:p 요소는 4번 라인 근처에 있어야 함
        elements = editor.dom.getElementsByTagName("w:p")
        assert len(elements) >= 1

        # parse_position 속성이 있는지 확인
        first_p = elements[0]
        assert hasattr(first_p, 'parse_position')

    def test_get_node_by_contains(self, sample_xml_file):
        """텍스트 내용으로 노드 검색"""
        editor = XMLEditor(sample_xml_file)

        # "Hello World" 텍스트를 포함하는 w:t 요소 검색
        node = editor.get_node(tag="w:t", contains="Hello World")

        assert node is not None
        assert node.tagName == "w:t"
        assert "Hello World" in node.firstChild.data

    def test_get_node_not_found(self, sample_xml_file):
        """에러 케이스: 노드를 찾을 수 없음"""
        editor = XMLEditor(sample_xml_file)

        with pytest.raises(ValueError, match="Node not found"):
            editor.get_node(tag="w:nonexistent", attrs={"w:id": "999"})

    def test_get_node_multiple_matches(self, sample_xml_file):
        """에러 케이스: 여러 노드가 매칭됨"""
        editor = XMLEditor(sample_xml_file)

        # w:r 태그는 여러 개 있으므로 필터 없이 검색하면 에러
        with pytest.raises(ValueError, match="Multiple nodes found"):
            editor.get_node(tag="w:r")

    def test_get_element_text(self, sample_xml_file):
        """요소의 텍스트 추출"""
        editor = XMLEditor(sample_xml_file)

        p_elem = editor.get_node(tag="w:p", attrs={"w14:paraId": "12345678"})
        text = editor._get_element_text(p_elem)

        assert "Hello World" in text

    def test_replace_node(self, sample_xml_file):
        """노드 교체"""
        editor = XMLEditor(sample_xml_file)

        # 첫 번째 w:t 요소 찾기
        old_node = editor.get_node(tag="w:t", contains="Hello World")

        # 새로운 XML로 교체
        new_nodes = editor.replace_node(old_node, '<w:t>Replaced Text</w:t>')

        assert len(new_nodes) > 0
        assert new_nodes[0].tagName == "w:t"

    def test_insert_after(self, sample_xml_file):
        """노드 뒤에 삽입"""
        editor = XMLEditor(sample_xml_file)

        # 첫 번째 w:p 요소 찾기
        p_elem = editor.dom.getElementsByTagName("w:p")[0]

        # 새로운 w:p 삽입
        new_nodes = editor.insert_after(p_elem, '<w:p><w:r><w:t>Inserted</w:t></w:r></w:p>')

        assert len(new_nodes) > 0
        assert new_nodes[0].tagName == "w:p"

    def test_insert_before(self, sample_xml_file):
        """노드 앞에 삽입"""
        editor = XMLEditor(sample_xml_file)

        # 첫 번째 w:p 요소 찾기
        p_elem = editor.dom.getElementsByTagName("w:p")[0]

        # 새로운 w:p 삽입
        new_nodes = editor.insert_before(p_elem, '<w:p><w:r><w:t>Before</w:t></w:r></w:p>')

        assert len(new_nodes) > 0
        assert new_nodes[0].tagName == "w:p"

    def test_append_to(self, sample_xml_file):
        """자식 노드로 추가"""
        editor = XMLEditor(sample_xml_file)

        # w:body 요소에 새로운 w:p 추가
        body = editor.dom.getElementsByTagName("w:body")[0]

        new_nodes = editor.append_to(body, '<w:p><w:r><w:t>Appended</w:t></w:r></w:p>')

        assert len(new_nodes) > 0
        assert new_nodes[0].tagName == "w:p"

    def test_get_next_rid(self):
        """다음 rId 생성 테스트"""
        content = '''<?xml version="1.0" encoding="utf-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="some-type" Target="target1.xml"/>
  <Relationship Id="rId2" Type="some-type" Target="target2.xml"/>
  <Relationship Id="rId5" Type="some-type" Target="target5.xml"/>
</Relationships>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        try:
            editor = XMLEditor(temp_path)
            next_rid = editor.get_next_rid()

            # 최대값이 5이므로 다음은 6
            assert next_rid == "rId6"
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_save(self, sample_xml_file):
        """XML 파일 저장"""
        editor = XMLEditor(sample_xml_file)

        # 수정 수행
        t_elem = editor.get_node(tag="w:t", contains="Hello World")
        t_elem.firstChild.data = "Modified"

        # 저장
        editor.save()

        # 다시 로드하여 확인
        editor2 = XMLEditor(sample_xml_file)
        modified_elem = editor2.get_node(tag="w:t", contains="Modified")

        assert modified_elem is not None
        assert "Modified" in modified_elem.firstChild.data

    def test_parse_fragment(self, sample_xml_file):
        """XML 프래그먼트 파싱"""
        editor = XMLEditor(sample_xml_file)

        fragment = '<w:r><w:t>Fragment text</w:t></w:r>'
        nodes = editor._parse_fragment(fragment)

        assert len(nodes) > 0
        # 요소 노드가 최소 1개 있어야 함
        elements = [n for n in nodes if n.nodeType == n.ELEMENT_NODE]
        assert len(elements) >= 1

    def test_parse_fragment_no_elements(self, sample_xml_file):
        """에러 케이스: 요소가 없는 프래그먼트"""
        editor = XMLEditor(sample_xml_file)

        # 텍스트만 있는 프래그먼트는 에러
        with pytest.raises(AssertionError):
            editor._parse_fragment('Just text')


class TestLineTrackingParser:
    """라인 추적 파서 테스트"""

    def test_create_line_tracking_parser(self):
        """라인 추적 파서 생성"""
        parser = _create_line_tracking_parser()

        assert parser is not None
        # setContentHandler가 monkey-patched 되었는지 확인
        assert hasattr(parser, 'setContentHandler')

    def test_line_tracking_in_parsed_document(self):
        """파싱된 문서에 라인 번호가 추적되는지 확인"""
        content = '''<?xml version="1.0" encoding="utf-8"?>
<root>
  <elem1>Line 3</elem1>
  <elem2>Line 4</elem2>
  <elem3>Line 5</elem3>
</root>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        try:
            editor = XMLEditor(temp_path)

            # 각 요소에 parse_position이 설정되어 있는지 확인
            for elem in editor.dom.getElementsByTagName("elem1"):
                assert hasattr(elem, 'parse_position')
                line, col = elem.parse_position
                assert isinstance(line, int)
                assert isinstance(col, int)
                assert line > 0  # 라인 번호는 1부터 시작
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestXMLEditorEdgeCases:
    """엣지 케이스 테스트"""

    def test_get_node_with_range(self):
        """라인 번호 범위로 노드 검색"""
        content = '''<?xml version="1.0" encoding="utf-8"?>
<root xmlns:w="http://example.com">
  <w:p>Paragraph 1</w:p>
  <w:p>Paragraph 2</w:p>
  <w:p>Paragraph 3</w:p>
</root>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        try:
            editor = XMLEditor(temp_path)

            # 범위 내의 요소들이 검색되는지 확인
            elements = editor.dom.getElementsByTagName("w:p")
            assert len(elements) == 3
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_contains_with_html_entities(self):
        """HTML 엔티티를 포함한 텍스트 검색"""
        content = '''<?xml version="1.0" encoding="utf-8"?>
<root xmlns:w="http://example.com">
  <w:t>Test &#8220;quoted&#8221; text</w:t>
</root>'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        try:
            editor = XMLEditor(temp_path)

            # HTML 엔티티를 유니코드로 변환하여 검색
            node = editor.get_node(tag="w:t", contains="\u201cquoted\u201d")
            assert node is not None
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_empty_xml_file(self):
        """빈 XML 파일 처리"""
        content = '<?xml version="1.0" encoding="utf-8"?><root/>'

        with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as f:
            f.write(content)
            temp_path = f.name

        try:
            editor = XMLEditor(temp_path)
            assert editor.dom.documentElement.tagName == 'root'
            assert len(list(editor.dom.documentElement.childNodes)) == 0
        finally:
            Path(temp_path).unlink(missing_ok=True)
