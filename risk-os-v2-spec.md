# Risk-OS v2 — Personal Trading Copilot
**Status:** Living document — iterate freely  
**Last updated:** Feb 2026

---

## What This Is

A personal AI agent that watches my portfolio while I'm busy with life. It doesn't trade for me or make decisions — it gathers information, surfaces what matters, explains its reasoning, and waits for me to act.

**Philosophy:** Show me what's happening and why it matters. Let me decide what to do.

---

## What It Is Not

- Not a SaaS product
- Not a black box decision-maker
- Not a replacement for my own judgment
- Not trying to impress anyone — optimized for my workflow only

---

## Core Behaviors

### 1. Proactive Monitoring (Scheduled)
The agent runs on a schedule and checks portfolio health without being asked. It only surfaces something when there's a reason to.

**Hard alerts (always notify):**
- Portfolio down >1% in a single day
- Any position approaching or hitting its stop loss
- Phase transition on any position (especially Phase 3→4 or 4→5)
- Adversarial research published on a holding (short reports, regulatory actions)
- Major news event directly affecting a holding

**Soft flags (include in briefing if relevant):**
- Consecutive down days on portfolio or individual position — flag for potential exit/rebalance consideration
- Strong performer — suggest whether to add or take profit, with reasoning and cited sources
- HMA dead cross or trend structure shift on a holding
- Macro sentiment shift relevant to sector exposure

### 2. Morning Briefing
A concise daily summary. If nothing is urgent, it can be very short. No noise about positions that are quietly healthy.

**Format principle:** If it's too long, it won't be read. Prioritize signal over completeness.

Structure:
- Portfolio health snapshot (1 line)
- Positions that need attention (only those with something to say)
- Any external events tied to holdings
- One actionable thought if warranted

### 3. On-Demand Q&A
When I ask a question ("what's going on with DG?", "should I add to ON?"), the agent reasons through it using available data and explains its thinking. It cites sources for any suggestions — no opinions without backing.

---

## Investment Framework (Agent Must Know This)

### Phase System (James Boyd)
Uses 10EMA, 30SMA, and 10-period Hull MA to classify each position:

| Phase | Conditions | Meaning | Action |
|-------|------------|---------|--------|
| 1 | Close < 10EMA **and** Close < 30SMA | Broken support, downtrend | Avoid |
| 2 | Close > 10EMA **and** Close < 30SMA | Breaking upward through resistance, early recovery | Watch |
| 3 | Close > 10EMA **and** Close > 30SMA | Strong trend — sweet spot for bull flags and breakouts | Long entry zone |
| 4 | Phase 3 conditions **+** 10EMA > 30SMA **+** Hull MA is falling | Still Phase 3 technically, but showing weakness — warning sign | Watch closely, possible add or prepare to exit |
| 5 | Close < 10EMA **and** Close > 30SMA | Pullback in strong trend — may bounce off 30SMA or break down | Caution, watch for breakdown |

**Indicators:**
- MA10 = 10-period Exponential Moving Average
- MA30 = 30-period Simple Moving Average
- Hull = 10-period Hull Moving Average (used only for Phase 4 detection — falling Hull = warning)

**Phase priority (from script):** Phase 4 is evaluated first, then 1, 2, 3, 5. This means a stock meeting Phase 4 conditions will show as Phase 4 even though it technically satisfies Phase 3.

*Note: Periods above are the originals. You mentioned adjusting them for longer-trend analysis — update here when decided.*

### Risk Rules
- Risk per trade default: **0.75% of account** (from old app calculator), user configurable
- Position sizing formula: `shares = (account × risk%) / |entry - stop|`
- Stop losses set per position and tracked via Schwab API
- Portfolio-level exposure monitored at all times
- Consecutive down days on portfolio or position → flag for exit/rebalance
- **Configured thresholds (from `config/risk-rules.yaml`):**
  - `hard_alerts.portfolio_daily_down_pct = 1.0`
  - `hard_alerts.stop_approaching_pct = 5.0`
  - `hard_alerts.phase_transition_pairs = [[3,4],[4,5]]`
  - `soft_flags.consecutive_down_days = 2`
  - `soft_flags.concentration_warn_pct = 20.0`
- **Schwab protective-order detection config (from `config/risk-rules.yaml`):**
  - `active_statuses = [WORKING, AWAITING_STOP_CONDITION, QUEUED, PENDING_ACTIVATION]`
  - `protective_order_types = [STOP, STOP_LIMIT, TRAILING_STOP]`
  - `short_limit_as_stop_fallback = true` (carry-over compatibility rule)
- **Options risk handling (from old app logic):**
  - Long single-leg: max loss = premium × 100 × contracts
  - Short single-leg: unbounded risk (N/A) — excluded from portfolio totals
  - Defined-risk spreads (verticals, iron condors): theoretical max loss formula
  - Unbalanced/complex multi-leg: conservative unknown-risk fallback

### Decision Style
- Technical indicators + macro context + investment bank research inform entries/exits
- Agent can suggest, but must show reasoning and cite credible sources
- Final decision is always mine

---

## Technical Architecture

### Platform
- **Runtime:** OpenClaw, self-hosted on NAS (Docker)
- **Trigger:** Cron jobs for scheduled checks + always-on for on-demand chat
- **Notification:** OpenClaw-native (channel TBD — Telegram, WhatsApp, etc.)

### Data Sources
- **Portfolio positions:** Schwab Trader API (already integrated — carry over `api/schwab/sync.ts` logic from old repo)
  - OAuth 2.0 three-legged flow, tokens stored securely, auto-refresh
  - Handles equities, options (single + multi-leg), unsupported instruments (futures)
  - Active protective order statuses include `WORKING`, `AWAITING_STOP_CONDITION`, `QUEUED`, `PENDING_ACTIVATION`
  - Protective order types include `STOP`, `STOP_LIMIT`, `TRAILING_STOP`; for short positions, use protective `LIMIT` buy orders above entry as stop fallback
  - OCO order normalization for stop/target detection already battle-tested
  - Schwab Streamer API available for real-time WebSocket data if needed later
- **Price & indicators:**
  - Current implementation (agent): yfinance in `phase-analyzer`
  - Target carry-over path: Schwab price history API as primary + Stooq fallback
- **News:** To be determined — needs to be position-relevant, not generic market noise
- **Research/reports:** TBD — investment bank reports, Citron-style short reports

### Skills (to be built)
| Skill | Purpose |
|-------|---------|
| `schwab-portfolio` | Pull current positions, prices, P&L, stops |
| `phase-analyzer` | Compute phase (1-5) per ticker using configured indicators |
| `market-news` | Fetch and score news relevance to current holdings |
| `risk-calculator` | Compute stop proximity, drawdown, portfolio-level exposure |

### Agent Soul (SOUL.md)
The agent will be configured with:
- This investment philosophy
- My risk tolerance and rules
- Preferred communication style (concise, no fluff)
- Instruction to always show reasoning and cite sources for suggestions
- Instruction to flag when something is outside its confidence

---

## Build Order

1. **Alerts + Schwab integration** — highest ROI, transforms app from passive to active
2. **Phase analyzer** — automates my existing framework, natural alert triggers
3. **Suggestions with reasoning** — surface risk flags with explanation
4. **News integration** — position-relevant only, last because hardest to do well

---

## Carry Over From Old Repo
These are already solved — extract from old codebase rather than rebuilding:
- Schwab OAuth flow + token refresh logic (`api/auth/schwab/`)
- Position + stop order sync and normalization (`api/schwab/sync.ts`)
- Options symbol parsing and strategy classification (`optionStrategy.ts`)
- Options risk calculation logic (`optionRisk.ts`)
- Mock Schwab data for local testing (`api/lib/mockSchwabData.ts`)

Carry-over behavior that should remain consistent:
- Flatten nested orders (including OCO trees) before evaluating stops/targets per symbol.
- Match close-side instructions by direction:
  - Long close: `SELL`, `SELL_TO_CLOSE`
  - Short close: `BUY`, `BUY_TO_COVER`, `BUY_TO_CLOSE`
- Normalize short-equity pricing to positive display/risk math (`entry` positive, `currentPrice` from absolute market value).
- Normalize option premiums to per-share premium (handle Schwab values where `averagePrice > 100` by dividing by 100).
- Use quantity-weighted target extraction for multiple valid target legs.

---

## Open Questions
- Exact indicator periods for phase system (send updated ThinkScript)
- News API source selection
- Whether to keep minimal web dashboard or retire it entirely
- How to ingest investment bank reports (PDF parsing?)

---

*This is a living document. Update as thinking evolves.*
