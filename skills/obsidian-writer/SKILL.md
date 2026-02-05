---
name: obsidian-writer
description: Obsidian vault에 마크다운 노트를 생성/수정하는 skill. Zettelkasten 스타일 지원. 개발 메모, TIL, 회의록, 프로젝트 문서화 등 범용 목적. "옵시디언에 저장", "노트 작성", "TIL 기록", "회의록 작성", "메모 추가" 등의 요청 시 사용. 환경변수 OBSIDIAN_PATH에 vault 경로 설정 필요.
---

# Obsidian Writer

Obsidian vault에 Zettelkasten 스타일 마크다운 노트를 생성/수정한다.

## 환경 설정

```bash
export OBSIDIAN_PATH="/path/to/your/obsidian/vault"
```

## 에이전트 행동 규칙

### 1. 경로 확인 절차

사용자가 특정 폴더/경로를 언급한 경우:

1. **먼저 직접 하위 경로 확인**: `ls "$OBSIDIAN_PATH/{경로}/"` 시도
2. **없으면 전체 검색**: `find "$OBSIDIAN_PATH" -type d -name "*{키워드}*"` 로 모든 하위 경로에서 검색
3. 여러 개 발견 시 사용자에게 선택 요청

### 2. 생성 위치 확인 (필수)

노트/문서 작성 요청 시:

- **경로가 명시된 경우**: 바로 해당 경로에 생성
- **경로가 없는 경우**: 반드시 "어디에 생성할까요?" 질문 후 진행
  - 예: "01_Projects > 01_Analysis 하위에 생성할까요?"

### 3. 메시지 규칙

- OBSIDIAN_PATH 환경변수 확인 관련 메시지 출력 금지
- 에러 발생 시에만 환경변수 관련 안내

## 노트 생성

```bash
scripts/obsidian.py create "<title>" --type <type> --content "<content>" [--tags "tag1,tag2"]
```

### 노트 타입

| 타입 | 용도 | 폴더 |
|------|------|------|
| `dev` | 개발 메모, 에러 해결 | `01-Development/` |
| `til` | Today I Learned | `02-TIL/` |
| `meeting` | 회의록 | `03-Meetings/` |
| `project` | 프로젝트 문서 | `04-Projects/` |
| `fleeting` | 임시 아이디어 | `00-Inbox/` |
| `permanent` | 영구 노트 | `05-Permanent/` |

### 예시

```bash
# 개발 메모
scripts/obsidian.py create "MySQL 연결 에러 해결" --type dev \
  --content "Communications link failure 에러 원인과 해결법..." \
  --tags "mysql,troubleshooting"

# TIL
scripts/obsidian.py create "Kotlin sealed class" --type til \
  --content "sealed class는 제한된 계층 구조 표현에 사용..."

# 회의록
scripts/obsidian.py create "스프린트 회의" --type meeting \
  --content "## 참석자\n- Aaron\n\n## 안건\n..."
```

## 노트 수정

```bash
# 내용 추가
scripts/obsidian.py append "<note-id>" --content "추가 내용"

# 전체 교체
scripts/obsidian.py update "<note-id>" --content "새 내용"
```

## 노트 검색

```bash
scripts/obsidian.py search "키워드"
scripts/obsidian.py search --tag "kotlin"
scripts/obsidian.py list --type dev
```

## Zettelkasten ID

모든 노트는 `YYYYMMDDHHmmss` 형식 ID 자동 부여.
파일명: `{ID} {제목}.md`

## YAML Frontmatter

```yaml
---
id: "20260205143052"
title: "노트 제목"
type: dev
tags: [kotlin, spring]
created: 2026-02-05T14:30:52
modified: 2026-02-05T14:30:52
links: []
---
```

## 폴더 구조

```
$OBSIDIAN_PATH/
├── 00-Inbox/
├── 01-Development/
├── 02-TIL/
├── 03-Meetings/
├── 04-Projects/
└── 05-Permanent/
```
