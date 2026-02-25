#!/usr/bin/env python3
"""
Portfolio exposure summary. Uses decimal for deterministic math.
Reads from workspace/portfolio/positions.json.
"""

import json
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
POSITIONS_PATH = REPO_ROOT / "workspace" / "portfolio" / "positions.json"
CONFIG_PATH = REPO_ROOT / "config" / "risk-rules.yaml"


def load_concentration_threshold() -> Decimal:
    try:
        import yaml

        if CONFIG_PATH.exists():
            with open(CONFIG_PATH) as f:
                cfg = yaml.safe_load(f) or {}
                soft_flags = cfg.get("soft_flags", {}) if isinstance(cfg, dict) else {}
                value = soft_flags.get("concentration_warn_pct", 20.0)
                return Decimal(str(value))
    except Exception:
        pass
    return Decimal("20.0")


def main():
    if not POSITIONS_PATH.exists():
        print(json.dumps({"positions": 0, "totalValue": 0, "reEvalFlags": []}))
        return

    with open(POSITIONS_PATH) as f:
        data = json.load(f)

    positions = data.get("positions", [])
    summary = data.get("summary", {})
    total = Decimal(str(summary.get("totalValue", 0)))

    threshold = load_concentration_threshold()
    re_eval = []
    if total > 0:
        for p in positions:
            market_value = p.get("marketValue")
            asset_type = (p.get("instrument") or {}).get("assetType")
            if market_value is not None:
                mv = Decimal(str(market_value))
            elif asset_type == "EQUITY" or market_value is None:
                mv = Decimal(str(p.get("quantity", 0))) * Decimal(str(p.get("currentPrice", 0)))
            pct = (mv / total * 100).quantize(Decimal("0.1"))
            if pct > threshold:
                re_eval.append({"ticker": p.get("ticker"), "weightPct": float(pct), "reason": "concentration"})

    out = {
        "positions": len(positions),
        "totalValue": float(total),
        "reEvalFlags": re_eval,
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
