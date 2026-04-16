"""Tests for requirement-aware generation pipeline outputs."""

from __future__ import annotations

from pathlib import Path

import yaml

from orchestrator.advanced_qa.requirement_generator import RequirementAwareGenerator
from orchestrator.advanced_qa.requirement_models import Requirement
from orchestrator.advanced_qa.requirement_outputs import RequirementOutputBuilder


FIXTURE_DIR = Path(__file__).parent / "shared" / "fixtures"



def _load_rankmate_requirements_payload() -> dict:
    return yaml.safe_load((FIXTURE_DIR / "rankmate_requirements.yaml").read_text(encoding="utf-8"))



def test_requirement_aware_generator_produces_rankmate_artifacts():
    """Critical RankMate requirements should produce smoke/regression and permission plans."""

    generator = RequirementAwareGenerator()
    result = generator.generate(_load_rankmate_requirements_payload())

    assert len(result.requirements) == 10
    assert len(result.test_plans) > 0
    assert len(result.test_cases) >= 20

    buckets = {plan.bucket.value for plan in result.test_plans}
    assert "smoke" in buckets
    assert "regression" in buckets
    assert "permission" in buckets
    assert "edge_case" in buckets
    assert "high_risk" in buckets



def test_generated_test_cases_are_deterministic_and_complete():
    """Generator outputs deterministic test cases with required contract fields."""

    generator = RequirementAwareGenerator()
    first = generator.generate(_load_rankmate_requirements_payload())
    second = generator.generate(_load_rankmate_requirements_payload())

    first_cases = [case.to_dict() for case in first.test_cases]
    second_cases = [case.to_dict() for case in second.test_cases]

    assert first_cases == second_cases

    sample_case = first_cases[0]
    assert sample_case["id"]
    assert sample_case["title"]
    assert sample_case["module"]
    assert sample_case["scenario_type"]
    assert sample_case["preconditions"]
    assert sample_case["steps"]
    assert sample_case["expected_result"]
    assert sample_case["related_requirement_ids"]



def test_coverage_gap_detection_flags_missing_acceptance_and_roles():
    """Coverage gaps should include missing acceptance criteria and role coverage."""

    output_builder = RequirementOutputBuilder()

    requirements = [
        Requirement(
            requirement_id="RM-GAP-001",
            title="Payment callback timeout fallback",
            description="Payment callback timeout should trigger safe fallback and retry.",
            module="Payment",
            priority="p0",
            related_flows=["payment_callback_retry_timeout"],
            risk_hints=["timeout", "retry"],
            # intentionally missing acceptance_criteria, roles, dependencies
        )
    ]

    risk_maps = output_builder.generate_risk_maps(requirements)
    test_cases = output_builder.generate_test_cases(requirements, risk_maps)
    gaps = output_builder.detect_coverage_gaps(requirements, test_cases)

    gap_types = {gap.gap_type for gap in gaps}
    assert "missing_acceptance_criteria" in gap_types
    assert "missing_role_coverage" in gap_types
    assert "missing_flow_dependency" in gap_types



def test_risk_map_generation_distinguishes_high_and_low_risk_requirements():
    """Payment/order/auth risks should be elevated while informational content stays low."""

    output_builder = RequirementOutputBuilder()

    requirements = [
        Requirement(
            requirement_id="RM-RISK-001",
            title="Payment callback retry timeout",
            description="Payment callback should retry and handle timeout safely.",
            module="Payment",
            roles=["system", "merchant"],
            priority="p0",
            changed_area=True,
            risk_hints=["callback", "timeout"],
        ),
        Requirement(
            requirement_id="RM-RISK-002",
            title="Update informational footer copy",
            description="Update static legal text on info page.",
            module="Notifications",
            roles=["admin"],
            priority="p3",
        ),
    ]

    risk_maps = output_builder.generate_risk_maps(requirements)
    risk_by_id = {item.requirement_id: item for item in risk_maps}

    assert risk_by_id["RM-RISK-001"].risk_level.value in {"high", "critical"}
    assert risk_by_id["RM-RISK-001"].risk_score > risk_by_id["RM-RISK-002"].risk_score
    assert risk_by_id["RM-RISK-002"].risk_level.value in {"low", "medium"}
