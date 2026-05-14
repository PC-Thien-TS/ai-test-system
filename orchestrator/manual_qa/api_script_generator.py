"""Deterministic API test script draft generation for Manual QA."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Sequence
from urllib.parse import urlparse

from orchestrator.manual_qa.models import (
    APITestScriptDraft,
    ManualTestCase,
    ScriptGenerationReadiness,
)


class APITestScriptGenerator:
    """Generate pytest + requests API script drafts without executing them."""

    _BASE_TIME = datetime(2024, 1, 8, 0, 0, 0)
    _METHOD_PRIORITY = ("POST", "PUT", "PATCH", "DELETE", "GET")
    _STATUS_CODES = ("200", "201", "204", "400", "401", "403", "404", "409", "422", "500")
    _API_TERMS = ("api", "endpoint", "request", "response", "status code", "payload", "header", "token")

    def __init__(self) -> None:
        self._next_draft_number = 1
        self._next_timestamp_offset = 0

    def generate_api_script_draft(
        self,
        test_case: ManualTestCase,
        readiness: ScriptGenerationReadiness | None = None,
        base_url_env_var: str = "API_BASE_URL",
        base_url_default: str = "http://localhost:8000",
        auth_token_env_var: str = "API_AUTH_TOKEN",
        metadata: dict | None = None,
    ) -> APITestScriptDraft:
        if readiness is not None:
            if readiness.readiness_status == "Not Suitable":
                raise ValueError(
                    f"Test case '{test_case.test_case_id}' is not suitable for API draft generation."
                )
            if readiness.target_type != "api":
                raise ValueError(
                    f"Test case '{test_case.test_case_id}' is not classified as an API target."
                )
        elif not self._looks_api_like(test_case):
            raise ValueError(
                f"Test case '{test_case.test_case_id}' does not look API-like and cannot be drafted as an API script."
            )

        warnings: list[str] = []
        assumptions: list[str] = [
            "Draft only. Not executed or verified.",
            f"Assumes {base_url_env_var} points to a valid API base URL.",
        ]

        method = self._detect_method(test_case)
        if not method:
            method = "GET"
            warnings.append("HTTP method not detected. Defaulted to GET.")

        endpoint = self._detect_endpoint(test_case)
        if not endpoint:
            endpoint = "/TODO_ENDPOINT"
            warnings.append("Endpoint not detected. Added TODO endpoint placeholder.")

        status_code = self._detect_status_code(test_case)
        if status_code is None:
            status_code = 200
            warnings.append("Expected status code not detected. Defaulted to 200.")

        payload_text = self._detect_payload_hint(test_case)
        payload_needed = method in {"POST", "PUT", "PATCH"}
        if payload_needed and not payload_text:
            warnings.append("Request payload details were not detected. Added TODO payload placeholder.")

        if "token" in self._combined_text(test_case) or "auth" in self._combined_text(test_case):
            assumptions.append(f"Assumes optional bearer token can be provided by {auth_token_env_var}.")

        safe_name = self._safe_test_name(test_case)
        file_name = f"test_{safe_name}.py"
        script_content = self._render_script(
            test_case=test_case,
            method=method,
            endpoint=endpoint,
            status_code=status_code,
            payload_text=payload_text,
            payload_needed=payload_needed,
            base_url_env_var=base_url_env_var,
            base_url_default=base_url_default,
            auth_token_env_var=auth_token_env_var,
            warnings=warnings,
            readiness=readiness,
            safe_name=safe_name,
        )

        draft = APITestScriptDraft(
            draft_id=f"API-DRAFT-{self._next_draft_number:03d}",
            test_case_id=test_case.test_case_id,
            requirement_ids=list(test_case.requirement_ids),
            module=test_case.module,
            title=test_case.title,
            readiness_id=readiness.readiness_id if readiness is not None else "",
            target_type="api",
            framework="pytest-requests",
            language="python",
            file_name=file_name,
            script_content=script_content,
            status="Draft",
            warnings=warnings,
            assumptions=assumptions,
            metadata={
                "http_method": method,
                "endpoint": endpoint,
                "expected_status_code": status_code,
                "base_url_env_var": base_url_env_var,
                "auth_token_env_var": auth_token_env_var,
                **dict(metadata or {}),
            },
            created_at=self._next_timestamp(),
        )
        self._next_draft_number += 1
        return draft

    def generate_api_script_drafts(
        self,
        test_cases: Sequence[ManualTestCase],
        readiness_items: Sequence[ScriptGenerationReadiness] | None = None,
        base_url_env_var: str = "API_BASE_URL",
        base_url_default: str = "http://localhost:8000",
        auth_token_env_var: str = "API_AUTH_TOKEN",
        metadata: dict | None = None,
    ) -> list[APITestScriptDraft]:
        readiness_by_case_id = {
            item.test_case_id: item for item in (readiness_items or [])
        }
        drafts: list[APITestScriptDraft] = []
        for test_case in test_cases:
            readiness = readiness_by_case_id.get(test_case.test_case_id)
            try:
                drafts.append(
                    self.generate_api_script_draft(
                        test_case,
                        readiness=readiness,
                        base_url_env_var=base_url_env_var,
                        base_url_default=base_url_default,
                        auth_token_env_var=auth_token_env_var,
                        metadata=metadata,
                    )
                )
            except ValueError:
                continue
        return drafts

    def _render_script(
        self,
        *,
        test_case: ManualTestCase,
        method: str,
        endpoint: str,
        status_code: int,
        payload_text: str | None,
        payload_needed: bool,
        base_url_env_var: str,
        base_url_default: str,
        auth_token_env_var: str,
        warnings: Sequence[str],
        readiness: ScriptGenerationReadiness | None,
        safe_name: str,
    ) -> str:
        docstring_lines = [
            "Manual QA API script draft.",
            f"Source test case: {test_case.test_case_id}",
            f"Requirement IDs: {', '.join(test_case.requirement_ids) if test_case.requirement_ids else 'None'}",
            f"Readiness ID: {readiness.readiness_id if readiness is not None else 'N/A'}",
            "Status: Draft only. Not executed / not verified.",
        ]
        if warnings:
            docstring_lines.append(f"Warnings: {'; '.join(warnings)}")

        endpoint_expression = self._endpoint_expression(endpoint)
        request_call = f"requests.{method.lower()}({endpoint_expression}, headers=headers"
        lines = [
            "import os",
            "import requests",
            "",
            f'BASE_URL = os.getenv("{base_url_env_var}", "{base_url_default}")',
            f'{auth_token_env_var} = os.getenv("{auth_token_env_var}", "")',
            "",
            "",
            f"def test_{safe_name}():",
            '    """',
        ]
        lines.extend(f"    {line}" for line in docstring_lines)
        lines.extend(
            [
                '    """',
                "    headers = {}",
                f"    if {auth_token_env_var}:",
                f'        headers["Authorization"] = f"Bearer {{{auth_token_env_var}}}"',
            ]
        )
        if payload_needed:
            if payload_text:
                lines.extend(
                    [
                        "    # TODO: confirm payload fields before using this draft.",
                        f"    payload = {payload_text}",
                    ]
                )
            else:
                lines.extend(
                    [
                        "    # TODO: replace placeholder payload with real request data.",
                        '    payload = {"TODO": "payload"}',
                    ]
                )
            request_call += ", json=payload"
        request_call += ")"
        lines.extend(
            [
                "    # Manual QA draft only. Not executed by the generator.",
                f"    response = {request_call}",
                f"    assert response.status_code == {status_code}",
                "",
            ]
        )
        return "\n".join(lines)

    def _detect_method(self, test_case: ManualTestCase) -> str | None:
        text = self._combined_text(test_case).upper()
        for method in self._METHOD_PRIORITY:
            if re.search(rf"\b{method}\b", text):
                return method
        method_hints = {
            "POST": ("create", "submit"),
            "PUT": ("replace",),
            "PATCH": ("update", "modify"),
            "DELETE": ("delete", "remove"),
            "GET": ("fetch", "retrieve", "search", "list", "read"),
        }
        lower_text = self._combined_text(test_case)
        for method, hints in method_hints.items():
            if any(hint in lower_text for hint in hints):
                return method
        return None

    def _detect_endpoint(self, test_case: ManualTestCase) -> str | None:
        text = self._combined_text(test_case)
        url_match = re.search(r"https?://[^\s'\"`]+", text)
        if url_match:
            parsed = urlparse(url_match.group(0))
            path = parsed.path or "/"
            if parsed.query:
                path = f"{path}?{parsed.query}"
            return path.rstrip(".,;:)")
        path_match = re.search(r"(/[a-z0-9._~!$&'()*+,;=:@%/-]+)", text)
        if path_match:
            return path_match.group(1).rstrip(".,;:)")
        return None

    def _detect_status_code(self, test_case: ManualTestCase) -> int | None:
        status_sources = [
            test_case.expected_result,
            " ".join(test_case.steps),
        ]
        for source in status_sources:
            for code in self._STATUS_CODES:
                if re.search(rf"\b{code}\b", source):
                    return int(code)
        return None

    def _detect_payload_hint(self, test_case: ManualTestCase) -> str | None:
        test_data = test_case.metadata.get("test_data")
        if isinstance(test_data, dict):
            return repr(dict(test_data))
        if isinstance(test_data, str) and test_data.strip():
            return repr({"TODO_input": test_data.strip()})
        payload_match = re.search(r"payload[:=]\s*([a-z0-9 _\-/@.]+)", self._combined_text(test_case))
        if payload_match:
            return repr({"TODO_payload_hint": payload_match.group(1).strip()})
        return None

    def _looks_api_like(self, test_case: ManualTestCase) -> bool:
        text = self._combined_text(test_case)
        return any(term in text for term in self._API_TERMS) or bool(re.search(r"/[a-z0-9/_-]+", text))

    def _combined_text(self, test_case: ManualTestCase) -> str:
        return " ".join(
            [
                test_case.module,
                test_case.title,
                test_case.expected_result,
                " ".join(test_case.steps),
                " ".join(test_case.preconditions),
                str(test_case.metadata.get("test_data", "")),
            ]
        ).lower()

    def _safe_test_name(self, test_case: ManualTestCase) -> str:
        base = f"{test_case.test_case_id}_{test_case.title}".lower()
        slug = re.sub(r"[^a-z0-9]+", "_", base).strip("_")
        return slug or "api_draft"

    def _endpoint_expression(self, endpoint: str) -> str:
        if endpoint.startswith("/"):
            return f'f"{{BASE_URL}}{endpoint}"'
        return repr(endpoint)

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


_DEFAULT_API_SCRIPT_GENERATOR = APITestScriptGenerator()


def generate_api_script_draft(
    test_case: ManualTestCase,
    readiness: ScriptGenerationReadiness | None = None,
    base_url_env_var: str = "API_BASE_URL",
    base_url_default: str = "http://localhost:8000",
    auth_token_env_var: str = "API_AUTH_TOKEN",
    metadata: dict | None = None,
) -> APITestScriptDraft:
    """Convenience wrapper for generating a single API script draft."""

    return _DEFAULT_API_SCRIPT_GENERATOR.generate_api_script_draft(
        test_case,
        readiness=readiness,
        base_url_env_var=base_url_env_var,
        base_url_default=base_url_default,
        auth_token_env_var=auth_token_env_var,
        metadata=metadata,
    )


def generate_api_script_drafts(
    test_cases: Sequence[ManualTestCase],
    readiness_items: Sequence[ScriptGenerationReadiness] | None = None,
    base_url_env_var: str = "API_BASE_URL",
    base_url_default: str = "http://localhost:8000",
    auth_token_env_var: str = "API_AUTH_TOKEN",
    metadata: dict | None = None,
) -> list[APITestScriptDraft]:
    """Convenience wrapper for generating API draft artifacts in input order."""

    return _DEFAULT_API_SCRIPT_GENERATOR.generate_api_script_drafts(
        test_cases,
        readiness_items=readiness_items,
        base_url_env_var=base_url_env_var,
        base_url_default=base_url_default,
        auth_token_env_var=auth_token_env_var,
        metadata=metadata,
    )
