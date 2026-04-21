from orchestrator.connectors.lark import (
    LarkNotificationService,
    LarkNotificationEvent,
    LarkNotificationEventType,
)

svc = LarkNotificationService()

result = svc.send(
    LarkNotificationEvent(
        event_type=LarkNotificationEventType.DECISION_RESULT,
        title="Release gate decision",
        project="rankmate",
        adapter="rankmate",
        primary_decision="BLOCK_RELEASE",
        severity="critical",
        occurrence_count=4,
        confidence=0.91,
        root_cause="Payment settlement endpoint regression",
        action_required="Immediate investigation required",
        metadata={"source": "manual_smoke_test"},
    )
)

print(result)