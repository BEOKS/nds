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

### Claude Code Marketplace (권장)

Claude Code의 플러그인 마켓플레이스를 통해 설치할 수 있습니다.

**Claude Desktop (앱)**

1. `사용자 지정` > `플러그인 탐색` > `개인` 탭 이동
2. `URL로 마켓플레이스 추가` 클릭
3. 아래 URL 입력:
   ```
   https://repo.gabia.com/repository/raw-repository/nds/marketplace.json
   ```
4. `개인` 탭에 스킬이 표시되면 설치 버튼 클릭

> **참고**: 스킬 다운로드에 시간이 걸려 앱에서 오류가 표시될 수 있습니다. 실제로는 백그라운드에서 다운로드가 진행 중이므로 잠시 기다린 후 `개인` 탭을 다시 확인하면 스킬이 추가되어 있습니다. 설치 완료 후 대화 창에서 바로 사용할 수 있습니다.

**Claude Code (CLI)**

```shell
# 1. 마켓플레이스 추가 (최초 1회)
/plugin marketplace add https://repo.gabia.com/repository/raw-repository/nds/marketplace.json

# 2. 스킬 설치
/plugin install gabia-skills@gabia

# 3. 업데이트
/plugin marketplace update
```

### 스크립트 설치

여러 코딩 에이전트(Claude Code, Cursor, Codex, Gemini 등)에 일괄 설치할 때 사용합니다.

#### macOS / Linux

```bash
curl -fsSL https://repo.gabia.com/repository/raw-repository/nds/install.sh | bash
```

### Windows (PowerShell)

```powershell
irm https://repo.gabia.com/repository/raw-repository/nds/install.ps1 | iex
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
