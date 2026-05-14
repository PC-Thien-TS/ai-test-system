from __future__ import annotations

import json

from orchestrator.manual_qa.exporters import (
    export_bundle_to_json_file,
    export_bundle_to_json_string,
    export_bundle_to_markdown_file,
    export_bundle_to_markdown_string,
)
from orchestrator.manual_qa.models import (
    ChecklistItem,
    ExportBundle,
    ManualTestCase,
    NormalizedRequirement,
    ProjectProfile,
)


def _build_bundle() -> ExportBundle:
    project = ProjectProfile(
        project_id="checkout-web",
        name="Checkout Web",
        product_type="web",
        owner="manual-qa",
    )
    requirements = [
        NormalizedRequirement(
            requirement_id="REQ-001",
            title="Checkout payment",
            description="Customer completes checkout payment.",
            module="Checkout",
            priority="High",
        )
    ]
    checklist_items = [
        ChecklistItem(
            checklist_id="CHK-001",
            requirement_id="REQ-001",
            module="Checkout",
            title="Verify checkout payment",
            description="Confirm checkout payment can be completed.",
            priority="High",
        )
    ]
    test_cases = [
        ManualTestCase(
            test_case_id="TC-001",
            requirement_ids=["REQ-001"],
            module="Checkout",
            title="Checkout payment - positive path",
            preconditions=["Customer has items in cart."],
            steps=["Open checkout.", "Submit payment."],
            expected_result="Payment is accepted.",
            priority="High",
        )
    ]
    return ExportBundle(
        project=project,
        requirements=requirements,
        checklist_items=checklist_items,
        test_cases=test_cases,
    )


def test_exports_json_string():
    bundle = _build_bundle()

    exported = export_bundle_to_json_string(bundle)
    payload = json.loads(exported)

    assert payload["requirements"][0]["requirement_id"] == "REQ-001"
    assert payload["test_cases"][0]["test_case_id"] == "TC-001"


def test_writes_json_file(tmp_path):
    bundle = _build_bundle()
    output_path = tmp_path / "manual_qa.json"

    written = export_bundle_to_json_file(bundle, output_path)

    assert written == output_path
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["checklist_items"][0]["checklist_id"] == "CHK-001"


def test_exports_markdown_string():
    bundle = _build_bundle()

    exported = export_bundle_to_markdown_string(bundle)

    assert "REQ-001" in exported
    assert "TC-001" in exported
    assert "## Checklist" in exported


def test_writes_markdown_file(tmp_path):
    bundle = _build_bundle()
    output_path = tmp_path / "manual_qa.md"

    written = export_bundle_to_markdown_file(bundle, output_path)

    assert written == output_path
    exported = output_path.read_text(encoding="utf-8")
    assert "REQ-001" in exported
    assert "TC-001" in exported
