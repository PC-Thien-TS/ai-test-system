from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from orchestrator.decision.domain.models import DecisionPolicyResult
from orchestrator.self_healing.domain.models import ActionExecutionResult


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CandidateType(str, Enum):
    BUG = "bug_candidate"
    INCIDENT = "incident_candidate"
    SUPPRESSION = "candidate_suppression"


class GenerationStatus(str, Enum):
    CREATED = "created"
    UPDATED = "updated"
    DUPLICATE = "duplicate"
    SUPPRESSED = "suppressed"
    SKIPPED = "skipped"


@dataclass
class CandidateGovernanceFlags:
    allow_bug_generation: bool = True
    allow_incident_generation: bool = True
    require_manual_review_for_ambiguous: bool = True
    allow_auto_update_existing_candidate: bool = True
    allow_generation_on_similar_match_only: bool = True


@dataclass
class CandidateConfig:
    bug_auto_generation_enabled: bool = True
    incident_auto_generation_enabled: bool = True
    bug_min_occurrences: int = 2
    incident_min_occurrences: int = 3
    bug_min_confidence: float = 0.55
    incident_min_confidence: float = 0.70
    bug_allow_similar_match: bool = True
    incident_require_release_critical: bool = True
    candidate_allow_auto_update_existing: bool = True
    candidate_require_manual_review_for_ambiguous: bool = True
    root_dir: str = "artifacts/candidate_artifacts"


@dataclass
class CandidateInputBase:
    adapter_id: str
    project_id: str
    run_id: str
    failure_id: str
    memory_id: str
    signature_hash: str
    memory_resolution_type: str
    root_cause: str
    severity: str
    confidence: float
    occurrence_count: int
    recurrence_score: Optional[float] = None
    flaky: bool = False
    decision_result: Optional[DecisionPolicyResult] = None
    self_healing_result: Optional[ActionExecutionResult] = None
    evidence_refs: List[str] = field(default_factory=list)
    execution_path: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def release_critical(self) -> bool:
        if self.decision_result is None:
            return bool(self.metadata.get("release_critical", False))
        return bool(self.decision_result.secondary_signals.get("release_critical", False))

    @property
    def protected_path(self) -> bool:
        if self.decision_result is None:
            return bool(self.metadata.get("protected_path", False))
        return bool(self.decision_result.secondary_signals.get("protected_path", False))


@dataclass
class BugCandidateInput(CandidateInputBase):
    pass


@dataclass
class IncidentCandidateInput(CandidateInputBase):
    impact_scope: str = "service_path"


@dataclass
class CandidateDedupResult:
    is_duplicate: bool
    existing_candidate_id: str = ""
    action: str = "create"  # create / update / skip
    rationale: str = ""


@dataclass
class CandidateArtifactBase:
    candidate_id: str
    artifact_type: str
    title: str
    summary: str
    severity: str
    confidence: float
    recurrence: int
    recommended_owner: str
    evidence_refs: List[str]
    rationale: List[str]
    duplicate_of: str = ""
    generation_status: str = GenerationStatus.CREATED.value
    timestamp: str = field(default_factory=utc_now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BugCandidateArtifact(CandidateArtifactBase):
    root_cause: str = ""


@dataclass
class IncidentCandidateArtifact(CandidateArtifactBase):
    impact_scope: str = "service_path"
    escalation_reason: str = ""


@dataclass
class CandidateSuppressionRecord:
    suppression_id: str
    candidate_type: str
    adapter_id: str
    project_id: str
    run_id: str
    failure_id: str
    memory_id: str
    signature_hash: str
    rationale: List[str]
    timestamp: str = field(default_factory=utc_now_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateGenerationResult:
    generated: bool
    candidate_type: str
    candidate_id: str = ""
    artifact: Optional[Dict[str, Any]] = None
    dedup_result: Optional[CandidateDedupResult] = None
    rationale: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def load_candidate_config_from_env() -> CandidateConfig:
    return CandidateConfig(
        bug_auto_generation_enabled=_env_bool("BUG_AUTO_GENERATION_ENABLED", True),
        incident_auto_generation_enabled=_env_bool("INCIDENT_AUTO_GENERATION_ENABLED", True),
        bug_min_occurrences=_env_int("BUG_MIN_OCCURRENCES", 2),
        incident_min_occurrences=_env_int("INCIDENT_MIN_OCCURRENCES", 3),
        bug_min_confidence=_env_float("BUG_MIN_CONFIDENCE", 0.55),
        incident_min_confidence=_env_float("INCIDENT_MIN_CONFIDENCE", 0.70),
        bug_allow_similar_match=_env_bool("BUG_ALLOW_SIMILAR_MATCH", True),
        incident_require_release_critical=_env_bool("INCIDENT_REQUIRE_RELEASE_CRITICAL", True),
        candidate_allow_auto_update_existing=_env_bool("CANDIDATE_ALLOW_AUTO_UPDATE_EXISTING", True),
        candidate_require_manual_review_for_ambiguous=_env_bool(
            "CANDIDATE_REQUIRE_MANUAL_REVIEW_FOR_AMBIGUOUS",
            True,
        ),
        root_dir=os.getenv("CANDIDATE_ARTIFACT_ROOT", "artifacts/candidate_artifacts"),
    )

