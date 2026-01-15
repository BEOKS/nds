---
name: gabia-dev-mcp-memory
description: 로컬 JSONL 지식 그래프 파일에 엔터티/관계/관찰을 저장·검색·열람·삭제할 때 사용한다. MCP 없이 scripts/memory_cli.py로 수행한다.
---

# Memory (Knowledge Graph)

## 제공 기능

- 엔터티/관계 생성
- 관찰 추가
- 전체 그래프 읽기, 검색(search), 이름으로 열기(open)
- 엔터티/관찰/관계 삭제

## 사전 조건(환경변수)

- (선택) `MEMORY_FILE_PATH`: 저장 파일 경로
  - 미지정 시 기본 `./memory.json` 사용
  - 상대경로는 현재 작업 디렉터리 기준

## 기본 워크플로우(권장)

1. `python3 scripts/memory_cli.py create-entities`로 엔터티를 만듭니다.
2. `add-observations`로 관찰(노하우/규칙/링크)을 누적합니다.
3. `create-relations`로 엔터티 간 관계를 추가합니다(능동태 권장).
4. 찾을 때는 `search-nodes`로 검색하고 `open-nodes`로 상세를 봅니다.
5. 정리는 `delete-*` 명령으로 수행합니다.

## 작성 규칙(권장)

- 엔터티 `name`은 안정적인 키로 사용합니다(띄어쓰기 대신 하이픈 권장).
- `entityType`은 분류용 문자열입니다(예: `doc`, `service`, `runbook`, `team` 등).
- `relationType`은 “능동태”로 씁니다(예: `references`, `depends_on`, `owned_by`).

## 예시

### 엔터티 생성

```bash
cat <<'JSON' | python3 scripts/memory_cli.py create-entities
{
  "entities": [
    {
      "name": "gabia-logging-guide",
      "entityType": "doc",
      "observations": [
        "Sentry 이슈 링크는 MR 본문에 첨부",
        "Kibana 쿼리는 팀 공통 DSL 사용"
      ]
    }
  ]
}
JSON
```

### 관계 생성

```bash
cat <<'JSON' | python3 scripts/memory_cli.py create-relations
{
  "relations": [
    { "from": "gabia-logging-guide", "to": "Sentry", "relationType": "references" }
  ]
}
JSON
```

### 관찰 추가 + 검색/열람

```bash
cat <<'JSON' | python3 scripts/memory_cli.py add-observations
{
  "observations": [
    { "entityName": "gabia-logging-guide", "contents": ["Error budget은 월별 99.9% 초과 시 알림"] }
  ]
}
JSON
```

```bash
python3 scripts/memory_cli.py search-nodes --query Sentry
```

```bash
python3 scripts/memory_cli.py open-nodes --names gabia-logging-guide
```
