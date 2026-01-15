# Confluence 첨부파일 조회 실패 기록

## 날짜
2026-01-15

## 문제
Confluence 페이지에서 첨부파일 목록 조회 시 결과가 반환되지 않음

## 시도한 방법
- `attachments` 서브커맨드로 첨부파일 목록 조회
- REST API endpoint: `/rest/api/content/{page_id}/child/attachment`

## 결과
- 빈 배열 반환 (`"results": []`)
- 에러는 발생하지 않았으나 첨부파일이 있는 페이지에서도 조회되지 않음

## 가능한 원인
1. API 토큰 권한 부족 (첨부파일 읽기 권한)
2. Confluence 버전/에디션별 API 차이
3. 특정 공간(Space)의 권한 설정
4. 첨부파일이 특수한 형태로 저장되어 있을 가능성 (예: Page Properties macro 등)

## 추가 조사 필요
- Confluence 관리자에게 API 권한 확인 요청
- 다른 페이지/공간에서 테스트
- Confluence REST API 문서 재확인

## 구현 상태
- `attachments` 서브커맨드: 구현 완료 (테스트 미완료)
- `download` 서브커맨드: 구현 완료 (테스트 미완료)
