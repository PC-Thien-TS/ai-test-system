from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from orchestrator.connectors.lark.application.lark_service import LarkNotificationService
from orchestrator.connectors.lark.domain.models import (
    LarkNotificationConfig,
    LarkNotificationEvent,
    LarkNotificationEventType,
)
from orchestrator.connectors.lark.infrastructure.client import LarkClientResponse


@dataclass
class FakeLarkClient:
    calls: List[Dict[str, Any]] = field(default_factory=list)
    response: LarkClientResponse = field(
        default_factory=lambda: LarkClientResponse(success=True, status_code=200, response_json={"StatusCode": 0})
    )

    def send(self, webhook_url: str, payload: Dict[str, Any], timeout_seconds: float = 5.0) -> LarkClientResponse:
        self.calls.append(
            {
                "webhook_url": webhook_url,
                "payload": payload,
                "timeout_seconds": timeout_seconds,
            }
        )
        return self.response


def _service(
    *,
    critical_only: bool = False,
    dry_run: bool = True,
    bug_threshold: int = 2,
    heal_attempt_threshold: int = 3,
    client: FakeLarkClient | None = None,
) -> LarkNotificationService:
    return LarkNotificationService(
        config=LarkNotificationConfig(
            webhook_url="https://example.test/lark-webhook",
            enabled=True,
            notify_critical_only=critical_only,
            dry_run=dry_run,
            bug_occurrence_threshold=bug_threshold,
            self_healing_attempt_threshold=heal_attempt_threshold,
        ),
        client=client or FakeLarkClient(),
    )


def test_incident_triggers_notification():
    service = _service(dry_run=True)
    event = LarkNotificationEvent(
        event_type=LarkNotificationEventType.INCIDENT_CANDIDATE,
        title="Payment API failure",
        project="rankmate",
        adapter="rankmate",
        severity="critical",
        occurrence_count=4,
        confidence=0.91,
        primary_decision="BLOCK_RELEASE",
        self_healing_status="FAILED",
    )
    should_notify, reason = service.should_notify(event)
    result = service.send(event)
    assert should_notify is True
    assert reason == "incident_candidate_always_notified"
    assert result.attempted is True
    assert result.dry_run is True
    assert result.reason == "incident_candidate_always_notified"


def test_critical_bug_triggers_notification():
    service = _service(critical_only=False, dry_run=True, bug_threshold=3)
    event = LarkNotificationEvent(
        event_type=LarkNotificationEventType.BUG_CANDIDATE,
        title="Store lookup returns 500",
        project="rankmate",
        adapter="rankmate",
        severity="critical",
        occurrence_count=3,
    )
    should_notify, reason = service.should_notify(event)
    assert should_notify is True
    assert reason == "critical_bug_threshold_match"


def test_low_severity_bug_does_not_notify():
    service = _service(critical_only=False, dry_run=True)
    event = LarkNotificationEvent(
        event_type=LarkNotificationEventType.BUG_CANDIDATE,
        title="Minor copy mismatch",
        project="rankmate",
        adapter="rankmate",
        severity="low",
        occurrence_count=10,
    )
    should_notify, reason = service.should_notify(event)
    result = service.send(event)
    assert should_notify is False
    assert reason == "bug_severity_not_eligible"
    assert result.attempted is False
    assert result.reason == "bug_severity_not_eligible"


def test_dry_run_mode_does_not_call_webhook_client():
    client = FakeLarkClient()
    service = _service(dry_run=True, client=client)
    event = LarkNotificationEvent(
        event_type=LarkNotificationEventType.DECISION_RESULT,
        title="Release gate decision",
        project="rankmate",
        adapter="rankmate",
        primary_decision="BLOCK_RELEASE",
    )
    result = service.send(event)
    assert result.attempted is True
    assert result.sent is False
    assert result.dry_run is True
    assert len(client.calls) == 0


def test_message_format_contains_required_sections():
    service = _service(dry_run=True, critical_only=False)
    event = LarkNotificationEvent(
        event_type=LarkNotificationEventType.INCIDENT_CANDIDATE,
        title="Payment API failure",
        project="rankmate",
        adapter="rankmate",
        severity="critical",
        occurrence_count=4,
        confidence=0.91,
        primary_decision="BLOCK_RELEASE",
        self_healing_status="FAILED",
        root_cause="Payment settlement endpoint regression",
        action_required="Immediate investigation required",
        dashboard_url="https://dashboard.example/runs/123",
    )
    message = service.build_message(event)
    assert message.title == "🚨 [INCIDENT] Payment API failure (CRITICAL)"
    joined = "\n".join(message.body_lines)
    assert "- Project: rankmate" in joined
    assert "- Adapter: rankmate" in joined
    assert "- Severity: CRITICAL" in joined
    assert "- Occurrences: 4" in joined
    assert "- Confidence: 0.91" in joined
    assert "- Decision: BLOCK_RELEASE" in joined
    assert "- Self-healing: FAILED" in joined
    assert "Root Cause:" in joined
    assert "Payment settlement endpoint regression" in joined
    assert "Action:" in joined
    assert "→ Immediate investigation required" in joined
    assert message.payload["msg_type"] == "post"

