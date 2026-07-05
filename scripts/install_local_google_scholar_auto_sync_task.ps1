param(
    [string]$TaskName = "FanChengLocalGoogleScholarAutoSync",
    [string]$DailyAt = "09:00"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$scriptDir = Split-Path -Parent $PSCommandPath
$wrapper = Join-Path $scriptDir "run_local_google_scholar_auto_sync_hidden.vbs"
if (-not (Test-Path -LiteralPath $wrapper)) {
    throw "Missing wrapper: $wrapper"
}

$time = [datetime]::ParseExact($DailyAt, "HH:mm", [System.Globalization.CultureInfo]::InvariantCulture)
$action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument "`"$wrapper`""
$trigger = New-ScheduledTaskTrigger -Daily -At $time
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Principal $principal `
    -Description "Daily local Google Scholar citation sync for fancheng5640.github.io." `
    -Force | Out-Null

Write-Host "Installed scheduled task: $TaskName at $DailyAt"
