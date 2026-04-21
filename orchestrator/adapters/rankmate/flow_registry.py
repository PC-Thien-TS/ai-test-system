from __future__ import annotations

from orchestrator.adapters.base.models import FlowDefinition


FLOW_REGISTRY: dict[str, FlowDefinition] = {
    "search_discovery": FlowDefinition(
        flow_id="search_discovery",
        title="Search & Discovery Flow",
        description="Store search, suggestions, and detail eligibility funnel.",
        suites=("tests/rankmate_wave1/test_search_store_api.py",),
        release_critical=True,
    ),
    "order_core": FlowDefinition(
        flow_id="order_core",
        title="Order Core Flow",
        description="Order contracts, lifecycle seed generation, and core state progression.",
        suites=(
            "tests/rankmate_wave1/test_order_api.py",
            "tests/rankmate_wave1/test_order_lifecycle_flow_api.py",
        ),
        release_critical=True,
    ),
    "merchant_handling": FlowDefinition(
        flow_id="merchant_handling",
        title="Merchant Handling Flow",
        description="Merchant queue/detail and transition-state behavior.",
        suites=("tests/rankmate_wave1/test_merchant_transition_api.py",),
        release_critical=True,
    ),
    "admin_consistency": FlowDefinition(
        flow_id="admin_consistency",
        title="Admin Consistency Flow",
        description="Cross-surface continuity across user, merchant, and admin.",
        suites=("tests/rankmate_wave1/test_admin_consistency_api.py",),
        release_critical=True,
    ),
    "payment_integrity": FlowDefinition(
        flow_id="payment_integrity",
        title="Payment Integrity Flow",
        description="Payment init/verify/retry/webhook integrity coverage.",
        suites=("tests/rankmate_wave1/test_payment_api.py",),
        release_critical=True,
    ),
    "auth_foundation": FlowDefinition(
        flow_id="auth_foundation",
        title="Auth Foundation Flow",
        description="Authentication contract and token baseline.",
        suites=("tests/rankmate_wave1/test_auth_api.py",),
        release_critical=True,
    ),
}

FLOW_ORDER: tuple[str, ...] = (
    "auth_foundation",
    "search_discovery",
    "order_core",
    "merchant_handling",
    "admin_consistency",
    "payment_integrity",
)

CORE_ANCHOR_FLOWS: tuple[str, ...] = (
    "auth_foundation",
    "order_core",
    "admin_consistency",
)

RELEASE_CRITICAL_FLOWS: tuple[str, ...] = (
    "auth_foundation",
    "order_core",
    "search_discovery",
    "merchant_handling",
    "admin_consistency",
    "payment_integrity",
)

