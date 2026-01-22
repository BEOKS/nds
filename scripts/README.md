# Scripts

## Skills 설치

프로젝트의 `skills/`를 에이전트별 디렉토리로 복사합니다.

```bash
# 기본 설치 (codex)
./scripts/setup-skills.sh

# 특정 에이전트만 설치 (복수 지정 가능)
./scripts/setup-skills.sh --agent claude,codex

# 지원 에이전트 전체 설치
./scripts/setup-skills.sh --all

# 기존 파일 덮어쓰기
./scripts/setup-skills.sh -f

# 미리보기 (실제 복사 안 함)
./scripts/setup-skills.sh -n
```

지원 에이전트: `claude`, `codex`, `gemini`
