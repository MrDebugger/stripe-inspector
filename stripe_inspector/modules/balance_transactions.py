"""Balance transactions module."""

from stripe_inspector.modules._base import stripe_get, stripe_get_all


def inspect(key: str, deep: bool = False) -> dict:
    if deep:
        items = stripe_get_all(key, "/v1/balance_transactions")
        has_more = False
    else:
        data = stripe_get(key, "/v1/balance_transactions", {"limit": 100})
        items = data.get("data", [])
        has_more = data.get("has_more", False)

    txns = []
    for t in items:
        txns.append({
            "id": t.get("id"),
            "amount": (t.get("amount", 0) or 0) / 100,
            "net": (t.get("net", 0) or 0) / 100,
            "fee": (t.get("fee", 0) or 0) / 100,
            "currency": t.get("currency"),
            "type": t.get("type"),
            "status": t.get("status"),
            "description": t.get("description"),
            "created": t.get("created"),
            "source": t.get("source"),
        })

    return {
        "count": len(txns),
        "has_more": has_more,
        "transactions": txns,
    }
