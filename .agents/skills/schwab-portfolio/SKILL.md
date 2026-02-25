---
name: schwab-portfolio
description: Pull current positions, prices, P&L, and stops from Schwab API. Use when the agent needs portfolio data for monitoring, alerts, or Q&A.
metadata:
  openclaw:
    requires:
      env: ["SCHWAB_API_KEY", "SCHWAB_APP_SECRET"]
    primaryEnv: "SCHWAB_API_KEY"
---

# Schwab Portfolio

## Purpose

Fetch portfolio positions and account summary directly from Schwab Trader API via schwab-py. Fully self-contained; no external risk-os dependency.

## Tools

### get_positions

Returns current positions with: ticker, quantity, avg cost, current price, P&L, stop (if in local stops file).

**Invocation:** `python scripts/get_positions.py`

### get_account_summary

Returns account-level summary: total value, cash, buying power, daily P&L % (derived from Schwab `currentBalances.dailyProfitLoss` or `currentBalances.currentDayProfitLoss` when available).

**Invocation:** Same script returns both positions and summary in one call.

## Output Format

```json
{
  "positions": [
    {
      "ticker": "NVDA",
      "quantity": 100,
      "avgCost": 112.50,
      "currentPrice": 118.20,
      "pnl": 570.00,
      "pnlPct": 5.07,
      "stop": 105.00
    }
  ],
  "summary": {
    "totalValue": 50000,
    "cash": 5000,
    "dailyPnlPct": -0.5
  },
  "_stderr": "dailyProfitLoss not found in securitiesAccount.currentBalances (observed keys: [...])"
}
```

## Configuration

- `SCHWAB_API_KEY` — Schwab app key (from developer portal)
- `SCHWAB_APP_SECRET` — Schwab app secret
- `SCHWAB_CALLBACK_URL` — OAuth callback (default: `https://127.0.0.1/auth/schwab/callback`)
- `SCHWAB_TOKEN_PATH` — Path to token file (default: `workspace/portfolio/token.json`)
- `config/risk-rules.yaml` `schwab_order_detection`:
  - `active_statuses` (default: WORKING, AWAITING_STOP_CONDITION, QUEUED, PENDING_ACTIVATION)
  - `protective_order_types` (default: STOP, STOP_LIMIT, TRAILING_STOP)
  - `short_limit_as_stop_fallback` (carry-over compatibility flag from old app sync logic)

**First run:** Run `python scripts/auth_schwab.py` to complete OAuth flow. Token is saved to token path.

## Stops

Protective stops are fetched from Schwab API using `schwab_order_detection` config values. Default active statuses include `WORKING`, `AWAITING_STOP_CONDITION`, `QUEUED`, `PENDING_ACTIVATION`; default protective order types include `STOP`, `STOP_LIMIT`, `TRAILING_STOP`. Fallback: `workspace/portfolio/stops.json` for manual overrides.

## References

- [schwab-py](https://schwab-py.readthedocs.io/) — Schwab API client
- [risk-os](https://github.com/zijian-wang/risk-os) — Web-based risk calculator with Schwab integration (related project)
- [risk-os-v2-spec.md](/risk-os-v2-spec.md) — Data sources
