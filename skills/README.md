# NDS Skills

NDS 프로젝트의 Claude Code 스킬 모음입니다.

## 환경 변수 설정

환경 변수가 필요한 스킬을 사용하기 전에 아래 환경 변수를 설정해야 합니다.

### 필수 환경 변수 목록

| 스킬 | 환경 변수 | 설명 |
|------|----------|------|
| **Confluence** | `CONFLUENCE_BASE_URL` | Confluence 서버 베이스 URL (**필수**) |
| | `ATLASSIAN_OAUTH_ACCESS_TOKEN` | OAuth 액세스 토큰 (인증 방법 1) |
| | `CONFLUENCE_USERNAME` | 사용자명 (인증 방법 2) |
| | `CONFLUENCE_API_TOKEN` | API 토큰 (인증 방법 2) |
| | `ATLASSIAN_EMAIL` | 이메일 (인증 방법 3) |
| | `ATLASSIAN_API_TOKEN` | Atlassian API 토큰 (인증 방법 3) |
| | `CONFLUENCE_SPACES_FILTER` | 검색 대상 space 제한 (쉼표 구분, 선택) |
| **Elasticsearch** | `LDAP_USER` | LDAP 사용자 ID (**필수**, nginx Basic Auth) |
| | `LDAP_PWD` | LDAP 비밀번호 (**필수**) |
| | `KIBANA_USER` | Kibana 로그인 사용자 (기본값: `developer`) |
| | `KIBANA_PWD` | Kibana 로그인 비밀번호 (기본값: 내부 설정값) |
| | `KIBANA_URL` | Kibana 서버 URL (기본값: 내부 설정값) |
| | `KIBANA_SPACE` | 기본 Kibana space (기본값: `kubernetes`) |
| | `KIBANA_INDEX_PATTERN` | 기본 인덱스 패턴 ID (기본값: 내부 설정값) |
| | `KIBANA_SSL_VERIFY` | SSL 인증서 검증 여부 (기본값: `false`) |
| **Figma** | `FIGMA_OAUTH_TOKEN` | OAuth 토큰 (인증 방법 1) |
| | `FIGMA_API_KEY` | API 키 (인증 방법 2) |
| **GitLab Issues** | `GITLAB_TOKEN` | GitLab 액세스 토큰 (**필수**) |
| | `GITLAB_API_URL` | GitLab API URL (기본값: `https://gitlab.gabia.com/api/v4`) |
| **GitLab MR** | `GITLAB_TOKEN` | GitLab 액세스 토큰 (**필수**) |
| | `GITLAB_API_URL` | GitLab API URL (기본값: `https://gitlab.gabia.com/api/v4`) |
| **Mattermost** | `MATTERMOST_TOKEN` | Mattermost 액세스 토큰 (**필수**) |
| | `MATTERMOST_API_URL` | API URL (기본값: `https://mattermost.gabia.com/api/v4`) |
| | `MATTERMOST_BOARDS_API_URL` | Boards API URL (기본값: `https://mattermost.gabia.com/plugins/focalboard/api/v2`) |
| **Memory** | `MEMORY_FILE_PATH` | 지식 그래프 저장 경로 (기본값: `./memory.json`) |
| **Sentry** | `SENTRY_TOKEN` | Sentry Auth Token (**필수**, `event:read` 스코프) |
| | `SENTRY_API_URL` | Sentry API URL (기본값: `https://sentry.gabia.io:9000`) |
| | `SENTRY_ORG` | Sentry 조직 slug (기본값: `sentry-gabia`) |
| | `SENTRY_SSL_VERIFY` | SSL 인증서 검증 여부 (기본값: `false`) |
| **Oracle** | `ORACLE_HOST` | Oracle DB 호스트 (**필수**) |
| | `ORACLE_USERNAME` | Oracle DB 사용자명 (**필수**) |
| | `ORACLE_PASSWORD` | Oracle DB 비밀번호 (**필수**) |
| | `ORACLE_PORT` | Oracle DB 포트 (기본값: `1521`) |
| | `ORACLE_SID` | Oracle SID (기본값: `DEVGABIA`) |
| | `ORACLE_SERVICE_NAME` | Oracle 서비스명 (선택, SID 대신 사용) |
| | `ORACLE_JDBC_JAR` | ojdbc jar 경로 (선택, 기본: `~/.gradle/caches/`에서 자동 탐색) |
| **MySQL** | `MYSQL_ACCOUNTS` | 다중 계정 JSON (배열 또는 객체) |
| | `MYSQL_DEFAULT_ACCOUNT` | 기본 계정명 (다중 계정 시) |
| | `MYSQL_DEFAULT_SCHEMA` | 기본 스키마 |
| | `MYSQL_HOST` | MySQL 호스트 (단일 계정 시 **필수**) |
| | `MYSQL_USERNAME` | MySQL 사용자명 (단일 계정 시 **필수**) |
| | `MYSQL_PASSWORD` | MySQL 비밀번호 (단일 계정 시 **필수**) |
| | `MYSQL_PORT` | MySQL 포트 (기본값: `3306`) |
| | `MYSQL_DATABASE` | 기본 DB/스키마 (단일 계정 시) |
| **Hiworks 쪽지** | `HIWORKS_ID` | 사용자 ID (**필수**, 이메일의 @ 앞부분) |
| | `HIWORKS_DOMAIN` | 도메인 (**필수**, 예: `company.com`) |
| | `HIWORKS_PWD` | 비밀번호 (**필수**) |
| | `HIWORKS_OTP_SECRET` | OTP 시크릿 (선택, TOTP 기반) |
| | `HIWORKS_ENV` | 환경 선택 (기본값: `prod`) |

### 인증 방식별 설정 가이드

#### Confluence

`CONFLUENCE_BASE_URL`은 항상 필수이며, 인증은 다음 중 하나의 방식으로 설정하세요:

```bash
# 베이스 URL (필수)
export CONFLUENCE_BASE_URL="https://your-confluence-server"

# 방법 1: OAuth 토큰 (권장)
export ATLASSIAN_OAUTH_ACCESS_TOKEN="your-oauth-token"

# 방법 2: Basic 인증 (사용자명 + API 토큰)
export CONFLUENCE_USERNAME="your-username"
export CONFLUENCE_API_TOKEN="your-api-token"

# 방법 3: Basic 인증 (이메일 + API 토큰)
export ATLASSIAN_EMAIL="your-email@example.com"
export ATLASSIAN_API_TOKEN="your-api-token"

# 선택: 검색 대상 space 제한
export CONFLUENCE_SPACES_FILTER="DEV,OPS"
```

#### Elasticsearch

```bash
# 필수: LDAP 인증
export LDAP_USER="your-ldap-id"
export LDAP_PWD="your-ldap-password"

# 선택 설정
export KIBANA_URL="http://your-kibana-host"
export KIBANA_USER="developer"
export KIBANA_SPACE="kubernetes"
```

#### Figma

```bash
# 방법 1: OAuth 토큰 (권장)
export FIGMA_OAUTH_TOKEN="your-oauth-token"

# 방법 2: API 키
export FIGMA_API_KEY="your-api-key"
```

#### GitLab (Issues & Merge Requests)

```bash
export GITLAB_TOKEN="your-gitlab-token"

# 선택: 사내 GitLab 서버 사용 시 (기본값: https://gitlab.gabia.com/api/v4)
export GITLAB_API_URL="https://your-gitlab-server/api/v4"
```

#### Mattermost

```bash
export MATTERMOST_TOKEN="your-mattermost-token"

# 선택: 사내 Mattermost 서버 사용 시
export MATTERMOST_API_URL="https://your-mattermost-server/api/v4"
export MATTERMOST_BOARDS_API_URL="https://your-mattermost-server/plugins/focalboard/api/v2"
```

#### Sentry

```bash
export SENTRY_TOKEN="your-sentry-token"

# 선택 설정
export SENTRY_API_URL="https://sentry.gabia.io:9000"
export SENTRY_ORG="sentry-gabia"
export SENTRY_SSL_VERIFY="false"
```

#### Oracle

```bash
export ORACLE_HOST="your-oracle-host"
export ORACLE_USERNAME="your-username"
export ORACLE_PASSWORD="your-password"

# 선택 설정
export ORACLE_PORT="1521"           # 기본값: 1521
export ORACLE_SID="DEVGABIA"        # 기본값: DEVGABIA
export ORACLE_SERVICE_NAME=""       # 서비스명 사용 시 설정
export ORACLE_JDBC_JAR=""           # ojdbc jar 경로 (미설정 시 자동 탐색)
```

#### MySQL

다중 계정 예시:

```bash
export MYSQL_ACCOUNTS='[
  {"name":"dev","host":"127.0.0.1","port":3306,"username":"app","password":"secret","database":"app_db"},
  {"name":"report","host":"10.0.0.10","username":"ro","password":"secret","database":"report_db"}
]'
export MYSQL_DEFAULT_ACCOUNT="dev"
export MYSQL_DEFAULT_SCHEMA="app_db"
```

단일 계정 예시:

```bash
export MYSQL_HOST="your-mysql-host"
export MYSQL_USERNAME="your-username"
export MYSQL_PASSWORD="your-password"
export MYSQL_PORT="3306"
export MYSQL_DATABASE="your-db"
```

#### Hiworks 쪽지

```bash
export HIWORKS_ID="your-id"
export HIWORKS_DOMAIN="company.com"
export HIWORKS_PWD="your-password"

# 선택: OTP가 필요한 계정
export HIWORKS_OTP_SECRET="your-otp-secret"
export HIWORKS_ENV="prod"           # prod / dev / stage
```

## 스킬 목록

### Gabia 내부 서비스 연동

| 디렉토리 | 설명 | 환경 변수 필요 |
|---------|------|:---:|
| `gabia-dev-mcp-confluence` | Confluence 페이지 검색/조회/생성/수정/삭제/댓글 관리 | O |
| `gabia-dev-mcp-elasticsearch` | Kibana API 통한 Elasticsearch 로그 검색/조회 | O |
| `gabia-dev-mcp-figma` | Figma 파일/노드 JSON 조회, PNG/SVG 다운로드 | O |
| `gabia-dev-mcp-gitlab-issues` | GitLab 이슈 생성/조회/수정/삭제, 토론/노트 관리 | O |
| `gabia-dev-mcp-gitlab-merge-requests` | GitLab MR 조회/변경사항/토론 수집 및 MR 생성 | O |
| `gabia-dev-mcp-mattermost` | Mattermost 포스트/파일 검색, 팀/채널/사용자 조회, Boards 카드 조회 | O |
| `gabia-dev-mcp-memory` | 로컬 JSONL 지식 그래프에 엔터티/관계/관찰 저장/검색 | - |
| `gabia-dev-mcp-mysql` | MySQL 연결 테스트 및 읽기 전용 쿼리 실행 | O |
| `gabia-dev-mcp-oracle` | Oracle DB 연결 테스트 및 SELECT 쿼리 실행 | O |
| `gabia-dev-mcp-sentry` | Sentry 이슈 검색/조회, 이벤트/스택트레이스 조회, 상태 변경 | O |
| `hiworks-memo` | Hiworks 쪽지 목록/상세 조회, 읽지 않은 쪽지 수 확인 | O |
| `board-resolver` | Mattermost Boards 이슈 분석 및 해결방안 제시 | O (간접) |

### 개발 도구

| 디렉토리 | 설명 | 환경 변수 필요 |
|---------|------|:---:|
| `code-simplifier` | 코드 단순화 및 리팩토링 | - |
| `git-worktree` | Git worktree 기반 독립 작업 환경 관리 | - |
| `mac-cron` | Mac launchd 기반 크론 작업 관리 | - |
| `mcp-builder` | MCP 서버 생성 가이드 | - |
| `skill-creator` | 새로운 스킬 생성 가이드 | - |
| `webapp-testing` | Playwright 기반 웹앱 테스트 | - |
| `web-artifacts-builder` | 멀티 컴포넌트 HTML artifact 빌드 도구 | - |

### 문서/콘텐츠 도구

| 디렉토리 | 설명 | 환경 변수 필요 |
|---------|------|:---:|
| `doc-coauthoring` | 문서 공동 작성 워크플로우 가이드 | - |
| `docx` | Word 문서 생성/편집/분석 | - |
| `internal-comms` | 사내 커뮤니케이션 문서 작성 | - |
| `pdf` | PDF 텍스트 추출, 생성, 병합/분할, 폼 처리 | - |
| `pptx` | PowerPoint 프레젠테이션 생성/편집 | - |
| `xlsx` | Excel 스프레드시트 생성/편집/분석 | - |

### UI/디자인 도구

| 디렉토리 | 설명 | 환경 변수 필요 |
|---------|------|:---:|
| `algorithmic-art` | p5.js 기반 알고리즘 아트 생성 | - |
| `brand-guidelines` | Anthropic 브랜드 가이드라인 적용 | - |
| `canvas-design` | 디자인 철학 기반 비주얼 아트 생성 | - |
| `frontend-design` | 프로덕션 수준 프론트엔드 인터페이스 생성 | - |
| `slack-gif-creator` | Slack 최적화 애니메이션 GIF 생성 | - |
| `theme-factory` | 10가지 프리셋 테마 적용 | - |

### 기타

| 디렉토리 | 설명 | 환경 변수 필요 |
|---------|------|:---:|
| `divide-conquer-tasks` | 복잡한 개발 작업 분할정복 관리 | - |
| `work-logger` | 에이전트 작업 완료 기록 자동 저장 | - |
| `dev-plan` | 개발계획서 작성 | - |

## 환경 변수 설정 팁

### 영구 설정 (쉘 프로필에 추가)

```bash
# ~/.bashrc 또는 ~/.zshrc에 추가
export GITLAB_TOKEN="your-token"
export MATTERMOST_TOKEN="your-token"
export SENTRY_TOKEN="your-token"
export LDAP_USER="your-ldap-id"
export LDAP_PWD="your-ldap-password"
# ... 기타 환경 변수
```

### direnv 사용 (프로젝트별 설정)

```bash
# .envrc 파일 생성
export GITLAB_TOKEN="your-token"
export MATTERMOST_TOKEN="your-token"
export SENTRY_TOKEN="your-token"

# direnv 활성화
direnv allow
```

### Claude Code 설정 시

Claude Code의 MCP 설정 시 환경 변수를 함께 지정할 수 있습니다:

```json
{
  "mcpServers": {
    "gitlab-issues": {
      "command": "python",
      "args": ["scripts/gitlab_issue_cli.py"],
      "env": {
        "GITLAB_TOKEN": "your-token"
      }
    }
  }
}
```
