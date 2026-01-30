# Scripts

## Skills 설치

프로젝트의 `skills/`를 에이전트별 디렉토리로 복사합니다.

```bash
# 기본 설치 (codex)
./scripts/setup-skills.sh

# 특정 에이전트만 설치 (복수 지정 가능)
./scripts/setup-skills.sh --agent claude,codex

# 지원 에이전트 전체 설치
./scripts/setup-skills.sh --all

# 기존 파일 덮어쓰기
./scripts/setup-skills.sh -f

# 미리보기 (실제 복사 안 함)
./scripts/setup-skills.sh -n
```

지원 에이전트: `claude`, `codex`, `gemini`

## OpenWork 설치 파일 빌드

로컬 `opencode/` + `openwork/` 소스를 빌드하고, `opencode`를 OpenWork(Tauri) sidecar로 포함해 단일 설치 파일을 생성합니다.

### macOS (DMG)

```bash
./scripts/build-openwork-installer.sh
```

옵션:
- `--baseline`: opencode baseline 빌드 포함(가능 시 baseline 바이너리 우선 사용)
- `--target aarch64-apple-darwin|x86_64-apple-darwin`
- `--opencode-bin /path/to/opencode`: opencode 바이너리 직접 지정
- `--dmg-skip-jenkins`: DMG 생성 시 Finder/AppleScript 단계를 건너뜀(헤드리스/권한 제한 환경용)

### Windows (MSI 등)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-openwork-installer.ps1
```

옵션:
- `-Baseline`: opencode baseline 빌드 포함
- `-Target x86_64-pc-windows-msvc`
- `-Bundles msi` (또는 `-Bundles msi,nsis` 등)
- `-OpencodeBin C:\path\to\opencode.exe`: opencode 바이너리 직접 지정
