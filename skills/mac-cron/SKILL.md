---
name: mac-cron
description: Mac launchd 기반 크론 작업 관리 스킬. 크론 등록, 조회, 수정, 삭제, 즉시 실행, 로그 확인 기능 제공. "크론 등록해줘", "스케줄 작업 추가", "매일 10시에 실행", "크론 목록", "크론 삭제", "예약 작업 관리" 등의 요청 시 사용.
---

# Mac Cron Manager

Mac launchd 기반 크론 작업 관리 스킬.

## 데이터 저장 위치

- 메타데이터: `~/.claude/cron/jobs.json`
- 로그: `~/.claude/cron/logs/`
- plist: `~/Library/LaunchAgents/com.claude.cron.*.plist`

## 스크립트 사용법

```bash
python3 scripts/cron_manager.py <command> [options]
```

### 작업 등록 (add)

```bash
python3 scripts/cron_manager.py add <job_id> \
  --cmd "실행할 명령어" \
  --schedule "스케줄" \
  --workdir "/작업/디렉토리" \
  --desc "설명"
```

**스케줄 형식:**
| 형식 | 설명 | 예시 |
|------|------|------|
| `HH:MM` | 매일 지정 시간 | `10:30` |
| `요일 HH:MM` | 매주 특정 요일 | `mon 09:00` |
| `일 HH:MM` | 매월 특정 일 | `15 10:30` |
| `interval:초` | N초마다 반복 | `interval:300` |

**요일**: sun, mon, tue, wed, thu, fri, sat

**예시:**
```bash
# 매일 18:00에 백업
python3 scripts/cron_manager.py add daily-backup \
  --cmd "tar -czf ~/backup.tar.gz ~/Documents" \
  --schedule "18:00" \
  --desc "문서 백업"

# 매주 월요일 09:00에 Claude 커밋
python3 scripts/cron_manager.py add weekly-commit \
  --cmd "claude -p '/commit'" \
  --workdir "/Users/ljs/Project" \
  --schedule "mon 09:00"

# 5분마다 상태 체크
python3 scripts/cron_manager.py add health-check \
  --cmd "curl http://localhost:8080/health" \
  --schedule "interval:300"
```

### 작업 목록 (list)

```bash
python3 scripts/cron_manager.py list
```

### 작업 상세 (get)

```bash
python3 scripts/cron_manager.py get <job_id>
```

### 작업 수정 (update)

```bash
python3 scripts/cron_manager.py update <job_id> \
  --schedule "09:30" \
  --cmd "새 명령어"
```

### 작업 삭제 (remove)

```bash
python3 scripts/cron_manager.py remove <job_id>
```

### 즉시 실행 (run)

```bash
python3 scripts/cron_manager.py run <job_id>
```

### 로그 조회 (logs)

```bash
python3 scripts/cron_manager.py logs <job_id> -n 100
```

## 알림

기본적으로 작업 완료/실패 시 Mac 알림이 발생한다. 비활성화하려면 `--no-notify` 옵션 사용.

## Claude 작업 예시

```bash
# Claude로 매일 커밋
python3 scripts/cron_manager.py add claude-commit \
  --cmd "claude -p '/commit' --dangerously-skip-permissions" \
  --workdir "/Users/ljs/Project/myapp" \
  --schedule "18:00" \
  --desc "일일 자동 커밋"

# Claude로 테스트 실행
python3 scripts/cron_manager.py add claude-test \
  --cmd "claude -p '테스트 실행하고 실패하면 수정해줘'" \
  --workdir "/Users/ljs/Project/myapp" \
  --schedule "mon 10:00"
```
