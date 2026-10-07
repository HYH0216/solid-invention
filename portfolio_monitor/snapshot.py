"""Turn raw Trading 212 responses into a compact snapshot and compare it with the previous one."""

from datetime import datetime, timezone


def _num(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def build_snapshot(summary: dict, positions: list[dict]) -> dict:
    cash = summary.get("cash") or {}
    investments = summary.get("investments") or {}

    holdings = []
    for p in positions:
        instrument = p.get("instrument") or {}
        wallet = p.get("walletImpact") or {}
        holdings.append({
            "ticker": instrument.get("ticker") or p.get("ticker"),
            "name": instrument.get("name"),
            "isin": instrument.get("isin"),
            "instrument_currency": instrument.get("currency"),
            "quantity": _num(p.get("quantity")),
            "average_price": _num(p.get("averagePricePaid")),
            "current_price": _num(p.get("currentPrice")),
            "cost": _num(wallet.get("totalCost")),
            "value": _num(wallet.get("currentValue")),
            "unrealized_pl": _num(wallet.get("unrealizedProfitLoss")),
            "fx_impact": _num(wallet.get("fxImpact")),
            "opened_at": p.get("createdAt"),
        })

    invested_value = sum(h["value"] for h in holdings)
    available_cash = _num(cash.get("availableToTrade"))
    total = _num(summary.get("totalValue")) or invested_value + available_cash
    for h in holdings:
        h["weight_pct"] = round(h["value"] / total * 100, 2) if total else 0.0
        h["return_pct"] = round(h["unrealized_pl"] / h["cost"] * 100, 2) if h["cost"] else 0.0
    holdings.sort(key=lambda h: h["value"], reverse=True)

    return {
        "taken_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "currency": summary.get("currency"),
        "total_value": total,
        "cash_available": available_cash,
        "cash_in_pies": _num(cash.get("inPies")),
        "invested_value": invested_value,
        "total_cost": _num(investments.get("totalCost")),
        "unrealized_pl": _num(investments.get("unrealizedProfitLoss")),
        "realized_pl": _num(investments.get("realizedProfitLoss")),
        "holdings": holdings,
    }


def diff_snapshots(previous: dict | None, current: dict) -> dict | None:
    """Changes since the previous run, or None on the first run."""
    if not previous:
        return None

    prev = {h["ticker"]: h for h in previous.get("holdings", [])}
    curr = {h["ticker"]: h for h in current["holdings"]}

    moves = []
    for ticker, h in curr.items():
        old = prev.get(ticker)
        if not old or not old.get("current_price"):
            continue
        moves.append({
            "ticker": ticker,
            "price_change_pct": round((h["current_price"] / old["current_price"] - 1) * 100, 2),
            "value_change": round(h["value"] - old["value"], 2),
            "quantity_change": round(h["quantity"] - old["quantity"], 6),
        })
    moves.sort(key=lambda m: abs(m["price_change_pct"]), reverse=True)

    prev_total = previous.get("total_value") or 0
    return {
        "previous_taken_at": previous.get("taken_at"),
        "total_value_change": round(current["total_value"] - prev_total, 2),
        "total_value_change_pct": round((current["total_value"] / prev_total - 1) * 100, 2) if prev_total else None,
        "opened": sorted(set(curr) - set(prev)),
        "closed": sorted(set(prev) - set(curr)),
        "moves": moves,
    }
