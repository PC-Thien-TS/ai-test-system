from __future__ import annotations

from orchestrator.manual_qa.models import NormalizedRequirement
from orchestrator.manual_qa.testcase_generator import ManualTestCaseGenerator


def test_generates_positive_test_case_per_requirement():
    generator = ManualTestCaseGenerator()
    requirements = [
        NormalizedRequirement(
            requirement_id="REQ-001",
            title="Create order",
            description="User can create an order.",
            module="Ordering",
            priority="High",
            acceptance_criteria=["Order is created successfully."],
        )
    ]

    cases = generator.generate(requirements)

    assert len(cases) >= 1
    assert cases[0].test_type == "Positive"
    assert cases[0].title == "Create order - positive path"


def test_preserves_requirement_id_and_default_status():
    generator = ManualTestCaseGenerator()
    requirement = NormalizedRequirement(
        requirement_id="REQ-020",
        title="Update address",
        description="Customer can update an address.",
        module="Profile",
    )

    case = generator.generate([requirement])[0]

    assert case.requirement_ids == ["REQ-020"]
    assert case.status == "Not Run"


def test_generates_negative_validation_case_when_hints_are_present():
    generator = ManualTestCaseGenerator()
    requirement = NormalizedRequirement(
        requirement_id="REQ-030",
        title="Admin permission validation",
        description="Unauthorized users receive an error for missing permission.",
        module="Admin",
        acceptance_criteria=["Show a validation error when required fields are missing."],
    )

    cases = generator.generate([requirement])

    assert len(cases) == 2
    assert cases[0].test_case_id == "TC-001"
    assert cases[1].test_case_id == "TC-002"
    assert cases[1].test_type == "Negative"
