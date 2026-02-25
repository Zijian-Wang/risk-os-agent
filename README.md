# RiskOS Agent

Personal AI trading copilot for OpenClaw. Watches your portfolio, surfaces alerts, and answers questions — without making trades. Your second brain for investment decisions.

**Philosophy:** Show me what's happening and why it matters. Let me decide what to do.

---

## Quick Start

### Option A: Tell OpenClaw to Integrate (Recommended)

Paste the prompt from [OPENCLAW_INTEGRATION_PROMPT.md](OPENCLAW_INTEGRATION_PROMPT.md) into OpenClaw chat, or use:

```
Read this repository (risk-os-agent) and integrate it as your agent workspace.

1. Read README.md, risk-os-v2-spec.md, and the plan in .cursor/plans/ if present.
2. Set your workspace to this repo's root (or add .agents/skills to skills.load.extraDirs in ~/.openclaw/openclaw.json).
3. Use SOUL.md and HEARTBEAT.md from this repo as your agent identity and heartbeat checklist.
4. Run the structure check: ./scripts/check-structure.sh
5. Run the security check: ./scripts/check-security.sh
6. Report what's configured and what still needs setup (e.g., Schwab from risk-os, price API, notification channel).
```

OpenClaw will read the repo, understand the structure, and configure itself. You may need to approve config changes or run commands it suggests.

### Option B: Manual Setup

1. **Clone and enter the repo:**
   ```bash
   cd /path/to/risk-os-agent
   ```

2. **Add skills to OpenClaw** — edit `~/.openclaw/openclaw.json`:
   ```json5
   {
     skills: {
       load: {
         extraDirs: ["/path/to/risk-os-agent/.agents/skills"],
         watch: true
       }
     },
     agents: {
       defaults: {
         workspace: "/path/to/risk-os-agent"
       }
     }
   }
   ```

3. **Run checks** (requires Bash: Git Bash, WSL, or Linux/macOS):
   ```bash
   ./scripts/check-structure.sh
   ./scripts/check-security.sh
   ```

4. **Restart OpenClaw Gateway** so it picks up the new workspace and skills.

---

## Project Structure

```
risk-os-agent/
├── .agents/skills/           # OpenClaw skills (auto-discovered when workspace is this repo)
│   ├── schwab-portfolio/     # Positions, P&L, stops (Schwab API)
│   ├── phase-analyzer/       # Phase 1-5, HMA (uses yfinance)
│   ├── risk-calculator/     # Stop proximity, drawdown, exposure
│   └── market-news/         # Position-relevant news (API TBD)
├── config/
│   ├── phase-config.yaml    # Phase system periods (TBD)
│   ├── ta-config.yaml       # RSI, MACD, etc. (extensible)
│   └── risk-rules.yaml      # Alert thresholds (TBD)
├── workspace/               # Agent workspace data
│   ├── portfolio/          # Cached positions
│   ├── alerts/             # Alert history (dedup)
│   └── briefings/           # Morning brief outputs
├── scaffolds/              # Templates and scripts for creating skills
│   ├── templates/          # SKILL.md and skill structure templates
│   └── scripts/            # create-skill, check-structure, check-security
├── AGENTS.md               # Instructions for AI agents (security, scaffolds, math, docs)
├── SOUL.md                 # Agent identity, values, constraints
├── HEARTBEAT.md            # Proactive monitoring checklist
├── .env.example            # Env vars template (copy to .env)
├── CRON_SETUP.md           # Cron + heartbeat setup
├── risk-os-v2-spec.md      # Full spec
└── README.md
```

---

## Creating Skills and Agents

### Scaffolds

Use the scaffolds to create new skills and validate the project:

| Script | Purpose |
|-------|---------|
| `./scripts/create-skill.sh <name>` | Create a new skill from template in `.agents/skills/<name>/` |
| `./scripts/check-structure.sh` | Validate project structure, required files, skill layout |
| `./scripts/check-security.sh` | Check for secrets, env exposure, unsafe patterns |

### Creating a New Skill

```bash
./scripts/create-skill.sh my-new-skill
```

Then edit `.agents/skills/my-new-skill/SKILL.md` with:
- YAML frontmatter: `name`, `description`
- Optional: `metadata.openclaw.requires` (bins, env, config)
- Markdown body: instructions, tools, examples

### Skill Structure (OpenClaw)

Each skill needs:

```
skill-name/
├── SKILL.md              # Required: YAML frontmatter + instructions
├── scripts/              # Optional: executable helpers
├── references/           # Optional: docs loaded on demand
└── assets/               # Optional: templates, icons
```

**SKILL.md minimal format:**
```yaml
---
name: skill-name
description: Brief description of what the skill does and when to use it
---
# Skill Name
Instructions for the agent...
```

---

## Checks

### Structure Check (`check-structure.sh`)

Verifies:
- `.agents/skills/` exists
- Each skill has `SKILL.md` with valid YAML frontmatter (`name`, `description`)
- `config/`, `workspace/` directories exist
- `SOUL.md`, `HEARTBEAT.md` present
- No stray binaries or obviously wrong paths

### Security Check (`check-security.sh`)

Verifies:
- No hardcoded API keys, tokens, or secrets in tracked files
- `.env` and secrets in `.gitignore`
- No `eval`, `exec` of user input without sanitization in scripts
- Skills don't expose sensitive paths or credentials in SKILL.md

---

## Dependencies

- **OpenClaw** — Runtime (self-hosted, Docker on NAS)
- **Python 3** — For all skill scripts
- **schwab-portfolio** — `pip install schwab-py`; set `SCHWAB_API_KEY`, `SCHWAB_APP_SECRET`; run `auth_schwab.py` once
- **phase-analyzer** — `pip install yfinance pyyaml`
- **Price API** — yfinance used by default
- **market-news** — Supports NewsAPI.org and Finnhub; set `NEWS_API_KEY`, choose `NEWS_API_SOURCE` (`newsapi` or `finnhub`), optional `NEWS_CACHE_TTL_MIN`

See [.env.example](.env.example) for required env vars.

---

## Agent Instructions

- [AGENTS.md](AGENTS.md) — Instructions for AI agents: security, scaffolds workflow, deterministic math, token optimization, docs updates

## Spec and Plan

- [risk-os-v2-spec.md](risk-os-v2-spec.md) — Full product spec
- [CRON_SETUP.md](CRON_SETUP.md) — Cron + heartbeat for morning brief
- Plan: `.cursor/plans/` or Cursor's plan view

---

## License

Private / personal use.
