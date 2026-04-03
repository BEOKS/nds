---
name: hiworks-drive
description: Hiworks 드라이브 파일/폴더 조회, 업로드, 다운로드, 검색, 외부공유, 복사를 안내한다.
---

# Hiworks Drive Skill

## When to use

- 특정 경로의 파일/폴더 목록을 보고 싶을 때
- 파일 업로드나 다운로드를 해야 할 때
- 파일 검색이나 단일 노드 메타데이터 조회가 필요할 때
- 외부공유 링크를 만들거나 설정을 바꿔야 할 때
- 한 폴더로 파일/폴더를 복사해야 할 때

## Primary commands

```bash
hiworks drive list --path /
hiworks drive list --path /documents
hiworks drive search --query 계약서
hiworks drive node-detail <node_id>
hiworks drive info
hiworks drive upload --file ./report.pdf --path /TeamDocs
hiworks drive download --file-id 12345 --output ./downloaded.pdf
hiworks drive share-get <node_id>
hiworks drive share-create <node_id>
hiworks drive share-update <node_id> --permission R
hiworks drive copy <node_id> --target-id <folder_node_id>
hiworks drive copy-recent-targets
```

## Workflow

```bash
hiworks drive list --path /
hiworks drive search --query 계약서
hiworks drive node-detail <node_id>
hiworks drive share-get <node_id>
hiworks drive copy <node_id> --target-id <folder_node_id>
```

## Rules

- 경로를 모르면 먼저 `list` 또는 `search`로 대상을 찾습니다.
- 단일 파일/폴더의 상세 메타데이터는 `node-detail`을 사용합니다.
- 외부공유가 없으면 `share-get`이 실패할 수 있으므로 먼저 `share-create`가 필요할 수 있습니다.
- 복사 대상 폴더가 확실하지 않으면 최근 사용 이력을 `copy-recent-targets`로 확인합니다.
