# Codex + Gradle 프로젝트 주의사항

## 문제

Codex를 이용해 Gradle 프로젝트 바이브 코딩 시 별도의 빌드 환경을 생성함:
- `.gradle-user-home/`
- `.gradle/` 등

## 발생 이슈

1. **디스크 공간 부족**: 빌드 캐시가 계속 쌓임
2. **Git diff 오염**: 모든 빌드 파일이 diff에 출력
3. **잘못된 커밋 위험**: 빌드 파일이 실수로 커밋될 수 있음

## 해결책

프로젝트 `.gitignore`에 반드시 추가:

```
.gradle*
```

## 체크리스트

- [ ] `.gitignore`에 `.gradle*` 패턴 추가 확인
- [ ] 기존 커밋된 빌드 파일 있으면 제거
- [ ] 주기적으로 `.gradle-user-home/` 정리
