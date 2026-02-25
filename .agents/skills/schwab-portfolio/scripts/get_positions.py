#!/usr/bin/env python3
"""
Fetch positions and account summary from Schwab API. Self-contained.
Requires: pip install schwab-py
Env: SCHWAB_API_KEY, SCHWAB_APP_SECRET; optional SCHWAB_CALLBACK_URL, SCHWAB_TOKEN_PATH
"""

import json
import os
import sys
from decimal import Decimal
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
WORKSPACE = REPO_ROOT / "workspace" / "portfolio"
WORKSPACE.mkdir(parents=True, exist_ok=True)

TOKEN_PATH = Path(os.environ.get("SCHWAB_TOKEN_PATH", str(WORKSPACE / "token.json")))
STOPS_PATH = WORKSPACE / "stops.json"
OUTPUT_PATH = WORKSPACE / "positions.json"


def load_risk_rules() -> dict:
    cfg_path = REPO_ROOT / "config" / "risk-rules.yaml"
    try:
        import yaml

        if cfg_path.exists():
            with open(cfg_path) as f:
                cfg = yaml.safe_load(f) or {}
                return cfg if isinstance(cfg, dict) else {}
    except Exception:
        pass
    return {}


def load_stops():
    """Local stops from workspace/portfolio/stops.json (fallback)."""
    if STOPS_PATH.exists():
        with open(STOPS_PATH) as f:
            return json.load(f)
    return {}


def fetch_stop_orders(client, account_hash) -> dict:
    """Fetch active stop orders from Schwab API. Returns {symbol: stop_price}."""
    stops = {}
    try:
        from schwab.client import Client
        rules = load_risk_rules().get("schwab_order_detection", {})
        status_names = rules.get("active_statuses", []) if isinstance(rules, dict) else []
        if not isinstance(status_names, list) or not status_names:
            status_names = ["WORKING", "AWAITING_STOP_CONDITION", "QUEUED", "PENDING_ACTIVATION"]
        order_types = rules.get("protective_order_types", []) if isinstance(rules, dict) else []
        if not isinstance(order_types, list) or not order_types:
            order_types = ["STOP", "STOP_LIMIT", "TRAILING_STOP"]

        statuses = []
        for name in status_names:
            if not isinstance(name, str):
                continue
            status_enum = getattr(Client.Order.Status, name, None)
            if status_enum is not None:
                statuses.append(status_enum)
        if not statuses:
            for name in ["WORKING", "AWAITING_STOP_CONDITION", "QUEUED", "PENDING_ACTIVATION"]:
                status_enum = getattr(Client.Order.Status, name, None)
                if status_enum is not None:
                    statuses.append(status_enum)

        resp = client.get_orders_for_account(
            account_hash,
            statuses=statuses,
            max_results=50,
        )
        if resp.status_code != 200:
            return stops
        data = resp.json()
        orders = data if isinstance(data, list) else data.get("orders", data.get("order", []))
        if not isinstance(orders, list):
            orders = []
        allowed_types = {str(x).upper() for x in order_types if isinstance(x, str)}
        for order in orders:
            order_type = (order.get("orderType") or "").upper()
            if order_type not in allowed_types:
                continue
            stop_price = order.get("stopPrice")
            if stop_price is None:
                continue
            legs = order.get("orderLegCollection", [])
            for leg in legs:
                inst = leg.get("instrument", {})
                symbol = inst.get("symbol") if isinstance(inst, dict) else None
                if symbol:
                    stops[symbol] = float(stop_price)
    except Exception:
        pass
    return stops


def parse_position(pos: dict, stops: dict) -> dict | None:
    """Parse Schwab position to our format. Handles common response shapes."""
    try:
        inst = pos.get("instrument", {}) or pos.get("symbol", {})
        if isinstance(inst, dict):
            symbol = inst.get("symbol") or inst.get("ticker")
        else:
            symbol = str(inst)
        if not symbol:
            return None

        qty = Decimal(str(pos.get("longQuantity", 0) or pos.get("quantity", 0))) - Decimal(
            str(pos.get("shortQuantity", 0))
        )
        if qty <= 0:
            return None

        avg_price = Decimal(str(pos.get("averagePrice", 0) or pos.get("costBasis", 0) or 0))
        mkt_val = pos.get("marketValue") or pos.get("currentMarketValue")
        if isinstance(mkt_val, dict):
            mkt_val = mkt_val.get("amount") or mkt_val.get("value")
        mkt_val = Decimal(str(mkt_val or 0))
        cost = avg_price * qty
        current_price = (mkt_val / qty).quantize(Decimal("0.01")) if qty else Decimal("0")
        pnl = mkt_val - cost
        pnl_pct = (pnl / cost * 100).quantize(Decimal("0.01")) if cost else Decimal("0")

        return {
            "ticker": symbol,
            "quantity": int(qty),
            "avgCost": float(avg_price.quantize(Decimal("0.01"))),
            "currentPrice": float(current_price),
            "pnl": float(pnl.quantize(Decimal("0.01"))),
            "pnlPct": float(pnl_pct),
            "stop": stops.get(symbol),
        }
    except Exception:
        return None


def main():
    api_key = os.environ.get("SCHWAB_API_KEY")
    app_secret = os.environ.get("SCHWAB_APP_SECRET")
    if not api_key or not app_secret:
        # Fallback to cache
        if OUTPUT_PATH.exists():
            with open(OUTPUT_PATH) as f:
                data = json.load(f)
            data["_cached"] = True
            print(json.dumps(data))
            return
        out = {"error": "SCHWAB_API_KEY and SCHWAB_APP_SECRET required. Run auth_schwab.py first.", "positions": [], "summary": {}}
        print(json.dumps(out))
        sys.exit(1)

    if not TOKEN_PATH.exists():
        out = {"error": f"Token not found at {TOKEN_PATH}. Run auth_schwab.py to authenticate.", "positions": [], "summary": {}}
        print(json.dumps(out))
        sys.exit(1)

    try:
        from schwab.auth import client_from_token_file
        from schwab.client import Client
    except ImportError:
        out = {"error": "schwab-py required: pip install schwab-py", "positions": [], "summary": {}}
        print(json.dumps(out))
        sys.exit(1)

    client = client_from_token_file(
        str(TOKEN_PATH), api_key=api_key, app_secret=app_secret
    )

    resp = client.get_account_numbers()
    if resp.status_code != 200:
        out = {"error": f"Failed to get accounts: {resp.text}", "positions": [], "summary": {}}
        print(json.dumps(out))
        sys.exit(1)

    accounts = resp.json()
    if not accounts:
        out = {"error": "No accounts found", "positions": [], "summary": {}}
        print(json.dumps(out))
        sys.exit(1)

    account_hash = accounts[0]["hashValue"]
    resp = client.get_account(account_hash, fields=[Client.Account.Fields.POSITIONS])
    if resp.status_code != 200:
        out = {"error": f"Failed to get positions: {resp.text}", "positions": [], "summary": {}}
        print(json.dumps(out))
        sys.exit(1)

    data = resp.json()
    stops = fetch_stop_orders(client, account_hash)
    if not stops:
        stops = load_stops()

    positions = []
    for sec in data.get("securitiesAccount", {}).get("positions", []):
        p = parse_position(sec, stops)
        if p:
            positions.append(p)

    # Summary from Schwab
    sec = data.get("securitiesAccount", {})
    total = sec.get("currentBalances", {}).get("liquidationValue") or sec.get("initialBalances", {}).get("liquidationValue")
    cash = sec.get("currentBalances", {}).get("cashBalance") or sec.get("initialBalances", {}).get("cashBalance")
    if isinstance(total, dict):
        total = total.get("amount") or total.get("value")
    if isinstance(cash, dict):
        cash = cash.get("value") or cash.get("amount")

    summary = {
        "totalValue": float(total or 0),
        "cash": float(cash or 0),
        "dailyPnlPct": None,  # Schwab may provide in different field
    }

    out = {"positions": positions, "summary": summary}

    # Cache for risk-calculator and offline use
    with open(OUTPUT_PATH, "w") as f:
        json.dump(out, f, indent=2)

    print(json.dumps(out))


if __name__ == "__main__":
    main()
