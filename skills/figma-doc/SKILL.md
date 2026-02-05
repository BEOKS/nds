---
name: figma-doc
description: Figma 기획서/디자인 파일에서 프레임(화면 단위)을 이미지로 추출하여 Markdown 문서로 자동 생성한다. AI 모델 입력 크기에 맞는 이미지 리사이징, 화면별 AI 설명 생성을 지원한다. "피그마 문서화", "Figma 화면 추출", "기획서 이미지 뽑기", "Figma to Markdown" 등의 요청 시 사용.
---

# Figma Documentation Generator

Figma 파일의 프레임들을 이미지로 추출하고 Markdown 문서로 정리한다.

## 사전 조건

- `FIGMA_API_KEY` 또는 `FIGMA_OAUTH_TOKEN` 환경변수 설정
- 이미지 리사이징 시: `pip install Pillow`

## 워크플로우

### 1. 프레임 목록 확인

```bash
python3 scripts/figma_doc.py --insecure list --file-key <FILE_KEY>
```

이름으로 검색:
```bash
python3 scripts/figma_doc.py --insecure list --file-key <FILE_KEY> --filter "로그인"
```

### 2. 화면 1장 추출 (--single)

특정 화면 1장만 이미지로 추출:
```bash
python3 scripts/figma_doc.py --insecure export \
  --file-key <FILE_KEY> \
  --node-id "1:11" \
  --single \
  --resize \
  --with-description \
  --output ./output
```

### 3. 검색 결과 일괄 추출 (--filter)

이름 패턴으로 검색해서 일치하는 프레임만 추출:
```bash
python3 scripts/figma_doc.py --insecure export \
  --file-key <FILE_KEY> \
  --filter "자산구매" \
  --resize \
  --with-description \
  --output ./output
```

### 4. AI 설명 자동 생성

`--with-description` 옵션 사용 시, export 완료 후 Claude Code가 자동으로 설명을 채운다:

1. 생성된 Markdown 파일을 Read로 읽는다
2. 각 이미지 파일(`images/*.png`)을 Read로 읽어 분석한다
3. `<!-- AI_DESCRIPTION_START -->` ~ `<!-- AI_DESCRIPTION_END -->` 사이를 채운다:
   - 화면의 목적
   - 주요 UI 요소 (버튼, 입력필드, 테이블 등)
   - 사용자 플로우/인터랙션
4. Edit 도구로 Markdown 파일에 설명을 업데이트한다

**전체 논스톱 워크플로우 예시:**
```bash
# 1. export 실행
python3 scripts/figma_doc.py --insecure export \
  --file-key <FILE_KEY> \
  --node-id "1:11" --single \
  --resize --with-description \
  --output ./output

# 2. Claude Code가 자동으로:
#    - ./output/*.md 읽기
#    - ./output/images/*.png 분석
#    - AI_DESCRIPTION 플레이스홀더 채우기
```

## 명령어

| 명령어 | 설명 |
|--------|------|
| `list` | Figma 파일의 프레임 목록 출력 |
| `export` | 프레임을 이미지로 추출하고 Markdown 문서 생성 |
| `describe` | (선택) Markdown 파일의 이미지/플레이스홀더 상태 확인 |

## 옵션 설명

| 옵션 | 설명 |
|------|------|
| `--insecure` | SSL 인증서 검증 비활성화 (회사 프록시 환경) |
| `--file-key` | Figma URL의 `/file/<KEY>/` 또는 `/design/<KEY>/` 부분 |
| `--node-id` | 특정 노드만 추출 (페이지 또는 섹션) |
| `--single` | node-id로 지정한 프레임 자체를 1장으로 렌더링 |
| `--filter` | 프레임 이름 필터 (정규식 지원) |
| `--output` | 출력 디렉토리 |
| `--title` | 문서 제목 (기본값: Figma 파일명) |
| `--scale` | 이미지 스케일 (기본값: 2) |
| `--max-depth` | 프레임 탐색 깊이 (기본값: 2) |
| `--resize` | AI 모델 입력 크기에 맞게 리사이징 |
| `--model` | 리사이징 기준 모델: claude(1568px), gpt4(2048px), gemini(3072px) |
| `--delay` | 배치 요청 간 딜레이 초 (기본값: 12, View좌석 5회/분 제한 대응) |
| `--with-description` | AI 설명 플레이스홀더 추가 (export 후 Claude Code가 자동 채움) |
| `--markdown` | describe 명령용 Markdown 파일 경로 (선택적 디버깅용) |

## 출력 구조

```
output/
├── Document_Title.md    # Markdown 문서
└── images/
    ├── 001_Login.png
    ├── 002_Home.png
    └── ...
```
