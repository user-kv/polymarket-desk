<#
.SYNOPSIS
  Registers (or removes) the three PaperTrader Windows Scheduled Tasks.

.DESCRIPTION
  Creates three Task Scheduler jobs:
    1. PaperTrader-Scan    -- runs every 2 hours to check for betting opportunities
    2. PaperTrader-Daily   -- runs daily at 9:30 AM (local time) to settle resolved
                             markets and regenerate the dashboard
    3. PaperTrader-Weekly  -- runs weekly (Sunday 9:00 AM local time) to refresh
                             the self-correcting forecast calibration and send
                             a one-shot digest notification (bankroll, win rate,
                             calibration deltas, days until your real-money date)

  NOTIFICATIONS: scan/settle/weekly only pop a Windows toast (via BurntToast)
  for events worth knowing about -- a bet placed, bets settled, or the weekly
  digest. Routine "nothing happened" scans stay silent.

  IMPORTANT:
  - Tasks only run when your laptop is ON and AWAKE (Windows limitation).
  - No real money is ever involved -- this is paper trading only.
  - If your laptop is off when a scan was due, just run it manually.

.USAGE
  Register tasks:   .\setup_tasks.ps1
  Remove tasks:     .\setup_tasks.ps1 -Uninstall

.NOTES
  Requires PowerShell 5.1+ and Administrator rights (for Task Scheduler).
  Run in PowerShell: Right-click > Run as Administrator, or open an elevated PS prompt.
#>

param(
    [switch]$Uninstall
)

# -- Configuration -------------------------------------------------------------
$ProjectDir   = $PSScriptRoot
$PythonExe    = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) {
    Write-Error "Python not found on PATH. Please install Python 3 and try again."
    exit 1
}

$ScanScript   = Join-Path $ProjectDir "papertrader.py"
$ScanTaskName = "PaperTrader-Scan"
$DailyTaskName = "PaperTrader-Daily"
$WeeklyTaskName = "PaperTrader-Weekly"

# -- Uninstall ------------------------------------------------------------------
if ($Uninstall) {
    Write-Host "Removing PaperTrader scheduled tasks..." -ForegroundColor Yellow

    foreach ($taskName in @($ScanTaskName, $DailyTaskName, $WeeklyTaskName)) {
        if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
            Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
            Write-Host "  Removed: $taskName" -ForegroundColor Green
        } else {
            Write-Host "  Not found (already removed): $taskName" -ForegroundColor Gray
        }
    }
    Write-Host "Done. Tasks removed." -ForegroundColor Green
    exit 0
}

# -- Register tasks -------------------------------------------------------------
Write-Host "Setting up PaperTrader scheduled tasks..." -ForegroundColor Cyan
Write-Host "  Python  : $PythonExe"
Write-Host "  Script  : $ScanScript"
Write-Host "  WorkDir : $ProjectDir"
Write-Host ""

# --- Task 1: Scan every 2 hours ---
$scanAction = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$ScanScript`" scan" `
    -WorkingDirectory $ProjectDir

# Trigger: repeat every 2 hours, starting 5 minutes from now, for 3 years
$startTime = (Get-Date).AddMinutes(5)
$scanTrigger = New-ScheduledTaskTrigger -Once -At $startTime `
    -RepetitionInterval (New-TimeSpan -Hours 2) `
    -RepetitionDuration (New-TimeSpan -Days 1095)

$scanSettings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -StartWhenAvailable `
    -WakeToRun:$false `
    -RunOnlyIfNetworkAvailable:$false

# Run as current user (no special permissions needed)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

if (Get-ScheduledTask -TaskName $ScanTaskName -ErrorAction SilentlyContinue) {
    Write-Host "  Updating existing task: $ScanTaskName" -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $ScanTaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $ScanTaskName `
    -Description "PaperTrader: Scan Polymarket weather markets every 2 hours (FAKE MONEY ONLY)" `
    -Action $scanAction `
    -Trigger $scanTrigger `
    -Settings $scanSettings `
    -Principal $principal | Out-Null

Write-Host "  Registered: $ScanTaskName (every 2 hours)" -ForegroundColor Green

# --- Task 2: Daily settle + report at 9:30 AM local time ---
# 9:30 AM ET = 14:30 UTC (EST) or 13:30 UTC (EDT)
# Using local 9:30 AM so Task Scheduler handles timezone automatically
$dailyAction = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$ScanScript`" settle && `"$PythonExe`" `"$ScanScript`" report" `
    -WorkingDirectory $ProjectDir

# Actually, chain settle + report properly via cmd /c
$dailyAction = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"`"$PythonExe`" `"$ScanScript`" settle && `"$PythonExe`" `"$ScanScript`" report`"" `
    -WorkingDirectory $ProjectDir

$dailyTrigger = New-ScheduledTaskTrigger -Daily -At "09:30AM"

$dailySettings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
    -StartWhenAvailable `
    -WakeToRun:$false

if (Get-ScheduledTask -TaskName $DailyTaskName -ErrorAction SilentlyContinue) {
    Write-Host "  Updating existing task: $DailyTaskName" -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $DailyTaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $DailyTaskName `
    -Description "PaperTrader: Settle resolved markets + regenerate dashboard (daily 9:30 AM)" `
    -Action $dailyAction `
    -Trigger $dailyTrigger `
    -Settings $dailySettings `
    -Principal $principal | Out-Null

Write-Host "  Registered: $DailyTaskName (daily 9:30 AM)" -ForegroundColor Green

# --- Task 3: Weekly calibration + digest, Sunday 9:00 AM local time ---
$weeklyAction = New-ScheduledTaskAction `
    -Execute $PythonExe `
    -Argument "`"$ScanScript`" weekly" `
    -WorkingDirectory $ProjectDir

$weeklyTrigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At "09:00AM"

$weeklySettings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 15) `
    -StartWhenAvailable `
    -WakeToRun:$false

if (Get-ScheduledTask -TaskName $WeeklyTaskName -ErrorAction SilentlyContinue) {
    Write-Host "  Updating existing task: $WeeklyTaskName" -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $WeeklyTaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $WeeklyTaskName `
    -Description "PaperTrader: weekly calibration refresh + digest notification (FAKE MONEY ONLY)" `
    -Action $weeklyAction `
    -Trigger $weeklyTrigger `
    -Settings $weeklySettings `
    -Principal $principal | Out-Null

Write-Host "  Registered: $WeeklyTaskName (weekly, Sunday 9:00 AM)" -ForegroundColor Green

# -- Summary --------------------------------------------------------------------
Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Tasks created:"
Write-Host "  $ScanTaskName   - runs every 2 hours (market scan)"
Write-Host "  $DailyTaskName  - runs daily at 9:30 AM (settle + report)"
Write-Host "  $WeeklyTaskName  - runs weekly, Sunday 9:00 AM (calibration + digest notification)"
Write-Host ""
Write-Host "Notifications: you'll get a Windows toast only when something happened --"
Write-Host "  a bet placed, bets settled, or the weekly digest. Silent otherwise."
Write-Host ""
Write-Host "To view tasks: Open Task Scheduler > Task Scheduler Library"
Write-Host "To run manually at any time:"
Write-Host "  cd `"$ProjectDir`""
Write-Host "  python papertrader.py scan"
Write-Host "  python papertrader.py settle"
Write-Host "  python papertrader.py report"
Write-Host "  python papertrader.py status"
Write-Host "  python papertrader.py weekly"
Write-Host ""
Write-Host 'IMPORTANT: Tasks only run when your laptop is ON and awake.'
Write-Host 'This is FAKE MONEY only -- no real orders are ever placed.'
Write-Host ''
Write-Host 'To remove these tasks later, run:'
Write-Host '  .\setup_tasks.ps1 -Uninstall'
Write-Host ''
