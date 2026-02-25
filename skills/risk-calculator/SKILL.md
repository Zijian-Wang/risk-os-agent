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

Returns positions approaching or at stop loss. Uses `config/risk-rules.yaml` `hard_alerts.stop_approaching_pct`.

**Invocation:** `python scripts/check_stops.py` (reads positions from stdin or workspace/portfolio/positions.json)

### portfolio_drawdown(positions)

Returns portfolio daily P&L % and drawdown metrics. Uses `hard_alerts.portfolio_daily_down_pct`.

**Invocation:** `python scripts/portfolio_drawdown.py`

### exposure_summary(positions)

Returns portfolio-level risk exposure, sector concentration, re-eval flags. Uses `soft_flags.concentration_warn_pct`.

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

- Portfolio daily P&L < `-hard_alerts.portfolio_daily_down_pct`
- Any position at or within `hard_alerts.stop_approaching_pct` of stop
- Phase transitions in `hard_alerts.phase_transition_pairs` are consumed by the morning brief pipeline

## Config

Read from `config/risk-rules.yaml`:
- `risk_per_trade.default_pct` (default account risk baseline, from old app)
- `hard_alerts.portfolio_daily_down_pct`
- `hard_alerts.stop_approaching_pct`
- `hard_alerts.phase_transition_pairs`
- `soft_flags.concentration_warn_pct`

## References

- [config/risk-rules.yaml](/config/risk-rules.yaml)
- [AGENTS.md](/AGENTS.md) — Use decimal for money math
