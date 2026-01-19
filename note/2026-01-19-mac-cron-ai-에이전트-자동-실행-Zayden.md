# Mac Cron으로 AI 에이전트 자동 실행하기

> 작성자: Zayden

AI 에이전트는 기본적으로 사용자가 요청해야 실행된다. 사용자 주도형 구조다. 하지만 반복적인 작업은 자동화하고 싶다. 매주 주간보고를 작성하거나, 매일 코드를 정리하거나, 정기적으로 문서를 업데이트하는 일들이 그렇다.

**mac-cron** 스킬은 이 문제를 해결한다. Mac의 launchd를 활용해 특정 시간에 Claude 명령을 자동 실행할 수 있다.

## 실제 활용 예시

### 주간보고 자동 작성

매주 목요일 11시에 주간회의가 있다. 회의 전에 일주일간 작업 내역을 정리해야 한다. 이걸 10시 30분에 자동화하면:

```bash
python3 skills/mac-cron/scripts/cron_manager.py add weekly-report \
  --cmd "claude -p '이번 주 git 커밋 내역을 분석해서 주간보고 형식으로 정리하고 Confluence에 업데이트해줘' --dangerously-skip-permissions" \
  --workdir "/Users/leejs/Project/myapp" \
  --schedule "thu 10:30" \
  --desc "주간보고 자동 작성"
```

### 일일 코드 커밋

매일 퇴근 전에 작업 내용을 커밋하는 습관이 있다면:

```bash
python3 skills/mac-cron/scripts/cron_manager.py add daily-commit \
  --cmd "claude -p '/commit' --dangerously-skip-permissions" \
  --workdir "/Users/leejs/Project/myapp" \
  --schedule "18:00" \
  --desc "일일 자동 커밋"
```

### 테스트 자동 실행

매주 월요일 아침에 전체 테스트를 돌리고 실패 시 수정까지:

```bash
python3 skills/mac-cron/scripts/cron_manager.py add weekly-test \
  --cmd "claude -p '테스트 실행하고 실패하면 수정해줘' --dangerously-skip-permissions" \
  --workdir "/Users/leejs/Project/myapp" \
  --schedule "mon 09:00" \
  --desc "주간 테스트 및 버그 수정"
```

## 스케줄 형식

| 형식 | 설명 | 예시 |
|------|------|------|
| `HH:MM` | 매일 지정 시간 | `10:30` |
| `요일 HH:MM` | 매주 특정 요일 | `thu 10:30` |
| `일 HH:MM` | 매월 특정 일 | `15 10:30` |
| `interval:초` | N초마다 반복 | `interval:300` |

요일: `sun`, `mon`, `tue`, `wed`, `thu`, `fri`, `sat`

## 주요 명령어

```bash
# 등록된 작업 목록
python3 scripts/cron_manager.py list

# 작업 상세 정보
python3 scripts/cron_manager.py get weekly-report

# 즉시 실행 (테스트용)
python3 scripts/cron_manager.py run weekly-report

# 로그 확인
python3 scripts/cron_manager.py logs weekly-report -n 50

# 작업 삭제
python3 scripts/cron_manager.py remove weekly-report
```

## 데이터 저장 위치

- 메타데이터: `~/.claude/cron/jobs.json`
- 로그: `~/.claude/cron/logs/`
- plist: `~/Library/LaunchAgents/com.claude.cron.*.plist`

## 주의사항

1. **`--dangerously-skip-permissions`**: 자동 실행 시 권한 승인 프롬프트를 건너뛴다. 신뢰할 수 있는 명령어에만 사용해야 한다.

2. **작업 디렉토리**: `--workdir` 옵션으로 Claude가 실행될 프로젝트 경로를 반드시 지정한다.

3. **로그 확인**: 자동 실행 결과는 `logs` 명령어로 확인할 수 있다. 문제 발생 시 디버깅에 필요하다.

4. **Mac 알림**: 기본적으로 작업 완료/실패 시 Mac 알림이 발생한다. `--no-notify` 옵션으로 비활성화 가능.

## 활용 아이디어

- **문서 자동 동기화**: 코드 변경 시 API 문서 자동 업데이트
- **정기 코드 리뷰**: 매주 코드 품질 분석 리포트 생성
- **백업 자동화**: 매일 중요 파일 백업
- **모니터링**: 5분마다 서버 상태 체크 및 이상 시 알림
- **일일 스탠드업 준비**: 매일 아침 어제 작업 내역 요약
