from __future__ import annotations

from orchestrator.manual_qa.checklist_generator import ChecklistGenerator
from orchestrator.manual_qa.models import NormalizedRequirement


def test_generates_checklist_items():
    generator = ChecklistGenerator()
    requirements = [
        NormalizedRequirement(
            requirement_id="REQ-001",
            title="User login",
            description="User can sign in.",
            module="Auth",
            priority="High",
            acceptance_criteria=["Dashboard is shown."],
        ),
        NormalizedRequirement(
            requirement_id="REQ-002",
            title="Profile update",
            description="User can update profile data.",
        ),
    ]

    items = generator.generate(requirements)

    assert len(items) == 2
    assert items[0].title == "Verify User login"
    assert items[1].title == "Verify Profile update"


def test_preserves_requirement_id_and_defaults_checked_false():
    generator = ChecklistGenerator()
    requirement = NormalizedRequirement(
        requirement_id="REQ-010",
        title="Permission guard",
        description="Restricted users are blocked.",
        module="Admin",
        priority="Medium",
    )

    item = generator.generate([requirement])[0]

    assert item.requirement_id == "REQ-010"
    assert item.checked is False


def test_checklist_ids_are_stable():
    generator = ChecklistGenerator()
    requirements = [
        NormalizedRequirement(requirement_id="REQ-001", title="A", description="A"),
        NormalizedRequirement(requirement_id="REQ-002", title="B", description="B"),
    ]

    first = [item.checklist_id for item in generator.generate(requirements)]
    second = [item.checklist_id for item in generator.generate(requirements)]

    assert first == ["CHK-001", "CHK-002"]
    assert second == first
