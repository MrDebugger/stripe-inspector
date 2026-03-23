"""Invoices module."""

from stripe_inspector.modules._base import stripe_get, stripe_get_all


def inspect(key: str, deep: bool = False) -> dict:
    if deep:
        items = stripe_get_all(key, "/v1/invoices")
        has_more = False
    else:
        data = stripe_get(key, "/v1/invoices", {"limit": 100})
        items = data.get("data", [])
        has_more = data.get("has_more", False)

    invoices = []
    for inv in items:
        invoices.append({
            "id": inv.get("id"),
            "customer": inv.get("customer"),
            "amount_due": (inv.get("amount_due", 0) or 0) / 100,
            "amount_paid": (inv.get("amount_paid", 0) or 0) / 100,
            "currency": inv.get("currency"),
            "status": inv.get("status"),
            "created": inv.get("created"),
            "hosted_invoice_url": inv.get("hosted_invoice_url"),
        })

    return {
        "count": len(invoices),
        "has_more": has_more,
        "invoices": invoices,
    }
