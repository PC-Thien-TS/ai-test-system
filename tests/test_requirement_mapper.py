"""Tests for requirement-to-domain mapping."""

from __future__ import annotations

from orchestrator.advanced_qa.requirement_mapper import RequirementMapper
from orchestrator.advanced_qa.requirement_models import Requirement



def test_payment_requirement_maps_to_payment_domain():
    """Payment callback/retry language maps to Payment module."""

    mapper = RequirementMapper()
    requirement = Requirement(
        requirement_id="RM-MAP-001",
        title="Payment callback retry and timeout",
        description="Handle callback retry and timeout for payment confirmation.",
    )

    mapped = mapper.map_requirement(requirement)

    assert mapped.module == "Payment"
    assert "Payment" in mapped.metadata["mapped_modules"]
    assert "payment_callback_retry_timeout" in mapped.related_flows



def test_cart_order_requirement_maps_to_multiple_modules():
    """Checkout duplicate-prevention can map across Cart, Order Creation, and Payment."""

    mapper = RequirementMapper()
    requirement = Requirement(
        requirement_id="RM-MAP-002",
        title="Duplicate checkout prevention",
        description="Prevent duplicate checkout from cart and payment race condition.",
        related_flows=["cart_to_checkout"],
    )

    mapped = mapper.map_requirement(requirement)
    mapped_modules = mapped.metadata["mapped_modules"]

    assert "Cart" in mapped_modules
    assert "Order Creation" in mapped_modules
    assert "Payment" in mapped_modules



def test_multi_domain_search_flow_mapping():
    """Search and store detail requirement should map to multiple domain flows."""

    mapper = RequirementMapper()
    requirement = Requirement(
        requirement_id="RM-MAP-003",
        title="Search rewritten query behavior",
        description="Search should rewrite query and open store detail with matched menu section.",
    )

    mapped = mapper.map_requirement(requirement)

    assert "Search & Discovery" in mapped.metadata["mapped_modules"]
    assert "Store Detail & Menu" in mapped.metadata["mapped_modules"]
    assert "search_to_store_detail" in mapped.related_flows
