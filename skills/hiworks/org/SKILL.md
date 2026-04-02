---
name: hiworks-org
description: Hiworks 조직도 트리와 조직 구성원 조회를 안내한다.
---

# Hiworks Org Skill

## When to use

- 조직도 전체 트리를 보고 싶은데 `node_id`를 모를 때
- 특정 조직 또는 하위 조직의 구성원을 조회해야 할 때
- 결재선이나 관리자 리포트 전에 정확한 조직 `node_id`를 확인해야 할 때

## Primary commands

```bash
hiworks org tree
hiworks org members --node-id 639
hiworks org members --node-id-with-child 639 --name-like 조희권
```

## Workflow

```bash
hiworks org tree
hiworks org members --node-id 639
hiworks org members --node-id-with-child 639 --name-like 조희권
```

## Rules

- `node_id`를 모르면 항상 `org tree`부터 실행합니다.
- 특정 부서 하위 전체를 포함하려면 `--node-id-with-child`를 사용합니다.
- `admin employees-export --node-id ...` 같은 후속 작업은 여기서 확인한 `node_id`를 사용합니다.
