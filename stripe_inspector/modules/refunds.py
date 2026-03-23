"""Refunds module."""

from stripe_inspector.modules._base import stripe_get, stripe_get_all


def inspect(key: str, deep: bool = False) -> dict:
    if deep:
        items = stripe_get_all(key, "/v1/refunds")
        has_more = False
    else:
        data = stripe_get(key, "/v1/refunds", {"limit": 100})
        items = data.get("data", [])
        has_more = data.get("has_more", False)

    refunds = []
    for r in items:
        refunds.append({
            "id": r.get("id"),
            "amount": (r.get("amount", 0) or 0) / 100,
            "currency": r.get("currency"),
            "status": r.get("status"),
            "reason": r.get("reason"),
            "charge": r.get("charge"),
            "created": r.get("created"),
        })

    return {
        "count": len(refunds),
        "has_more": has_more,
        "refunds": refunds,
    }
