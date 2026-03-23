"""Customers module."""

from stripe_inspector.modules._base import stripe_get, stripe_get_all


def inspect(key: str, deep: bool = False) -> dict:
    if deep:
        items = stripe_get_all(key, "/v1/customers")
        has_more = False
    else:
        data = stripe_get(key, "/v1/customers", {"limit": 100})
        items = data.get("data", [])
        has_more = data.get("has_more", False)

    customers = []
    for c in items:
        customers.append({
            "id": c.get("id"),
            "name": c.get("name"),
            "email": c.get("email"),
            "phone": c.get("phone"),
            "currency": c.get("currency"),
            "balance": (c.get("balance", 0) or 0) / 100,
            "created": c.get("created"),
            "metadata": c.get("metadata", {}),
            "country": (c.get("address") or {}).get("country"),
        })

    return {
        "count": len(customers),
        "has_more": has_more,
        "customers": customers,
    }
