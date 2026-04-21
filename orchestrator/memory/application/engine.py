from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from orchestrator.memory.domain.models import (
    ActionEffectiveness,
    FailureActionRecord,
    IncomingFailureRecord,
    MemoryEngineConfig,
    MemoryResolutionResult,
    MemoryResolutionType,
)
from orchestrator.memory.domain.normalization import build_failure_signature
from orchestrator.memory.domain.scoring import (
    confidence_on_contradiction,
    confidence_on_exact_recurrence,
    confidence_on_similar_merge,
    update_action_effectiveness,
)
from orchestrator.storage.domain.models import FailureMemoryRecord
from orchestrator.storage.domain.repositories import MemoryRepository, VectorMemoryRepository


SEVERITY_RANK = {"unknown": 0, "p3": 1, "p2": 2, "p1": 3, "p0": 4, "critical": 5}
SUCCESS_RESULTS = {"success", "resolved", "mitigated", "improved"}


class FailureMemoryEngine:
    def __init__(
        self,
        *,
        memory_repository: MemoryRepository,
        vector_repository: VectorMemoryRepository,
        config: Optional[MemoryEngineConfig] = None,
    ):
        self._memory_repo = memory_repository
        self._vector_repo = vector_repository
        self._config = config or MemoryEngineConfig.from_env()

    def resolve_failure(self, incoming: IncomingFailureRecord) -> MemoryResolutionResult:
        signature = build_failure_signature(incoming)
        if self._config.exact_match_enabled:
            exact = self._memory_repo.lookup_by_signature(adapter_id=incoming.adapter_id, signature=signature)
            if exact:
                updated = self.update_memory(
                    existing=exact,
                    incoming=incoming,
                    strategy="exact",
                    similarity=1.0,
                )
                return MemoryResolutionResult(
                    resolution_type=MemoryResolutionType.EXACT_MATCH,
                    resolved_memory_id=updated.memory_id,
                    similarity=1.0,
                    confidence=updated.confidence,
                    matched_record=updated,
                    candidate_matches=[],
                    recommended_actions=list(updated.recommended_actions),
                    notes="Exact signature match found and updated.",
                )

        candidates = self._find_semantic_candidates(incoming)
        if not candidates:
            created = self.create_memory(incoming=incoming, signature=signature)
            return MemoryResolutionResult(
                resolution_type=MemoryResolutionType.NEW_MEMORY,
                resolved_memory_id=created.memory_id,
                similarity=0.0,
                confidence=created.confidence,
                matched_record=created,
                candidate_matches=[],
                recommended_actions=list(created.recommended_actions),
                notes="No exact or semantic candidate found; created new memory.",
            )

        top = candidates[0]
        second_score = float(candidates[1]["similarity"]) if len(candidates) > 1 else 0.0
        score_gap = float(top["similarity"]) - second_score
        top_record = top["record"]

        if float(top["similarity"]) >= self._config.auto_merge_threshold and score_gap >= self._config.ambiguous_gap_threshold:
            updated = self.merge_memory(existing=top_record, incoming=incoming, similarity=float(top["similarity"]))
            return MemoryResolutionResult(
                resolution_type=MemoryResolutionType.SIMILAR_MATCH,
                resolved_memory_id=updated.memory_id,
                similarity=float(top["similarity"]),
                confidence=updated.confidence,
                matched_record=updated,
                candidate_matches=self._candidate_payload(candidates),
                recommended_actions=list(updated.recommended_actions),
                notes="High-similarity semantic match auto-merged into existing memory.",
            )

        if (
            float(top["similarity"]) >= self._config.similarity_threshold
            and score_gap >= self._config.ambiguous_gap_threshold
        ):
            updated = self.update_memory(
                existing=top_record,
                incoming=incoming,
                strategy="similar",
                similarity=float(top["similarity"]),
            )
            return MemoryResolutionResult(
                resolution_type=MemoryResolutionType.SIMILAR_MATCH,
                resolved_memory_id=updated.memory_id,
                similarity=float(top["similarity"]),
                confidence=updated.confidence,
                matched_record=updated,
                candidate_matches=self._candidate_payload(candidates),
                recommended_actions=list(updated.recommended_actions),
                notes="Semantic match above threshold; updated matched memory.",
            )

        if float(top["similarity"]) >= self._config.ambiguous_threshold:
            return MemoryResolutionResult(
                resolution_type=MemoryResolutionType.AMBIGUOUS_MATCH,
                resolved_memory_id=top_record.memory_id,
                similarity=float(top["similarity"]),
                confidence=min(top_record.confidence, incoming.triage_confidence),
                matched_record=top_record,
                candidate_matches=self._candidate_payload(candidates),
                recommended_actions=list(top_record.recommended_actions),
                notes="Semantic candidates are ambiguous; no auto-merge performed.",
            )

        created = self.create_memory(incoming=incoming, signature=signature)
        return MemoryResolutionResult(
            resolution_type=MemoryResolutionType.NEW_MEMORY,
            resolved_memory_id=created.memory_id,
            similarity=float(top["similarity"]),
            confidence=created.confidence,
            matched_record=created,
            candidate_matches=self._candidate_payload(candidates),
            recommended_actions=list(created.recommended_actions),
            notes="Semantic candidates below threshold; created new memory.",
        )

    def create_memory(self, *, incoming: IncomingFailureRecord, signature=None) -> FailureMemoryRecord:
        resolved_signature = signature or build_failure_signature(incoming)
        root_cause = incoming.triage_root_cause or "unclassified_failure"
        confidence = max(min(incoming.triage_confidence, self._config.confidence_max), self._config.confidence_min)
        severity = (incoming.severity_hint or "unknown").lower()
        recommended = list(dict.fromkeys(incoming.recommended_actions))
        record = FailureMemoryRecord.new(
            adapter_id=incoming.adapter_id,
            project_id=incoming.project_id,
            signature=resolved_signature,
            root_cause=root_cause,
            severity=severity,
            confidence=confidence,
            recommended_actions=recommended,
            flaky=bool(incoming.metadata.get("flaky", False)),
            metadata=dict(incoming.metadata or {}),
        )
        persisted = self._memory_repo.upsert_memory(record)
        self._upsert_vector(persisted, incoming=incoming)
        return persisted

    def update_memory(
        self,
        *,
        existing: FailureMemoryRecord,
        incoming: IncomingFailureRecord,
        strategy: str,
        similarity: float,
    ) -> FailureMemoryRecord:
        now = datetime.now(timezone.utc)
        existing.last_seen = now
        existing.occurrence_count += 1
        existing.project_id = incoming.project_id or existing.project_id
        incoming_root = (incoming.triage_root_cause or "").strip()
        if incoming_root:
            if existing.root_cause and incoming_root.lower() != existing.root_cause.lower():
                existing.confidence = confidence_on_contradiction(existing.confidence, self._config)
                existing.action_history.append(
                    {
                        "timestamp": now.isoformat(),
                        "type": "root_cause_contradiction",
                        "incoming_root_cause": incoming_root,
                        "existing_root_cause": existing.root_cause,
                    }
                )
            else:
                existing.root_cause = incoming_root

        if strategy == "exact":
            existing.confidence = confidence_on_exact_recurrence(
                existing.confidence,
                incoming.triage_confidence,
                self._config,
            )
        elif strategy == "similar":
            existing.confidence = confidence_on_similar_merge(
                existing.confidence,
                incoming.triage_confidence,
                self._config,
            )

        existing.severity = self._max_severity(existing.severity, incoming.severity_hint)
        existing.recommended_actions = sorted(
            set(existing.recommended_actions).union(incoming.recommended_actions)
        )
        existing.metadata = dict(existing.metadata or {})
        existing.metadata.update(incoming.metadata or {})
        existing.metadata["last_resolution_strategy"] = strategy
        existing.metadata["last_similarity"] = similarity
        existing.signature_hash = existing.signature.hash()

        persisted = self._memory_repo.upsert_memory(existing)
        self._upsert_vector(persisted, incoming=incoming)
        return persisted

    def merge_memory(
        self,
        *,
        existing: FailureMemoryRecord,
        incoming: IncomingFailureRecord,
        similarity: float,
    ) -> FailureMemoryRecord:
        return self.update_memory(
            existing=existing,
            incoming=incoming,
            strategy="similar",
            similarity=similarity,
        )

    def record_action_outcome(
        self,
        *,
        memory_id: str,
        adapter_id: str,
        action_type: str,
        strategy: str,
        result: str,
        notes: str = "",
        source: str = "auto-healing",
    ) -> Optional[FailureMemoryRecord]:
        record = self._memory_repo.get_memory(memory_id, adapter_id=adapter_id)
        if record is None:
            return None

        now = datetime.now(timezone.utc)
        action = FailureActionRecord(
            action_type=action_type,
            strategy=strategy,
            timestamp=now,
            result=result,
            notes=notes,
            source=source,
        )
        record.action_history.append(action.to_dict())

        existing_map = dict(record.action_effectiveness or {})
        action_state = ActionEffectiveness.from_dict(
            dict(existing_map.get(action_type) or {"action_type": action_type})
        )
        success = result.strip().lower() in SUCCESS_RESULTS
        action_state = update_action_effectiveness(action_state, success=success)
        existing_map[action_type] = action_state.to_dict()
        record.action_effectiveness = existing_map

        if success:
            record.confidence = confidence_on_exact_recurrence(record.confidence, record.confidence, self._config)
        else:
            record.confidence = confidence_on_contradiction(record.confidence, self._config)

        record.last_seen = now
        persisted = self._memory_repo.upsert_memory(record)
        return persisted

    def get_best_action(self, *, memory_id: str, adapter_id: str) -> Optional[dict]:
        record = self._memory_repo.get_memory(memory_id, adapter_id=adapter_id)
        if record is None:
            return None

        best: Optional[ActionEffectiveness] = None
        for key, value in dict(record.action_effectiveness or {}).items():
            row = ActionEffectiveness.from_dict(dict(value or {"action_type": key}))
            if best is None or row.effectiveness_score > best.effectiveness_score:
                best = row
        if best is not None and best.action_type:
            return best.to_dict()

        if record.recommended_actions:
            return {
                "action_type": record.recommended_actions[0],
                "success_count": 0,
                "failure_count": 0,
                "effectiveness_score": 0.0,
            }
        return None

    def build_memory_context(
        self,
        *,
        resolution: Optional[MemoryResolutionResult] = None,
        memory_id: Optional[str] = None,
        adapter_id: Optional[str] = None,
    ) -> dict:
        record = None
        if resolution and resolution.matched_record:
            record = resolution.matched_record
        elif memory_id and adapter_id:
            record = self._memory_repo.get_memory(memory_id, adapter_id=adapter_id)

        if record is None:
            return {
                "has_memory": False,
                "memory_id": None,
                "recurrence_count": 0,
                "best_action": None,
                "severity": None,
                "confidence": None,
            }

        return {
            "has_memory": True,
            "memory_id": record.memory_id,
            "recurrence_count": record.occurrence_count,
            "best_action": self.get_best_action(memory_id=record.memory_id, adapter_id=record.adapter_id),
            "severity": record.severity,
            "confidence": record.confidence,
            "root_cause": record.root_cause,
            "recommended_actions": list(record.recommended_actions),
        }

    def _find_semantic_candidates(self, incoming: IncomingFailureRecord) -> list[dict]:
        if not self._config.semantic_match_enabled or not self._vector_repo.is_available:
            return []
        query = self._semantic_query_text(incoming)
        matches = self._vector_repo.search_similar(
            adapter_id=incoming.adapter_id,
            query_text=query,
            top_k=5,
            min_score=self._config.ambiguous_threshold,
        )
        candidates: list[dict] = []
        for match in matches:
            memory = self._memory_repo.get_memory(match.memory_id, adapter_id=incoming.adapter_id)
            if memory is None:
                continue
            candidates.append({"record": memory, "similarity": float(match.score), "reason": match.reason})
        candidates.sort(key=lambda x: x["similarity"], reverse=True)
        return candidates

    def _candidate_payload(self, candidates: list[dict]) -> list[dict]:
        payload: list[dict] = []
        for candidate in candidates:
            memory: FailureMemoryRecord = candidate["record"]
            payload.append(
                {
                    "memory_id": memory.memory_id,
                    "similarity": candidate["similarity"],
                    "reason": candidate["reason"],
                    "severity": memory.severity,
                    "confidence": memory.confidence,
                    "root_cause": memory.root_cause,
                    "occurrence_count": memory.occurrence_count,
                }
            )
        return payload

    def _semantic_query_text(self, incoming: IncomingFailureRecord) -> str:
        parts = [
            incoming.error_type,
            incoming.endpoint or "",
            incoming.plugin or "",
            incoming.component or "",
            incoming.message,
            incoming.triage_root_cause or "",
            " ".join(incoming.recommended_actions),
            incoming.stack_trace or "",
        ]
        return " | ".join(part for part in parts if part)

    def _upsert_vector(self, record: FailureMemoryRecord, *, incoming: IncomingFailureRecord) -> None:
        if not self._vector_repo.is_available:
            return
        semantic_text = self._semantic_query_text(incoming)
        self._vector_repo.upsert_vector(
            memory_id=record.memory_id,
            adapter_id=record.adapter_id,
            text=semantic_text,
            metadata={
                "severity": record.severity,
                "root_cause": record.root_cause,
                "signature_hash": record.signature_hash,
            },
        )

    @staticmethod
    def _max_severity(left: str, right: str) -> str:
        l = (left or "unknown").strip().lower()
        r = (right or "unknown").strip().lower()
        return l if SEVERITY_RANK.get(l, 0) >= SEVERITY_RANK.get(r, 0) else r
