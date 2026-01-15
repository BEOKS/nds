# NDS Project Agent Instructions

## 프로젝트 개요

차세대 LLM 개발 툴(Agentic Workflow) 비교 연구 및 실무 도입 가이드 구축 프로젝트

## 핵심 목표

- AI 코딩 어시스턴트 활용 표준 가이드 수립
- 개발자 의존 없이 기획자가 직접 데이터 추출 가능한 시스템 구축
- 반복 업무 시간 50% 이상 단축
- 코드 품질 향상 및 기술 부채 감소

## 작업 규칙

### 언어
- 한국어 사용 (코드 주석, 문서 등)
- 기술 용어는 영문 그대로 사용 가능

### 문서 작성
- 노트 파일명: `{날짜-시간}-{제목}-{작성자}.md` 형식
  - 예: `2026-01-15-1023-codex-비교분석-Zayden.md`
  - 날짜-시간: `date +%Y-%m-%d-%H%M` 명령어로 확인
  - 작성자: `git config user.name` 명령어로 확인
- 위치: `note/` 디렉토리
- 내용: 간결하게 핵심만 기록

### 코드 스타일
- 명확하고 읽기 쉬운 코드 작성
- 적절한 주석 추가
- 기존 프로젝트 패턴 따르기

## 디렉토리 구조

```
nds/
├── CLAUDE.md      # Claude Code 설정
├── AGENT.md       # 에이전트 지침
├── README.md      # 프로젝트 소개
├── scripts/       # 설정 및 유틸리티 스크립트
│   └── setup-skills.sh  # Skills 설치 스크립트
├── skills/        # Claude Code Skills 모음
└── note/          # 개발 노트 및 인사이트
    └── README.md  # 노트 가이드
```

## 설정 명령어

### Skills 설치
프로젝트의 skills를 `~/.claude/skills`로 복사:

```bash
# 기본 설치
./scripts/setup-skills.sh

# 기존 파일 덮어쓰기
./scripts/setup-skills.sh -f

# 미리보기 (실제 복사 안 함)
./scripts/setup-skills.sh -n

# 도움말
./scripts/setup-skills.sh -h
```

## 주요 작업 영역

1. **LLM 도구 비교 분석**: Claude, GPT, Cursor 등 도구 비교
2. **실무 가이드 작성**: 도입 및 활용 가이드 문서화
3. **인사이트 기록**: 발견한 내용을 note/에 정리
