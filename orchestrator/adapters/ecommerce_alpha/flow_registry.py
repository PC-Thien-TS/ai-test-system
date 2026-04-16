from __future__ import annotations

from orchestrator.adapters.base.models import FlowDefinition


FLOW_REGISTRY: dict[str, FlowDefinition] = {
    "auth_foundation": FlowDefinition(
        flow_id="auth_foundation",
        title="Auth Foundation",
        description="Authentication and token baseline.",
        suites=("tests/ecommerce_alpha/test_auth_foundation_api.py",),
        release_critical=True,
    ),
    "catalog_discovery": FlowDefinition(
        flow_id="catalog_discovery",
        title="Catalog Discovery",
        description="Catalog/search/listing funnel.",
        suites=("tests/ecommerce_alpha/test_catalog_discovery_api.py",),
        release_critical=True,
    ),
    "cart_checkout": FlowDefinition(
        flow_id="cart_checkout",
        title="Cart & Checkout",
        description="Cart management and checkout path.",
        suites=("tests/ecommerce_alpha/test_cart_checkout_api.py",),
        release_critical=True,
    ),
    "order_management": FlowDefinition(
        flow_id="order_management",
        title="Order Management",
        description="Order status and fulfillment lifecycle.",
        suites=("tests/ecommerce_alpha/test_order_management_api.py",),
        release_critical=True,
    ),
    "payment_integrity": FlowDefinition(
        flow_id="payment_integrity",
        title="Payment Integrity",
        description="Payment initiation and callback integrity.",
        suites=("tests/ecommerce_alpha/test_payment_integrity_api.py",),
        release_critical=True,
    ),
    "admin_ops": FlowDefinition(
        flow_id="admin_ops",
        title="Admin Operations",
        description="Admin operational consistency and controls.",
        suites=("tests/ecommerce_alpha/test_admin_ops_api.py",),
        release_critical=True,
    ),
}

FLOW_ORDER: tuple[str, ...] = (
    "auth_foundation",
    "catalog_discovery",
    "cart_checkout",
    "order_management",
    "payment_integrity",
    "admin_ops",
)

CORE_ANCHOR_FLOWS: tuple[str, ...] = (
    "auth_foundation",
    "admin_ops",
    "catalog_discovery",
)

RELEASE_CRITICAL_FLOWS: tuple[str, ...] = (
    "auth_foundation",
    "catalog_discovery",
    "cart_checkout",
    "order_management",
    "payment_integrity",
    "admin_ops",
)

