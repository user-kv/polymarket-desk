# 06 — Execution Venue: Polymarket Reality

**Status:** PLANNING ONLY. No build authorized.
**Scope:** Polymarket's API architecture, order mechanics, settlement, fees, and the operational realities of an AU user going live via VPN.

---

## 1. Architecture Overview

Polymarket exposes four distinct services. Understanding which to call and when is non-trivial — they have different authentication models, data formats, and update rates.

| Service | Base URL | Auth | Purpose |
|---|---|---|---|
| **Gamma API** | `https://gamma-api.polymarket.com` | None | Market discovery, metadata, volume, last prices |
| **CLOB API** | `https://clob.polymarket.com` | None (reads) / EIP-712 (writes) | Live order book, depth, price history, order placement |
| **Data API** | `https://data-api.polymarket.com` | None | User positions, trades, leaderboards |
| **Bridge API** | `https://bridge.polymarket.com` | — | Deposits/withdrawals via fun.xyz |

**The canonical workflow**: Gamma to discover markets and get token IDs → CLOB for live depth and trade execution → Data API to track positions and PnL.

---

## 2. The Gamma API (Read Only)

### 2.1 Key Endpoints

- `GET /markets` — paginated list of all markets. Returns `conditionId`, `slug`, `outcomes`, `outcomePrices`, `clobTokenIds`, `volume24hr`, `liquidity`, `endDate`, and more.
- `GET /markets/{id}` — single market detail.
- `GET /events` — event-level grouping (multiple related markets).

### 2.2 The Double-Parse Quirk (Critical)

Gamma ships `outcomes`, `outcomePrices`, and `clobTokenIds` as **JSON-encoded strings** inside the outer JSON object — not as native arrays. The raw response looks like:

```json
{
  "clobTokenIds": "[\"12345678\", \"87654321\"]",
  "outcomePrices": "[\"0.535\", \"0.465\"]"
}
```

If you do `market["clobTokenIds"][0]` you get the character `[`, not the first token ID. You must always double-parse:

```python
import json
token_ids = json.loads(market["clobTokenIds"])   # second parse
prices = [float(p) for p in json.loads(market["outcomePrices"])]
```

This is already handled in the existing `papertrader/lib/polymarket.py`. Do not regress it.

Additional Gamma gotchas:
- `volume` field is a stringified float — cast before comparison.
- Pagination uses `limit` + `offset` with no guaranteed stable ordering between calls.
- Prices returned are share prices in [0,1] range representing implied probability.

### 2.3 Market Identification

- `conditionId`: identifies the prediction market contract on-chain.
- `clobTokenIds`: two ERC-1155 token IDs — index 0 = YES outcome, index 1 = NO outcome.
- For trading, you need the token ID, not the condition ID. The CLOB endpoints operate on token IDs.

---

## 3. The CLOB API (Read + Trade)

### 3.1 Public Endpoints (No Auth)

- `GET /book?token_id=<id>` — full order book snapshot for a token. Returns bids/asks as arrays of `{price, size}` string pairs.
- `GET /price?token_id=<id>&side=<BUY|SELL>` — best executable price for a given side.
- `GET /midpoint?token_id=<id>` — mid between best bid and best ask.
- `GET /spread?token_id=<id>` — current bid-ask spread.
- `GET /prices-history?market=<token_id>&interval=<1m|1h|1d>` — price history. Note: the query param is named `market` despite taking a token_id (a naming inconsistency in the API).

All numeric values in CLOB responses are returned as quoted strings for precision. Always cast to `float` or `Decimal` before arithmetic.

### 3.2 Authentication (For Order Placement)

Polymarket uses a two-level auth system:

**L1 (Wallet / Private Key):**
- Sign an EIP-712 typed message with your Ethereum private key.
- Proves wallet ownership. Required to derive L2 credentials.
- Never sent repeatedly; used once to bootstrap.

**L2 (API Key):**
- `(apiKey, secret, passphrase)` tuple derived from your L1 signature.
- HMAC-SHA256 signing on API requests.
- Used for all trading operations. Can be rotated without re-signing L1.

**Wallet signature types:**

| Type | ID | Use Case |
|---|---|---|
| EOA | 0 | Standard hardware/software wallet |
| POLY_PROXY | 1 | Legacy Magic Link / Google login |
| GNOSIS_SAFE | 2 | Existing Safe multisig |
| POLY_1271 | 3 | New users with Polymarket deposit wallets (ERC-1271) |

**Known issue (2026):** POLY_1271 (type 3) users with a fresh EOA + deposit wallet encounter an auth binding problem — the L1 auth signs using the EOA address, producing an API key bound to the EOA, while orders set `signer=deposit_wallet`, causing 401 rejections. Monitor `github.com/Polymarket/py-clob-client-v2/issues/70` for resolution. Use EOA (type 0) with a direct funded wallet to avoid this.

### 3.3 Order Types

| Type | Code | Behaviour |
|---|---|---|
| Good Till Cancelled | GTC | Rests in book until filled or manually cancelled. The standard limit order. |
| Good Till Date | GTD | Same as GTC but auto-expires at a specified timestamp. |
| Fill or Kill | FOK | Must fill completely immediately or is cancelled. No partial fills. |
| Immediate or Cancel | IOC | Fills what it can immediately; any unfilled portion is cancelled. |

For the Institute's use case: **GTC limit orders are the correct default**. They avoid slippage from walking the book, provide maker rebates, and work with the Institute's non-urgent horizon (we are forecasting, not market-making).

### 3.4 Order Placement

Using `py-clob-client` (the official Python client):

```python
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, PartialCreateOrderOptions

client = ClobClient(
    host="https://clob.polymarket.com",
    chain_id=137,           # Polygon mainnet
    key=PRIVATE_KEY,        # L1 signing key (env var, never hardcoded)
    creds=api_creds,        # L2 creds object
    signature_type=0,       # Use EOA (type 0) for direct wallet
)

order = client.create_and_post_order(
    OrderArgs(
        token_id="12345678",   # YES token_id from Gamma
        price=0.62,            # limit price (share price, not odds)
        size=50,               # number of shares (= dollars if price ~$1)
        side="BUY",
    ),
    options=PartialCreateOrderOptions(
        tick_size="0.01",
        neg_risk=False,
    )
)
```

Key detail: `price` is the share price (0.62 = paying 62 cents per share = implied 62% probability). `size` is shares, not dollars. Dollar cost = `price × size`.

Batch order placement: up to 15 orders per call (increased from 5 in 2025). Useful for placing multiple concurrent GTC limits.

---

## 4. On-Chain Settlement

### 4.1 The Token Framework

Polymarket uses the **Conditional Token Framework (CTF)**, an ERC-1155 multi-token contract on Polygon. Each outcome is a distinct ERC-1155 token. When you buy YES shares:

1. USDC.e moves from your wallet to the CTF collateral pool.
2. ERC-1155 YES tokens are minted and sent to your wallet.
3. The corresponding NO tokens are sent to your counterparty (or minted from the pool).

The CLOB matches orders off-chain; the final atomic swap is submitted on-chain via the CTF Exchange contract (audited by ChainSecurity).

### 4.2 The UMA Resolution Process

When a market's resolution date arrives:

1. **Proposal**: Any address from Polymarket's whitelist (177 addresses as of 2026) posts a 750 USDC.e bond and proposes an outcome.
2. **Challenge window**: 2 hours during which anyone can dispute. ~93% of markets pass unchallenged.
3. **Unchallenged path**: UMA validates automatically. Payouts begin. Winning shares = $1.00 each; losing shares = $0.00.
4. **Challenged path**: Dispute escalated to UMA token holders. DVM voting runs 48–96 hours. Resolution typically takes 4–7 days total.
5. **On-chain settlement**: The CTF adapter burns your ERC-1155 tokens and releases USDC.e collateral. Funds arrive in your Polymarket deposit wallet.

**Automation implication**: Do not build settlement detection around fixed timestamps. Markets resolve asynchronously after end date. The Institute's settlement module should poll market status via Gamma API until `resolved=true` appears.

### 4.3 Gas Fees

Polygon L2 network. Polymarket subsidises most gas fees through meta-transactions. At small scale, gas is not a meaningful cost. There are no deposit or withdrawal fees from Polymarket itself; third-party on-ramps (Coinbase, MoonPay) may charge.

---

## 5. Fee Structure

Polymarket uses a **taker-only fee model**. Makers (resting limit orders that provide liquidity) pay zero fees and receive rebates.

### 5.1 Taker Fees (2026)

Fees are calculated per market category, assessed as a fraction of trade value. The formula produces a fee that peaks at the 50/50 price point and goes to zero at prices near 0 or 1.

Approximate fee rates at 50% probability (the maximum):

| Category | Max Taker Fee Rate |
|---|---|
| Geopolitics / World Events | **0%** (free) |
| Sports | ~0.75% (~$0.75 per 100 shares at 50¢) |
| Finance / Politics / Tech | ~1.00% |
| Crypto | ~1.80% (~$1.80 per 100 shares at 50¢) |
| Economics / Culture / Weather | ~1.25% |

The fee scales down toward 0% as the market price approaches 0 or 1 — meaning deep longshots (the Institute's NO-side strategy) are cheaper to trade than near-50% markets.

**Strategic implication**: Prefer markets in fee-free or low-fee categories when edge is equivalent. The NO-side longshot strategy (ask ≤ 0.15) is in the cheap fee zone by construction.

### 5.2 Maker Rebates

Limit orders that rest in the book (GTC orders that don't immediately match) receive a rebate of ~20–25% of the taker fee when they get filled. This effectively makes the Institute's preferred order type (GTC limit) a net-positive on fees when providing liquidity.

**Operational implication**: Always use GTC limit orders, never market orders. This gets you the maker rebate and avoids crossing the spread.

---

## 6. What Is Safely Automatable vs. Must Stay Manual

This is the most important operational table in the document. "Safe" means a bug is recoverable; "must stay manual" means a bug costs real money or legal exposure.

### 6.1 Automatable (Safe)

| Operation | Why Safe |
|---|---|
| Market scanning (Gamma API reads) | Read-only. No financial consequence. |
| Order book fetching (CLOB reads) | Read-only. |
| Forecast computation | Local computation, no side effects. |
| Gate 1/4 statistical assessment | Read from ledger, write assessment. No orders. |
| Paper trade ledger writes | Fake money. No on-chain effect. |
| Price history download | Read-only. |
| Settlement status polling | Read-only. |
| Generating order *recommendations* | No order placement; just a signal. |
| Sending alerts (Telegram/email) | Notification only. |
| Decay detection | Statistical read of ledger. No orders. |

### 6.2 Automatable with Guards

| Operation | Required Guards |
|---|---|
| Placing GTC limit orders | (1) Gate 4 graduated + user sign-off. (2) Position size check vs current bankroll. (3) Duplicate order check before placing. (4) Kill switch in code. (5) Daily loss cap. |
| Cancelling stale open orders | Only cancel orders the bot placed (track by order ID). Never cancel unknown orders. |
| Position reconciliation | Read-only; write only to internal ledger. |

### 6.3 Must Stay Manual (Human Required)

| Operation | Why Manual |
|---|---|
| Escalating a strategy from paper to real money | Explicit sign-off rule (see §7). Legal/financial risk. |
| Moving funds on-chain (deposits/withdrawals) | Irreversible. Private key operations. |
| Changing Kelly fraction or cap parameters | Parameter change = strategy change; requires Gate 4 re-entry. |
| Responding to a disputed market resolution | Requires judgement; UMA dispute mechanics are complex. |
| Any operation during a book-level drawdown halt | Human must review before resuming. |
| Increasing allocation tier (micro → scale) | Explicit tier promotion gate. |

---

## 7. VPN and Operational Realities for an AU User

This section is a candid assessment of the risk, not a recommendation.

### 7.1 The Legal Position

Australia restricts access to unlicensed interactive gambling platforms under the Interactive Gambling Act 2001. Polymarket is not licensed in Australia. ACMA (Australian Communications and Media Authority) has directed ISPs to block the site.

Using a VPN to access Polymarket from Australia:
- **Violates Polymarket's Terms of Service** (Section 2.1.4 explicitly prohibits VPN use to bypass geographic restrictions). This is a ToS violation, not necessarily a criminal act, but accounts detected via VPN are subject to permanent suspension and balance forfeiture.
- **Does not change the legal status of the activity** under Australian law. The user is accessing a blocked service regardless of VPN.
- **Is the user's explicit, informed choice.** The Institute's build stays fake-money and venue-agnostic. The decision to go live, with full understanding of these risks, belongs entirely to the user.

### 7.2 Practical VPN Risks

Polymarket has implemented VPN detection and has been expanding it. Specific risks:

- **Account suspension**: Detected VPN users face permanent suspension. Funds in an actively resolved position could become inaccessible.
- **KYC escalation**: Polymarket has added identity verification for some users. A flagged account may be asked to KYC with a photo ID before withdrawal, at which point Australian identity would likely trigger a block.
- **IP consistency**: Using multiple VPN exit nodes from different countries in the same session may trigger fraud detection.
- **Withdrawal risk**: If an account is suspended during a period when you have winning positions, recovering the USDC on-chain directly (bypassing the Polymarket interface) is theoretically possible through direct CTF interaction but requires sophisticated smart contract interaction.

### 7.3 Mitigations (If User Proceeds)

These are operational recommendations if the user chooses to go live, not an endorsement:

- Use a single, consistent VPN exit node (same city/country) for all Polymarket interactions.
- Maintain a low profile: no leaderboard chasing, no unusual activity patterns.
- Keep individual position sizes small enough that a suspension event doesn't produce a material loss.
- Maintain a separate funded Polygon wallet. Winning shares are yours on-chain even if the UI is blocked — but interacting with the CTF directly requires technical sophistication.
- Consider alternatives: Interactive Brokers' ForecastTrader platform is ASIC-licensed and accessible from Australia, though market depth and breadth is far inferior.

### 7.4 Impact on the Build

The Institute's code stays **venue-agnostic** throughout the paper phase:
- No hardcoded VPN dependencies.
- All Polymarket-specific calls are behind the `polymarket.py` client interface.
- Settlement uses Wunderground (not Polymarket's resolution) for the weather vertical — orthogonal to venue access.
- The execution layer is designed so a different venue can be substituted.

---

## 8. Automation Architecture (When Live)

The minimal safe automation stack for going live, derived from the above constraints:

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
Daily loss cap: if daily_pnl < -DAILY_LOSS_LIMIT, pause all writes until tomorrow
```

The kill switch is not optional. It must be the first check before any CLOB write.

---

## 9. Key References

- Polymarket API docs: `https://docs.polymarket.com/api-reference/introduction`
- CLOB fee schedule: `https://docs.polymarket.com/trading/fees`
- UMA resolution: `https://docs.polymarket.com/developers/resolution/UMA`
- py-clob-client: `https://github.com/Polymarket/py-clob-client`
- Geographic restrictions: `https://help.polymarket.com/en/articles/13364163-geographic-restrictions`
