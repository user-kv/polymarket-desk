---
name: papertrader-pointer
description: One-line map from the wiki to the live weather papertrading bot's code/data
metadata:
  type: reference
---

# PaperTrader (live code, not in this vault)

The weather strategy described in [[guides/GUIDE3|the guides]] has a real, running
implementation — but it's a program, not a note, so it lives outside `wiki/` at:

```
../papertrader/
```

Key files there (for reference, not duplicated here):
- `papertrader.py` — CLI entrypoint (`scan`, `settle`, `report`, `status`, `backtest`,
  `calibrate`, `weekly`)
- `config.json` — discipline thresholds (edge %, stake, exposure cap), `real_money_target_date`
- `data/bets.csv`, `data/bankroll.json` — the paper ledger (fake money only)
- `data/calibration.json` — self-correcting forecast bias per city
- `dashboard.html`, `backtest.html` — generated reports
- `setup_tasks.ps1` — Windows Task Scheduler automation (scan every 2h, daily settle+report,
  weekly calibration+digest)
- `README-PAPERTRADER.md` — the bot's own usage docs

See [[00-Index]] for how this fits into the rest of the research.
