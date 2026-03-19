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

> **⚠️ 현재 Confluence 환경의 Mermaid 버전: 9.2.2**
> 아래 가이드는 mermaid 9.2.2 호환성을 기준으로 작성되었습니다.

- Confluence 문서에 다이어그램이 필요하면 **이미지 첨부보다 `mermaid-macro` 사용을 우선**합니다.
- 기존 페이지에 mermaid가 있으면 반드시 `get --output-format storage`로 본문 XML을 확인한 뒤 같은 패턴으로 수정합니다.
- 새 다이어그램을 추가할 때는 storage 본문에 아래 매크로를 직접 넣습니다.
- 사용자의 요청 의도에 따라 적절한 Mermaid 타입을 선택합니다.
  - 흐름/절차 설명: `flowchart`, `sequenceDiagram`, `stateDiagram-v2`, `journey`
  - 데이터/객체 관계 설명: `erDiagram`, `classDiagram`
  - 일정/비율 설명: `gantt`, `pie`
  - ~~브랜치 흐름: `gitGraph`~~ → 9.2.2 미지원, PlantUML 또는 이미지로 대체
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
- **`%%{init:...}%%` directive는 반드시 한 줄에 작성해야 합니다.** 멀티라인으로 작성하면 mermaid 9.2.2에서 "Syntax error in graph" 파싱 에러가 발생합니다.
- 현재 페이지 기준으로 렌더링 확인된 Mermaid 타입은 아래와 같습니다 (mermaid 9.2.2 호환).
  - `erDiagram`
  - `flowchart` (`graph TD`도 사용 가능)
  - `sequenceDiagram`
  - `classDiagram`
  - `stateDiagram-v2`
  - `gantt`
  - `pie`
  - `journey`
- **9.2.2 미지원/호환성 이슈 다이어그램 타입:**
  - `gitGraph` — 9.2.2에서는 구문법(`gitGraph:` + options 블록)만 지원하며 신문법(`gitGraph` + commit/branch)은 "Syntax error" 발생. 사용을 피하고 필요시 PlantUML이나 이미지로 대체합니다.
  - `requirementDiagram` — 현재 Confluence 환경에서 제외
  - `mindmap`, `timeline`, `quadrantChart`, `sankey`, `zenuml`, `xychart-beta`, `block-beta` — mermaid 10.x 이후 추가된 타입으로 9.2.2에서 미지원
- 다이어그램 데이터가 너무 커서 Confluence 편집기 성능 저하, 매크로 렌더링 지연, 페이지 로딩 저하가 우려되면 Mermaid 매크로를 고집하지 않습니다.
- 이런 경우에는 Python 스크립트로 다이어그램 이미지를 생성한 뒤, Confluence 첨부파일로 업로드하고 페이지 본문에는 이미지를 삽입하는 방식으로 진행합니다.
- 대용량 다이어그램 처리 순서는 아래를 따릅니다.
  - Python 스크립트로 SVG 또는 PNG 생성
  - `attachments` 또는 `upload`로 Confluence 페이지에 파일 업로드
  - 본문에는 이미지 또는 첨부 링크를 배치
  - 필요한 경우 원본 Mermaid 텍스트는 별도 코드 블록이나 하위 문단에 보관

```xml
<!-- ⚠️ %%{init:...}%% 는 반드시 한 줄로 작성 (mermaid 9.2.2 호환) -->
<ac:structured-macro ac:name="mermaid-macro" ac:schema-version="1">
  <ac:plain-text-body><![CDATA[%%{init: {"theme": "base", "themeVariables": {"darkMode": false, "background": "#FFFFFF", "primaryColor": "#E0F2FE", "primaryTextColor": "#0F172A", "primaryBorderColor": "#0369A1", "secondaryColor": "#DCFCE7", "secondaryTextColor": "#14532D", "secondaryBorderColor": "#16A34A", "tertiaryColor": "#FDE68A", "tertiaryTextColor": "#78350F", "tertiaryBorderColor": "#D97706", "lineColor": "#334155", "noteBkgColor": "#FEF3C7", "noteTextColor": "#1F2937"}}}%%
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
| 다이어그램 종류 | flowchart, sequence, state, class, ER, gantt, pie, journey (9.2.2 기준) | 시퀀스, 상태, 컴포넌트, 클래스, 배포, gitGraph 대체 |

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
| `mermaid-macro` init directive | **멀티라인 `%%{init:...}%%` → mermaid 9.2.2에서 "Syntax error in graph"** | 반드시 한 줄로 작성 |
| `mermaid-macro` gitGraph | 9.2.2에서 신문법 미지원 → "Syntax error" | PlantUML 또는 이미지 첨부로 대체 |
| `mermaid-macro` 10.x 전용 타입 | `mindmap`, `timeline`, `quadrantChart`, `sankey` 등 9.2.2 미지원 | PlantUML 또는 이미지 첨부로 대체 |

## 화면 UI 목업 (Storage Format HTML)

Confluence 정책서에 화면 UI를 HTML로 삽입할 때 사용하는 컴포넌트 라이브러리입니다.
PDF 기획서나 와이어프레임을 Confluence 페이지에 HTML로 재현할 때 아래 빌딩블록을 조합합니다.

### 사용 시점

- 사용자가 "화면 넣어줘", "UI 목업 추가", "화면 섹션 추가" 등 요청 시
- PDF 기획서를 Confluence 정책서로 변환할 때
- 정책서에 시각적 화면 레이아웃이 필요할 때

### 기본 원칙

1. **모든 화면은 `panel` 매크로로 감싼다** — 본문과 시각적으로 구분
2. **inline style만 사용** — Confluence는 외부 CSS/class를 지원하지 않음
3. **`status` 매크로로 상태 뱃지 표현** — Green(활성화), Grey(비활성화), Blue(버튼), Yellow(대기), Red(삭제/경고)
4. **`section`+`column` 매크로로 비교 레이아웃** — 검색결과 있음/없음 등 병렬 표시
5. **중첩 `panel`로 모달 표현** — 바깥 panel(딤 배경) > 안쪽 panel(모달 본체)

### 컴포넌트 목록

#### 1. 탭 네비게이션

```xml
<p style="margin-top: 8px;">
<span style="margin-right: 16px; color: #666;">탭1</span>
<span style="border-bottom: 2px solid #2563eb; padding-bottom: 4px; margin-right: 16px; color: #2563eb; font-weight: bold;">현재탭</span>
<span style="margin-right: 16px; color: #666;">탭3</span>
</p>
```

#### 2. 상태 뱃지

```xml
<!-- 활성화 -->
<ac:structured-macro ac:name="status"><ac:parameter ac:name="title">활성화</ac:parameter><ac:parameter ac:name="colour">Green</ac:parameter></ac:structured-macro>

<!-- 비활성화 -->
<ac:structured-macro ac:name="status"><ac:parameter ac:name="title">비활성화</ac:parameter><ac:parameter ac:name="colour">Grey</ac:parameter></ac:structured-macro>

<!-- 버튼 스타일 -->
<ac:structured-macro ac:name="status"><ac:parameter ac:name="title">공고 수정</ac:parameter><ac:parameter ac:name="colour">Blue</ac:parameter></ac:structured-macro>
```

#### 3. 카드형 목록 아이템 (드래그 핸들 포함)

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

#### 4. 태그/칩 (제거 가능)

```xml
<span style="background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 12px; padding: 2px 10px; font-size: 12px;">홍길동 &#10005;</span>
```

#### 5. 추가(+) 버튼

```xml
<span style="border: 1px solid #d1d5db; border-radius: 4px; padding: 2px 6px; font-size: 14px; color: #999;">&#43;</span>
```

#### 6. 검색 필드

```xml
<span style="background: #fff; border: 1px solid #d1d5db; border-radius: 4px; padding: 2px 8px; font-size: 12px; color: #999;">검색 &#128269;</span>
```

#### 7. 액션 버튼 (Primary)

```xml
<span style="background: #2563eb; color: white; padding: 4px 12px; border-radius: 4px; font-size: 13px;">버튼명</span>
```

#### 8. 액션 버튼 (Secondary/Outline)

```xml
<span style="border: 1px solid #d1d5db; padding: 6px 24px; border-radius: 4px; font-size: 13px; color: #333;">닫기</span>
```

#### 9. 텍스트 링크 버튼

```xml
<span style="color: #2563eb; cursor: pointer;">&#8635; 초기화</span>
```

#### 10. 체크박스 (미선택/선택)

```xml
<!-- 미선택 -->
<span style="border: 1px solid #d1d5db; display: inline-block; width: 16px; height: 16px; text-align: center; font-size: 11px; border-radius: 2px; vertical-align: middle;">&#9744;</span>

<!-- 선택 -->
<span style="background: #2563eb; color: white; display: inline-block; width: 16px; height: 16px; text-align: center; font-size: 11px; border-radius: 2px; vertical-align: middle;">&#10003;</span>
```

#### 11. 드롭다운/레이어 메뉴

```xml
<table style="width: 200px; border-collapse: collapse; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
<tbody>
<tr><td style="border: 1px solid #e5e7eb; padding: 10px 16px; cursor: pointer; font-size: 13px;">메뉴1</td></tr>
<tr><td style="border: 1px solid #e5e7eb; padding: 10px 16px; cursor: pointer; font-size: 13px;">메뉴2</td></tr>
<tr><td style="border: 1px solid #e5e7eb; padding: 10px 16px; cursor: pointer; font-size: 13px; color: #ef4444;">삭제</td></tr>
</tbody>
</table>
```

#### 12. 모달 래퍼

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

#### 13. 검색 드롭다운 (결과 있음/없음)

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

#### 14. 빈 상태 (Empty State)

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

#### 15. 평가자/사용자 태그 행 (라벨 + 태그 목록 + 추가 버튼)

```xml
<p style="color: #666; font-size: 13px;">
평가자&nbsp;&nbsp;
<span style="background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 12px; padding: 2px 10px; font-size: 12px;">이름1 &#10005;</span>&nbsp;
<span style="background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 12px; padding: 2px 10px; font-size: 12px;">이름2 &#10005;</span>&nbsp;
<span style="border: 1px solid #d1d5db; border-radius: 4px; padding: 2px 6px; font-size: 14px; color: #999;">&#43;</span>
</p>
```

### 조합 예시: 카드 목록 화면

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

### 주의사항 (화면 UI)

- Confluence storage format에서 `class` 속성은 무시됨 → 반드시 `style` 인라인으로 작성
- `border-radius`, `box-shadow` 등 CSS3 속성은 Confluence에서 대부분 지원됨
- 화면 섹션은 정책서의 **정책 테이블 위에** 배치하는 것을 권장 (먼저 화면 보고 정책 읽는 흐름)
- 복잡한 화면은 `expand` 매크로로 접어둘 수 있음
- HTML 엔티티 참고: `&#8942;&#8942;`(드래그핸들), `&#8943;`(더보기), `&#10005;`(X), `&#43;`(+), `&#128269;`(돋보기), `&#8635;`(새로고침), `&#9744;`(빈체크), `&#10003;`(체크)

## 주의사항

- `comment`와 `comment-update`의 기본 format은 **`storage`** (Confluence HTML)입니다.
  - Confluence에서 복사한 HTML을 그대로 전달할 때는 기본값 사용
  - Markdown으로 작성하려면 반드시 `--format markdown` 지정
- `--page-id`에 page ID 숫자 또는 Confluence URL을 모두 사용할 수 있습니다.
  - 예: `--page-id 241911562` 또는 `--page-id "https://confluence.gabia.com/spaces/clouddev/pages/241911562/..."`
