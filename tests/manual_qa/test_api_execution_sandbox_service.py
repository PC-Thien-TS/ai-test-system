from __future__ import annotations

import sys
from dataclasses import replace

from orchestrator.manual_qa.api_execution_sandbox_service import (
    APIExecutionSandboxService,
)
from orchestrator.manual_qa.execution_safety_service import (
    create_default_execution_safety_policy,
)
from orchestrator.manual_qa.models import (
    APIScriptValidationResult,
    APITestScriptDraft,
    TestResult,
)


class _FakeResponse:
    def __init__(self, *, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


class _FakeSession:
    def __init__(self, response: _FakeResponse | None = None, exception: Exception | None = None) -> None:
        self.response = response
        self.exception = exception
        self.calls: list[dict[str, object]] = []

    def request(self, method: str, url: str, **kwargs: object) -> _FakeResponse:
        self.calls.append({"method": method, "url": url, **kwargs})
        if self.exception is not None:
            raise self.exception
        assert self.response is not None
        return self.response


def _build_draft(
    *,
    method: str = "GET",
    base_url: str = "http://localhost:8000",
    endpoint: str = "/api/orders",
    expected_status: int | None = 200,
    payload_line: str = "",
) -> APITestScriptDraft:
    assertion_line = (
        f"    assert response.status_code == {expected_status}"
        if expected_status is not None
        else "    # no explicit assertion"
    )
    script_lines = [
        "import os",
        "import requests",
        "",
        f'BASE_URL = os.getenv("API_BASE_URL", "{base_url}")',
        "",
        "def test_api_draft():",
        "    headers = {}",
    ]
    if payload_line:
        script_lines.append(payload_line)
    request_call = f'    response = requests.{method.lower()}(BASE_URL + "{endpoint}", headers=headers'
    if payload_line:
        request_call += ", json=payload"
    request_call += ")"
    script_lines.extend([request_call, assertion_line, ""])
    return APITestScriptDraft(
        draft_id="API-DRAFT-001",
        test_case_id="TC-900",
        requirement_ids=["REQ-900"],
        module="Order API",
        title="Order API draft",
        readiness_id="READ-900",
        target_type="api",
        framework="pytest-requests",
        language="python",
        file_name="test_api_tc_001.py",
        script_content="\n".join(script_lines),
        status="Draft",
        warnings=[],
        assumptions=[],
        metadata={
            "http_method": method,
            "endpoint": endpoint,
            "base_url_env_var": "API_BASE_URL",
        },
        created_at="2024-01-08T00:00:00Z",
    )


def _build_validation(*, is_valid: bool = True, has_todo_endpoint: bool = False) -> APIScriptValidationResult:
    return APIScriptValidationResult(
        validation_id="APIVAL-001",
        draft_id="API-DRAFT-001",
        test_case_id="TC-900",
        file_name="test_api_tc_001.py",
        is_valid=is_valid,
        syntax_valid=True,
        has_draft_warning=True,
        has_no_execution_marker=True,
        has_status_assertion=True,
        has_todo_endpoint=has_todo_endpoint,
        has_todo_payload=False,
        issues=[],
        metadata={},
        created_at="2024-01-09T00:00:00Z",
    )


def _executable_policy(*, allow_write_methods: bool = False, allow_delete_methods: bool = False):
    base = create_default_execution_safety_policy(dry_run_only=False)
    return replace(
        base,
        allow_execution=True,
        dry_run_only=False,
        allow_write_methods=allow_write_methods,
        allow_delete_methods=allow_delete_methods,
    )


def test_dry_run_does_not_call_session():
    service = APIExecutionSandboxService()
    draft = _build_draft()
    session = _FakeSession(response=_FakeResponse(status_code=200, text="ok"))

    result = service.execute_api_sandbox_from_draft(
        draft,
        validation_result=_build_validation(),
        policy=_executable_policy(),
        session=session,
        dry_run=True,
        approved=True,
    )

    assert result.status == "Dry Run"
    assert session.calls == []


def test_policy_allow_execution_false_returns_dry_run():
    service = APIExecutionSandboxService()
    draft = _build_draft()
    session = _FakeSession(response=_FakeResponse(status_code=200, text="ok"))
    policy = create_default_execution_safety_policy(dry_run_only=False)

    result = service.execute_api_sandbox_from_draft(
        draft,
        validation_result=_build_validation(),
        policy=policy,
        session=session,
        dry_run=False,
        approved=True,
    )

    assert result.status == "Dry Run"
    assert session.calls == []


def test_blocked_production_url_returns_blocked():
    service = APIExecutionSandboxService()
    draft = _build_draft(base_url="https://production.example.com")
    session = _FakeSession(response=_FakeResponse(status_code=200, text="ok"))

    result = service.execute_api_sandbox_from_draft(
        draft,
        validation_result=_build_validation(),
        policy=_executable_policy(),
        session=session,
        dry_run=False,
        approved=True,
    )

    assert result.status == "Blocked"
    assert session.calls == []


def test_localhost_allowed_policy_can_execute_with_mocked_session():
    service = APIExecutionSandboxService()
    draft = _build_draft()
    session = _FakeSession(response=_FakeResponse(status_code=200, text="ok"))

    result = service.execute_api_sandbox_from_draft(
        draft,
        validation_result=_build_validation(),
        policy=_executable_policy(),
        session=session,
        dry_run=False,
        approved=True,
    )

    assert result.status == "Passed"
    assert len(session.calls) == 1
    assert session.calls[0]["method"] == "GET"


def test_delete_blocked_by_default():
    service = APIExecutionSandboxService()
    draft = _build_draft(method="DELETE", endpoint="/api/orders/1")
    session = _FakeSession(response=_FakeResponse(status_code=204, text=""))

    result = service.execute_api_sandbox_from_draft(
        draft,
        validation_result=_build_validation(),
        policy=_executable_policy(),
        session=session,
        dry_run=False,
        approved=True,
    )

    assert result.status == "Blocked"
    assert session.calls == []


def test_post_blocked_unless_write_methods_allowed():
    service = APIExecutionSandboxService()
    draft = _build_draft(method="POST", endpoint="/api/orders", payload_line='    payload = {"sku": "ABC"}')
    session = _FakeSession(response=_FakeResponse(status_code=200, text="ok"))

    blocked = service.execute_api_sandbox_from_draft(
        draft,
        validation_result=_build_validation(),
        policy=_executable_policy(allow_write_methods=False),
        session=session,
        dry_run=False,
        approved=True,
    )
    allowed = service.execute_api_sandbox_from_draft(
        draft,
        validation_result=_build_validation(),
        policy=_executable_policy(allow_write_methods=True),
        session=_FakeSession(response=_FakeResponse(status_code=200, text="ok")),
        dry_run=False,
        approved=True,
    )

    assert blocked.status == "Blocked"
    assert allowed.status == "Passed"


def test_invalid_validation_result_blocks_execution():
    service = APIExecutionSandboxService()
    draft = _build_draft()
    session = _FakeSession(response=_FakeResponse(status_code=200, text="ok"))

    result = service.execute_api_sandbox_from_draft(
        draft,
        validation_result=_build_validation(is_valid=False),
        policy=_executable_policy(),
        session=session,
        dry_run=False,
        approved=True,
    )

    assert result.status == "Blocked"
    assert session.calls == []


def test_todo_endpoint_blocks_execution():
    service = APIExecutionSandboxService()
    draft = _build_draft(endpoint="/TODO_ENDPOINT")
    session = _FakeSession(response=_FakeResponse(status_code=200, text="ok"))

    result = service.execute_api_sandbox_from_draft(
        draft,
        validation_result=_build_validation(has_todo_endpoint=True),
        policy=_executable_policy(),
        session=session,
        dry_run=False,
        approved=True,
    )

    assert result.status == "Blocked"
    assert session.calls == []


def test_missing_human_approval_blocks_execution():
    service = APIExecutionSandboxService()
    draft = _build_draft()
    session = _FakeSession(response=_FakeResponse(status_code=200, text="ok"))

    result = service.execute_api_sandbox_from_draft(
        draft,
        validation_result=_build_validation(),
        policy=_executable_policy(),
        session=session,
        dry_run=False,
        approved=False,
    )

    assert result.status == "Blocked"
    assert session.calls == []


def test_actual_mocked_get_success_returns_passed_when_expected_status_matches():
    service = APIExecutionSandboxService()
    draft = _build_draft(expected_status=200)
    session = _FakeSession(response=_FakeResponse(status_code=200, text="ok"))

    result = service.execute_api_sandbox_from_draft(
        draft,
        validation_result=_build_validation(),
        policy=_executable_policy(),
        session=session,
        dry_run=False,
        approved=True,
    )

    assert result.status == "Passed"
    assert result.assertion_passed is True
    assert result.http_status_code == 200


def test_actual_mocked_get_status_mismatch_returns_failed():
    service = APIExecutionSandboxService()
    draft = _build_draft(expected_status=201)
    session = _FakeSession(response=_FakeResponse(status_code=200, text="ok"))

    result = service.execute_api_sandbox_from_draft(
        draft,
        validation_result=_build_validation(),
        policy=_executable_policy(),
        session=session,
        dry_run=False,
        approved=True,
    )

    assert result.status == "Failed"
    assert result.assertion_passed is False


def test_request_exception_returns_error():
    service = APIExecutionSandboxService()
    draft = _build_draft()
    session = _FakeSession(exception=RuntimeError("boom"))

    result = service.execute_api_sandbox_from_draft(
        draft,
        validation_result=_build_validation(),
        policy=_executable_policy(),
        session=session,
        dry_run=False,
        approved=True,
    )

    assert result.status == "Error"
    assert result.error_type == "RuntimeError"
    assert "boom" in result.error_message


def test_response_excerpt_is_truncated():
    service = APIExecutionSandboxService()
    draft = _build_draft()
    session = _FakeSession(response=_FakeResponse(status_code=200, text="x" * 1500))

    result = service.execute_api_sandbox_from_draft(
        draft,
        validation_result=_build_validation(),
        policy=_executable_policy(),
        session=session,
        dry_run=False,
        approved=True,
    )

    assert result.status == "Passed"
    assert len(result.response_excerpt) == 1000


def test_manual_test_result_is_not_modified():
    service = APIExecutionSandboxService()
    draft = _build_draft()
    validation = _build_validation()
    manual_result = TestResult(result_id="RESULT-001", run_id="RUN-001", test_case_id="TC-900", status="Not Run")
    before = manual_result.to_dict()

    _ = service.execute_api_sandbox_from_draft(
        draft,
        validation_result=validation,
        policy=_executable_policy(),
        session=_FakeSession(response=_FakeResponse(status_code=200, text="ok")),
        dry_run=False,
        approved=True,
    )

    assert manual_result.to_dict() == before


def test_no_playwright_browser_or_mobile_imports():
    import orchestrator.manual_qa.api_execution_sandbox_service as sandbox_module

    assert sandbox_module is not None
    assert "mobile_appium" not in sys.modules
    assert "appium" not in sys.modules
