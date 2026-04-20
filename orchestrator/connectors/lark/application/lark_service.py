from __future__ import annotations

import logging
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional

from ..domain.models import (
    LarkNotificationConfig,
    LarkNotificationEvent,
    LarkNotificationEventType,
    LarkNotificationResult,
    load_lark_config_from_env,
)
from ..infrastructure.client import LarkWebhookClient


class LarkNotificationService:
    """
    Minimal fail-safe Lark notification service.
    - never raises from send()
    - dry-run safe without network
    - no hard dependency on third-party packages
    """

    def __init__(
        self,
        *,
        config: Optional[LarkNotificationConfig] = None,
        client: Optional[LarkWebhookClient] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.config = config or load_lark_config_from_env()
        self.client = client or LarkWebhookClient()
        self.logger = logger or logging.getLogger(__name__)

    def send(self, event: LarkNotificationEvent | Dict[str, Any]) -> LarkNotificationResult:
        try:
            resolved = self._coerce_event(event)
        except Exception as exc:
            return LarkNotificationResult(
                attempted=False,
                sent=False,
                reason="invalid_event",
                error=f"{type(exc).__name__}: {exc}",
            )

        if not self.config.enabled:
            return LarkNotificationResult(
                attempted=False,
                sent=False,
                reason="disabled",
            )

        if self.config.dry_run:
            return LarkNotificationResult(
                attempted=True,
                sent=False,
                reason="dry_run",
                dry_run=True,
                response_data={"title": resolved.title, "event_type": resolved.event_type.value},
            )

        if not self.config.webhook_url:
            return LarkNotificationResult(
                attempted=False,
                sent=False,
                reason="missing_webhook",
            )

        payload = self._build_payload(resolved)
        try:
            resp = self.client.send(
                self.config.webhook_url,
                payload,
                timeout_seconds=self.config.timeout_seconds,
            )
            return LarkNotificationResult(
                attempted=True,
                sent=resp.success,
                reason="sent" if resp.success else "send_failed",
                dry_run=False,
                status_code=resp.status_code,
                error=resp.error,
                response_data=resp.data,
            )
        except Exception as exc:
            self.logger.warning("Lark send failed: %s", exc)
            return LarkNotificationResult(
                attempted=True,
                sent=False,
                reason="send_exception",
                error=f"{type(exc).__name__}: {exc}",
            )

    def _coerce_event(self, event: LarkNotificationEvent | Dict[str, Any]) -> LarkNotificationEvent:
        if isinstance(event, LarkNotificationEvent):
            return event
        if is_dataclass(event):
            event = asdict(event)
        if not isinstance(event, dict):
            raise TypeError("event must be LarkNotificationEvent or dict")

        event_type = event.get("event_type", LarkNotificationEventType.DECISION_RESULT.value)
        if isinstance(event_type, LarkNotificationEventType):
            resolved_type = event_type
        else:
            resolved_type = LarkNotificationEventType(str(event_type))

        return LarkNotificationEvent(
            event_type=resolved_type,
            title=str(event.get("title", "Lark notification")),
            project=str(event.get("project", "unknown")),
            adapter=str(event.get("adapter", "unknown")),
            severity=str(event.get("severity", "medium")),
            occurrence_count=int(event.get("occurrence_count", 1)),
            confidence=event.get("confidence"),
            primary_decision=event.get("primary_decision"),
            self_healing_status=event.get("self_healing_status"),
            root_cause=str(event.get("root_cause", "")),
            action_required=str(event.get("action_required", "")),
            dashboard_url=event.get("dashboard_url"),
            metadata=dict(event.get("metadata", {}) or {}),
        )

    def _build_payload(self, event: LarkNotificationEvent) -> Dict[str, Any]:
        title_prefix = {
            LarkNotificationEventType.INCIDENT_CANDIDATE: "🚨 [INCIDENT]",
            LarkNotificationEventType.BUG_CANDIDATE: "🚨 [BUG]",
            LarkNotificationEventType.DECISION_RESULT: "🚨 [DECISION]",
            LarkNotificationEventType.SELF_HEALING_RESULT: "⚠️ [SELF-HEALING]",
        }[event.event_type]
        title = f"{title_prefix} {event.title}"

        lines = [
            f"Project: {event.project}",
            f"Adapter: {event.adapter}",
            f"Severity: {str(event.severity).upper()}",
            f"Occurrences: {event.occurrence_count}",
        ]
        if event.confidence is not None:
            lines.append(f"Confidence: {float(event.confidence):.2f}")
        if event.primary_decision:
            lines.append(f"Decision: {event.primary_decision}")
        if event.self_healing_status:
            lines.append(f"Self-healing: {event.self_healing_status}")
        if event.root_cause:
            lines.extend(["", "Root Cause:", event.root_cause])
        if event.action_required:
            lines.extend(["", "Action:", f"→ {event.action_required}"])
        if event.dashboard_url:
            lines.extend(["", f"Dashboard: {event.dashboard_url}"])

        content = [[{"tag": "text", "text": line}] for line in lines]
        return {
            "msg_type": "post",
            "content": {
                "post": {
                    "en_us": {
                        "title": title,
                        "content": content,
                    }
                }
            },
        }

