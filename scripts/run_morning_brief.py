#!/usr/bin/env python3
"""
Run the morning briefing pipeline and write markdown/json artifacts.

P0 scope:
1) Pull positions
2) Run risk checks
3) Run phase checks
4) Run news checks
5) Emit one concise briefing
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BRIEFINGS_DIR = REPO_ROOT / "workspace" / "briefings"

GET_POSITIONS = REPO_ROOT / ".agents" / "skills" / "schwab-portfolio" / "scripts" / "get_positions.py"
CHECK_STOPS = REPO_ROOT / ".agents" / "skills" / "risk-calculator" / "scripts" / "check_stops.py"
PORTFOLIO_DRAWDOWN = REPO_ROOT / ".agents" / "skills" / "risk-calculator" / "scripts" / "portfolio_drawdown.py"
EXPOSURE_SUMMARY = REPO_ROOT / ".agents" / "skills" / "risk-calculator" / "scripts" / "exposure_summary.py"
GET_PHASES = REPO_ROOT / ".agents" / "skills" / "phase-analyzer" / "scripts" / "get_phases.py"
GET_NEWS = REPO_ROOT / ".agents" / "skills" / "market-news" / "scripts" / "get_news.py"


def as_decimal(value: Any, default: str = "0") -> Decimal:
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def q2(value: Any) -> Decimal:
    return as_decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def fmt_currency(value: Any) -> str:
    quantized = q2(value)
    sign = "-" if quantized < 0 else ""
    abs_value = abs(quantized)
    return f"{sign}${abs_value:,.2f}"


def fmt_pct(value: Any) -> str:
    quantized = q2(value)
    sign = "+" if quantized > 0 else ""
    return f"{sign}{quantized:.2f}%"


def run_json(cmd: list[str], timeout_s: int = 180) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=REPO_ROOT,
        )
    except Exception as exc:
        return {"error": str(exc), "_command": cmd}

    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()

    parsed: dict[str, Any]
    if stdout:
        try:
            payload = json.loads(stdout)
            parsed = payload if isinstance(payload, dict) else {"result": payload}
        except json.JSONDecodeError:
            parsed = {"error": "Invalid JSON output", "rawStdout": stdout}
    else:
        parsed = {}

    if proc.returncode != 0:
        parsed.setdefault("error", stderr or f"Command failed with exit code {proc.returncode}")
    if stderr:
        parsed.setdefault("_stderr", stderr)

    return parsed


def unique_lines(lines: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        out.append(line)
    return out


def choose_actionable_thought(hard_alerts: list[str], phases: list[dict[str, Any]]) -> str | None:
    if hard_alerts:
        return "Address hard alerts first before considering new entries."

    phase3 = [p.get("ticker") for p in phases if p.get("phase") == 3]
    weakening = [p.get("ticker") for p in phases if p.get("phase") in (4, 5)]

    if weakening:
        tickers = ", ".join(sorted(str(t) for t in weakening if t))
        return f"Trend is weakening on {tickers}; review stop placement and position size."
    if phase3:
        tickers = ", ".join(sorted(str(t) for t in phase3 if t))
        return f"Phase 3 names ({tickers}) remain in the long-entry zone; wait for high-quality setups."
    return None


def build_external_events(headlines: list[dict[str, Any]], limit: int = 8) -> list[str]:
    filtered = [h for h in headlines if h.get("score") in ("adversarial", "major", "macro")]
    filtered.sort(key=lambda h: str(h.get("publishedAt") or ""), reverse=True)

    lines: list[str] = []
    for item in filtered[:limit]:
        ticker = item.get("ticker", "?")
        score = item.get("score", "relevant")
        title = item.get("title", "")
        source = item.get("source", "unknown")
        lines.append(f"{ticker}: [{score}] {title} ({source})")
    return unique_lines(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run RiskOS morning briefing pipeline.")
    parser.add_argument("--date", default=date.today().isoformat(), help="As-of date (YYYY-MM-DD).")
    parser.add_argument("--since", default="24h", help="News lookback window, e.g. 24h, 2d.")
    parser.add_argument(
        "--output-dir",
        default=str(BRIEFINGS_DIR),
        help="Directory for briefing outputs.",
    )
    parser.add_argument("--no-news-cache", action="store_true", help="Disable news cache for this run.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    py = sys.executable

    positions_data = run_json([py, str(GET_POSITIONS)], timeout_s=120)
    positions = positions_data.get("positions", []) if isinstance(positions_data.get("positions"), list) else []
    summary = positions_data.get("summary", {}) if isinstance(positions_data.get("summary"), dict) else {}
    tickers = sorted({str(p.get("ticker", "")).upper() for p in positions if p.get("ticker")})

    stops_data = run_json([py, str(CHECK_STOPS)], timeout_s=90)
    drawdown_data = run_json([py, str(PORTFOLIO_DRAWDOWN)], timeout_s=90)
    exposure_data = run_json([py, str(EXPOSURE_SUMMARY)], timeout_s=90)

    phases_data: dict[str, Any]
    if tickers:
        phases_data = run_json([py, str(GET_PHASES), *tickers], timeout_s=240)
    else:
        phases_data = {"phases": [], "status": "No tickers"}
    phases = phases_data.get("phases", []) if isinstance(phases_data.get("phases"), list) else []

    news_data: dict[str, Any]
    if tickers:
        news_cmd = [py, str(GET_NEWS), *tickers, "--since", args.since]
        if args.no_news_cache:
            news_cmd.append("--no-cache")
        news_data = run_json(news_cmd, timeout_s=180)
    else:
        news_data = {"headlines": [], "alerts": [], "status": "No tickers"}

    hard_alerts: list[str] = []
    daily_pnl_pct = drawdown_data.get("dailyPnlPct", summary.get("dailyPnlPct", 0))
    if drawdown_data.get("alert"):
        hard_alerts.append(f"Portfolio daily move is {fmt_pct(daily_pnl_pct)} (hard-alert threshold breached).")

    stop_alerts = stops_data.get("alerts", []) if isinstance(stops_data.get("alerts"), list) else []
    for alert in sorted(stop_alerts, key=lambda a: str(a.get("ticker", ""))):
        hard_alerts.append(
            f"{alert.get('ticker', '?')} stop {alert.get('status', 'alert')}: "
            f"price {fmt_currency(alert.get('currentPrice', 0))}, "
            f"stop {fmt_currency(alert.get('stop', 0))}, "
            f"distance {fmt_pct(alert.get('pctToStop', 0))}."
        )

    news_alerts = news_data.get("alerts", []) if isinstance(news_data.get("alerts"), list) else []
    for alert in sorted(str(x) for x in news_alerts):
        hard_alerts.append(f"News alert: {alert}")
    hard_alerts = unique_lines(hard_alerts)

    watch_flags: list[str] = []
    phase_rows = [p for p in phases if isinstance(p, dict) and not p.get("error")]
    for row in sorted(phase_rows, key=lambda p: str(p.get("ticker", ""))):
        ticker = row.get("ticker", "?")
        phase = row.get("phase")
        hma_trend = row.get("hmaTrend")
        if phase == 4:
            watch_flags.append(f"{ticker} is in Phase 4 (weakening trend; Hull is falling).")
        elif phase == 5:
            watch_flags.append(f"{ticker} is in Phase 5 (pullback below 10EMA while above 30SMA).")
        elif phase == 3 and hma_trend == "falling":
            watch_flags.append(f"{ticker} remains Phase 3, but Hull slope is falling.")
        if row.get("hmaCross") == "bearish":
            watch_flags.append(f"{ticker} shows bearish HMA cross behavior.")

    exposure_flags = exposure_data.get("reEvalFlags", []) if isinstance(exposure_data.get("reEvalFlags"), list) else []
    for flag in sorted(exposure_flags, key=lambda f: str(f.get("ticker", ""))):
        watch_flags.append(
            f"{flag.get('ticker', '?')} concentration at {fmt_pct(flag.get('weightPct', 0))} "
            f"({flag.get('reason', 'review')})."
        )
    watch_flags = unique_lines(watch_flags)

    headlines = news_data.get("headlines", []) if isinstance(news_data.get("headlines"), list) else []
    external_events = build_external_events([h for h in headlines if isinstance(h, dict)])

    actionable_thought = choose_actionable_thought(hard_alerts, phase_rows)

    total_value = summary.get("totalValue", exposure_data.get("totalValue", 0))
    snapshot_line = (
        f"{fmt_currency(total_value)} total | daily move {fmt_pct(daily_pnl_pct)} | "
        f"{len(positions)} positions | {len(hard_alerts)} hard alerts"
    )

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    briefing_json = {
        "asOfDate": args.date,
        "generatedAt": generated_at,
        "portfolio": {
            "totalValue": float(q2(total_value)),
            "dailyPnlPct": float(q2(daily_pnl_pct)),
            "positions": len(positions),
            "hardAlertCount": len(hard_alerts),
        },
        "summaryLine": snapshot_line,
        "sections": {
            "immediateActions": hard_alerts,
            "watchlistFlags": watch_flags,
            "externalEvents": external_events,
            "actionableThought": actionable_thought,
        },
        "inputs": {
            "positions": positions_data,
            "stops": stops_data,
            "drawdown": drawdown_data,
            "exposure": exposure_data,
            "phases": phases_data,
            "news": news_data,
        },
    }

    md_lines = [
        f"# Morning Briefing - {args.date}",
        "",
        f"Generated: {generated_at}",
        "",
        f"Portfolio health snapshot: {snapshot_line}",
        "",
        "## Immediate actions",
    ]
    if hard_alerts:
        md_lines.extend(f"- {line}" for line in hard_alerts)
    else:
        md_lines.append("- None.")

    md_lines.extend(["", "## Watchlist flags"])
    if watch_flags:
        md_lines.extend(f"- {line}" for line in watch_flags)
    else:
        md_lines.append("- None.")

    md_lines.extend(["", "## External events tied to holdings"])
    if external_events:
        md_lines.extend(f"- {line}" for line in external_events)
    else:
        md_lines.append("- None.")

    md_lines.extend(["", "## One actionable thought"])
    md_lines.append(actionable_thought or "No high-confidence action today.")
    md_lines.append("")

    json_path = output_dir / f"{args.date}.json"
    md_path = output_dir / f"{args.date}.md"
    json_path.write_text(json.dumps(briefing_json, indent=2))
    md_path.write_text("\n".join(md_lines))

    print(
        json.dumps(
            {
                "status": "ok",
                "asOfDate": args.date,
                "json": str(json_path),
                "markdown": str(md_path),
                "hardAlerts": len(hard_alerts),
                "watchFlags": len(watch_flags),
                "externalEvents": len(external_events),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
