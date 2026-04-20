from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from orchestrator.memory.domain.models import MemoryResolutionType


class DecisionPolicyType(str, Enum):
    NO_ACTION = "NO_ACTION"
    RERUN = "RERUN"
    RERUN_WITH_STRATEGY = "RERUN_WITH_STRATEGY"
    SUPPRESS_KNOWN_FLAKY = "SUPPRESS_KNOWN_FLAKY"
    ESCALATE = "ESCALATE"
    MANUAL_INVESTIGATION = "MANUAL_INVESTIGATION"
    BLOCK_RELEASE = "BLOCK_RELEASE"
    BUG_CANDIDATE = "BUG_CANDIDATE"
    INCIDENT_CANDIDATE = "INCIDENT_CANDIDATE"


class DecisionStrategy(str, Enum):
    RETRY_3X = "retry_3x"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    INCREASE_TIMEOUT = "increase_timeout"
    ISOLATE_TEST = "isolate_test"
    RERUN_SUBSET = "rerun_subset"
    QUARANTINE_TEST = "quarantine_test"
    BLOCK_AND_ESCALATE = "block_and_escalate"
    INVESTIGATE_BACKEND = "investigate_backend"
    INVESTIGATE_INFRA = "investigate_infra"
    INVESTIGATE_DATA = "investigate_data"


@dataclass(slots=True)
class GovernanceFlags:
    allow_auto_rerun: bool = True
    allow_auto_suppress: bool = False
    allow_auto_block_release: bool = True
    require_manual_review_on_critical: bool = True
    allow_bug_candidate: bool = True
    allow_incident_candidate: bool = True


@dataclass(slots=True)
class DecisionPolicyProfile:
    profile_name: str
    block_threshold: float
    escalate_threshold: float
    rerun_threshold: float
    ambiguity_penalty: float
    critical_recurrence_block_count: int
    release_critical_boost: float
    min_action_effectiveness_for_rerun: float
    ambiguous_manual_review_confidence: float
    flaky_suppress_recurrence: int
    bug_candidate_recurrence: int
    incident_candidate_recurrence: int
    severity_weights: dict[str, float] = field(default_factory=dict)
    memory_resolution_weights: dict[str, float] = field(default_factory=dict)
    recurrence_weight: float = 0.25
    action_effectiveness_weight: float = 0.2
    release_critical_weight: float = 0.2
    protected_path_weight: float = 0.1
    flaky_bonus: float = 0.12
    new_memory_uncertainty_penalty: float = 0.1


@dataclass(slots=True)
class DecisionPolicyInput:
    adapter_id: str
    project_id: Optional[str]
    run_id: str
    plugin: Optional[str]
    execution_path: str
    severity: str
    confidence: float
    memory_resolution_type: MemoryResolutionType | str
    memory_confidence: float
    occurrence_count: int
    recurrence_score: float = 0.0
    flaky: bool = False
    best_action: Optional[dict[str, Any]] = None
    best_action_effectiveness: float = 0.0
    release_critical: bool = False
    protected_path: bool = False
    ci_mode: str = "default"
    governance_flags: GovernanceFlags = field(default_factory=GovernanceFlags)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def memory_resolution_value(self) -> str:
        raw = self.memory_resolution_type
        if isinstance(raw, MemoryResolutionType):
            return raw.value
        return str(raw).strip().upper()


@dataclass(slots=True)
class DecisionPolicyResult:
    primary_decision: DecisionPolicyType
    strategy: Optional[DecisionStrategy]
    rationale: str
    confidence: float
    decision_score: float
    governance_flags: GovernanceFlags
    secondary_signals: dict[str, Any]
    should_block_release: bool
    should_trigger_rerun: bool
    should_escalate: bool
    should_open_bug_candidate: bool
    should_open_incident_candidate: bool
    should_request_manual_review: bool
    recommended_owner: Optional[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "primary_decision": self.primary_decision.value,
            "strategy": self.strategy.value if self.strategy else None,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "decision_score": self.decision_score,
            "governance_flags": {
                "allow_auto_rerun": self.governance_flags.allow_auto_rerun,
                "allow_auto_suppress": self.governance_flags.allow_auto_suppress,
                "allow_auto_block_release": self.governance_flags.allow_auto_block_release,
                "require_manual_review_on_critical": self.governance_flags.require_manual_review_on_critical,
                "allow_bug_candidate": self.governance_flags.allow_bug_candidate,
                "allow_incident_candidate": self.governance_flags.allow_incident_candidate,
            },
            "secondary_signals": self.secondary_signals,
            "should_block_release": self.should_block_release,
            "should_trigger_rerun": self.should_trigger_rerun,
            "should_escalate": self.should_escalate,
            "should_open_bug_candidate": self.should_open_bug_candidate,
            "should_open_incident_candidate": self.should_open_incident_candidate,
            "should_request_manual_review": self.should_request_manual_review,
            "recommended_owner": self.recommended_owner,
            "metadata": self.metadata,
        }


def parse_env_governance(default: Optional[GovernanceFlags] = None) -> GovernanceFlags:
    base = default or GovernanceFlags()

    def _bool(name: str, fallback: bool) -> bool:
        raw = os.getenv(name, "").strip().lower()
        if not raw:
            return fallback
        return raw in {"1", "true", "yes", "y", "on"}

    return GovernanceFlags(
        allow_auto_rerun=_bool("DECISION_ALLOW_AUTO_RERUN", base.allow_auto_rerun),
        allow_auto_suppress=_bool("DECISION_ALLOW_AUTO_SUPPRESS", base.allow_auto_suppress),
        allow_auto_block_release=_bool("DECISION_ALLOW_AUTO_BLOCK_RELEASE", base.allow_auto_block_release),
        require_manual_review_on_critical=_bool(
            "DECISION_REQUIRE_MANUAL_REVIEW_ON_CRITICAL",
            base.require_manual_review_on_critical,
        ),
        allow_bug_candidate=_bool("DECISION_ALLOW_BUG_CANDIDATE", base.allow_bug_candidate),
        allow_incident_candidate=_bool("DECISION_ALLOW_INCIDENT_CANDIDATE", base.allow_incident_candidate),
    )
