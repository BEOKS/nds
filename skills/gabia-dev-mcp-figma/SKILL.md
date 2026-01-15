---
name: gabia-dev-mcp-figma
description: Figma API를 직접 호출해 파일/노드 JSON을 조회하고 필요한 노드를 PNG/SVG로 다운로드할 때 사용한다. MCP가 없어도 scripts/figma_cli.py로 수행한다.
---

# Figma Automation

## 제공 기능

- 파일/노드 JSON 조회
- 노드 렌더(PNG/SVG) 및 fill 이미지 다운로드

## 사전 조건(환경변수)

- `FIGMA_API_KEY` 또는 `FIGMA_OAUTH_TOKEN`

## 기본 워크플로우(권장)

1. `python3 scripts/figma_cli.py get`으로 파일 또는 특정 노드를 조회합니다.
2. 필요한 노드 ID / imageRef를 추려 `python3 scripts/figma_cli.py download`로 다운로드합니다.

## 사용 팁

- `fileKey`는 Figma URL의 `/file/<fileKey>/...` 또는 `/design/<fileKey>/...` 부분입니다.
- 큰 파일은 `--node-id`로 범위를 줄입니다.
- 다운로드는 `--nodes-json`에 “JSON 배열”을 넣어 전달합니다.
  - 각 원소는 최소 `fileName`과 (`nodeId` 또는 `imageRef`)가 필요합니다.
  - `fileName`이 `.svg`로 끝나면 SVG 렌더, 그 외는 PNG 렌더로 처리합니다.

## 예시

### 파일/노드 조회

```bash
python3 scripts/figma_cli.py get --file-key AbCdEfGhIjKlMnOp
```

```bash
python3 scripts/figma_cli.py get --file-key AbCdEfGhIjKlMnOp --node-id 1234:5678
```

### 이미지 다운로드(PNG/SVG)

```json
[
  { "nodeId": "1234:5678", "fileName": "icon-search.svg" },
  { "nodeId": "2345:6789", "fileName": "button-primary.png" }
]
```

```bash
python3 scripts/figma_cli.py download \
  --file-key AbCdEfGhIjKlMnOp \
  --local-path ./figma_images \
  --png-scale 2 \
  --nodes-json ./nodes.json
```
