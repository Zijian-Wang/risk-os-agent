# OpenClaw Integration Prompt

Copy and paste this into OpenClaw chat to have it read this repo and integrate the agent:

---

Read this repository (risk-os-agent) and integrate it as your agent workspace.

1. Read AGENTS.md, README.md, risk-os-v2-spec.md, and the plan in .cursor/plans/ if present.
2. Set your workspace to this repo's root (or add .agents/skills to skills.load.extraDirs in ~/.openclaw/openclaw.json).
3. Use SOUL.md and HEARTBEAT.md from this repo as your agent identity and heartbeat checklist.
4. Install Python deps: pip install -r requirements.txt
5. Run the structure check: ./scripts/check-structure.sh
6. Run the security check: ./scripts/check-security.sh
7. Report what's configured and what still needs setup (e.g., SCHWAB_* for portfolio, NEWS_API_KEY, notification channel).

---

Note: On Windows, the check scripts require Bash (Git Bash or WSL). OpenClaw may run on Linux/Docker, where bash is available.
