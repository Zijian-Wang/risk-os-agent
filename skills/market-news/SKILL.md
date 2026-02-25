---
name: market-news
description: Fetch and score news relevance to current holdings. Use when checking for adversarial research, major news, or position-relevant headlines.
metadata:
  openclaw:
    requires:
      env: ["NEWS_API_KEY", "NEWS_API_SOURCE"]
    primaryEnv: "NEWS_API_KEY"
---

# Market News

## Purpose

Fetch news for portfolio tickers. Score by relevance: position-relevant, adversarial (short reports, regulatory), macro. Hard alert on adversarial or major news; soft flag for general relevance.

## Tools

### get_news(tickers, since)

Returns scored headlines for the given tickers since the specified time.

**Invocation:** `python scripts/get_news.py TICKER1 TICKER2 ... --since 24h`

Disable cache for one run: `python scripts/get_news.py NVDA --since 24h --no-cache`

**News source:** `newsapi` and `finnhub` are supported. Set `NEWS_API_KEY`; choose provider with `NEWS_API_SOURCE` (default `newsapi`).

## Output Format

```json
{
  "headlines": [
    {
      "ticker": "NVDA",
      "title": "...",
      "source": "...",
      "url": "...",
      "score": "adversarial|major|relevant|macro",
      "publishedAt": "2026-02-25T..."
    }
  ],
  "alerts": ["NVDA: Short report published"]
}
```

## Scoring

- **adversarial** — Short reports, regulatory actions, litigation. Hard alert.
- **major** — Earnings, guidance, M&A. Hard alert if material.
- **relevant** — General company news. Soft flag.
- **macro** — Sector/market news affecting holdings. Soft flag.

## Status

Implemented providers:
- **NewsAPI.org** (`NEWS_API_SOURCE=newsapi`)
- **Finnhub** (`NEWS_API_SOURCE=finnhub`)

Responses are cached in `workspace/news/` (default TTL 15 minutes via `NEWS_CACHE_TTL_MIN`). Use `--no-cache` to bypass cache.

If `NEWS_API_KEY` is missing, the script returns a structured error and empty result.

## References

- [risk-os-v2-spec.md](/risk-os-v2-spec.md) — News: position-relevant only
