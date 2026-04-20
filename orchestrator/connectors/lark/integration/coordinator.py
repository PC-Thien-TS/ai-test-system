from __future__ import annotations

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Optional

from orchestrator.candidates.domain.models import CandidateGenerationResult, CandidateInputBase
from orchestrator.decision.domain.models import DecisionPolicyResult
from orchestrator.self_healing.domain.models import ActionContext, ActionExecutionBundle

from ..application.lark_service import LarkNotificationService
from ..domain.models import (
    LarkFlowHooksConfig,
    LarkNotificationAuditRecord,
    LarkNotificationHookResult,
    LarkNotificationResult,
    NormalizedLarkSourceContext,
    build_notification_id,
    load_lark_flow_hooks_config_from_env,
)
from .artifact_bridge import LarkNotificationAuditStore
from .candidate_hook import notify_from_candidate_result
from .decision_hook import notify_from_decision_result
from .self_healing_hook import notify_from_self_healing_result


class LarkFlowNotificationCoordinator:
    def __init__(
        self,
        *,
        service: Optional[LarkNotificationService] = None,
        audit_store: Optional[LarkNotificationAuditStore] = None,
        config: Optional[LarkFlowHooksConfig] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.config = config or load_lark_flow_hooks_config_from_env()
        self.service = service or LarkNotificationService()
        self.audit_store = audit_store or LarkNotificationAuditStore(Path(self.config.audit_root))
        self.logger = logger or logging.getLogger(__name__)

    def notify_candidate(
        self,
        *,
        candidate_result: CandidateGenerationResult,
        candidate_input: Optional[CandidateInputBase] = None,
    ) -> LarkNotificationHookResult:
        if not self.config.enabled:
            return self._persist_and_return(
                self._build_skipped_hook_result(
                    source_type="candidate",
                    source_id=candidate_result.candidate_id or "candidate",
                    reason="flow_hooks_disabled",
                )
            )

        build = notify_from_candidate_result(candidate_result=candidate_result, candidate_input=candidate_input)
        if build.event is None:
            return self._persist_and_return(
                self._build_skipped_hook_result(
                    source_type="candidate",
                    source_id=build.source_id or candidate_result.candidate_id or "candidate",
                    reason=build.reason,
                    context=build.context,
                    candidate_id=candidate_result.candidate_id,
                )
            )

        if build.event.event_type.value == "incident_candidate" and not self.config.notify_on_incident_candidate:
            return self._persist_and_return(
                self._build_skipped_hook_result(
                    source_type="candidate",
                    source_id=build.source_id or candidate_result.candidate_id or "candidate",
                    reason="incident_notifications_disabled",
                    context=build.context,
                    candidate_id=candidate_result.candidate_id,
                    event_type=build.event.event_type.value,
                    title=build.event.title,
                )
            )
        if build.event.event_type.value == "bug_candidate" and not self.config.notify_on_critical_bug:
            return self._persist_and_return(
                self._build_skipped_hook_result(
                    source_type="candidate",
                    source_id=build.source_id or candidate_result.candidate_id or "candidate",
                    reason="bug_notifications_disabled",
                    context=build.context,
                    candidate_id=candidate_result.candidate_id,
                    event_type=build.event.event_type.value,
                    title=build.event.title,
                )
            )

        return self._send_and_audit(
            source_type="candidate",
            source_id=build.source_id or candidate_result.candidate_id or "candidate",
            candidate_id=candidate_result.candidate_id,
            event=build.event,
            context=build.context,
        )

    def notify_decision(
        self,
        *,
        decision_result: DecisionPolicyResult,
        source_context: Optional[NormalizedLarkSourceContext] = None,
    ) -> LarkNotificationHookResult:
        if not self.config.enabled:
            return self._persist_and_return(
                self._build_skipped_hook_result(
                    source_type="decision",
                    source_id=source_context.run_id if source_context else "decision",
                    reason="flow_hooks_disabled",
                    context=source_context,
                )
            )

        build = notify_from_decision_result(decision_result=decision_result, source_context=source_context)
        if build.event is None:
            return self._persist_and_return(
                self._build_skipped_hook_result(
                    source_type="decision",
                    source_id=build.source_id or (source_context.run_id if source_context else "decision"),
                    reason=build.reason,
                    context=build.context or source_context,
                )
            )
        if not self.config.notify_on_block_release:
            return self._persist_and_return(
                self._build_skipped_hook_result(
                    source_type="decision",
                    source_id=build.source_id or (source_context.run_id if source_context else "decision"),
                    reason="block_release_notifications_disabled",
                    context=build.context or source_context,
                    event_type=build.event.event_type.value,
                    title=build.event.title,
                )
            )
        return self._send_and_audit(
            source_type="decision",
            source_id=build.source_id or (source_context.run_id if source_context else "decision"),
            event=build.event,
            context=build.context or source_context,
        )

    def notify_self_healing(
        self,
        *,
        action_bundle: ActionExecutionBundle,
        action_context: Optional[ActionContext] = None,
    ) -> LarkNotificationHookResult:
        if not self.config.enabled:
            return self._persist_and_return(
                self._build_skipped_hook_result(
                    source_type="self_healing",
                    source_id=action_bundle.execution_result.action_id or "self_healing",
                    reason="flow_hooks_disabled",
                )
            )

        build = notify_from_self_healing_result(action_bundle=action_bundle, action_context=action_context)
        if build.event is None:
            return self._persist_and_return(
                self._build_skipped_hook_result(
                    source_type="self_healing",
                    source_id=build.source_id or action_bundle.execution_result.action_id or "self_healing",
                    reason=build.reason,
                    context=build.context,
                )
            )
        if not self.config.notify_on_self_healing_fail:
            return self._persist_and_return(
                self._build_skipped_hook_result(
                    source_type="self_healing",
                    source_id=build.source_id or action_bundle.execution_result.action_id or "self_healing",
                    reason="self_healing_notifications_disabled",
                    context=build.context,
                    event_type=build.event.event_type.value,
                    title=build.event.title,
                )
            )
        return self._send_and_audit(
            source_type="self_healing",
            source_id=build.source_id or action_bundle.execution_result.action_id or "self_healing",
            event=build.event,
            context=build.context,
            run_id=(action_context.run_id if action_context else ""),
            failure_id=(action_context.failure_id if action_context else ""),
        )

    def _send_and_audit(
        self,
        *,
        source_type: str,
        source_id: str,
        event,
        context: Optional[NormalizedLarkSourceContext] = None,
        candidate_id: str = "",
        run_id: str = "",
        failure_id: str = "",
    ) -> LarkNotificationHookResult:
        connector_result: LarkNotificationResult
        try:
            connector_result = self.service.send(event)
        except Exception as exc:  # fail-safe
            connector_result = LarkNotificationResult(
                attempted=True,
                sent=False,
                event_type=event.event_type.value,
                reason="connector_exception",
                error=f"{type(exc).__name__}: {exc}",
            )

        hook = self._hook_result_from_connector(
            source_type=source_type,
            source_id=source_id,
            event_type=event.event_type.value,
            title=event.title,
            context=context,
            connector_result=connector_result,
            candidate_id=candidate_id,
            run_id=run_id or (context.run_id if context else ""),
            failure_id=failure_id or (context.failure_id if context else ""),
        )
        return self._persist_and_return(hook)

    def _hook_result_from_connector(
        self,
        *,
        source_type: str,
        source_id: str,
        event_type: str,
        title: str,
        context: Optional[NormalizedLarkSourceContext],
        connector_result: LarkNotificationResult,
        candidate_id: str = "",
        run_id: str = "",
        failure_id: str = "",
    ) -> LarkNotificationHookResult:
        status = "failed"
        if connector_result.dry_run:
            status = "dry_run"
        elif connector_result.sent:
            status = "sent"
        elif not connector_result.attempted:
            status = "skipped"

        audit = LarkNotificationAuditRecord(
            notification_id=build_notification_id(source_type),
            source_type=source_type,
            source_id=source_id,
            event_type=event_type,
            title=title,
            adapter_id=(context.adapter_id if context else ""),
            project_id=(context.project_id if context else ""),
            candidate_id=candidate_id,
            run_id=run_id,
            failure_id=failure_id,
            status=status,
            dry_run=connector_result.dry_run,
            rationale=connector_result.reason,
            error=connector_result.error or "",
            metadata={
                "connector_status_code": connector_result.status_code,
                "connector_metadata": connector_result.metadata,
            },
        )
        return LarkNotificationHookResult(
            attempted=connector_result.attempted,
            sent=connector_result.sent,
            skipped=(status == "skipped"),
            failed=(status == "failed"),
            audit_record=audit,
            connector_result=connector_result,
        )

    def _build_skipped_hook_result(
        self,
        *,
        source_type: str,
        source_id: str,
        reason: str,
        context: Optional[NormalizedLarkSourceContext] = None,
        candidate_id: str = "",
        event_type: str = "",
        title: str = "",
    ) -> LarkNotificationHookResult:
        audit = LarkNotificationAuditRecord(
            notification_id=build_notification_id(source_type),
            source_type=source_type,
            source_id=source_id,
            event_type=event_type,
            title=title or f"{source_type} notification skipped",
            adapter_id=(context.adapter_id if context else ""),
            project_id=(context.project_id if context else ""),
            candidate_id=candidate_id,
            run_id=(context.run_id if context else ""),
            failure_id=(context.failure_id if context else ""),
            status="skipped",
            dry_run=False,
            rationale=reason,
        )
        return LarkNotificationHookResult(
            attempted=False,
            sent=False,
            skipped=True,
            failed=False,
            audit_record=audit,
            connector_result=None,
            metadata={},
        )

    def _persist_and_return(self, hook_result: LarkNotificationHookResult) -> LarkNotificationHookResult:
        try:
            path = self.persist_audit_record(hook_result.audit_record)
            hook_result.audit_record.metadata["audit_path"] = path
            return hook_result
        except Exception as exc:  # fail-safe
            self.logger.warning("Lark audit persistence failed: %s", exc)
            hook_result.audit_record.metadata["audit_persist_error"] = f"{type(exc).__name__}: {exc}"
            return hook_result

    def persist_audit_record(self, record: LarkNotificationAuditRecord) -> str:
        return self.audit_store.write_record(record)

    def build_audit_record(self, hook_result: LarkNotificationHookResult) -> LarkNotificationAuditRecord:
        return LarkNotificationAuditRecord(**asdict(hook_result.audit_record))
