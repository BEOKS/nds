$ErrorActionPreference = "Stop"

<#
  build-openwork-installer.ps1 - 로컬 opencode + openwork를 빌드해 Windows 설치 파일(MSI 등)을 생성합니다.

  사용법:
    powershell -ExecutionPolicy Bypass -File .\scripts\build-openwork-installer.ps1
#>

param(
  [string]$Target = "",
  [string]$Bundles = "msi",
  [switch]$Baseline,
  [string]$OpencodeBin = "",
  [switch]$WithUpdaterArtifacts,
  [switch]$NoFrozenLockfile
)

function Die($Message) {
  Write-Host "오류: $Message" -ForegroundColor Red
  exit 1
}

function Need-Cmd($Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    Die "'$Name' 명령을 찾을 수 없습니다."
  }
}

if (-not $IsWindows) {
  Die "이 스크립트는 Windows에서만 실행 가능합니다."
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir "..") | Select-Object -ExpandProperty Path

$openworkDir = Join-Path $projectRoot "openwork"
$opencodeDir = Join-Path $projectRoot "opencode"
$opencodePkgDir = Join-Path $opencodeDir "packages\\opencode"
$openworkDesktopDir = Join-Path $openworkDir "packages\\desktop"
$openworkTauriConf = Join-Path $openworkDesktopDir "src-tauri\\tauri.conf.json"
$openworkSidecarsDir = Join-Path $openworkDesktopDir "src-tauri\\sidecars"

if (-not (Test-Path $openworkDir) -or -not (Test-Path $opencodeDir)) {
  Die "submodule(openwork/opencode) 디렉토리를 찾을 수 없습니다. (힌트: git submodule update --init --recursive)"
}

$hostTarget = "x86_64-pc-windows-msvc"
$hostArch = $env:PROCESSOR_ARCHITECTURE
if ($hostArch -ne "AMD64") {
  Die "현재 아키텍처($hostArch)는 지원하지 않습니다. (현재 스크립트는 x64(AMD64)만 지원)"
}

if ([string]::IsNullOrWhiteSpace($Target)) {
  $Target = $hostTarget
}

Write-Host "=== OpenWork 설치 파일 빌드(Windows) ===" -ForegroundColor Green
Write-Host "프로젝트 루트: $projectRoot"
Write-Host "타겟: $Target"
Write-Host "번들: $Bundles"
Write-Host ""

Need-Cmd bun
Need-Cmd pnpm
Need-Cmd node
Need-Cmd cargo

if ([string]::IsNullOrWhiteSpace($OpencodeBin)) {
  if ($Target -ne $hostTarget) {
    Die "현재 머신($hostTarget)과 다른 타겟($Target)으로 opencode를 자동 빌드할 수 없습니다. (-OpencodeBin으로 해당 타겟 바이너리를 직접 지정하세요.)"
  }

  if (-not (Test-Path $opencodePkgDir)) {
    Die "opencode 패키지 경로를 찾을 수 없습니다: $opencodePkgDir"
  }

  Write-Host "[1/3] opencode 빌드" -ForegroundColor Green
  Push-Location $opencodePkgDir
  bun install | Out-Host
  if ($Baseline) {
    bun run build --single --baseline | Out-Host
  }
  else {
    bun run build --single | Out-Host
  }
  Pop-Location

  $distRoot = Join-Path $opencodePkgDir "dist"
  if (-not (Test-Path $distRoot)) {
    Die "opencode dist 디렉토리를 찾을 수 없습니다: $distRoot"
  }

  $candidateList = @()
  if ($Baseline) {
    $candidateList += (Join-Path $distRoot "opencode-windows-x64-baseline\\bin\\opencode.exe")
    $candidateList += (Join-Path $distRoot "opencode-windows-x64-baseline\\bin\\opencode")
  }
  $candidateList += (Join-Path $distRoot "opencode-windows-x64\\bin\\opencode.exe")
  $candidateList += (Join-Path $distRoot "opencode-windows-x64\\bin\\opencode")

  $OpencodeBin = $candidateList | Where-Object { Test-Path $_ } | Select-Object -First 1

  if ([string]::IsNullOrWhiteSpace($OpencodeBin)) {
    $OpencodeBin = Get-ChildItem -Path $distRoot -Recurse -File -ErrorAction SilentlyContinue |
      Where-Object { $_.Name -in @("opencode.exe", "opencode") } |
      Select-Object -First 1 -ExpandProperty FullName
  }
}

if ([string]::IsNullOrWhiteSpace($OpencodeBin) -or -not (Test-Path $OpencodeBin)) {
  Die "opencode 바이너리를 찾을 수 없습니다. (-OpencodeBin C:\\path\\to\\opencode.exe)"
}

Write-Host "[2/3] OpenWork sidecar 준비" -ForegroundColor Green
New-Item -ItemType Directory -Force -Path $openworkSidecarsDir | Out-Null

$sidecarTargetPath = Join-Path $openworkSidecarsDir ("opencode-$Target.exe")
Copy-Item -Force -Path $OpencodeBin -Destination $sidecarTargetPath
Write-Host "opencode sidecar: $sidecarTargetPath"
Write-Host ""

Write-Host "[3/3] OpenWork(Tauri) 빌드" -ForegroundColor Green
if (-not (Test-Path $openworkTauriConf)) {
  Die "OpenWork tauri.conf.json을 찾을 수 없습니다: $openworkTauriConf"
}

$tauriConfPath = $openworkTauriConf
$tempConf = $null
if (-not $WithUpdaterArtifacts) {
  $tempConf = Join-Path ([System.IO.Path]::GetTempPath()) ("openwork-tauri-conf-" + [Guid]::NewGuid().ToString() + ".json")
  $config = Get-Content -Raw $openworkTauriConf | ConvertFrom-Json
  if (-not $config.bundle) {
    $config | Add-Member -NotePropertyName bundle -NotePropertyValue (@{})
  }
  $config.bundle.createUpdaterArtifacts = $false
  $config | ConvertTo-Json -Depth 100 | Set-Content -Path $tempConf -Encoding UTF8
  $tauriConfPath = $tempConf
}

Push-Location $openworkDir
if ($NoFrozenLockfile) {
  pnpm install | Out-Host
}
else {
  pnpm install --frozen-lockfile | Out-Host
}

pnpm --filter @different-ai/openwork exec tauri build `
  --config "$tauriConfPath" `
  --target "$Target" `
  --bundles "$Bundles" | Out-Host
Pop-Location

if ($tempConf -and (Test-Path $tempConf)) {
  Remove-Item -Force $tempConf
}

$bundleDir = Join-Path $openworkDesktopDir ("src-tauri\\target\\$Target\\release\\bundle")
Write-Host ""
Write-Host "✅ 완료! 생성된 설치 파일/번들 후보:" -ForegroundColor Green
if (Test-Path $bundleDir) {
  Get-ChildItem -Path $bundleDir -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -in @(".msi", ".exe") } |
    Select-Object -ExpandProperty FullName
}
else {
  Write-Host "경고: 번들 디렉토리를 찾지 못했습니다: $bundleDir" -ForegroundColor Yellow
}

