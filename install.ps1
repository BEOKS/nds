#Requires -Version 5.1
<#
.SYNOPSIS
    NDS Skills Installer for Windows

.DESCRIPTION
    Installs NDS skills to various coding agent directories with interactive TUI selection

.PARAMETER Claude
    Install to Claude Code (~/.claude/skills)

.PARAMETER Cursor
    Install to Cursor (~/.claude/skills)

.PARAMETER Codex
    Install to Codex CLI (~/.codex/skills)

.PARAMETER Gemini
    Install to Gemini CLI (~/.gemini/skills)

.PARAMETER Antigravity
    Install to Antigravity (~/.gemini/antigravity/global_skills)

.PARAMETER Copilot
    Install to GitHub Copilot (~/.claude/skills)

.PARAMETER All
    Install to all agents

.PARAMETER List
    List available skills and exit

.PARAMETER Skills
    Comma-separated list of skills to install

.EXAMPLE
    # Interactive mode (TUI selection)
    irm https://gitlab.gabia.com/<group>/nds/-/raw/main/install.ps1 | iex

    # Install to specific agents
    $env:NDS_AGENTS = "claude,codex"; irm <url>/install.ps1 | iex

    # Install to all agents
    $env:NDS_AGENTS = "all"; irm <url>/install.ps1 | iex
#>

[CmdletBinding()]
param(
    [switch]$Claude,
    [switch]$Cursor,
    [switch]$Codex,
    [switch]$Gemini,
    [switch]$Antigravity,
    [switch]$Copilot,
    [switch]$All,
    [switch]$List,
    [string]$Skills,
    [switch]$Help
)

# ============================================================================
# Configuration
# ============================================================================
$NexusBaseUrl = if ($env:NDS_NEXUS_URL) { $env:NDS_NEXUS_URL } else { "https://repo.gabia.com/repository/raw-repository/nds" }
$GitLabHost = if ($env:NDS_GITLAB_HOST) { $env:NDS_GITLAB_HOST } else { "gitlab.gabia.com" }
$GitLabProject = if ($env:NDS_GITLAB_PROJECT) { $env:NDS_GITLAB_PROJECT } else { "gabia/idc/nds" }
$Branch = if ($env:NDS_BRANCH) { $env:NDS_BRANCH } else { "main" }

# ============================================================================
# Agent configurations
# ============================================================================
$AgentConfig = @{
    "claude" = @{
        Name = "Claude Code"
        Path = Join-Path $env:USERPROFILE ".claude\skills"
    }
    "cursor" = @{
        Name = "Cursor"
        Path = Join-Path $env:USERPROFILE ".claude\skills"
    }
    "codex" = @{
        Name = "Codex CLI"
        Path = Join-Path $env:USERPROFILE ".codex\skills"
    }
    "gemini" = @{
        Name = "Gemini CLI"
        Path = Join-Path $env:USERPROFILE ".gemini\skills"
    }
    "antigravity" = @{
        Name = "Antigravity"
        Path = Join-Path $env:USERPROFILE ".gemini\antigravity\global_skills"
    }
    "copilot" = @{
        Name = "GitHub Copilot"
        Path = Join-Path $env:USERPROFILE ".claude\skills"
    }
}

$AgentOrder = @("claude", "cursor", "codex", "gemini", "antigravity", "copilot")

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
NDS Skills Installer for Windows

Usage:
    irm <url>/install.ps1 | iex

Environment Variables:
    NDS_AGENTS         Comma-separated agents: claude,cursor,codex,gemini,antigravity (or "all")
    NDS_SKILLS         Comma-separated list of skills to install
    NDS_GITLAB_HOST    GitLab host (default: gitlab.gabia.com)
    NDS_GITLAB_PROJECT GitLab project path (default: gabia/idc/nds)
    NDS_BRANCH         Branch to use (default: main)

Agent Paths:
    Claude Code   ~/.claude/skills
    Cursor        ~/.claude/skills
    Codex CLI     ~/.codex/skills
    Gemini CLI    ~/.gemini/skills
    Antigravity   ~/.gemini/antigravity/global_skills
    Copilot       ~/.claude/skills

Examples:
    # Interactive mode
    irm <url>/install.ps1 | iex

    # Install to Claude and Codex
    `$env:NDS_AGENTS = "claude,codex"
    irm <url>/install.ps1 | iex

    # Install to all agents
    `$env:NDS_AGENTS = "all"
    irm <url>/install.ps1 | iex

    # Install specific skills
    `$env:NDS_SKILLS = "gabia-dev-mcp-oracle,pptx"
    irm <url>/install.ps1 | iex

    # List available skills
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

# Remove duplicates
$SelectedAgents = $SelectedAgents | Select-Object -Unique

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
            Write-Host "   NDS Skills Installer" -ForegroundColor Cyan
            Write-Host "================================" -ForegroundColor Cyan
            Write-Host ""
            Write-Host $Title -ForegroundColor White
            Write-Host ""
            Write-Host "  [Space] Toggle  [Enter] Confirm  [A] Select All  [N] Select None  [Q] Quit" -ForegroundColor DarkGray
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
                    Write-Info "Installation cancelled"
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
    $manifestUrl = "https://$GitLabHost/$GitLabProject/-/raw/$Branch/skills/manifest.txt"

    try {
        $manifest = Invoke-RestMethod -Uri $manifestUrl -ErrorAction Stop
        # Check if response is valid (not HTML)
        if ($manifest -and -not $manifest.StartsWith("<!DOCTYPE") -and -not $manifest.StartsWith("<html")) {
            return ($manifest -split "`n" | Where-Object { $_.Trim() -ne "" })
        }
    }
    catch {
    }

    # Fallback to hardcoded list
    return @(
        "algorithmic-art"
        "board-resolver"
        "brand-guidelines"
        "canvas-design"
        "code-simplifier"
        "dev-plan"
        "divide-conquer-tasks"
        "doc-coauthoring"
        "docx"
        "frontend-design"
        "gabia-dev-mcp-confluence"
        "gabia-dev-mcp-figma"
        "gabia-dev-mcp-gitlab-issues"
        "gabia-dev-mcp-gitlab-merge-requests"
        "gabia-dev-mcp-mattermost"
        "gabia-dev-mcp-memory"
        "gabia-dev-mcp-mysql"
        "gabia-dev-mcp-oracle"
        "hiworks-memo"
        "internal-comms"
        "mac-cron"
        "mcp-builder"
        "pdf"
        "pptx"
        "skill-creator"
        "slack-gif-creator"
        "theme-factory"
        "web-artifacts-builder"
        "webapp-testing"
        "work-logger"
        "xlsx"
    )
}

# ============================================================================
# List skills
# ============================================================================
if ($List) {
    Write-Host ""
    Write-Host "Available NDS Skills:" -ForegroundColor Cyan
    Write-Host "========================"
    $skillsList = Get-SkillsList
    foreach ($skill in $skillsList) {
        Write-Host "  * $skill"
    }
    Write-Host ""
    Write-Host "Total: $($skillsList.Count)"
    Write-Host ""
    exit 0
}

# ============================================================================
# Python installation and dependency management
# ============================================================================
$script:PythonCmd = $null
$script:PipCmd = $null
$script:SkipPython = $false

function Find-Python {
    # Try py launcher first (Windows-specific), then python3, then python
    $pythonPaths = @(
        "py -3",
        "python3",
        "python",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python310\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "$env:ProgramFiles\Python311\python.exe",
        "$env:ProgramFiles\Python310\python.exe"
    )

    foreach ($pythonPath in $pythonPaths) {
        try {
            if ($pythonPath -eq "py -3") {
                # Special handling for py launcher
                $version = & py -3 --version 2>&1
                if ($version -match "Python 3") {
                    $script:PythonCmd = "py -3"
                    break
                }
            }
            else {
                $version = & $pythonPath --version 2>&1
                if ($version -match "Python 3") {
                    $script:PythonCmd = $pythonPath
                    break
                }
            }
        }
        catch {
            continue
        }
    }

    if ($script:PythonCmd) {
        # Always prefer python -m pip to ensure pip matches Python version
        try {
            if ($script:PythonCmd -eq "py -3") {
                & py -3 -m pip --version 2>&1 | Out-Null
                $script:PipCmd = "py -3 -m pip"
            }
            else {
                & $script:PythonCmd -m pip --version 2>&1 | Out-Null
                $script:PipCmd = "$script:PythonCmd -m pip"
            }
            return $true
        }
        catch {
            Write-Warn "pip not available for $script:PythonCmd"
        }
        return $true
    }

    return $false
}

function Get-PythonVersion {
    if ($script:PythonCmd) {
        $version = & $script:PythonCmd --version 2>&1
        if ($version -match "Python (\d+\.\d+\.\d+)") {
            return $matches[1]
        }
    }
    return $null
}

function Install-PythonWindows {
    Write-Info "Attempting to install Python on Windows..."

    # Check for winget
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Info "Installing Python via winget..."
        try {
            winget install -e --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
            return $true
        }
        catch {
            Write-Warn "winget installation failed"
        }
    }

    # Check for chocolatey
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        Write-Info "Installing Python via Chocolatey..."
        try {
            choco install python3 -y
            return $true
        }
        catch {
            Write-Warn "Chocolatey installation failed"
        }
    }

    # Check for scoop
    if (Get-Command scoop -ErrorAction SilentlyContinue) {
        Write-Info "Installing Python via Scoop..."
        try {
            scoop install python
            return $true
        }
        catch {
            Write-Warn "Scoop installation failed"
        }
    }

    # Fallback: Download from python.org
    Write-Warn "No package manager found. Please install Python manually:"
    Write-Host "  1. Visit https://www.python.org/downloads/"
    Write-Host "  2. Download and install Python 3.11 or later"
    Write-Host "  3. Make sure to check 'Add Python to PATH' during installation"
    Write-Host "  4. Re-run this installer"
    return $false
}

function Test-AndInstallPython {
    Write-Host ""
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host "   Python Environment Setup" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""

    if (Find-Python) {
        $version = Get-PythonVersion
        Write-Success "Python found: $script:PythonCmd (version $version)"

        if ($script:PipCmd) {
            Write-Success "pip found: $script:PipCmd"
        }
        else {
            Write-Warn "pip not available. Python dependencies will not be installed."
            return $false
        }
        return $true
    }

    Write-Warn "Python 3 not found on this system."
    Write-Host ""
    Write-Host "Python is required for many NDS skills to work properly."
    Write-Host ""

    $answer = Read-Host "Would you like to install Python automatically? (y/n)"

    if ($answer -match "^[Yy]") {
        if (Install-PythonWindows) {
            # Refresh environment and re-detect
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

            if (Find-Python) {
                Write-Success "Python installed successfully: $script:PythonCmd"
                return $true
            }
        }
        Write-Err "Failed to install Python"
        return $false
    }
    else {
        Write-Warn "Skipping Python installation"
        $script:SkipPython = $true
        return $false
    }
}

function Install-PythonDependencies {
    if ($script:SkipPython -or -not $script:PipCmd) {
        Write-Warn "Skipping Python dependencies installation"
        return
    }

    Write-Host ""
    Write-Info "Installing Python dependencies..."

    # Download requirements.txt
    $reqUrl = "$NexusBaseUrl/requirements.txt"
    $reqFile = Join-Path $env:TEMP "nds-requirements.txt"

    try {
        Invoke-WebRequest -Uri $reqUrl -OutFile $reqFile -ErrorAction Stop
        Write-Info "Downloaded requirements.txt from Nexus"
    }
    catch {
        # Fallback: try GitLab
        $reqUrl = "https://$GitLabHost/$GitLabProject/-/raw/$Branch/requirements.txt"
        try {
            Invoke-WebRequest -Uri $reqUrl -OutFile $reqFile -ErrorAction Stop
            Write-Info "Downloaded requirements.txt from GitLab"
        }
        catch {
            Write-Warn "Could not download requirements.txt"
            return
        }
    }

    # Install dependencies
    Write-Info "Installing packages (this may take a few minutes)..."

    try {
        # Build and execute pip install command based on detected pip
        if ($script:PipCmd -eq "py -3 -m pip") {
            $process = Start-Process -FilePath "py" -ArgumentList "-3", "-m", "pip", "install", "--user", "-r", $reqFile -NoNewWindow -PassThru -Wait
        }
        elseif ($script:PipCmd -match "-m pip$") {
            # Using python -m pip
            $process = Start-Process -FilePath $script:PythonCmd -ArgumentList "-m", "pip", "install", "--user", "-r", $reqFile -NoNewWindow -PassThru -Wait
        }
        else {
            # Direct pip command (shouldn't happen with current logic, but kept for safety)
            $process = Start-Process -FilePath "pip" -ArgumentList "install", "--user", "-r", $reqFile -NoNewWindow -PassThru -Wait
        }

        if ($process.ExitCode -eq 0) {
            Write-Success "Python dependencies installed successfully"
        }
        else {
            Write-Warn "Some Python dependencies may have failed to install (exit code: $($process.ExitCode))"
            Write-Warn "You can manually install them later with:"
            Write-Host "  pip install -r requirements.txt"
        }
    }
    catch {
        Write-Warn "Failed to install Python dependencies: $_"
        Write-Warn "You can manually install them later with:"
        Write-Host "  pip install -r requirements.txt"
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
function Install-Skills {
    param(
        [string]$TargetDir
    )

    $tempDir = Join-Path $env:TEMP "nds_install_$([guid]::NewGuid().ToString('N').Substring(0,8))"

    try {
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

        $archiveUrl = "$NexusBaseUrl/nds-skills.zip"
        $archiveFile = Join-Path $tempDir "nds-skills.zip"

        Write-Info "Downloading skills archive from Nexus..."

        try {
            Invoke-WebRequest -Uri $archiveUrl -OutFile $archiveFile -ErrorAction Stop
        }
        catch {
            Write-Err "Failed to download archive from Nexus"
            Write-Err "URL: $archiveUrl"
            return $false
        }

        Write-Info "Extracting..."
        Expand-Archive -Path $archiveFile -DestinationPath $tempDir -Force

        # Find skills directory
        $skillsDir = Get-ChildItem -Path $tempDir -Recurse -Directory -Filter "skills" | Select-Object -First 1

        if (-not $skillsDir) {
            Write-Err "Skills directory not found in archive"
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

            $srcSkillDir = Join-Path $skillsDir.FullName $skill
            $srcSkillFile = Join-Path $skillsDir.FullName "$skill.skill"
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

                Write-Success "Installed: $skill"
                $installed++
            }
            # Check for .skill file
            elseif (Test-Path $srcSkillFile) {
                Copy-Item -Path $srcSkillFile -Destination $destSkillFile -Force
                Write-Success "Installed: $skill.skill"
                $installed++
            }
            else {
                Write-Warn "Not found: $skill"
                $skipped++
            }
        }

        Write-Host ""
        Write-Info "Installed: $installed skills"
        if ($skipped -gt 0) {
            Write-Warn "Skipped: $skipped skills"
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
    Write-Info "Installing to $agentName ($skillsDir)..."

    New-Item -ItemType Directory -Path $skillsDir -Force | Out-Null

    if (Install-Skills -TargetDir $skillsDir) {
        Write-Success "Installation to $agentName complete"
        return $true
    }
    else {
        Write-Err "Installation to $agentName failed"
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
        Write-Success "$VarName is already set"
        return $true
    }

    Write-Host ""
    Write-Host "* $VarName" -ForegroundColor Yellow
    Write-Host "  $Description"
    if ($TokenUrl) {
        Write-Host "  토큰 생성: $TokenUrl" -ForegroundColor DarkGray
    }

    $promptText = "  Enter value"
    if ($IsOptional) {
        $promptText += " (or press Enter to skip)"
    }

    $value = Read-Host $promptText

    if ([string]::IsNullOrWhiteSpace($value)) {
        if ($IsOptional) {
            Write-Warn "Skipped $VarName"
            return $true
        }
        else {
            Write-Warn "Skipped $VarName (required for this skill)"
            return $false
        }
    }

    $script:EnvVarsAdded[$VarName] = $value
    Write-Success "Set $VarName"
    return $true
}

function Configure-EnvironmentVariables {
    Write-Host ""
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host "   Environment Variables Setup" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "설치된 스킬에 필요한 환경변수를 설정합니다."
    Write-Host "사용하지 않는 스킬은 Enter를 눌러 스킵할 수 있습니다."
    Write-Host ""

    # GitLab Token
    Write-Host "[GitLab - Issues & Merge Requests]" -ForegroundColor White
    Prompt-EnvVar -VarName "GITLAB_TOKEN" `
        -Description "GitLab 액세스 토큰 (Issues, MR 스킬에 필요)" `
        -TokenUrl "https://gitlab.gabia.com/-/profile/personal_access_tokens" `
        -IsOptional $true

    # Confluence
    Write-Host ""
    Write-Host "[Confluence]" -ForegroundColor White
    Prompt-EnvVar -VarName "CONFLUENCE_BASE_URL" `
        -Description "Confluence 서버 베이스 URL (예: https://confluence.gabia.com)" `
        -IsOptional $true

    Prompt-EnvVar -VarName "CONFLUENCE_API_TOKEN" `
        -Description "Confluence API 토큰" `
        -TokenUrl "https://confluence.gabia.com/plugins/personalaccesstokens/usertokens.action" `
        -IsOptional $true

    $confToken = [Environment]::GetEnvironmentVariable("CONFLUENCE_USERNAME", "User")
    if (-not $confToken) {
        Prompt-EnvVar -VarName "CONFLUENCE_USERNAME" `
            -Description "Confluence 사용자명 (API 토큰과 함께 사용)" `
            -IsOptional $true
    }

    # Mattermost Token
    Write-Host ""
    Write-Host "[Mattermost]" -ForegroundColor White
    Prompt-EnvVar -VarName "MATTERMOST_TOKEN" `
        -Description "Mattermost 액세스 토큰" `
        -IsOptional $true

    # Figma Token
    Write-Host ""
    Write-Host "[Figma]" -ForegroundColor White
    Prompt-EnvVar -VarName "FIGMA_API_KEY" `
        -Description "Figma API 키" `
        -IsOptional $true

    # Sentry
    Write-Host ""
    Write-Host "[Sentry]" -ForegroundColor White
    Prompt-EnvVar -VarName "SENTRY_TOKEN" `
        -Description "Sentry Auth Token (event:read 스코프 필요)" `
        -IsOptional $true

    # Elasticsearch / Kibana
    Write-Host ""
    Write-Host "[Elasticsearch / Kibana]" -ForegroundColor White
    Prompt-EnvVar -VarName "LDAP_USER" `
        -Description "LDAP 사용자 ID (nginx Basic Auth)" `
        -IsOptional $true

    if ($script:EnvVarsAdded.ContainsKey("LDAP_USER")) {
        Prompt-EnvVar -VarName "LDAP_PWD" `
            -Description "LDAP 비밀번호" `
            -IsOptional $true
    }

    # Hiworks 쪽지
    Write-Host ""
    Write-Host "[Hiworks 쪽지]" -ForegroundColor White
    Prompt-EnvVar -VarName "HIWORKS_ID" `
        -Description "Hiworks 사용자 ID (이메일의 @ 앞부분)" `
        -IsOptional $true

    if ($script:EnvVarsAdded.ContainsKey("HIWORKS_ID")) {
        Prompt-EnvVar -VarName "HIWORKS_DOMAIN" `
            -Description "Hiworks 도메인 (예: company.com)" `
            -IsOptional $true
        Prompt-EnvVar -VarName "HIWORKS_PWD" `
            -Description "Hiworks 비밀번호" `
            -IsOptional $true
    }

    # Oracle DB
    Write-Host ""
    Write-Host "[Oracle DB]" -ForegroundColor White
    Prompt-EnvVar -VarName "ORACLE_HOST" `
        -Description "Oracle DB 호스트" `
        -IsOptional $true

    # Only ask for other Oracle vars if host was provided
    if ($script:EnvVarsAdded.ContainsKey("ORACLE_HOST")) {
        Prompt-EnvVar -VarName "ORACLE_USERNAME" `
            -Description "Oracle DB 사용자명" `
            -IsOptional $true
        Prompt-EnvVar -VarName "ORACLE_PASSWORD" `
            -Description "Oracle DB 비밀번호" `
            -IsOptional $true
    }

    # MySQL DB
    Write-Host ""
    Write-Host "[MySQL DB]" -ForegroundColor White
    Prompt-EnvVar -VarName "MYSQL_HOST" `
        -Description "MySQL DB 호스트 (단일 계정 사용 시)" `
        -IsOptional $true

    # Only ask for other MySQL vars if host was provided
    if ($script:EnvVarsAdded.ContainsKey("MYSQL_HOST")) {
        Prompt-EnvVar -VarName "MYSQL_USERNAME" `
            -Description "MySQL DB 사용자명" `
            -IsOptional $true
        Prompt-EnvVar -VarName "MYSQL_PASSWORD" `
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
        Write-Info "No environment variables were configured"
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
    Write-Host "   NDS Skills Installer" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""

    # Check and install Python
    Test-AndInstallPython | Out-Null

    # Interactive selection if no agents specified
    if ($SelectedAgents.Count -eq 0) {
        # Check if running interactively
        if ([Environment]::UserInteractive -and [Console]::WindowHeight -gt 0) {
            $SelectedAgents = Show-MultiSelectMenu -Title "Select coding agents to install skills:"

            if ($SelectedAgents.Count -eq 0) {
                Write-Warn "No agents selected"
                exit 0
            }
        }
        else {
            # Non-interactive fallback
            Write-Host "Available coding agents:"
            Write-Host "  1) Claude Code  (~/.claude/skills)"
            Write-Host "  2) Cursor       (~/.claude/skills)"
            Write-Host "  3) Codex CLI    (~/.codex/skills)"
            Write-Host "  4) Gemini CLI   (~/.gemini/skills)"
            Write-Host "  5) Antigravity  (~/.gemini/antigravity/global_skills)"
            Write-Host "  6) Copilot      (~/.claude/skills)"
            Write-Host ""
            $selection = Read-Host "Enter numbers separated by space (e.g., '1 3 4') or 'all'"

            if ($selection -eq "all") {
                $SelectedAgents = $AgentOrder.Clone()
            }
            else {
                $nums = $selection -split '\s+'
                foreach ($num in $nums) {
                    switch ($num.Trim()) {
                        "1" { $SelectedAgents += "claude" }
                        "2" { $SelectedAgents += "cursor" }
                        "3" { $SelectedAgents += "codex" }
                        "4" { $SelectedAgents += "gemini" }
                        "5" { $SelectedAgents += "antigravity" }
                        "6" { $SelectedAgents += "copilot" }
                    }
                }
            }

            if ($SelectedAgents.Count -eq 0) {
                Write-Warn "No agents selected"
                exit 0
            }
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

    Write-Info "Source: $NexusBaseUrl"
    Write-Host ""
    Write-Info "Selected agents:"
    foreach ($agent in $SelectedAgents) {
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
        Write-Err "Installation completed with errors"
        exit 1
    }

    Write-Success "Skills installation complete!"
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""

    # Install Python dependencies
    Install-PythonDependencies

    # Configure environment variables
    Configure-EnvironmentVariables

    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  1. Restart your coding agent"
    Write-Host "  2. Restart PowerShell to apply environment variables"
    if ($script:PythonCmd) {
        Write-Host "  3. Python dependencies have been installed for skills"
    }
    Write-Host ""
}

Main
