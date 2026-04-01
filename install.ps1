#Requires -Version 5.1
<#
.SYNOPSIS
    Windows용 NDS 스킬 설치기

.DESCRIPTION
    대화형 TUI 선택으로 다양한 코딩 에이전트 디렉터리에 NDS 스킬을 설치합니다

.PARAMETER Claude
    Claude Code에 설치 (~/.claude/skills)

.PARAMETER Cursor
    Cursor에 설치 (~/.claude/skills)

.PARAMETER Codex
    Codex CLI에 설치 (~/.codex/skills)

.PARAMETER Opencode
    OpenCode에 설치 (~/.config/opencode/skills)

.PARAMETER Gemini
    Gemini CLI에 설치 (~/.gemini/skills)

.PARAMETER Antigravity
    Antigravity에 설치 (~/.gemini/antigravity/global_skills)

.PARAMETER Copilot
    GitHub Copilot에 설치 (~/.claude/skills)

.PARAMETER All
    모든 에이전트에 설치

.PARAMETER List
    사용 가능한 스킬 목록을 표시하고 종료

.PARAMETER Skills
    설치할 스킬 목록 (쉼표로 구분)

.PARAMETER NoInteractive
    대화형 TUI 선택을 건너뜀

.EXAMPLE
    # 대화형 모드 (TUI 선택)
    irm https://gitlab.gabia.com/<group>/nds/-/raw/main/install.ps1 | iex

    # 특정 에이전트에 설치
    $env:NDS_AGENTS = "claude,codex"; irm <url>/install.ps1 | iex

    # 모든 에이전트에 설치
    $env:NDS_AGENTS = "all"; irm <url>/install.ps1 | iex
#>

[CmdletBinding()]
param(
    [switch]$Claude,
    [switch]$Cursor,
    [switch]$Codex,
    [switch]$Opencode,
    [switch]$Gemini,
    [switch]$Antigravity,
    [switch]$Copilot,
    [switch]$All,
    [switch]$List,
    [string]$Skills,
    [switch]$NoInteractive,
    [switch]$Help
)

function Initialize-Utf8Console {
    try {
        $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
        [Console]::InputEncoding = $utf8NoBom
        [Console]::OutputEncoding = $utf8NoBom
        $OutputEncoding = $utf8NoBom
    }
    catch {
    }
}

function Get-InstallerSourceText {
    param([string]$ScriptPath)

    if ($ScriptPath -and (Test-Path -LiteralPath $ScriptPath)) {
        return [System.Text.Encoding]::UTF8.GetString([System.IO.File]::ReadAllBytes($ScriptPath))
    }

    $installerUrl = if ($env:NDS_INSTALLER_URL) {
        $env:NDS_INSTALLER_URL
    }
    elseif ($env:NDS_NEXUS_URL) {
        ($env:NDS_NEXUS_URL.TrimEnd('/') + "/install.ps1")
    }
    else {
        "https://repo.gabia.com/repository/raw-repository/nds/install.ps1"
    }

    $webClient = New-Object System.Net.WebClient
    try {
        return [System.Text.Encoding]::UTF8.GetString($webClient.DownloadData($installerUrl))
    }
    finally {
        $webClient.Dispose()
    }
}

if (($PSVersionTable.PSEdition -eq "Desktop") -and (-not $env:NDS_UTF8_BOOTSTRAPPED)) {
    Initialize-Utf8Console
    $env:NDS_UTF8_BOOTSTRAPPED = "1"
    $scriptText = Get-InstallerSourceText -ScriptPath $MyInvocation.MyCommand.Path
    $scriptText = $scriptText.TrimStart([char]0xFEFF)
    $tokens = $null
    $errors = $null
    $ast = [System.Management.Automation.Language.Parser]::ParseInput($scriptText, [ref]$tokens, [ref]$errors)
    if ($errors.Count -gt 0) {
        throw $errors[0]
    }

    $bodyOffset = if ($ast.ParamBlock) { $ast.ParamBlock.Extent.EndOffset } else { 0 }
    $scriptBody = $scriptText.Substring($bodyOffset)
    Invoke-Expression $scriptBody
    return
}

Initialize-Utf8Console

# ============================================================================
# Configuration
# ============================================================================
$NexusBaseUrl = if ($env:NDS_NEXUS_URL) { $env:NDS_NEXUS_URL } else { "https://repo.gabia.com/repository/raw-repository/nds" }
$GitLabHost = if ($env:NDS_GITLAB_HOST) { $env:NDS_GITLAB_HOST } else { "gitlab.gabia.com" }
$GitLabProject = if ($env:NDS_GITLAB_PROJECT) { $env:NDS_GITLAB_PROJECT } else { "gabia/idc/nds" }
$Branch = if ($env:NDS_BRANCH) { $env:NDS_BRANCH } else { "main" }

function Get-UserHomePath {
    foreach ($candidate in @(
        $env:USERPROFILE,
        $HOME,
        [Environment]::GetFolderPath("UserProfile")
    )) {
        if (-not [string]::IsNullOrWhiteSpace($candidate)) {
            return $candidate
        }
    }

    throw "사용자 홈 디렉터리를 확인할 수 없습니다."
}

function Get-TempPathSafe {
    foreach ($candidate in @(
        $env:TEMP,
        $env:TMP,
        [IO.Path]::GetTempPath()
    )) {
        if (-not [string]::IsNullOrWhiteSpace($candidate)) {
            return $candidate
        }
    }

    throw "임시 디렉터리를 확인할 수 없습니다."
}

function Test-CanPrompt {
    if ($NoInteractive) {
        return $false
    }

    try {
        return [Environment]::UserInteractive -and ([Console]::WindowHeight -gt 0)
    }
    catch {
        return $false
    }
}

$UserHomePath = Get-UserHomePath

# ============================================================================
# Agent configurations
# ============================================================================
$AgentConfig = @{
    "claude" = @{
        Name = "Claude Code"
        Path = Join-Path $UserHomePath ".claude\skills"
    }
    "cursor" = @{
        Name = "Cursor"
        Path = Join-Path $UserHomePath ".claude\skills"
    }
    "codex" = @{
        Name = "Codex CLI"
        Path = Join-Path $UserHomePath ".codex\skills"
    }
    "opencode" = @{
        Name = "OpenCode"
        Path = Join-Path $UserHomePath ".config\opencode\skills"
    }
    "gemini" = @{
        Name = "Gemini CLI"
        Path = Join-Path $UserHomePath ".gemini\skills"
    }
    "antigravity" = @{
        Name = "Antigravity"
        Path = Join-Path $UserHomePath ".gemini\antigravity\global_skills"
    }
    "copilot" = @{
        Name = "GitHub Copilot"
        Path = Join-Path $UserHomePath ".claude\skills"
    }
}

$AgentOrder = @("claude", "cursor", "codex", "opencode", "gemini", "antigravity", "copilot")

# ============================================================================
# Logging functions
# ============================================================================
function Write-Info {
    param([string]$Message)
    Write-Host "[INFO] " -ForegroundColor Blue -NoNewline
    Write-Host $Message
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[WARN] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

function Write-Err {
    param([string]$Message)
    Write-Host "[ERROR] " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

# ============================================================================
# Show help
# ============================================================================
if ($Help) {
    @"
Windows용 NDS 스킬 설치기

사용법:
    irm <url>/install.ps1 | iex

환경변수:
    NDS_AGENTS         쉼표로 구분된 에이전트: claude,cursor,codex,opencode,gemini,antigravity,copilot (또는 "all")
    NDS_SKILLS         설치할 스킬 목록 (쉼표로 구분)
    NDS_NO_INTERACTIVE "true"로 설정하면 TUI 선택을 건너뜀
    NDS_GITLAB_HOST    GitLab 호스트 (기본값: gitlab.gabia.com)
    NDS_GITLAB_PROJECT GitLab 프로젝트 경로 (기본값: gabia/idc/nds)
    NDS_BRANCH         사용할 브랜치 (기본값: main)

에이전트 경로:
    Claude Code   ~/.claude/skills
    Cursor        ~/.claude/skills
    Codex CLI     ~/.codex/skills
    OpenCode      ~/.config/opencode/skills
    Gemini CLI    ~/.gemini/skills
    Antigravity   ~/.gemini/antigravity/global_skills
    Copilot       ~/.claude/skills

예시:
    # 대화형 모드
    irm <url>/install.ps1 | iex

    # Claude와 Codex에 설치
    `$env:NDS_AGENTS = "claude,codex"
    irm <url>/install.ps1 | iex

    # 모든 에이전트에 설치
    `$env:NDS_AGENTS = "all"
    irm <url>/install.ps1 | iex

    # 특정 스킬 설치
    `$env:NDS_SKILLS = "gabia-dev-mcp-oracle,pptx"
    irm <url>/install.ps1 | iex

    # 대화형 프롬프트 건너뜀
    `$env:NDS_NO_INTERACTIVE = "true"
    irm <url>/install.ps1 | iex

    # 사용 가능한 스킬 목록 표시
    `$env:NDS_LIST = "true"
    irm <url>/install.ps1 | iex
"@
    exit 0
}

# ============================================================================
# Parse environment variables
# ============================================================================
$SelectedAgents = @()

# Check environment variable first
if ($env:NDS_AGENTS) {
    if ($env:NDS_AGENTS -eq "all") {
        $SelectedAgents = $AgentOrder.Clone()
    } else {
        $SelectedAgents = $env:NDS_AGENTS -split ',' | ForEach-Object { $_.Trim().ToLower() }
    }
}

# Check command line switches
if ($Claude) { $SelectedAgents += "claude" }
if ($Cursor) { $SelectedAgents += "cursor" }
if ($Codex) { $SelectedAgents += "codex" }
if ($Opencode) { $SelectedAgents += "opencode" }
if ($Gemini) { $SelectedAgents += "gemini" }
if ($Antigravity) { $SelectedAgents += "antigravity" }
if ($Copilot) { $SelectedAgents += "copilot" }
if ($All) { $SelectedAgents = $AgentOrder.Clone() }

if ($env:NDS_SKILLS -and -not $Skills) {
    $Skills = $env:NDS_SKILLS
}

if ($env:NDS_LIST -eq "true") {
    $List = $true
}

if ($env:NDS_NO_INTERACTIVE -match "^(?i:true|1|yes|y)$") {
    $NoInteractive = $true
}

# Remove duplicates
$SelectedAgents = $SelectedAgents | Select-Object -Unique

$InvalidAgents = @(
    $SelectedAgents |
        Where-Object { -not [string]::IsNullOrWhiteSpace($_) -and -not $AgentConfig.ContainsKey($_) } |
        Select-Object -Unique
)

if ($InvalidAgents.Count -gt 0) {
    Write-Err "알 수 없는 에이전트: $($InvalidAgents -join ', ')"
    Write-Info "유효한 에이전트: $($AgentOrder -join ', ')"
    exit 1
}

# ============================================================================
# TUI Multi-select Menu
# ============================================================================
function Show-MultiSelectMenu {
    param(
        [string]$Title
    )

    $selected = @{}
    foreach ($agent in $AgentOrder) {
        $selected[$agent] = $false
    }

    $cursor = 0
    $numOptions = $AgentOrder.Count

    # Hide cursor
    [Console]::CursorVisible = $false

    try {
        while ($true) {
            Clear-Host
            Write-Host ""
            Write-Host "================================" -ForegroundColor Cyan
            Write-Host "   NDS 스킬 설치기" -ForegroundColor Cyan
            Write-Host "================================" -ForegroundColor Cyan
            Write-Host ""
            Write-Host $Title -ForegroundColor White
            Write-Host ""
            Write-Host "  [Space] 선택/해제  [Enter] 확인  [A] 전체 선택  [N] 전체 해제  [Q] 종료" -ForegroundColor DarkGray
            Write-Host ""

            for ($i = 0; $i -lt $numOptions; $i++) {
                $agentKey = $AgentOrder[$i]
                $agentName = $AgentConfig[$agentKey].Name
                $agentPath = $AgentConfig[$agentKey].Path

                $prefix = "  "
                $checkbox = "[ ]"

                if ($i -eq $cursor) {
                    $prefix = "> "
                    Write-Host -NoNewline $prefix -ForegroundColor White
                } else {
                    Write-Host -NoNewline $prefix
                }

                if ($selected[$agentKey]) {
                    Write-Host -NoNewline "[" -ForegroundColor Green
                    Write-Host -NoNewline ([char]0x2713) -ForegroundColor Green  # checkmark
                    Write-Host -NoNewline "] " -ForegroundColor Green
                } else {
                    Write-Host -NoNewline "[ ] "
                }

                if ($i -eq $cursor) {
                    Write-Host $agentName -ForegroundColor White
                } else {
                    Write-Host $agentName
                }

                Write-Host "      $agentPath" -ForegroundColor DarkGray
                Write-Host ""
            }

            $key = [Console]::ReadKey($true)

            switch ($key.Key) {
                "UpArrow" {
                    $cursor--
                    if ($cursor -lt 0) { $cursor = $numOptions - 1 }
                }
                "DownArrow" {
                    $cursor++
                    if ($cursor -ge $numOptions) { $cursor = 0 }
                }
                "Spacebar" {
                    $agentKey = $AgentOrder[$cursor]
                    $selected[$agentKey] = -not $selected[$agentKey]
                }
                "Enter" {
                    break
                }
                "A" {
                    foreach ($agent in $AgentOrder) {
                        $selected[$agent] = $true
                    }
                }
                "N" {
                    foreach ($agent in $AgentOrder) {
                        $selected[$agent] = $false
                    }
                }
                "Q" {
                    [Console]::CursorVisible = $true
                    Clear-Host
                    Write-Info "설치가 취소되었습니다"
                    exit 0
                }
                "J" {
                    $cursor++
                    if ($cursor -ge $numOptions) { $cursor = 0 }
                }
                "K" {
                    $cursor--
                    if ($cursor -lt 0) { $cursor = $numOptions - 1 }
                }
            }

            if ($key.Key -eq "Enter") { break }
        }
    }
    finally {
        [Console]::CursorVisible = $true
    }

    Clear-Host

    # Return selected agents
    $result = @()
    foreach ($agent in $AgentOrder) {
        if ($selected[$agent]) {
            $result += $agent
        }
    }
    return $result
}

# ============================================================================
# Get available skills list
# ============================================================================
function Get-SkillsList {
    $manifestUrls = @(
        "$NexusBaseUrl/manifest.txt",
        "https://$GitLabHost/$GitLabProject/-/raw/$Branch/skills/manifest.txt"
    )

    foreach ($manifestUrl in $manifestUrls) {
        try {
            $response = Invoke-WebRequest -Uri $manifestUrl -ErrorAction Stop
            $manifest = $response.Content
            # Check if response is valid (not HTML)
            if ($manifest -and -not $manifest.StartsWith("<!DOCTYPE") -and -not $manifest.StartsWith("<html")) {
                return ($manifest -split '\r?\n' | Where-Object { $_.Trim() -ne "" })
            }
        }
        catch {
        }
    }

    # Fallback to current manifest snapshot
    return @(
        "algorithmic-art"
        "board-resolver"
        "brand-guidelines"
        "canvas-design"
        "code-simplifier"
        "composition-patterns"
        "cve-scan"
        "doc-coauthoring"
        "docx"
        "frontend-design"
        "gabia-dev-mcp-confluence"
        "gabia-dev-mcp-elasticsearch"
        "gabia-dev-mcp-figma"
        "gabia-dev-mcp-gitlab-issues"
        "gabia-dev-mcp-gitlab-merge-requests"
        "gabia-dev-mcp-mattermost"
        "gabia-dev-mcp-memory"
        "gabia-dev-mcp-mysql"
        "gabia-dev-mcp-oracle"
        "gabia-dev-mcp-sentry"
        "gsap-core"
        "gsap-frameworks"
        "gsap-gif-creator"
        "gsap-performance"
        "gsap-plugins"
        "gsap-react"
        "gsap-scrolltrigger"
        "gsap-timeline"
        "gsap-utils"
        "git-worktree"
        "gitlab-review"
        "hiworks-mail"
        "hiworks-ui"
        "hiworks-memo"
        "internal-comms"
        "mac-cron"
        "mcp-builder"
        "obsidian-writer"
        "pdf"
        "pptx"
        "react-best-practices"
        "react-native-skills"
        "skill-creator"
        "slack-gif-creator"
        "theme-factory"
        "tmux-review"
        "vercel-deploy-claimable"
        "web-artifacts-builder"
        "web-design-guidelines"
        "webapp-testing"
        "xlsx"
    )
}

# ============================================================================
# List skills
# ============================================================================
if ($List) {
    Write-Host ""
    Write-Host "사용 가능한 NDS 스킬:" -ForegroundColor Cyan
    Write-Host "========================"
    $skillsList = Get-SkillsList
    foreach ($skill in $skillsList) {
        Write-Host "  * $skill"
    }
    Write-Host ""
    Write-Host "총: $($skillsList.Count)"
    Write-Host ""
    exit 0
}

# ============================================================================
# Python installation and dependency management
# ============================================================================
$script:PythonCmd = $null
$script:PythonArgs = @()
$script:PythonDisplay = $null
$script:PipCmd = $null
$script:SkipPython = $false

function Invoke-Python {
    param(
        [string[]]$ArgumentList
    )

    & $script:PythonCmd @script:PythonArgs @ArgumentList
}

function Find-Python {
    # Try py launcher first (Windows-specific), then python3, then python
    $pythonPaths = @(
        @{ FilePath = "py"; Args = @("-3"); Display = "py -3" }
        @{ FilePath = "python3"; Args = @(); Display = "python3" }
        @{ FilePath = "python"; Args = @(); Display = "python" }
        @{ FilePath = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"; Args = @(); Display = "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" }
        @{ FilePath = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"; Args = @(); Display = "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" }
        @{ FilePath = "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe"; Args = @(); Display = "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe" }
        @{ FilePath = "$env:ProgramFiles\Python312\python.exe"; Args = @(); Display = "$env:ProgramFiles\Python312\python.exe" }
        @{ FilePath = "$env:ProgramFiles\Python311\python.exe"; Args = @(); Display = "$env:ProgramFiles\Python311\python.exe" }
        @{ FilePath = "$env:ProgramFiles\Python310\python.exe"; Args = @(); Display = "$env:ProgramFiles\Python310\python.exe" }
    )

    foreach ($pythonPath in $pythonPaths) {
        try {
            $version = & $pythonPath.FilePath @($pythonPath.Args + @("--version")) 2>&1
            if ($version -match "Python 3") {
                $script:PythonCmd = $pythonPath.FilePath
                $script:PythonArgs = @($pythonPath.Args)
                $script:PythonDisplay = $pythonPath.Display
                break
            }
        }
        catch {
            continue
        }
    }

    if ($script:PythonCmd) {
        # Always prefer python -m pip to ensure pip matches Python version
        try {
            Invoke-Python -ArgumentList @("-m", "pip", "--version") 2>&1 | Out-Null
            $script:PipCmd = "$script:PythonDisplay -m pip"
            return $true
        }
        catch {
            Write-Warn "pip을 사용할 수 없습니다: $script:PythonDisplay"
        }
        return $true
    }

    return $false
}

function Get-PythonVersion {
    if ($script:PythonCmd) {
        $version = Invoke-Python -ArgumentList @("--version") 2>&1
        if ($version -match "Python (\d+\.\d+\.\d+)") {
            return $matches[1]
        }
    }
    return $null
}

function Install-PythonWindows {
    Write-Info "Windows에서 Python 설치 시도 중..."

    # Check for winget
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Info "winget으로 Python 설치 중..."
        try {
            winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
            return $true
        }
        catch {
            Write-Warn "winget 설치 실패"
        }
    }

    # Check for chocolatey
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Info "Chocolatey로 Python 설치 중..."
        try {
            choco install python3 -y
            return $true
        }
        catch {
            Write-Warn "Chocolatey 설치 실패"
        }
    }

    # Check for scoop
    if (Get-Command scoop -ErrorAction SilentlyContinue) {
        Write-Info "Scoop으로 Python 설치 중..."
        try {
            scoop install python
            return $true
        }
        catch {
            Write-Warn "Scoop 설치 실패"
        }
    }

    # Fallback: Download from python.org
    Write-Warn "패키지 관리자를 찾을 수 없습니다. Python을 수동으로 설치하세요:"
    Write-Host "  1. https://www.python.org/downloads/ 방문"
    Write-Host "  2. Python 3.11 이상 버전 다운로드 및 설치"
    Write-Host "  3. 설치 중 'Add Python to PATH' 항목을 반드시 체크하세요"
    Write-Host "  4. 이 설치기를 다시 실행하세요"
    return $false
}

function Test-AndInstallPython {
    Write-Host ""
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host "   Python 환경 설정" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""

    if (Find-Python) {
        $version = Get-PythonVersion
        Write-Success "Python 발견: $script:PythonDisplay (버전 $version)"

        if ($script:PipCmd) {
            Write-Success "pip 발견: $script:PipCmd"
        }
        else {
            Write-Warn "pip을 사용할 수 없습니다. Python 의존성이 설치되지 않습니다."
            return $false
        }
        return $true
    }

    Write-Warn "이 시스템에서 Python 3을 찾을 수 없습니다."
    Write-Host ""
    Write-Host "많은 NDS 스킬이 정상 작동하려면 Python이 필요합니다."
    Write-Host ""

    if (-not (Test-CanPrompt)) {
        Write-Warn "대화형 프롬프트를 사용할 수 없어 Python 설치를 건너뜁니다."
        $script:SkipPython = $true
        return $false
    }

    $answer = Read-Host "Python을 자동으로 설치하시겠습니까? (y/n)"

    if ($answer -match "^[Yy]") {
        if (Install-PythonWindows) {
            # Refresh environment and re-detect
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

            if (Find-Python) {
                Write-Success "Python 설치 완료: $script:PythonDisplay"
                return $true
            }
        }
        Write-Err "Python 설치 실패"
        return $false
    }
    else {
        Write-Warn "Python 설치를 건너뜁니다"
        $script:SkipPython = $true
        return $false
    }
}

function Install-PythonDependencies {
    if ($script:SkipPython -or -not $script:PipCmd) {
        Write-Warn "Python 의존성 설치를 건너뜁니다"
        return
    }

    function Get-RequirementsFile {
        param(
            [string]$FileName
        )

        $localFile = Join-Path (Get-TempPathSafe) "nds-$FileName"
        $urls = @(
            "$NexusBaseUrl/$FileName",
            "https://$GitLabHost/$GitLabProject/-/raw/$Branch/$FileName"
        )

        foreach ($url in $urls) {
            try {
                Invoke-WebRequest -Uri $url -OutFile $localFile -ErrorAction Stop
                $contentPreview = Get-Content -Path $localFile -TotalCount 1 -ErrorAction SilentlyContinue
                if ($contentPreview -match '^(<!DOCTYPE|<html)') {
                    Remove-Item $localFile -Force -ErrorAction SilentlyContinue
                    continue
                }
                Write-Info "$FileName 다운로드 완료: $url"
                return $localFile
            }
            catch {
            }
        }

        return $null
    }

    function Invoke-RequirementsInstall {
        param(
            [string]$ReqFile,
            [string]$DisplayName,
            [bool]$Optional = $false
        )

        try {
            $pipArgs = @($script:PythonArgs + @("-m", "pip", "install", "--user", "-r", $ReqFile))
            $process = Start-Process -FilePath $script:PythonCmd -ArgumentList $pipArgs -NoNewWindow -PassThru -Wait

            if ($process.ExitCode -eq 0) {
                Write-Success "$DisplayName 설치 완료"
                return $true
            }

            if ($Optional) {
                Write-Warn "$DisplayName 설치 실패 (종료 코드: $($process.ExitCode))"
                Write-Warn "이 패키지는 선택 사항으로 특정 스킬에만 필요합니다"
            }
            else {
                Write-Warn "일부 Python 의존성 설치에 실패했을 수 있습니다 (종료 코드: $($process.ExitCode))"
                Write-Warn "나중에 수동으로 설치할 수 있습니다:"
                Write-Host "  pip install --user -r requirements.txt"
            }
            return $false
        }
        catch {
            if ($Optional) {
                Write-Warn "${DisplayName} 설치 실패: $_"
            }
            else {
                Write-Warn "Python 의존성 설치 실패: $_"
                Write-Warn "나중에 수동으로 설치할 수 있습니다:"
                Write-Host "  pip install --user -r requirements.txt"
            }
            return $false
        }
    }

    Write-Host ""
    Write-Info "패키지 설치 중 (몇 분 소요될 수 있습니다)..."

    $reqFile = Get-RequirementsFile -FileName "requirements.txt"
    if (-not $reqFile) {
        Write-Warn "requirements.txt를 다운로드할 수 없습니다"
        return
    }

    try {
        $installed = Invoke-RequirementsInstall -ReqFile $reqFile -DisplayName "Python 의존성"

        if (-not $installed) {
            return
        }

        $optReqFile = Get-RequirementsFile -FileName "requirements-optional.txt"
        if ($optReqFile) {
            Write-Info "선택적 의존성 설치 중 (mcp, anthropic)..."
            Invoke-RequirementsInstall -ReqFile $optReqFile -DisplayName "선택적 의존성" -Optional $true | Out-Null
            Remove-Item $optReqFile -Force -ErrorAction SilentlyContinue
        }
    }
    finally {
        if (Test-Path $reqFile) {
            Remove-Item $reqFile -Force -ErrorAction SilentlyContinue
        }
    }
}

# ============================================================================
# Download and install skills
# ============================================================================
function Test-SkillsSourceRoot {
    param(
        [string]$Path
    )

    if (-not (Test-Path $Path -PathType Container)) {
        return $false
    }

    if (Test-Path (Join-Path $Path "manifest.txt") -PathType Leaf) {
        return $true
    }

    $hasSkillFile = Get-ChildItem -Path $Path -File -Filter "*.skill" -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($hasSkillFile) {
        return $true
    }

    $hasSkillDir = Get-ChildItem -Path $Path -Directory -ErrorAction SilentlyContinue |
        Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") -PathType Leaf } |
        Select-Object -First 1

    return [bool]$hasSkillDir
}

function Resolve-SkillsArchiveRoot {
    param(
        [string]$ExtractedDir
    )

    if (Test-SkillsSourceRoot -Path $ExtractedDir) {
        return $ExtractedDir
    }

    $skillsDir = Get-ChildItem -Path $ExtractedDir -Recurse -Directory -Filter "skills" -ErrorAction SilentlyContinue |
        Sort-Object FullName |
        Where-Object { Test-SkillsSourceRoot -Path $_.FullName } |
        Select-Object -First 1
    if ($skillsDir) {
        return $skillsDir.FullName
    }

    $candidateDir = Get-ChildItem -Path $ExtractedDir -Recurse -Directory -ErrorAction SilentlyContinue |
        Sort-Object { $_.FullName.Length } |
        Where-Object { Test-SkillsSourceRoot -Path $_.FullName } |
        Select-Object -First 1
    if ($candidateDir) {
        return $candidateDir.FullName
    }

    return $null
}

function Install-Skills {
    param(
        [string]$TargetDir
    )

    $tempDir = Join-Path (Get-TempPathSafe) "nds_install_$([guid]::NewGuid().ToString('N').Substring(0,8))"

    try {
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

        $archiveUrl = "$NexusBaseUrl/nds-skills.zip"
        $archiveFile = Join-Path $tempDir "nds-skills.zip"

        Write-Info "Nexus에서 스킬 아카이브 다운로드 중..."

        try {
            Invoke-WebRequest -Uri $archiveUrl -OutFile $archiveFile -ErrorAction Stop
        }
        catch {
            Write-Err "Nexus에서 아카이브 다운로드 실패"
            Write-Err "URL: $archiveUrl"
            return $false
        }

        Write-Info "압축 해제 중..."
        Expand-Archive -Path $archiveFile -DestinationPath $tempDir -Force

        # 아카이브 구조가 달라도 실제 skills source root를 찾는다.
        $skillsRoot = Resolve-SkillsArchiveRoot -ExtractedDir $tempDir

        if (-not $skillsRoot) {
            Write-Err "아카이브에서 스킬 디렉터리를 찾을 수 없습니다"
            return $false
        }

        # Determine which skills to install
        $skillsToInstall = if ($Skills) {
            $Skills -split ',' | ForEach-Object { $_.Trim() }
        }
        else {
            Get-SkillsList
        }

        $installed = 0
        $skipped = 0

        foreach ($skill in $skillsToInstall) {
            if ([string]::IsNullOrWhiteSpace($skill)) { continue }

            $srcSkillDir = Join-Path $skillsRoot $skill
            $srcSkillFile = Join-Path $skillsRoot "$skill.skill"
            $destSkillDir = Join-Path $TargetDir $skill
            $destSkillFile = Join-Path $TargetDir "$skill.skill"

            # Check for directory-based skill
            if (Test-Path $srcSkillDir -PathType Container) {
                if (Test-Path $destSkillDir) {
                    Remove-Item -Path $destSkillDir -Recurse -Force
                }
                Copy-Item -Path $srcSkillDir -Destination $destSkillDir -Recurse

                # Remove __pycache__ directories
                Get-ChildItem -Path $destSkillDir -Recurse -Directory -Filter "__pycache__" |
                    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

                Write-Success "설치 완료: $skill"
                $installed++
            }
            # Check for .skill file
            elseif (Test-Path $srcSkillFile) {
                Copy-Item -Path $srcSkillFile -Destination $destSkillFile -Force
                Write-Success "설치 완료: $skill.skill"
                $installed++
            }
            else {
                Write-Warn "찾을 수 없음: $skill"
                $skipped++
            }
        }

        Write-Host ""
        Write-Info "설치 완료: $installed개 스킬"
        if ($skipped -gt 0) {
            Write-Warn "건너뜀: $skipped개 스킬"
        }

        return $true
    }
    finally {
        if (Test-Path $tempDir) {
            Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
}

function Install-SkillsTo {
    param(
        [string]$AgentKey
    )

    $agentName = $AgentConfig[$AgentKey].Name
    $skillsDir = $AgentConfig[$AgentKey].Path

    Write-Host ""
    Write-Info "$agentName ($skillsDir)에 설치 중..."

    New-Item -ItemType Directory -Path $skillsDir -Force | Out-Null

    if (Install-Skills -TargetDir $skillsDir) {
        Write-Success "$agentName 설치 완료"
        return $true
    }
    else {
        Write-Err "$agentName 설치 실패"
        return $false
    }
}

# ============================================================================
# Environment variable configuration
# ============================================================================
$script:EnvVarsAdded = @{}

function Prompt-EnvVar {
    param(
        [string]$VarName,
        [string]$Description,
        [string]$TokenUrl = "",
        [bool]$IsOptional = $true
    )

    # Check if already set
    $currentValue = [Environment]::GetEnvironmentVariable($VarName, "User")

    if ($currentValue) {
        Write-Success "$VarName 이미 설정되어 있습니다"
        return $true
    }

    Write-Host ""
    Write-Host "* $VarName" -ForegroundColor Yellow
    Write-Host "  $Description"
    if ($TokenUrl) {
        Write-Host "  토큰 생성: $TokenUrl" -ForegroundColor DarkGray
    }

    $promptText = "  값을 입력하세요"
    if ($IsOptional) {
        $promptText += " (건너뛰려면 Enter를 누르세요)"
    }

    $value = Read-Host $promptText

    if ([string]::IsNullOrWhiteSpace($value)) {
        if ($IsOptional) {
            Write-Warn "$VarName 건너뜀"
            return $true
        }
        else {
            Write-Warn "$VarName 건너뜀 (이 스킬에 필요합니다)"
            return $false
        }
    }

    $script:EnvVarsAdded[$VarName] = $value
    Write-Success "$VarName 설정 완료"
    return $true
}

function Configure-EnvironmentVariables {
    if (-not (Test-CanPrompt)) {
        Write-Info "비대화형 모드로 환경변수 설정을 건너뜁니다"
        return
    }

    Write-Host ""
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host "   환경변수 설정" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "설치된 스킬에 필요한 환경변수를 설정합니다."
    Write-Host "사용하지 않는 스킬은 Enter를 눌러 스킵할 수 있습니다."
    Write-Host ""

    # GitLab Token
    Write-Host "[GitLab - Issues & Merge Requests]" -ForegroundColor White
    $null = Prompt-EnvVar -VarName "GITLAB_TOKEN" `
        -Description "GitLab 액세스 토큰 (Issues, MR 스킬에 필요)" `
        -TokenUrl "https://gitlab.gabia.com/-/profile/personal_access_tokens" `
        -IsOptional $true

    # Confluence
    Write-Host ""
    Write-Host "[Confluence]" -ForegroundColor White
    $null = Prompt-EnvVar -VarName "CONFLUENCE_BASE_URL" `
        -Description "Confluence 서버 베이스 URL (예: https://confluence.gabia.com)" `
        -IsOptional $true

    $null = Prompt-EnvVar -VarName "ATLASSIAN_OAUTH_ACCESS_TOKEN" `
        -Description "Confluence 개인용 액세스 토큰 (Bearer 인증). confluence.gabia.com 사용 시 https://confluence.gabia.com/plugins/personalaccesstokens/usertokens.action 에서 발급한 토큰을 입력하세요." `
        -TokenUrl "https://confluence.gabia.com/plugins/personalaccesstokens/usertokens.action" `
        -IsOptional $true

    # Mattermost Token
    Write-Host ""
    Write-Host "[Mattermost]" -ForegroundColor White
    $null = Prompt-EnvVar -VarName "MATTERMOST_TOKEN" `
        -Description "Mattermost 액세스 토큰" `
        -IsOptional $true

    # Figma Token
    Write-Host ""
    Write-Host "[Figma]" -ForegroundColor White
    $null = Prompt-EnvVar -VarName "FIGMA_API_KEY" `
        -Description "Figma API 키" `
        -IsOptional $true

    # Sentry
    Write-Host ""
    Write-Host "[Sentry]" -ForegroundColor White
    $null = Prompt-EnvVar -VarName "SENTRY_TOKEN" `
        -Description "Sentry Auth Token (event:read 스코프 필요)" `
        -IsOptional $true

    # Elasticsearch / Kibana
    Write-Host ""
    Write-Host "[Elasticsearch / Kibana]" -ForegroundColor White
    $null = Prompt-EnvVar -VarName "LDAP_USER" `
        -Description "LDAP 사용자 ID (nginx Basic Auth)" `
        -IsOptional $true

    if ($script:EnvVarsAdded.ContainsKey("LDAP_USER")) {
        $null = Prompt-EnvVar -VarName "LDAP_PWD" `
            -Description "LDAP 비밀번호" `
            -IsOptional $true
    }

    # Hiworks 쪽지
    Write-Host ""
    Write-Host "[Hiworks 쪽지]" -ForegroundColor White
    $null = Prompt-EnvVar -VarName "HIWORKS_ID" `
        -Description "Hiworks 사용자 ID (이메일의 @ 앞부분)" `
        -IsOptional $true

    if ($script:EnvVarsAdded.ContainsKey("HIWORKS_ID")) {
        $null = Prompt-EnvVar -VarName "HIWORKS_DOMAIN" `
            -Description "Hiworks 도메인 (예: company.com)" `
            -IsOptional $true
        $null = Prompt-EnvVar -VarName "HIWORKS_PWD" `
            -Description "Hiworks 비밀번호" `
            -IsOptional $true
    }

    # Oracle DB
    Write-Host ""
    Write-Host "[Oracle DB]" -ForegroundColor White
    $null = Prompt-EnvVar -VarName "ORACLE_HOST" `
        -Description "Oracle DB 호스트" `
        -IsOptional $true

    # Only ask for other Oracle vars if host was provided
    if ($script:EnvVarsAdded.ContainsKey("ORACLE_HOST")) {
        $null = Prompt-EnvVar -VarName "ORACLE_USERNAME" `
            -Description "Oracle DB 사용자명" `
            -IsOptional $true
        $null = Prompt-EnvVar -VarName "ORACLE_PASSWORD" `
            -Description "Oracle DB 비밀번호" `
            -IsOptional $true
    }

    # MySQL DB
    Write-Host ""
    Write-Host "[MySQL DB]" -ForegroundColor White
    $null = Prompt-EnvVar -VarName "MYSQL_HOST" `
        -Description "MySQL DB 호스트 (단일 계정 사용 시)" `
        -IsOptional $true

    # Only ask for other MySQL vars if host was provided
    if ($script:EnvVarsAdded.ContainsKey("MYSQL_HOST")) {
        $null = Prompt-EnvVar -VarName "MYSQL_USERNAME" `
            -Description "MySQL DB 사용자명" `
            -IsOptional $true
        $null = Prompt-EnvVar -VarName "MYSQL_PASSWORD" `
            -Description "MySQL DB 비밀번호" `
            -IsOptional $true
    }

    # Save environment variables if any were added
    if ($script:EnvVarsAdded.Count -gt 0) {
        Write-Host ""
        Write-Host "================================" -ForegroundColor Cyan
        Save-EnvironmentVariables
    }
    else {
        Write-Host ""
        Write-Info "환경변수가 설정되지 않았습니다"
    }
}

function Save-EnvironmentVariables {
    Write-Host ""
    Write-Host "환경변수를 저장할 위치를 선택하세요:"
    Write-Host "  1) 사용자 환경변수로 저장 (권장)"
    Write-Host "  2) 화면에 출력만 (직접 복사)"
    Write-Host "  3) 저장 안 함"
    Write-Host ""

    $choice = Read-Host "선택 (1/2/3)"

    switch ($choice) {
        "1" {
            foreach ($key in $script:EnvVarsAdded.Keys) {
                [Environment]::SetEnvironmentVariable($key, $script:EnvVarsAdded[$key], "User")
            }
            Write-Success "환경변수가 사용자 환경변수로 저장되었습니다"
            Write-Info "새 PowerShell 창을 열면 적용됩니다"
        }
        "2" {
            Write-Host ""
            Write-Host "아래 내용을 PowerShell 프로필에 추가하세요:" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "# NDS Skills Environment Variables"
            foreach ($key in $script:EnvVarsAdded.Keys) {
                Write-Host "`$env:$key = `"$($script:EnvVarsAdded[$key])`""
            }
            Write-Host ""
        }
        default {
            Write-Info "환경변수 저장을 건너뛰었습니다"
        }
    }
}

# ============================================================================
# Main
# ============================================================================
function Main {
    Write-Host ""
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host "   NDS 스킬 설치기" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""

    # Check and install Python
    Test-AndInstallPython | Out-Null

    # Interactive selection if no agents specified
    if ($SelectedAgents.Count -eq 0) {
        if ($NoInteractive) {
            Write-Info "비대화형 모드로 실행 중, 모든 에이전트에 설치합니다"
            $SelectedAgents = $AgentOrder.Clone()
        }
        # Check if running interactively
        elseif (Test-CanPrompt) {
            $SelectedAgents = Show-MultiSelectMenu -Title "스킬을 설치할 코딩 에이전트를 선택하세요:"

            if ($SelectedAgents.Count -eq 0) {
                Write-Warn "에이전트가 선택되지 않았습니다"
                exit 0
            }
        }
        else {
            Write-Info "대화형 콘솔을 사용할 수 없어 모든 에이전트에 설치합니다"
            $SelectedAgents = $AgentOrder.Clone()
        }
    }

    # Remove duplicates and get unique paths
    $uniquePaths = @{}
    $finalAgents = @()
    foreach ($agent in $SelectedAgents) {
        $path = $AgentConfig[$agent].Path
        if (-not $uniquePaths.ContainsKey($path)) {
            $uniquePaths[$path] = $true
            $finalAgents += $agent
        }
    }

    Write-Info "소스: $NexusBaseUrl"
    Write-Host ""
    Write-Info "선택된 에이전트:"
    foreach ($agent in $finalAgents) {
        $name = $AgentConfig[$agent].Name
        $path = $AgentConfig[$agent].Path
        Write-Host "  * $name ($path)"
    }
    Write-Host ""

    $installFailed = $false

    foreach ($agent in $finalAgents) {
        if (-not (Install-SkillsTo -AgentKey $agent)) {
            $installFailed = $true
        }
    }

    Write-Host ""
    Write-Host "================================" -ForegroundColor Cyan

    if ($installFailed) {
        Write-Err "설치가 오류와 함께 완료되었습니다"
        exit 1
    }

    Write-Success "스킬 설치 완료!"
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""

    # Install Python dependencies
    Install-PythonDependencies

    # Configure environment variables
    Configure-EnvironmentVariables

    Write-Host ""
    Write-Host "다음 단계:"
    Write-Host "  1. 코딩 에이전트를 재시작하세요"
    Write-Host "  2. 환경변수를 적용하려면 PowerShell을 재시작하세요"
    if ($script:PythonCmd) {
        Write-Host "  3. 스킬에 필요한 Python 의존성이 설치되었습니다"
    }
    Write-Host ""
}

Main
