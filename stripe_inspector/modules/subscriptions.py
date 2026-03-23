"""Subscriptions module."""

from stripe_inspector.modules._base import stripe_get, stripe_get_all


def inspect(key: str, deep: bool = False) -> dict:
    if deep:
        items = stripe_get_all(key, "/v1/subscriptions")
        has_more = False
    else:
        data = stripe_get(key, "/v1/subscriptions", {"limit": 100})
        items = data.get("data", [])
        has_more = data.get("has_more", False)

    subs = []
    for s in items:
        subs.append({
            "id": s.get("id"),
            "customer": s.get("customer"),
            "status": s.get("status"),
            "currency": s.get("currency"),
            "created": s.get("created"),
            "current_period_start": s.get("current_period_start"),
            "current_period_end": s.get("current_period_end"),
            "cancel_at_period_end": s.get("cancel_at_period_end"),
        })

    return {
        "count": len(subs),
        "has_more": has_more,
        "subscriptions": subs,
    }
