"""Core inspector engine that orchestrates all modules."""

import re
import time
from typing import Optional

from stripe_inspector.modules import (
    account,
    balance,
    balance_transactions,
    charges,
    connected,
    coupons,
    customers,
    disputes,
    events,
    invoices,
    payment_intents,
    payouts,
    permission_scan,
    products,
    refunds,
    subscriptions,
    webhooks,
)

ALL_MODULES = {
    "account": account,
    "balance": balance,
    "customers": customers,
    "charges": charges,
    "payment_intents": payment_intents,
    "products": products,
    "payouts": payouts,
    "subscriptions": subscriptions,
    "invoices": invoices,
    "webhooks": webhooks,
    "events": events,
    "connected": connected,
    "disputes": disputes,
    "refunds": refunds,
    "balance_transactions": balance_transactions,
    "coupons": coupons,
    "permission_scan": permission_scan,
}

KEY_PATTERNS = {
    r"^sk_test_": "secret_test",
    r"^sk_live_": "secret_live",
    r"^rk_test_": "restricted_test",
    r"^rk_live_": "restricted_live",
}


def detect_key_type(key: str) -> Optional[str]:
    for pattern, key_type in KEY_PATTERNS.items():
        if re.match(pattern, key):
            return key_type
    return None


def mask_key(key: str) -> str:
    if len(key) <= 12:
        return key[:4] + "..." + key[-4:]
    return key[:8] + "..." + key[-4:]


class StripeInspector:
    def __init__(self, key: str, modules: Optional[list[str]] = None, deep: bool = False):
        self.key = key
        self.key_type = detect_key_type(key)
        self.masked_key = mask_key(key)
        self.deep = deep
        self.modules_to_run = modules or list(ALL_MODULES.keys())

    def validate_key(self) -> bool:
        return self.key_type is not None

    def inspect(self, progress_callback=None) -> dict:
        if not self.validate_key():
            return {
                "error": "Invalid key format. Expected sk_test_*, sk_live_*, rk_test_*, or rk_live_*",
                "key_type": None,
                "masked_key": self.masked_key,
            }

        start_time = time.time()

        result = {
            "key_type": self.key_type,
            "masked_key": self.masked_key,
            "is_live": "live" in self.key_type,
            "is_restricted": "restricted" in self.key_type,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "modules": {},
            "permissions": {},
        }

        for name in self.modules_to_run:
            if name not in ALL_MODULES:
                continue

            module = ALL_MODULES[name]

            if progress_callback:
                progress_callback(name)

            try:
                import inspect as _inspect
                sig = _inspect.signature(module.inspect)
                if 'deep' in sig.parameters:
                    data = module.inspect(self.key, deep=self.deep)
                else:
                    data = module.inspect(self.key)
                result["modules"][name] = {
                    "success": True,
                    "data": data,
                }
                result["permissions"][name] = "allowed"
            except PermissionError:
                result["modules"][name] = {
                    "success": False,
                    "error": "Permission denied (403)",
                }
                result["permissions"][name] = "denied"
            except ConnectionError as e:
                result["modules"][name] = {
                    "success": False,
                    "error": f"Connection error: {e}",
                }
                result["permissions"][name] = "error"
            except Exception as e:
                result["modules"][name] = {
                    "success": False,
                    "error": str(e),
                }
                result["permissions"][name] = "error"

        # PII summary
        from stripe_inspector.pii import scan_pii
        result["pii"] = scan_pii(result)

        # Rate limit info
        from stripe_inspector.modules._base import get_rate_limit_info
        result["rate_limit"] = get_rate_limit_info()

        # Scan duration
        result["duration_seconds"] = round(time.time() - start_time, 2)

        return result
