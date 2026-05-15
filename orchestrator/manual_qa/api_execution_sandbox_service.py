"""Safe API-only sandbox execution prototype for Manual QA draft artifacts."""

from __future__ import annotations

import ast
import json
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Sequence

from orchestrator.manual_qa.execution_preflight_service import ExecutionPreflightService
from orchestrator.manual_qa.execution_safety_service import ExecutionSafetyService
from orchestrator.manual_qa.models import (
    APIExecutionLogEntry,
    APIExecutionRequest,
    APIExecutionResult,
    APIScriptValidationResult,
    APITestScriptDraft,
    ExecutionPreflightResult,
    ExecutionSafetyPolicy,
    ExecutionTarget,
)
from orchestrator.manual_qa.workspace_service import ManualQAWorkspaceService


class APIExecutionSandboxService:
    """Build and optionally execute tightly gated API sandbox requests."""

    _BASE_TIME = datetime(2024, 1, 18, 0, 0, 0)
    _BLOCKED_KEYWORDS = ("production", "prod", "live", "payment-live", "real-bank")
    _WRITE_METHODS = {"POST", "PUT", "PATCH"}
    _DELETE_METHODS = {"DELETE"}
    _MAX_RESPONSE_EXCERPT = 1000

    def __init__(self) -> None:
        self._workspace_service = ManualQAWorkspaceService()
        self._safety_service = ExecutionSafetyService()
        self._preflight_service = ExecutionPreflightService()
        self._next_request_number = 1
        self._next_log_number = 1
        self._next_execution_number = 1
        self._next_timestamp_offset = 0

    def build_api_execution_request(
        self,
        draft: APITestScriptDraft,
        *,
        validation_result: APIScriptValidationResult | None = None,
        policy: ExecutionSafetyPolicy,
        preflight_result: ExecutionPreflightResult | None = None,
        override_base_url: str | None = None,
        dry_run: bool | None = None,
        approved: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> APIExecutionRequest:
        extracted = self._extract_request_parts(draft)
        method = extracted["method"] or "GET"
        base_url = str(override_base_url or extracted["base_url"])
        endpoint = str(extracted["endpoint"])
        expected_status = extracted["expected_status"]
        request_metadata = {
            "assertion_expected_status": expected_status,
            "approved": approved,
            "validation_is_valid": validation_result.is_valid if validation_result is not None else None,
            "method_extracted": extracted["method_extracted"],
            **dict(metadata or {}),
        }
        request = APIExecutionRequest(
            request_id=f"API-EXEC-REQ-{self._next_request_number:03d}",
            draft_id=draft.draft_id,
            test_case_id=draft.test_case_id,
            file_name=draft.file_name,
            method=method,
            base_url=base_url,
            endpoint=endpoint,
            headers=extracted["headers"],
            payload=extracted["payload"],
            timeout_seconds=policy.timeout_seconds,
            policy_id=policy.policy_id,
            preflight_id=preflight_result.preflight_id if preflight_result is not None else "",
            dry_run=policy.dry_run_only if dry_run is None else bool(dry_run),
            metadata=request_metadata,
            created_at=self._next_timestamp(),
        )
        self._next_request_number += 1
        return request

    def execute_api_sandbox_request(
        self,
        request: APIExecutionRequest,
        *,
        policy: ExecutionSafetyPolicy,
        preflight_result: ExecutionPreflightResult | None = None,
        session: Any | None = None,
    ) -> APIExecutionResult:
        logs: list[APIExecutionLogEntry] = []
        expected_status = request.metadata.get("assertion_expected_status")
        approved = bool(request.metadata.get("approved", False))

        if request.method == "GET" and not request.metadata.get("method_extracted", True):
            logs.append(self._log("Warning", "HTTP method was missing and defaulted to GET."))
        if expected_status is None:
            logs.append(self._log("Warning", "Expected status assertion was not detected in the draft."))

        blocked_reason = self._blocked_reason(request, policy=policy, approved=approved)
        if blocked_reason:
            logs.append(self._log("Error", blocked_reason))
            return self._result(
                request,
                status="Blocked",
                logs=logs,
                assertion_expected_status=expected_status,
                error_type="PolicyBlocked",
                error_message=blocked_reason,
            )

        if preflight_result is not None and preflight_result.decision == "Blocked":
            logs.append(self._log("Error", "Execution blocked by current preflight result."))
            return self._result(
                request,
                status="Blocked",
                logs=logs,
                assertion_expected_status=expected_status,
                error_type="PreflightBlocked",
                error_message="Execution blocked by current preflight result.",
            )

        if request.dry_run or not policy.allow_execution:
            reason = "Dry-run only mode; request was not sent."
            logs.append(self._log("Info", reason))
            return self._result(
                request,
                status="Dry Run",
                logs=logs,
                assertion_expected_status=expected_status,
                error_message=reason,
            )

        client = session if session is not None else self._create_default_session()
        url = self._compose_url(request.base_url, request.endpoint)
        payload = request.payload if request.payload else None
        start = time.perf_counter_ns()
        try:
            logs.append(self._log("Info", f"Executing sandbox request {request.method} {url}"))
            response = client.request(
                request.method,
                url,
                headers=dict(request.headers),
                json=payload,
                timeout=request.timeout_seconds,
            )
            duration_ms = int((time.perf_counter_ns() - start) / 1_000_000)
            response_text = self._truncate_text(getattr(response, "text", ""))
            http_status_code = int(getattr(response, "status_code", 0) or 0)
            assertion_passed = None if expected_status is None else http_status_code == int(expected_status)
            if expected_status is not None and assertion_passed:
                logs.append(self._log("Info", f"Expected HTTP status {expected_status} matched."))
                status = "Passed"
            else:
                if expected_status is None:
                    logs.append(
                        self._log("Warning", "No expected status was available; result cannot be treated as passed.")
                    )
                else:
                    logs.append(
                        self._log(
                            "Warning",
                            f"Expected HTTP status {expected_status} but received {http_status_code}.",
                        )
                    )
                status = "Failed"
            return self._result(
                request,
                status=status,
                logs=logs,
                http_status_code=http_status_code,
                duration_ms=duration_ms,
                response_excerpt=response_text,
                assertion_expected_status=expected_status,
                assertion_passed=assertion_passed,
                metadata={"sandbox_only": True, "executed_url": url},
            )
        except Exception as exc:
            duration_ms = int((time.perf_counter_ns() - start) / 1_000_000)
            logs.append(self._log("Error", f"Sandbox request failed: {exc.__class__.__name__}: {exc}"))
            return self._result(
                request,
                status="Error",
                logs=logs,
                duration_ms=duration_ms,
                assertion_expected_status=expected_status,
                error_type=exc.__class__.__name__,
                error_message=str(exc),
                metadata={"sandbox_only": True},
            )

    def execute_api_sandbox_from_draft(
        self,
        draft: APITestScriptDraft,
        *,
        validation_result: APIScriptValidationResult | None = None,
        policy: ExecutionSafetyPolicy,
        preflight_result: ExecutionPreflightResult | None = None,
        session: Any | None = None,
        override_base_url: str | None = None,
        dry_run: bool | None = None,
        approved: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> APIExecutionResult:
        current_preflight = self._current_preflight_result(
            draft,
            validation_result=validation_result,
            policy=policy,
            provided_preflight_result=preflight_result,
            override_base_url=override_base_url,
            approved=approved,
        )
        request = self.build_api_execution_request(
            draft,
            validation_result=validation_result,
            policy=policy,
            preflight_result=current_preflight,
            override_base_url=override_base_url,
            dry_run=dry_run,
            approved=approved,
            metadata=metadata,
        )
        return self.execute_api_sandbox_request(
            request,
            policy=policy,
            preflight_result=current_preflight,
            session=session,
        )

    def execute_api_sandbox_from_workspace(
        self,
        workspace_path: str | Path,
        *,
        policy: ExecutionSafetyPolicy,
        session: Any | None = None,
        override_base_url: str | None = None,
        dry_run: bool | None = None,
        approved: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> list[APIExecutionResult]:
        workspace = Path(workspace_path)
        draft_path = workspace / "script_drafts" / "api" / "api_script_drafts.json"
        validation_path = workspace / "script_drafts" / "api" / "api_script_validation.json"
        if not draft_path.exists():
            raise FileNotFoundError(f"API script drafts file does not exist: {draft_path}")

        drafts = self._load_api_drafts(draft_path)
        validations = self._load_api_validation_results(validation_path)
        validations_by_draft_id = {item.draft_id: item for item in validations}
        preflight_results_by_draft_id = self._load_preflight_results_by_draft_id(
            workspace / "reports" / "execution_preflight_plan.json"
        )

        results: list[APIExecutionResult] = []
        for draft in drafts:
            results.append(
                self.execute_api_sandbox_from_draft(
                    draft,
                    validation_result=validations_by_draft_id.get(draft.draft_id),
                    policy=policy,
                    preflight_result=preflight_results_by_draft_id.get(draft.draft_id),
                    session=session,
                    override_base_url=override_base_url,
                    dry_run=dry_run,
                    approved=approved,
                    metadata=metadata,
                )
            )
        return results

    def _current_preflight_result(
        self,
        draft: APITestScriptDraft,
        *,
        validation_result: APIScriptValidationResult | None,
        policy: ExecutionSafetyPolicy,
        provided_preflight_result: ExecutionPreflightResult | None,
        override_base_url: str | None,
        approved: bool,
    ) -> ExecutionPreflightResult:
        extracted = self._extract_request_parts(draft)
        target = ExecutionTarget(
            target_id="EXEC-TARGET-API-RUNTIME",
            script_type="api",
            draft_id=draft.draft_id,
            file_name=draft.file_name,
            package_status=str(
                (provided_preflight_result.metadata.get("package_status") if provided_preflight_result is not None else "")
                or draft.metadata.get("package_status", "Ready for Review")
            ),
            validation_status=self._validation_status(validation_result),
            base_url=str(override_base_url or extracted["base_url"]),
            method=str(extracted["method"] or "GET").upper(),
            endpoint_or_page=str(extracted["endpoint"]),
            has_todos=self._has_todos(draft, extracted["endpoint"]),
            has_critical_todos=self._has_critical_todos(draft, extracted["endpoint"]),
            metadata={
                "human_approval": approved,
                "browser_execution_requested": False,
            },
        )
        return self._preflight_service.preflight_execution_target(target, policy=policy)

    def _blocked_reason(
        self,
        request: APIExecutionRequest,
        *,
        policy: ExecutionSafetyPolicy,
        approved: bool,
    ) -> str:
        method = str(request.method or "").upper()
        endpoint = str(request.endpoint or "")
        base_url = str(request.base_url or "")
        validation_is_valid = request.metadata.get("validation_is_valid")

        if "TODO" in endpoint:
            return "Execution blocked because the endpoint still contains a TODO placeholder."
        if any(keyword in base_url.lower() for keyword in self._BLOCKED_KEYWORDS):
            return f"Execution blocked because base URL '{base_url}' matches a blocked keyword."
        if not self._safety_service.is_base_url_allowed(policy, base_url):
            return f"Execution blocked because base URL '{base_url}' is not allowed by policy."
        if method in self._DELETE_METHODS and not policy.allow_delete_methods:
            return "Execution blocked because DELETE methods are not allowed by policy."
        if method in self._WRITE_METHODS and not policy.allow_write_methods:
            return f"Execution blocked because {method} write methods are not allowed by policy."
        if validation_is_valid is False:
            return "Execution blocked because the API draft validation result is invalid."
        if policy.require_human_approval and not approved and not request.dry_run:
            return "Execution blocked because human approval was not provided."
        return ""

    def _extract_request_parts(self, draft: APITestScriptDraft) -> dict[str, Any]:
        metadata = draft.metadata if isinstance(draft.metadata, dict) else {}
        script_content = str(draft.script_content or "")

        method_from_metadata = str(metadata.get("http_method", "")).strip().upper()
        method = method_from_metadata or self._extract_method(script_content) or "GET"
        endpoint = str(metadata.get("endpoint", "")).strip() or self._extract_endpoint(script_content)
        base_url = str(metadata.get("base_url", "")).strip() or self._extract_base_url(script_content)
        expected_status = self._extract_expected_status(script_content)
        headers = self._extract_headers(script_content)
        payload = self._extract_payload(script_content)

        return {
            "method": method,
            "endpoint": endpoint,
            "base_url": base_url,
            "expected_status": expected_status,
            "headers": headers,
            "payload": payload,
            "method_extracted": bool(method_from_metadata or self._extract_method(script_content)),
        }

    def _extract_method(self, script_content: str) -> str:
        match = re.search(r"requests\.(get|post|put|patch|delete)\(", str(script_content or ""), re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return ""

    def _extract_endpoint(self, script_content: str) -> str:
        direct_match = re.search(r'BASE_URL\s*\+\s*"([^"]+)"', str(script_content or ""))
        if direct_match:
            return direct_match.group(1)
        path_match = re.search(r'requests\.[a-z]+\([^,]*"(/[^"]*)"', str(script_content or ""), re.IGNORECASE)
        if path_match:
            return path_match.group(1)
        return ""

    def _extract_base_url(self, script_content: str) -> str:
        match = re.search(
            r'BASE_URL\s*=\s*os\.getenv\(\s*"[^"]+"\s*,\s*"([^"]+)"\s*\)',
            str(script_content or ""),
        )
        if match:
            return match.group(1)
        return ""

    def _extract_expected_status(self, script_content: str) -> int | None:
        match = re.search(r"assert\s+response\.status_code\s*==\s*(\d+)", str(script_content or ""))
        if match:
            return int(match.group(1))
        return None

    def _extract_headers(self, script_content: str) -> dict[str, Any]:
        return self._extract_dict_assignment(script_content, "headers")

    def _extract_payload(self, script_content: str) -> dict[str, Any]:
        payload = self._extract_dict_assignment(script_content, "payload")
        return payload if isinstance(payload, dict) else {}

    def _extract_dict_assignment(self, script_content: str, variable_name: str) -> dict[str, Any]:
        match = re.search(rf"{variable_name}\s*=\s*(\{{.*?\}})", str(script_content or ""), re.DOTALL)
        if not match:
            return {}
        try:
            value = ast.literal_eval(match.group(1))
        except (ValueError, SyntaxError):
            return {}
        return value if isinstance(value, dict) else {}

    def _has_todos(self, draft: APITestScriptDraft, endpoint: str) -> bool:
        combined = "\n".join(
            [
                str(draft.script_content or ""),
                str(endpoint or ""),
                json.dumps(draft.metadata or {}, sort_keys=True),
            ]
        )
        return "TODO" in combined

    def _has_critical_todos(self, draft: APITestScriptDraft, endpoint: str) -> bool:
        combined = "\n".join(
            [
                str(draft.script_content or ""),
                str(endpoint or ""),
                json.dumps(draft.metadata or {}, sort_keys=True),
            ]
        )
        return any(token in combined for token in ("TODO_ENDPOINT", '"TODO": "payload"'))

    def _validation_status(self, validation_result: APIScriptValidationResult | None) -> str:
        if validation_result is None:
            return "Missing"
        if not validation_result.is_valid:
            return "Invalid"
        if validation_result.has_todo_endpoint or validation_result.has_todo_payload:
            return "Needs Attention"
        if any(
            (item.severity if hasattr(item, "severity") else str(item.get("severity", ""))) == "Warning"
            for item in validation_result.issues
        ):
            return "Needs Attention"
        return "Valid"

    def _compose_url(self, base_url: str, endpoint: str) -> str:
        if endpoint.startswith("http://") or endpoint.startswith("https://"):
            return endpoint
        return f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"

    def _truncate_text(self, text: str) -> str:
        raw = str(text or "")
        return raw[: self._MAX_RESPONSE_EXCERPT]

    def _result(
        self,
        request: APIExecutionRequest,
        *,
        status: str,
        logs: Sequence[APIExecutionLogEntry],
        http_status_code: int | None = None,
        duration_ms: int = 0,
        response_excerpt: str = "",
        error_type: str = "",
        error_message: str = "",
        assertion_expected_status: int | None = None,
        assertion_passed: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> APIExecutionResult:
        result = APIExecutionResult(
            execution_id=f"API-EXEC-RESULT-{self._next_execution_number:03d}",
            request=request,
            status=status,
            http_status_code=http_status_code,
            duration_ms=duration_ms,
            response_excerpt=response_excerpt,
            error_type=error_type,
            error_message=error_message,
            assertion_expected_status=assertion_expected_status,
            assertion_passed=assertion_passed,
            logs=list(logs),
            executed_at=self._next_timestamp(),
            metadata={"sandbox_only": True, **dict(metadata or {})},
        )
        self._next_execution_number += 1
        return result

    def _log(self, level: str, message: str, *, metadata: dict[str, Any] | None = None) -> APIExecutionLogEntry:
        entry = APIExecutionLogEntry(
            log_id=f"API-EXEC-LOG-{self._next_log_number:03d}",
            level=level,
            message=message,
            metadata=dict(metadata or {}),
            created_at=self._next_timestamp(),
        )
        self._next_log_number += 1
        return entry

    def _load_api_drafts(self, path: Path) -> list[APITestScriptDraft]:
        payload = self._workspace_service.read_json(path)
        if not isinstance(payload, list):
            return []
        return [APITestScriptDraft(**item) for item in payload if isinstance(item, dict)]

    def _load_api_validation_results(self, path: Path) -> list[APIScriptValidationResult]:
        if not path.exists():
            return []
        payload = self._workspace_service.read_json(path)
        if not isinstance(payload, list):
            return []
        results: list[APIScriptValidationResult] = []
        for item in payload:
            if not isinstance(item, dict):
                continue
            data = dict(item)
            data["issues"] = item.get("issues", [])
            results.append(APIScriptValidationResult(**data))
        return results

    def _load_preflight_results_by_draft_id(self, path: Path) -> dict[str, ExecutionPreflightResult]:
        if not path.exists():
            return {}
        payload = self._workspace_service.read_json(path)
        if not isinstance(payload, dict):
            return {}
        targets = payload.get("targets", [])
        results = payload.get("preflight_results", [])
        if not isinstance(targets, list) or not isinstance(results, list):
            return {}

        draft_id_by_target_id = {
            str(item.get("target_id", "")): str(item.get("draft_id", ""))
            for item in targets
            if isinstance(item, dict)
        }
        mapped: dict[str, ExecutionPreflightResult] = {}
        for item in results:
            if not isinstance(item, dict):
                continue
            draft_id = draft_id_by_target_id.get(str(item.get("target_id", "")), "")
            if not draft_id:
                continue
            result = ExecutionPreflightResult(
                preflight_id=str(item.get("preflight_id", "")),
                target_id=str(item.get("target_id", "")),
                script_type=str(item.get("script_type", "")),
                decision=str(item.get("decision", "")),
                is_allowed=bool(item.get("is_allowed", False)),
                issues=[],
                risk_level=str(item.get("risk_level", "")),
                recommended_action=str(item.get("recommended_action", "")),
                metadata=item.get("metadata", {}) if isinstance(item.get("metadata"), dict) else {},
                created_at=item.get("created_at"),
            )
            mapped[draft_id] = result
        return mapped

    def _create_default_session(self) -> Any:
        import requests  # type: ignore

        return requests.Session()

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


def build_api_execution_request(
    draft: APITestScriptDraft,
    *,
    validation_result: APIScriptValidationResult | None = None,
    policy: ExecutionSafetyPolicy,
    preflight_result: ExecutionPreflightResult | None = None,
    override_base_url: str | None = None,
    dry_run: bool | None = None,
    approved: bool = False,
    metadata: dict[str, Any] | None = None,
) -> APIExecutionRequest:
    """Convenience wrapper for building a gated API sandbox execution request."""

    return APIExecutionSandboxService().build_api_execution_request(
        draft,
        validation_result=validation_result,
        policy=policy,
        preflight_result=preflight_result,
        override_base_url=override_base_url,
        dry_run=dry_run,
        approved=approved,
        metadata=metadata,
    )


def execute_api_sandbox_request(
    request: APIExecutionRequest,
    *,
    policy: ExecutionSafetyPolicy,
    preflight_result: ExecutionPreflightResult | None = None,
    session: Any | None = None,
) -> APIExecutionResult:
    """Convenience wrapper for executing a gated API sandbox request."""

    return APIExecutionSandboxService().execute_api_sandbox_request(
        request,
        policy=policy,
        preflight_result=preflight_result,
        session=session,
    )


def execute_api_sandbox_from_draft(
    draft: APITestScriptDraft,
    *,
    validation_result: APIScriptValidationResult | None = None,
    policy: ExecutionSafetyPolicy,
    preflight_result: ExecutionPreflightResult | None = None,
    session: Any | None = None,
    override_base_url: str | None = None,
    dry_run: bool | None = None,
    approved: bool = False,
    metadata: dict[str, Any] | None = None,
) -> APIExecutionResult:
    """Convenience wrapper for building and executing one gated API sandbox request."""

    return APIExecutionSandboxService().execute_api_sandbox_from_draft(
        draft,
        validation_result=validation_result,
        policy=policy,
        preflight_result=preflight_result,
        session=session,
        override_base_url=override_base_url,
        dry_run=dry_run,
        approved=approved,
        metadata=metadata,
    )


def execute_api_sandbox_from_workspace(
    workspace_path: str | Path,
    *,
    policy: ExecutionSafetyPolicy,
    session: Any | None = None,
    override_base_url: str | None = None,
    dry_run: bool | None = None,
    approved: bool = False,
    metadata: dict[str, Any] | None = None,
) -> list[APIExecutionResult]:
    """Convenience wrapper for gated API sandbox execution over workspace draft artifacts."""

    return APIExecutionSandboxService().execute_api_sandbox_from_workspace(
        workspace_path,
        policy=policy,
        session=session,
        override_base_url=override_base_url,
        dry_run=dry_run,
        approved=approved,
        metadata=metadata,
    )
