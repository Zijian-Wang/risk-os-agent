#!/usr/bin/env python3
"""
Load portfolio positions from a Schwab CSV export and write positions.json.

Bypasses Schwab OAuth for environments where browser auth is unavailable (e.g. NAS/Docker).
Export from Schwab: Accounts > Positions > Export (top-right icon).

Usage:
    python3 skills/portfolio/scripts/load_csv.py positions.csv

Output:
    workspace/portfolio/positions.json  (same schema as get_positions.py)
"""

from __future__ import annotations

import csv
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
POSITIONS_PATH = REPO_ROOT / "workspace" / "portfolio" / "positions.json"


def _parse_decimal(value: str | None, default: str = "0") -> Decimal:
    if not value:
        return Decimal(default)
    cleaned = value.strip().replace(",", "").replace("%", "").replace("$", "")
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return Decimal(default)


def _is_cash_row(symbol: str) -> bool:
    s = symbol.strip().upper()
    return s in ("CASH & CASH INVESTMENTS", "SCHWAB ONE(R) BROKERAGE ACCOUNT", "")


def _is_total_row(symbol: str) -> bool:
    s = symbol.strip().upper()
    return "ACCOUNT TOTAL" in s or "TOTAL" == s


def load_csv(csv_path: Path) -> dict:
    """
    Parse Schwab position CSV export. Returns positions.json-compatible dict.

    Expected Schwab column headers (may vary slightly by export version):
      Symbol, Description, Qty, Price, Price Change %, Mkt Val,
      Day's Gain - Pct, Total Gain - Pct, % Of Account
    """
    positions = []
    total_value = Decimal("0")
    cash = Decimal("0")
    daily_pnl_pct = None

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        # Schwab CSVs sometimes have a header line before the column names.
        # Read until we find the row containing "Symbol".
        lines = f.readlines()

    header_idx = None
    for i, line in enumerate(lines):
        if "Symbol" in line and "Qty" in line:
            header_idx = i
            break

    if header_idx is None:
        return {"error": "Could not find header row in CSV. Expected columns: Symbol, Qty, Price, Mkt Val"}

    reader = csv.DictReader(lines[header_idx:])

    for row in reader:
        symbol = (row.get("Symbol") or "").strip()
        if not symbol:
            continue

        if _is_total_row(symbol):
            # Account total row: capture total market value and daily P&L
            total_value = _parse_decimal(row.get("Mkt Val"))
            raw_day_pct = row.get("Day's Gain - Pct") or row.get("Day's Gain -\nPct", "")
            if raw_day_pct.strip():
                daily_pnl_pct = float(_parse_decimal(raw_day_pct))
            continue

        if _is_cash_row(symbol):
            cash = _parse_decimal(row.get("Mkt Val"))
            continue

        # Skip option rows (contain spaces and special chars like C/P + strike)
        # Standard equity symbols are uppercase letters only (1-5 chars)
        if len(symbol) > 6 or " " in symbol:
            continue

        qty_raw = _parse_decimal(row.get("Qty") or row.get("Quantity", "0"))
        if qty_raw == 0:
            continue

        direction = "long" if qty_raw > 0 else "short"
        quantity = int(abs(qty_raw))
        current_price = float(_parse_decimal(row.get("Price", "0")))
        pnl_pct_raw = row.get("Total Gain - Pct") or row.get("Total Gain -\nPct", "")
        pnl_pct = float(_parse_decimal(pnl_pct_raw)) if pnl_pct_raw.strip() else None

        positions.append({
            "ticker": symbol.upper(),
            "quantity": quantity,
            "direction": direction,
            "avgCost": None,
            "currentPrice": current_price,
            "pnl": None,
            "pnlPct": pnl_pct,
            "stop": None,
        })

    # Merge manual stops from stops.json if present
    stops_path = REPO_ROOT / "workspace" / "portfolio" / "stops.json"
    if stops_path.exists():
        try:
            stops_data = json.loads(stops_path.read_text())
            stops_map = {str(k).upper(): v for k, v in stops_data.items()}
            for p in positions:
                if p["ticker"] in stops_map:
                    p["stop"] = stops_map[p["ticker"]]
        except Exception:
            pass

    return {
        "positions": positions,
        "summary": {
            "totalValue": float(total_value),
            "cash": float(cash),
            "dailyPnlPct": daily_pnl_pct,
        },
        "_source": "csv",
    }


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: load_csv.py <path-to-schwab-export.csv>"}))
        return 1

    csv_path = Path(sys.argv[1])
    if not csv_path.exists():
        print(json.dumps({"error": f"File not found: {csv_path}"}))
        return 1

    result = load_csv(csv_path)
    if "error" in result:
        print(json.dumps(result))
        return 1

    POSITIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    POSITIONS_PATH.write_text(json.dumps(result, indent=2))

    n = len(result.get("positions", []))
    total = result.get("summary", {}).get("totalValue", 0)
    print(json.dumps({
        "status": "ok",
        "positions": n,
        "totalValue": total,
        "output": str(POSITIONS_PATH),
        "_source": "csv",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
