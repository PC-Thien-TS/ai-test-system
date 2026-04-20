from __future__ import annotations

from orchestrator.connectors.lark import (
    LarkNotificationConfig,
    LarkNotificationEvent,
    LarkNotificationEventType,
    LarkNotificationService,
)


def test_import_and_dry_run_send():
    service = LarkNotificationService(
        config=LarkNotificationConfig(
            webhook_url="",
            enabled=True,
            dry_run=True,
        )
    )
    result = service.send(
        LarkNotificationEvent(
            event_type=LarkNotificationEventType.DECISION_RESULT,
            title="Release gate decision",
            project="rankmate",
            adapter="rankmate",
            primary_decision="BLOCK_RELEASE",
        )
    )
    assert result.attempted is True
    assert result.sent is False
    assert result.dry_run is True
    assert result.reason == "dry_run"

