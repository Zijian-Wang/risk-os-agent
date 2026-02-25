#!/usr/bin/env python3
"""
Fetch news for tickers. Placeholder until NEWS_API_KEY is configured.
Usage: get_news.py TICKER1 TICKER2 ... [--since 24h]
"""

import argparse
import json
import os
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("tickers", nargs="+")
    parser.add_argument("--since", default="24h")
    args = parser.parse_args()

    api_key = os.environ.get("NEWS_API_KEY") or os.environ.get("NEWS_API_KEY_ALT")
    if not api_key:
        print(json.dumps({
            "headlines": [],
            "alerts": [],
            "error": "NEWS_API_KEY not set. Configure a news API (NewsAPI, Benzinga, Finnhub) and set the key.",
        }))
        return

    # Placeholder: when API is chosen, implement fetch + scoring here
    # For now return empty; agent knows to use web search as fallback
    print(json.dumps({
        "headlines": [],
        "alerts": [],
        "status": "News API integration TBD. Use web search for manual checks.",
    }))


if __name__ == "__main__":
    main()
