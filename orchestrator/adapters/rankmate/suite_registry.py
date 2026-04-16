from __future__ import annotations


SUITE_CATALOG: dict[str, dict[str, str]] = {
    "auth": {
        "suite": "tests/rankmate_wave1/test_auth_api.py",
        "priority": "P0",
        "blast_radius": "core-flow",
    },
    "auth_foundation": {
        "suite": "tests/rankmate_wave1/test_auth_api.py",
        "priority": "P0",
        "blast_radius": "core-flow",
    },
    "search_store": {
        "suite": "tests/rankmate_wave1/test_search_store_api.py",
        "priority": "P1",
        "blast_radius": "release-critical",
    },
    "order_core": {
        "suite": "tests/rankmate_wave1/test_order_api.py",
        "priority": "P0",
        "blast_radius": "release-critical",
    },
    "search_discovery": {
        "suite": "tests/rankmate_wave1/test_search_store_api.py",
        "priority": "P1",
        "blast_radius": "release-critical",
    },
    "lifecycle": {
        "suite": "tests/rankmate_wave1/test_order_lifecycle_flow_api.py",
        "priority": "P0",
        "blast_radius": "release-critical",
    },
    "admin_consistency": {
        "suite": "tests/rankmate_wave1/test_admin_consistency_api.py",
        "priority": "P0",
        "blast_radius": "release-critical",
    },
    "merchant_depth": {
        "suite": "tests/rankmate_wave1/test_merchant_transition_api.py",
        "priority": "P2",
        "blast_radius": "partial-surface",
    },
    "payment_realism": {
        "suite": "tests/rankmate_wave1/test_payment_api.py",
        "priority": "P1",
        "blast_radius": "release-critical",
    },
}
