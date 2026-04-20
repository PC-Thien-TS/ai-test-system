from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, List, Sequence

from .models import CandidateInputBase, CandidateType


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def normalized_title_key(parts: Sequence[str]) -> str:
    raw = " | ".join(_normalize_text(p).lower() for p in parts if p)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def build_candidate_id(candidate_type: CandidateType, key: str) -> str:
    short = hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]
    prefix = "BUG" if candidate_type == CandidateType.BUG else "INC"
    return f"{prefix}-{short}"


def build_bug_title(candidate_input: CandidateInputBase) -> str:
    adapter = candidate_input.adapter_id.upper()
    severity = candidate_input.severity.capitalize()
    path = candidate_input.execution_path or "unknown path"
    risk = "protected path" if (candidate_input.release_critical or candidate_input.protected_path) else "operational path"
    return f"[{adapter}][{severity}] Recurrent failure on {risk} ({path})"


def build_incident_title(candidate_input: CandidateInputBase) -> str:
    adapter = candidate_input.adapter_id.upper()
    severity = candidate_input.severity.capitalize()
    return f"[{adapter}][{severity}] Repeated release-impacting failure incident candidate"


def build_summary(candidate_input: CandidateInputBase, *, candidate_type: CandidateType) -> str:
    decision = candidate_input.decision_result.primary_decision.value if candidate_input.decision_result else "UNKNOWN"
    healed = "n/a"
    if candidate_input.self_healing_result is not None:
        healed = "success" if candidate_input.self_healing_result.success else "failed_or_unsafe"
    label = "bug" if candidate_type == CandidateType.BUG else "incident"
    return (
        f"Deterministic {label} candidate from recurring failure pattern. "
        f"Failure={candidate_input.failure_id}, memory={candidate_input.memory_id}, "
        f"occurrences={candidate_input.occurrence_count}, severity={candidate_input.severity}, "
        f"decision={decision}, self_healing={healed}. "
        f"Root cause hint: {candidate_input.root_cause or 'unknown'}."
    )


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {k: to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [to_jsonable(v) for v in value]
    return value


def collect_default_evidence_refs(candidate_input: CandidateInputBase) -> List[str]:
    refs = list(candidate_input.evidence_refs)
    refs.extend(
        [
            f"run:{candidate_input.run_id}",
            f"failure:{candidate_input.failure_id}",
            f"memory:{candidate_input.memory_id}",
            f"signature:{candidate_input.signature_hash}",
        ]
    )
    # preserve order but dedupe
    output = []
    seen = set()
    for item in refs:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output

