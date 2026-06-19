# Reflective loop (Windows): autopsy resolved bets, update memory, briefs, self-mod
# gate (frozen by default), write the daily digest. Called by "PolymarketDesk-Cycle".
$ErrorActionPreference = "Continue"
$root = "C:\Users\kavee\projects\polymarket"
$log  = "$root\desk\logs\cycle.log"
New-Item -ItemType Directory -Force -Path "$root\desk\logs" | Out-Null
$ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
Add-Content $log "`n==== cycle run $ts ===="
Set-Location $root
# DESK_LLM is inherited from the machine env if you set one (ollama/claude/etc);
# otherwise it auto-detects a local Ollama, else runs the free deterministic mock.
python -m desk.run_cycle *>> $log
