$ErrorActionPreference = "Stop"

$ProjectDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LogDir = Join-Path $ProjectDir "tmp"
$LogFile = Join-Path $LogDir "local-preview.log"

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
            Write-PreviewLog "Stopped hidden local preview process $($process.ProcessId)."
        } catch {
            Write-PreviewLog "Failed to stop hidden local preview process $($process.ProcessId): $($_.Exception.Message)"
        }
    }
}

Stop-ProjectPreview
Write-PreviewLog "Hidden local preview stop command finished."
