---
name: hiworks
description: Hiworks CLI 전체 기능 가이드. OAuth 로그인, 메일, 쪽지, 일정, 예약, 업무, 팀 리포트, 게시판, 드라이브, 전자결재, AI, 관리자 기능을 사용할 때 사용한다.
---

# Hiworks Skill Index

`hiworks` CLI 전체 기능을 사용하는 루트 스킬입니다. 설치, 인증, 문서 탐색, 메일/쪽지, 일정/예약, 업무/게시판, 전자결재, 드라이브, AI, 관리자 기능을 한 곳에서 안내합니다.

## 업데이트 기준

- 신규 CLI 기능, 명령 변경, 스킬 문서 업데이트가 필요하면 먼저 Hiworks CLI 원본 저장소를 확인합니다.
- 기준 저장소: `https://gitlab.gabia.com/hiworks/ai/hiworks-cli`

## CLI setup

```bash
hiworks setup
hiworks version
hiworks self-update
```

## 인증 및 상태 확인

```bash
hiworks auth browser-login
hiworks auth status
hiworks whoami
hiworks doctor
```

- 기본 인증 모델은 OAuth Bearer 토큰입니다.
- 프로필이 필요하면 `hiworks --profile gabia ...` 또는 `hiworks --profile dev ...` 형태로 실행합니다.
- 실제 호출 URL이 필요하면 전역 `--trace-http`를 사용합니다.

## 공통 유지보수

```bash
hiworks skills sync --target codex --dest ~/.codex/skills
hiworks refresh
```

## 문서/탐색 명령

- [Reference](./reference/SKILL.md) — `search`, `flow`, `ids`, `capability`, `spec`, `names`
- [Auth](./auth/SKILL.md) — `auth`, `whoami`, `doctor`

## 업무 도메인

- [Memo](./memo/SKILL.md) — 쪽지 조회/전송
- [Mail](./mail/SKILL.md) — 메일함 조회, 읽기, 발송 preflight
- [Booking](./booking/SKILL.md) — 회의실/자원 예약
- [Schedule](./schedule/SKILL.md) — 캘린더/일정 조회
- [Work](./work/SKILL.md) — 휴가/근태 조회 및 신청
- [Contacts](./contacts/SKILL.md) — 사람/계정 검색
- [Org](./org/SKILL.md) — 조직도/구성원 조회
- [Task](./task/SKILL.md) — 업무 앱, 업무 생성/상태변경, 댓글
- [Team](./team/SKILL.md) — 팀 주간 리포트, 자가점검일 업데이트
- [Board](./board/SKILL.md) — 게시판 조회/작성/댓글/좋아요
- [Drive](./drive/SKILL.md) — 드라이브 조회, 업로드, 다운로드, 공유, 복사
- [Approval](./approval/SKILL.md) — 전자결재 양식, 문서 조회, 기안 초안
- [AI](./ai/SKILL.md) — Hiworks AI 앱, 세션, 채팅, `tui`, `code`
- [Admin](./admin/SKILL.md) — 관리자 전용 근태/인사 다운로드 및 보고서

## 개발자 가이드

- [OAuth Guide](./developer/OAUTH_GUIDE.md) — 앱/에이전트에서 Hiworks OAuth를 자체 연동할 때 참고

## 공통 규칙

1. raw ID보다 사람 기준 입력을 우선 사용합니다.
2. state-changing 명령은 먼저 조회 또는 `--dry-run`으로 확인합니다.
3. 실제 반영은 `--yes` 또는 확정 플래그가 있을 때만 진행합니다.
4. JSON을 지원하는 명령은 에이전트가 우선 사용합니다.
5. raw vault 파일을 직접 열기보다 CLI 검색 명령을 먼저 사용합니다.
6. 과거 계정/비밀번호 기반 직접 인증 흐름은 사용하지 않습니다.
