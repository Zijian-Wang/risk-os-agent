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


def main():
    if not POSITIONS_PATH.exists():
        print(json.dumps({"positions": 0, "totalValue": 0, "reEvalFlags": []}))
        return

    with open(POSITIONS_PATH) as f:
        data = json.load(f)

    positions = data.get("positions", [])
    summary = data.get("summary", {})
    total = Decimal(str(summary.get("totalValue", 0)))

    re_eval = []
    if total > 0:
        for p in positions:
            mv = Decimal(str(p.get("quantity", 0))) * Decimal(str(p.get("currentPrice", 0)))
            pct = (mv / total * 100).quantize(Decimal("0.1"))
            if float(pct) > 20:
                re_eval.append({"ticker": p.get("ticker"), "weightPct": float(pct), "reason": "concentration"})

    out = {
        "positions": len(positions),
        "totalValue": float(total),
        "reEvalFlags": re_eval,
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
