## CHANGELOG
- **2026-06-30 red-team + hardening pass** (rubric Tiers 1-2):
  - Elevated VPN/forfeiture risk from a §7 sidebar to the document's primary risk warning. Per 2026 reporting: accounts detected via VPN face **permanent suspension with no appeal process and full balance forfeiture**. This can zero the account independently of trading edge — it dominates all other risks at small capital.
  - Added concrete 2025-2026 UMA dispute facts: 1,150+ disputes in 2026 YTD; single actor manipulated $7M contract with 25% of UMA voting power; >60% of active UMA voters linked to Polymarket accounts with live positions (conflict-of-interest risk is systemic, not theoretical).
  - Sized the UMA/oracle risk explicitly: disputed markets can take 4–7 days with an uncertain outcome. At small capital the dollar impact per dispute is manageable but the tail scenario (governance attack on a large position) is real.
  - Corrected fee rates to 2026 actuals (dynamic fee model effective 3pm ET April 3, 2026).
  - Removed maker-rebate reliance as a guaranteed cost offset — rebate requires resting in the book; fast-moving markets may fill as taker. Flagged appropriately.
  - Added KYC escalation path as a distinct risk channel (AU identity → block at withdrawal stage even if not suspended earlier).
  - POLY_1271 auth bug status updated (still open as of 2026; EOA type 0 recommendation unchanged).

---

# 06 — Execution Venue: Polymarket Reality

**Status:** PLANNING ONLY. No build authorized.
**Scope:** Polymarket's API architecture, order mechanics, settlement, fees, and the operational realities of an AU user going live via VPN.

---

## !! PRIORITY WARNING: VENUE FORFEITURE RISK !!

**Before reading anything else:** for an AU user accessing Polymarket via VPN, the single largest risk is not a bad trade — it is **account suspension with full balance forfeiture**.

As of May 2026, Polymarket employs device fingerprinting, browser-based detection, behavioural analysis, and VPN IP-range blocking. Accounts detected as originating from a restricted jurisdiction via VPN are subject to **permanent suspension with no appeal process and full fund forfeiture**. [Source: TechRadar, Gizmodo, 2026 reporting; Polymarket ToS §2.1.4]

This event:
- Is independent of trading edge or gate status.
- Zeroes the entire balance, not just the current position.
- Can occur at any time, including during a period of open winning positions.
- Cannot be appealed under current Polymarket policy.

**At $500 bankroll: this risk is 100% loss of $500.** At any bankroll size, it is a single-event ruin. The mitigations in §7 reduce (not eliminate) detection probability. The decision to go live belongs entirely to the user, made with full awareness of this risk.

On-chain recovery of winning positions (via direct CTF interaction) is theoretically possible but requires advanced smart-contract knowledge and is not reliable when the account/UI is blocked. Do not plan around it.

---

## 1. Architecture Overview

Polymarket exposes four distinct services with different auth models, data formats, and update rates.

| Service | Base URL | Auth | Purpose |
|---|---|---|---|
| Gamma API | `https://gamma-api.polymarket.com` | None | Market discovery, metadata, volume, last prices |
| CLOB API | `https://clob.polymarket.com` | None (reads) / EIP-712 (writes) | Live order book, depth, price history, order placement |
| Data API | `https://data-api.polymarket.com` | None | User positions, trades, leaderboards |
| Bridge API | `https://bridge.polymarket.com` | — | Deposits/withdrawals via fun.xyz |

**Canonical workflow:** Gamma → discover markets and get token IDs → CLOB → live depth and execution → Data API → track positions and PnL.

---

## 2. The Gamma API (Read Only)

### 2.1 Key Endpoints

- `GET /markets` — paginated list. Returns `conditionId`, `slug`, `outcomes`, `outcomePrices`, `clobTokenIds`, `volume24hr`, `liquidity`, `endDate`.
- `GET /markets/{id}` — single market detail.
- `GET /events` — event-level grouping.

### 2.2 The Double-Parse Quirk (Critical)

Gamma ships `outcomes`, `outcomePrices`, and `clobTokenIds` as **JSON-encoded strings** inside the outer JSON — not as native arrays:

```json
{
  "clobTokenIds": "[\"12345678\", \"87654321\"]",
  "outcomePrices": "[\"0.535\", \"0.465\"]"
}
```

Always double-parse:

```python
import json
token_ids = json.loads(market["clobTokenIds"])
prices = [float(p) for p in json.loads(market["outcomePrices"])]
```

Already handled in `papertrader/lib/polymarket.py`. Do not regress it.

Additional gotchas: `volume` is a stringified float. Pagination uses `limit` + `offset` with no stable ordering. Prices are share prices in [0,1].

### 2.3 Market Identification

- `conditionId`: on-chain prediction market contract identifier.
- `clobTokenIds`: two ERC-1155 token IDs — index 0 = YES, index 1 = NO.
- CLOB endpoints operate on token IDs, not condition IDs.

---

## 3. The CLOB API (Read + Trade)

### 3.1 Public Endpoints (No Auth)

- `GET /book?token_id=<id>` — full order book snapshot. Returns bids/asks as `{price, size}` string pairs.
- `GET /price?token_id=<id>&side=<BUY|SELL>` — best executable price.
- `GET /midpoint?token_id=<id>` — mid between best bid and ask.
- `GET /spread?token_id=<id>` — current bid-ask spread.
- `GET /prices-history?market=<token_id>&interval=<1m|1h|1d>` — price history. Note: param is named `market` despite taking a token_id.

All CLOB numeric values returned as quoted strings. Always cast to `float` or `Decimal` before arithmetic.

### 3.2 Authentication (For Order Placement)

**L1 (Wallet / Private Key):** Sign an EIP-712 typed message with your Ethereum private key. Proves wallet ownership. Used once to bootstrap L2 credentials.

**L2 (API Key):** `(apiKey, secret, passphrase)` derived from L1 signature. HMAC-SHA256 signing on API requests. Used for all trading.

| Wallet Type | ID | Use Case |
|---|---|---|
| EOA | 0 | Standard hardware/software wallet |
| POLY_PROXY | 1 | Legacy Magic Link / Google login |
| GNOSIS_SAFE | 2 | Existing Safe multisig |
| POLY_1271 | 3 | New users with deposit wallets (ERC-1271) |

**Known issue (still open 2026):** POLY_1271 (type 3) users with fresh EOA + deposit wallet encounter an auth binding problem — L1 auth signs using EOA, producing an API key bound to EOA, while orders set `signer=deposit_wallet`, causing 401 rejections. Use EOA (type 0) with a directly funded wallet to avoid this. Monitor `github.com/Polymarket/py-clob-client-v2/issues/70`.

### 3.3 Order Types

| Type | Code | Behaviour |
|---|---|---|
| Good Till Cancelled | GTC | Rests in book until filled or manually cancelled. Default. |
| Good Till Date | GTD | Same as GTC but auto-expires at a timestamp. |
| Fill or Kill | FOK | Must fill completely immediately or cancelled. |
| Immediate or Cancel | IOC | Fills what it can immediately; unfilled portion cancelled. |

**Use GTC limit orders as the default.** Avoids slippage, earns potential maker rebate, fits the Institute's non-urgent horizon.

### 3.4 Order Placement

```python
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, PartialCreateOrderOptions

client = ClobClient(
    host="https://clob.polymarket.com",
    chain_id=137,           # Polygon mainnet
    key=PRIVATE_KEY,        # L1 signing key (env var, never hardcoded)
    creds=api_creds,        # L2 creds object
    signature_type=0,       # EOA (type 0) for direct wallet
)

order = client.create_and_post_order(
    OrderArgs(
        token_id="12345678",
        price=0.62,            # share price (0.62 = 62¢ = 62% implied probability)
        size=50,               # shares (≈ dollars when price ~$1)
        side="BUY",
    ),
    options=PartialCreateOrderOptions(tick_size="0.01", neg_risk=False)
)
```

`price` is share price; `size` is shares; dollar cost = `price × size`. Batch placement: up to 15 orders per call.

---

## 4. On-Chain Settlement

### 4.1 The Token Framework

Polymarket uses the **Conditional Token Framework (CTF)**, ERC-1155 on Polygon. Buying YES shares:
1. USDC.e moves to CTF collateral pool.
2. ERC-1155 YES tokens minted to your wallet.
3. Corresponding NO tokens go to counterparty.

CLOB matches orders off-chain; final atomic swap submitted on-chain via the CTF Exchange contract (audited by ChainSecurity).

### 4.2 The UMA Resolution Process — Sizing the Oracle Risk

When a market reaches resolution date:

1. **Proposal:** Whitelisted address (177 addresses as of 2026) posts 750 USDC.e bond and proposes an outcome.
2. **Challenge window:** 2 hours. ~93% of markets pass unchallenged.
3. **Unchallenged path:** UMA validates automatically. Winning shares = $1.00; losing = $0.00.
4. **Challenged path:** Escalated to UMA token holder vote (DVM). Takes 48–96 hours. Resolution 4–7 days total.
5. **On-chain settlement:** CTF adapter burns tokens and releases USDC.e to your deposit wallet.

**Oracle risk is not theoretical — it is live and systemic (2025-2026 facts):**
- Polymarket logged 1,150+ disputed markets in 2026 YTD, already exceeding the full-year 2025 total. [Source: Polymarket documentation, KuCoin reporting]
- In March 2025, a single actor using 25% of UMA voting power falsely settled a $7M contract. [Source: The Defiant, CoinDesk]
- A Wall Street Journal investigation found >60% of active UMA voters could be linked to live Polymarket accounts — voters with financial stakes in markets they are ruling on. Conflict-of-interest is systemic, not isolated. [Source: KuCoin/WSJ reporting]

**Sizing this risk at the Institute's scale:**
- A disputed market freezes your capital for 4–7 days.
- A manipulated vote could resolve a market against the objectively correct outcome.
- At $50 per position, the dollar impact of a single bad dispute is bounded. At $500 per position, it is material.
- **Mitigation:** CELL_CAP of 10% limits single-market exposure. The real concern is a cluster of markets sharing the same resolution event (e.g., all political markets on the same election) — they may dispute simultaneously.

Do not build settlement detection around fixed timestamps. Markets resolve asynchronously. Poll Gamma API for `resolved=true`.

### 4.3 Gas Fees

Polygon L2. Polymarket subsidises most gas via meta-transactions. At small scale, gas is not a meaningful cost.

---

## 5. Fee Structure (2026 Actuals)

Dynamic fee model effective 3pm ET, April 3, 2026. Taker-only model — makers pay zero fees.

### 5.1 Taker Fees

Fees peak at the 50¢ price point and fall toward 0% at prices near 0 or 1. Approximate max taker fee rates:

| Category | Max Taker Fee Rate |
|---|---|
| Geopolitics / World Events | **0%** (free) |
| Sports | ~0.75% |
| Finance / Politics / Tech | ~1.00% |
| Economics / Culture / Weather | ~1.25% |
| Crypto | ~1.80% |

**NO-side longshot strategy (ask ≤ 0.15):** Fee rate at prices near 0.15 is well below the category maximum. The longshot strategy is in the cheap fee zone by design.

**Net-edge requirement:** All Kelly sizing must use net-of-fee edge. See `05_RISK_AND_PORTFOLIO.md §2.4` for the formula.

### 5.2 Maker Rebates

GTC limit orders that rest in the book and get filled receive a rebate of ~25% of the taker fee (20% for crypto). Rebates distributed daily; minimum $1 USDC threshold.

**Caveat:** Rebate is not guaranteed on every GTC order. If the market moves and your limit is immediately matched as a taker (latent taker), you pay the taker fee. Do not assume maker economics in the sizing model; treat rebate as a positive offset when it accrues.

---

## 6. What Is Safely Automatable vs. Must Stay Manual

"Safe" = a bug is recoverable. "Must stay manual" = a bug costs real money or triggers legal exposure.

### 6.1 Automatable (Safe)

| Operation | Why Safe |
|---|---|
| Market scanning (Gamma reads) | Read-only |
| Order book fetching (CLOB reads) | Read-only |
| Forecast computation | Local, no side effects |
| Gate 1/4 statistical assessment | Ledger read, no orders |
| Paper trade ledger writes | Fake money, no on-chain effect |
| Settlement status polling | Read-only |
| Generating order recommendations | Signal only, no placement |
| Sending alerts (Telegram/email) | Notification only |
| Decay detection | Statistical ledger read, no orders |

### 6.2 Automatable with Guards

| Operation | Required Guards |
|---|---|
| Placing GTC limit orders | (1) Gate 4 graduated + user sign-off. (2) Position size check vs current bankroll. (3) Duplicate order check. (4) Kill switch active. (5) Daily loss cap. |
| Cancelling stale open orders | Only cancel orders the bot placed (track by order ID). Never cancel unknown orders. |
| Position reconciliation | Read-only; write only to internal ledger. |

### 6.3 Must Stay Manual

| Operation | Why Manual |
|---|---|
| Escalating from paper to real money | Explicit sign-off rule. Legal/financial risk. |
| Moving funds on-chain (deposits/withdrawals) | Irreversible private key operations |
| Changing Kelly fraction or cap parameters | Parameter change = strategy change; Gate 4 re-entry required |
| Responding to a disputed market resolution | UMA mechanics require judgement; automated response could worsen outcome |
| Any operation during a book-level drawdown halt | Human review required |
| Increasing allocation tier (micro → scale) | Explicit tier promotion gate |

---

## 7. VPN and Operational Realities for an AU User

**This section is a candid assessment of risk, not an endorsement or recommendation.**

### 7.1 The Legal and ToS Position

Australia restricts access to unlicensed interactive gambling platforms under the Interactive Gambling Act 2001. Polymarket is not licensed in Australia. ACMA has directed ISPs to block the site.

Using a VPN to access Polymarket from Australia:
- **Violates Polymarket's Terms of Service** (§2.1.4 explicitly prohibits VPN use to bypass geographic restrictions). Detected accounts face **permanent suspension and full balance forfeiture, with no appeal process.**
- **Does not change the user's legal position** under Australian law.
- **Is the user's explicit, informed choice.** The Institute's build stays fake-money and venue-agnostic throughout the paper phase. The decision to go live belongs entirely to the user.

### 7.2 Practical VPN Risks (2026 Reality)

Polymarket now employs VPN IP-range blocking, device fingerprinting, browser detection, and behavioural analysis. As of May 2026, enforcement is active and expanding.

Specific risk channels:
- **Account suspension + forfeiture:** Permanent, no appeal, full balance. This is the single largest risk.
- **KYC escalation:** A flagged account may be asked to KYC with photo ID before withdrawal. Australian identity at this stage triggers a block — you cannot withdraw even existing winnings.
- **IP consistency:** Multiple VPN exit nodes from different countries in the same session may trigger fraud detection.
- **Open-position suspension:** If suspended while holding winning positions, recovery requires direct CTF interaction (burning ERC-1155 tokens to redeem USDC.e). This is theoretically possible but practically complex and not reliable when the UI/account is blocked.

### 7.3 Mitigations (If User Proceeds to Live)

These reduce detection probability; they do not eliminate it:
- Use a single, consistent VPN exit node (same city/country) for all Polymarket interactions. Never switch nodes mid-session.
- Maintain a low profile: no leaderboard activity, no unusual trading volume patterns.
- Keep individual position sizes small enough that a full-account suspension produces a loss the user can absorb. **Do not deposit more than you can afford to lose entirely to a non-trading event.**
- Maintain a funded Polygon wallet separately. Winning shares exist on-chain even if the UI is blocked — but direct CTF redemption requires technical sophistication.
- Consider ForecastEx / Kalshi (CFTC-regulated, AU-accessible) as partial alternatives for certain verticals, noting substantially lower market depth and breadth.

### 7.4 Impact on the Build

The Institute's code stays **venue-agnostic** throughout the paper phase:
- No hardcoded VPN dependencies.
- All Polymarket-specific calls behind the `polymarket.py` client interface.
- Settlement uses Wunderground for the weather vertical — orthogonal to venue access.
- Execution layer designed for venue substitution.

---

## 8. Automation Architecture (When Live)

The minimal safe automation stack:

```
Cron (GCP VM, every 30 min)
  → scan_markets()        [Gamma read — safe]
  → compute_forecasts()   [local — safe]
  → evaluate_gates()      [ledger read — safe]
  → generate_signals()    [local — safe]
  → [IF cell graduated + user_signed_off]
      → check_open_positions()    [CLOB read — safe]
      → place_limit_orders()      [CLOB write — guarded]
      → log_orders_to_ledger()    [local write — safe]
  → alert_user()          [notification — safe]

Kill switch: env var LIVE_TRADING_ENABLED=false disables all CLOB writes
Daily loss cap: if daily_pnl < -DAILY_LOSS_LIMIT, pause all writes until next day
```

The kill switch is not optional. It must be the first check before any CLOB write.

---

## 9. Key References

- Polymarket API docs: `https://docs.polymarket.com/api-reference/introduction`
- CLOB fee schedule: `https://docs.polymarket.com/trading/fees`
- UMA resolution: `https://docs.polymarket.com/developers/resolution/UMA`
- py-clob-client: `https://github.com/Polymarket/py-clob-client`
- Geographic restrictions: `https://help.polymarket.com/en/articles/13364163-geographic-restrictions`
- Maker rebates: `https://help.polymarket.com/en/articles/13364471-maker-rebates-program`
- UMA dispute controversy (2025): `https://thedefiant.io/news/markets/usd85m-polymarket-dispute-over-strategy-s-may-bitcoin-sale-puts-uma-s-token-voting-oracle-on`
- VPN enforcement (2026): `https://www.techradar.com/vpn/vpn-privacy-security/polymarket-blocks-vpns-and-tightens-identity-verification-as-over-30-countries-ban-the-betting-platform`
