---
name: risk-calculator
description: Compute stop proximity, portfolio drawdown, and exposure. Use when checking if positions are near stops, portfolio daily P&L, or risk flags for alerts.
metadata:
  openclaw:
    requires:
      bins: ["python3"]
---

# Risk Calculator

## Purpose

Consumes positions from schwab-portfolio and phase data from phase-analyzer. Computes stop proximity, drawdown, and portfolio-level exposure for hard alerts and soft flags.

## Tools

### check_stops(positions)

Returns positions approaching or at stop loss. Uses `config/risk-rules.yaml` for `stop_approaching_pct`.

**Invocation:** `python scripts/check_stops.py` (reads positions from stdin or workspace/portfolio/positions.json)

### portfolio_drawdown(positions)

Returns portfolio daily P&L % and drawdown metrics.

**Invocation:** `python scripts/portfolio_drawdown.py`

### exposure_summary(positions)

Returns portfolio-level risk exposure, sector concentration, re-eval flags.

**Invocation:** `python scripts/exposure_summary.py`

## Input

Positions JSON from schwab-portfolio. Expected format:
```json
{
  "positions": [
    {"ticker": "NVDA", "quantity": 100, "avgCost": 112.50, "currentPrice": 118.20, "stop": 105.00}
  ],
  "summary": {"totalValue": 50000, "dailyPnlPct": -0.5}
}
```

## Output Format

check_stops:
```json
{
  "alerts": [
    {"ticker": "XYZ", "currentPrice": 102, "stop": 100, "pctToStop": 2.0, "status": "approaching"}
  ]
}
```

portfolio_drawdown:
```json
{
  "dailyPnlPct": -0.5,
  "alert": true,
  "drawdownPct": 3.2
}
```

## Hard Alerts

- Portfolio daily P&L < -1% (from risk-rules)
- Any position at or within stop_approaching_pct of stop

## Config

Read from `config/risk-rules.yaml`.

## References

- [config/risk-rules.yaml](/config/risk-rules.yaml)
- [AGENTS.md](/AGENTS.md) — Use decimal for money math
