"""Coupons module."""

from stripe_inspector.modules._base import stripe_get, stripe_get_all


def inspect(key: str, deep: bool = False) -> dict:
    if deep:
        items = stripe_get_all(key, "/v1/coupons")
        has_more = False
    else:
        data = stripe_get(key, "/v1/coupons", {"limit": 100})
        items = data.get("data", [])
        has_more = data.get("has_more", False)

    coupons = []
    for c in items:
        coupons.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "percent_off": c.get("percent_off"),
            "amount_off": (c.get("amount_off") or 0) / 100 if c.get("amount_off") else None,
            "currency": c.get("currency"),
            "duration": c.get("duration"),
            "times_redeemed": c.get("times_redeemed"),
            "valid": c.get("valid"),
            "created": c.get("created"),
        })

    return {
        "count": len(coupons),
        "has_more": has_more,
        "coupons": coupons,
    }
