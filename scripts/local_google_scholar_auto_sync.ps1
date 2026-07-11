param(
    [string]$Remote = "origin",
    [string]$Branch = "master",
    [switch]$IgnoreChecklist
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $PSCommandPath
$repoRoot = Split-Path -Parent $scriptDir
$stateDir = Join-Path $env:USERPROFILE ".codex\scholar-auto-sync"
$logPath = Join-Path $stateDir "local_google_scholar_auto_sync.log"
$runStatePath = Join-Path $stateDir "local_google_scholar_auto_sync_status.json"
$scholarStatusPath = Join-Path $stateDir "google_scholar_status.json"
$targetDataPath = "_data/google_scholar.json"

New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

function Write-RunLog {
    param(
        [string]$Level,
        [string]$Message
    )
    $timestamp = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss zzz")
    $line = "[$timestamp] [$Level] $Message"
    Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
    Write-Host $line
}

function Write-RunState {
    param(
        [string]$Status,
        [string]$Message
    )
    $payload = [ordered]@{
        status = $Status
        message = $Message
        time = (Get-Date).ToString("o")
        repo = $repoRoot
        branch = $Branch
        log_path = $logPath
        scholar_status_path = $scholarStatusPath
    }
    $payload | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $runStatePath -Encoding UTF8
}

function Finish-Run {
    param(
        [string]$Status,
        [string]$Message,
        [int]$Code = 0
    )
    Write-RunLog $Status.ToUpperInvariant() $Message
    Write-RunState $Status $Message
    Pop-Location
    exit $Code
}

function Invoke-Capture {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )
    $previousErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        $output = & $FilePath @Arguments 2>&1
        $exitCode = $LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $previousErrorActionPreference
    }
    foreach ($line in @($output)) {
        if ($null -ne $line -and "$line".Trim().Length -gt 0) {
            Write-RunLog "INFO" "$FilePath $($Arguments -join ' '): $line"
        }
    }
    if ($exitCode -ne 0) {
        throw "$FilePath $($Arguments -join ' ') failed with exit code $exitCode"
    }
    return @($output)
}

function Invoke-Git {
    param([string[]]$Arguments)
    return Invoke-Capture "git" $Arguments
}

function Resolve-Tool {
    param(
        [string]$Name,
        [string[]]$Fallbacks = @()
    )
    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    foreach ($candidate in $Fallbacks) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) {
            return $candidate
        }
    }
    throw "Required command was not found: $Name"
}

function Decode-Utf8 {
    param([string]$Base64)
    return [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($Base64))
}

function Get-ChecklistSection {
    param(
        [string]$Text,
        [string]$StartHeader,
        [string]$EndHeader
    )
    $pattern = "(?s)" + [regex]::Escape($StartHeader) + "\s*(.*?)\s*" + [regex]::Escape($EndHeader)
    $match = [regex]::Match($Text, $pattern)
    if (-not $match.Success) {
        return ""
    }
    return $match.Groups[1].Value.Trim()
}

function Test-ChecklistBlocksAutoSync {
    if ($IgnoreChecklist) {
        Write-RunLog "INFO" "Checklist gate bypassed for an explicit operator run."
        return $false
    }

    $checklistPath = Join-Path $repoRoot (Decode-Utf8 "6ZyA5rGC5riF5Y2VLnR4dA==")
    if (-not (Test-Path -LiteralPath $checklistPath)) {
        return $false
    }

    $text = [System.IO.File]::ReadAllText($checklistPath, [System.Text.Encoding]::UTF8)
    $high = Get-ChecklistSection `
        -Text $text `
        -StartHeader (Decode-Utf8 "PT09IOaWsOmcgOaxgu+8iOmrmOS8mOWFiOe6p++8jOWcqOi/memHjOWGme+8iSA9PT0=") `
        -EndHeader (Decode-Utf8 "PT09IOaWsOmcgOaxgu+8iOS9juS8mOWFiOe6p++8jOWcqOi/memHjOWGme+8iSA9PT0=")
    $low = Get-ChecklistSection `
        -Text $text `
        -StartHeader (Decode-Utf8 "PT09IOaWsOmcgOaxgu+8iOS9juS8mOWFiOe6p++8jOWcqOi/memHjOWGme+8iSA9PT0=") `
        -EndHeader (Decode-Utf8 "PT09IOW3suWujOaIkO+8iOWAkuW6j++8jOacgOaWsOWcqOacgOWJje+8iSA9PT0=")

    if ($high.Length -gt 0) {
        Write-RunLog "INFO" "Checklist has high-priority items; auto sync will wait."
        return $true
    }
    if ($text.Contains((Decode-Utf8 "W+acquWujOaIkF0=")) -or $text.Contains((Decode-Utf8 "W+mDqOWIhuWujOaIkF0="))) {
        Write-RunLog "INFO" "Checklist has unfinished legacy items; auto sync will wait."
        return $true
    }
    if ($low.Length -gt 0) {
        Write-RunLog "INFO" "Checklist has low-priority queued items; continuing because the worktree is clean and this sync only touches Scholar data."
    }
    return $false
}

function Get-ChangedPaths {
    $unstaged = @(Invoke-Git @("diff", "--name-only"))
    $staged = @(Invoke-Git @("diff", "--cached", "--name-only"))
    $untracked = @(Invoke-Git @("ls-files", "--others", "--exclude-standard"))
    return @($unstaged + $staged + $untracked | Where-Object { $_ } | Sort-Object -Unique)
}

Write-RunLog "INFO" "Starting local Google Scholar auto sync."
Push-Location $repoRoot

try {
    if (Test-ChecklistBlocksAutoSync) {
        Finish-Run "skipped" "High-priority or unfinished checklist items are still pending; no files were changed."
    }

    $currentBranch = (Invoke-Git @("rev-parse", "--abbrev-ref", "HEAD") | Select-Object -First 1).ToString().Trim()
    if ($currentBranch -ne $Branch) {
        Finish-Run "skipped" "Current branch is $currentBranch, not $Branch; no files were changed."
    }

    $initialStatus = @(Invoke-Git @("status", "--porcelain", "--untracked-files=all"))
    if ($initialStatus.Count -gt 0) {
        Finish-Run "skipped" "Worktree is not clean before sync; no files were changed."
    }

    Invoke-Git @("fetch", $Remote, $Branch) | Out-Null
    $comparison = (Invoke-Git @("rev-list", "--left-right", "--count", "$Branch...$Remote/$Branch") | Select-Object -First 1).ToString().Trim()
    $parts = $comparison -split "\s+"
    if ($parts.Count -lt 2) {
        throw "Could not compare local $Branch with $Remote/$Branch. Raw comparison: $comparison"
    }
    $localAhead = [int]$parts[0]
    $remoteAhead = [int]$parts[1]
    if ($localAhead -eq 0 -and $remoteAhead -gt 0) {
        Write-RunLog "INFO" "Local $Branch is behind $Remote/$Branch by $remoteAhead commit(s); fast-forwarding before Scholar sync."
        Invoke-Git @("merge", "--ff-only", "$Remote/$Branch") | Out-Null
        $statusAfterFastForward = @(Invoke-Git @("status", "--porcelain", "--untracked-files=all"))
        if ($statusAfterFastForward.Count -gt 0) {
            throw "Worktree is not clean after fast-forward: $($statusAfterFastForward -join ', ')"
        }
    }
    elseif ($localAhead -ne 0 -or $remoteAhead -ne 0) {
        Finish-Run "skipped" "Local $Branch and $Remote/$Branch are not aligned ($comparison); no files were changed."
    }

    $python = Resolve-Tool "python" @(
        (Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe")
    )
    $bundle = Resolve-Tool "bundle" @("C:\Ruby33-x64\bin\bundle.bat")

    if (Test-Path -LiteralPath $scholarStatusPath) {
        Remove-Item -LiteralPath $scholarStatusPath -Force
    }

    $env:PYTHONIOENCODING = "utf-8"
    $env:GOOGLE_SCHOLAR_STATUS_OUTPUT = $scholarStatusPath
    $env:GOOGLE_SCHOLAR_WRITE_STALE_ON_FAILURE = "0"

    Invoke-Capture $python @("-B", ".github/scripts/sync_google_scholar.py") | Out-Null

    if (-not (Test-Path -LiteralPath $scholarStatusPath)) {
        throw "Google Scholar sync did not write a status file."
    }
    $scholarStatus = Get-Content -LiteralPath $scholarStatusPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($scholarStatus.status -ne "ok" -or [bool]$scholarStatus.used_cache) {
        throw "Google Scholar sync did not return fresh data. Status: $($scholarStatus.status); used_cache: $($scholarStatus.used_cache); error: $($scholarStatus.error)"
    }

    $changedPaths = @(Get-ChangedPaths)
    if ($changedPaths.Count -eq 0) {
        Finish-Run "ok" "Google Scholar sync returned fresh data; repository data was already current."
    }
    if ($changedPaths.Count -ne 1 -or $changedPaths[0] -ne $targetDataPath) {
        throw "Unexpected changed paths after Scholar sync: $($changedPaths -join ', ')"
    }

    Invoke-Capture $python @(
        "-B",
        "-m",
        "py_compile",
        ".github/scripts/sync_google_scholar.py",
        ".github/scripts/scholarly_sync_report.py"
    ) | Out-Null
    Invoke-Capture $python @("scripts/check_journal_metrics_freshness.py") | Out-Null
    Invoke-Capture $bundle @("exec", "jekyll", "build") | Out-Null

    Invoke-Git @("add", "--", $targetDataPath) | Out-Null
    $commitTitle = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String("6Ieq5Yqo5pu05pawIEdvb2dsZSBTY2hvbGFyIOW8leeUqOaVsOaNrg=="))
    $commitBody = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String("5pys5py65a6a5pe25ZCM5q2lIEdvb2dsZSBTY2hvbGFyIOW8leeUqOaVsOaNruOAgg=="))
    Invoke-Git @("commit", "-m", $commitTitle, "-m", $commitBody) | Out-Null
    Invoke-Git @("push", $Remote, $Branch) | Out-Null

    Finish-Run "ok" "Committed and pushed fresh Google Scholar data."
}
catch {
    Write-RunState "failed" "$_"
    Write-RunLog "ERROR" "$_"
    Pop-Location
    exit 1
}
