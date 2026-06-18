# PaperTrader — Your Weather Prediction Market Practice System

**This system uses FAKE money only. No real money will ever be touched.**

Think of it like a flight simulator: you practice all the real moves, see real results, but nothing in your bank account changes. Only after 100+ paper bets with positive results should you consider using real money.

---

## What Does This Do?

Every 2 hours, the system:
1. Checks Polymarket for temperature markets in **Dallas** and **Atlanta** that resolve within 48 hours
2. Pulls the professional weather forecast (80 ensemble model members from GFS + ECMWF)
3. Compares the forecast probability to the market price
4. If it finds a big enough gap (≥ 10 percentage points), it paper-bets **$5 of fake money**
5. Logs everything so you can see if the strategy really works

Every morning at 9:30 AM:
1. Checks which markets have resolved (yesterday's temperature was officially recorded)
2. Marks each bet WON or LOST, updates your fake bankroll
3. Regenerates the dashboard so you can see your results

---

## How to Run It Manually

Open PowerShell in the `papertrader` folder and type:

```
python papertrader.py scan       ← Find markets + place paper bets right now
python papertrader.py settle     ← Settle resolved markets, update balance
python papertrader.py report     ← Rebuild dashboard.html + tracker.xlsx
python papertrader.py status     ← Quick summary: balance, open bets, win rate
```

---

## Set Up Automatic Scheduling

Run this once in an **Administrator** PowerShell window (right-click PowerShell > Run as Administrator):

```powershell
cd C:\Users\kavee\projects\polymarket\papertrader
.\setup_tasks.ps1
```

This creates two scheduled tasks:
- **Scan** runs every 2 hours automatically
- **Daily report** runs at 9:30 AM

To remove them later: `.\setup_tasks.ps1 -Uninstall`

**Important caveat:** Tasks only run when your laptop is on and awake. If you close your lid, scans are skipped. Just run `python papertrader.py scan` manually whenever you want.

---

## Reading the Dashboard (dashboard.html)

Open `dashboard.html` in any web browser (double-click the file).

| Section | What It Means |
|---|---|
| **Current Bankroll** | Your fake starting $500, updated after every win/loss |
| **Total P&L** | Your overall profit or loss in fake dollars, after the 2% fee |
| **Win Rate** | % of resolved bets you won |
| **Avg Edge** | Average gap between model probability and market price (higher = better opportunities) |
| **Bankroll Curve** | Chart showing how your fake balance changes over time |
| **Open Bets** | Markets you've bet on that haven't resolved yet |
| **Settled Bets** | Green = won, Red = lost |
| **Calibration** | When the model said "80%", did you actually win ~80% of those? This tells you whether to trust the model. (Needs 100+ bets to be meaningful.) |

---

## Reading the Tracker (tracker.xlsx)

Open in Microsoft Excel.

**Weather Bets tab:** Automatically filled from the system. One row per paper bet. Read-only for tracking purposes.

**Sports Bets (Manual) tab:** Template for Strategy 2 (sports value betting). You fill this in yourself:
1. Find a sports market on Polymarket
2. Look up the same event on Pinnacle (sharp bookmaker)
3. Enter Pinnacle's decimal odds in columns D and E
4. Excel automatically calculates the "true" probability (column F) by removing the bookmaker's fee
5. Enter the Polymarket ask price (column H)
6. Column I shows the edge — if ≥ 8%, it's worth considering
7. After the market resolves, enter the closing Polymarket price in column N
8. Column O shows CLV (Closing Line Value) — if this is positive over many bets, you have genuine skill

---

## The Five Rules (When a Paper Bet Is Placed)

The system only bets if ALL five checks pass:

1. **≥ 10 percentage point edge** — Model says 65%, market charges 50%? Edge = 15pt. ✓ Bet. If the model says 55% and market charges 50%? Edge = 5pt. ✗ Skip (near-miss logged).
2. **Resolves within 48 hours** — Weather forecasts beyond 2 days are too uncertain.
3. **GFS and ECMWF models agree** — Both must forecast within 1.5°C (2.7°F) of each other. If the models disagree, the forecast is uncertain — sit out.
4. **Not straddling the forecast mean** — Skip buckets within ±3°F of the predicted temperature. These are 50/50 coin flips even with good models.
5. **Bankroll check** — Max 1 bet per bucket, and total open bets can't exceed 20% of your bankroll ($100 max).

---

## Understanding the Numbers

**Example bet:**
- Market: "Will Dallas be 96-97°F on June 13?"
- Market ask price: $0.13 (market thinks it's 13% likely)
- Model probability: 35% (35 of 80 ensemble members land in that bucket)
- **Edge = 35% - 13% = 22 percentage points** — well above the 10pt threshold ✓
- Stake: $5.00 (flat always)
- Shares bought: $5.00 ÷ $0.13 = **38.46 shares**
- If WON: 38.46 × $1.00 = $38.46 gross, minus 2% fee ($0.77) minus stake ($5.00) = **+$32.69 profit**
- If LOST: just the $5 stake gone = **-$5.00**
- Expected value: 35% × $32.69 + 65% × (-$5.00) = **+$11.44 per bet** (on average)

**Near-misses** (5-10pt edge): logged to the scan snapshots but not bet. After 100+ scans, you can compare whether the near-misses also make money — if so, consider lowering the threshold to 8pt.

---

## Where Are the Files?

```
papertrader/
  papertrader.py       ← the main program (run this)
  config.json          ← settings: cities, thresholds, stake size, bankroll
  dashboard.html       ← your results (open in browser)
  tracker.xlsx         ← full ledger + sports template (open in Excel)
  data/
    bets.csv           ← every single paper bet, one row each (never deleted)
    bankroll.json      ← current fake balance + full history
    scans/             ← JSON snapshot of every scan (audit trail)
  logs/                ← plain-text logs, one file per day
  lib/                 ← the code (don't need to touch)
```

---

## Frequently Asked Questions

**Q: Why is there a "TEST" bet in my ledger?**
A: When the system was first installed, a single test bet was placed to verify everything works. It's marked `is_test=Y`. You can ignore it, or delete its row from `data/bets.csv`.

**Q: It's been running for a week and placed zero bets — is it broken?**
A: Probably not. The 10pt edge threshold is strict. Run `python papertrader.py status` to see if markets are being found and evaluated. Check `data/scans/` for the latest JSON — it lists every market evaluated and why each was skipped. No bets = no qualifying edge = good discipline.

**Q: The model says 60% but I'm only winning 40%. Is something wrong?**
A: After fewer than 50 bets, this is just normal variance — 40% is only 20 away from 60%, and small samples swing wildly. Judge after 100+ bets. The calibration chart in the dashboard will show the trend.

**Q: Dallas and Atlanta don't have markets today. What happens?**
A: The scan logs "no markets found" and exits cleanly. It tries again in 2 hours. Polymarket creates new temperature markets roughly 1-3 days in advance.

**Q: Can I add more cities?**
A: Yes. Edit `config.json` and add an entry to the `"cities"` list with the city name (exactly as it appears on Polymarket), the airport station code, latitude, longitude, and timezone.

**Q: Should I be worried about losing the $500?**
A: No — it's completely fake. None of your real money is involved at any step.

---

## What "Good" Results Look Like

After 100+ paper bets:
- **Win rate ~60%** with 10pt+ edges → edge is real
- **Positive total P&L after fees** → strategy is profitable
- **Calibration chart roughly diagonal** (model's 70% ≈ actual 70% wins) → model is reliable

If win rate is 45% after 100 bets: the strategy has a problem. Before risking real money, figure out what's wrong (model bias? resolution source disagreement? wrong station?)

---

## Safety Reminders

- This system makes ZERO real orders. No wallet needed. No API keys.
- It only reads free public data (Polymarket prices, weather forecasts).
- The system will never ask you to connect your Polymarket account.
- Even when you're ready for real trading, Polymarket blocks Australian users (VPN breaks their Terms of Service). Solve access first.

---

*Built June 2026. Questions? Run `python papertrader.py status` first — it shows everything at a glance.*
