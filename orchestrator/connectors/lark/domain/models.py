from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class LarkNotificationEventType(str, Enum):
    INCIDENT_CANDIDATE = "incident_candidate"
    BUG_CANDIDATE = "bug_candidate"
    DECISION_RESULT = "decision_result"
    SELF_HEALING_RESULT = "self_healing_result"


@dataclass
class LarkNotificationEvent:
    event_type: LarkNotificationEventType
    title: str
    project: str
    adapter: str
    severity: str = "medium"
    occurrence_count: int = 1
    confidence: Optional[float] = None
    primary_decision: Optional[str] = None
    self_healing_status: Optional[str] = None
    root_cause: str = ""
    action_required: str = ""
    dashboard_url: Optional[str] = None
    run_id: Optional[str] = None
    memory_id: Optional[str] = None
    self_healing_success: Optional[bool] = None
    attempts_used: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LarkNotificationResult:
    attempted: bool
    sent: bool
    reason: str
    event_type: str = ""
    dry_run: bool = False
    status_code: Optional[int] = None
    error: Optional[str] = None
    response_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now_iso)


@dataclass
class LarkNotificationConfig:
    webhook_url: str = ""
    enabled: bool = True
    notify_critical_only: bool = True
    dry_run: bool = True
    timeout_seconds: float = 5.0
    bug_occurrence_threshold: int = 2
    self_healing_attempt_threshold: int = 3


@dataclass
class LarkFlowHooksConfig:
    enabled: bool = True
    notify_on_incident_candidate: bool = True
    notify_on_critical_bug: bool = True
    notify_on_block_release: bool = True
    notify_on_self_healing_fail: bool = True
    audit_root: str = "artifacts/notifications/lark"


@dataclass
class NormalizedLarkSourceContext:
    adapter_id: str = ""
    project_id: str = ""
    run_id: str = ""
    failure_id: str = ""
    severity: str = ""
    confidence: Optional[float] = None
    occurrence_count: int = 1
    root_cause: str = ""
    action_required: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LarkNotificationAuditRecord:
    notification_id: str
    source_type: str
    source_id: str
    event_type: str = ""
    title: str = ""
    adapter_id: str = ""
    project_id: str = ""
    candidate_id: str = ""
    run_id: str = ""
    failure_id: str = ""
    status: str = ""
    dry_run: bool = False
    rationale: str = ""
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now_iso)


@dataclass
class LarkNotificationHookResult:
    attempted: bool
    sent: bool
    skipped: bool
    failed: bool
    audit_record: LarkNotificationAuditRecord
    connector_result: Optional[LarkNotificationResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def load_lark_config_from_env() -> LarkNotificationConfig:
    return LarkNotificationConfig(
        webhook_url=os.getenv("LARK_WEBHOOK_URL", "").strip(),
        enabled=_env_bool("LARK_ENABLED", True),
        notify_critical_only=_env_bool("LARK_NOTIFY_CRITICAL_ONLY", True),
        dry_run=_env_bool("LARK_DRY_RUN", True),
        timeout_seconds=_env_float("LARK_TIMEOUT_SECONDS", 5.0),
        bug_occurrence_threshold=int(_env_float("LARK_BUG_OCCURRENCE_THRESHOLD", 2)),
        self_healing_attempt_threshold=int(_env_float("LARK_SELF_HEALING_ATTEMPT_THRESHOLD", 3)),
    )


def load_lark_flow_hooks_config_from_env() -> LarkFlowHooksConfig:
    return LarkFlowHooksConfig(
        enabled=_env_bool("LARK_FLOW_HOOKS_ENABLED", True),
        notify_on_incident_candidate=_env_bool("LARK_NOTIFY_ON_INCIDENT_CANDIDATE", True),
        notify_on_critical_bug=_env_bool("LARK_NOTIFY_ON_CRITICAL_BUG", True),
        notify_on_block_release=_env_bool("LARK_NOTIFY_ON_BLOCK_RELEASE", True),
        notify_on_self_healing_fail=_env_bool("LARK_NOTIFY_ON_SELF_HEALING_FAIL", True),
        audit_root=os.getenv("LARK_AUDIT_ROOT", "artifacts/notifications/lark").strip()
        or "artifacts/notifications/lark",
    )


def build_notification_id(source_type: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    normalized_source = str(source_type or "notification").replace("_", "-")
    return f"lark-{normalized_source}-{timestamp}"
