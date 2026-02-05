---
name: gabia-dev-mcp-figma
description: Figma API를 직접 호출해 파일/노드 JSON 조회, PNG/SVG 다운로드, Markdown 문서 자동 생성을 수행한다. "피그마 문서화", "Figma 화면 추출", "기획서 이미지 뽑기" 등 요청 시 사용.
---

# Figma Automation

## 제공 기능

1. **파일/노드 JSON 조회** (`figma_cli.py`)
2. **노드 렌더(PNG/SVG) 다운로드** (`figma_cli.py`)
3. **Markdown 문서 자동 생성** (`figma_doc.py`)
4. **AI 설명 자동 생성** (`figma_doc.py`)

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

## 사용 팁

- `fileKey`는 Figma URL의 `/file/<fileKey>/...` 또는 `/design/<fileKey>/...` 부분
- 큰 파일은 `--node-id`로 범위를 줄임
- `fileName`이 `.svg`로 끝나면 SVG, 그 외는 PNG 렌더
