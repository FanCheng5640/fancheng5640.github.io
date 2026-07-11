param(
    [string]$TaskName = "FanChengLocalGoogleScholarAutoSync",
    [string]$DailyAt = "07:30"
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
$dailyTrigger = New-ScheduledTaskTrigger -Daily -At $time
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$triggers = @($dailyTrigger, $logonTrigger)
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -StartWhenAvailable
$principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $triggers `
    -Settings $settings `
    -Principal $principal `
    -Description "Daily and logon local Google Scholar citation sync for fancheng5640.github.io." `
    -Force | Out-Null

Write-Host "Installed scheduled task: $TaskName daily at $DailyAt and at user logon"
