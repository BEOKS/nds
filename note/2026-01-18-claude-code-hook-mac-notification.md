# Claude Code 작업 완료 시 Mac 알림 받기

Claude Code 에이전트로 작업을 하다 보면 다른 작업을 병행하게 된다. 그러다 보니 에이전트가 권한 승인을 요청하거나 작업이 완료되었을 때 바로 확인하기 어렵다. 터미널을 계속 쳐다보고 있을 수도 없고, 확인이 늦어지면 작업 흐름이 끊긴다.

이 문제는 Claude Code의 **hooks** 기능으로 해결할 수 있다.

## 설정 방법

`~/.claude/settings.json` 파일에 다음 내용을 추가한다:

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"작업이 완료되었습니다.\" with title \"Claude Code\" sound name \"Glass\"'"
          }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "osascript -e 'display notification \"입력이 필요합니다\" with title \"Claude Code\" sound name \"Purr\"'"
          }
        ]
      }
    ]
  }
}
```

## Hook 이벤트 종류

| 이벤트 | 설명 |
|--------|------|
| `Stop` | Claude 메인 작업 완료 시 |
| `Notification` | 권한 요청 등 사용자 입력이 필요할 때 |
| `SessionEnd` | 세션 종료 시 |
| `SubagentStop` | 서브에이전트 작업 완료 시 |

## 사용 가능한 알림 사운드

macOS 기본 제공 사운드: `Glass`, `Purr`, `Bottle`, `Bell`, `Basso`, `Ping`

## 참고

- 설정 파일 위치는 `~/.claude/settings.json` (전역) 또는 `.claude/settings.json` (프로젝트별)
- `/hooks` 명령어로 대화형 설정도 가능
- 다음 Claude Code 세션부터 적용됨
