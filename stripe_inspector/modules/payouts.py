"""Payouts module."""

from stripe_inspector.modules._base import stripe_get, stripe_get_all


def inspect(key: str, deep: bool = False) -> dict:
    if deep:
        items = stripe_get_all(key, "/v1/payouts")
        has_more = False
    else:
        data = stripe_get(key, "/v1/payouts", {"limit": 100})
        items = data.get("data", [])
        has_more = data.get("has_more", False)

    payouts = []
    for p in items:
        payouts.append({
            "id": p.get("id"),
            "amount": (p.get("amount", 0) or 0) / 100,
            "currency": p.get("currency"),
            "status": p.get("status"),
            "method": p.get("method"),
            "type": p.get("type"),
            "arrival_date": p.get("arrival_date"),
            "created": p.get("created"),
            "destination": p.get("destination"),
            "description": p.get("description"),
        })

    return {
        "count": len(payouts),
        "has_more": has_more,
        "payouts": payouts,
    }
