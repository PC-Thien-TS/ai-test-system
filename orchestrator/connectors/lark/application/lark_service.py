from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, is_dataclass
from typing import Any, Dict, Optional

from ..domain.models import (
    LarkNotificationConfig,
    LarkNotificationEvent,
    LarkNotificationEventType,
    LarkNotificationResult,
    load_lark_config_from_env,
)
from ..infrastructure.client import LarkWebhookClient


@dataclass
class LarkNotificationMessage:
    title: str
    body_lines: list[str]
    payload: Dict[str, Any]


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
                event_type=resolved.event_type.value,
                reason="disabled",
            )

        should_notify, notify_reason = self.should_notify(resolved)
        if not should_notify:
            return LarkNotificationResult(
                attempted=False,
                sent=False,
                event_type=resolved.event_type.value,
                reason=notify_reason,
            )

        if self.config.dry_run:
            reason = notify_reason
            if resolved.event_type == LarkNotificationEventType.DECISION_RESULT:
                reason = "dry_run"
            return LarkNotificationResult(
                attempted=True,
                sent=False,
                event_type=resolved.event_type.value,
                reason=reason,
                dry_run=True,
                response_data={"title": resolved.title, "event_type": resolved.event_type.value},
                metadata={"notify_reason": notify_reason},
            )

        if not self.config.webhook_url:
            return LarkNotificationResult(
                attempted=False,
                sent=False,
                event_type=resolved.event_type.value,
                reason="missing_webhook",
            )

        try:
            resp = self.client.send(
                self.config.webhook_url,
                self.build_message(resolved).payload,
                timeout_seconds=self.config.timeout_seconds,
            )
            return LarkNotificationResult(
                attempted=True,
                sent=resp.success,
                event_type=resolved.event_type.value,
                reason="sent" if resp.success else "send_failed",
                dry_run=False,
                status_code=resp.status_code,
                error=resp.error,
                response_data=resp.data,
                metadata={"notify_reason": notify_reason},
            )
        except Exception as exc:
            self.logger.warning("Lark send failed: %s", exc)
            return LarkNotificationResult(
                attempted=True,
                sent=False,
                event_type=resolved.event_type.value,
                reason="send_exception",
                error=f"{type(exc).__name__}: {exc}",
            )

    def should_notify(self, event: LarkNotificationEvent) -> tuple[bool, str]:
        severity = str(event.severity or "").strip().lower()
        if event.event_type == LarkNotificationEventType.INCIDENT_CANDIDATE:
            if self.config.notify_critical_only and severity and severity != "critical":
                return False, "critical_only_non_critical_incident"
            return True, "incident_candidate_always_notified"
        if event.event_type == LarkNotificationEventType.BUG_CANDIDATE:
            if severity not in {"critical", "high"}:
                return False, "bug_severity_not_eligible"
            if int(event.occurrence_count) < int(self.config.bug_occurrence_threshold):
                return False, "bug_occurrence_below_threshold"
            # Safest minimal interpretation: only severity=critical bug alerts survive the critical-only mode.
            if self.config.notify_critical_only and severity != "critical":
                return False, "critical_only_non_critical_bug"
            return True, "critical_bug_threshold_match"
        if event.event_type == LarkNotificationEventType.DECISION_RESULT:
            if str(event.primary_decision or "").upper() != "BLOCK_RELEASE":
                return False, "decision_not_block_release"
            return True, "block_release_decision"
        if event.event_type == LarkNotificationEventType.SELF_HEALING_RESULT:
            if event.self_healing_success is True:
                return False, "self_healing_success"
            if event.attempts_used is not None and int(event.attempts_used) < int(self.config.self_healing_attempt_threshold):
                return False, "self_healing_attempts_below_threshold"
            return True, "self_healing_failed_threshold_match"
        return False, "unsupported_event_type"

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
            run_id=event.get("run_id"),
            memory_id=event.get("memory_id"),
            self_healing_success=event.get("self_healing_success"),
            attempts_used=event.get("attempts_used"),
            metadata=dict(event.get("metadata", {}) or {}),
        )

    def build_message(self, event: LarkNotificationEvent) -> LarkNotificationMessage:
        title_prefix = {
            LarkNotificationEventType.INCIDENT_CANDIDATE: "🚨 [INCIDENT]",
            LarkNotificationEventType.BUG_CANDIDATE: "🚨 [BUG]",
            LarkNotificationEventType.DECISION_RESULT: "🚨 [DECISION]",
            LarkNotificationEventType.SELF_HEALING_RESULT: "⚠️ [SELF-HEALING]",
        }[event.event_type]
        title = f"{title_prefix} {event.title} ({str(event.severity).upper()})"

        body_lines = [
            f"- Project: {event.project}",
            f"- Adapter: {event.adapter}",
            f"- Severity: {str(event.severity).upper()}",
            f"- Occurrences: {event.occurrence_count}",
        ]
        if event.confidence is not None:
            body_lines.append(f"- Confidence: {float(event.confidence):.2f}")
        if event.primary_decision:
            body_lines.append(f"- Decision: {event.primary_decision}")
        if event.self_healing_status:
            body_lines.append(f"- Self-healing: {event.self_healing_status}")
        if event.root_cause:
            body_lines.extend(["", "Root Cause:", event.root_cause])
        if event.action_required:
            body_lines.extend(["", "Action:", f"→ {event.action_required}"])
        if event.dashboard_url:
            body_lines.extend(["", f"Dashboard: {event.dashboard_url}"])

        content = [[{"tag": "text", "text": line}] for line in body_lines]
        payload = {
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
        return LarkNotificationMessage(title=title, body_lines=body_lines, payload=payload)

    def _build_payload(self, event: LarkNotificationEvent) -> Dict[str, Any]:
        return self.build_message(event).payload
