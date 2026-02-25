# Cron Setup for Morning Briefing

OpenClaw uses cron jobs for scheduled tasks. To add the morning briefing:

## Add Cron Job

```bash
openclaw cron add --cron '0 7 * * *' --message 'Run python3 scripts/run_morning_brief.py --since 24h and summarize workspace/briefings/<today>.md'
```

Use `sessionTarget: "isolated"` so it runs independently of active chat.

## Cron Expression

- `0 7 * * *` — 7:00 AM daily (adjust for your timezone)
- Jobs persist at `~/.openclaw/cron/jobs.json`

## Morning Brief Format

Per [risk-os-v2-spec.md](risk-os-v2-spec.md):

1. Portfolio health snapshot (1 line)
2. Positions that need attention (only those with something to say)
3. Any external events tied to holdings
4. One actionable thought if warranted

**Principle:** If it's too long, it won't be read. Prioritize signal over completeness.

## Local Dry Run

```bash
python3 scripts/run_morning_brief.py --date 2026-02-25 --since 24h
```

Outputs:
- `workspace/briefings/2026-02-25.md`
- `workspace/briefings/2026-02-25.json`

## Heartbeat

For proactive monitoring (every 30–60 min), ensure heartbeat is enabled in `~/.openclaw/openclaw.json`:

```json5
{
  heartbeat: { every: '30m' }
}
```

The agent reads [HEARTBEAT.md](HEARTBEAT.md) and runs the checklist. `HEARTBEAT_OK` suppresses output when nothing actionable.
