#!/usr/bin/env python3
"""
Fetch and score news for tickers.
Usage: get_news.py TICKER1 TICKER2 ... [--since 24h] [--no-cache]

Providers:
- newsapi  (https://newsapi.org)
- finnhub  (https://finnhub.io)

Auth:
- NEWS_API_KEY
- optional NEWS_API_SOURCE (default: newsapi)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

CACHE_DIR = Path("workspace/news")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

ADVERSARIAL_KEYWORDS = (
    "short report",
    "short seller",
    "fraud",
    "sec investigation",
    "doj investigation",
    "class action",
    "regulatory action",
    "accounting irregular",
    "restatement",
    "bankruptcy",
)

MAJOR_KEYWORDS = (
    "earnings",
    "guidance",
    "merger",
    "acquisition",
    "m&a",
    "ceo",
    "cfo",
    "layoff",
    "dividend",
    "buyback",
)

MACRO_KEYWORDS = (
    "fed",
    "interest rate",
    "inflation",
    "recession",
    "gdp",
    "treasury",
    "oil",
)


def parse_since_window(since: str) -> datetime:
    """Parse windows like 24h, 2d, 90m into UTC datetime."""
    unit = since[-1].lower() if since else "h"
    value_text = since[:-1] if len(since) > 1 else "24"
    try:
        value = int(value_text)
    except ValueError:
        value = 24

    if value <= 0:
        value = 24

    if unit == "m":
        delta = timedelta(minutes=value)
    elif unit == "d":
        delta = timedelta(days=value)
    else:
        delta = timedelta(hours=value)

    return datetime.now(timezone.utc) - delta


def classify_text(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ADVERSARIAL_KEYWORDS):
        return "adversarial"
    if any(word in lowered for word in MAJOR_KEYWORDS):
        return "major"
    if any(word in lowered for word in MACRO_KEYWORDS):
        return "macro"
    return "relevant"


def fetch_json(url: str, timeout_s: int = 12) -> dict | list:
    req = Request(url, headers={"User-Agent": "risk-os-agent/1.0"})
    with urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_newsapi(ticker: str, api_key: str, since_dt: datetime) -> list[dict]:
    params = {
        "q": f'"{ticker}"',
        "language": "en",
        "sortBy": "publishedAt",
        "from": since_dt.isoformat().replace("+00:00", "Z"),
        "pageSize": 20,
        "apiKey": api_key,
    }
    payload = fetch_json("https://newsapi.org/v2/everything?" + urlencode(params))

    if not isinstance(payload, dict) or payload.get("status") != "ok":
        msg = payload.get("message", "NewsAPI request failed") if isinstance(payload, dict) else "NewsAPI request failed"
        raise RuntimeError(msg)

    out: list[dict] = []
    for article in payload.get("articles", []):
        if not isinstance(article, dict):
            continue
        title = (article.get("title") or "").strip()
        desc = (article.get("description") or "").strip()
        text = f"{title} {desc}".strip()
        if not text:
            continue
        out.append(
            {
                "ticker": ticker,
                "title": title,
                "source": (article.get("source") or {}).get("name") or "unknown",
                "url": article.get("url"),
                "publishedAt": article.get("publishedAt"),
                "score": classify_text(text),
            }
        )
    return out


def fetch_finnhub(ticker: str, api_key: str, since_dt: datetime) -> list[dict]:
    now = datetime.now(timezone.utc)
    params = {
        "symbol": ticker,
        "from": since_dt.date().isoformat(),
        "to": now.date().isoformat(),
        "token": api_key,
    }
    payload = fetch_json("https://finnhub.io/api/v1/company-news?" + urlencode(params))

    if isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(payload.get("error", "Finnhub request failed"))
    if not isinstance(payload, list):
        raise RuntimeError("Finnhub request failed")

    out: list[dict] = []
    for article in payload:
        if not isinstance(article, dict):
            continue
        title = (article.get("headline") or "").strip()
        summary = (article.get("summary") or "").strip()
        text = f"{title} {summary}".strip()
        if not text:
            continue

        timestamp = article.get("datetime")
        published_at = None
        if isinstance(timestamp, int):
            published_at = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat().replace("+00:00", "Z")

        out.append(
            {
                "ticker": ticker,
                "title": title,
                "source": article.get("source") or "finnhub",
                "url": article.get("url"),
                "publishedAt": published_at,
                "score": classify_text(text),
            }
        )
    return out


def deduplicate(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for item in items:
        key = item.get("url") or f"{item.get('ticker')}|{item.get('title')}|{item.get('publishedAt')}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def cache_path(source: str, ticker: str, since: str) -> Path:
    key = f"{source}|{ticker}|{since}".encode("utf-8")
    digest = hashlib.sha256(key).hexdigest()[:16]
    return CACHE_DIR / f"{source}_{ticker}_{digest}.json"


def load_cache(path: Path, ttl_minutes: int) -> list[dict] | None:
    if not path.exists():
        return None
    age = datetime.now(timezone.utc) - datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    if age > timedelta(minutes=ttl_minutes):
        return None
    try:
        data = json.loads(path.read_text())
        return data.get("headlines", []) if isinstance(data, dict) else None
    except Exception:
        return None


def write_cache(path: Path, headlines: list[dict]) -> None:
    payload = {
        "savedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "headlines": headlines,
    }
    path.write_text(json.dumps(payload))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("tickers", nargs="+")
    parser.add_argument("--since", default="24h")
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    tickers = [t.upper().strip() for t in args.tickers if t.strip()]
    since_dt = parse_since_window(args.since)

    api_key = os.environ.get("NEWS_API_KEY") or os.environ.get("NEWS_API_KEY_ALT")
    source = os.environ.get("NEWS_API_SOURCE", "newsapi").lower()
    ttl_minutes = int(os.environ.get("NEWS_CACHE_TTL_MIN", "15"))

    if not api_key:
        print(json.dumps({
            "headlines": [],
            "alerts": [],
            "error": "NEWS_API_KEY not set. Configure a provider key and retry.",
            "status": "No provider configured",
        }))
        return

    provider_map: dict[str, Callable[[str, str, datetime], list[dict]]] = {
        "newsapi": fetch_newsapi,
        "finnhub": fetch_finnhub,
    }

    provider = provider_map.get(source)
    if provider is None:
        supported = ", ".join(sorted(provider_map.keys()))
        print(json.dumps({
            "headlines": [],
            "alerts": [],
            "error": f"Unsupported NEWS_API_SOURCE='{source}'. Supported: {supported}",
        }))
        return

    headlines: list[dict] = []
    errors: list[str] = []
    cache_hits = 0

    for ticker in tickers:
        cpath = cache_path(source, ticker, args.since)
        if not args.no_cache:
            cached = load_cache(cpath, ttl_minutes=ttl_minutes)
            if cached is not None:
                headlines.extend(cached)
                cache_hits += 1
                continue

        try:
            fetched = provider(ticker, api_key, since_dt)
            headlines.extend(fetched)
            if not args.no_cache:
                write_cache(cpath, fetched)
        except Exception as exc:
            errors.append(f"{ticker}: {exc}")

    headlines = deduplicate(headlines)

    alerts = []
    for item in headlines:
        score = item.get("score")
        if score in ("adversarial", "major"):
            alerts.append(f"{item['ticker']}: {score} — {item['title']}")

    out = {
        "headlines": headlines,
        "alerts": alerts,
        "source": source,
        "since": args.since,
        "cache": {
            "enabled": not args.no_cache,
            "ttlMinutes": ttl_minutes,
            "hits": cache_hits,
        },
    }
    if errors:
        out["errors"] = errors

    print(json.dumps(out))


if __name__ == "__main__":
    main()
