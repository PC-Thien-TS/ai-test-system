from __future__ import annotations


SUITE_CATALOG: dict[str, dict[str, str]] = {
    "auth_foundation": {
        "suite": "tests/ecommerce_alpha/test_auth_foundation_api.py",
        "priority": "P0",
        "blast_radius": "release-critical",
    },
    "catalog_discovery": {
        "suite": "tests/ecommerce_alpha/test_catalog_discovery_api.py",
        "priority": "P1",
        "blast_radius": "release-critical",
    },
    "cart_checkout": {
        "suite": "tests/ecommerce_alpha/test_cart_checkout_api.py",
        "priority": "P0",
        "blast_radius": "release-critical",
    },
    "order_management": {
        "suite": "tests/ecommerce_alpha/test_order_management_api.py",
        "priority": "P0",
        "blast_radius": "release-critical",
    },
    "payment_integrity": {
        "suite": "tests/ecommerce_alpha/test_payment_integrity_api.py",
        "priority": "P1",
        "blast_radius": "release-critical",
    },
    "admin_ops": {
        "suite": "tests/ecommerce_alpha/test_admin_ops_api.py",
        "priority": "P0",
        "blast_radius": "release-critical",
    },
    "auth": {
        "suite": "tests/ecommerce_alpha/test_auth_foundation_api.py",
        "priority": "P1",
        "blast_radius": "partial-surface",
    },
    "order_core": {
        "suite": "tests/ecommerce_alpha/test_order_management_api.py",
        "priority": "P1",
        "blast_radius": "partial-surface",
    },
    "search_store": {
        "suite": "tests/ecommerce_alpha/test_catalog_discovery_api.py",
        "priority": "P1",
        "blast_radius": "partial-surface",
    },
    "lifecycle": {
        "suite": "tests/ecommerce_alpha/test_order_management_api.py",
        "priority": "P1",
        "blast_radius": "partial-surface",
    },
    "admin_consistency": {
        "suite": "tests/ecommerce_alpha/test_admin_ops_api.py",
        "priority": "P1",
        "blast_radius": "partial-surface",
    },
    "merchant_depth": {
        "suite": "tests/ecommerce_alpha/test_order_management_api.py",
        "priority": "P1",
        "blast_radius": "partial-surface",
    },
    "payment_realism": {
        "suite": "tests/ecommerce_alpha/test_payment_integrity_api.py",
        "priority": "P1",
        "blast_radius": "partial-surface",
    },
}

