# Codex 작업 완료 시 알림 Hook 설정

Codex가 한 턴을 끝낼 때(agent turn complete) 외부 커맨드를 실행하여 알림이나 후처리를 할 수 있다. Claude Code의 hooks와 유사한 기능이지만, 설정 방식이 다르다.

## 동작 원리

`notify` 설정에 명령어 배열을 지정하면, Codex가 실행 시 마지막 인자로 JSON payload를 자동으로 추가한다.

```
cmd arg1 ... '<json>'
```

실행 방식:
- **fire-and-forget**: 완료를 기다리지 않음
- 실패 시 경고 로그만 남김

## JSON Payload 구조

`agent-turn-complete` 이벤트에서 전달되는 JSON에는 다음 필드가 포함된다:

| 필드 | 설명 |
|------|------|
| `thread-id` | 스레드 ID |
| `turn-id` | 턴 ID |
| `cwd` | 현재 작업 디렉토리 |
| `input-messages` | 입력 메시지 |
| `last-assistant-message` | 마지막 어시스턴트 메시지 |

## 설정 방법

`~/.codex/config.toml` 파일에 `notify` 배열을 추가한다. 배열의 각 요소는 argv 토큰 단위이다.

### macOS 알림 예시

```toml
notify = [
  "/usr/bin/osascript",
  "-e", "on run argv",
  "-e", "display notification \"작업이 완료되었습니다.\" with title \"Codex\" sound name \"Glass\"",
  "-e", "end run"
]
```

osascript는 `on run argv ... end run` 형태로 받아서 Codex가 추가하는 JSON 인자를 안전하게 무시/처리할 수 있다.

## 소스 코드 참조

| 파일 | 설명 |
|------|------|
| `codex-rs/core/src/config/mod.rs:161` | notify 설정 키 정의 |
| `codex-rs/core/config.schema.json:278` | 설정 스키마 정의 |
| `codex-rs/core/src/user_notification.rs:11` | 알림 실행 로직 |
| `codex-rs/core/src/user_notification.rs:31` | fire-and-forget 실행 |
| `codex-rs/core/src/user_notification.rs:49` | JSON payload 구조 |
| `docs/config.md:15` | 사용자 문서 엔트리 |

## Claude Code와의 차이점

| 항목 | Claude Code | Codex |
|------|-------------|-------|
| 설정 파일 | `~/.claude/settings.json` | `~/.codex/config.toml` |
| 설정 키 | `hooks` | `notify` |
| 이벤트 종류 | Stop, Notification 등 다양 | agent-turn-complete |
| 데이터 전달 | 환경 변수/stdin | JSON 인자 |
