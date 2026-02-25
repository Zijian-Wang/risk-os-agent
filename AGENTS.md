# RiskOS Agent — Instructions for AI Agents

This file guides AI agents (Cursor, OpenClaw, Copilot, etc.) working in this codebase. Read it before making changes.

---

## Documentation

**Always update docs when you change the project.**

- Add or modify features → update [README.md](README.md)
- New skills, config, or structure → update README project structure and relevant sections
- New scripts or checks → update scaffolds/README.md and README Checks section
- Security or workflow changes → update this file (AGENTS.md)

Keep README and docs in sync with code. Out-of-date docs cause confusion and errors.

---

## Security

- **No secrets in code** — Use env vars (`.env`, `process.env`, `os.environ`). Never commit API keys, tokens, or passwords.
- **Sensitive data** — Portfolio, positions, P&L stay in workspace/ or external APIs. Don't log or expose in chat.
- **Input validation** — Sanitize user input before `eval`, `exec`, or shell commands. Avoid arbitrary code execution.
- **.gitignore** — Ensure `.env`, `token.json`, `credentials*.json` are ignored. Run `check-security.sh` after changes.
- **Skills** — Document required env vars in SKILL.md `metadata.openclaw.requires`; never hardcode credentials.

---

## Scaffolds Workflow

When creating or modifying skills:

1. **New skill** → Run `./scripts/create-skill.sh <name>` (lowercase, hyphens)
2. **Edit SKILL.md** → Set `name`, `description`, add instructions
3. **Validate** → Run `./scripts/check-structure.sh`
4. **Security** → Run `./scripts/check-security.sh`
5. **Docs** → Update README if the skill is part of the core set

Skill layout: `skill-name/SKILL.md` (required), optional `scripts/`, `references/`, `assets/`.

---

## Math and Calculations

**Use deterministic, reproducible math.**

- **Financial calculations** — Use decimal libraries (e.g. `decimal.Decimal` in Python, `decimal.js` in JS) for money, percentages, P&L. Avoid raw `float` for currency.
- **Rounding** — Define explicit rounding rules (e.g. 2 decimals for currency, 4 for percentages). Document in config.
- **Order of operations** — Prefer explicit parentheses and clear formulas. Avoid relying on language-specific operator precedence for financial logic.
- **Reproducibility** — Same inputs must yield same outputs. No randomness in core calculations unless explicitly required and documented.

---

## Token Usage and Quality

- **Minimize tokens** — Keep SKILL.md concise. Use progressive disclosure: essentials in SKILL.md, details in `references/`. Target SKILL.md under ~500 lines.
- **Avoid redundancy** — Don't repeat what the agent already knows. Only add project-specific context.
- **Optimize for quality** — Prefer clear, correct logic over clever shortcuts. Financial code must be auditable.
- **Caching** — Cache API responses where appropriate (portfolio, prices) to reduce calls and tokens. Document TTL and invalidation.

---

## Project Context

- **schwab-portfolio** — Uses schwab-py directly. Set `SCHWAB_API_KEY`, `SCHWAB_APP_SECRET`; run `auth_schwab.py` once.
- **OpenClaw** — Runtime. Skills go in `.agents/skills/`. SOUL.md and HEARTBEAT.md define agent identity and proactive checks.
- **Config** — `config/*.yaml` holds tunable parameters. Keep logic in code, values in config.
- **Skills** — schwab-portfolio, phase-analyzer, risk-calculator, market-news. Each has SKILL.md + scripts/.
