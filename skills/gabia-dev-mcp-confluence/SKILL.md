---
name: gabia-dev-mcp-confluence
description: Confluence REST API를 직접 호출해 페이지 검색/조회/생성/수정/삭제/댓글(조회/추가/수정/삭제)을 자동화할 때 사용한다. MCP가 없어도 scripts/confluence_cli.py로 수행한다.
---

# Confluence Automation

## 제공 기능

- 페이지 검색(단순 텍스트 또는 CQL)
- 페이지 조회(page_id 또는 title+space_key)
- 페이지 생성/수정/삭제
- **댓글 조회/추가/수정/삭제**
- 첨부파일 목록 조회
- 첨부파일 다운로드 (개별 또는 전체)
- **첨부파일 업로드** (개별 또는 다중)
- Markdown ↔ Confluence storage HTML(간이 변환)
- **URL에서 page-id 자동 추출** (`--page-id`에 Confluence URL을 그대로 전달 가능)

## 사전 조건(환경변수)

- `CONFLUENCE_BASE_URL` (필수)
- 인증(아래 중 1개)
  - `ATLASSIAN_OAUTH_ACCESS_TOKEN`
  - `CONFLUENCE_USERNAME` + `CONFLUENCE_API_TOKEN`
  - `ATLASSIAN_EMAIL` + `ATLASSIAN_API_TOKEN`
- (선택) `CONFLUENCE_SPACES_FILTER`: 검색 결과를 특정 space로 제한(쉼표 구분)

## 기본 워크플로우(권장)

1. `scripts/confluence_cli.py search`로 관련 페이지를 찾습니다.
2. `scripts/confluence_cli.py get`로 본문을 가져옵니다.
   - 기본: HTML (렌더링된 결과)
   - `--output-format storage`: 원본 XML (매크로 포함)
   - `--output-format markdown`: Markdown 변환 (LLM 처리용)
3. 새 문서면 `create`, 기존 문서 수정이면 `update`를 사용합니다.
4. 변경 이력/추가 설명은 `comment`로 남깁니다.

### 다이어그램 작성

- Confluence 문서에 다이어그램이 필요하면 **이미지 첨부보다 `mermaid-macro` 사용을 우선**합니다.
- 기존 페이지에 mermaid가 있으면 반드시 `get --output-format storage`로 본문 XML을 확인한 뒤 같은 패턴으로 수정합니다.
- 새 다이어그램을 추가할 때는 storage 본문에 아래 매크로를 직접 넣습니다.
- 사용자의 요청 의도에 따라 적절한 Mermaid 타입을 선택합니다.
  - 흐름/절차 설명: `flowchart`, `sequenceDiagram`, `stateDiagram-v2`, `journey`
  - 데이터/객체 관계 설명: `erDiagram`, `classDiagram`
  - 일정/비율/브랜치 흐름 설명: `gantt`, `pie`, `gitGraph`
- 색상은 아래 `themeVariables` 값을 기본값으로 사용합니다.
  - `background: #FFFFFF`
  - `primaryColor: #E0F2FE`
  - `primaryTextColor: #0F172A`
  - `primaryBorderColor: #0369A1`
  - `secondaryColor: #DCFCE7`
  - `secondaryTextColor: #14532D`
  - `secondaryBorderColor: #16A34A`
  - `tertiaryColor: #FDE68A`
  - `tertiaryTextColor: #78350F`
  - `tertiaryBorderColor: #D97706`
  - `lineColor: #334155`
  - `noteBkgColor: #FEF3C7`
  - `noteTextColor: #1F2937`
- 현재 Confluence 환경에서는 `classDef`, `linkStyle` 같은 명시적 스타일보다 `%%{init: ... themeVariables ...}%%` 방식의 호환성이 더 높으므로 이를 우선 사용합니다.
- 현재 페이지 기준으로 렌더링 확인된 Mermaid 타입은 아래와 같습니다.
  - `erDiagram`
  - `flowchart`
  - `sequenceDiagram`
  - `classDiagram`
  - `stateDiagram-v2`
  - `gantt`
  - `pie`
  - `journey`
  - `gitGraph`
- `requirementDiagram`은 현재 Confluence 환경에서 제외합니다.
- 다이어그램 데이터가 너무 커서 Confluence 편집기 성능 저하, 매크로 렌더링 지연, 페이지 로딩 저하가 우려되면 Mermaid 매크로를 고집하지 않습니다.
- 이런 경우에는 Python 스크립트로 다이어그램 이미지를 생성한 뒤, Confluence 첨부파일로 업로드하고 페이지 본문에는 이미지를 삽입하는 방식으로 진행합니다.
- 대용량 다이어그램 처리 순서는 아래를 따릅니다.
  - Python 스크립트로 SVG 또는 PNG 생성
  - `attachments` 또는 `upload`로 Confluence 페이지에 파일 업로드
  - 본문에는 이미지 또는 첨부 링크를 배치
  - 필요한 경우 원본 Mermaid 텍스트는 별도 코드 블록이나 하위 문단에 보관

```xml
<ac:structured-macro ac:name="mermaid-macro" ac:schema-version="1">
  <ac:plain-text-body><![CDATA[
%%{init: {"theme": "base", "themeVariables": {
  "darkMode": false,
  "background": "#FFFFFF",
  "primaryColor": "#E0F2FE",
  "primaryTextColor": "#0F172A",
  "primaryBorderColor": "#0369A1",
  "secondaryColor": "#DCFCE7",
  "secondaryTextColor": "#14532D",
  "secondaryBorderColor": "#16A34A",
  "tertiaryColor": "#FDE68A",
  "tertiaryTextColor": "#78350F",
  "tertiaryBorderColor": "#D97706",
  "lineColor": "#334155",
  "noteBkgColor": "#FEF3C7",
  "noteTextColor": "#1F2937"
}}}%%
flowchart TD
    A[시작] --> B[다이어그램 작성]
    B --> C[Confluence 업데이트]
  ]]></ac:plain-text-body>
</ac:structured-macro>
```

- 문서 구조를 설명할 때는 `flowchart`, 데이터 관계를 설명할 때는 `erDiagram`을 우선 고려합니다.
- mermaid가 포함된 페이지를 수정한 뒤에는 HTML 렌더링 결과도 다시 조회해 매크로 오류 여부를 확인합니다.

### 댓글 워크플로우

1. `comments`로 기존 댓글 조회 → 형식/패턴 파악
2. `comment`로 새 댓글 추가 (기본 format: `storage`)
3. 수정이 필요하면 `comment-update --comment-id <id>`
4. 삭제가 필요하면 `comment-delete --comment-id <id>`

## 사용법(스크립트)

### 검색

```bash
python3 scripts/confluence_cli.py search --query "deployment guide" --limit 10
```
- `--spaces-filter ""`를 주면 space 필터를 강제로 해제합니다.

### 페이지 조회

```bash
# HTML로 조회 (기본값)
python3 scripts/confluence_cli.py get --page-id 123456

# Storage format으로 조회 (원본 XML, 매크로 포함)
python3 scripts/confluence_cli.py get --page-id 123456 --output-format storage

# Markdown으로 변환해서 조회
python3 scripts/confluence_cli.py get --page-id 123456 --output-format markdown

# title + space-key로 조회
python3 scripts/confluence_cli.py get --space-key DEV --title "문서 제목"

# Confluence URL을 그대로 전달 (page-id 자동 추출)
python3 scripts/confluence_cli.py get --page-id "https://confluence.example.com/spaces/DEV/pages/123456/제목"
```

### 페이지 생성/수정/삭제

- `--format` 기본은 `storage`(HTML)이며, 본문을 그대로 Confluence에 업로드합니다.
- Markdown으로 작성하려면 `--format markdown`을 지정하면 스크립트가 HTML로 변환합니다.

```bash
# 페이지 생성
python3 scripts/confluence_cli.py create \
  --space DEV \
  --title '릴리즈 노트 - 2026-01-07' \
  --content '<h1>릴리즈 노트</h1><p>본문 내용</p>'

# Markdown 파일로 생성
python3 scripts/confluence_cli.py create \
  --space DEV \
  --title '릴리즈 노트 - 2026-01-07' \
  --format markdown \
  --content-file ./release-note.md

# 페이지 수정
python3 scripts/confluence_cli.py update \
  --page-id 123456789 \
  --title '릴리즈 노트 - 2026-01-07' \
  --version-comment '자동 업데이트: MR 요약 반영' \
  --content-file ./release-note.md

# 페이지 삭제
python3 scripts/confluence_cli.py delete --page-id 123456789
```

### 댓글

```bash
# 댓글 목록 조회
python3 scripts/confluence_cli.py comments --page-id 123456789
python3 scripts/confluence_cli.py comments --page-id 123456789 --limit 50

# 댓글 추가 (기본 format: storage - HTML을 그대로 전달)
python3 scripts/confluence_cli.py comment \
  --page-id 123456789 \
  --content '<p>댓글 내용</p>'

# 댓글 추가 (Markdown으로 작성)
python3 scripts/confluence_cli.py comment \
  --page-id 123456789 \
  --format markdown \
  --content '**변경 요약**: 배포 후 모니터링 항목을 추가했습니다.'

# 댓글 수정 (comment-id는 comments 조회 결과에서 확인)
python3 scripts/confluence_cli.py comment-update \
  --comment-id 241913446 \
  --content '<p>수정된 댓글 내용</p>'

# 댓글 삭제
python3 scripts/confluence_cli.py comment-delete --comment-id 241913446
```

### 첨부파일

```bash
# 첨부파일 목록 조회
python3 scripts/confluence_cli.py attachments --page-id 123456789

# 모든 첨부파일 다운로드 (현재 디렉토리)
python3 scripts/confluence_cli.py download --page-id 123456789

# 특정 파일만 다운로드
python3 scripts/confluence_cli.py download --page-id 123456789 --filename "가이드문서.pdf"

# 지정 경로에 다운로드 (기존 파일 덮어쓰기)
python3 scripts/confluence_cli.py download \
  --page-id 123456789 \
  --output-dir ./attachments \
  --overwrite

# 첨부파일 업로드 (단일)
python3 scripts/confluence_cli.py upload --page-id 123456789 --file ./image.png

# 첨부파일 업로드 (다중)
python3 scripts/confluence_cli.py upload \
  --page-id 123456789 \
  --file ./img1.png \
  --file ./img2.png

# Confluence URL 사용
python3 scripts/confluence_cli.py upload \
  --page-id "https://confluence.gabia.com/spaces/DEV/pages/123456/제목" \
  --file ./document.pdf
```

## 사용 가능한 Confluence 매크로

`--format markdown`으로 업로드 시 ` ```mermaid ` 블록은 Mermaid 매크로로, ` ```plantuml ` 블록은 PlantUML 매크로로, 그 외 ` ```lang ` 블록은 코드 매크로로 자동 변환됩니다.

`--format storage`로 직접 storage XML을 작성할 때는 아래 매크로를 사용할 수 있습니다.

### 다이어그램/시각화

| 매크로 | 용도 | storage format 예시 |
|--------|------|---------------------|
| `mermaid-macro` | Mermaid 다이어그램 (flowchart, sequence, state, pie 등) - **권장** | `<ac:structured-macro ac:name="mermaid-macro" ac:schema-version="1"><ac:plain-text-body><![CDATA[flowchart TD ...]]></ac:plain-text-body></ac:structured-macro>` |
| `plantuml` | PlantUML 다이어그램 (시퀀스, 상태, 컴포넌트 등) | `<ac:structured-macro ac:name="plantuml" ac:schema-version="1"><ac:parameter ac:name="atlassian-macro-output-type">INLINE</ac:parameter><ac:plain-text-body><![CDATA[@startuml ... @enduml]]></ac:plain-text-body></ac:structured-macro>` |
| `chart` | 내장 차트 (pie, bar, line 등). **⚠️ 한국어 라벨 깨짐(□□) → mermaid pie 사용 권장** | `<ac:structured-macro ac:name="chart"><ac:parameter ac:name="type">pie</ac:parameter><ac:rich-text-body><table>...</table></ac:rich-text-body></ac:structured-macro>` |

### 코드/서식

| 매크로 | 용도 | storage format 예시 |
|--------|------|---------------------|
| `code` | 코드 블록 (구문 강조) | `<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">typescript</ac:parameter><ac:plain-text-body><![CDATA[코드]]></ac:plain-text-body></ac:structured-macro>` |
| `noformat` | 서식 없는 텍스트 | `<ac:structured-macro ac:name="noformat"><ac:plain-text-body><![CDATA[텍스트]]></ac:plain-text-body></ac:structured-macro>` |
| `markdown` | Markdown 렌더링. **⚠️ mermaid flowchart 렌더링 충돌 → 사용 비권장** (storage format으로 직접 작성 권장) | `<ac:structured-macro ac:name="markdown"><ac:plain-text-body><![CDATA[# 제목 ...]]></ac:plain-text-body></ac:structured-macro>` |

### 정보 패널

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

### 상태/라벨

| 매크로 | 용도 | 사용 가능 색상 |
|--------|------|---------------|
| `status` | 인라인 상태 라벨 | Green, Yellow, Red, Blue, Grey |

```xml
<ac:structured-macro ac:name="status">
  <ac:parameter ac:name="title">완료</ac:parameter>
  <ac:parameter ac:name="colour">Green</ac:parameter>
</ac:structured-macro>
```

### 레이아웃/구조

| 매크로 | 용도 |
|--------|------|
| `section` + `column` | 멀티 컬럼 레이아웃 |
| `toc` | 목차 자동 생성 |
| `div` | CSS 스타일 커스텀 블록 |
| `children` | 하위 페이지 목록 |
| `pagetree` | 페이지 트리 |
| `excerpt` / `excerpt-include` | 발췌 정의/포함 |

### 동적 콘텐츠

| 매크로 | 용도 |
|--------|------|
| `recently-updated` | 최근 업데이트 목록 |
| `change-history` | 변경 이력 |
| `contributors` | 기여자 목록 |
| `contributors-summary` | 기여자 요약 |
| `loremipsum` | 더미 텍스트 생성 |
| `attachments` | 첨부파일 목록 표시 |

### 수학/LaTeX

| 매크로 | 용도 | storage format 예시 |
|--------|------|---------------------|
| `latex-inline` | 인라인 수식 | `<ac:structured-macro ac:name="latex-inline"><ac:plain-text-body><![CDATA[E = mc^2]]></ac:plain-text-body></ac:structured-macro>` |
| `latex-block` | 블록 수식 | `<ac:structured-macro ac:name="latex-block"><ac:plain-text-body><![CDATA[\sum_{i=1}^{n} x_i]]></ac:plain-text-body></ac:structured-macro>` |

### 기타

| 요소 | 용도 |
|------|------|
| `ac:task-list` / `ac:task` | 체크리스트 (태스크 목록) |

```xml
<ac:task-list>
  <ac:task><ac:task-id>1</ac:task-id><ac:task-status>complete</ac:task-status><ac:task-body>완료 항목</ac:task-body></ac:task>
  <ac:task><ac:task-id>2</ac:task-id><ac:task-status>incomplete</ac:task-status><ac:task-body>미완료 항목</ac:task-body></ac:task>
</ac:task-list>
```

### Mermaid vs PlantUML 선택 기준

| 기준 | Mermaid (`mermaid-macro`) | PlantUML (`plantuml`) |
|------|--------------------------|----------------------|
| **권장** | O (기본 선택) | 복잡한 UML 필요 시 |
| Markdown 호환 | ` ```mermaid ` 그대로 사용 | ` ```plantuml ` + @startuml/@enduml 필요 |
| 문법 난이도 | 쉬움 | 보통 |
| 한국어 | 지원 | 지원 |
| 다이어그램 종류 | flowchart, sequence, state, class, ER, gantt, pie | 시퀀스, 상태, 컴포넌트, 클래스, 배포 |

### PlantUML 작성 시 주의사항

- participant/state 이름에 **하이픈(`-`)이나 특수문자**가 있으면 반드시 따옴표로 감싸기: `participant "ingress-auth" as ingressAuth`
- `@startuml` / `@enduml`로 반드시 감싸야 함
- 한국어 텍스트 사용 가능

### 검증된 매크로 목록 (PoC 테스트 완료)

**다이어그램/시각화:** `mermaid-macro` (flowchart, sequence, state, pie), `plantuml`, `chart` (⚠️ 한국어 깨짐 → mermaid 대체 권장)

**코드/서식:** `code`, `noformat`, `markdown` (⚠️ mermaid flowchart 충돌 주의)

**정보 패널:** `info`, `note`, `warning`, `tip`, `panel`, `expand`

**상태/라벨:** `status` (Green, Yellow, Red, Blue, Grey)

**레이아웃:** `section`+`column`, `toc`, `div`

**네비게이션:** `children`, `pagetree`

**동적 콘텐츠:** `recently-updated`, `change-history`, `contributors`, `contributors-summary`

**수학:** `latex-inline`, `latex-block`

**기타:** `loremipsum`, `excerpt`, `attachments`, `tasklist` (ac:task-list)

### API 업로드 불가 매크로

아래 매크로는 REST API를 통한 storage format 업로드 시 500 에러 발생 (ResourceIdentifier ClassCastException). Confluence 에디터 UI에서 직접 추가해야 합니다.

- `livesearch` - spaceKey 파라미터 파싱 실패
- `widget` - url 파라미터 파싱 실패

미설치: `drawio`, `gliffy`, `lucidchart`
미동작: `flowchart` (파라미터명, 독립 매크로 아님)

### 알려진 호환성 이슈

| 매크로 | 이슈 | 대안 |
|--------|------|------|
| `chart` (pie, bar, line) | 한국어 라벨 서버사이드 폰트 미지원 → □□□ 깨짐 | `mermaid-macro`의 `pie` 사용 |
| `markdown` | 같은 페이지에서 mermaid flowchart 렌더링을 깨트림 (JS 충돌) | storage format(HTML)으로 직접 작성 |
| `mermaid-macro` flowchart | `graph TD` 대신 `flowchart TD` 사용 권장 | - |

## 주의사항

- `comment`와 `comment-update`의 기본 format은 **`storage`** (Confluence HTML)입니다.
  - Confluence에서 복사한 HTML을 그대로 전달할 때는 기본값 사용
  - Markdown으로 작성하려면 반드시 `--format markdown` 지정
- `--page-id`에 page ID 숫자 또는 Confluence URL을 모두 사용할 수 있습니다.
  - 예: `--page-id 241911562` 또는 `--page-id "https://confluence.gabia.com/spaces/clouddev/pages/241911562/..."`
