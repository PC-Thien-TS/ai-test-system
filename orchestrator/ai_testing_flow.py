from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Mapping

from orchestrator.bug_report_generator import generate_bug_report
from orchestrator.mobile_evidence_adapter import collect_mobile_exploration_evidence
from orchestrator.mobile_failure_classifier import classify_mobile_failure
from orchestrator.requirement_ingestion import ingest_requirement
from orchestrator.root_cause_analysis import analyze_root_cause
from orchestrator.script_generator import generate_pytest_script
from orchestrator.testcase_generator import generate_test_cases


@dataclass(frozen=True)
class RequirementToScriptFlowResult:
    normalized_requirement: dict[str, Any]
    test_cases: list[dict[str, Any]]
    generated_script: dict[str, Any]
    metadata: dict[str, Any]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FailureToBugReportFlowResult:
    root_cause: dict[str, Any]
    bug_report: dict[str, Any]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MobileFailureToBugReportFlowResult:
    mobile_evidence: dict[str, Any]
    mobile_failure: dict[str, Any]
    root_cause: dict[str, Any]
    bug_report: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AITestingFlow:
    """Thin orchestration layer that composes deterministic testing modules into reusable flows."""

    def requirement_to_script(
        self,
        raw_requirement_text: str,
        *,
        source_id: str | None = None,
        source_name: str | None = None,
    ) -> dict[str, Any]:
        normalized_requirement = ingest_requirement(
            raw_requirement_text,
            source_id=source_id,
            source_name=source_name,
        )
        test_cases = generate_test_cases(normalized_requirement)
        generated_script = generate_pytest_script(test_cases)
        warnings = self._build_requirement_warnings(normalized_requirement, test_cases)

        return RequirementToScriptFlowResult(
            normalized_requirement=normalized_requirement,
            test_cases=test_cases,
            generated_script=generated_script,
            metadata={
                "flow_type": "requirement_to_script",
                "source_id": source_id or "",
                "source_name": source_name or "",
                "requirement_id": normalized_requirement.get("requirement_id", ""),
                "test_case_count": len(test_cases),
                "generated_test_count": len(generated_script.get("generated_test_names", [])),
                "script_type": generated_script.get("script_type", ""),
                "framework": generated_script.get("framework", ""),
            },
            warnings=warnings,
        ).to_dict()

    def failure_to_bug_report(
        self,
        *,
        failure_context: Mapping[str, Any],
        locator_healing_result: Mapping[str, Any] | None = None,
        mobile_failure_result: Mapping[str, Any] | None = None,
        evidence: Any = None,
        test_name: str | None = None,
        source_file: str | None = None,
        environment: Any = None,
        steps_to_reproduce: list[str] | str | None = None,
        expected_result: str | None = None,
        actual_result: str | None = None,
    ) -> dict[str, Any]:
        normalized_failure_context = self._mapping_or_empty(failure_context)
        normalized_locator_result = self._mapping_or_empty(locator_healing_result)
        normalized_mobile_result = self._mapping_or_empty(mobile_failure_result)
        normalized_evidence = self._to_jsonable(evidence)

        rca_input = dict(normalized_failure_context)
        if normalized_locator_result:
            rca_input["locator_healing_result"] = dict(normalized_locator_result)
        if normalized_mobile_result:
            mobile_failure_type = self._as_str(normalized_mobile_result.get("failure_type"))
            if mobile_failure_type:
                rca_input["mobile_failure_type"] = mobile_failure_type
        if isinstance(normalized_evidence, Mapping):
            rca_input["evidence_summary"] = dict(normalized_evidence)

        root_cause = analyze_root_cause(rca_input)
        bug_report = generate_bug_report(
            {
                "test_name": test_name or normalized_failure_context.get("test_name"),
                "source_file": source_file or normalized_failure_context.get("source_file"),
                "environment": environment if environment is not None else normalized_failure_context.get("environment"),
                "failure_context": {
                    **dict(normalized_failure_context),
                    **({"locator_healing_result": dict(normalized_locator_result)} if normalized_locator_result else {}),
                    **(
                        {"mobile_failure_type": normalized_mobile_result.get("failure_type")}
                        if normalized_mobile_result.get("failure_type")
                        else {}
                    ),
                },
                "rca_result": root_cause,
                "evidence": {
                    "failure_context": self._to_jsonable(normalized_failure_context),
                    "locator_healing_result": self._to_jsonable(normalized_locator_result),
                    "mobile_failure_result": self._to_jsonable(normalized_mobile_result),
                    "input_evidence": normalized_evidence,
                },
                "steps_to_reproduce": steps_to_reproduce,
                "expected_result": expected_result,
                "actual_result": actual_result,
            }
        )

        return FailureToBugReportFlowResult(
            root_cause=root_cause,
            bug_report=bug_report,
            metadata={
                "flow_type": "failure_to_bug_report",
                "root_cause_type": root_cause.get("root_cause_type", ""),
                "has_locator_healing_result": bool(normalized_locator_result),
                "has_mobile_failure_result": bool(normalized_mobile_result),
                "has_evidence": evidence is not None,
            },
        ).to_dict()

    def mobile_failure_to_bug_report(
        self,
        payload: Mapping[str, Any] | Any,
        *,
        environment: Any = "mobile",
        test_name: str | None = None,
        source_file: str | None = None,
        steps_to_reproduce: list[str] | str | None = None,
        expected_result: str | None = None,
        actual_result: str | None = None,
        artifact_path: str | None = None,
    ) -> dict[str, Any]:
        mobile_evidence = collect_mobile_exploration_evidence(payload, artifact_path=artifact_path)
        mobile_failure = classify_mobile_failure(mobile_evidence)

        root_cause = analyze_root_cause(
            {
                "error_message": mobile_evidence.get("error") or mobile_evidence.get("failure_signal"),
                "mobile_failure_type": mobile_failure.get("failure_type"),
                "evidence_summary": mobile_evidence,
            }
        )

        run_id = self._as_str(mobile_evidence.get("run_id"))
        bug_report = generate_bug_report(
            {
                "test_name": test_name or self._build_mobile_test_name(run_id),
                "source_file": source_file,
                "environment": environment,
                "failure_context": {
                    "run_id": run_id,
                    "error_message": mobile_evidence.get("error") or mobile_evidence.get("failure_signal"),
                    "mobile_failure_type": mobile_failure.get("failure_type"),
                    "artifact_path": mobile_evidence.get("artifact_path"),
                },
                "rca_result": root_cause,
                "evidence": {
                    "mobile_evidence": mobile_evidence,
                    "mobile_failure": mobile_failure,
                },
                "steps_to_reproduce": steps_to_reproduce,
                "expected_result": expected_result,
                "actual_result": actual_result,
            }
        )

        return MobileFailureToBugReportFlowResult(
            mobile_evidence=mobile_evidence,
            mobile_failure=mobile_failure,
            root_cause=root_cause,
            bug_report=bug_report,
        ).to_dict()

    def _build_requirement_warnings(
        self,
        normalized_requirement: Mapping[str, Any],
        test_cases: list[Mapping[str, Any]],
    ) -> list[str]:
        warnings: list[str] = []
        unknowns = normalized_requirement.get("unknowns")
        if isinstance(unknowns, list):
            for item in unknowns:
                token = self._as_str(item)
                if token:
                    warnings.append(f"missing_{token}")
        if any(self._as_str(case.get("test_type")) == "fallback" for case in test_cases):
            warnings.append("fallback_test_case_generated")
        return list(dict.fromkeys(warnings))

    def _build_mobile_test_name(self, run_id: str) -> str:
        return f"mobile_exploration_run_{run_id}" if run_id else "mobile_exploration_run"

    def _mapping_or_empty(self, value: Any) -> Mapping[str, Any]:
        if isinstance(value, Mapping):
            return value
        return {}

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

    def _as_str(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()


def run_requirement_to_script_flow(
    raw_requirement_text: str,
    *,
    source_id: str | None = None,
    source_name: str | None = None,
) -> dict[str, Any]:
    """Compose requirement ingestion, test-case generation, and script generation."""
    return AITestingFlow().requirement_to_script(
        raw_requirement_text,
        source_id=source_id,
        source_name=source_name,
    )


def run_failure_to_bug_report_flow(
    *,
    failure_context: Mapping[str, Any],
    locator_healing_result: Mapping[str, Any] | None = None,
    mobile_failure_result: Mapping[str, Any] | None = None,
    evidence: Any = None,
    test_name: str | None = None,
    source_file: str | None = None,
    environment: Any = None,
    steps_to_reproduce: list[str] | str | None = None,
    expected_result: str | None = None,
    actual_result: str | None = None,
) -> dict[str, Any]:
    """Compose RCA and bug-report generation from a generic failure context."""
    return AITestingFlow().failure_to_bug_report(
        failure_context=failure_context,
        locator_healing_result=locator_healing_result,
        mobile_failure_result=mobile_failure_result,
        evidence=evidence,
        test_name=test_name,
        source_file=source_file,
        environment=environment,
        steps_to_reproduce=steps_to_reproduce,
        expected_result=expected_result,
        actual_result=actual_result,
    )


def run_mobile_failure_to_bug_report_flow(
    payload: Mapping[str, Any] | Any,
    *,
    environment: Any = "mobile",
    test_name: str | None = None,
    source_file: str | None = None,
    steps_to_reproduce: list[str] | str | None = None,
    expected_result: str | None = None,
    actual_result: str | None = None,
    artifact_path: str | None = None,
) -> dict[str, Any]:
    """Compose mobile evidence, mobile failure classification, RCA, and bug-report generation."""
    return AITestingFlow().mobile_failure_to_bug_report(
        payload,
        environment=environment,
        test_name=test_name,
        source_file=source_file,
        steps_to_reproduce=steps_to_reproduce,
        expected_result=expected_result,
        actual_result=actual_result,
        artifact_path=artifact_path,
    )
