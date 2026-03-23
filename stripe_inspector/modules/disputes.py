"""Disputes module."""

from stripe_inspector.modules._base import stripe_get, stripe_get_all


def inspect(key: str, deep: bool = False) -> dict:
    if deep:
        items = stripe_get_all(key, "/v1/disputes")
        has_more = False
    else:
        data = stripe_get(key, "/v1/disputes", {"limit": 100})
        items = data.get("data", [])
        has_more = data.get("has_more", False)

    disputes = []
    for d in items:
        disputes.append({
            "id": d.get("id"),
            "amount": (d.get("amount", 0) or 0) / 100,
            "currency": d.get("currency"),
            "status": d.get("status"),
            "reason": d.get("reason"),
            "charge": d.get("charge"),
            "created": d.get("created"),
            "is_charge_refundable": d.get("is_charge_refundable"),
        })

    return {
        "count": len(disputes),
        "has_more": has_more,
        "disputes": disputes,
    }
