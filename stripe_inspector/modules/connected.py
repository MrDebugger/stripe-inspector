"""Connected accounts module (Stripe Connect)."""

from stripe_inspector.modules._base import stripe_get, stripe_get_all


def inspect(key: str, deep: bool = False) -> dict:
    if deep:
        items = stripe_get_all(key, "/v1/accounts")
        has_more = False
    else:
        data = stripe_get(key, "/v1/accounts", {"limit": 100})
        items = data.get("data", [])
        has_more = data.get("has_more", False)

    accounts = []
    for a in items:
        accounts.append({
            "id": a.get("id"),
            "email": a.get("email"),
            "country": a.get("country"),
            "type": a.get("type"),
            "charges_enabled": a.get("charges_enabled"),
            "payouts_enabled": a.get("payouts_enabled"),
            "created": a.get("created"),
        })

    return {
        "count": len(accounts),
        "has_more": has_more,
        "accounts": accounts,
    }
