# OpenCode 동작원리 분석

> OpenCode는 독립형 HTTP 서버로 동작하는 모듈러 에이전틱 엔진이며, OpenWork는 이를 감싸는 GUI 래퍼이다.

## 1. 전체 아키텍처

```
┌──────────────────────────────────────────┐
│        OpenWork Desktop (Tauri)          │
│                                          │
│  ┌──────────────┐   ┌────────────────┐  │
│  │  SolidJS UI  │◄─►│ Tauri (Rust)   │  │
│  │  (프론트엔드) │   │ (네이티브 셸)  │  │
│  └──────┬───────┘   └──────┬─────────┘  │
│         └────────┬─────────┘             │
└──────────────────┼───────────────────────┘
                   │ HTTP/SSE
                   ▼
    ┌───────────────────────────────┐
    │  OpenWork Server (Bun/TS)    │
    │  - REST 래퍼                  │
    │  - 권한 승인/감사 로깅        │
    │  - 워크스페이스 관리          │
    └──────────┬────────────────────┘
               │
               ▼
    ┌───────────────────────────────┐
    │  OpenCode Engine             │
    │  `opencode serve` 프로세스    │
    │  (127.0.0.1:4096)           │
    ├───────────────────────────────┤
    │  - 세션 관리                  │
    │  - LLM 추론                  │
    │  - 도구 실행                  │
    │  - 권한 제어                  │
    │  - MCP 서버 연동              │
    │  - SSE 이벤트 스트리밍        │
    └──────────┬────────────────────┘
               ▼
    ┌───────────────────────────────┐
    │  사용자 프로젝트 워크스페이스   │
    │  (.opencode/, opencode.json)  │
    └───────────────────────────────┘
```

**역할 분리**:
- **Engine (OpenCode)**: 실행 담당 - 세션, 도구, LLM 추론
- **Server (OpenWork Server)**: 설정/승인 담당 - 워크스페이스, 권한, 감사
- **UI (OpenWork App)**: 표현 담당 - 실시간 스트리밍, 사용자 인터랙션

---

## 2. OpenCode 서버 메커니즘

### 서버 실행

```bash
opencode serve --hostname 127.0.0.1 --port 4096 --cors ...
```

- HTTP 서버로 동작하며 Bearer 토큰 인증
- 세션 기반 실행 모델
- SSE(Server-Sent Events)로 실시간 이벤트 스트리밍

### SDK 클라이언트 연결

```typescript
import { createOpencodeClient } from "@opencode-ai/sdk/v2/client";

const client = createOpencodeClient({
  baseUrl: "http://127.0.0.1:4096",
  directory: "/path/to/project",
  fetch: platformFetch,
  throwOnError: true,
});
```

**주요 메서드**:
- `client.session.*` - 세션 생명주기
- `client.event.subscribe()` - SSE 스트리밍
- `client.permission.*` - 권한 요청/응답
- `client.file.*` - 파일 조작
- `client.config.*` - 설정 관리

---

## 3. 세션 생명주기

```
created → idle → executing → idle (완료) → archived
```

| 상태 | 설명 |
|------|------|
| `created` | 세션 초기화 |
| `idle` | 대기 상태 |
| `executing` | 프롬프트 처리 중 |
| `completed` | 작업 완료 |
| `archived` | 활성 뷰에서 제거 |

**핵심 API**:
- `client.session.create()` - 세션 생성
- `client.session.prompt(sessionID, message)` - 프롬프트 전송
- `client.session.abort(sessionID)` - 실행 중단
- `client.session.messages(sessionID)` - 대화 이력 조회
- `client.session.todo(sessionID)` - 실행 계획(Todo) 조회

---

## 4. 도구 실행 모델

### 도구 카테고리

| 카테고리 | 도구 | 설명 |
|----------|------|------|
| 파일 조작 | `read`, `write`, `edit`, `apply_patch` | 파일 읽기/쓰기/편집 |
| 시스템 | `bash` | 셸 명령 실행 |
| 검색 | `find.text`, `find.files`, `find.symbols` | 텍스트/파일/심볼 검색 |
| MCP | 외부 도구 | MCP 서버를 통한 확장 도구 |
| 웹 | HTTP 요청 | 웹 리소스 접근 |

### 실행 흐름

```
사용자 프롬프트
    ↓
LLM 추론 (어떤 도구를 사용할지 계획)
    ↓
도구 실행 (각 단계를 SSE로 스트리밍)
    ↓
권한 검사 (필요 시 permission.asked 이벤트 발생)
    ↓
도구 결과 (LLM에 다시 전달)
    ↓
응답 스트리밍 (SSE로 텍스트 청크 전송)
```

---

## 5. 실시간 이벤트 시스템

### SSE 이벤트 파이프라인

```
OpenCode Engine (이벤트 발생)
    ↓ SSE (/event 엔드포인트)
SDK client.event.subscribe()
    ↓
OpenWork GlobalSDKContext (이벤트 에미터)
    ↓
이벤트 코얼레싱 & 배칭 (16ms 윈도우)
    ↓
SolidJS 리액티브 스토어 (applyEvent)
    ↓
UI 컴포넌트 (리액티비티가 리렌더링 트리거)
```

### 이벤트 타입

| 이벤트 | 설명 |
|--------|------|
| `session.created/updated/deleted` | 세션 생명주기 |
| `session.status` | 상태 변경 (idle → executing) |
| `session.idle` | 실행 완료 |
| `message.updated` | 메시지 업데이트 |
| `message.part.updated` | 응답 스트리밍 (텍스트, 도구 호출 등) |
| `todo.updated` | 실행 계획 변경 |
| `permission.asked/replied` | 권한 요청/응답 |
| `mcp.tools.changed` | 사용 가능한 도구 변경 |

### 이벤트 코얼레싱 (최적화)

같은 타입의 이벤트가 16ms 윈도우 내에 발생하면 하나로 합쳐서 UI 쓰래싱 방지. 핵심 이벤트의 순서는 보존.

---

## 6. 권한 시스템

### 2계층 인가 모델

**1계층 - 폴더 인가 (OpenWork)**:
- 사용자가 네이티브 파일 선택기로 허용 폴더 지정
- 연결 시점에 OpenWork가 검증
- 워크스페이스별 영속 저장

**2계층 - 권한 요청 (OpenCode)**:
- 도구 실행 시 `permission.asked` 이벤트 발생
- 범위 포함: 경로, 도구명, 액션
- 사용자 명시적 응답 필요

### 권한 흐름

```
도구가 리소스 접근 시도
    ↓
OpenCode → permission.asked 이벤트 발생
    ↓
OpenWork UI → 권한 승인 모달 표시
    ↓
사용자 선택: once(이번만) / always(항상) / reject(거부)
    ↓
UI → client.permission.reply(requestID, reply)
    ↓
OpenCode → 응답 수신, 도구 허용/거부
```

---

## 7. MCP(Model Context Protocol) 연동

### 설정 방법

`opencode.json`에서 MCP 서버 정의:

```jsonc
{
  "mcp": {
    "chrome-devtools": {
      "type": "local",
      "command": ["npx", "-y", "chrome-devtools-mcp@latest"]
    }
  }
}
```

### 동작 원리

1. OpenCode가 `opencode.json`에서 MCP 서버 목록 로드
2. 서버 타입: `local`(로컬 프로세스) 또는 `remote`(원격 URL)
3. OpenCode가 MCP 프로세스를 **동적 스폰** 및 관리
4. MCP 서버가 노출하는 도구를 LLM이 사용 가능
5. `tools.deny` 패턴(glob)으로 특정 도구 차단 가능

### 설정 소스 우선순위

1. 프로젝트 설정: `<workspace>/opencode.json` → `mcp.*`
2. 글로벌 설정: `~/.config/opencode/opencode.json` → `mcp.*`
3. 원격 (서버 API 경유)

---

## 8. 설정 시스템

### 3계층 설정

| 계층 | 파일 | 용도 |
|------|------|------|
| OpenCode | `opencode.json` / `opencode.jsonc` | 모델, MCP, 플러그인, 도구 |
| OpenWork Server | `~/.config/openwork/server.json` | 호스트, 포트, 승인 모드 |
| OpenWork Workspace | `.opencode/openwork.json` | 워크스페이스 메타데이터 |

### 설정 해석 우선순위

```
CLI 인수 > 환경 변수 > 파일 설정 > 기본값
```

**주요 환경 변수**:
- `OPENWORK_TOKEN` - 클라이언트 Bearer 토큰
- `OPENWORK_HOST_TOKEN` - 호스트 승인 토큰
- `OPENWORK_PORT` - 서버 포트
- `OPENWORK_APPROVAL_MODE` - manual | auto

---

## 9. 확장 시스템

### 스킬 (Skills)

**탐색 경로** (우선순위 순):
1. `<workspace>/.opencode/skills/`
2. `<workspace>/.claude/skills/` (레거시)
3. `~/.config/opencode/skills/`
4. `~/.claude/skills/`

**스킬 구조**:
```
skill-name/
  SKILL.md    # 프론트매터 + 마크다운 콘텐츠
```

### 플러그인 (Plugins)

`opencode.json`에서 설정:
```jsonc
{
  "plugin": ["opencode-scheduler", "opencode-wakatime"]
}
```

OpenCode가 런타임에 npm 패키지를 동적 로드.

### 커맨드 (Commands)

`.opencode/commands/` 디렉토리에 마크다운 파일로 저장:
```markdown
---
name: "refactor"
description: "TypeScript 코드 리팩토링"
template: "이 파일을 리팩토링: {{filePath}}"
model: "anthropic/claude-3-5-sonnet-20241022"
---
리팩토링 실행 템플릿 내용
```

---

## 10. 보안 모델

### 인증

| 구분 | 방식 | 헤더 |
|------|------|------|
| 클라이언트 인증 | Bearer 토큰 (UUID v4) | `Authorization: Bearer <token>` |
| 호스트 인증 | 호스트 토큰 (UUID v4) | `X-OpenWork-Host-Token: <token>` |

### 폴더 접근 제어

- 승인된 루트 디렉토리 목록(`authorizedRoots`)으로 접근 범위 제한
- 워크스페이스 경로가 승인된 루트의 하위 경로인지 검증
- 모든 파일 조작이 이 범위 내에서만 허용

### 감사 로깅

`.opencode/.audit.jsonl`에 모든 변경 기록:

```typescript
interface AuditEntry {
  id: string;
  workspaceId: string;
  actor: { type: "remote" | "host" };
  action: string;        // config.patch, skills.upsert 등
  target: string;
  summary: string;
  timestamp: number;
}
```

---

## 11. 프롬프트 실행 전체 사이클

```
 1. 사용자: OpenWork UI에서 프롬프트 입력
 2. UI: client.session.prompt(sessionID, message) 호출
 3. SDK: POST /session/:id/prompt (Bearer 토큰)
 4. OpenCode: 프롬프트 수신, LLM 추론 시작
 5. OpenCode: 사용할 도구 결정
 6. OpenCode: 도구 실행 (파일 읽기, bash, MCP 등)
 7. OpenCode: SSE /event 엔드포인트로 각 단계 스트리밍
 8. UI: client.event.subscribe()로 스트림 수신
 9. UI: 이벤트를 SolidJS 스토어에 적용
10. UI: 메시지, Todo, 권한 프롬프트 렌더링
11. 사용자: 실시간 진행 상황 확인 (스트리밍 텍스트)
12. 사용자: 권한 프롬프트에 응답 (허용/거부)
13. UI: client.permission.reply(requestID, reply)
14. OpenCode: 응답 수신, 실행 계속
15. UI: session.idle 이벤트 수신 시 최종 결과 표시
```

---

## 12. 실행 모드

### Host 모드 (데스크톱)

- Tauri(Rust)가 로컬에서 `opencode serve` 프로세스 스폰
- `127.0.0.1:4096`에 바인딩 (자동 포트 감지)
- 엔진 생명주기 전체 관리 (시작/모니터링/종료)

```rust
// Tauri가 sidecar로 번들된 opencode 실행
let command = app.shell().sidecar("opencode")
    .args(["serve", "--hostname", hostname, "--port", port])
    .current_dir(project_dir)
    .spawn();
```

### Client 모드 (원격/모바일)

- 기존 OpenCode 서버에 연결 (URL + Bearer 토큰)
- QR 코드 또는 페어링 토큰으로 접속
- 로컬 엔진 관리 없음
- 원격 모니터링 및 제어

---

## 13. 핵심 데이터 구조

### 메시지 & 파트 모델

**Message**: 대화 교환의 컨테이너
**Part**: 메시지 내 원자 단위 (텍스트, 도구 호출 등)

```typescript
interface Message {
  id: string;
  sessionID: string;
  role: "user" | "assistant";
  tokens: { input: number; output: number; cache: { read: number; write: number } };
}

interface Part {
  id: string;
  messageID: string;
  type: "text" | "tool" | "error" | "system";
  tool?: string;
  state?: { input?: unknown; output?: unknown; diff?: string };
}
```

### SolidJS 상태 스토어

```typescript
const [store, setStore] = createStore<StoreState>({
  sessions: [],
  sessionStatus: {},
  messages: {},        // messageID → Part[]
  parts: {},           // partID → Part
  todos: {},           // sessionID → TodoItem[]
  pendingPermissions: [],
});
```

---

## 14. 핵심 파일 맵

| 컴포넌트 | 경로 | 역할 |
|----------|------|------|
| UI 엔트리 | `packages/app/src/index.tsx` | 웹 UI 진입점 |
| 메인 앱 | `packages/app/src/app/app.tsx` | 핵심 앱 컴포넌트 |
| SDK 컨텍스트 | `packages/app/src/app/context/global-sdk.tsx` | SDK + 이벤트 스트리밍 |
| 세션 스토어 | `packages/app/src/app/context/session.ts` | 세션 상태 관리 |
| Tauri 엔트리 | `packages/desktop/src-tauri/src/main.rs` | 네이티브 셸 진입점 |
| 엔진 관리 | `packages/desktop/src-tauri/src/commands/engine.rs` | OpenCode 시작/종료 |
| 서버 관리 | `packages/desktop/src-tauri/src/openwork_server/` | OpenWork Server 관리 |
| 서버 엔트리 | `packages/server/src/cli.ts` | REST 서버 진입점 |

---

## 요약

OpenCode는 **세션 기반 에이전틱 엔진**으로, HTTP 서버로 독립 실행되며 SSE를 통해 실시간으로 도구 실행 과정을 스트리밍한다. OpenWork는 이를 감싸는 Tauri+SolidJS 기반 데스크톱 앱으로, 터미널 없이도 AI 에이전트 워크플로우를 시각적으로 제어할 수 있게 해준다.

핵심 설계 원칙: **Engine(실행) / Server(설정·승인) / UI(표현)** 의 명확한 관심사 분리.
