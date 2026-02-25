---
name: phase-analyzer
description: Compute phase (1-5) per ticker using 10EMA, 30SMA, HMA. Use when checking trend phase, phase transitions, or HMA dead cross for portfolio positions.
metadata:
  openclaw:
    requires:
      bins: ["python3"]
      env: []
---

# Phase Analyzer

## Purpose

Classify each position into phase 1–5 (James Boyd system) and detect HMA dead cross. Phase is one TA method among others; combine with RSI, MACD, etc. for full analysis.

## Phase Table (James Boyd Priority)

| Phase | Conditions | Meaning | Action |
|-------|------------|---------|--------|
| 1 | Close < 10EMA and Close < 30SMA | Broken support, downtrend | Avoid |
| 2 | Close > 10EMA and Close < 30SMA | Early recovery through resistance | Watch |
| 3 | Close > 10EMA and Close > 30SMA | Strong trend | Long entry zone |
| 4 | Phase 3 base + 10EMA > 30SMA + Hull is falling | Technically strong but weakening | Watch closely |
| 5 | Close < 10EMA and Close > 30SMA | Pullback in uptrend | Caution |

Priority in script: **4, 1, 2, 3, 5**. If a ticker meets Phase 4 conditions, it is reported as Phase 4.

## Tools

### get_phase(ticker)

Returns phase 1–5, 10EMA, 30SMA, HMA values, and HMA cross signal for one ticker.

**Invocation:** `python scripts/get_phase.py <TICKER>`

### get_phases(tickers)

Returns phases for multiple tickers using one batched yfinance download call. Input: comma-separated or JSON array.

**Invocation:** `python scripts/get_phases.py TICKER1 TICKER2 ...`

### get_ta(ticker, indicators[])

Optional. Returns additional indicators (RSI, MACD, etc.) when configured in `config/ta-config.yaml`.

**Invocation:** `python scripts/get_ta.py <TICKER> [--indicators rsi,macd]`

## Output Format

```json
{
  "ticker": "NVDA",
  "phase": 3,
  "price": 118.20,
  "ema10": 116.50,
  "sma30": 114.20,
  "hma": 115.80,
  "hmaPrev": 115.92,
  "hmaTrend": "falling",
  "hmaCross": "neutral",
  "previousPhase": 2
}
```

`hmaCross`: "bullish" | "bearish" | "neutral" (dead cross = bearish). Uses prior close vs prior HMA: bearish when `prev_close >= hmaPrev and price < hma`; bullish when `prev_close <= hmaPrev and price > hma`. For single-bar histories, `prev_close` falls back to current `price`.
`hmaTrend`: "rising" | "falling" | "flat"

## Config

Read from `config/phase-config.yaml`: `ema_period`, `sma_period`, `hma_period`.

## Data Source

Current implementation uses yfinance for candles/indicators. Target architecture is Schwab price history API as primary with Stooq fallback.

## Hard Alerts

Hard transition alerts come from `config/risk-rules.yaml` `hard_alerts.phase_transition_pairs` (default: 3→4 and 4→5). Flag HMA dead cross as soft flag.

## References

- [config/phase-config.yaml](/config/phase-config.yaml)
- [risk-os-v2-spec.md](/risk-os-v2-spec.md) — Phase system
