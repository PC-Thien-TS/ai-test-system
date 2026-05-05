from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping

from orchestrator.root_cause_analysis import (
    ENVIRONMENT_ISSUE,
    FLAKY_TEST,
    KNOWN_BACKEND_DEFECT,
    PRODUCT_BUG,
    TEST_DATA_ISSUE,
    TEST_SCRIPT_ISSUE,
    UNKNOWN,
)


@dataclass(frozen=True)
class BugReportDraft:
    title: str
    severity: str
    priority: str
    root_cause_type: str
    summary: str
    environment: Any
    steps_to_reproduce: list[str]
    expected_result: str
    actual_result: str
    evidence: dict[str, Any]
    suspected_root_cause: str
    suggested_action: str
    labels: list[str]
    markdown: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BugReportGenerator:
    """Deterministically build a structured bug-report draft from RCA and failure signals."""

    def generate(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_payload(payload)
        severity, priority = self._map_severity_and_priority(normalized)
        title = self._build_title(normalized, severity)
        summary = self._build_summary(normalized)
        steps_to_reproduce = self._build_steps_to_reproduce(normalized)
        expected_result = self._build_expected_result(normalized)
        actual_result = self._build_actual_result(normalized)
        evidence = self._build_evidence(normalized)
        suspected_root_cause = self._build_suspected_root_cause(normalized)
        suggested_action = self._build_suggested_action(normalized)
        labels = self._build_labels(normalized, severity, priority)
        markdown = self._build_markdown(
            title=title,
            summary=summary,
            environment=normalized["environment"],
            steps_to_reproduce=steps_to_reproduce,
            expected_result=expected_result,
            actual_result=actual_result,
            evidence=evidence,
            suspected_root_cause=suspected_root_cause,
            suggested_action=suggested_action,
        )

        return BugReportDraft(
            title=title,
            severity=severity,
            priority=priority,
            root_cause_type=normalized["root_cause_type"],
            summary=summary,
            environment=normalized["environment"],
            steps_to_reproduce=steps_to_reproduce,
            expected_result=expected_result,
            actual_result=actual_result,
            evidence=evidence,
            suspected_root_cause=suspected_root_cause,
            suggested_action=suggested_action,
            labels=labels,
            markdown=markdown,
        ).to_dict()

    def _normalize_payload(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping")

        failure_context_raw = payload.get("failure_context")
        failure_context = self._mapping_or_empty(failure_context_raw)

        rca_result_raw = payload.get("rca_result")
        rca_result = self._mapping_or_empty(rca_result_raw)
        rca_signals = self._mapping_or_empty(rca_result.get("signals"))

        environment = self._to_jsonable(payload.get("environment"))
        if environment in (None, ""):
            environment = "unknown"

        test_name = self._coalesce_str(
            payload.get("test_name"),
            failure_context.get("test_name"),
            failure_context.get("name"),
        )
        source_file = self._coalesce_str(
            payload.get("source_file"),
            failure_context.get("source_file"),
            failure_context.get("file"),
        )
        root_cause_type = self._coalesce_str(
            rca_result.get("root_cause_type"),
            payload.get("root_cause_type"),
            UNKNOWN,
        )

        return {
            "test_name": test_name,
            "source_file": source_file,
            "environment": environment,
            "environment_display": self._format_environment(environment),
            "failure_context": self._to_jsonable(failure_context),
            "rca_result": self._to_jsonable(rca_result),
            "evidence": self._to_jsonable(payload.get("evidence")),
            "steps_to_reproduce": self._to_jsonable(payload.get("steps_to_reproduce")),
            "expected_result": self._coalesce_str(
                payload.get("expected_result"),
                failure_context.get("expected_result"),
            ),
            "actual_result": self._coalesce_str(
                payload.get("actual_result"),
                failure_context.get("actual_result"),
            ),
            "root_cause_type": root_cause_type or UNKNOWN,
            "rca_severity": self._coalesce_str(rca_result.get("severity"), "medium").lower(),
            "rca_confidence": self._as_float(rca_result.get("confidence"), 0.0),
            "rca_reason": self._coalesce_str(rca_result.get("reason")),
            "rca_suggested_action": self._coalesce_str(rca_result.get("suggested_action")),
            "likely_owner": self._coalesce_str(rca_result.get("likely_owner")),
            "rca_signals": self._to_jsonable(rca_signals),
            "error_message": self._coalesce_str(
                failure_context.get("error_message"),
                failure_context.get("message"),
            ),
            "api_status_code": self._as_int(
                failure_context.get("api_status_code", rca_signals.get("api_status_code")),
                0,
            ),
            "api_response_text": self._coalesce_str(failure_context.get("api_response_text")),
            "mobile_failure_type": self._coalesce_str(
                failure_context.get("mobile_failure_type"),
                rca_signals.get("mobile_failure_type"),
            ),
            "locator_healing_applicable": bool(
                self._mapping_or_empty(failure_context.get("locator_healing_result")).get("healing_applicable")
                or rca_signals.get("locator_healing_applicable")
            ),
            "seen_count": self._as_int(rca_signals.get("seen_count"), 0),
        }

    def _map_severity_and_priority(self, payload: dict[str, Any]) -> tuple[str, str]:
        root_cause_type = payload["root_cause_type"]
        rca_severity = payload["rca_severity"]
        seen_count = payload["seen_count"]
        confidence = payload["rca_confidence"]

        if root_cause_type == PRODUCT_BUG:
            level = "High" if rca_severity == "high" else "Medium"
            return level, level

        if root_cause_type == KNOWN_BACKEND_DEFECT:
            level = "High" if rca_severity == "high" or seen_count >= 3 else "Medium"
            return level, level

        if root_cause_type == TEST_SCRIPT_ISSUE:
            level = "Medium" if payload["locator_healing_applicable"] or confidence >= 0.75 else "Low"
            return level, level

        if root_cause_type == ENVIRONMENT_ISSUE:
            return "Medium", "Medium"

        if root_cause_type in {FLAKY_TEST, TEST_DATA_ISSUE}:
            return "Medium", "Medium"

        if root_cause_type == UNKNOWN:
            level = "Medium" if confidence >= 0.5 else "Low"
            return level, level

        return "Medium", "Medium"

    def _build_title(self, payload: dict[str, Any], severity: str) -> str:
        test_name = payload["test_name"] or "unknown_test"
        environment = payload["environment_display"]
        return f"[{severity}][{payload['root_cause_type']}] {test_name} failure in {environment}"

    def _build_summary(self, payload: dict[str, Any]) -> str:
        test_name = payload["test_name"] or "The automated test"
        environment = payload["environment_display"]
        root_cause_type = payload["root_cause_type"]
        reason = payload["rca_reason"] or "Deterministic RCA did not produce a stronger explanation."
        return f"{test_name} failed in {environment} and was classified as {root_cause_type}. {reason}"

    def _build_steps_to_reproduce(self, payload: dict[str, Any]) -> list[str]:
        provided = payload["steps_to_reproduce"]
        if isinstance(provided, list) and provided:
            steps = [self._as_str(item) for item in provided if self._as_str(item)]
            if steps:
                return steps
        if isinstance(provided, str) and provided.strip():
            return [provided.strip()]

        steps = []
        if payload["test_name"]:
            steps.append(f"Run `{payload['test_name']}`.")
        else:
            steps.append("Run the affected automated test.")
        if payload["source_file"]:
            steps.append(f"Use the test source `{payload['source_file']}`.")
        steps.append(f"Execute the flow in `{payload['environment_display']}`.")
        steps.append("Observe the reported failure and collect the attached evidence.")
        return steps

    def _build_expected_result(self, payload: dict[str, Any]) -> str:
        if payload["expected_result"]:
            return payload["expected_result"]
        if payload["api_status_code"]:
            return "The request should complete successfully without unexpected 4xx/5xx failures."
        return "The automated test should complete successfully and match the expected product behavior."

    def _build_actual_result(self, payload: dict[str, Any]) -> str:
        if payload["actual_result"]:
            return payload["actual_result"]

        parts = []
        if payload["error_message"]:
            parts.append(payload["error_message"])
        if payload["api_status_code"]:
            parts.append(f"API status: {payload['api_status_code']}")
        if payload["api_response_text"]:
            parts.append(payload["api_response_text"])
        if payload["mobile_failure_type"]:
            parts.append(f"Mobile failure: {payload['mobile_failure_type']}")

        if not parts:
            return "The test failed without a richer captured actual-result description."
        return "Observed failure: " + " | ".join(parts)

    def _build_evidence(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "failure_context": payload["failure_context"],
            "rca_signals": payload["rca_signals"],
            "input_evidence": payload["evidence"],
        }

    def _build_suspected_root_cause(self, payload: dict[str, Any]) -> str:
        if payload["rca_reason"]:
            return payload["rca_reason"]
        return f"The failure was classified as {payload['root_cause_type']}, but the supporting RCA context is limited."

    def _build_suggested_action(self, payload: dict[str, Any]) -> str:
        if payload["rca_suggested_action"]:
            return payload["rca_suggested_action"]
        return "Review the failing run, confirm the classification, and gather more supporting evidence before escalation."

    def _build_labels(self, payload: dict[str, Any], severity: str, priority: str) -> list[str]:
        labels = [
            "auto-bug-report-v1",
            f"root-cause-{self._slug(payload['root_cause_type'])}",
            f"severity-{self._slug(severity)}",
            f"priority-{self._slug(priority)}",
        ]
        if payload["likely_owner"]:
            labels.append(f"owner-{self._slug(payload['likely_owner'])}")
        if payload["locator_healing_applicable"]:
            labels.append("locator-self-healing-signal")
        if payload["mobile_failure_type"]:
            labels.append("mobile-failure-signal")
        return labels

    def _build_markdown(
        self,
        *,
        title: str,
        summary: str,
        environment: Any,
        steps_to_reproduce: list[str],
        expected_result: str,
        actual_result: str,
        evidence: dict[str, Any],
        suspected_root_cause: str,
        suggested_action: str,
    ) -> str:
        lines = [
            "# Bug Title",
            title,
            "",
            summary,
            "",
            "## Environment",
            self._format_markdown_block(environment),
            "",
            "## Steps to Reproduce",
        ]
        for index, step in enumerate(steps_to_reproduce, start=1):
            lines.append(f"{index}. {step}")
        lines.extend(
            [
                "",
                "## Expected Result",
                expected_result,
                "",
                "## Actual Result",
                actual_result,
                "",
                "## Evidence",
                self._format_markdown_block(evidence),
                "",
                "## Suspected Root Cause",
                suspected_root_cause,
                "",
                "## Suggested Action",
                suggested_action,
            ]
        )
        return "\n".join(lines).strip()

    def _format_markdown_block(self, value: Any) -> str:
        if isinstance(value, Mapping):
            items = []
            for key, item_value in value.items():
                items.append(f"- **{key}**: {self._format_inline_value(item_value)}")
            return "\n".join(items) if items else "- none"
        if isinstance(value, list):
            return "\n".join(f"- {self._format_inline_value(item)}" for item in value) if value else "- none"
        text = self._format_inline_value(value)
        return text or "- none"

    def _format_inline_value(self, value: Any) -> str:
        if isinstance(value, Mapping):
            parts = [f"{key}={self._format_inline_value(item_value)}" for key, item_value in value.items()]
            return "; ".join(parts) if parts else "none"
        if isinstance(value, list):
            return ", ".join(self._format_inline_value(item) for item in value) if value else "none"
        text = self._as_str(value)
        return text or "none"

    def _format_environment(self, environment: Any) -> str:
        if isinstance(environment, Mapping):
            for key in ["name", "environment", "env"]:
                value = self._as_str(environment.get(key))
                if value:
                    return value
            rendered = self._format_inline_value(environment)
            return rendered if rendered != "none" else "unknown"
        if isinstance(environment, list):
            rendered = self._format_inline_value(environment)
            return rendered if rendered != "none" else "unknown"
        text = self._as_str(environment)
        return text or "unknown"

    def _mapping_or_empty(self, value: Any) -> Mapping[str, Any]:
        if isinstance(value, Mapping):
            return value
        return {}

    def _coalesce_str(self, *values: Any) -> str:
        for value in values:
            text = self._as_str(value)
            if text:
                return text
        return ""

    def _to_jsonable(self, value: Any) -> Any:
        if isinstance(value, Enum):
            return value.value
        if is_dataclass(value):
            return {key: self._to_jsonable(item) for key, item in asdict(value).items()}
        if isinstance(value, Mapping):
            return {str(key): self._to_jsonable(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._to_jsonable(item) for item in value]
        return value

    def _slug(self, value: str) -> str:
        return value.strip().lower().replace("_", "-").replace(" ", "-")

    def _as_str(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _as_float(self, value: Any, default: float) -> float:
        try:
            if value is None or value == "":
                return default
            return float(value)
        except (TypeError, ValueError):
            return default

    def _as_int(self, value: Any, default: int) -> int:
        try:
            if value is None or value == "":
                return default
            return int(value)
        except (TypeError, ValueError):
            return default


def generate_bug_report(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Generate a structured deterministic bug-report draft without creating a real ticket."""
    return BugReportGenerator().generate(payload)
