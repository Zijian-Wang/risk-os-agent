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

| Phase | Condition | Meaning |
|-------|-----------|---------|
| 1 | Below both 10EMA and 30SMA | Avoid / very bearish |
| 2 | Above 10EMA, below 30SMA | Gaining momentum, watch |
| 3 | Above both 10EMA and 30SMA | Long entry zone |
| 4 | Phase 3 base + 10EMA > 30SMA + 10-period Hull is falling | Weakening while still structurally strong |
| 5 | Below 10EMA and above 30SMA | Pullback in strong trend; watch for breakdown |

Priority in script: **4, 1, 2, 3, 5**. If a ticker meets Phase 4 conditions, it is reported as Phase 4.

## Tools

### get_phase(ticker)

Returns phase 1–5, 10EMA, 30SMA, HMA values, and HMA cross signal for one ticker.

**Invocation:** `python scripts/get_phase.py <TICKER>`

### get_phases(tickers)

Returns phases for multiple tickers. Input: comma-separated or JSON array.

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

`hmaCross`: "bullish" | "bearish" | "neutral" (dead cross = bearish)
`hmaTrend`: "rising" | "falling" | "flat"

## Config

Read from `config/phase-config.yaml`: `ema_period`, `sma_period`, `hma_period`.

## Hard Alerts

Flag phase transitions 3→4 and 4→5. Flag HMA dead cross as soft flag.

## References

- [config/phase-config.yaml](/config/phase-config.yaml)
- [risk-os-v2-spec.md](/risk-os-v2-spec.md) — Phase system
