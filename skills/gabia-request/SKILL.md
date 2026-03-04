---
name: gabia-request
description: gabiarequest GitLab 프로젝트(`devops/gabiarequest`)에 운영/배포/DB/k8s/방화벽/접속 요청 이슈를 등록할 때 사용한다. 템플릿 기반 본문 작성, 초기 라벨 규칙(`1. 승인 중`, `11시 배포`, `긴급`, `18시 배포/18시 이후 요청`) 적용, DDL 18시 이후 제약 검증이 필요할 때 트리거한다.
---

# gabia-request

## 개요

이 스킬은 `devops/gabiarequest` 이슈를 표준 템플릿으로 생성하고, 초기 라벨 및 배포 시간 규칙을 자동으로 반영한다.  
GitLab 연동은 기존 스킬 `gabia-dev-mcp-gitlab-issues`의 CLI를 재사용한다.
또한 사용자 교정 사항(운영 룰)을 `instruction.md`에 누적해 이후 요청부터 동일하게 반영한다.

## 기본 워크플로우

1. 요청 유형을 결정한다 (`deploy`, `db`, `request`, `k8s`, `firewall`, `new-server`, `server-access`, `oracle-sync`).
2. `instruction.md`를 먼저 확인해 누적된 운영 룰을 적용한다.
3. 템플릿을 로드한다.
   - `references/templates/*.md`에서만 로드한다.
4. 초기 라벨 정책을 적용한다.
   - 기본: `1. 승인 중`
   - 11시 배포: `11시 배포`
   - 긴급 요청: `긴급`
   - 18시 이후 배포: `18시 배포` 우선, 없으면 `18시 이후 요청`으로 매핑
5. DDL 요청 검증을 수행한다.
   - `db` + `ddl` 요청은 `18시 이후` 배포만 허용한다.
6. `gitlab_issue_cli.py create`를 호출해 이슈를 생성한다.

## 사용자 교정 누적 규칙

- 사용자가 요청 작성 방식/검증 규칙을 교정하면 같은 턴에서 즉시 `instruction.md`를 갱신한다.
- 교정 내용은 기존 규칙과 충돌할 수 있으므로, 동일 주제에서는 가장 최근 항목을 우선 적용한다.
- 신규 항목은 아래 4개 필드를 유지해 추가한다.
  - 날짜
  - 상황
  - 규칙
  - 적용 방법
- 이슈 생성 시 템플릿 작성 전에 `instruction.md`의 규칙을 체크리스트처럼 순차 반영한다.

## 이슈 생성 명령

### 권장(헬퍼 스크립트 사용)

```bash
python3 skills/gabia-request/scripts/create_gabia_request_issue.py \
  --title "gadmin.gabia.com 배포 요청의 건" \
  --template deploy \
  --deploy-hour 11
```

### 긴급 + 18시 이후 배포

```bash
python3 skills/gabia-request/scripts/create_gabia_request_issue.py \
  --title "gcron 배포 요청" \
  --template deploy \
  --deploy-hour 18 \
  --urgent
```

### DDL 요청(18시 이후 강제)

```bash
python3 skills/gabia-request/scripts/create_gabia_request_issue.py \
  --title "차세대클라우드 QA 환경 DB DDL 요청" \
  --template db \
  --db-kind ddl \
  --deploy-hour 18
```

### 실행 전 검증만 수행(dry-run)

```bash
python3 skills/gabia-request/scripts/create_gabia_request_issue.py \
  --title "DNS 설정 요청" \
  --template request \
  --dry-run
```

## 직접 GitLab CLI를 써야 하는 경우

헬퍼 스크립트 대신 아래 CLI를 직접 호출할 수 있다.

```bash
python3 skills/gabia-dev-mcp-gitlab-issues/scripts/gitlab_issue_cli.py create \
  --project-id devops/gabiarequest \
  --title "요청 제목" \
  --description-file /path/to/request.md \
  --labels "1. 승인 중"
```

## 참고 자료

- 템플릿 스냅샷: `references/templates/*.md`
- 사용자 교정 누적: `instruction.md`
- 자동화 스크립트: `scripts/create_gabia_request_issue.py`
