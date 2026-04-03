---
name: hiworks-ai
description: Hiworks AI 앱/세션/메시지/채팅과 보조 UI인 tui, code 사용을 안내한다.
---

# Hiworks AI Skill

## When to use

- 사용 가능한 AI 앱이나 모델 목록을 보고 싶을 때
- 새 세션을 만들고 질문을 보내야 할 때
- 기존 세션 메시지, 제목, 최근 옵션을 확인하거나 수정할 때
- 간단한 interactive 흐름을 `tui`로 사용하거나, 작은 앱 생성 모드를 `code`로 실행할 때

## Primary commands

```bash
hiworks ai models
hiworks ai apps
hiworks ai sessions --limit 10
hiworks ai messages --session-id <session_id> --limit 20
hiworks ai new-session --app-id <app_id>
hiworks ai chat --app-id <app_id> --input '하이웍스 매뉴얼 요약해줘'
hiworks ai session-title --session-id <session_id> --title '휴가 질의'
hiworks ai session-delete --session-id <session_id>
hiworks tui
hiworks code
```

## Workflow

```bash
hiworks ai apps
hiworks ai new-session --app-id <app_id>
hiworks ai chat --app-id <app_id> --input '하이웍스 매뉴얼 요약해줘'
hiworks ai sessions --limit 10
```

## Rules

- 먼저 `apps` 또는 `models`로 현재 사용할 수 있는 선택지를 확인합니다.
- 기존 대화를 이어갈 때는 `session_id`를 명시하고, 새 대화면 `new-session` 또는 `chat --app-id ...`를 사용합니다.
- 빠른 수동 탐색은 `tui`, 작은 자동화 앱/번들 생성은 `code`를 사용합니다.
