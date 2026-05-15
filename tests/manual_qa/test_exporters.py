from __future__ import annotations

import json

from orchestrator.manual_qa.automation_candidate_service import AutomationCandidateService
from orchestrator.manual_qa.api_script_generator import APITestScriptGenerator
from orchestrator.manual_qa.api_script_packaging_service import APIScriptPackagingService
from orchestrator.manual_qa.api_script_validation_service import APIScriptValidationService
from orchestrator.manual_qa.exporters import (
    export_api_execution_evidence_list_to_json_file,
    export_api_execution_evidence_list_to_json_string,
    export_api_execution_evidence_list_to_markdown_file,
    export_api_execution_evidence_list_to_markdown_string,
    export_api_execution_history_entries_to_json_file,
    export_api_execution_history_entries_to_json_string,
    export_api_execution_history_entries_to_markdown_file,
    export_api_execution_history_entries_to_markdown_string,
    export_api_execution_history_entry_to_json_file,
    export_api_execution_history_entry_to_json_string,
    export_api_execution_history_entry_to_markdown_file,
    export_api_execution_history_entry_to_markdown_string,
    export_api_execution_history_report_to_markdown_string,
    export_api_execution_evidence_report_to_markdown_string,
    export_api_execution_evidence_to_json_file,
    export_api_execution_evidence_to_json_string,
    export_api_execution_evidence_to_markdown_file,
    export_api_execution_evidence_to_markdown_string,
    export_api_execution_request_to_json_file,
    export_api_execution_request_to_json_string,
    export_api_execution_request_to_markdown_file,
    export_api_execution_request_to_markdown_string,
    export_api_execution_result_to_json_file,
    export_api_execution_result_to_json_string,
    export_api_execution_result_to_markdown_file,
    export_api_execution_result_to_markdown_string,
    export_api_execution_results_to_json_file,
    export_api_execution_results_to_json_string,
    export_api_execution_results_to_markdown_file,
    export_api_execution_results_to_markdown_string,
    export_api_execution_summary_to_json_file,
    export_api_execution_summary_to_json_string,
    export_api_execution_summary_to_markdown_file,
    export_api_execution_summary_to_markdown_string,
    export_api_execution_trend_summary_to_json_file,
    export_api_execution_trend_summary_to_json_string,
    export_api_execution_trend_summary_to_markdown_file,
    export_api_execution_trend_summary_to_markdown_string,
    export_automation_candidate_to_json_file,
    export_automation_candidate_to_json_string,
    export_automation_candidate_to_markdown_file,
    export_automation_candidate_to_markdown_string,
    export_automation_candidates_to_json_file,
    export_automation_candidates_to_json_string,
    export_automation_candidates_to_markdown_file,
    export_automation_candidates_to_markdown_string,
    export_api_script_draft_to_json_file,
    export_api_script_draft_to_json_string,
    export_api_script_draft_to_markdown_file,
    export_api_script_draft_to_markdown_string,
    export_api_script_draft_to_python_file,
    export_api_script_drafts_to_json_file,
    export_api_script_drafts_to_json_string,
    export_api_script_drafts_to_markdown_file,
    export_api_script_drafts_to_markdown_string,
    export_api_script_package_manifest_to_json_file,
    export_api_script_package_manifest_to_json_string,
    export_api_script_package_manifest_to_markdown_file,
    export_api_script_package_manifest_to_markdown_string,
    export_api_script_validation_result_to_json_file,
    export_api_script_validation_result_to_json_string,
    export_api_script_validation_result_to_markdown_file,
    export_api_script_validation_result_to_markdown_string,
    export_api_script_validation_results_to_json_file,
    export_api_script_validation_results_to_json_string,
    export_api_script_validation_results_to_markdown_file,
    export_api_script_validation_results_to_markdown_string,
    export_bug_draft_to_json_file,
    export_bug_draft_to_json_string,
    export_bug_draft_to_markdown_file,
    export_bug_draft_to_markdown_string,
    export_bundle_to_json_file,
    export_bundle_to_json_string,
    export_bundle_to_markdown_file,
    export_bundle_to_markdown_string,
    export_draft_package_group_summary_to_json_file,
    export_draft_package_group_summary_to_json_string,
    export_draft_package_group_summary_to_markdown_file,
    export_draft_package_group_summary_to_markdown_string,
    export_evidence_to_json_file,
    export_evidence_to_json_string,
    export_evidence_to_markdown_file,
    export_evidence_to_markdown_string,
    export_execution_plan_to_json_file,
    export_execution_plan_to_json_string,
    export_execution_plan_to_markdown_file,
    export_execution_plan_to_markdown_string,
    export_execution_preflight_result_to_json_file,
    export_execution_preflight_result_to_json_string,
    export_execution_preflight_result_to_markdown_file,
    export_execution_preflight_result_to_markdown_string,
    export_execution_safety_policy_to_json_file,
    export_execution_safety_policy_to_json_string,
    export_execution_safety_policy_to_markdown_file,
    export_execution_safety_policy_to_markdown_string,
    export_failure_record_to_json_file,
    export_failure_record_to_json_string,
    export_failure_record_to_markdown_file,
    export_failure_record_to_markdown_string,
    export_failure_records_to_json_file,
    export_failure_records_to_json_string,
    export_failure_records_to_markdown_file,
    export_failure_records_to_markdown_string,
    export_failure_signature_to_json_file,
    export_failure_signature_to_json_string,
    export_failure_signature_to_markdown_file,
    export_failure_signature_to_markdown_string,
    export_run_to_json_file,
    export_run_to_json_string,
    export_run_to_markdown_file,
    export_run_to_markdown_string,
    export_script_readiness_list_to_json_file,
    export_script_readiness_list_to_json_string,
    export_script_readiness_list_to_markdown_file,
    export_script_readiness_list_to_markdown_string,
    export_script_readiness_to_json_file,
    export_script_readiness_to_json_string,
    export_script_readiness_to_markdown_file,
    export_script_readiness_to_markdown_string,
    export_suite_to_json_file,
    export_suite_to_json_string,
    export_suite_to_markdown_file,
    export_suite_to_markdown_string,
    export_summary_to_json_file,
    export_summary_to_json_string,
    export_summary_to_markdown_file,
    export_summary_to_markdown_string,
    export_unified_draft_package_summary_to_json_file,
    export_unified_draft_package_summary_to_json_string,
    export_unified_draft_package_summary_to_markdown_file,
    export_unified_draft_package_summary_to_markdown_string,
    export_web_playwright_readiness_list_to_json_file,
    export_web_playwright_readiness_list_to_json_string,
    export_web_playwright_readiness_list_to_markdown_file,
    export_web_playwright_readiness_list_to_markdown_string,
    export_web_playwright_readiness_to_json_file,
    export_web_playwright_readiness_to_json_string,
    export_web_playwright_readiness_to_markdown_file,
    export_web_playwright_readiness_to_markdown_string,
    export_web_playwright_script_draft_to_json_file,
    export_web_playwright_script_draft_to_json_string,
    export_web_playwright_script_draft_to_markdown_file,
    export_web_playwright_script_draft_to_markdown_string,
    export_web_playwright_script_draft_to_python_file,
    export_web_playwright_script_drafts_to_json_file,
    export_web_playwright_script_drafts_to_json_string,
    export_web_playwright_script_drafts_to_markdown_file,
    export_web_playwright_script_drafts_to_markdown_string,
    export_web_playwright_validation_result_to_json_file,
    export_web_playwright_validation_result_to_json_string,
    export_web_playwright_validation_result_to_markdown_file,
    export_web_playwright_validation_result_to_markdown_string,
    export_web_playwright_validation_results_to_json_file,
    export_web_playwright_validation_results_to_json_string,
    export_web_playwright_validation_results_to_markdown_file,
    export_web_playwright_validation_results_to_markdown_string,
    export_web_playwright_package_manifest_to_json_file,
    export_web_playwright_package_manifest_to_json_string,
    export_web_playwright_package_manifest_to_markdown_file,
    export_web_playwright_package_manifest_to_markdown_string,
)
from orchestrator.manual_qa.bug_service import BugDraftService
from orchestrator.manual_qa.evidence_service import EvidenceService
from orchestrator.manual_qa.failure_memory_service import FailureMemoryService
from orchestrator.manual_qa.models import (
    APIExecutionEvidence,
    APIExecutionHistoryEntry,
    APIExecutionLogEntry,
    APIExecutionRequest,
    APIExecutionResult,
    APIExecutionSummary,
    APIExecutionTrendSummary,
    ChecklistItem,
    DraftPackageGroupSummary,
    ExecutionPlan,
    ExecutionPreflightIssue,
    ExecutionPreflightResult,
    ExecutionSafetyPolicy,
    ExecutionTarget,
    ExportBundle,
    ManualTestCase,
    NormalizedRequirement,
    ProjectProfile,
    UnifiedDraftPackageSummary,
)
from orchestrator.manual_qa.result_service import TestResultService
from orchestrator.manual_qa.run_service import TestRunService
from orchestrator.manual_qa.script_readiness_service import ScriptReadinessService
from orchestrator.manual_qa.summary_service import RunSummaryService
from orchestrator.manual_qa.suite_service import TestSuiteService
from orchestrator.manual_qa.web_playwright_packaging_service import WebPlaywrightPackagingService
from orchestrator.manual_qa.web_playwright_readiness_service import WebPlaywrightReadinessService
from orchestrator.manual_qa.web_playwright_script_generator import WebPlaywrightScriptGenerator
from orchestrator.manual_qa.web_playwright_validation_service import WebPlaywrightValidationService


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


def _build_failure_signature_and_record():
    service = FailureMemoryService()
    signature = service.create_failure_signature(
        module="Checkout",
        test_case_id="TC-001",
        title="Checkout validation failure",
        symptom="Validation message missing",
        expected_result="A validation message is shown.",
        actual_result="The request succeeded without validation.",
        environment="staging",
        build="build-001",
        severity="Major",
        priority="High",
        source_bug_id="BUG-001",
        metadata={"run_id": "RUN-001"},
    )
    record = service.remember_failure(signature)
    return signature, record, [record]


def _build_automation_candidate_and_list():
    service = AutomationCandidateService()
    primary = service.score_automation_candidate(
        ManualTestCase(
            test_case_id="TC-010",
            requirement_ids=["REQ-010"],
            module="Order API",
            title="Regression API order create flow",
            steps=["Send create order request.", "Inspect response."],
            expected_result="Response status code is 200 and order is created.",
            priority="High",
            test_type="Regression",
        )
    )
    secondary = service.score_automation_candidate(
        ManualTestCase(
            test_case_id="TC-011",
            requirement_ids=["REQ-011"],
            module="Checkout",
            title="Visual only checkout appearance review looks good",
            steps=["Open checkout page.", "Review manually."],
            expected_result="Looks good to tester.",
            priority="Medium",
            test_type="Usability",
        )
    )
    return primary, [primary, secondary]


def _build_script_readiness_items():
    service = ScriptReadinessService()
    primary = service.analyze_script_readiness(
        ManualTestCase(
            test_case_id="TC-100",
            requirement_ids=["REQ-100"],
            module="Order API",
            title="Create order endpoint returns status code 201",
            steps=["Send POST request to /api/orders with valid payload.", "Verify response status code is 201."],
            expected_result="Response status code is 201 and order is created.",
            priority="High",
            metadata={"test_data": "valid order payload"},
        )
    )
    secondary = service.analyze_script_readiness(
        ManualTestCase(
            test_case_id="TC-101",
            requirement_ids=["REQ-101"],
            module="Checkout UI",
            title="Visual only checkout review looks good",
            steps=["Open checkout page and review manually."],
            expected_result="Looks good to the tester.",
        )
    )
    return primary, [primary, secondary]


def _build_api_script_drafts():
    readiness_service = ScriptReadinessService()
    generator = APITestScriptGenerator()
    cases = [
        ManualTestCase(
            test_case_id="TC-200",
            requirement_ids=["REQ-200"],
            module="Order API",
            title="Create order endpoint returns status code 201",
            steps=["Send POST request to /api/orders with valid payload.", "Verify response status code is 201."],
            expected_result="Response status code is 201 and order is created.",
            metadata={"test_data": {"sku": "ABC-001"}},
        ),
        ManualTestCase(
            test_case_id="TC-201",
            requirement_ids=["REQ-201"],
            module="User API",
            title="Get user endpoint returns status code 200",
            steps=["Send GET request to /api/users/1.", "Verify response status code is 200."],
            expected_result="Response status code is 200 and user details are returned.",
        ),
    ]
    readiness_items = readiness_service.analyze_script_readiness_batch(cases)
    drafts = generator.generate_api_script_drafts(cases, readiness_items=readiness_items)
    return drafts[0], drafts


def _build_api_script_validation_and_package():
    _draft, drafts = _build_api_script_drafts()
    validation_service = APIScriptValidationService()
    packaging_service = APIScriptPackagingService()
    validation_results = validation_service.validate_api_script_drafts(drafts)
    manifest = packaging_service.build_api_script_package(
        drafts,
        validation_results,
        validation_report_files=["script_drafts/api/api_script_validation.json"],
    )
    return validation_results[0], validation_results, manifest


def _build_web_playwright_readiness_items():
    service = WebPlaywrightReadinessService()
    primary = service.analyze_web_playwright_readiness(
        ManualTestCase(
            test_case_id="TC-300",
            requirement_ids=["REQ-300"],
            module="Portal UI",
            title="Login page submit flow",
            steps=[
                "Navigate to /login page.",
                "Fill data-testid=login-email with valid email.",
                "Fill data-testid=login-password with valid password.",
                "Click button text sign in.",
            ],
            expected_result="User should see dashboard and URL contains /dashboard.",
        )
    )
    secondary = service.analyze_web_playwright_readiness(
        ManualTestCase(
            test_case_id="TC-301",
            requirement_ids=["REQ-301"],
            module="Portal UI",
            title="Visual review looks good",
            steps=["Open /homepage and review manually."],
            expected_result="Looks good visually.",
        )
    )
    return primary, [primary, secondary]


def _build_web_playwright_script_drafts():
    readiness_service = WebPlaywrightReadinessService()
    generator = WebPlaywrightScriptGenerator()
    cases = [
        ManualTestCase(
            test_case_id="TC-400",
            requirement_ids=["REQ-400"],
            module="Portal UI",
            title="Login page submit flow",
            steps=[
                "Navigate to /login page.",
                "Fill data-testid=login-email with valid email.",
                "Fill data-testid=login-password with valid password.",
                "Click button text sign in.",
            ],
            expected_result="User should see dashboard and URL contains /dashboard.",
        ),
        ManualTestCase(
            test_case_id="TC-401",
            requirement_ids=["REQ-401"],
            module="Portal UI",
            title="Search page filter flow",
            steps=[
                "Navigate to /search page.",
                "Fill field label Search with valid text.",
                "Click button text search.",
            ],
            expected_result="User should see results and URL contains /search.",
        ),
    ]
    readiness_items = readiness_service.analyze_web_playwright_readiness_batch(cases)
    drafts = generator.generate_web_playwright_script_drafts(cases, readiness_items=readiness_items)
    return drafts[0], drafts


def _build_web_playwright_validation_and_package():
    _draft, drafts = _build_web_playwright_script_drafts()
    validation_service = WebPlaywrightValidationService()
    packaging_service = WebPlaywrightPackagingService()
    validation_results = validation_service.validate_web_playwright_script_drafts(drafts)
    manifest = packaging_service.build_web_playwright_package(
        drafts,
        validation_results,
        validation_report_files=["script_drafts/web_playwright/web_playwright_validation.json"],
    )
    return validation_results[0], validation_results, manifest


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


def test_exports_failure_signature_record_and_record_list_json_strings():
    signature, record, records = _build_failure_signature_and_record()

    signature_payload = json.loads(export_failure_signature_to_json_string(signature))
    record_payload = json.loads(export_failure_record_to_json_string(record))
    records_payload = json.loads(export_failure_records_to_json_string(records))

    assert signature_payload["signature_id"] == "FSIG-001"
    assert signature_payload["fingerprint"].startswith("FP-")
    assert record_payload["record_id"] == "FMEM-001"
    assert record_payload["occurrence_count"] == 1
    assert record_payload["related_bug_ids"] == ["BUG-001"]
    assert records_payload[0]["record_id"] == "FMEM-001"


def test_writes_failure_signature_record_and_record_list_json_files(tmp_path):
    signature, record, records = _build_failure_signature_and_record()

    signature_path = tmp_path / "failure_signature.json"
    record_path = tmp_path / "failure_record.json"
    records_path = tmp_path / "failure_records.json"

    export_failure_signature_to_json_file(signature, signature_path)
    export_failure_record_to_json_file(record, record_path)
    export_failure_records_to_json_file(records, records_path)

    assert json.loads(signature_path.read_text(encoding="utf-8"))["signature_id"] == "FSIG-001"
    assert json.loads(record_path.read_text(encoding="utf-8"))["occurrence_count"] == 1
    assert json.loads(records_path.read_text(encoding="utf-8"))[0]["related_bug_ids"] == ["BUG-001"]


def test_exports_failure_signature_record_and_record_list_markdown_strings():
    signature, record, records = _build_failure_signature_and_record()

    signature_markdown = export_failure_signature_to_markdown_string(signature)
    record_markdown = export_failure_record_to_markdown_string(record)
    records_markdown = export_failure_records_to_markdown_string(records)

    assert "FSIG-001" in signature_markdown
    assert signature.fingerprint in signature_markdown
    assert "FMEM-001" in record_markdown
    assert "Occurrence Count: 1" in record_markdown
    assert "BUG-001" in record_markdown
    assert "FMEM-001" in records_markdown


def test_writes_failure_signature_record_and_record_list_markdown_files(tmp_path):
    signature, record, records = _build_failure_signature_and_record()

    signature_path = tmp_path / "failure_signature.md"
    record_path = tmp_path / "failure_record.md"
    records_path = tmp_path / "failure_records.md"

    export_failure_signature_to_markdown_file(signature, signature_path)
    export_failure_record_to_markdown_file(record, record_path)
    export_failure_records_to_markdown_file(records, records_path)

    assert "FSIG-001" in signature_path.read_text(encoding="utf-8")
    record_markdown = record_path.read_text(encoding="utf-8")
    assert "FMEM-001" in record_markdown
    assert signature.fingerprint in record_markdown
    assert "BUG-001" in record_markdown
    assert "FMEM-001" in records_path.read_text(encoding="utf-8")


def test_exports_automation_candidate_and_list_json_strings():
    candidate, candidates = _build_automation_candidate_and_list()

    candidate_payload = json.loads(export_automation_candidate_to_json_string(candidate))
    candidates_payload = json.loads(export_automation_candidates_to_json_string(candidates))

    assert candidate_payload["candidate_id"] == "AUTO-001"
    assert candidate_payload["recommendation"] == "Should Automate"
    assert candidate_payload["suggested_automation_type"] == "api"
    assert isinstance(candidate_payload["reasons"], list)
    assert isinstance(candidate_payload["blockers"], list)
    assert candidates_payload[1]["candidate_id"] == "AUTO-002"


def test_writes_automation_candidate_and_list_json_files(tmp_path):
    candidate, candidates = _build_automation_candidate_and_list()

    candidate_path = tmp_path / "automation_candidate.json"
    candidates_path = tmp_path / "automation_candidates.json"

    export_automation_candidate_to_json_file(candidate, candidate_path)
    export_automation_candidates_to_json_file(candidates, candidates_path)

    assert json.loads(candidate_path.read_text(encoding="utf-8"))["candidate_id"] == "AUTO-001"
    assert json.loads(candidates_path.read_text(encoding="utf-8"))[1]["candidate_id"] == "AUTO-002"


def test_exports_automation_candidate_and_list_markdown_strings():
    candidate, candidates = _build_automation_candidate_and_list()

    candidate_markdown = export_automation_candidate_to_markdown_string(candidate)
    candidates_markdown = export_automation_candidates_to_markdown_string(candidates)

    assert "AUTO-001" in candidate_markdown
    assert "Should Automate" in candidate_markdown
    assert "api" in candidate_markdown
    assert "Reasons" in candidate_markdown
    assert "Blockers" in candidate_markdown
    assert "AUTO-002" in candidates_markdown


def test_writes_automation_candidate_and_list_markdown_files(tmp_path):
    candidate, candidates = _build_automation_candidate_and_list()

    candidate_path = tmp_path / "automation_candidate.md"
    candidates_path = tmp_path / "automation_candidates.md"

    export_automation_candidate_to_markdown_file(candidate, candidate_path)
    export_automation_candidates_to_markdown_file(candidates, candidates_path)

    candidate_markdown = candidate_path.read_text(encoding="utf-8")
    assert "AUTO-001" in candidate_markdown
    assert "Should Automate" in candidate_markdown
    candidates_markdown = candidates_path.read_text(encoding="utf-8")
    assert "AUTO-002" in candidates_markdown


def test_exports_script_readiness_and_list_json_strings():
    readiness, readiness_items = _build_script_readiness_items()

    readiness_payload = json.loads(export_script_readiness_to_json_string(readiness))
    list_payload = json.loads(export_script_readiness_list_to_json_string(readiness_items))

    assert readiness_payload["readiness_id"] == "READ-001"
    assert readiness_payload["test_case_id"] == "TC-100"
    assert "gaps" in readiness_payload
    assert list_payload[1]["readiness_id"] == "READ-002"


def test_writes_script_readiness_and_list_json_files(tmp_path):
    readiness, readiness_items = _build_script_readiness_items()

    readiness_path = tmp_path / "script_readiness.json"
    list_path = tmp_path / "script_readiness_list.json"

    export_script_readiness_to_json_file(readiness, readiness_path)
    export_script_readiness_list_to_json_file(readiness_items, list_path)

    assert json.loads(readiness_path.read_text(encoding="utf-8"))["readiness_id"] == "READ-001"
    assert json.loads(list_path.read_text(encoding="utf-8"))[1]["test_case_id"] == "TC-101"


def test_exports_script_readiness_and_list_markdown_strings():
    readiness, readiness_items = _build_script_readiness_items()

    readiness_markdown = export_script_readiness_to_markdown_string(readiness)
    list_markdown = export_script_readiness_list_to_markdown_string(readiness_items)

    assert "READ-001" in readiness_markdown
    assert "TC-100" in readiness_markdown
    assert "Readiness Score" in readiness_markdown
    assert "Suggested Next Step" in readiness_markdown
    assert "READ-002" in list_markdown


def test_writes_script_readiness_and_list_markdown_files(tmp_path):
    readiness, readiness_items = _build_script_readiness_items()

    readiness_path = tmp_path / "script_readiness.md"
    list_path = tmp_path / "script_readiness_list.md"

    export_script_readiness_to_markdown_file(readiness, readiness_path)
    export_script_readiness_list_to_markdown_file(readiness_items, list_path)

    assert "READ-001" in readiness_path.read_text(encoding="utf-8")
    assert "READ-002" in list_path.read_text(encoding="utf-8")


def test_exports_api_script_draft_and_list_json_strings():
    draft, drafts = _build_api_script_drafts()

    draft_payload = json.loads(export_api_script_draft_to_json_string(draft))
    drafts_payload = json.loads(export_api_script_drafts_to_json_string(drafts))

    assert draft_payload["draft_id"] == "API-DRAFT-001"
    assert draft_payload["test_case_id"] == "TC-200"
    assert draft_payload["status"] == "Draft"
    assert "script_content" in draft_payload
    assert drafts_payload[1]["draft_id"] == "API-DRAFT-002"


def test_writes_api_script_draft_and_list_json_files(tmp_path):
    draft, drafts = _build_api_script_drafts()

    draft_path = tmp_path / "api_script_draft.json"
    drafts_path = tmp_path / "api_script_drafts.json"

    export_api_script_draft_to_json_file(draft, draft_path)
    export_api_script_drafts_to_json_file(drafts, drafts_path)

    assert json.loads(draft_path.read_text(encoding="utf-8"))["draft_id"] == "API-DRAFT-001"
    assert json.loads(drafts_path.read_text(encoding="utf-8"))[1]["test_case_id"] == "TC-201"


def test_exports_api_script_draft_and_list_markdown_strings():
    draft, drafts = _build_api_script_drafts()

    draft_markdown = export_api_script_draft_to_markdown_string(draft)
    drafts_markdown = export_api_script_drafts_to_markdown_string(drafts)

    assert "API-DRAFT-001" in draft_markdown
    assert "TC-200" in draft_markdown
    assert "Draft" in draft_markdown
    assert "Warnings" in draft_markdown
    assert "```python" in draft_markdown
    assert "API-DRAFT-002" in drafts_markdown


def test_writes_api_script_draft_and_list_markdown_files(tmp_path):
    draft, drafts = _build_api_script_drafts()

    draft_path = tmp_path / "api_script_draft.md"
    drafts_path = tmp_path / "api_script_drafts.md"

    export_api_script_draft_to_markdown_file(draft, draft_path)
    export_api_script_drafts_to_markdown_file(drafts, drafts_path)

    assert "API-DRAFT-001" in draft_path.read_text(encoding="utf-8")
    assert "API-DRAFT-002" in drafts_path.read_text(encoding="utf-8")


def test_writes_api_script_draft_python_file(tmp_path):
    draft, _drafts = _build_api_script_drafts()
    output_path = tmp_path / draft.file_name

    written = export_api_script_draft_to_python_file(draft, output_path)

    assert written == output_path
    content = output_path.read_text(encoding="utf-8")
    assert "requests.post" in content or "requests.get" in content
    assert "Draft only. Not executed / not verified." in content


def test_exports_api_script_validation_result_and_list_json_strings():
    result, results, manifest = _build_api_script_validation_and_package()

    result_payload = json.loads(export_api_script_validation_result_to_json_string(result))
    results_payload = json.loads(export_api_script_validation_results_to_json_string(results))
    manifest_payload = json.loads(export_api_script_package_manifest_to_json_string(manifest))

    assert result_payload["validation_id"] == "APIVAL-001"
    assert result_payload["draft_id"] == "API-DRAFT-001"
    assert "issues" in result_payload
    assert results_payload[1]["validation_id"] == "APIVAL-002"
    assert manifest_payload["package_id"] == "APIPKG-001"


def test_writes_api_script_validation_result_and_list_json_files(tmp_path):
    result, results, manifest = _build_api_script_validation_and_package()

    result_path = tmp_path / "api_script_validation_result.json"
    results_path = tmp_path / "api_script_validation_results.json"
    manifest_path = tmp_path / "api_script_package_manifest.json"

    export_api_script_validation_result_to_json_file(result, result_path)
    export_api_script_validation_results_to_json_file(results, results_path)
    export_api_script_package_manifest_to_json_file(manifest, manifest_path)

    assert json.loads(result_path.read_text(encoding="utf-8"))["validation_id"] == "APIVAL-001"
    assert json.loads(results_path.read_text(encoding="utf-8"))[1]["draft_id"] == "API-DRAFT-002"
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["status"] == manifest.status


def test_exports_api_script_validation_result_and_package_markdown_strings():
    result, results, manifest = _build_api_script_validation_and_package()

    result_markdown = export_api_script_validation_result_to_markdown_string(result)
    results_markdown = export_api_script_validation_results_to_markdown_string(results)
    manifest_markdown = export_api_script_package_manifest_to_markdown_string(manifest)

    assert "APIVAL-001" in result_markdown
    assert "API-DRAFT-001" in result_markdown
    assert "Is Valid" in result_markdown
    assert "APIVAL-002" in results_markdown
    assert "APIPKG-001" in manifest_markdown
    assert "Package Status" in manifest_markdown


def test_writes_api_script_validation_result_and_package_markdown_files(tmp_path):
    result, results, manifest = _build_api_script_validation_and_package()

    result_path = tmp_path / "api_script_validation_result.md"
    results_path = tmp_path / "api_script_validation_results.md"
    manifest_path = tmp_path / "api_script_package_manifest.md"

    export_api_script_validation_result_to_markdown_file(result, result_path)
    export_api_script_validation_results_to_markdown_file(results, results_path)
    export_api_script_package_manifest_to_markdown_file(manifest, manifest_path)

    assert "APIVAL-001" in result_path.read_text(encoding="utf-8")
    assert "APIVAL-002" in results_path.read_text(encoding="utf-8")
    assert "APIPKG-001" in manifest_path.read_text(encoding="utf-8")


def test_exports_web_playwright_readiness_and_list_json_strings():
    readiness, readiness_items = _build_web_playwright_readiness_items()

    readiness_payload = json.loads(export_web_playwright_readiness_to_json_string(readiness))
    list_payload = json.loads(export_web_playwright_readiness_list_to_json_string(readiness_items))

    assert readiness_payload["readiness_id"] == "WPREAD-001"
    assert readiness_payload["test_case_id"] == "TC-300"
    assert "selector_hints" in readiness_payload
    assert list_payload[1]["readiness_id"] == "WPREAD-002"


def test_writes_web_playwright_readiness_and_list_json_files(tmp_path):
    readiness, readiness_items = _build_web_playwright_readiness_items()

    readiness_path = tmp_path / "web_playwright_readiness.json"
    list_path = tmp_path / "web_playwright_readiness_list.json"

    export_web_playwright_readiness_to_json_file(readiness, readiness_path)
    export_web_playwright_readiness_list_to_json_file(readiness_items, list_path)

    assert json.loads(readiness_path.read_text(encoding="utf-8"))["readiness_id"] == "WPREAD-001"
    assert json.loads(list_path.read_text(encoding="utf-8"))[1]["test_case_id"] == "TC-301"


def test_exports_web_playwright_readiness_and_list_markdown_strings():
    readiness, readiness_items = _build_web_playwright_readiness_items()

    readiness_markdown = export_web_playwright_readiness_to_markdown_string(readiness)
    list_markdown = export_web_playwright_readiness_list_to_markdown_string(readiness_items)

    assert "WPREAD-001" in readiness_markdown
    assert "TC-300" in readiness_markdown
    assert "Selector Hints" in readiness_markdown
    assert "Suggested Next Step" in readiness_markdown
    assert "WPREAD-002" in list_markdown


def test_writes_web_playwright_readiness_and_list_markdown_files(tmp_path):
    readiness, readiness_items = _build_web_playwright_readiness_items()

    readiness_path = tmp_path / "web_playwright_readiness.md"
    list_path = tmp_path / "web_playwright_readiness_list.md"

    export_web_playwright_readiness_to_markdown_file(readiness, readiness_path)
    export_web_playwright_readiness_list_to_markdown_file(readiness_items, list_path)

    assert "WPREAD-001" in readiness_path.read_text(encoding="utf-8")
    assert "WPREAD-002" in list_path.read_text(encoding="utf-8")


def test_exports_web_playwright_script_draft_and_list_json_strings():
    draft, drafts = _build_web_playwright_script_drafts()

    draft_payload = json.loads(export_web_playwright_script_draft_to_json_string(draft))
    drafts_payload = json.loads(export_web_playwright_script_drafts_to_json_string(drafts))

    assert draft_payload["draft_id"] == "WEB-DRAFT-001"
    assert draft_payload["test_case_id"] == "TC-400"
    assert draft_payload["status"] == "Draft"
    assert "script_content" in draft_payload
    assert drafts_payload[1]["draft_id"] == "WEB-DRAFT-002"


def test_writes_web_playwright_script_draft_and_list_json_files(tmp_path):
    draft, drafts = _build_web_playwright_script_drafts()

    draft_path = tmp_path / "web_playwright_script_draft.json"
    drafts_path = tmp_path / "web_playwright_script_drafts.json"

    export_web_playwright_script_draft_to_json_file(draft, draft_path)
    export_web_playwright_script_drafts_to_json_file(drafts, drafts_path)

    assert json.loads(draft_path.read_text(encoding="utf-8"))["draft_id"] == "WEB-DRAFT-001"
    assert json.loads(drafts_path.read_text(encoding="utf-8"))[1]["test_case_id"] == "TC-401"


def test_exports_web_playwright_script_draft_and_list_markdown_strings():
    draft, drafts = _build_web_playwright_script_drafts()

    draft_markdown = export_web_playwright_script_draft_to_markdown_string(draft)
    drafts_markdown = export_web_playwright_script_drafts_to_markdown_string(drafts)

    assert "WEB-DRAFT-001" in draft_markdown
    assert "TC-400" in draft_markdown
    assert "Draft" in draft_markdown
    assert "Warnings" in draft_markdown
    assert "```python" in draft_markdown
    assert "WEB-DRAFT-002" in drafts_markdown


def test_writes_web_playwright_script_draft_and_list_markdown_files(tmp_path):
    draft, drafts = _build_web_playwright_script_drafts()

    draft_path = tmp_path / "web_playwright_script_draft.md"
    drafts_path = tmp_path / "web_playwright_script_drafts.md"

    export_web_playwright_script_draft_to_markdown_file(draft, draft_path)
    export_web_playwright_script_drafts_to_markdown_file(drafts, drafts_path)

    assert "WEB-DRAFT-001" in draft_path.read_text(encoding="utf-8")
    assert "WEB-DRAFT-002" in drafts_path.read_text(encoding="utf-8")


def test_writes_web_playwright_script_draft_python_file(tmp_path):
    draft, _drafts = _build_web_playwright_script_drafts()
    output_path = tmp_path / draft.file_name

    written = export_web_playwright_script_draft_to_python_file(draft, output_path)

    assert written == output_path
    content = output_path.read_text(encoding="utf-8")
    assert "playwright.sync_api" in content
    assert "Draft only. Not executed / not verified." in content


def test_exports_web_playwright_validation_result_and_package_json_strings():
    result, results, manifest = _build_web_playwright_validation_and_package()

    result_payload = json.loads(export_web_playwright_validation_result_to_json_string(result))
    results_payload = json.loads(export_web_playwright_validation_results_to_json_string(results))
    manifest_payload = json.loads(export_web_playwright_package_manifest_to_json_string(manifest))

    assert result_payload["validation_id"] == "WPVAL-001"
    assert result_payload["draft_id"] == "WEB-DRAFT-001"
    assert "issues" in result_payload
    assert results_payload[1]["validation_id"] == "WPVAL-002"
    assert manifest_payload["package_id"] == "WPPKG-001"


def test_writes_web_playwright_validation_result_and_package_json_files(tmp_path):
    result, results, manifest = _build_web_playwright_validation_and_package()

    result_path = tmp_path / "web_playwright_validation_result.json"
    results_path = tmp_path / "web_playwright_validation_results.json"
    manifest_path = tmp_path / "web_playwright_package_manifest.json"

    export_web_playwright_validation_result_to_json_file(result, result_path)
    export_web_playwright_validation_results_to_json_file(results, results_path)
    export_web_playwright_package_manifest_to_json_file(manifest, manifest_path)

    assert json.loads(result_path.read_text(encoding="utf-8"))["validation_id"] == "WPVAL-001"
    assert json.loads(results_path.read_text(encoding="utf-8"))[1]["draft_id"] == "WEB-DRAFT-002"
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["status"] == manifest.status


def test_exports_web_playwright_validation_result_and_package_markdown_strings():
    result, results, manifest = _build_web_playwright_validation_and_package()

    result_markdown = export_web_playwright_validation_result_to_markdown_string(result)
    results_markdown = export_web_playwright_validation_results_to_markdown_string(results)
    manifest_markdown = export_web_playwright_package_manifest_to_markdown_string(manifest)

    assert "WPVAL-001" in result_markdown
    assert "WEB-DRAFT-001" in result_markdown
    assert "Is Valid" in result_markdown
    assert "WPVAL-002" in results_markdown
    assert "WPPKG-001" in manifest_markdown
    assert "Package Status" in manifest_markdown


def test_writes_web_playwright_validation_result_and_package_markdown_files(tmp_path):
    result, results, manifest = _build_web_playwright_validation_and_package()

    result_path = tmp_path / "web_playwright_validation_result.md"
    results_path = tmp_path / "web_playwright_validation_results.md"
    manifest_path = tmp_path / "web_playwright_package_manifest.md"

    export_web_playwright_validation_result_to_markdown_file(result, result_path)
    export_web_playwright_validation_results_to_markdown_file(results, results_path)
    export_web_playwright_package_manifest_to_markdown_file(manifest, manifest_path)

    assert "WPVAL-001" in result_path.read_text(encoding="utf-8")
    assert "WPVAL-002" in results_path.read_text(encoding="utf-8")
    assert "WPPKG-001" in manifest_path.read_text(encoding="utf-8")


def _build_draft_package_group_summary() -> DraftPackageGroupSummary:
    return DraftPackageGroupSummary(
        group_id="DRAFT-GROUP-API",
        group_type="api",
        manifest_path="script_drafts/api/api_script_package_manifest.json",
        validation_path="script_drafts/api/api_script_validation.json",
        status="Needs Attention",
        draft_count=2,
        valid_count=2,
        invalid_count=0,
        warning_count=1,
        ready_for_review_count=1,
        needs_attention_count=1,
        invalid_item_count=0,
        missing=False,
        notes=["Validation metadata includes 1 warning issue(s)."],
        metadata={"package_id": "APIPKG-001"},
        created_at="2024-01-15T00:00:00Z",
    )


def _build_unified_draft_package_summary() -> UnifiedDraftPackageSummary:
    api_group = _build_draft_package_group_summary()
    web_group = DraftPackageGroupSummary(
        group_id="DRAFT-GROUP-WEB-PLAYWRIGHT",
        group_type="web_playwright",
        manifest_path="script_drafts/web_playwright/web_playwright_package_manifest.json",
        validation_path="script_drafts/web_playwright/web_playwright_validation.json",
        status="Missing",
        draft_count=0,
        valid_count=0,
        invalid_count=0,
        warning_count=0,
        ready_for_review_count=0,
        needs_attention_count=0,
        invalid_item_count=0,
        missing=True,
        notes=["Draft package manifest is missing."],
        metadata={"manifest_exists": False},
        created_at="2024-01-15T00:01:00Z",
    )
    return UnifiedDraftPackageSummary(
        summary_id="DRAFT-SUM-001",
        workspace_path="artifacts/manual_qa_demo",
        total_groups=2,
        total_drafts=2,
        total_valid=2,
        total_invalid=0,
        total_warnings=1,
        ready_groups=0,
        needs_attention_groups=1,
        invalid_groups=0,
        missing_groups=1,
        groups=[api_group, web_group],
        overall_status="Needs Attention",
        recommended_next_step="Resolve warnings and TODOs before execution planning",
        created_at="2024-01-15T00:02:00Z",
        metadata={"available_group_types": ["api"]},
    )


def test_exports_draft_package_group_summary_json(tmp_path):
    group = _build_draft_package_group_summary()
    payload = json.loads(export_draft_package_group_summary_to_json_string(group))

    assert payload["group_id"] == "DRAFT-GROUP-API"
    assert payload["status"] == "Needs Attention"

    output_path = tmp_path / "draft_group_summary.json"
    export_draft_package_group_summary_to_json_file(group, output_path)
    assert json.loads(output_path.read_text(encoding="utf-8"))["warning_count"] == 1


def test_exports_draft_package_group_summary_markdown(tmp_path):
    group = _build_draft_package_group_summary()
    markdown = export_draft_package_group_summary_to_markdown_string(group)

    assert "DRAFT-GROUP-API" in markdown
    assert "Needs Attention" in markdown
    assert "Warning Count: 1" in markdown

    output_path = tmp_path / "draft_group_summary.md"
    export_draft_package_group_summary_to_markdown_file(group, output_path)
    assert "Manifest Path" in output_path.read_text(encoding="utf-8")


def test_exports_unified_draft_package_summary_json(tmp_path):
    summary = _build_unified_draft_package_summary()
    payload = json.loads(export_unified_draft_package_summary_to_json_string(summary))

    assert payload["summary_id"] == "DRAFT-SUM-001"
    assert payload["overall_status"] == "Needs Attention"
    assert payload["groups"][1]["group_type"] == "web_playwright"

    output_path = tmp_path / "draft_package_summary.json"
    export_unified_draft_package_summary_to_json_file(summary, output_path)
    assert json.loads(output_path.read_text(encoding="utf-8"))["missing_groups"] == 1


def test_exports_unified_draft_package_summary_markdown(tmp_path):
    summary = _build_unified_draft_package_summary()
    markdown = export_unified_draft_package_summary_to_markdown_string(summary)

    assert "Overall Status: Needs Attention" in markdown
    assert "Recommended Next Step: Resolve warnings and TODOs before execution planning" in markdown
    assert "API Group Summary" in markdown
    assert "Web Playwright Group Summary" in markdown
    assert "Missing Groups" in markdown

    output_path = tmp_path / "draft_package_summary.md"
    export_unified_draft_package_summary_to_markdown_file(summary, output_path)
    assert "Total Drafts: 2" in output_path.read_text(encoding="utf-8")


def _build_execution_safety_policy() -> ExecutionSafetyPolicy:
    return ExecutionSafetyPolicy(
        policy_id="EXEC-POLICY-DEFAULT",
        name="default",
        allow_execution=False,
        allowed_base_urls=["http://localhost", "http://127.0.0.1"],
        blocked_base_urls=["production", "prod", "live", "payment-live", "real-bank"],
        allowed_script_types=["api", "web_playwright"],
        blocked_script_types=["mobile_appium"],
        allow_write_methods=False,
        allow_delete_methods=False,
        require_human_approval=True,
        require_valid_package=True,
        require_no_critical_todos=True,
        timeout_seconds=30,
        max_scripts_per_run=5,
        dry_run_only=True,
        metadata={},
        created_at="2024-01-16T00:00:00Z",
    )


def _build_execution_target() -> ExecutionTarget:
    return ExecutionTarget(
        target_id="EXEC-TARGET-001",
        script_type="api",
        draft_id="API-DRAFT-001",
        file_name="test_api_tc_001.py",
        package_status="Ready for Review",
        validation_status="Valid",
        base_url="http://localhost:8000",
        method="GET",
        endpoint_or_page="/api/orders",
        has_todos=False,
        has_critical_todos=False,
        metadata={},
    )


def _build_execution_preflight_result() -> ExecutionPreflightResult:
    issue = ExecutionPreflightIssue(
        issue_id="EXEC-ISSUE-001",
        target_id="EXEC-TARGET-001",
        severity="High",
        issue_type="execution_disabled_by_policy",
        message="Execution is disabled by the current safety policy.",
        recommendation="Keep this plan static until a later sandbox phase enables execution safely.",
        metadata={},
    )
    return ExecutionPreflightResult(
        preflight_id="EXEC-PREFLIGHT-001",
        target_id="EXEC-TARGET-001",
        script_type="api",
        decision="Dry Run Only",
        is_allowed=False,
        issues=[issue],
        risk_level="High",
        recommended_action="Keep this target in dry-run planning mode only.",
        metadata={"package_status": "Ready for Review"},
        created_at="2024-01-17T00:00:00Z",
    )


def _build_execution_plan() -> ExecutionPlan:
    policy = _build_execution_safety_policy()
    target = _build_execution_target()
    result = _build_execution_preflight_result()
    return ExecutionPlan(
        plan_id="EXEC-PLAN-001",
        workspace_path="artifacts/manual_qa_demo",
        policy=policy,
        targets=[target],
        preflight_results=[result],
        total_targets=1,
        allowed_count=0,
        blocked_count=0,
        needs_approval_count=1,
        dry_run_only=True,
        overall_decision="Needs Attention",
        recommended_next_step="Review policy issues, TODOs, and approval requirements before sandbox prototyping",
        metadata={"missing_group_types": ["web_playwright"]},
        created_at="2024-01-17T00:01:00Z",
    )


def test_exports_execution_safety_policy_json_and_markdown(tmp_path):
    policy = _build_execution_safety_policy()
    payload = json.loads(export_execution_safety_policy_to_json_string(policy))
    markdown = export_execution_safety_policy_to_markdown_string(policy)

    assert payload["policy_id"] == "EXEC-POLICY-DEFAULT"
    assert payload["dry_run_only"] is True
    assert "Policy Summary" in markdown
    assert "Dry Run Only: True" in markdown

    json_path = tmp_path / "execution_policy.json"
    md_path = tmp_path / "execution_policy.md"
    export_execution_safety_policy_to_json_file(policy, json_path)
    export_execution_safety_policy_to_markdown_file(policy, md_path)
    assert json.loads(json_path.read_text(encoding="utf-8"))["name"] == "default"
    assert "Allowed Base URLs" in md_path.read_text(encoding="utf-8")


def test_exports_execution_preflight_result_json_and_markdown(tmp_path):
    result = _build_execution_preflight_result()
    payload = json.loads(export_execution_preflight_result_to_json_string(result))
    markdown = export_execution_preflight_result_to_markdown_string(result)

    assert payload["preflight_id"] == "EXEC-PREFLIGHT-001"
    assert payload["issues"][0]["issue_type"] == "execution_disabled_by_policy"
    assert "Decision: Dry Run Only" in markdown
    assert "Risk Level: High" in markdown

    json_path = tmp_path / "execution_preflight_result.json"
    md_path = tmp_path / "execution_preflight_result.md"
    export_execution_preflight_result_to_json_file(result, json_path)
    export_execution_preflight_result_to_markdown_file(result, md_path)
    assert json.loads(json_path.read_text(encoding="utf-8"))["target_id"] == "EXEC-TARGET-001"
    assert "EXEC-ISSUE-001" in md_path.read_text(encoding="utf-8")


def test_exports_execution_plan_json_and_markdown(tmp_path):
    plan = _build_execution_plan()
    payload = json.loads(export_execution_plan_to_json_string(plan))
    markdown = export_execution_plan_to_markdown_string(plan)

    assert payload["plan_id"] == "EXEC-PLAN-001"
    assert payload["policy"]["policy_id"] == "EXEC-POLICY-DEFAULT"
    assert payload["preflight_results"][0]["decision"] == "Dry Run Only"
    assert "Overall Decision: Needs Attention" in markdown
    assert "Needs Approval Count: 1" in markdown
    assert "Risk Levels" in markdown

    json_path = tmp_path / "execution_plan.json"
    md_path = tmp_path / "execution_plan.md"
    export_execution_plan_to_json_file(plan, json_path)
    export_execution_plan_to_markdown_file(plan, md_path)
    assert json.loads(json_path.read_text(encoding="utf-8"))["total_targets"] == 1
    assert "Execution Preflight Plan" in md_path.read_text(encoding="utf-8")


def _build_api_execution_request() -> APIExecutionRequest:
    return APIExecutionRequest(
        request_id="API-EXEC-REQ-001",
        draft_id="API-DRAFT-001",
        test_case_id="TC-900",
        file_name="test_api_tc_001.py",
        method="GET",
        base_url="http://localhost:8000",
        endpoint="/api/orders",
        headers={},
        payload={},
        timeout_seconds=30,
        policy_id="EXEC-POLICY-DEFAULT",
        preflight_id="EXEC-PREFLIGHT-001",
        dry_run=True,
        metadata={"approved": False},
        created_at="2024-01-18T00:00:00Z",
    )


def _build_api_execution_result(status: str = "Dry Run") -> APIExecutionResult:
    request = _build_api_execution_request()
    logs = [
        APIExecutionLogEntry(
            log_id="API-EXEC-LOG-001",
            level="Info",
            message="Dry-run only mode; request was not sent.",
            metadata={},
            created_at="2024-01-18T00:01:00Z",
        )
    ]
    return APIExecutionResult(
        execution_id="API-EXEC-RESULT-001",
        request=request,
        status=status,
        http_status_code=200 if status == "Passed" else None,
        duration_ms=12,
        response_excerpt="ok" if status == "Passed" else "",
        error_type="",
        error_message="",
        assertion_expected_status=200,
        assertion_passed=True if status == "Passed" else None,
        logs=logs,
        executed_at="2024-01-18T00:02:00Z",
        metadata={"sandbox_only": True},
    )


def _build_api_execution_evidence(status: str = "Passed") -> APIExecutionEvidence:
    return APIExecutionEvidence(
        evidence_id="API-EVD-001",
        execution_id="API-EXEC-RESULT-001",
        draft_id="API-DRAFT-001",
        test_case_id="TC-900",
        evidence_type="api_execution_result",
        title="Order API draft - API sandbox Passed",
        summary="Sandbox request GET /api/orders passed with HTTP 200.",
        status=status,
        method="GET",
        base_url="http://localhost:8000",
        endpoint="/api/orders",
        http_status_code=200 if status == "Passed" else 500,
        assertion_passed=True if status == "Passed" else False,
        response_excerpt="ok",
        error_type="",
        error_message="",
        log_refs=["API-EXEC-LOG-001"],
        metadata={"sandbox_only": True},
        created_at="2024-01-20T00:00:00Z",
    )


def _build_api_execution_summary(status: str = "Passed") -> APIExecutionSummary:
    return APIExecutionSummary(
        summary_id="API-EXEC-SUM-001",
        total=2,
        passed=1 if status == "Passed" else 0,
        failed=1 if status == "Failed" else 0,
        blocked=1 if status == "Blocked" else 0,
        dry_run=2 if status == "All Dry Run" else 0,
        error=1 if status == "Failed" else 0,
        not_run=0,
        pass_rate=50.0 if status == "Passed" else 0.0,
        failure_rate=50.0 if status == "Failed" else 0.0,
        evidence_ids=["API-EVD-001"],
        bug_suggestion_ids=["BUG-APIEXEC-001"] if status == "Failed" else [],
        failure_signature_ids=["FSIG-001"] if status == "Failed" else [],
        status=status,
        recommended_next_step="Review mixed execution outcomes",
        metadata={"sandbox_only": True},
        created_at="2024-01-20T00:01:00Z",
    )


def _build_api_execution_history_entry(status: str = "Passed") -> APIExecutionHistoryEntry:
    return APIExecutionHistoryEntry(
        history_id="API-HIST-001",
        source_file="reports/api_execution_summary.json",
        run_label="current",
        summary_id="API-EXEC-SUM-001",
        total=2,
        passed=1 if status == "Passed" else 0,
        failed=1 if status == "Failed" else 0,
        blocked=1 if status == "Blocked" else 0,
        dry_run=2 if status == "All Dry Run" else 0,
        error=1 if status == "Failed" else 0,
        not_run=0,
        pass_rate=50.0 if status == "Passed" else 0.0,
        failure_rate=50.0 if status == "Failed" else 0.0,
        status=status,
        evidence_ids=["API-EVD-001"],
        bug_suggestion_ids=["BUG-APIEXEC-001"] if status == "Failed" else [],
        failure_signature_ids=["FSIG-001"] if status == "Failed" else [],
        created_at="2024-01-21T00:00:00Z",
        metadata={"sandbox_only": True},
    )


def _build_api_execution_trend_summary(status: str = "Stable") -> APIExecutionTrendSummary:
    return APIExecutionTrendSummary(
        trend_id="API-TREND-001",
        total_runs=2,
        total_executions=4,
        total_passed=2,
        total_failed=1,
        total_blocked=0,
        total_dry_run=0,
        total_error=1,
        total_not_run=0,
        average_pass_rate=50.0,
        average_failure_rate=50.0,
        latest_status="Failed" if status == "Regressing" else "Passed",
        trend_status=status,
        repeated_failure_count=1,
        flaky_candidate_count=1,
        repeated_failure_keys=["endpoint:GET /api/orders"],
        flaky_candidate_keys=["TC-900"],
        entries=[_build_api_execution_history_entry(status="Failed"), _build_api_execution_history_entry(status="Passed")],
        recommended_next_step="Review mixed history and failure patterns",
        metadata={"sandbox_only": True},
        created_at="2024-01-21T00:05:00Z",
    )


def test_exports_api_execution_request_json_and_markdown(tmp_path):
    request = _build_api_execution_request()
    payload = json.loads(export_api_execution_request_to_json_string(request))
    markdown = export_api_execution_request_to_markdown_string(request)

    assert payload["request_id"] == "API-EXEC-REQ-001"
    assert payload["dry_run"] is True
    assert "Method: GET" in markdown
    assert "Base URL: http://localhost:8000" in markdown

    json_path = tmp_path / "api_execution_request.json"
    md_path = tmp_path / "api_execution_request.md"
    export_api_execution_request_to_json_file(request, json_path)
    export_api_execution_request_to_markdown_file(request, md_path)
    assert json.loads(json_path.read_text(encoding="utf-8"))["draft_id"] == "API-DRAFT-001"
    assert "Policy ID: EXEC-POLICY-DEFAULT" in md_path.read_text(encoding="utf-8")


def test_exports_api_execution_result_json_and_markdown(tmp_path):
    result = _build_api_execution_result(status="Passed")
    payload = json.loads(export_api_execution_result_to_json_string(result))
    markdown = export_api_execution_result_to_markdown_string(result)

    assert payload["execution_id"] == "API-EXEC-RESULT-001"
    assert payload["request"]["request_id"] == "API-EXEC-REQ-001"
    assert "Sandbox Warning" in markdown
    assert "Status: Passed" in markdown
    assert "Assertion Passed: True" in markdown

    json_path = tmp_path / "api_execution_result.json"
    md_path = tmp_path / "api_execution_result.md"
    export_api_execution_result_to_json_file(result, json_path)
    export_api_execution_result_to_markdown_file(result, md_path)
    assert json.loads(json_path.read_text(encoding="utf-8"))["status"] == "Passed"
    assert "HTTP Status Code: 200" in md_path.read_text(encoding="utf-8")


def test_exports_api_execution_result_list_json_and_markdown(tmp_path):
    results = [_build_api_execution_result(status="Dry Run"), _build_api_execution_result(status="Blocked")]
    payload = json.loads(export_api_execution_results_to_json_string(results))
    markdown = export_api_execution_results_to_markdown_string(results)

    assert len(payload) == 2
    assert payload[0]["execution_id"] == "API-EXEC-RESULT-001"
    assert "API Sandbox Execution Results" in markdown
    assert "Status: Dry Run" in markdown

    json_path = tmp_path / "api_execution_results.json"
    md_path = tmp_path / "api_execution_results.md"
    export_api_execution_results_to_json_file(results, json_path)
    export_api_execution_results_to_markdown_file(results, md_path)
    assert len(json.loads(json_path.read_text(encoding="utf-8"))) == 2
    assert "sandbox-only" in md_path.read_text(encoding="utf-8").lower()


def test_exports_api_execution_evidence_json_and_markdown(tmp_path):
    evidence = _build_api_execution_evidence()
    payload = json.loads(export_api_execution_evidence_to_json_string(evidence))
    markdown = export_api_execution_evidence_to_markdown_string(evidence)

    assert payload["evidence_id"] == "API-EVD-001"
    assert payload["status"] == "Passed"
    assert "API Execution Evidence" in markdown
    assert "does not overwrite Manual QA TestResult state" in markdown

    json_path = tmp_path / "api_execution_evidence.json"
    md_path = tmp_path / "api_execution_evidence.md"
    export_api_execution_evidence_to_json_file(evidence, json_path)
    export_api_execution_evidence_to_markdown_file(evidence, md_path)
    assert json.loads(json_path.read_text(encoding="utf-8"))["execution_id"] == "API-EXEC-RESULT-001"
    assert "Evidence ID: API-EVD-001" in md_path.read_text(encoding="utf-8")


def test_exports_api_execution_summary_json_and_markdown(tmp_path):
    summary = _build_api_execution_summary(status="Failed")
    payload = json.loads(export_api_execution_summary_to_json_string(summary))
    markdown = export_api_execution_summary_to_markdown_string(summary)

    assert payload["summary_id"] == "API-EXEC-SUM-001"
    assert payload["status"] == "Failed"
    assert "Failure Rate: 50.0" in markdown
    assert "Bug Suggestion IDs: BUG-APIEXEC-001" in markdown

    json_path = tmp_path / "api_execution_summary.json"
    md_path = tmp_path / "api_execution_summary.md"
    export_api_execution_summary_to_json_file(summary, json_path)
    export_api_execution_summary_to_markdown_file(summary, md_path)
    assert json.loads(json_path.read_text(encoding="utf-8"))["failed"] == 1
    assert "Status: Failed" in md_path.read_text(encoding="utf-8")


def test_exports_api_execution_evidence_list_json_and_markdown(tmp_path):
    evidence_items = [_build_api_execution_evidence(status="Passed"), _build_api_execution_evidence(status="Failed")]
    payload = json.loads(export_api_execution_evidence_list_to_json_string(evidence_items))
    markdown = export_api_execution_evidence_list_to_markdown_string(evidence_items)

    assert len(payload) == 2
    assert "API Execution Evidence" in markdown
    assert "Summary: Sandbox request GET /api/orders passed with HTTP 200." in markdown

    json_path = tmp_path / "api_execution_evidence_list.json"
    md_path = tmp_path / "api_execution_evidence_list.md"
    export_api_execution_evidence_list_to_json_file(evidence_items, json_path)
    export_api_execution_evidence_list_to_markdown_file(evidence_items, md_path)
    assert len(json.loads(json_path.read_text(encoding="utf-8"))) == 2
    assert "does not overwrite Manual QA TestResult state" in md_path.read_text(encoding="utf-8")


def test_exports_api_execution_evidence_report_markdown():
    bug_service = BugDraftService()
    suite = TestSuiteService().create_test_suite(project_id="checkout-web", name="API", test_cases=["TC-900"])
    test_run = TestRunService().create_test_run(
        project_id="checkout-web",
        suite=suite,
        environment="sandbox",
        build="api-execution-sandbox",
        tester="qa-user",
    )
    TestResultService().update_test_result(test_run, "TC-900", "Fail", actual_result="Expected 200 but received 500.")
    report = {
        "evidence_items": [_build_api_execution_evidence(status="Failed")],
        "summary": _build_api_execution_summary(status="Failed"),
        "bug_suggestions": [bug_service.generate_bug_draft(test_run, "TC-900")],
        "failure_signatures": [
            FailureMemoryService().create_failure_signature(title="Sandbox failure", symptom="GET /api/orders failed")
        ],
        "metadata": {"sandbox_only": True},
    }

    markdown = export_api_execution_evidence_report_to_markdown_string(report)

    assert "Summary Status: Failed" in markdown
    assert "Bug Suggestions" in markdown
    assert "Failure Signatures" in markdown


def test_exports_api_execution_history_entry_json_and_markdown(tmp_path):
    entry = _build_api_execution_history_entry(status="Failed")
    payload = json.loads(export_api_execution_history_entry_to_json_string(entry))
    markdown = export_api_execution_history_entry_to_markdown_string(entry)

    assert payload["history_id"] == "API-HIST-001"
    assert payload["status"] == "Failed"
    assert "API Execution History Entry" in markdown
    assert "History ID: API-HIST-001" in markdown

    json_path = tmp_path / "api_execution_history_entry.json"
    md_path = tmp_path / "api_execution_history_entry.md"
    export_api_execution_history_entry_to_json_file(entry, json_path)
    export_api_execution_history_entry_to_markdown_file(entry, md_path)
    assert json.loads(json_path.read_text(encoding="utf-8"))["summary_id"] == "API-EXEC-SUM-001"
    assert "does not overwrite Manual QA TestResult state" in md_path.read_text(encoding="utf-8")


def test_exports_api_execution_trend_summary_json_and_markdown(tmp_path):
    summary = _build_api_execution_trend_summary(status="Regressing")
    payload = json.loads(export_api_execution_trend_summary_to_json_string(summary))
    markdown = export_api_execution_trend_summary_to_markdown_string(summary)

    assert payload["trend_id"] == "API-TREND-001"
    assert payload["trend_status"] == "Regressing"
    assert "Trend Status: Regressing" in markdown
    assert "Repeated Failure Count: 1" in markdown

    json_path = tmp_path / "api_execution_trend_summary.json"
    md_path = tmp_path / "api_execution_trend_summary.md"
    export_api_execution_trend_summary_to_json_file(summary, json_path)
    export_api_execution_trend_summary_to_markdown_file(summary, md_path)
    assert json.loads(json_path.read_text(encoding="utf-8"))["total_runs"] == 2
    assert "Flaky Candidate Count: 1" in md_path.read_text(encoding="utf-8")


def test_exports_api_execution_history_entries_json_and_markdown(tmp_path):
    entries = [_build_api_execution_history_entry(status="Passed"), _build_api_execution_history_entry(status="Failed")]
    payload = json.loads(export_api_execution_history_entries_to_json_string(entries))
    markdown = export_api_execution_history_entries_to_markdown_string(entries)

    assert len(payload) == 2
    assert "API Execution History" in markdown
    assert "Run Label: current" in markdown

    json_path = tmp_path / "api_execution_history_entries.json"
    md_path = tmp_path / "api_execution_history_entries.md"
    export_api_execution_history_entries_to_json_file(entries, json_path)
    export_api_execution_history_entries_to_markdown_file(entries, md_path)
    assert len(json.loads(json_path.read_text(encoding="utf-8"))) == 2
    assert "metadata-only" in md_path.read_text(encoding="utf-8").lower()


def test_exports_api_execution_history_report_markdown():
    report = {
        "history_entries": [_build_api_execution_history_entry(status="Failed")],
        "trend_summary": _build_api_execution_trend_summary(status="Needs Review"),
        "repeated_failures": ["endpoint:GET /api/orders"],
        "flaky_candidates": ["TC-900"],
        "metadata": {"sandbox_only": True},
    }

    markdown = export_api_execution_history_report_to_markdown_string(report)

    assert "Trend Summary" in markdown
    assert "Repeated Failures" in markdown
    assert "Flaky Candidates" in markdown
