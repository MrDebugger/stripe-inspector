"""Events module."""

from stripe_inspector.modules._base import stripe_get, stripe_get_all


def inspect(key: str, deep: bool = False) -> dict:
    if deep:
        items = stripe_get_all(key, "/v1/events")
        has_more = False
    else:
        data = stripe_get(key, "/v1/events", {"limit": 20})
        items = data.get("data", [])
        has_more = data.get("has_more", False)

    events = []
    for e in items:
        events.append({
            "id": e.get("id"),
            "type": e.get("type"),
            "created": e.get("created"),
            "livemode": e.get("livemode"),
        })

    return {
        "count": len(events),
        "has_more": has_more,
        "events": events,
    }
