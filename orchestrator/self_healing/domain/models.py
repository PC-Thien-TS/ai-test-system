from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from orchestrator.decision.domain.models import DecisionPolicyResult, DecisionPolicyType, DecisionStrategy


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ActionPlan:
    action_id: str
    decision_type: DecisionPolicyType
    strategy: Optional[DecisionStrategy]
    max_attempts: int
    cooldown_seconds: float
    allow_partial_success: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionExecutionResult:
    action_id: str
    executed: bool
    success: bool
    attempts_used: int
    duration_ms: int
    error: Optional[str]
    logs: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=utc_now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionContext:
    adapter_id: str
    project_id: str
    run_id: str
    failure_id: str
    execution_path: Optional[str] = None
    ci_context: Dict[str, Any] = field(default_factory=dict)
    memory_context: Dict[str, Any] = field(default_factory=dict)
    decision_context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    executor: Optional[Callable[[int, ActionPlan, "ActionContext"], bool]] = None


@dataclass
class ActionOutcomeRecord:
    action_type: str
    strategy: str
    success: bool
    attempts: int
    timestamp: str = field(default_factory=utc_now_iso)
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SelfHealingConfig:
    max_attempts: int = 3
    max_total_attempts: int = 20
    max_attempts_per_failure: int = 5
    backoff_base: float = 2.0
    timeout_multiplier: float = 1.5
    cooldown_seconds: float = 2.0
    min_action_effectiveness_for_rerun: float = 0.55
    enable_suppression: bool = True
    enable_escalation: bool = True


@dataclass
class ActionExecutionBundle:
    decision_result: DecisionPolicyResult
    action_plan: ActionPlan
    execution_result: ActionExecutionResult
    outcome_record: ActionOutcomeRecord

