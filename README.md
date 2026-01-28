# 프로젝트 주제 및 목표

## 주제

개발 업무 효율화를 위한 차세대 LLM 개발 툴(Agentic Workflow) 비교 연구 및 실무 도입 가이드 구축

## 목표 (기대 효과)

- 사내 개발 환경에 최적화된 “AI 코딩 어시스턴트 활용 표준 가이드” 수립
- 데이터 접근성 혁신 및 플랫폼 고도화
  - 개발자 의존 없이 기획자가 직접 데이터를 추출할 수 있는 시스템의 기술적 토대 마련 (커뮤니케이션 비용 절감)
- 반복적인 문서 작업, 이슈 트래킹 및 보고 업무 시간 50% 이상 단축
- 최신 AI 도구 도입을 통한 개발 팀원들의 기술 부채 감소 및 코드 품질 향상

## Skills 설치

### macOS / Linux

```bash
curl -fsSL https://gitlab.gabia.com/<group>/nds/-/raw/main/install.sh | bash
```

### Windows (PowerShell)

```powershell
irm https://gitlab.gabia.com/<group>/nds/-/raw/main/install.ps1 | iex
```

실행하면 TUI 메뉴에서 설치할 코딩 에이전트를 선택할 수 있습니다:

```
================================
   NDS Skills Installer
================================

Select coding agents to install skills:

  [Space] Toggle  [Enter] Confirm  [a] Select All  [n] Select None  [q] Quit

> [✓] Claude Code
      ~/.claude/skills

  [✓] Cursor
      ~/.claude/skills

  [ ] Codex CLI
      ~/.codex/skills

  [✓] Gemini CLI
      ~/.gemini/skills

  [ ] Antigravity
      ~/.gemini/antigravity/global_skills
```

### 지원 코딩 에이전트

| Agent | 설치 경로 |
|-------|----------|
| Claude Code | `~/.claude/skills` |
| Cursor | `~/.claude/skills` |
| Codex CLI | `~/.codex/skills` |
| Gemini CLI | `~/.gemini/skills` |
| Antigravity | `~/.gemini/antigravity/global_skills` |

### 설치 옵션

```bash
# 특정 에이전트에만 설치
curl -fsSL <url>/install.sh | bash -s -- --claude --codex

# 모든 에이전트에 설치
curl -fsSL <url>/install.sh | bash -s -- --all

# 특정 스킬만 설치
curl -fsSL <url>/install.sh | bash -s -- --skills "gabia-dev-mcp-oracle,pptx"

# 사용 가능한 스킬 목록 확인
curl -fsSL <url>/install.sh | bash -s -- --list
```

자세한 환경 변수 설정은 [skills/README.md](./skills/README.md)를 참고하세요.

## 문서

- [Notes](./note/README.md) - 개발 경험 및 인사이트 기록
- [Skills](./skills/README.md) - MCP 스킬 목록 및 환경 변수 설정
