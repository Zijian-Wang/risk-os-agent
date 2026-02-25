# RiskOS Agent

Personal AI trading copilot for OpenClaw. Watches your portfolio, surfaces alerts, and explains its reasoning — without making trades.

**Philosophy:** Show me what's happening and why it matters. Let me decide what to do.

---

## Setup

### 1. Configure OpenClaw

Edit `~/.openclaw/openclaw.json`:

```json
{
  "skills": {
    "load": {
      "extraDirs": ["/path/to/risk-os-agent/skills"],
      "watch": true
    }
  },
  "agents": {
    "defaults": {
      "workspace": "/path/to/risk-os-agent"
    }
  }
}
```

Paste the contents of `agent/AGENT.md` as your OpenClaw system prompt.

Restart OpenClaw Gateway.

### 2. Install dependencies

```bash
pip install schwab-py yfinance pyyaml
```

### 3. Load your positions

**Option A — Schwab CSV (no auth required):**

Export from Schwab web UI: Accounts → Positions → Export (CSV icon). Then:

```bash
python3 skills/portfolio/scripts/load_csv.py ~/Downloads/positions.csv
```

**Option B — Live Schwab API:**

```bash
cp .env.example .env
# Edit .env: set SCHWAB_API_KEY, SCHWAB_APP_SECRET, SCHWAB_CALLBACK_URL
python3 skills/portfolio/scripts/auth_schwab.py   # run once on Mac with browser
```

### 4. Set manual stops (optional)

Create `workspace/portfolio/stops.json`:

```json
{ "NVDA": 110.00, "AAPL": 185.00 }
```

The CSV loader merges these automatically.

### 5. Set up news (optional)

Add to `.env`:

```
NEWS_API_KEY=your_key
NEWS_API_SOURCE=newsapi   # or finnhub
```

### 6. Schedule morning brief (NAS / cron)

```bash
# OpenClaw cron:
openclaw cron add --cron '0 7 * * *' --message 'Run python3 scripts/run_morning_brief.py --since 24h'

# Or system cron (replace path):
0 7 * * * cd /path/to/risk-os-agent && python3 scripts/run_morning_brief.py --since 24h
```

---

## Structure

```
risk-os-agent/
├── agent/
│   ├── AGENT.md              # OpenClaw system prompt (paste into OpenClaw)
│   └── config/
│       ├── risk-rules.yaml   # Alert thresholds + concentration limits
│       └── phase-config.yaml # MA periods (10EMA, 30SMA, 10HMA)
│
├── skills/
│   ├── portfolio/            # Schwab positions + CSV loader
│   ├── phase-analyzer/       # James Boyd phase system (1-5)
│   ├── risk-calculator/      # Stop proximity, drawdown, exposure
│   └── market-news/          # Position-relevant news scoring
│
├── scripts/
│   └── run_morning_brief.py  # Morning briefing pipeline
│
└── workspace/
    ├── portfolio/
    │   ├── positions.json    # Written by load_csv.py or get_positions.py
    │   └── stops.json        # Manual stop overrides
    ├── briefings/            # Daily brief outputs (<date>.md + .json)
    └── alerts/               # briefing_state.json (phase/news dedup)
```

---

## Running manually

```bash
# Load positions from CSV
python3 skills/portfolio/scripts/load_csv.py export.csv

# Check phases
python3 skills/phase-analyzer/scripts/get_phases.py NVDA AAPL MSFT

# Check stop proximity
python3 skills/risk-calculator/scripts/check_stops.py

# Run full morning brief
python3 scripts/run_morning_brief.py --since 24h
```

---

## Environment variables

See `.env.example`. Required for live Schwab API and news:

| Variable | Required for |
|----------|-------------|
| `SCHWAB_API_KEY` | Live positions via Schwab API |
| `SCHWAB_APP_SECRET` | Live positions via Schwab API |
| `SCHWAB_CALLBACK_URL` | OAuth flow (default: `https://127.0.0.1/auth/schwab/callback`) |
| `NEWS_API_KEY` | Market news skill |
| `NEWS_API_SOURCE` | `newsapi` or `finnhub` |

---

## License

Private / personal use.
