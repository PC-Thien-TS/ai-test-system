from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from orchestrator.ai_testing_flow import (
    run_failure_to_bug_report_flow,
    run_mobile_failure_to_bug_report_flow,
    run_requirement_to_script_flow,
)
from orchestrator.locator_self_healing import suggest_locator_healing


INGEST_REQUIREMENT = "INGEST_REQUIREMENT"
GENERATE_TEST_CASES = "GENERATE_TEST_CASES"
GENERATE_SCRIPT = "GENERATE_SCRIPT"
ANALYZE_FAILURE = "ANALYZE_FAILURE"
SUGGEST_LOCATOR_HEALING = "SUGGEST_LOCATOR_HEALING"
GENERATE_BUG_REPORT = "GENERATE_BUG_REPORT"
ANALYZE_MOBILE_FAILURE = "ANALYZE_MOBILE_FAILURE"
SKIP_WITH_REASON = "SKIP_WITH_REASON"

PLAN_ONLY = "plan_only"
DRAFT_ARTIFACTS = "draft_artifacts"

ALL_ACTIONS = [
    INGEST_REQUIREMENT,
    GENERATE_TEST_CASES,
    GENERATE_SCRIPT,
    ANALYZE_FAILURE,
    SUGGEST_LOCATOR_HEALING,
    GENERATE_BUG_REPORT,
    ANALYZE_MOBILE_FAILURE,
    SKIP_WITH_REASON,
]


@dataclass(frozen=True)
class AgenticTestingResult:
    run_id: str
    selected_actions: list[str]
    skipped_actions: list[str]
    artifacts: dict[str, Any]
    decision_trace: list[dict[str, Any]]
    warnings: list[str]
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AgenticTestingEngine:
    """Deterministic decision loop that selects safe testing flows from the available inputs."""

    def run(
        self,
        *,
        requirement_text: str | None = None,
        failure_context: Mapping[str, Any] | None = None,
        mobile_artifact: Mapping[str, Any] | Any = None,
        locator_failure_payload: Mapping[str, Any] | None = None,
        mode: str | None = None,
        source_id: str | None = None,
        source_name: str | None = None,
        evidence: Any = None,
        environment: Any = None,
        test_name: str | None = None,
        source_file: str | None = None,
        steps_to_reproduce: list[str] | str | None = None,
        expected_result: str | None = None,
        actual_result: str | None = None,
        artifact_path: str | None = None,
    ) -> dict[str, Any]:
        normalized_mode, warnings = self._normalize_mode(mode)
        run_id = f"agentic-{uuid.uuid4().hex[:12]}"

        has_requirement = requirement_text is not None
        has_failure_context = failure_context is not None
        has_mobile_artifact = mobile_artifact is not None
        has_locator_payload = locator_failure_payload is not None

        selected_actions: list[str] = []
        decision_trace: list[dict[str, Any]] = []
        artifacts: dict[str, Any] = {}

        if not any([has_requirement, has_failure_context, has_mobile_artifact, has_locator_payload]):
            selected_actions.append(SKIP_WITH_REASON)
            decision_trace.append(
                self._trace(
                    SKIP_WITH_REASON,
                    decision="selected",
                    reason="No actionable input was provided to the agentic decision loop.",
                    executed=False,
                )
            )
            warnings.append("no_actionable_input")
            skipped_actions = [action for action in ALL_ACTIONS if action != SKIP_WITH_REASON]
            return AgenticTestingResult(
                run_id=run_id,
                selected_actions=selected_actions,
                skipped_actions=skipped_actions,
                artifacts={},
                decision_trace=decision_trace,
                warnings=self._dedupe(warnings),
                status="skipped",
            ).to_dict()

        if has_requirement:
            self._select(
                selected_actions,
                decision_trace,
                INGEST_REQUIREMENT,
                reason="Requirement text is available, so deterministic requirement ingestion should run.",
                executed=normalized_mode == DRAFT_ARTIFACTS,
            )
            self._select(
                selected_actions,
                decision_trace,
                GENERATE_TEST_CASES,
                reason="A normalized requirement enables deterministic test-case generation.",
                executed=normalized_mode == DRAFT_ARTIFACTS,
            )
            self._select(
                selected_actions,
                decision_trace,
                GENERATE_SCRIPT,
                reason="Generated test cases can be converted into a safe pytest skeleton.",
                executed=normalized_mode == DRAFT_ARTIFACTS,
            )

        if has_locator_payload:
            self._select(
                selected_actions,
                decision_trace,
                SUGGEST_LOCATOR_HEALING,
                reason="Locator-failure payload is available, so safe locator-healing suggestions can be produced.",
                executed=normalized_mode == DRAFT_ARTIFACTS,
            )

        if has_failure_context:
            self._select(
                selected_actions,
                decision_trace,
                ANALYZE_FAILURE,
                reason="Failure context is available, so RCA should classify the likely root cause.",
                executed=normalized_mode == DRAFT_ARTIFACTS,
            )
            self._select(
                selected_actions,
                decision_trace,
                GENERATE_BUG_REPORT,
                reason="A failure analysis result can be converted into a deterministic bug-report draft.",
                executed=normalized_mode == DRAFT_ARTIFACTS,
            )

        if has_mobile_artifact:
            self._select(
                selected_actions,
                decision_trace,
                ANALYZE_MOBILE_FAILURE,
                reason="Mobile artifact input is available, so mobile evidence and failure intelligence should run.",
                executed=normalized_mode == DRAFT_ARTIFACTS,
            )
            self._select(
                selected_actions,
                decision_trace,
                ANALYZE_FAILURE,
                reason="Mobile failure intelligence feeds deterministic RCA.",
                executed=normalized_mode == DRAFT_ARTIFACTS,
            )
            self._select(
                selected_actions,
                decision_trace,
                GENERATE_BUG_REPORT,
                reason="Mobile RCA output can be converted into a deterministic bug-report draft.",
                executed=normalized_mode == DRAFT_ARTIFACTS,
            )

        if normalized_mode == PLAN_ONLY:
            warnings.append("plan_only_no_artifacts_generated")
            skipped_actions = [action for action in ALL_ACTIONS if action not in selected_actions]
            return AgenticTestingResult(
                run_id=run_id,
                selected_actions=selected_actions,
                skipped_actions=skipped_actions,
                artifacts={},
                decision_trace=decision_trace,
                warnings=self._dedupe(warnings),
                status="planned",
            ).to_dict()

        locator_healing_result: dict[str, Any] | None = None
        if has_locator_payload:
            locator_healing_result = suggest_locator_healing(self._mapping_or_empty(locator_failure_payload))
            artifacts["locator_healing"] = locator_healing_result
            if not has_failure_context:
                warnings.append("locator_healing_generated_without_failure_analysis")

        if has_requirement:
            artifacts["requirement_to_script"] = run_requirement_to_script_flow(
                requirement_text or "",
                source_id=source_id,
                source_name=source_name,
            )

        if has_failure_context:
            artifacts["failure_to_bug_report"] = run_failure_to_bug_report_flow(
                failure_context=self._mapping_or_empty(failure_context),
                locator_healing_result=locator_healing_result,
                evidence=evidence,
                test_name=test_name,
                source_file=source_file,
                environment=environment,
                steps_to_reproduce=steps_to_reproduce,
                expected_result=expected_result,
                actual_result=actual_result,
            )

        if has_mobile_artifact:
            artifacts["mobile_failure_to_bug_report"] = run_mobile_failure_to_bug_report_flow(
                mobile_artifact,
                environment=environment if environment is not None else "mobile",
                test_name=test_name,
                source_file=source_file,
                steps_to_reproduce=steps_to_reproduce,
                expected_result=expected_result,
                actual_result=actual_result,
                artifact_path=artifact_path,
            )

        skipped_actions = [action for action in ALL_ACTIONS if action not in selected_actions]
        return AgenticTestingResult(
            run_id=run_id,
            selected_actions=selected_actions,
            skipped_actions=skipped_actions,
            artifacts=artifacts,
            decision_trace=decision_trace,
            warnings=self._dedupe(warnings),
            status="completed",
        ).to_dict()

    def _normalize_mode(self, mode: str | None) -> tuple[str, list[str]]:
        normalized = (mode or DRAFT_ARTIFACTS).strip().lower()
        if normalized in {PLAN_ONLY, DRAFT_ARTIFACTS}:
            return normalized, []
        return DRAFT_ARTIFACTS, [f"unknown_mode_defaulted_to_{DRAFT_ARTIFACTS}"]

    def _select(
        self,
        selected_actions: list[str],
        decision_trace: list[dict[str, Any]],
        action: str,
        *,
        reason: str,
        executed: bool,
    ) -> None:
        if action not in selected_actions:
            selected_actions.append(action)
        decision_trace.append(
            self._trace(
                action,
                decision="selected",
                reason=reason,
                executed=executed,
            )
        )

    def _trace(self, action: str, *, decision: str, reason: str, executed: bool) -> dict[str, Any]:
        return {
            "action": action,
            "decision": decision,
            "reason": reason,
            "executed": executed,
        }

    def _mapping_or_empty(self, value: Any) -> Mapping[str, Any]:
        if isinstance(value, Mapping):
            return value
        return {}

    def _dedupe(self, values: list[str]) -> list[str]:
        return list(dict.fromkeys(value for value in values if value))


def run_agentic_testing(
    *,
    requirement_text: str | None = None,
    failure_context: Mapping[str, Any] | None = None,
    mobile_artifact: Mapping[str, Any] | Any = None,
    locator_failure_payload: Mapping[str, Any] | None = None,
    mode: str | None = None,
    source_id: str | None = None,
    source_name: str | None = None,
    evidence: Any = None,
    environment: Any = None,
    test_name: str | None = None,
    source_file: str | None = None,
    steps_to_reproduce: list[str] | str | None = None,
    expected_result: str | None = None,
    actual_result: str | None = None,
    artifact_path: str | None = None,
) -> dict[str, Any]:
    """Run the deterministic agentic testing decision loop without executing external side effects."""
    return AgenticTestingEngine().run(
        requirement_text=requirement_text,
        failure_context=failure_context,
        mobile_artifact=mobile_artifact,
        locator_failure_payload=locator_failure_payload,
        mode=mode,
        source_id=source_id,
        source_name=source_name,
        evidence=evidence,
        environment=environment,
        test_name=test_name,
        source_file=source_file,
        steps_to_reproduce=steps_to_reproduce,
        expected_result=expected_result,
        actual_result=actual_result,
        artifact_path=artifact_path,
    )
