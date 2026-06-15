$ErrorActionPreference = "Stop"

$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LogDir = Join-Path $ProjectDir "tmp"
$LogFile = Join-Path $LogDir "local-preview.log"
$PidFile = Join-Path $LogDir "local-preview.pid"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-PreviewLog {
    param([string]$Message)

    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Message"
    try {
        $line | Add-Content -LiteralPath $LogFile -Encoding UTF8 -ErrorAction Stop
    } catch {
        $fallbackLog = Join-Path $LogDir "local-preview-control.log"
        $fallbackLine = "$line (local-preview.log locked: $($_.Exception.Message))"
        $fallbackLine | Add-Content -LiteralPath $fallbackLog -Encoding UTF8
    }
}

function Stop-ProjectPreview {
    $processes = Get-CimInstance Win32_Process | Where-Object {
        $_.CommandLine -and
        $_.CommandLine.Contains($ProjectDir) -and
        $_.CommandLine -match "jekyll" -and
        $_.CommandLine -match "serve"
    }

    foreach ($process in $processes) {
        try {
            Stop-Process -Id $process.ProcessId -Force -ErrorAction Stop
            Write-PreviewLog "Stopped old local preview process $($process.ProcessId)."
        } catch {
            Write-PreviewLog "Failed to stop old local preview process $($process.ProcessId): $($_.Exception.Message)"
        }
    }
}

Stop-ProjectPreview
Start-Sleep -Milliseconds 800

$startLine = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting hidden local preview for $ProjectDir"
$logReset = $false
$lastLogError = $null
foreach ($attempt in 1..10) {
    try {
        $startLine | Set-Content -LiteralPath $LogFile -Encoding UTF8 -ErrorAction Stop
        $logReset = $true
        break
    } catch {
        $lastLogError = $_.Exception.Message
        Start-Sleep -Milliseconds 250
    }
}

if (-not $logReset) {
    Write-PreviewLog "Could not reset local preview log; appending start entry instead. Last error: $lastLogError"
    Write-PreviewLog "Starting hidden local preview for $ProjectDir"
}

$cmdCommand = 'chcp 65001 >nul && cd /d "' + $ProjectDir + '" && bundle exec jekyll serve --host 127.0.0.1 --port 4000 --livereload --force_polling >> "' + $LogFile + '" 2>&1'

$preview = Start-Process -FilePath "cmd.exe" `
    -ArgumentList @("/d", "/s", "/c", $cmdCommand) `
    -WorkingDirectory $ProjectDir `
    -WindowStyle Hidden `
    -PassThru

$preview.Id | Set-Content -LiteralPath $PidFile -Encoding ASCII
Write-PreviewLog "Started hidden local preview launcher process $($preview.Id)."

Start-Sleep -Seconds 4
Start-Process "http://localhost:4000"
