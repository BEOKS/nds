# NDS Skills

NDS 프로젝트의 MCP 스킬 모음입니다.

## 환경 변수 설정

각 스킬을 사용하기 전에 아래 환경 변수를 설정해야 합니다.

### 필수 환경 변수 목록

| 스킬 | 환경 변수 | 설명 |
|------|----------|------|
| **Confluence** | `ATLASSIAN_OAUTH_ACCESS_TOKEN` | OAuth 액세스 토큰 (권장) |
| | `CONFLUENCE_API_TOKEN` | API 토큰 (Basic 인증 시) |
| | `ATLASSIAN_API_TOKEN` | Atlassian API 토큰 (대체) |
| | `CONFLUENCE_USERNAME` | 사용자명 (Basic 인증 시 필요) |
| | `ATLASSIAN_EMAIL` | 이메일 (Basic 인증 시 대체) |
| **Figma** | `FIGMA_OAUTH_TOKEN` | OAuth 토큰 (권장) |
| | `FIGMA_API_KEY` | API 키 (대체) |
| **GitLab Issues** | `GITLAB_TOKEN` | GitLab 액세스 토큰 (**필수**) |
| **GitLab MR** | `GITLAB_TOKEN` | GitLab 액세스 토큰 (**필수**) |
| **Mattermost** | `MATTERMOST_TOKEN` | Mattermost 액세스 토큰 (**필수**) |
| **Oracle** | `ORACLE_PASSWORD` | Oracle DB 비밀번호 (**필수**) |
| | `ORACLE_HOST` | Oracle DB 호스트 (**필수**) |
| | `ORACLE_USERNAME` | Oracle DB 사용자명 (**필수**) |
| | `ORACLE_PORT` | Oracle DB 포트 (기본값: 1521) |
| | `ORACLE_SID` | Oracle SID (기본값: DEVGABIA) |
| | `ORACLE_SERVICE_NAME` | Oracle 서비스명 (선택) |

### 인증 방식별 설정 가이드

#### Confluence

다음 중 하나의 방식으로 인증을 설정하세요:

```bash
# 방법 1: OAuth 토큰 (권장)
export ATLASSIAN_OAUTH_ACCESS_TOKEN="your-oauth-token"

# 방법 2: Basic 인증 (사용자명 + API 토큰)
export CONFLUENCE_USERNAME="your-username"
export CONFLUENCE_API_TOKEN="your-api-token"

# 방법 3: Basic 인증 (이메일 + API 토큰)
export ATLASSIAN_EMAIL="your-email@example.com"
export ATLASSIAN_API_TOKEN="your-api-token"
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

# 선택: 사내 Mattermost 서버 사용 시 (기본값: https://mattermost.gabia.com/api/v4)
export MATTERMOST_API_URL="https://your-mattermost-server/api/v4"
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
```

## 스킬 목록

| 디렉토리 | 설명 |
|---------|------|
| `gabia-dev-mcp-confluence` | Confluence 페이지 관리 |
| `gabia-dev-mcp-figma` | Figma 디자인 파일 접근 |
| `gabia-dev-mcp-gitlab-issues` | GitLab 이슈 관리 |
| `gabia-dev-mcp-gitlab-merge-requests` | GitLab MR 관리 |
| `gabia-dev-mcp-mattermost` | Mattermost 메시지/채널 관리 |
| `gabia-dev-mcp-memory` | 메모리 기반 데이터 저장 |
| `gabia-dev-mcp-oracle` | Oracle DB 쿼리 실행 |
| `pptx` | PowerPoint 파일 처리 |

## 환경 변수 설정 팁

### 영구 설정 (쉘 프로필에 추가)

```bash
# ~/.bashrc 또는 ~/.zshrc에 추가
export GITLAB_TOKEN="your-token"
export MATTERMOST_TOKEN="your-token"
# ... 기타 환경 변수
```

### direnv 사용 (프로젝트별 설정)

```bash
# .envrc 파일 생성
export GITLAB_TOKEN="your-token"
export MATTERMOST_TOKEN="your-token"

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
