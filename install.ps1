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
    [switch]$All,
    [switch]$List,
    [string]$Skills,
    [switch]$Help
)

# ============================================================================
# Configuration
# ============================================================================
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
}

$AgentOrder = @("claude", "cursor", "codex", "gemini", "antigravity")

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
# Download and install skills
# ============================================================================
function Install-Skills {
    param(
        [string]$TargetDir
    )

    $tempDir = Join-Path $env:TEMP "nds_install_$([guid]::NewGuid().ToString('N').Substring(0,8))"

    try {
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null

        $projectName = $GitLabProject.Split('/')[-1]
        $archiveUrl = "https://$GitLabHost/$GitLabProject/-/archive/$Branch/$projectName-$Branch.zip"
        $archiveFile = Join-Path $tempDir "nds.zip"

        Write-Info "Downloading skills archive..."

        try {
            Invoke-WebRequest -Uri $archiveUrl -OutFile $archiveFile -ErrorAction Stop
        }
        catch {
            Write-Err "Failed to download archive from GitLab"
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
# Main
# ============================================================================
function Main {
    Write-Host ""
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host "   NDS Skills Installer" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""

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

    Write-Info "GitLab: https://$GitLabHost/$GitLabProject"
    Write-Info "Branch: $Branch"
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

    Write-Success "Installation complete!"
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Next steps:"
    Write-Host "  1. Configure environment variables for skills that need them"
    Write-Host "     (See each skill's SKILL.md for required variables)"
    Write-Host "  2. Restart your coding agent"
    Write-Host ""
    Write-Host "For environment variable setup, see:"
    Write-Host "  https://$GitLabHost/$GitLabProject/-/blob/$Branch/skills/README.md"
    Write-Host ""
}

Main
