"""Products module."""

from stripe_inspector.modules._base import stripe_get, stripe_get_all


def inspect(key: str, deep: bool = False) -> dict:
    if deep:
        items = stripe_get_all(key, "/v1/products")
        has_more = False
    else:
        data = stripe_get(key, "/v1/products", {"limit": 100})
        items = data.get("data", [])
        has_more = data.get("has_more", False)

    products = []
    for p in items:
        products.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "description": p.get("description"),
            "active": p.get("active"),
            "type": p.get("type"),
            "created": p.get("created"),
            "default_price": p.get("default_price"),
            "metadata": p.get("metadata", {}),
        })

    return {
        "count": len(products),
        "has_more": has_more,
        "products": products,
    }
