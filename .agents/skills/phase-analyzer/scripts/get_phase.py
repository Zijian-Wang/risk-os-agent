#!/usr/bin/env python3
"""
Compute phase (1-5) for a ticker using James Boyd phase logic.
Uses yfinance for price data when no API key is set.
Requires: pip install yfinance pyyaml
"""

import json
import sys

from phase_core import analyze_closes, dump_error_and_exit


def main():
    if len(sys.argv) < 2:
        dump_error_and_exit("Usage: get_phase.py TICKER")

    ticker = sys.argv[1].upper()

    try:
        import yfinance as yf
    except ImportError:
        dump_error_and_exit("yfinance required: pip install yfinance", ticker=ticker)

    hist = yf.download(ticker, period="3mo", interval="1d", progress=False, auto_adjust=True)
    if hist.empty or "Close" not in hist:
        dump_error_and_exit("Insufficient data", ticker=ticker)

    closes = hist["Close"].dropna().tolist()
    out = analyze_closes(ticker=ticker, closes=closes)

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
    if "error" in out:
        print(json.dumps(out))
        sys.exit(1)

    print(json.dumps(out))


if __name__ == "__main__":
    main()
