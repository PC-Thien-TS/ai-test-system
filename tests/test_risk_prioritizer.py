"""Tests for deterministic risk prioritization and execution queue contracts."""

from __future__ import annotations

from pathlib import Path

import yaml

from orchestrator.advanced_qa.requirement_generator import RequirementAwareGenerator
from orchestrator.advanced_qa.risk_prioritizer import RiskPrioritizer
from orchestrator.advanced_qa.risk_rules import map_score_to_priority_level


FIXTURE_DIR = Path(__file__).parent / "shared" / "fixtures"


def _load_rankmate_fixture() -> dict:
    return yaml.safe_load((FIXTURE_DIR / "rankmate_requirements.yaml").read_text(encoding="utf-8"))


def _generate_and_prioritize(payload: dict):
    generator = RequirementAwareGenerator()
    prioritizer = RiskPrioritizer()
    generation_result = generator.generate(payload)
    return generation_result, prioritizer.prioritize(generation_result)


def _find_item(result, source_type: str, source_id: str):
    for item in result.execution_queue.items:
        if item.source_type == source_type and item.source_id == source_id:
            return item
    raise AssertionError(f"Prioritized item not found: source_type={source_type} source_id={source_id}")


def test_priority_scoring_payment_order_auth_higher_than_informational():
    """Payment/order/auth flows must score above low-risk informational items."""

    payload = {
        "requirements": [
            {
                "id": "RM-HIGH-001",
                "title": "Payment callback retry timeout",
                "description": "Payment callback retries on timeout and protects order state.",
                "module": "Payment",
                "source_type": "api_contract",
                "acceptance_criteria": ["Callback retry succeeds or flags pending review."],
                "business_rules": ["Duplicate callback id must be ignored."],
                "roles": ["system"],
                "dependencies": ["Order Creation"],
                "priority": "p0",
                "risk_hints": ["callback", "timeout", "retry"],
                "related_flows": ["payment_callback_retry_timeout"],
                "changed_area": True,
            },
            {
                "id": "RM-LOW-001",
                "title": "Informational email footer copy update",
                "description": "Update static informational footer text.",
                "module": "Notifications",
                "source_type": "prd",
                "acceptance_criteria": ["Footer text displays updated copy."],
                "roles": ["admin"],
                "priority": "p3",
            },
        ]
    }

    _, prioritized = _generate_and_prioritize(payload)

    high_case = _find_item(prioritized, "test_case", "TC-RM-HIGH-001-POS")
    low_case = _find_item(prioritized, "test_case", "TC-RM-LOW-001-POS")

    assert high_case.priority_score > low_case.priority_score
    assert high_case.priority_level.value in {"critical", "high"}
    assert low_case.priority_level.value in {"low", "medium"}


def test_changed_area_and_coverage_gap_raise_priority_score():
    """Changed-area requirements and linked coverage gaps should raise execution score."""

    payload = {
        "requirements": [
            {
                "id": "RM-BASE-001",
                "title": "Create order from checkout",
                "description": "Checkout creates a single order.",
                "module": "Order Creation",
                "source_type": "srs",
                "acceptance_criteria": ["One checkout action creates one order."],
                "roles": ["user"],
                "dependencies": ["Cart", "Payment"],
                "priority": "p1",
                "related_flows": ["checkout_create_order"],
                "changed_area": False,
            },
            {
                "id": "RM-DELTA-001",
                "title": "Create order from checkout changed area",
                "description": "Checkout duplicate submit prevention after recent changes.",
                "module": "Order Creation",
                "source_type": "srs",
                "roles": ["user"],
                "priority": "p1",
                "related_flows": ["checkout_create_order"],
                "risk_hints": ["duplicate", "race"],
                "changed_area": True,
            },
        ]
    }

    _, prioritized = _generate_and_prioritize(payload)

    baseline_case = _find_item(prioritized, "test_case", "TC-RM-BASE-001-POS")
    changed_case = _find_item(prioritized, "test_case", "TC-RM-DELTA-001-POS")

    assert changed_case.priority_score > baseline_case.priority_score

    changed_gap_items = [
        item
        for item in prioritized.execution_queue.items
        if item.source_type == "coverage_gap" and "RM-DELTA-001" in item.related_requirement_ids
    ]
    assert changed_gap_items
    assert any(item.priority_level.value in {"critical", "high", "medium"} for item in changed_gap_items)


def test_priority_level_threshold_mapping_is_stable():
    """Score thresholds should map consistently to CRITICAL/HIGH/MEDIUM/LOW."""

    assert map_score_to_priority_level(1.10).value == "critical"
    assert map_score_to_priority_level(0.83).value == "high"
    assert map_score_to_priority_level(0.55).value == "medium"
    assert map_score_to_priority_level(0.20).value == "low"


def test_execution_depth_recommendations_match_rankmate_patterns():
    """Depth recommendations should reflect callback/state/permission complexity."""

    _, prioritized = _generate_and_prioritize(_load_rankmate_fixture())

    payment_case = _find_item(prioritized, "test_case", "TC-RM-REQ-005-POS")
    invalid_state_case = _find_item(prioritized, "test_case", "TC-RM-REQ-010-STATE")

    assert payment_case.execution_depth.depth.value == "deep"
    assert invalid_state_case.execution_depth.depth.value == "deep"

    login_payload = {
        "requirements": [
            {
                "id": "RM-LOGIN-001",
                "title": "User login happy path smoke",
                "description": "Verified user logs in successfully.",
                "module": "Auth & Account",
                "source_type": "prd",
                "acceptance_criteria": ["Login returns success and session token."],
                "roles": ["user"],
                "priority": "p2",
                "related_flows": ["login_register_verify"],
            }
        ]
    }
    _, login_prioritized = _generate_and_prioritize(login_payload)
    login_case = _find_item(login_prioritized, "test_case", "TC-RM-LOGIN-001-POS")
    assert login_case.execution_depth.depth.value in {"basic", "standard"}

    permission_payload = {
        "requirements": [
            {
                "id": "RM-PERM-001",
                "title": "Permission weirdness guard for admin-only endpoint",
                "description": "Prevent user role from accessing admin order mutation endpoint.",
                "module": "Permission / Security",
                "source_type": "srs",
                "acceptance_criteria": ["Unauthorized role receives denied response."],
                "roles": ["user", "admin"],
                "priority": "p1",
                "risk_hints": ["permission"],
                "related_flows": ["admin_tracking"],
            }
        ]
    }
    _, perm_prioritized = _generate_and_prioritize(permission_payload)
    perm_case = _find_item(perm_prioritized, "test_case", "TC-RM-PERM-001-POS")
    assert perm_case.execution_depth.depth.value in {"standard", "deep"}


def test_blast_radius_hints_cover_wide_medium_narrow_cases():
    """Blast radius should separate critical flow impact from localized items."""

    _, prioritized = _generate_and_prioritize(_load_rankmate_fixture())
    payment_case = _find_item(prioritized, "test_case", "TC-RM-REQ-005-POS")
    assert payment_case.blast_radius.level.value == "wide"

    merchant_payload = {
        "requirements": [
            {
                "id": "RM-MER-001",
                "title": "Merchant dashboard filter display issue",
                "description": "Merchant-only list filter display alignment issue.",
                "module": "Merchant Operations",
                "source_type": "workflow",
                "acceptance_criteria": ["Filter list renders correctly for merchant role."],
                "roles": ["merchant"],
                "priority": "p2",
            }
        ]
    }
    _, merchant_prioritized = _generate_and_prioritize(merchant_payload)
    merchant_case = _find_item(merchant_prioritized, "test_case", "TC-RM-MER-001-POS")
    assert merchant_case.blast_radius.level.value == "medium"

    info_payload = {
        "requirements": [
            {
                "id": "RM-INFO-001",
                "title": "Informational banner copy update",
                "description": "Change static informational message on help screen.",
                "module": "Notifications",
                "source_type": "prd",
                "acceptance_criteria": ["Banner shows updated text."],
                "roles": ["admin"],
                "priority": "p3",
            }
        ]
    }
    _, info_prioritized = _generate_and_prioritize(info_payload)
    info_case = _find_item(info_prioritized, "test_case", "TC-RM-INFO-001-POS")
    assert info_case.blast_radius.level.value == "narrow"


def test_execution_queue_ordering_is_deterministic_and_relationships_preserved():
    """Queue ordering must be deterministic with stable tie-break and linked requirements."""

    _, first = _generate_and_prioritize(_load_rankmate_fixture())
    _, second = _generate_and_prioritize(_load_rankmate_fixture())

    first_ids = [item.item_id for item in first.execution_queue.items]
    second_ids = [item.item_id for item in second.execution_queue.items]

    assert first_ids == second_ids
    assert first.execution_queue.items[0].priority_score >= first.execution_queue.items[1].priority_score
    assert first.execution_queue.items[0].priority_level.value in {"critical", "high"}
    assert first.execution_queue.items[0].related_requirement_ids


def test_exploratory_follow_up_tagging_for_race_callback_state_and_permission():
    """Callback/duplicate/state/permission-sensitive items should be flagged for exploratory follow-up."""

    _, prioritized = _generate_and_prioritize(_load_rankmate_fixture())

    assert any(
        item.exploratory_follow_up
        for item in prioritized.execution_queue.items
        if "RM-REQ-005" in item.related_requirement_ids
    )
    assert any(
        item.exploratory_follow_up
        for item in prioritized.execution_queue.items
        if "RM-REQ-009" in item.related_requirement_ids
    )
    assert any(
        item.exploratory_follow_up
        for item in prioritized.execution_queue.items
        if "RM-REQ-010" in item.related_requirement_ids
    )

    permission_payload = {
        "requirements": [
            {
                "id": "RM-PERM-002",
                "title": "Permission weirdness around admin-only transition",
                "description": "User and merchant cannot execute admin transition endpoint.",
                "module": "Permission / Security",
                "source_type": "srs",
                "acceptance_criteria": ["Unauthorized transition attempt is rejected with audit trail."],
                "roles": ["user", "merchant", "admin"],
                "priority": "p1",
                "risk_hints": ["permission", "state transition"],
                "related_flows": ["admin_tracking", "cancellation_invalid_state_transition"],
                "changed_area": True,
            }
        ]
    }
    _, perm_prioritized = _generate_and_prioritize(permission_payload)

    perm_items = [
        item
        for item in perm_prioritized.execution_queue.items
        if "RM-PERM-002" in item.related_requirement_ids
    ]
    assert perm_items
    assert any(item.exploratory_follow_up for item in perm_items)
    assert any("exploratory_follow_up" in item.tags for item in perm_items)
