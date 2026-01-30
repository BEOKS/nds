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
- `--with-updater-artifacts`: Tauri Updater 산출물(createUpdaterArtifacts=true) 포함
- `--updater-base-url <url>`: Updater endpoint base URL 주입(예: Nexus 공개 URL)
- `--updater-pubkey <string>` / `--updater-pubkey-file <path>`: Updater 서명 검증용 pubkey 주입

### Windows (MSI 등)

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-openwork-installer.ps1
```

옵션:
- `-Baseline`: opencode baseline 빌드 포함
- `-Target x86_64-pc-windows-msvc`
- `-Bundles msi` (또는 `-Bundles msi,nsis` 등)
- `-OpencodeBin C:\path\to\opencode.exe`: opencode 바이너리 직접 지정
- `-WithUpdaterArtifacts`: Tauri Updater 산출물(createUpdaterArtifacts=true) 포함
- `-UpdaterBaseUrl <url>`: Updater endpoint base URL 주입
- `-UpdaterPubkey <string>` / `-UpdaterPubkeyFile <path>`: Updater 서명 검증용 pubkey 주입

## OpenWork 자동 업데이트 배포(Nexus)

GitLab 프로젝트가 internal(로그인 필요)인 경우, Tauri Updater는 인증 없이 접근 가능한 URL이 필요합니다.
따라서 업데이트 산출물은 Nexus raw-repository(공개 접근 가능)로 업로드하는 구성이 가장 단순합니다.

### 업로드 구조(기본)

- `https://repo.gabia.com/repository/raw-repository/nds/openwork-updater/<platform>/latest.json`
- `https://repo.gabia.com/repository/raw-repository/nds/openwork-updater/<platform>/<update-file>`

`<platform>` 예: `darwin-aarch64`, `darwin-x86_64`, `windows-x86_64`

### 수동 업로드(로컬/CI 공용)

macOS:

```bash
node ./scripts/publish-openwork-updater.node.js --bundle-dir <.../bundle>
```

Windows:

```powershell
node .\scripts\publish-openwork-updater.node.js --bundle-dir <...\bundle>
```

### GitLab CI

`gitlab-ci.openwork.yml`을 참고해 레포 루트의 `.gitlab-ci.yml`로 구성하세요.

필수 CI 변수(Protected/Masked 권장):
- `NDS_NEXUS_USERNAME`, `NDS_NEXUS_PASSWORD`
- `TAURI_PRIVATE_KEY`, `TAURI_KEY_PASSWORD`
- `OPENWORK_UPDATER_PUBKEY`
