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

### Phase System (James Boyd / adapted)
Uses 10EMA, 30SMA, and HMA to classify each position:

| Phase | Condition | Meaning |
|-------|-----------|---------|
| 1 | Below both 10EMA and 30SMA | Avoid / very bearish |
| 2 | Above 10EMA, below 30SMA | Gaining momentum, watch |
| 3 | Above both 10EMA and 30SMA | Long entry zone |
| 4 | Below HMA but above 10/30 | Watch for trend break |
| 5 | Price breaking down hard | Exit or already exited |

*Note: Periods are adjusted for longer-trend analysis. Specifics TBD during build.*

Also uses: 10/20 day HMA for fast momentum detection.

### Risk Rules (High Level)
- Risk per trade is managed as a % of account — specifics TBD
- Stop losses are set per position and tracked
- Portfolio-level risk exposure is monitored
- Consecutive losses or drawdown triggers a re-evaluation signal

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
- **Portfolio positions:** Schwab Trader API via schwab-py (integrated in risk-os-agent)
- **Price & indicators:** To be determined during build
- **News:** To be determined — needs to be position-relevant, not generic market noise
- **Research/reports:** TBD — investment bank reports, Citron-style research

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

## Open Questions
- Exact indicator periods for phase system
- Specific risk % thresholds for alerts
- News API source selection
- Whether to keep minimal web dashboard or retire it entirely
- How to ingest investment bank reports (PDF parsing?)

---

*This is a living document. Update as thinking evolves.*
