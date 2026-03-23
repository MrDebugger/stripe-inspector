"""Base utilities for Stripe API requests."""

import requests

STRIPE_BASE = "https://api.stripe.com"

# Track rate limit info from the last response
rate_limit_info = {
    "remaining": None,
    "limit": None,
    "total_requests": 0,
}


def stripe_get(key: str, endpoint: str, params: dict = None) -> dict:
    url = f"{STRIPE_BASE}{endpoint}"
    resp = requests.get(url, auth=(key, ""), params=params, timeout=30)

    # Track rate limits from headers
    rate_limit_info["total_requests"] += 1
    if "Stripe-Rate-Limit-Remaining" in resp.headers:
        rate_limit_info["remaining"] = int(resp.headers["Stripe-Rate-Limit-Remaining"])
    if "Stripe-Rate-Limit-Limit" in resp.headers:
        rate_limit_info["limit"] = int(resp.headers["Stripe-Rate-Limit-Limit"])

    if resp.status_code == 429:
        raise ConnectionError("Rate limited by Stripe. Wait and retry.")
    if resp.status_code == 403:
        raise PermissionError(f"Access denied to {endpoint}")
    if resp.status_code == 401:
        raise PermissionError(f"Invalid API key for {endpoint}")
    if resp.status_code >= 500:
        raise ConnectionError(f"Stripe server error ({resp.status_code})")
    if resp.status_code != 200:
        error = resp.json().get("error", {})
        msg = error.get("message", f"HTTP {resp.status_code}")
        raise Exception(msg)

    return resp.json()


def stripe_get_all(key: str, endpoint: str, params: dict = None, max_pages: int = 50) -> list:
    """Fetch all pages of a paginated Stripe list endpoint.

    Returns a flat list of all items across pages. Stops at max_pages to
    prevent runaway pagination (default 50 pages = up to 5000 items).
    """
    params = dict(params or {})
    params.setdefault("limit", 100)

    all_items = []
    pages = 0

    while pages < max_pages:
        data = stripe_get(key, endpoint, params)
        items = data.get("data", [])
        all_items.extend(items)
        pages += 1

        if not data.get("has_more") or not items:
            break

        # Set cursor for next page
        params["starting_after"] = items[-1]["id"]

    return all_items


def get_rate_limit_info() -> dict:
    return dict(rate_limit_info)
