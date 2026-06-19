# desk/deploy/setup_local_windows.ps1
# Register Windows Scheduled Tasks so the desk runs autonomously whenever this PC is
# on — no laptop-lid problem only in the sense that it still needs the machine awake.
# (For fully laptop-independent operation, deploy to the VPS — see README-DEPLOY.md.)
# Re-runnable (uses /F to overwrite). Run:  powershell -ExecutionPolicy Bypass -File this.ps1
# Uninstall:  ... -File this.ps1 -Uninstall

param([switch]$Uninstall)

$root    = "C:\Users\kavee\projects\polymarket"
$scan    = "$root\desk\deploy\run_scan.ps1"
$cycle   = "$root\desk\deploy\run_cycle.ps1"
$scanTask  = "PolymarketDesk-Scan"
$cycleTask = "PolymarketDesk-Cycle"

if ($Uninstall) {
    schtasks /Delete /TN $scanTask  /F 2>$null
    schtasks /Delete /TN $cycleTask /F 2>$null
    Write-Host "Removed $scanTask and $cycleTask."
    return
}

# Reactive scan: every 6 hours starting 00:40 (approx model-run cadence).
schtasks /Create /TN $scanTask /F /SC HOURLY /MO 6 /ST 00:40 `
  /TR "powershell -NoProfile -ExecutionPolicy Bypass -File `"$scan`""

# Reflective cycle: once daily at 14:15.
schtasks /Create /TN $cycleTask /F /SC DAILY /ST 14:15 `
  /TR "powershell -NoProfile -ExecutionPolicy Bypass -File `"$cycle`""

Write-Host "`nRegistered tasks:"
schtasks /Query /TN $scanTask  /FO LIST | Select-String "TaskName|Next Run|Schedule"
schtasks /Query /TN $cycleTask /FO LIST | Select-String "TaskName|Next Run|Schedule"
Write-Host "`nThe desk now runs autonomously while this PC is on."
Write-Host "Free real-reasoning upgrade: Ollama + qwen2:7b are already installed here;"
Write-Host "set DESK_LLM=ollama (machine env) and the cycle uses it at zero cost, no API key."
