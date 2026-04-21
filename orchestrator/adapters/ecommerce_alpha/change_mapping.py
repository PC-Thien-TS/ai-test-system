from __future__ import annotations


_FILE_FLOW_RULES: tuple[tuple[str, str], ...] = (
    ("auth", "auth_foundation"),
    ("foundation", "auth_foundation"),
    ("login", "auth_foundation"),
    ("token", "auth_foundation"),
    ("catalog", "catalog_discovery"),
    ("discovery", "catalog_discovery"),
    ("product", "catalog_discovery"),
    ("search", "catalog_discovery"),
    ("cart", "cart_checkout"),
    ("checkout", "cart_checkout"),
    ("order", "cart_checkout"),
    ("fulfillment", "order_management"),
    ("management", "order_management"),
    ("order", "order_management"),
    ("shipment", "order_management"),
    ("billing", "payment_integrity"),
    ("integrity", "payment_integrity"),
    ("payment", "payment_integrity"),
    ("transaction", "payment_integrity"),
    ("webhook", "payment_integrity"),
    ("admin", "admin_ops"),
    ("console", "admin_ops"),
    ("ops", "admin_ops"),
)


def map_changed_files_to_flows(files: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for file_path in files:
        normalized = file_path.replace("\\", "/").lower()
        for token, flow_id in _FILE_FLOW_RULES:
            if token not in normalized:
                continue
            result.setdefault(flow_id, []).append(file_path)
    return result

