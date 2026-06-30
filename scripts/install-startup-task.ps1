$ErrorActionPreference = "Stop"

$TaskName = "Lighthouse AMC Dashboard Server"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$StartScript = Join-Path $ProjectRoot "scripts\start-dashboard.ps1"
$PowerShell = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$Arguments = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$StartScript`""

$Action = New-ScheduledTaskAction -Execute $PowerShell -Argument $Arguments -WorkingDirectory $ProjectRoot
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet `
  -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries `
  -ExecutionTimeLimit (New-TimeSpan -Hours 0)

Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $Action `
  -Trigger $Trigger `
  -Settings $Settings `
  -Description "Pulls the latest Lighthouse AMC dashboard from GitHub and starts the local server at logon." `
  -Force | Out-Null

Write-Host "Installed startup task: $TaskName"
Write-Host "The dashboard will update from GitHub and start after Windows logon."
