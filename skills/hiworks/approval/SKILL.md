---
name: hiworks-approval
description: Hiworks 전자결재 양식 조회, 결재선 확인, 문서 조회, 기안 초안 생성을 안내한다.
---

# Hiworks Approval Skill

## When to use

- 전자결재 양식과 기본 결재선을 확인해야 할 때
- 임시저장 초안 또는 기안 payload를 만들고 싶을 때
- 내 문서함이나 진행 문서의 상세를 읽고 싶을 때

## Primary commands

```bash
hiworks approval forms list
hiworks approval forms lines --form-id 12 --node-id 127781
hiworks approval draft --form-no 12 --title 기안테스트 --content '<p>본문</p>' --node-id 127781 --mode TEMP --dry-run
hiworks approval my-documents
hiworks approval my-documents --list-status PROGRESS
hiworks approval document-detail --document-id 205408
hiworks approval document-detail --document-id 205408 --with-comments
hiworks approval documents list --list-status PROGRESS
```

## Workflow

```bash
hiworks whoami
hiworks approval forms list
hiworks approval forms lines --form-id 12 --node-id 127781
hiworks approval draft --form-no 12 --title 기안테스트 --content '<p>본문</p>' --node-id 127781 --mode TEMP --dry-run
```

## Rules

- 결재선이 필요한 양식은 먼저 `whoami`와 `forms lines`로 office/user/node 문맥을 확인합니다.
- 기안은 먼저 `draft --dry-run`으로 payload를 확인합니다.
- 현재 계정이 multi-office 제한에 걸릴 수 있으므로 오류 메시지의 hint를 같이 확인합니다.
- approval은 문서/흐름 확인이 중요하므로 reference 스킬과 함께 사용해도 됩니다.
