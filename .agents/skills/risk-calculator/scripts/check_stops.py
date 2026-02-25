#!/usr/bin/env python3
"""
Check positions for stop proximity. Uses decimal for deterministic money math.
Reads positions from workspace/portfolio/positions.json or stdin.
"""

import json
import sys
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = REPO_ROOT / "config" / "risk-rules.yaml"
POSITIONS_PATH = REPO_ROOT / "workspace" / "portfolio" / "positions.json"


def load_config():
    try:
        import yaml
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                cfg = yaml.safe_load(f) or {}
                return cfg.get("hard_alerts", {}).get("stop_approaching_pct", 5.0)
    except Exception:
        pass
    return 5.0


def load_positions():
    if not sys.stdin.isatty():
        data = json.load(sys.stdin)
        return data.get("positions", data) if isinstance(data, dict) else data
    if POSITIONS_PATH.exists():
        with open(POSITIONS_PATH) as f:
            data = json.load(f)
            return data.get("positions", [])
    return []


def main():
    threshold_pct = Decimal(str(load_config()))
    positions = load_positions()

    if not positions:
        print(json.dumps({"alerts": [], "error": "No positions"}))
        return

    alerts = []
    for p in positions:
        ticker = p.get("ticker", "?")
        stop = p.get("stop")
        if stop is None:
            continue
        try:
            current = Decimal(str(p.get("currentPrice", 0)))
            stop_dec = Decimal(str(stop))
        except Exception:
            continue
        if current <= 0 or stop_dec <= 0:
            continue

        pct_to_stop = ((current - stop_dec) / current * 100).quantize(Decimal("0.01"))
        status = "hit" if current <= stop_dec else ("approaching" if float(pct_to_stop) <= threshold_pct else "ok")

        if status != "ok":
            alerts.append({
                "ticker": ticker,
                "currentPrice": float(current),
                "stop": float(stop_dec),
                "pctToStop": float(pct_to_stop),
                "status": status,
            })

    print(json.dumps({"alerts": alerts}))


if __name__ == "__main__":
    main()
