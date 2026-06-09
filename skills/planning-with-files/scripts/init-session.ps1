# Initialize planning files for a new session.
#
# Usage:
#   .\init-session.ps1
#   .\init-session.ps1 -Template default
#   .\init-session.ps1 "Backend Refactor"
#   .\init-session.ps1 -PlanDir "Quick Spike"

param(
    [switch]$PlanDir,
    [string]$ProjectName = "",
    [string]$Template = "default"
)

$DATE = Get-Date -Format "yyyy-MM-dd"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillRoot = Split-Path -Parent $ScriptDir
$TemplateDir = Join-Path $SkillRoot "templates"

if ($Template -ne "default" -and $Template -ne "analytics") {
    Write-Host "Unknown template: $Template (available: default, analytics). Using default."
    $Template = "default"
}

function ConvertTo-Slug {
    param([string]$Value)
    $slug = $Value.ToLowerInvariant()
    $slug = [regex]::Replace($slug, "[^a-z0-9]", "-")
    $slug = [regex]::Replace($slug, "-{2,}", "-").Trim("-")
    if ($slug.Length -gt 40) {
        $slug = $slug.Substring(0, 40).Trim("-")
    }
    return $slug
}

function New-ShortId {
    return ([guid]::NewGuid().ToString("N").Substring(0, 8))
}

function ConvertTo-SafeSessionId {
    param([string]$Raw)
    if ([string]::IsNullOrWhiteSpace($Raw)) {
        return ""
    }
    $uuidPattern = "([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})"
    $match = [regex]::Matches($Raw, $uuidPattern)
    if ($match.Count -gt 0) {
        return $match[$match.Count - 1].Groups[1].Value.ToLowerInvariant()
    }
    if ($Raw -match "^[A-Za-z0-9_.-]{8,160}$") {
        return $Raw
    }
    return ""
}

function Get-StableSessionId {
    foreach ($key in @("PWF_SESSION_ID", "CODEX_THREAD_ID", "CODEX_CONVERSATION_ID", "CODEX_SESSION_ID")) {
        $sessionId = ConvertTo-SafeSessionId ([Environment]::GetEnvironmentVariable($key))
        if (-not [string]::IsNullOrWhiteSpace($sessionId)) {
            return $sessionId
        }
    }
    return ""
}

function Write-DefaultTaskPlan {
    param([string]$Path)
@"
# Task Plan: [Brief Description]

## Goal
[One sentence describing the end state]

## Current Phase
Phase 1

## Phases

### Phase 1: Requirements & Discovery
- [ ] Understand user intent
- [ ] Identify constraints
- [ ] Document in findings.md
- **Status:** in_progress

### Phase 2: Planning & Structure
- [ ] Define approach
- [ ] Create project structure
- **Status:** pending

### Phase 3: Implementation
- [ ] Execute the plan
- [ ] Write to files before executing
- **Status:** pending

### Phase 4: Testing & Verification
- [ ] Verify requirements met
- [ ] Document test results
- **Status:** pending

### Phase 5: Delivery
- [ ] Review outputs
- [ ] Deliver to user
- **Status:** pending

## Decisions Made
| Decision | Rationale |
|----------|-----------|

## Errors Encountered
| Error | Resolution |
|-------|------------|
"@ | Out-File -FilePath $Path -Encoding UTF8
}

function Write-DefaultFindings {
    param([string]$Path)
@"
# Findings & Decisions

## Requirements
-

## Research Findings
-

## Technical Decisions
| Decision | Rationale |
|----------|-----------|

## Issues Encountered
| Issue | Resolution |
|-------|------------|

## Resources
-
"@ | Out-File -FilePath $Path -Encoding UTF8
}

function Write-DefaultProgress {
    param([string]$Path, [string]$DateValue)
@"
# Progress Log

## Session: $DateValue

### Current Status
- **Phase:** 1 - Requirements & Discovery
- **Started:** $DateValue

### Actions Taken
-

### Test Results
| Test | Expected | Actual | Status |
|------|----------|--------|--------|

### Errors
| Error | Resolution |
|-------|------------|
"@ | Out-File -FilePath $Path -Encoding UTF8
}

function Write-AnalyticsProgress {
    param([string]$Path, [string]$DateValue)
@"
# Progress Log

## Session: $DateValue

### Current Status
- **Phase:** 1 - Data Discovery
- **Started:** $DateValue

### Actions Taken
-

### Query Log
| Query | Result Summary | Interpretation |
|-------|---------------|----------------|

### Errors
| Error | Resolution |
|-------|------------|
"@ | Out-File -FilePath $Path -Encoding UTF8
}

function New-PlanningFiles {
    param([string]$TargetDir)

    New-Item -ItemType Directory -Force -Path $TargetDir | Out-Null

    $planPath = Join-Path $TargetDir "task_plan.md"
    $findingsPath = Join-Path $TargetDir "findings.md"
    $progressPath = Join-Path $TargetDir "progress.md"

    if (-not (Test-Path $planPath)) {
        $analyticsPlan = Join-Path $TemplateDir "analytics_task_plan.md"
        if ($Template -eq "analytics" -and (Test-Path $analyticsPlan)) {
            Copy-Item $analyticsPlan $planPath
        } else {
            Write-DefaultTaskPlan $planPath
        }
        Write-Host "Created $planPath"
    } else {
        Write-Host "$planPath already exists, skipping"
    }

    if (-not (Test-Path $findingsPath)) {
        $analyticsFindings = Join-Path $TemplateDir "analytics_findings.md"
        if ($Template -eq "analytics" -and (Test-Path $analyticsFindings)) {
            Copy-Item $analyticsFindings $findingsPath
        } else {
            Write-DefaultFindings $findingsPath
        }
        Write-Host "Created $findingsPath"
    } else {
        Write-Host "$findingsPath already exists, skipping"
    }

    if (-not (Test-Path $progressPath)) {
        if ($Template -eq "analytics") {
            Write-AnalyticsProgress $progressPath $DATE
        } else {
            Write-DefaultProgress $progressPath $DATE
        }
        Write-Host "Created $progressPath"
    } else {
        Write-Host "$progressPath already exists, skipping"
    }
}

function Set-SessionPlanIfAvailable {
    param([string]$PlanRoot, [string]$PlanId)
    $sessionId = Get-StableSessionId
    if ([string]::IsNullOrWhiteSpace($sessionId)) {
        Write-Host "[planning-with-files] No stable session id in environment; PostToolUse will try to bind this session."
        return
    }
    $sessionsDir = Join-Path $PlanRoot "sessions"
    New-Item -ItemType Directory -Force -Path $sessionsDir | Out-Null
    $sessionPlanPath = Join-Path $sessionsDir "$sessionId.active_plan"
    Set-Content -Path $sessionPlanPath -Value $PlanId -Encoding UTF8
    Set-Content -Path (Join-Path $sessionsDir "$sessionId.attached") -Value "attached" -Encoding UTF8
    Write-Host "[planning-with-files] Session plan bound: $sessionPlanPath"
}

$slugMode = $PlanDir -or -not [string]::IsNullOrWhiteSpace($ProjectName)

if ($slugMode) {
    $slug = ConvertTo-Slug $ProjectName
    if ([string]::IsNullOrWhiteSpace($slug)) {
        $slug = "untitled-$(New-ShortId)"
    }
    $baseId = "$DATE-$slug"
    $planId = $baseId
    $planRoot = Join-Path (Get-Location) ".planning"
    $counter = 2
    while (Test-Path (Join-Path $planRoot $planId)) {
        $planId = "$baseId-$counter"
        $counter += 1
    }
    $planDir = Join-Path $planRoot $planId

    Write-Host "Initializing planning files for: $(if ($ProjectName) { $ProjectName } else { 'untitled' }) (template: $Template)"
    Write-Host "PLAN_ID=$planId"
    New-PlanningFiles $planDir
    New-Item -ItemType Directory -Force -Path $planRoot | Out-Null
    Set-Content -Path (Join-Path $planRoot ".active_plan") -Value $planId -Encoding UTF8
    Set-SessionPlanIfAvailable $planRoot $planId
    Write-Host ""
    Write-Host "Active plan recorded: $(Join-Path $planRoot '.active_plan')"
    Write-Host "Pin this terminal to the plan for parallel sessions:"
    Write-Host "  `$env:PLAN_ID='$planId'"
} else {
    Write-Host "Initializing planning files for: project (template: $Template)"
    New-PlanningFiles (Get-Location)
    Write-Host ""
    Write-Host "Planning files initialized!"
    Write-Host "Files: task_plan.md, findings.md, progress.md"
}
