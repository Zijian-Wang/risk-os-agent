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

LONG_CLOSE_INSTRUCTIONS = {"SELL", "SELL_TO_CLOSE"}
SHORT_CLOSE_INSTRUCTIONS = {"BUY", "BUY_TO_COVER", "BUY_TO_CLOSE"}


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


def to_decimal(value, default="0"):
    try:
        return Decimal(str(value))
    except Exception:
        return Decimal(default)


def to_float(value):
    try:
        return float(Decimal(str(value)))
    except Exception:
        return None


def normalize_instruction(value) -> str:
    return str(value or "").strip().upper()


def resolve_local_stop(stops: dict, symbol: str, direction: str):
    if not isinstance(stops, dict):
        return None
    value = stops.get(symbol)
    if isinstance(value, dict):
        directional = value.get(direction)
        if directional is not None:
            return to_float(directional)
        direct_stop = value.get("stop")
        if direct_stop is not None:
            return to_float(direct_stop)
        return None
    return to_float(value)


def fetch_protective_orders(client, account_hash) -> dict:
    """Fetch active protective orders. Returns {symbol: [candidate,...]}."""
    candidates = {}
    try:
        from schwab.client import Client
        rules = load_risk_rules().get("schwab_order_detection", {})
        status_names = rules.get("active_statuses", []) if isinstance(rules, dict) else []
        if not isinstance(status_names, list) or not status_names:
            status_names = ["WORKING", "AWAITING_STOP_CONDITION", "QUEUED", "PENDING_ACTIVATION"]
        order_types = rules.get("protective_order_types", []) if isinstance(rules, dict) else []
        if not isinstance(order_types, list) or not order_types:
            order_types = ["STOP", "STOP_LIMIT", "TRAILING_STOP"]
        short_limit_as_stop = bool(
            rules.get("short_limit_as_stop_fallback", True)
        ) if isinstance(rules, dict) else True

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
            return candidates
        data = resp.json()
        orders = data if isinstance(data, list) else data.get("orders", data.get("order", []))
        if not isinstance(orders, list):
            orders = []
        allowed_types = {str(x).upper() for x in order_types if isinstance(x, str)}
        for order in orders:
            order_type = (order.get("orderType") or "").upper()
            stop_price = to_float(order.get("stopPrice"))
            limit_price = to_float(order.get("price"))
            legs = order.get("orderLegCollection", [])
            for leg in legs:
                inst = leg.get("instrument", {})
                symbol = inst.get("symbol") if isinstance(inst, dict) else None
                instruction = normalize_instruction(leg.get("instruction"))
                if not symbol:
                    continue

                if order_type in allowed_types and stop_price is not None:
                    candidates.setdefault(symbol, []).append(
                        {
                            "kind": "stop",
                            "price": stop_price,
                            "instruction": instruction,
                            "orderType": order_type,
                        }
                    )
                elif (
                    short_limit_as_stop
                    and order_type == "LIMIT"
                    and limit_price is not None
                    and instruction in SHORT_CLOSE_INSTRUCTIONS
                ):
                    candidates.setdefault(symbol, []).append(
                        {
                            "kind": "limit",
                            "price": limit_price,
                            "instruction": instruction,
                            "orderType": order_type,
                        }
                    )
    except Exception:
        pass
    return candidates


def parse_position(
    pos: dict,
    protective_orders: dict,
    local_stops: dict,
    short_limit_as_stop_fallback: bool = True,
) -> dict | None:
    """Parse Schwab position to our format. Handles common response shapes."""
    try:
        inst = pos.get("instrument", {}) or pos.get("symbol", {})
        if isinstance(inst, dict):
            symbol = inst.get("symbol") or inst.get("ticker")
        else:
            symbol = str(inst)
        if not symbol:
            return None

        long_qty = to_decimal(pos.get("longQuantity", 0) or pos.get("quantity", 0))
        short_qty = to_decimal(pos.get("shortQuantity", 0))
        if long_qty > 0:
            direction = "long"
            qty = long_qty
        elif short_qty > 0:
            direction = "short"
            qty = short_qty
        else:
            return None

        avg_price = to_decimal(pos.get("averagePrice", 0) or pos.get("costBasis", 0) or 0)
        if direction == "short" and avg_price < 0:
            avg_price = abs(avg_price)

        mkt_val = pos.get("marketValue") or pos.get("currentMarketValue")
        if isinstance(mkt_val, dict):
            mkt_val = mkt_val.get("amount") or mkt_val.get("value")
        mkt_val = to_decimal(mkt_val or 0)

        if direction == "short":
            current_price = (abs(mkt_val) / qty).quantize(Decimal("0.01")) if qty else Decimal("0")
            pnl = ((avg_price - current_price) * qty).quantize(Decimal("0.01"))
        else:
            current_price = (mkt_val / qty).quantize(Decimal("0.01")) if qty else Decimal("0")
            pnl = ((current_price - avg_price) * qty).quantize(Decimal("0.01"))
        cost = (avg_price * qty).quantize(Decimal("0.01"))
        pnl_pct = (pnl / cost * 100).quantize(Decimal("0.01")) if cost else Decimal("0")

        candidates = protective_orders.get(symbol, []) if isinstance(protective_orders, dict) else []
        stop_from_orders = None
        for candidate in candidates:
            kind = str(candidate.get("kind", "")).lower()
            instruction = normalize_instruction(candidate.get("instruction"))
            price = to_float(candidate.get("price"))
            if price is None:
                continue

            if direction == "long":
                if kind == "stop" and (not instruction or instruction in LONG_CLOSE_INSTRUCTIONS):
                    stop_from_orders = price
                    break
            else:
                if kind == "stop" and (not instruction or instruction in SHORT_CLOSE_INSTRUCTIONS):
                    stop_from_orders = price
                    break
                if (
                    kind == "limit"
                    and short_limit_as_stop_fallback
                    and (not instruction or instruction in SHORT_CLOSE_INSTRUCTIONS)
                    and Decimal(str(price)) > avg_price
                ):
                    stop_from_orders = price
                    break

        stop = stop_from_orders
        if stop is None:
            stop = resolve_local_stop(local_stops, symbol, direction)

        return {
            "ticker": symbol,
            "quantity": int(qty),
            "direction": direction,
            "avgCost": float(avg_price.quantize(Decimal("0.01"))),
            "currentPrice": float(current_price),
            "pnl": float(pnl),
            "pnlPct": float(pnl_pct),
            "stop": stop,
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
    rules = load_risk_rules().get("schwab_order_detection", {})
    short_limit_as_stop_fallback = bool(
        rules.get("short_limit_as_stop_fallback", True)
    ) if isinstance(rules, dict) else True
    protective_orders = fetch_protective_orders(client, account_hash)
    local_stops = load_stops()

    positions = []
    for sec in data.get("securitiesAccount", {}).get("positions", []):
        p = parse_position(
            sec,
            protective_orders,
            local_stops,
            short_limit_as_stop_fallback=short_limit_as_stop_fallback,
        )
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
