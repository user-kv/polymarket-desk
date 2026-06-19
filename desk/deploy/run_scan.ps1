# Reactive loop (Windows): scan for markets + place fake paper bets, then settle.
# Called by the scheduled task "PolymarketDesk-Scan". FAKE MONEY ONLY.
$ErrorActionPreference = "Continue"
$root = "C:\Users\kavee\projects\polymarket"
$log  = "$root\desk\logs\scan.log"
New-Item -ItemType Directory -Force -Path "$root\desk\logs" | Out-Null
$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content $log "`n==== scan run $ts ===="
# Set-Location is the fix the old PaperTrader-Scan task lacked (it ran with an
# invalid cwd -> ERROR_DIRECTORY). papertrader.py expects to run from its own dir.
Set-Location "$root\papertrader"
python papertrader.py scan   *>> $log
python papertrader.py settle *>> $log

# Data safety net: snapshot the ledger into git after every scan so a stray process
# can never cause real data loss (guardrail #2 applied to data). No-op if unchanged.
Set-Location $root
git add papertrader/data desk/memory/lessons 2>$null
git commit -q -m "auto: data snapshot after scan $ts" 2>$null
Add-Content $log "data snapshot committed (if changed)"
