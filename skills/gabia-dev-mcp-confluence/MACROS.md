---
name: confluence-macros-reference
description: Confluence storage format에서 사용 가능한 매크로 카탈로그. 다이어그램, 코드, 패널, 레이아웃, 상태 등 매크로별 용도와 storage format 예시.
---

# Confluence 매크로 레퍼런스

`--format storage`로 직접 storage XML을 작성할 때 사용할 수 있는 매크로 목록입니다.
`--format markdown`으로 업로드 시 ` ```mermaid ` 블록은 Mermaid 매크로로, ` ```plantuml ` 블록은 PlantUML 매크로로, 그 외 ` ```lang ` 블록은 코드 매크로로 자동 변환됩니다.

## 다이어그램/시각화

| 매크로 | 용도 | storage format 예시 |
|--------|------|---------------------|
| `mermaid-macro` | Mermaid 다이어그램 (flowchart, sequence, state, pie 등) - **권장** | `<ac:structured-macro ac:name="mermaid-macro" ac:schema-version="1"><ac:plain-text-body><![CDATA[flowchart TD ...]]></ac:plain-text-body></ac:structured-macro>` |
| `plantuml` | PlantUML 다이어그램 (시퀀스, 상태, 컴포넌트 등) | `<ac:structured-macro ac:name="plantuml" ac:schema-version="1"><ac:parameter ac:name="atlassian-macro-output-type">INLINE</ac:parameter><ac:plain-text-body><![CDATA[@startuml ... @enduml]]></ac:plain-text-body></ac:structured-macro>` |
| `chart` | 내장 차트 (pie, bar, line 등). **한국어 라벨 깨짐(□□) → mermaid pie 사용 권장** | `<ac:structured-macro ac:name="chart"><ac:parameter ac:name="type">pie</ac:parameter><ac:rich-text-body><table>...</table></ac:rich-text-body></ac:structured-macro>` |

## 코드/서식

| 매크로 | 용도 | storage format 예시 |
|--------|------|---------------------|
| `code` | 코드 블록 (구문 강조) | `<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">typescript</ac:parameter><ac:plain-text-body><![CDATA[코드]]></ac:plain-text-body></ac:structured-macro>` |
| `noformat` | 서식 없는 텍스트 | `<ac:structured-macro ac:name="noformat"><ac:plain-text-body><![CDATA[텍스트]]></ac:plain-text-body></ac:structured-macro>` |
| `markdown` | Markdown 렌더링. **mermaid flowchart 렌더링 충돌 → 사용 비권장** | `<ac:structured-macro ac:name="markdown"><ac:plain-text-body><![CDATA[# 제목 ...]]></ac:plain-text-body></ac:structured-macro>` |

## 정보 패널

| 매크로 | 용도 | 색상 |
|--------|------|------|
| `info` | 정보 안내 | 파랑 |
| `note` | 참고 사항 | 노랑 |
| `warning` | 경고 | 빨강 |
| `tip` | 팁/힌트 | 초록 |
| `panel` | 커스텀 패널 (borderColor, bgColor 등 설정 가능) | 설정 가능 |
| `expand` | 접기/펼치기 | - |

```xml
<!-- 예시: info 패널 -->
<ac:structured-macro ac:name="info">
  <ac:parameter ac:name="title">참고</ac:parameter>
  <ac:rich-text-body><p>내용</p></ac:rich-text-body>
</ac:structured-macro>

<!-- 예시: expand -->
<ac:structured-macro ac:name="expand">
  <ac:parameter ac:name="title">자세히 보기</ac:parameter>
  <ac:rich-text-body><p>숨겨진 내용</p></ac:rich-text-body>
</ac:structured-macro>
```

## 상태/라벨

| 매크로 | 용도 | 사용 가능 색상 |
|--------|------|---------------|
| `status` | 인라인 상태 라벨 | Green, Yellow, Red, Blue, Grey |

```xml
<ac:structured-macro ac:name="status">
  <ac:parameter ac:name="title">완료</ac:parameter>
  <ac:parameter ac:name="colour">Green</ac:parameter>
</ac:structured-macro>
```

## 레이아웃/구조

| 매크로 | 용도 |
|--------|------|
| `section` + `column` | 멀티 컬럼 레이아웃 |
| `toc` | 목차 자동 생성 |
| `div` | CSS 스타일 커스텀 블록 |
| `children` | 하위 페이지 목록 |
| `pagetree` | 페이지 트리 |
| `excerpt` / `excerpt-include` | 발췌 정의/포함 |

## 동적 콘텐츠

| 매크로 | 용도 |
|--------|------|
| `recently-updated` | 최근 업데이트 목록 |
| `change-history` | 변경 이력 |
| `contributors` | 기여자 목록 |
| `contributors-summary` | 기여자 요약 |
| `loremipsum` | 더미 텍스트 생성 |
| `attachments` | 첨부파일 목록 표시 |

## 수학/LaTeX

| 매크로 | 용도 | storage format 예시 |
|--------|------|---------------------|
| `latex-inline` | 인라인 수식 | `<ac:structured-macro ac:name="latex-inline"><ac:plain-text-body><![CDATA[E = mc^2]]></ac:plain-text-body></ac:structured-macro>` |
| `latex-block` | 블록 수식 | `<ac:structured-macro ac:name="latex-block"><ac:plain-text-body><![CDATA[\sum_{i=1}^{n} x_i]]></ac:plain-text-body></ac:structured-macro>` |

## 기타

| 요소 | 용도 |
|------|------|
| `ac:task-list` / `ac:task` | 체크리스트 (태스크 목록) |

```xml
<ac:task-list>
  <ac:task><ac:task-id>1</ac:task-id><ac:task-status>complete</ac:task-status><ac:task-body>완료 항목</ac:task-body></ac:task>
  <ac:task><ac:task-id>2</ac:task-id><ac:task-status>incomplete</ac:task-status><ac:task-body>미완료 항목</ac:task-body></ac:task>
</ac:task-list>
```

## Mermaid vs PlantUML 선택 기준

| 기준 | Mermaid (`mermaid-macro`) | PlantUML (`plantuml`) |
|------|--------------------------|----------------------|
| **권장** | O (기본 선택) | 복잡한 UML 필요 시 |
| Markdown 호환 | ` ```mermaid ` 그대로 사용 | ` ```plantuml ` + @startuml/@enduml 필요 |
| 문법 난이도 | 쉬움 | 보통 |
| 한국어 | 지원 | 지원 |
| 다이어그램 종류 | flowchart, sequence, state, class, ER, gantt, pie, journey (9.2.2 기준) | 시퀀스, 상태, 컴포넌트, 클래스, 배포, gitGraph 대체 |

## PlantUML 작성 시 주의사항

- participant/state 이름에 **하이픈(`-`)이나 특수문자**가 있으면 반드시 따옴표로 감싸기: `participant "ingress-auth" as ingressAuth`
- `@startuml` / `@enduml`로 반드시 감싸야 함
- 한국어 텍스트 사용 가능

## 검증된 매크로 목록 (PoC 테스트 완료)

**다이어그램/시각화:** `mermaid-macro` (flowchart, sequence, state, pie), `plantuml`, `chart` (한국어 깨짐 → mermaid 대체 권장)

**코드/서식:** `code`, `noformat`, `markdown` (mermaid flowchart 충돌 주의)

**정보 패널:** `info`, `note`, `warning`, `tip`, `panel`, `expand`

**상태/라벨:** `status` (Green, Yellow, Red, Blue, Grey)

**레이아웃:** `section`+`column`, `toc`, `div`

**네비게이션:** `children`, `pagetree`

**동적 콘텐츠:** `recently-updated`, `change-history`, `contributors`, `contributors-summary`

**수학:** `latex-inline`, `latex-block`

**기타:** `loremipsum`, `excerpt`, `attachments`, `tasklist` (ac:task-list)

## API 업로드 불가 매크로

아래 매크로는 REST API를 통한 storage format 업로드 시 500 에러 발생 (ResourceIdentifier ClassCastException). Confluence 에디터 UI에서 직접 추가해야 합니다.

- `livesearch` - spaceKey 파라미터 파싱 실패
- `widget` - url 파라미터 파싱 실패

미설치: `drawio`, `gliffy`, `lucidchart`
미동작: `flowchart` (파라미터명, 독립 매크로 아님)

## 알려진 호환성 이슈

| 매크로 | 이슈 | 대안 |
|--------|------|------|
| `chart` (pie, bar, line) | 한국어 라벨 서버사이드 폰트 미지원 → □□□ 깨짐 | `mermaid-macro`의 `pie` 사용 |
| `markdown` | 같은 페이지에서 mermaid flowchart 렌더링을 깨트림 (JS 충돌) | storage format(HTML)으로 직접 작성 |
| `mermaid-macro` flowchart | `graph TD` 대신 `flowchart TD` 사용 권장 | - |
| `mermaid-macro` init directive | **멀티라인 `%%{init:...}%%` → mermaid 9.2.2에서 "Syntax error in graph"** | 반드시 한 줄로 작성 |
| `mermaid-macro` gitGraph | 9.2.2에서 신문법 미지원 → "Syntax error" | PlantUML 또는 이미지 첨부로 대체 |
| `mermaid-macro` 10.x 전용 타입 | `mindmap`, `timeline`, `quadrantChart`, `sankey` 등 9.2.2 미지원 | PlantUML 또는 이미지 첨부로 대체 |
