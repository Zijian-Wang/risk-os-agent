---
name: market-news
description: Fetch and score news relevance to current holdings. Use when checking for adversarial research, major news, or position-relevant headlines.
metadata:
  openclaw:
    requires:
      env: ["NEWS_API_KEY"]
    primaryEnv: "NEWS_API_KEY"
---

# Market News

## Purpose

Fetch news for portfolio tickers. Score by relevance: position-relevant, adversarial (short reports, regulatory), macro. Hard alert on adversarial or major news; soft flag for general relevance.

## Tools

### get_news(tickers, since)

Returns scored headlines for the given tickers since the specified time.

**Invocation:** `python scripts/get_news.py TICKER1 TICKER2 ... --since 24h`

**News source:** TBD. Options: NewsAPI, Benzinga, Finnhub, RSS. Set `NEWS_API_KEY` when configured.

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

News API not yet configured. This skill provides the interface. When `NEWS_API_KEY` (or equivalent) is set, the agent can invoke the script. Until then, the agent may use web search for manual checks.

## References

- [risk-os-v2-spec.md](/risk-os-v2-spec.md) — News: position-relevant only
