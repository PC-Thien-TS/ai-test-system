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
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LarkNotificationResult:
    attempted: bool
    sent: bool
    reason: str
    dry_run: bool = False
    status_code: Optional[int] = None
    error: Optional[str] = None
    response_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=utc_now_iso)


@dataclass
class LarkNotificationConfig:
    webhook_url: str = ""
    enabled: bool = True
    notify_critical_only: bool = True
    dry_run: bool = True
    timeout_seconds: float = 5.0


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
    )

