"""CSV export for inspection results."""

import csv
import io


def result_to_csv(result: dict) -> dict[str, str]:
    """Convert inspection result to per-module CSV strings.

    Returns a dict of {module_name: csv_string}.
    """
    csvs = {}

    for name, mod in result.get("modules", {}).items():
        if not mod.get("success"):
            continue

        data = mod["data"]

        # Find the list key
        list_keys = [
            "customers", "charges", "intents", "products", "payouts",
            "subscriptions", "invoices", "endpoints", "events", "accounts",
            "disputes", "refunds", "transactions", "coupons",
            "allowed", "denied", "errors",
        ]

        items = None
        for lk in list_keys:
            if lk in data and isinstance(data[lk], list) and data[lk]:
                items = data[lk]
                break

        if not items:
            # Key-value module (account, balance) — single row
            if isinstance(data, dict):
                flat = _flatten_dict(data)
                if flat:
                    buf = io.StringIO()
                    writer = csv.DictWriter(buf, fieldnames=flat.keys())
                    writer.writeheader()
                    writer.writerow(flat)
                    csvs[name] = buf.getvalue()
            continue

        # List of strings (permission_scan allowed/denied)
        if items and isinstance(items[0], str):
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["value"])
            for item in items:
                writer.writerow([item])
            csvs[name] = buf.getvalue()
            continue

        # List of dicts
        if items and isinstance(items[0], dict):
            fields = [k for k in items[0].keys() if k != "metadata"]
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for item in items:
                writer.writerow({k: item.get(k, "") for k in fields})
            csvs[name] = buf.getvalue()

    return csvs


def _flatten_dict(d: dict, prefix: str = "") -> dict:
    flat = {}
    for k, v in d.items():
        key = f"{prefix}{k}" if not prefix else f"{prefix}.{k}"
        if isinstance(v, dict):
            flat.update(_flatten_dict(v, key))
        elif isinstance(v, list):
            flat[key] = ", ".join(str(x) for x in v)
        else:
            flat[key] = v
    return flat
