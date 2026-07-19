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

function Get-ChangedPaths {
    $unstaged = @(Invoke-Git @("diff", "--name-only"))
    $staged = @(Invoke-Git @("diff", "--cached", "--name-only"))
    $untracked = @(Invoke-Git @("ls-files", "--others", "--exclude-standard"))
    return @($unstaged + $staged + $untracked | Where-Object { $_ } | Sort-Object -Unique)
}

Write-RunLog "INFO" "Starting local Google Scholar auto sync."
$syncWorktree = Join-Path $stateDir ("worktree-" + [guid]::NewGuid().ToString("N"))
$worktreeAdded = $false
$insideSyncWorktree = $false
$finalMessage = ""

try {
    Push-Location $repoRoot
    try {
        $mainStatus = @(Invoke-Git @("status", "--porcelain", "--untracked-files=all"))
        if ($mainStatus.Count -gt 0) {
            Write-RunLog "INFO" "Main worktree has user changes; continuing safely in an isolated worktree."
        }
        if ($IgnoreChecklist) {
            Write-RunLog "INFO" "IgnoreChecklist is retained for backward compatibility; isolated sync never edits the main worktree."
        }
        Invoke-Git @("fetch", $Remote, $Branch) | Out-Null
        Invoke-Git @("worktree", "add", "--detach", $syncWorktree, "$Remote/$Branch") | Out-Null
        $worktreeAdded = $true
    }
    finally {
        Pop-Location
    }

    Push-Location $syncWorktree
    $insideSyncWorktree = $true
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
        $finalMessage = "Google Scholar sync returned fresh data; repository data was already current."
    }
    elseif ($changedPaths.Count -ne 1 -or $changedPaths[0] -ne $targetDataPath) {
        throw "Unexpected changed paths after Scholar sync: $($changedPaths -join ', ')"
    }
    else {
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
        Invoke-Git @("push", $Remote, "HEAD:$Branch") | Out-Null
        $finalMessage = "Committed and pushed fresh Google Scholar data from the isolated worktree."
    }
    Pop-Location
    $insideSyncWorktree = $false

    Push-Location $repoRoot
    try {
        Invoke-Git @("worktree", "remove", "--force", "--", $syncWorktree) | Out-Null
        $worktreeAdded = $false
    }
    finally {
        Pop-Location
    }

    Finish-Run "ok" $finalMessage
}
catch {
    $runError = $_
    if ($insideSyncWorktree) {
        Pop-Location
        $insideSyncWorktree = $false
    }
    if ($worktreeAdded) {
        Push-Location $repoRoot
        try {
            Invoke-Git @("worktree", "remove", "--force", "--", $syncWorktree) | Out-Null
        }
        catch {
            Write-RunLog "ERROR" "Could not remove isolated worktree $syncWorktree`: $_"
        }
        finally {
            Pop-Location
        }
    }
    Write-RunState "failed" "$runError"
    Write-RunLog "ERROR" "$runError"
    exit 1
}
