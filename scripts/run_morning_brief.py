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
import hashlib
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
BRIEFINGS_DIR = REPO_ROOT / "workspace" / "briefings"
ALERTS_DIR = REPO_ROOT / "workspace" / "alerts"
STATE_PATH = ALERTS_DIR / "briefing_state.json"
RISK_RULES_PATH = REPO_ROOT / "agent" / "config" / "risk-rules.yaml"

GET_POSITIONS = REPO_ROOT / "skills" / "portfolio" / "scripts" / "get_positions.py"
CHECK_STOPS = REPO_ROOT / "skills" / "risk-calculator" / "scripts" / "check_stops.py"
PORTFOLIO_DRAWDOWN = REPO_ROOT / "skills" / "risk-calculator" / "scripts" / "portfolio_drawdown.py"
EXPOSURE_SUMMARY = REPO_ROOT / "skills" / "risk-calculator" / "scripts" / "exposure_summary.py"
GET_PHASES = REPO_ROOT / "skills" / "phase-analyzer" / "scripts" / "get_phases.py"
GET_NEWS = REPO_ROOT / "skills" / "market-news" / "scripts" / "get_news.py"


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


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text())
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))


def phase_as_int(value: Any) -> int | None:
    try:
        return int(value)
    except Exception:
        return None


def headline_hash(item: dict[str, Any]) -> str:
    key = "|".join(
        [
            str(item.get("ticker", "")).upper(),
            str(item.get("title", "")).strip(),
            str(item.get("source", "")).strip(),
            str(item.get("publishedAt", "")).strip(),
        ]
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


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


def load_phase_transition_pairs() -> set[tuple[int, int]]:
    default_pairs = {(3, 4), (4, 5)}
    try:
        import yaml

        if not RISK_RULES_PATH.exists():
            return default_pairs
        with open(RISK_RULES_PATH) as f:
            cfg = yaml.safe_load(f) or {}
        hard_alerts = cfg.get("hard_alerts", {}) if isinstance(cfg, dict) else {}
        raw_pairs = hard_alerts.get("phase_transition_pairs", [])
        if not isinstance(raw_pairs, list):
            return default_pairs
        out: set[tuple[int, int]] = set()
        for item in raw_pairs:
            if not isinstance(item, list) or len(item) != 2:
                continue
            try:
                out.add((int(item[0]), int(item[1])))
            except Exception:
                continue
        return out or default_pairs
    except Exception:
        return default_pairs


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
    previous_state = load_state(STATE_PATH)
    state_loaded = bool(previous_state)
    hard_phase_transition_pairs = load_phase_transition_pairs()

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
    phase_transitions: list[str] = []
    previous_phase_map = previous_state.get("phaseByTicker", {})
    if not isinstance(previous_phase_map, dict):
        previous_phase_map = {}
    phase_rows = [p for p in phases if isinstance(p, dict) and not p.get("error")]
    for row in sorted(phase_rows, key=lambda p: str(p.get("ticker", ""))):
        ticker = row.get("ticker", "?")
        phase = phase_as_int(row.get("phase"))
        previous_phase = phase_as_int(previous_phase_map.get(str(ticker)))
        if previous_phase is not None and phase is not None:
            row["previousPhase"] = previous_phase
            if phase != previous_phase:
                transition = f"{ticker} phase transition {previous_phase} -> {phase}"
                phase_transitions.append(transition)
                if (previous_phase, phase) in hard_phase_transition_pairs:
                    hard_alerts.append(f"Phase alert: {transition} (hard-alert transition).")
                else:
                    watch_flags.append(f"{transition}.")

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
    hard_alerts = unique_lines(hard_alerts)
    watch_flags = unique_lines(watch_flags)

    headlines = [h for h in news_data.get("headlines", []) if isinstance(h, dict)] if isinstance(news_data.get("headlines"), list) else []
    previous_news_hashes = previous_state.get("newsHashes", [])
    if not isinstance(previous_news_hashes, list):
        previous_news_hashes = []
    previous_news_hash_set = {str(h) for h in previous_news_hashes}

    new_headlines: list[dict[str, Any]] = []
    all_headline_hashes: list[str] = []
    for item in headlines:
        digest = headline_hash(item)
        all_headline_hashes.append(digest)
        if digest not in previous_news_hash_set:
            new_headlines.append(item)

    # Show only newly seen items after first run; first run includes all available.
    external_events = build_external_events(new_headlines if state_loaded else headlines)
    delta_lines: list[str] = []
    if phase_transitions:
        delta_lines.extend(phase_transitions)
    if state_loaded:
        delta_lines.append(f"New scored headlines since last run: {len(new_headlines)}")
    else:
        delta_lines.append("Baseline run: no previous state found.")
    delta_lines = unique_lines(delta_lines)

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
            "changesSinceLastRun": delta_lines,
            "immediateActions": hard_alerts,
            "watchlistFlags": watch_flags,
            "externalEvents": external_events,
            "actionableThought": actionable_thought,
        },
        "deltas": {
            "phaseTransitions": phase_transitions,
            "newHeadlinesCount": len(new_headlines),
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
        "## Changes since previous run",
    ]
    if delta_lines:
        md_lines.extend(f"- {line}" for line in delta_lines)
    else:
        md_lines.append("- None.")

    md_lines.extend([
        "",
        "## Immediate actions",
    ])
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

    latest_phase_map: dict[str, int] = {}
    for row in phase_rows:
        ticker = str(row.get("ticker", "")).upper()
        phase_value = phase_as_int(row.get("phase"))
        if ticker and phase_value is not None:
            latest_phase_map[ticker] = phase_value
    latest_news_hashes = sorted(set(all_headline_hashes))[-500:]
    next_state = {
        "updatedAt": generated_at,
        "phaseByTicker": latest_phase_map,
        "newsHashes": latest_news_hashes,
    }
    save_state(STATE_PATH, next_state)

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
                "phaseTransitions": len(phase_transitions),
                "newHeadlines": len(new_headlines),
                "stateFile": str(STATE_PATH),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
