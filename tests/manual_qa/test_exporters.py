from __future__ import annotations

import json

from orchestrator.manual_qa.exporters import (
    export_bug_draft_to_json_file,
    export_bug_draft_to_json_string,
    export_bug_draft_to_markdown_file,
    export_bug_draft_to_markdown_string,
    export_bundle_to_json_file,
    export_bundle_to_json_string,
    export_bundle_to_markdown_file,
    export_bundle_to_markdown_string,
    export_evidence_to_json_file,
    export_evidence_to_json_string,
    export_evidence_to_markdown_file,
    export_evidence_to_markdown_string,
    export_run_to_json_file,
    export_run_to_json_string,
    export_run_to_markdown_file,
    export_run_to_markdown_string,
    export_suite_to_json_file,
    export_suite_to_json_string,
    export_suite_to_markdown_file,
    export_suite_to_markdown_string,
    export_summary_to_json_file,
    export_summary_to_json_string,
    export_summary_to_markdown_file,
    export_summary_to_markdown_string,
)
from orchestrator.manual_qa.bug_service import BugDraftService
from orchestrator.manual_qa.evidence_service import EvidenceService
from orchestrator.manual_qa.models import (
    ChecklistItem,
    ExportBundle,
    ManualTestCase,
    NormalizedRequirement,
    ProjectProfile,
)
from orchestrator.manual_qa.result_service import TestResultService
from orchestrator.manual_qa.run_service import TestRunService
from orchestrator.manual_qa.summary_service import RunSummaryService
from orchestrator.manual_qa.suite_service import TestSuiteService


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


def _build_suite_run_summary():
    suite = TestSuiteService().create_test_suite(
        project_id="checkout-web",
        name="Checkout Regression",
        test_cases=["TC-001", "TC-002"],
    )
    test_run = TestRunService().create_test_run(
        project_id="checkout-web",
        suite=suite,
        environment="staging",
        build="build-001",
        tester="qa-user",
    )
    TestResultService().update_test_result(test_run, "TC-001", "Pass")
    summary = RunSummaryService().summarize_test_run(test_run)
    return suite, test_run, summary


def _build_evidence_and_bug():
    suite = TestSuiteService().create_test_suite(
        project_id="checkout-web",
        name="Checkout Regression",
        test_cases=["TC-001"],
    )
    test_run = TestRunService().create_test_run(
        project_id="checkout-web",
        suite=suite,
        environment="staging",
        build="build-001",
        tester="qa-user",
    )
    test_case = ManualTestCase(
        test_case_id="TC-001",
        requirement_ids=["REQ-001"],
        module="Checkout",
        title="Checkout payment validation",
        steps=["Open checkout.", "Submit invalid payment details."],
        expected_result="A validation message is shown.",
    )
    TestResultService().update_test_result(
        test_run,
        "TC-001",
        "Fail",
        actual_result="No validation message was shown.",
    )
    evidence = EvidenceService().attach_evidence(
        test_run,
        "TC-001",
        "screenshot",
        "artifacts/screenshots/checkout-fail.png",
        description="Checkout failure screenshot",
        content_type="image/png",
    )
    bug = BugDraftService().generate_bug_draft(
        test_run,
        "TC-001",
        test_case=test_case,
        evidence=[evidence],
    )
    return evidence, bug


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


def test_exports_suite_run_summary_json_strings():
    suite, test_run, summary = _build_suite_run_summary()

    suite_payload = json.loads(export_suite_to_json_string(suite))
    run_payload = json.loads(export_run_to_json_string(test_run))
    summary_payload = json.loads(export_summary_to_json_string(summary))

    assert suite_payload["suite_id"] == "SUITE-001"
    assert run_payload["run_id"] == "RUN-001"
    assert summary_payload["run_id"] == "RUN-001"


def test_writes_suite_run_summary_json_files(tmp_path):
    suite, test_run, summary = _build_suite_run_summary()

    suite_path = tmp_path / "suite.json"
    run_path = tmp_path / "run.json"
    summary_path = tmp_path / "summary.json"

    export_suite_to_json_file(suite, suite_path)
    export_run_to_json_file(test_run, run_path)
    export_summary_to_json_file(summary, summary_path)

    assert json.loads(suite_path.read_text(encoding="utf-8"))["suite_id"] == "SUITE-001"
    assert json.loads(run_path.read_text(encoding="utf-8"))["results"][0]["test_case_id"] == "TC-001"
    assert json.loads(summary_path.read_text(encoding="utf-8"))["status"] == summary.status


def test_exports_suite_run_summary_markdown_strings():
    suite, test_run, summary = _build_suite_run_summary()

    suite_markdown = export_suite_to_markdown_string(suite)
    run_markdown = export_run_to_markdown_string(test_run)
    summary_markdown = export_summary_to_markdown_string(summary)

    assert "SUITE-001" in suite_markdown
    assert "RUN-001" in run_markdown
    assert "Pass Rate" in summary_markdown


def test_writes_suite_run_summary_markdown_files(tmp_path):
    suite, test_run, summary = _build_suite_run_summary()

    suite_path = tmp_path / "suite.md"
    run_path = tmp_path / "run.md"
    summary_path = tmp_path / "summary.md"

    export_suite_to_markdown_file(suite, suite_path)
    export_run_to_markdown_file(test_run, run_path)
    export_summary_to_markdown_file(summary, summary_path)

    assert "SUITE-001" in suite_path.read_text(encoding="utf-8")
    assert "RUN-001" in run_path.read_text(encoding="utf-8")
    assert "Pass Rate" in summary_path.read_text(encoding="utf-8")


def test_exports_evidence_and_bug_draft_json_strings():
    evidence, bug = _build_evidence_and_bug()

    evidence_payload = json.loads(export_evidence_to_json_string(evidence))
    bug_payload = json.loads(export_bug_draft_to_json_string(bug))

    assert evidence_payload["evidence_id"] == "EVD-001"
    assert evidence_payload["test_case_id"] == "TC-001"
    assert bug_payload["bug_id"] == "BUG-001"
    assert bug_payload["actual_result"] == "No validation message was shown."
    assert bug_payload["expected_result"] == "A validation message is shown."
    assert bug_payload["severity"] == "Major"
    assert bug_payload["priority"] == "High"
    assert bug_payload["evidence_ids"] == ["EVD-001"]


def test_writes_evidence_and_bug_draft_json_files(tmp_path):
    evidence, bug = _build_evidence_and_bug()

    evidence_path = tmp_path / "evidence.json"
    bug_path = tmp_path / "bug.json"

    export_evidence_to_json_file(evidence, evidence_path)
    export_bug_draft_to_json_file(bug, bug_path)

    assert json.loads(evidence_path.read_text(encoding="utf-8"))["evidence_id"] == "EVD-001"
    bug_payload = json.loads(bug_path.read_text(encoding="utf-8"))
    assert bug_payload["bug_id"] == "BUG-001"
    assert bug_payload["test_case_id"] == "TC-001"


def test_exports_evidence_and_bug_draft_markdown_strings():
    evidence, bug = _build_evidence_and_bug()

    evidence_markdown = export_evidence_to_markdown_string(evidence)
    bug_markdown = export_bug_draft_to_markdown_string(bug)

    assert "EVD-001" in evidence_markdown
    assert "BUG-001" in bug_markdown
    assert "TC-001" in bug_markdown
    assert "No validation message was shown." in bug_markdown
    assert "A validation message is shown." in bug_markdown
    assert "Major" in bug_markdown
    assert "High" in bug_markdown
    assert "EVD-001" in bug_markdown


def test_writes_evidence_and_bug_draft_markdown_files(tmp_path):
    evidence, bug = _build_evidence_and_bug()

    evidence_path = tmp_path / "evidence.md"
    bug_path = tmp_path / "bug.md"

    export_evidence_to_markdown_file(evidence, evidence_path)
    export_bug_draft_to_markdown_file(bug, bug_path)

    assert "EVD-001" in evidence_path.read_text(encoding="utf-8")
    bug_markdown = bug_path.read_text(encoding="utf-8")
    assert "BUG-001" in bug_markdown
    assert "TC-001" in bug_markdown
    assert "No validation message was shown." in bug_markdown
