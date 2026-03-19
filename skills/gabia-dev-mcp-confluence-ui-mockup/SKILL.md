---
name: gabia-dev-mcp-confluence-ui-mockup
description: Confluence storage format HTML 기반 화면 UI 목업 컴포넌트 라이브러리. PDF 기획서/와이어프레임을 Confluence 정책서에 HTML로 재현할 때 사용한다. 사용자가 "화면 넣어줘", "UI 목업 추가", "화면 섹션 추가" 등 요청 시 사용.
---

# Confluence 화면 UI 목업 컴포넌트 라이브러리

Confluence 정책서에 화면 UI를 HTML(storage format)로 삽입할 때 사용하는 빌딩블록 모음입니다.
PDF 기획서나 와이어프레임을 Confluence 페이지에 HTML로 재현할 때 아래 컴포넌트를 조합합니다.

> **참고**: Confluence 페이지 생성/수정/업로드는 `gabia-dev-mcp-confluence` 스킬을 사용하세요.

## 사용 시점

- 사용자가 "화면 넣어줘", "UI 목업 추가", "화면 섹션 추가" 등 요청 시
- PDF 기획서를 Confluence 정책서로 변환할 때
- 정책서에 시각적 화면 레이아웃이 필요할 때

## 기본 원칙

1. **모든 화면은 `panel` 매크로로 감싼다** — 본문과 시각적으로 구분
2. **inline style만 사용** — Confluence는 외부 CSS/class를 지원하지 않음
3. **`status` 매크로로 상태 뱃지 표현** — Green(활성화), Grey(비활성화), Blue(버튼), Yellow(대기), Red(삭제/경고)
4. **`section`+`column` 매크로로 비교 레이아웃** — 검색결과 있음/없음 등 병렬 표시
5. **중첩 `panel`로 모달 표현** — 바깥 panel(딤 배경) > 안쪽 panel(모달 본체)

## 컴포넌트 목록

### 1. 탭 네비게이션

```xml
<p style="margin-top: 8px;">
<span style="margin-right: 16px; color: #666;">탭1</span>
<span style="border-bottom: 2px solid #2563eb; padding-bottom: 4px; margin-right: 16px; color: #2563eb; font-weight: bold;">현재탭</span>
<span style="margin-right: 16px; color: #666;">탭3</span>
</p>
```

### 2. 상태 뱃지

```xml
<!-- 활성화 -->
<ac:structured-macro ac:name="status"><ac:parameter ac:name="title">활성화</ac:parameter><ac:parameter ac:name="colour">Green</ac:parameter></ac:structured-macro>

<!-- 비활성화 -->
<ac:structured-macro ac:name="status"><ac:parameter ac:name="title">비활성화</ac:parameter><ac:parameter ac:name="colour">Grey</ac:parameter></ac:structured-macro>

<!-- 버튼 스타일 -->
<ac:structured-macro ac:name="status"><ac:parameter ac:name="title">공고 수정</ac:parameter><ac:parameter ac:name="colour">Blue</ac:parameter></ac:structured-macro>
```

### 3. 카드형 목록 아이템 (드래그 핸들 포함)

```xml
<table style="width: 100%; border-collapse: collapse;">
<tbody>
<tr><td style="border: 1px solid #e5e7eb; border-left: 3px solid #e5e7eb; padding: 12px; background: #fafafa;">
<p>
<span style="cursor: grab; color: #999;">&#8942;&#8942;</span>&nbsp;&nbsp;
<strong>항목명</strong>&nbsp;&nbsp;
<ac:structured-macro ac:name="status"><ac:parameter ac:name="title">활성화</ac:parameter><ac:parameter ac:name="colour">Green</ac:parameter></ac:structured-macro>
<span style="float: right; font-size: 18px; color: #666;">&#8943;</span>
</p>
</td></tr>
</tbody>
</table>
```

### 4. 태그/칩 (제거 가능)

```xml
<span style="background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 12px; padding: 2px 10px; font-size: 12px;">홍길동 &#10005;</span>
```

### 5. 추가(+) 버튼

```xml
<span style="border: 1px solid #d1d5db; border-radius: 4px; padding: 2px 6px; font-size: 14px; color: #999;">&#43;</span>
```

### 6. 검색 필드

```xml
<span style="background: #fff; border: 1px solid #d1d5db; border-radius: 4px; padding: 2px 8px; font-size: 12px; color: #999;">검색 &#128269;</span>
```

### 7. 액션 버튼 (Primary)

```xml
<span style="background: #2563eb; color: white; padding: 4px 12px; border-radius: 4px; font-size: 13px;">버튼명</span>
```

### 8. 액션 버튼 (Secondary/Outline)

```xml
<span style="border: 1px solid #d1d5db; padding: 6px 24px; border-radius: 4px; font-size: 13px; color: #333;">닫기</span>
```

### 9. 텍스트 링크 버튼

```xml
<span style="color: #2563eb; cursor: pointer;">&#8635; 초기화</span>
```

### 10. 체크박스 (미선택/선택)

```xml
<!-- 미선택 -->
<span style="border: 1px solid #d1d5db; display: inline-block; width: 16px; height: 16px; text-align: center; font-size: 11px; border-radius: 2px; vertical-align: middle;">&#9744;</span>

<!-- 선택 -->
<span style="background: #2563eb; color: white; display: inline-block; width: 16px; height: 16px; text-align: center; font-size: 11px; border-radius: 2px; vertical-align: middle;">&#10003;</span>
```

### 11. 드롭다운/레이어 메뉴

```xml
<table style="width: 200px; border-collapse: collapse; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
<tbody>
<tr><td style="border: 1px solid #e5e7eb; padding: 10px 16px; cursor: pointer; font-size: 13px;">메뉴1</td></tr>
<tr><td style="border: 1px solid #e5e7eb; padding: 10px 16px; cursor: pointer; font-size: 13px;">메뉴2</td></tr>
<tr><td style="border: 1px solid #e5e7eb; padding: 10px 16px; cursor: pointer; font-size: 13px; color: #ef4444;">삭제</td></tr>
</tbody>
</table>
```

### 12. 모달 래퍼

```xml
<!-- 바깥: 딤 배경 -->
<ac:structured-macro ac:name="panel" ac:schema-version="1">
<ac:parameter ac:name="borderColor">#ddd</ac:parameter>
<ac:parameter ac:name="bgColor">#f9fafb</ac:parameter>
<ac:rich-text-body>

<!-- 안쪽: 모달 본체 -->
<ac:structured-macro ac:name="panel" ac:schema-version="1">
<ac:parameter ac:name="borderColor">#d1d5db</ac:parameter>
<ac:parameter ac:name="bgColor">#ffffff</ac:parameter>
<ac:rich-text-body>
<p><strong style="font-size: 16px;">모달 제목</strong></p>
<p style="color: #666; font-size: 13px;">설명 텍스트</p>
<!-- 모달 콘텐츠 -->
</ac:rich-text-body>
</ac:structured-macro>

</ac:rich-text-body>
</ac:structured-macro>
```

### 13. 검색 드롭다운 (결과 있음/없음)

```xml
<!-- section+column으로 병렬 배치 -->
<ac:structured-macro ac:name="section" ac:schema-version="1">
<ac:rich-text-body>
<ac:structured-macro ac:name="column" ac:schema-version="1">
<ac:parameter ac:name="width">50%</ac:parameter>
<ac:rich-text-body>
<p><strong>검색 결과 있음</strong></p>
<ac:structured-macro ac:name="panel" ac:schema-version="1">
<ac:parameter ac:name="borderColor">#d1d5db</ac:parameter>
<ac:parameter ac:name="bgColor">#ffffff</ac:parameter>
<ac:rich-text-body>
<table style="width: 100%; border-collapse: collapse;">
<tbody>
<tr><td style="border-bottom: 1px solid #e5e7eb; padding: 6px;">
<span style="border: 1px solid #2563eb; border-radius: 4px; padding: 4px 8px; font-size: 13px;">입력텍스트|</span>
</td></tr>
<tr><td style="border-bottom: 1px solid #f3f4f6; padding: 8px;">
<strong style="font-size: 13px;">이름</strong> <span style="color: #999; font-size: 12px;">소속 직위</span>
</td></tr>
</tbody>
</table>
</ac:rich-text-body>
</ac:structured-macro>
</ac:rich-text-body>
</ac:structured-macro>

<ac:structured-macro ac:name="column" ac:schema-version="1">
<ac:parameter ac:name="width">50%</ac:parameter>
<ac:rich-text-body>
<p><strong>검색 결과 없음</strong></p>
<ac:structured-macro ac:name="panel" ac:schema-version="1">
<ac:parameter ac:name="borderColor">#d1d5db</ac:parameter>
<ac:parameter ac:name="bgColor">#ffffff</ac:parameter>
<ac:rich-text-body>
<table style="width: 100%; border-collapse: collapse;">
<tbody>
<tr><td style="border-bottom: 1px solid #e5e7eb; padding: 6px;">
<span style="border: 1px solid #2563eb; border-radius: 4px; padding: 4px 8px; font-size: 13px;">입력텍스트|</span>
</td></tr>
<tr><td style="padding: 16px; text-align: center; color: #999; font-size: 13px;">
검색 결과가 없습니다.
</td></tr>
</tbody>
</table>
</ac:rich-text-body>
</ac:structured-macro>
</ac:rich-text-body>
</ac:structured-macro>
</ac:rich-text-body>
</ac:structured-macro>
```

### 14. 빈 상태 (Empty State)

```xml
<ac:structured-macro ac:name="panel" ac:schema-version="1">
<ac:parameter ac:name="borderColor">#d1d5db</ac:parameter>
<ac:parameter ac:name="bgColor">#f9fafb</ac:parameter>
<ac:rich-text-body>
<p style="text-align: center; padding: 24px 0;">
<strong style="font-size: 14px;">표시할 항목 없음</strong><br /><br />
<span style="color: #999; font-size: 13px;">안내 메시지</span>
</p>
</ac:rich-text-body>
</ac:structured-macro>
```

### 15. 평가자/사용자 태그 행 (라벨 + 태그 목록 + 추가 버튼)

```xml
<p style="color: #666; font-size: 13px;">
평가자&nbsp;&nbsp;
<span style="background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 12px; padding: 2px 10px; font-size: 12px;">이름1 &#10005;</span>&nbsp;
<span style="background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 12px; padding: 2px 10px; font-size: 12px;">이름2 &#10005;</span>&nbsp;
<span style="border: 1px solid #d1d5db; border-radius: 4px; padding: 2px 6px; font-size: 14px; color: #999;">&#43;</span>
</p>
```

## 조합 예시: 카드 목록 화면

아래는 컴포넌트를 조합하여 완성된 화면을 만드는 예시입니다.

```xml
<ac:structured-macro ac:name="panel" ac:schema-version="1">
<ac:parameter ac:name="borderColor">#ddd</ac:parameter>
<ac:parameter ac:name="bgColor">#ffffff</ac:parameter>
<ac:rich-text-body>

<!-- 헤더: 제목 + 탭 -->
<table style="border: none; width: 100%;"><tbody>
<tr><td style="border: none; padding: 12px 16px;">
<p><strong style="font-size: 16px;">%{공고명}</strong></p>
<p style="margin-top: 8px;">
<!-- 탭 네비게이션 컴포넌트 -->
</p>
</td></tr>
</tbody></table>

<!-- 작업 버튼 행 -->
<table style="border: none; width: 100%;"><tbody>
<tr><td style="border: none; padding: 8px 16px;">
<p>
<!-- 텍스트 링크 버튼 -->
<span style="float: right;"><!-- Primary 버튼 --></span>
</p>
</td></tr></tbody></table>

<!-- 카드 목록 (카드형 아이템 반복) -->
<!-- 각 카드 안에 태그 행 배치 -->

<!-- 하단 버튼 -->
<p style="text-align: center; margin-top: 16px;">
<!-- Primary 버튼 -->
</p>

</ac:rich-text-body>
</ac:structured-macro>
```

## 주의사항

- Confluence storage format에서 `class` 속성은 무시됨 → 반드시 `style` 인라인으로 작성
- `border-radius`, `box-shadow` 등 CSS3 속성은 Confluence에서 대부분 지원됨
- 화면 섹션은 정책서의 **정책 테이블 위에** 배치하는 것을 권장 (먼저 화면 보고 정책 읽는 흐름)
- 복잡한 화면은 `expand` 매크로로 접어둘 수 있음
- HTML 엔티티 참고: `&#8942;&#8942;`(드래그핸들), `&#8943;`(더보기), `&#10005;`(X), `&#43;`(+), `&#128269;`(돋보기), `&#8635;`(새로고침), `&#9744;`(빈체크), `&#10003;`(체크)
