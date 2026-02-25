#!/usr/bin/env python3
"""
Compute phases for multiple tickers with one batched yfinance download call.
Usage: get_phases.py TICKER1 TICKER2 ...
"""

from __future__ import annotations

import json
import sys

import pandas as pd

from phase_core import analyze_closes, dump_error_and_exit, load_config


def _extract_closes(hist: pd.DataFrame, ticker: str) -> list[float]:
    if hist.empty:
        return []

    # Batched call with group_by='ticker' returns MultiIndex columns.
    if isinstance(hist.columns, pd.MultiIndex):
        if ticker in hist.columns.get_level_values(0):
            series = hist[ticker]["Close"]
            return series.dropna().tolist()
        return []

    # Single-ticker shape fallback.
    if "Close" in hist:
        return hist["Close"].dropna().tolist()

    return []


def main():
    if len(sys.argv) < 2:
        dump_error_and_exit("Usage: get_phases.py TICKER1 TICKER2 ...")

    tickers = [t.upper() for t in sys.argv[1:]]

    try:
        import yfinance as yf
    except ImportError:
        print(
            json.dumps(
                {
                    "phases": [
                        {"ticker": ticker, "error": "yfinance required: pip install yfinance"}
                        for ticker in tickers
                    ]
                }
            )
        )
        sys.exit(1)

    hist = yf.download(
        tickers,
        period="3mo",
        interval="1d",
        group_by="ticker",
        progress=False,
        auto_adjust=True,
    )

    cfg = load_config()
    results = []
    for ticker in tickers:
        closes = _extract_closes(hist, ticker)
        results.append(analyze_closes(ticker=ticker, closes=closes, cfg=cfg))

    print(json.dumps({"phases": results}))


if __name__ == "__main__":
    main()
