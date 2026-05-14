from __future__ import annotations

import pytest

from orchestrator.manual_qa.api_script_generator import APITestScriptGenerator
from orchestrator.manual_qa.models import ManualTestCase, ScriptGenerationReadiness


def _api_case(
    *,
    test_case_id: str = "TC-001",
    title: str = "Get users endpoint returns status code 200",
    steps: list[str] | None = None,
    expected_result: str = "Response status code is 200 and users are returned.",
    metadata: dict | None = None,
) -> ManualTestCase:
    return ManualTestCase(
        test_case_id=test_case_id,
        requirement_ids=["REQ-001"],
        module="User API",
        title=title,
        steps=steps or ["Send GET request to /api/v1/users.", "Verify response status code is 200."],
        expected_result=expected_result,
        metadata=metadata or {},
    )


def _readiness(
    *,
    test_case_id: str = "TC-001",
    target_type: str = "api",
    readiness_status: str = "Ready",
) -> ScriptGenerationReadiness:
    return ScriptGenerationReadiness(
        readiness_id="READ-001",
        test_case_id=test_case_id,
        module="User API",
        title="API readiness",
        target_type=target_type,
        readiness_status=readiness_status,
        readiness_score=85,
    )


def test_generates_pytest_requests_draft_for_get_endpoint():
    generator = APITestScriptGenerator()

    draft = generator.generate_api_script_draft(_api_case(), readiness=_readiness())

    assert draft.framework == "pytest-requests"
    assert draft.language == "python"
    assert draft.metadata["http_method"] == "GET"
    assert draft.metadata["endpoint"] == "/api/v1/users"
    assert "requests.get" in draft.script_content
    assert 'assert response.status_code == 200' in draft.script_content


def test_generates_post_draft_when_post_is_detected():
    generator = APITestScriptGenerator()
    test_case = _api_case(
        title="Create user endpoint returns 201",
        steps=["Send POST request to /api/v1/users with valid payload.", "Verify response status code is 201."],
        expected_result="Response status code is 201 and user is created.",
        metadata={"test_data": {"name": "Alice"}},
    )

    draft = generator.generate_api_script_draft(test_case, readiness=_readiness())

    assert draft.metadata["http_method"] == "POST"
    assert "requests.post" in draft.script_content
    assert "payload =" in draft.script_content


def test_detects_expected_status_code():
    generator = APITestScriptGenerator()
    test_case = _api_case(expected_result="Response status code is 204 and the resource is deleted.")

    draft = generator.generate_api_script_draft(test_case, readiness=_readiness())

    assert draft.metadata["expected_status_code"] == 204
    assert "assert response.status_code == 204" in draft.script_content


def test_uses_todo_endpoint_and_warning_when_endpoint_missing():
    generator = APITestScriptGenerator()
    test_case = _api_case(
        title="Fetch user profile API",
        steps=["Send GET request with valid authorization token.", "Verify response status code is 200."],
    )

    draft = generator.generate_api_script_draft(test_case, readiness=_readiness())

    assert draft.metadata["endpoint"] == "/TODO_ENDPOINT"
    assert any("Endpoint not detected" in item for item in draft.warnings)
    assert "/TODO_ENDPOINT" in draft.script_content


def test_uses_default_status_code_and_warning_when_status_missing():
    generator = APITestScriptGenerator()
    test_case = _api_case(
        steps=["Send GET request to /api/v1/users."],
        expected_result="Users are returned successfully.",
    )

    draft = generator.generate_api_script_draft(test_case, readiness=_readiness())

    assert draft.metadata["expected_status_code"] == 200
    assert any("Defaulted to 200" in item for item in draft.warnings)


def test_rejects_not_suitable_readiness():
    generator = APITestScriptGenerator()

    with pytest.raises(ValueError, match="not suitable"):
        generator.generate_api_script_draft(
            _api_case(),
            readiness=_readiness(readiness_status="Not Suitable"),
        )


def test_preserves_test_case_id_and_requirement_ids():
    generator = APITestScriptGenerator()
    test_case = ManualTestCase(
        test_case_id="TC-123",
        requirement_ids=["REQ-100", "REQ-101"],
        module="Auth API",
        title="Login endpoint returns 200",
        steps=["Send POST request to /api/v1/login with valid credentials."],
        expected_result="Response status code is 200.",
    )

    draft = generator.generate_api_script_draft(
        test_case,
        readiness=_readiness(test_case_id="TC-123"),
    )

    assert draft.test_case_id == "TC-123"
    assert draft.requirement_ids == ["REQ-100", "REQ-101"]


def test_generated_script_includes_draft_only_not_executed_warning():
    generator = APITestScriptGenerator()

    draft = generator.generate_api_script_draft(_api_case(), readiness=_readiness())

    assert "Draft only. Not executed / not verified." in draft.script_content
    assert "Manual QA draft only. Not executed by the generator." in draft.script_content


def test_generated_script_is_deterministic():
    test_case = _api_case()
    readiness = _readiness()

    draft_one = APITestScriptGenerator().generate_api_script_draft(test_case, readiness=readiness)
    draft_two = APITestScriptGenerator().generate_api_script_draft(test_case, readiness=readiness)

    assert draft_one.to_dict() == draft_two.to_dict()


def test_batch_generation_preserves_input_order_for_eligible_cases():
    generator = APITestScriptGenerator()
    cases = [
        _api_case(test_case_id="TC-010", title="List users endpoint", steps=["Send GET request to /api/v1/users."]),
        _api_case(test_case_id="TC-011", title="Create user endpoint", steps=["Send POST request to /api/v1/users."]),
    ]
    readiness_items = [
        _readiness(test_case_id="TC-010"),
        _readiness(test_case_id="TC-011"),
    ]

    drafts = generator.generate_api_script_drafts(cases, readiness_items=readiness_items)

    assert [item.test_case_id for item in drafts] == ["TC-010", "TC-011"]


def test_no_script_execution_occurs():
    generator = APITestScriptGenerator()

    draft = generator.generate_api_script_draft(_api_case(), readiness=_readiness())

    assert draft.status == "Draft"
    assert "requests.get" in draft.script_content
    assert "Not executed" in draft.script_content
