"""Payment intents module."""

from stripe_inspector.modules._base import stripe_get, stripe_get_all


def inspect(key: str, deep: bool = False) -> dict:
    if deep:
        items = stripe_get_all(key, "/v1/payment_intents")
        has_more = False
    else:
        data = stripe_get(key, "/v1/payment_intents", {"limit": 100})
        items = data.get("data", [])
        has_more = data.get("has_more", False)

    intents = []
    for pi in items:
        intents.append({
            "id": pi.get("id"),
            "amount": (pi.get("amount", 0) or 0) / 100,
            "currency": pi.get("currency"),
            "status": pi.get("status"),
            "created": pi.get("created"),
            "description": pi.get("description"),
            "customer": pi.get("customer"),
            "payment_method_types": pi.get("payment_method_types", []),
        })

    return {
        "count": len(intents),
        "has_more": has_more,
        "intents": intents,
    }
