#!/usr/bin/env python3
"""
Compute phase (1-5) for a ticker using James Boyd phase logic.
Uses yfinance for price data when no API key is set.
Requires: pip install yfinance pyyaml
"""

import json
import sys
from pathlib import Path

# Add repo root for config
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))


def load_config():
    import yaml
    cfg_path = REPO_ROOT / "config" / "phase-config.yaml"
    if cfg_path.exists():
        with open(cfg_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def ema(prices: list[float], period: int) -> float:
    """Exponential moving average. Deterministic."""
    if not prices or len(prices) < period:
        return prices[-1] if prices else 0.0
    k = 2 / (period + 1)
    ema_val = sum(prices[:period]) / period
    for p in prices[period:]:
        ema_val = (p - ema_val) * k + ema_val
    return round(ema_val, 4)


def sma(prices: list[float], period: int) -> float:
    """Simple moving average. Deterministic."""
    if not prices or len(prices) < period:
        return prices[-1] if prices else 0.0
    return round(sum(prices[-period:]) / period, 4)


def wma(prices: list[float], period: int) -> float:
    """Weighted moving average. Deterministic."""
    if not prices or len(prices) < period:
        return prices[-1] if prices else 0.0
    window = prices[-period:]
    weights = list(range(1, period + 1))
    return round(sum(w * p for w, p in zip(weights, window)) / sum(weights), 4)


def hma(prices: list[float], period: int) -> float:
    """Hull Moving Average. Deterministic. Uses WMA(2*WMA(n/2)-WMA(n), sqrt(n))."""
    half = max(1, period // 2)
    sqrt_period = max(1, int(period ** 0.5))
    if not prices or len(prices) < period + sqrt_period:
        return round(prices[-1], 4) if prices else 0.0
    raw_vals = []
    for i in range(period - 1, len(prices)):
        window = prices[: i + 1]
        w1 = wma(window, half)
        w2 = wma(window, period)
        raw_vals.append(2 * w1 - w2)
    return round(wma(raw_vals, sqrt_period), 4)


def get_phase(price: float, ema10: float, sma30: float, hma_val: float, hma_prev: float) -> int:
    """Phase 1-5 with explicit priority: 4, 1, 2, 3, 5."""
    phase3_base = price > ema10 and price > sma30
    hma_falling = hma_val < hma_prev

    if phase3_base and ema10 > sma30 and hma_falling:
        return 4
    if price < ema10 and price < sma30:
        return 1
    if price > ema10 and price < sma30:
        return 2
    if phase3_base:
        return 3
    if price < ema10 and price > sma30:
        return 5
    # Equality edge-cases are treated as caution.
    return 5


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: get_phase.py TICKER"}))
        sys.exit(1)

    ticker = sys.argv[1].upper()
    cfg = load_config()
    ema_p = cfg.get("ema_period", 10)
    sma_p = cfg.get("sma_period", 30)
    hma_p = cfg.get("hma_period") or max(ema_p, sma_p)

    try:
        import yfinance as yf
    except ImportError:
        print(json.dumps({
            "error": "yfinance required: pip install yfinance",
            "ticker": ticker
        }))
        sys.exit(1)

    hist = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=True)
    if hist.empty or len(hist) < sma_p:
        print(json.dumps({"error": "Insufficient data", "ticker": ticker}))
        sys.exit(1)

    closes = hist["Close"].tolist()
    price = closes[-1]
    ema10_val = ema(closes, ema_p)
    sma30_val = sma(closes, sma_p)
    hma_val = hma(closes, hma_p)

    hma_prev = hma(closes[:-1], hma_p) if len(closes) > 1 else hma_val
    phase = get_phase(price, ema10_val, sma30_val, hma_val, hma_prev)

    prev_price = closes[-2] if len(closes) > 1 else price

    # HMA cross: detect price crossing through HMA using prior close vs prior HMA.
    if prev_price >= hma_prev and price < hma_val:
        hma_cross = "bearish"
    elif prev_price <= hma_prev and price > hma_val:
        hma_cross = "bullish"
    else:
        hma_cross = "neutral"

    if hma_val < hma_prev:
        hma_trend = "falling"
    elif hma_val > hma_prev:
        hma_trend = "rising"
    else:
        hma_trend = "flat"

    out = {
        "ticker": ticker,
        "phase": phase,
        "price": round(price, 2),
        "ema10": ema10_val,
        "sma30": sma30_val,
        "hma": hma_val,
        "hmaPrev": hma_prev,
        "hmaTrend": hma_trend,
        "hmaCross": hma_cross,
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
