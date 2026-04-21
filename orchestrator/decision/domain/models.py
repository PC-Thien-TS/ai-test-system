from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MemoryResolutionType(str, Enum):
    EXACT_MATCH = "EXACT_MATCH"
    SIMILAR_MATCH = "SIMILAR_MATCH"
    AMBIGUOUS_MATCH = "AMBIGUOUS_MATCH"
    NEW_MEMORY = "NEW_MEMORY"


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


@dataclass
class GovernanceFlags:
    allow_auto_rerun: bool = True
    allow_auto_suppress: bool = False
    allow_auto_block_release: bool = True
    require_manual_review_on_critical: bool = True
    allow_bug_candidate: bool = True
    allow_incident_candidate: bool = True


@dataclass
class DecisionPolicyProfile:
    profile_name: str
    block_threshold: float = 0.80
    escalate_threshold: float = 0.60
    rerun_threshold: float = 0.45
    ambiguity_penalty: float = 0.20
    critical_recurrence_block_count: int = 3
    release_critical_boost: float = 0.20
    min_action_effectiveness_for_rerun: float = 0.55
    bug_candidate_min_occurrences: int = 2
    incident_candidate_min_occurrences: int = 3
    severity_weights: Dict[str, float] = field(
        default_factory=lambda: {
            SeverityLevel.LOW.value: 0.20,
            SeverityLevel.MEDIUM.value: 0.45,
            SeverityLevel.HIGH.value: 0.72,
            SeverityLevel.CRITICAL.value: 0.92,
        }
    )
    component_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "severity": 0.35,
            "recurrence": 0.20,
            "memory_certainty": 0.20,
            "release_criticality": 0.15,
            "action_effectiveness": 0.10,
        }
    )
    flaky_suppression_bonus: float = 0.08
    new_memory_uncertainty_penalty: float = 0.06
    governance_defaults: GovernanceFlags = field(default_factory=GovernanceFlags)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionPolicyInput:
    adapter_id: str
    project_id: str
    run_id: str
    plugin: Optional[str] = None
    execution_path: Optional[str] = None
    failure_summary: Optional[str] = None
    triage_root_cause: Optional[str] = None
    severity: str = SeverityLevel.MEDIUM.value
    confidence: float = 0.50
    memory_resolution_type: str = MemoryResolutionType.NEW_MEMORY.value
    memory_confidence: float = 0.0
    occurrence_count: int = 1
    recurrence_score: Optional[float] = None
    flaky: bool = False
    best_action: Optional[str] = None
    best_action_effectiveness: Optional[float] = None
    release_critical: bool = False
    protected_path: bool = False
    ci_mode: Optional[str] = None
    governance_flags: Optional[GovernanceFlags] = None
    release_context: Dict[str, Any] = field(default_factory=dict)
    ci_context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def severity_level(self) -> SeverityLevel:
        try:
            return SeverityLevel(str(self.severity).lower())
        except ValueError:
            return SeverityLevel.MEDIUM

    def resolution_type(self) -> MemoryResolutionType:
        try:
            return MemoryResolutionType(str(self.memory_resolution_type))
        except ValueError:
            return MemoryResolutionType.NEW_MEMORY


@dataclass
class DecisionPolicyResult:
    primary_decision: DecisionPolicyType
    strategy: Optional[DecisionStrategy]
    rationale: List[str]
    confidence: float
    decision_score: float
    governance_flags: GovernanceFlags
    secondary_signals: Dict[str, Any]
    secondary_decisions: List[DecisionPolicyType]
    should_block_release: bool
    should_trigger_rerun: bool
    should_escalate: bool
    should_open_bug_candidate: bool
    should_open_incident_candidate: bool
    should_request_manual_review: bool
    recommended_owner: Optional[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def seen_count(input_data: DecisionPolicyInput) -> int:
    raw = input_data.metadata.get("seen_count")
    if raw is None:
        raw = input_data.occurrence_count
    return max(1, _safe_int(raw, default=max(1, input_data.occurrence_count)))


def rerun_history_counts(input_data: DecisionPolicyInput) -> tuple[int, int]:
    success_count = max(0, _safe_int(input_data.metadata.get("rerun_success_count"), 0))
    failure_count = max(0, _safe_int(input_data.metadata.get("rerun_failure_count"), 0))
    return success_count, failure_count


def rerun_success_rate(input_data: DecisionPolicyInput) -> Optional[float]:
    success_count, failure_count = rerun_history_counts(input_data)
    total = success_count + failure_count
    if total <= 0:
        return None
    return clamp01(success_count / float(total))


def historical_action_effectiveness(input_data: DecisionPolicyInput) -> float:
    rate = rerun_success_rate(input_data)
    if rate is not None:
        return rate
    return clamp01(input_data.best_action_effectiveness or 0.0)


def combine_confidence(signal_confidence: float, memory_confidence: float, resolution: MemoryResolutionType) -> float:
    base = (0.55 * clamp01(signal_confidence)) + (0.45 * clamp01(memory_confidence))
    if resolution == MemoryResolutionType.EXACT_MATCH:
        base += 0.10
    elif resolution == MemoryResolutionType.AMBIGUOUS_MATCH:
        base -= 0.10
    elif resolution == MemoryResolutionType.NEW_MEMORY:
        base -= 0.05
    return clamp01(base)


def merge_governance(profile_flags: GovernanceFlags, input_flags: Optional[GovernanceFlags]) -> GovernanceFlags:
    if input_flags is None:
        return profile_flags
    return GovernanceFlags(
        allow_auto_rerun=input_flags.allow_auto_rerun,
        allow_auto_suppress=input_flags.allow_auto_suppress,
        allow_auto_block_release=input_flags.allow_auto_block_release,
        require_manual_review_on_critical=input_flags.require_manual_review_on_critical,
        allow_bug_candidate=input_flags.allow_bug_candidate,
        allow_incident_candidate=input_flags.allow_incident_candidate,
    )


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def parse_env_governance(base: Optional[GovernanceFlags] = None) -> GovernanceFlags:
    flags = base or GovernanceFlags()
    return GovernanceFlags(
        allow_auto_rerun=_env_bool("DECISION_ALLOW_AUTO_RERUN", flags.allow_auto_rerun),
        allow_auto_suppress=_env_bool("DECISION_ALLOW_AUTO_SUPPRESS", flags.allow_auto_suppress),
        allow_auto_block_release=_env_bool("DECISION_ALLOW_AUTO_BLOCK_RELEASE", flags.allow_auto_block_release),
        require_manual_review_on_critical=_env_bool(
            "DECISION_REQUIRE_MANUAL_REVIEW_ON_CRITICAL", flags.require_manual_review_on_critical
        ),
        allow_bug_candidate=_env_bool("DECISION_ALLOW_BUG_CANDIDATE", flags.allow_bug_candidate),
        allow_incident_candidate=_env_bool("DECISION_ALLOW_INCIDENT_CANDIDATE", flags.allow_incident_candidate),
    )
