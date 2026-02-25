#!/usr/bin/env python3
"""
Compute portfolio daily P&L and drawdown. Uses decimal for deterministic math.
Reads from workspace/portfolio/positions.json.
"""

import json
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
                return cfg.get("hard_alerts", {}).get("portfolio_daily_down_pct", 1.0)
    except Exception:
        pass
    return 1.0


def main():
    threshold = Decimal(str(load_config()))
    if not POSITIONS_PATH.exists():
        print(json.dumps({"dailyPnlPct": 0, "alert": False, "error": "No positions file"}))
        return

    with open(POSITIONS_PATH) as f:
        data = json.load(f)

    summary = data.get("summary", {})
    daily_pnl_pct = Decimal(str(summary.get("dailyPnlPct", 0)))
    total_value = summary.get("totalValue")
    alert = daily_pnl_pct < -threshold

    # Drawdown: would need historical data; placeholder
    drawdown_pct = summary.get("drawdownPct")

    out = {
        "dailyPnlPct": float(daily_pnl_pct.quantize(Decimal("0.01"))),
        "alert": bool(alert),
        "drawdownPct": float(drawdown_pct) if drawdown_pct is not None else None,
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
