# Register (or -Unregister) a daily 6:00 AM task that refreshes the QuantiWise
# relative-return Excel and publishes it. Runs in the interactive logon session
# because it drives Excel/QuantiWise via the GUI (login click, ribbon refresh).
param([switch]$Unregister)
$ErrorActionPreference = "Stop"
$TaskName = "Lighthouse Relative Return Refresh"
$Script   = Join-Path $PSScriptRoot "refresh-relative.ps1"

if ($Unregister) {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
  Write-Host "Unregistered: $TaskName"
  return
}

$ps = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$action = New-ScheduledTaskAction -Execute $ps -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Script`""
$trigger = New-ScheduledTaskTrigger -Daily -At 6:00AM
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings `
  -Description "Refreshes the QuantiWise relative-return Excel (force-login on shared ID), regenerates data/relative-return.json, and pushes so GitHub Pages updates. Runs in the interactive session (screen should be unlocked)." -Force | Out-Null

Write-Host "Registered: $TaskName (daily 06:00, interactive logon session)"
Write-Host "The screen should be logged on/unlocked at 6 AM for the GUI automation to work."
