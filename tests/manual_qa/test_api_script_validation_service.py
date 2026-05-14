from __future__ import annotations

from orchestrator.manual_qa.api_script_generator import APITestScriptGenerator
from orchestrator.manual_qa.api_script_validation_service import APIScriptValidationService
from orchestrator.manual_qa.models import APITestScriptDraft, ManualTestCase, ScriptGenerationReadiness


def _draft(script_content: str, *, draft_id: str = "API-DRAFT-001", file_name: str = "test_demo.py") -> APITestScriptDraft:
    return APITestScriptDraft(
        draft_id=draft_id,
        test_case_id="TC-001",
        requirement_ids=["REQ-001"],
        module="Order API",
        title="API draft",
        readiness_id="READ-001",
        file_name=file_name,
        script_content=script_content,
    )


def _generated_draft() -> APITestScriptDraft:
    test_case = ManualTestCase(
        test_case_id="TC-001",
        requirement_ids=["REQ-001"],
        module="Order API",
        title="Create order endpoint returns status code 201",
        steps=["Send POST request to /api/orders with valid payload.", "Verify response status code is 201."],
        expected_result="Response status code is 201 and order is created.",
        metadata={"test_data": {"sku": "SKU-001"}},
    )
    readiness = ScriptGenerationReadiness(
        readiness_id="READ-001",
        test_case_id="TC-001",
        module="Order API",
        title=test_case.title,
        target_type="api",
        readiness_status="Ready",
        readiness_score=85,
    )
    return APITestScriptGenerator().generate_api_script_draft(test_case, readiness=readiness)


def test_validates_syntactically_valid_draft():
    service = APIScriptValidationService()

    result = service.validate_api_script_draft(_generated_draft())

    assert result.is_valid is True
    assert result.syntax_valid is True
    assert result.has_status_assertion is True


def test_detects_syntax_error():
    service = APIScriptValidationService()
    draft = _draft("def test_bad(:\n    pass\n")

    result = service.validate_api_script_draft(draft)

    assert result.is_valid is False
    assert result.syntax_valid is False
    assert any(issue.issue_type == "syntax_error" for issue in result.issues)


def test_detects_missing_draft_marker():
    service = APIScriptValidationService()
    draft = _draft(
        "import os\nimport requests\nBASE_URL='x'\n\ndef test_ok():\n    response = requests.get(BASE_URL)\n    assert response.status_code == 200\n"
    )

    result = service.validate_api_script_draft(draft)

    assert any(issue.issue_type == "missing_draft_marker" for issue in result.issues)


def test_detects_missing_no_execution_marker():
    service = APIScriptValidationService()
    draft = _draft(
        'import os\nimport requests\nBASE_URL = "x"\n\ndef test_ok():\n    """Draft only."""\n    response = requests.get(BASE_URL)\n    assert response.status_code == 200\n'
    )

    result = service.validate_api_script_draft(draft)

    assert any(issue.issue_type == "missing_no_execution_marker" for issue in result.issues)


def test_detects_missing_status_assertion():
    service = APIScriptValidationService()
    draft = _draft(
        'import os\nimport requests\nBASE_URL = "x"\n\ndef test_ok():\n    """Draft only. Not executed."""\n    response = requests.get(BASE_URL)\n    return response\n'
    )

    result = service.validate_api_script_draft(draft)

    assert any(issue.issue_type == "missing_status_assertion" for issue in result.issues)


def test_detects_todo_endpoint_as_warning():
    service = APIScriptValidationService()
    draft = _draft(
        'import os\nimport requests\nBASE_URL = "x"\n\ndef test_ok():\n    """Draft only. Not executed."""\n    response = requests.get(f"{BASE_URL}/TODO_ENDPOINT")\n    assert response.status_code == 200\n'
    )

    result = service.validate_api_script_draft(draft)

    assert result.has_todo_endpoint is True
    assert any(issue.issue_type == "todo_endpoint" for issue in result.issues)


def test_detects_todo_payload_as_warning():
    service = APIScriptValidationService()
    draft = _draft(
        'import os\nimport requests\nBASE_URL = "x"\n\ndef test_ok():\n    """Draft only. Not executed."""\n    payload = {"TODO": "payload"}\n    response = requests.post(BASE_URL, json=payload)\n    assert response.status_code == 200\n'
    )

    result = service.validate_api_script_draft(draft)

    assert result.has_todo_payload is True
    assert any(issue.issue_type == "todo_payload" for issue in result.issues)


def test_does_not_execute_script_content():
    service = APIScriptValidationService()
    draft = _draft(
        "import requests\nBASE_URL='x'\n\ndef test_side_effect():\n    '''Draft only. Not executed.'''\n    sentinel = 'should_not_run'\n    response = requests.get(BASE_URL)\n    assert response.status_code == 200\n"
    )

    result = service.validate_api_script_draft(draft)

    assert result.is_valid is True
    assert result.metadata["requests_usage_detected"] is True


def test_batch_validation_preserves_input_order():
    service = APIScriptValidationService()
    drafts = [
        _generated_draft(),
        _draft(
            'import os\nimport requests\nBASE_URL = "x"\n\ndef test_other():\n    """Draft only. Not executed."""\n    response = requests.get(BASE_URL)\n    assert response.status_code == 200\n',
            draft_id="API-DRAFT-002",
            file_name="test_other.py",
        ),
    ]

    results = service.validate_api_script_drafts(drafts)

    assert [item.draft_id for item in results] == ["API-DRAFT-001", "API-DRAFT-002"]
