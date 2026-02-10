---
name: gabia-dev-mcp-figma
description: Figma API를 직접 호출해 파일/노드 JSON 조회, PNG/SVG 다운로드, Markdown 문서 자동 생성을 수행한다. 수동 내보내기 이미지 폴더로도 기획서 문서화 가능. "피그마 문서화", "Figma 화면 추출", "기획서 이미지 뽑기", "피그마 기획서 이미지 문서화" 등 요청 시 사용.
---

# Figma Automation

## 제공 기능

1. **파일/노드 JSON 조회** (`figma_cli.py`)
2. **노드 렌더(PNG/SVG) 다운로드** (`figma_cli.py`)
3. **Markdown 문서 자동 생성** (`figma_doc.py` — API 기반)
4. **수동 이미지 → Markdown 변환** (`figma_doc.py build` — API 없이)
5. **AI 설명 자동 생성** (`figma_doc.py`)

## 사전 조건

- `FIGMA_API_KEY` 또는 `FIGMA_OAUTH_TOKEN` 환경변수
- 이미지 리사이징 시: `pip install Pillow`

---

## 1. 파일/노드 조회 및 다운로드 (figma_cli.py)

### 기본 워크플로우

1. `python3 scripts/figma_cli.py get`으로 파일 또는 특정 노드 조회
2. 필요한 노드 ID / imageRef를 추려 `python3 scripts/figma_cli.py download`로 다운로드

### 파일/노드 조회

```bash
python3 scripts/figma_cli.py get --file-key AbCdEfGhIjKlMnOp
python3 scripts/figma_cli.py get --file-key AbCdEfGhIjKlMnOp --node-id 1234:5678
```

### 이미지 다운로드(PNG/SVG)

```bash
python3 scripts/figma_cli.py download \
  --file-key AbCdEfGhIjKlMnOp \
  --local-path ./figma_images \
  --png-scale 2 \
  --nodes-json '[{"nodeId": "1234:5678", "fileName": "icon.svg"}]'
```

---

## 2. Markdown 문서 생성 (figma_doc.py)

Figma 파일의 프레임들을 이미지로 추출하고 Markdown 문서로 정리한다.

### 프레임 목록 확인

```bash
python3 scripts/figma_doc.py --insecure list --file-key <FILE_KEY>
python3 scripts/figma_doc.py --insecure list --file-key <FILE_KEY> --filter "로그인"
```

### 화면 1장 추출 (--single)

```bash
python3 scripts/figma_doc.py --insecure export \
  --file-key <FILE_KEY> \
  --node-id "1:11" \
  --single \
  --resize \
  --with-description \
  --output ./output
```

### 검색 결과 일괄 추출 (--filter)

```bash
python3 scripts/figma_doc.py --insecure export \
  --file-key <FILE_KEY> \
  --filter "자산구매" \
  --resize \
  --with-description \
  --output ./output
```

### 전체 파일 추출

`--node-id`와 `--filter` 없이 실행하면 파일 내 모든 프레임을 한 번에 추출한다.
기본 배치 크기가 500이므로 대부분의 파일은 **1회의 API 호출**로 전체 렌더 URL을 가져온다.

```bash
python3 scripts/figma_doc.py --insecure export \
  --file-key <FILE_KEY> \
  --resize \
  --with-description \
  --resume \
  --output ./output
```

`--resume`을 함께 사용하면 중간에 중단되더라도 이미 다운로드된 이미지를 건너뛰고 이어서 진행한다.

### Rate Limit 대응

Figma API는 분당 요청 횟수가 제한되어 있다 (Images API = Tier 2):

| 좌석 유형 | Starter | Professional | Organization | Enterprise |
|-----------|---------|--------------|--------------|------------|
| View/Collab | 5/min | 5/min | 5/min | 5/min |
| Dev/Full | 25/min | 50/min | 100/min | 150/min |

- 기본 `--batch-size 500`으로 **한 번에 전체 요청**하여 API 호출 횟수를 최소화
- 429 에러 발생 시 `Retry-After` 헤더를 읽고 자동 대기 후 재시도 (최대 3회)
- 5분 이상 대기 필요 시 에러 메시지와 함께 해결책 안내

프레임이 500개를 초과하는 대형 파일의 경우 배치가 나뉘며, `--delay`(기본 12초)만큼 배치 사이에 대기한다.

### AI 설명 자동 생성

`--with-description` 옵션 사용 시, export 완료 후 Claude Code가 자동으로 설명을 채운다:

1. 생성된 Markdown 파일을 Read로 읽는다
2. 각 이미지 파일(`images/*.png`)을 Read로 읽어 분석한다
3. `<!-- AI_DESCRIPTION_START -->` ~ `<!-- AI_DESCRIPTION_END -->` 사이를 채운다
4. Edit 도구로 Markdown 파일에 설명을 업데이트한다

### 옵션 설명

| 옵션 | 설명 |
|------|------|
| `--insecure` | SSL 인증서 검증 비활성화 (회사 프록시 환경) |
| `--file-key` | Figma URL의 `/file/<KEY>/` 또는 `/design/<KEY>/` 부분 |
| `--node-id` | 특정 노드만 추출 |
| `--single` | node-id로 지정한 프레임 자체를 1장으로 렌더링 |
| `--filter` | 프레임 이름 필터 (정규식 지원) |
| `--output` | 출력 디렉토리 |
| `--scale` | 이미지 스케일 (기본값: 2) |
| `--resize` | AI 모델 입력 크기에 맞게 리사이징 |
| `--model` | 리사이징 기준: claude(1568px), gpt4(2048px), gemini(3072px) |
| `--with-description` | AI 설명 플레이스홀더 추가 |
| `--delay` | 배치 요청 간 딜레이 초 (기본값: 12) |
| `--batch-size` | 렌더 요청 배치 크기 (기본값: 500, 한 번에 전체 요청) |
| `--resume` | 이미 다운로드된 이미지 건너뛰기 (중단 후 재시작) |

### 출력 구조

```
output/
├── Document_Title.md
└── images/
    ├── 001_Login.png
    ├── 002_Home.png
    └── ...
```

---

## 3. 수동 이미지 → Markdown 변환 (figma_doc.py build)

API 토큰 없이, Figma에서 직접 내보내기한 이미지 폴더를 Markdown 문서로 변환한다.
Rate limit에 걸렸거나 API 키가 없는 환경에서 유용하다.

### 워크플로우

1. Figma에서 프레임을 선택 → 우클릭 → "Export" → PNG 저장
2. 저장된 이미지 폴더 경로를 `build` 명령에 전달
3. 생성된 Markdown 파일의 AI 설명을 Claude Code가 자동 채움

### 기본 사용법

```bash
python3 scripts/figma_doc.py build \
  --images-dir ./figma_images \
  --resize \
  --output ./output
```

### 제목 지정

```bash
python3 scripts/figma_doc.py build \
  --images-dir ./figma_images \
  --title "인재채용 개편 2025" \
  --resize \
  --output ./output
```

### AI 설명 없이 이미지만 정리

```bash
python3 scripts/figma_doc.py build \
  --images-dir ./figma_images \
  --no-description \
  --output ./output
```

### 옵션 설명

| 옵션 | 설명 |
|------|------|
| `--images-dir` | (필수) Figma에서 내보낸 이미지 폴더 경로 |
| `--output` | 출력 디렉토리 (기본값: 이미지 폴더 상위) |
| `--title` | 문서 제목 (기본값: 폴더명) |
| `--resize` | AI 모델 입력 크기에 맞게 리사이징 |
| `--model` | 리사이징 기준: claude(1568px), gpt4(2048px), gemini(3072px) |
| `--no-description` | AI 설명 플레이스홀더 생략 |

### 출력 구조

```
output/
├── 인재채용_개편_2025.md
└── images/
    ├── 001_로그인.png
    ├── 002_메인화면.png
    └── ...
```

### AI 설명 채우기

`--no-description` 없이 실행하면 Markdown에 AI 설명 플레이스홀더가 포함된다.
생성 후 Claude Code에게 다음과 같이 요청:

> "output/인재채용_개편_2025.md 파일의 AI 설명을 채워줘"

Claude Code가 각 이미지를 읽고 `<!-- AI_DESCRIPTION_START -->` ~ `<!-- AI_DESCRIPTION_END -->` 사이를 자동으로 채운다.

---

## 사용 팁

- `fileKey`는 Figma URL의 `/file/<fileKey>/...` 또는 `/design/<fileKey>/...` 부분
- 큰 파일은 `--node-id`로 범위를 줄임
- `fileName`이 `.svg`로 끝나면 SVG, 그 외는 PNG 렌더
- 전체 추출 시 `--resume`을 항상 사용하면 중단 후 이어서 다운로드 가능
- 429 에러 시 자동 재시도 (최대 3회, `Retry-After` 헤더 존중)
- Rate limit 우회: 다른 Figma 계정 토큰 사용 또는 OAuth 앱 생성 (토큰별 별도 할당량)
- API 없이 사용: Figma에서 직접 PNG 내보내기 후 `build` 명령으로 Markdown 생성
