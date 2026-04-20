from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from orchestrator.candidates.application.coordinator import CandidateGenerationCoordinator
from orchestrator.candidates.domain.models import (
    BugCandidateInput,
    CandidateGenerationResult,
    CandidateType,
    IncidentCandidateInput,
)
from orchestrator.connectors.lark.application.lark_service import LarkNotificationService
from orchestrator.connectors.lark.domain.models import (
    LarkFlowHooksConfig,
    LarkNotificationConfig,
    LarkNotificationResult,
    NormalizedLarkSourceContext,
)
from orchestrator.connectors.lark.integration.coordinator import LarkFlowNotificationCoordinator
from orchestrator.decision.domain.models import (
    DecisionPolicyResult,
    DecisionPolicyType,
    GovernanceFlags,
)
from orchestrator.decision.integration.release_bridge import build_release_policy_signal
from orchestrator.self_healing.domain.models import (
    ActionContext,
    ActionExecutionBundle,
    ActionExecutionResult,
    ActionOutcomeRecord,
    ActionPlan,
)
from orchestrator.self_healing.integration.decision_bridge import execute_from_decision


@dataclass
class StubLarkService:
    result: LarkNotificationResult
    raise_exc: bool = False
    events: List[object] = field(default_factory=list)

    def send(self, event):
        self.events.append(event)
        if self.raise_exc:
            raise RuntimeError("connector boom")
        return self.result


@dataclass
class DummyBugEngine:
    result: CandidateGenerationResult

    def generate_bug_candidate(self, bug_input: BugCandidateInput) -> CandidateGenerationResult:
        return self.result


@dataclass
class DummyIncidentEngine:
    result: CandidateGenerationResult

    def generate_incident_candidate(self, incident_input: IncidentCandidateInput) -> CandidateGenerationResult:
        return self.result


class DummySelfHealingEngine:
    def __init__(self, bundle: ActionExecutionBundle) -> None:
        self.bundle = bundle

    def execute(self, decision_result, context) -> ActionExecutionBundle:
        return self.bundle


def _decision(primary: DecisionPolicyType = DecisionPolicyType.BLOCK_RELEASE, *, severity: str = "critical") -> DecisionPolicyResult:
    return DecisionPolicyResult(
        primary_decision=primary,
        strategy=None,
        rationale=["policy rationale"],
        confidence=0.91,
        decision_score=0.88,
        governance_flags=GovernanceFlags(),
        secondary_signals={"severity": severity, "release_critical": True, "protected_path": True},
        secondary_decisions=[],
        should_block_release=primary == DecisionPolicyType.BLOCK_RELEASE,
        should_trigger_rerun=False,
        should_escalate=primary in {DecisionPolicyType.BLOCK_RELEASE, DecisionPolicyType.ESCALATE},
        should_open_bug_candidate=False,
        should_open_incident_candidate=False,
        should_request_manual_review=False,
        recommended_owner="backend_owner",
        metadata={},
    )


def _candidate_result(candidate_type: str, *, generated: bool = True, severity: str = "critical", recurrence: int = 4):
    candidate_id = "INC-001" if candidate_type == CandidateType.INCIDENT.value else "BUG-001"
    return CandidateGenerationResult(
        generated=generated,
        candidate_type=candidate_type,
        candidate_id=candidate_id if generated else "",
        artifact=(
            {
                "candidate_id": candidate_id,
                "artifact_type": candidate_type,
                "title": "Payment API failure",
                "summary": "Candidate summary",
                "severity": severity,
                "confidence": 0.91,
                "recurrence": recurrence,
                "root_cause": "Settlement regression",
                "metadata": {
                    "adapter_id": "rankmate",
                    "project_id": "rankmate",
                    "run_id": "run-001",
                    "failure_id": "failure-001",
                    "memory_id": "mem-001",
                    "decision_primary": "BLOCK_RELEASE",
                    "self_healing_success": False,
                },
            }
            if generated
            else {"artifact_type": candidate_type}
        ),
        rationale=["rationale"],
    )


def _healing_bundle(*, success: bool, attempts: int) -> ActionExecutionBundle:
    decision = _decision(DecisionPolicyType.ESCALATE, severity="high")
    return ActionExecutionBundle(
        decision_result=decision,
        action_plan=ActionPlan(
            action_id="action-001",
            decision_type=DecisionPolicyType.RERUN_WITH_STRATEGY,
            strategy=None,
            max_attempts=attempts,
            cooldown_seconds=0,
        ),
        execution_result=ActionExecutionResult(
            action_id="action-001",
            executed=True,
            success=success,
            attempts_used=attempts,
            duration_ms=200,
            error=None if success else "failed",
            logs=["log"],
        ),
        outcome_record=ActionOutcomeRecord(
            action_type="RERUN_WITH_STRATEGY",
            strategy="retry_with_backoff",
            success=success,
            attempts=attempts,
        ),
    )


def _coordinator(tmp_path: Path, *, service=None, hooks_enabled: bool = True) -> LarkFlowNotificationCoordinator:
    lark_service = service or LarkNotificationService(
        config=LarkNotificationConfig(
            webhook_url="",
            enabled=True,
            notify_critical_only=False,
            dry_run=True,
            bug_occurrence_threshold=2,
            self_healing_attempt_threshold=3,
        )
    )
    return LarkFlowNotificationCoordinator(
        service=lark_service,
        config=LarkFlowHooksConfig(
            enabled=hooks_enabled,
            notify_on_incident_candidate=True,
            notify_on_critical_bug=True,
            notify_on_block_release=True,
            notify_on_self_healing_fail=True,
            audit_root=str(tmp_path / "artifacts" / "notifications" / "lark"),
        ),
    )


def _bug_input() -> BugCandidateInput:
    return BugCandidateInput(
        adapter_id="rankmate",
        project_id="rankmate",
        run_id="run-001",
        failure_id="f-1",
        memory_id="m-1",
        signature_hash="sig-1",
        memory_resolution_type="EXACT_MATCH",
        root_cause="root",
        severity="high",
        confidence=0.9,
        occurrence_count=3,
    )


def _incident_input() -> IncidentCandidateInput:
    return IncidentCandidateInput(
        adapter_id="rankmate",
        project_id="rankmate",
        run_id="run-001",
        failure_id="f-2",
        memory_id="m-2",
        signature_hash="sig-2",
        memory_resolution_type="EXACT_MATCH",
        root_cause="root",
        severity="critical",
        confidence=0.95,
        occurrence_count=4,
    )


def test_incident_candidate_created_notification_attempted(tmp_path: Path):
    coordinator = _coordinator(tmp_path)
    result = coordinator.notify_candidate(candidate_result=_candidate_result(CandidateType.INCIDENT.value))
    assert result.attempted is True
    assert result.audit_record.status == "dry_run"
    assert result.audit_record.event_type == "incident_candidate"


def test_duplicate_or_suppressed_candidate_no_notification(tmp_path: Path):
    service = StubLarkService(result=LarkNotificationResult(attempted=True, sent=True, event_type="bug_candidate", reason="ok"))
    coordinator = _coordinator(tmp_path, service=service)
    result = coordinator.notify_candidate(
        candidate_result=_candidate_result(CandidateType.BUG.value, generated=False),
    )
    assert result.skipped is True
    assert result.attempted is False
    assert len(service.events) == 0


def test_critical_bug_candidate_notification_attempted(tmp_path: Path):
    coordinator = _coordinator(tmp_path)
    result = coordinator.notify_candidate(candidate_result=_candidate_result(CandidateType.BUG.value, severity="high"))
    assert result.attempted is True
    assert result.audit_record.event_type == "bug_candidate"


def test_block_release_decision_notification_attempted(tmp_path: Path):
    coordinator = _coordinator(tmp_path)
    result = coordinator.notify_decision(
        decision_result=_decision(DecisionPolicyType.BLOCK_RELEASE),
        source_context=NormalizedLarkSourceContext(adapter_id="rankmate", project_id="rankmate", run_id="run-01"),
    )
    assert result.attempted is True
    assert result.audit_record.event_type == "decision_result"


def test_non_block_decision_no_notification(tmp_path: Path):
    service = StubLarkService(result=LarkNotificationResult(attempted=True, sent=True, event_type="decision_result", reason="ok"))
    coordinator = _coordinator(tmp_path, service=service)
    result = coordinator.notify_decision(
        decision_result=_decision(DecisionPolicyType.ESCALATE),
        source_context=NormalizedLarkSourceContext(adapter_id="rankmate", project_id="rankmate", run_id="run-02"),
    )
    assert result.skipped is True
    assert result.attempted is False
    assert len(service.events) == 0


def test_self_healing_failed_over_threshold_notification_attempted(tmp_path: Path):
    coordinator = _coordinator(tmp_path)
    bundle = _healing_bundle(success=False, attempts=3)
    context = ActionContext(adapter_id="rankmate", project_id="rankmate", run_id="run-03", failure_id="failure-03")
    result = coordinator.notify_self_healing(action_bundle=bundle, action_context=context)
    assert result.attempted is True
    assert result.audit_record.event_type == "self_healing_result"


def test_self_healing_success_no_notification(tmp_path: Path):
    service = StubLarkService(result=LarkNotificationResult(attempted=True, sent=True, event_type="self_healing_result", reason="ok"))
    coordinator = _coordinator(tmp_path, service=service)
    bundle = _healing_bundle(success=True, attempts=3)
    context = ActionContext(adapter_id="rankmate", project_id="rankmate", run_id="run-03", failure_id="failure-03")
    result = coordinator.notify_self_healing(action_bundle=bundle, action_context=context)
    assert result.skipped is True
    assert result.attempted is False
    assert len(service.events) == 0


def test_dry_run_produces_audit_record_without_send(tmp_path: Path):
    coordinator = _coordinator(tmp_path)
    result = coordinator.notify_decision(
        decision_result=_decision(DecisionPolicyType.BLOCK_RELEASE),
        source_context=NormalizedLarkSourceContext(adapter_id="rankmate", project_id="rankmate", run_id="run-04"),
    )
    record_path = Path(str(result.audit_record.metadata.get("audit_path", "")))
    assert result.audit_record.status == "dry_run"
    assert record_path.exists()


def test_send_failure_does_not_crash_integration(tmp_path: Path):
    service = StubLarkService(
        result=LarkNotificationResult(
            attempted=True,
            sent=False,
            event_type="decision_result",
            reason="send_failed",
            error="HTTPError",
            status_code=500,
        )
    )
    coordinator = _coordinator(tmp_path, service=service)
    result = coordinator.notify_decision(
        decision_result=_decision(DecisionPolicyType.BLOCK_RELEASE),
        source_context=NormalizedLarkSourceContext(adapter_id="rankmate", project_id="rankmate", run_id="run-05"),
    )
    assert result.failed is True
    assert result.audit_record.status == "failed"


def test_audit_artifact_written_correctly(tmp_path: Path):
    coordinator = _coordinator(tmp_path)
    result = coordinator.notify_candidate(candidate_result=_candidate_result(CandidateType.INCIDENT.value))
    audit_path = Path(str(result.audit_record.metadata.get("audit_path", "")))
    assert audit_path.exists()
    loaded = json.loads(audit_path.read_text(encoding="utf-8"))
    assert loaded["notification_id"] == result.audit_record.notification_id
    index_path = tmp_path / "artifacts" / "notifications" / "indexes" / "lark_notifications_index.json"
    assert index_path.exists()


def test_missing_optional_fields_graceful_audit_result(tmp_path: Path):
    coordinator = _coordinator(tmp_path)
    minimal = CandidateGenerationResult(
        generated=True,
        candidate_type=CandidateType.BUG.value,
        candidate_id="BUG-xyz",
        artifact={
            "candidate_id": "BUG-xyz",
            "artifact_type": CandidateType.BUG.value,
            "title": "Bug title",
            "severity": "critical",
            "recurrence": 2,
            "metadata": {},
        },
    )
    result = coordinator.notify_candidate(candidate_result=minimal)
    assert result.audit_record.adapter_id == ""
    assert result.audit_record.project_id == ""
    assert result.audit_record.notification_id.startswith("lark-candidate-")


def test_hooks_remain_non_blocking_under_connector_exception(tmp_path: Path):
    service = StubLarkService(
        result=LarkNotificationResult(attempted=True, sent=False, event_type="incident_candidate", reason="ignored"),
        raise_exc=True,
    )
    coordinator = _coordinator(tmp_path, service=service)
    result = coordinator.notify_candidate(candidate_result=_candidate_result(CandidateType.INCIDENT.value))
    assert result.failed is True
    assert result.audit_record.status == "failed"
    assert "connector_exception" in result.audit_record.rationale


def test_candidate_coordinator_auto_wires_notifications(tmp_path: Path):
    notifier = _coordinator(tmp_path)
    candidate_coordinator = CandidateGenerationCoordinator(
        bug_engine=DummyBugEngine(_candidate_result(CandidateType.BUG.value, severity="high")),
        incident_engine=DummyIncidentEngine(_candidate_result(CandidateType.INCIDENT.value)),
        lark_notifier=notifier,
    )
    output = candidate_coordinator.generate_all(bug_input=_bug_input(), incident_input=_incident_input())
    assert output["bug"].generated is True
    index_path = tmp_path / "artifacts" / "notifications" / "indexes" / "lark_notifications_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert len(index) >= 2


def test_decision_and_self_healing_bridges_auto_wire_notifications(tmp_path: Path):
    notifier = _coordinator(tmp_path)
    decision_input_context = NormalizedLarkSourceContext(adapter_id="rankmate", project_id="rankmate", run_id="run-bridge")
    decision_engine_result = _decision(DecisionPolicyType.BLOCK_RELEASE)

    class DummyDecisionEngine:
        def evaluate(self, input_data):
            return decision_engine_result

        def build_ci_decision_hint(self, result):
            return {"gate_signal": "hard_block"}

    release_output = build_release_policy_signal(
        DummyDecisionEngine(),
        input_data=type("DecisionInput", (), {
            "adapter_id": "rankmate",
            "project_id": "rankmate",
            "run_id": "run-bridge",
            "severity": "critical",
            "confidence": 0.9,
            "occurrence_count": 3,
            "triage_root_cause": "root",
        })(),
        lark_notifier=notifier,
    )
    assert release_output["release_signal"] == "block"

    bundle = _healing_bundle(success=False, attempts=3)
    self_healing_engine = DummySelfHealingEngine(bundle)
    context = ActionContext(adapter_id="rankmate", project_id="rankmate", run_id="run-sh", failure_id="failure-sh")
    execute_from_decision(self_healing_engine, decision_engine_result, context, lark_notifier=notifier)

    index_path = tmp_path / "artifacts" / "notifications" / "indexes" / "lark_notifications_index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    assert any(row["source_type"] == "decision" for row in index)
    assert any(row["source_type"] == "self_healing" for row in index)

