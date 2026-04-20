from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import List

from ..domain.dedupe import CandidateDedupService
from ..domain.formatting import (
    build_bug_title,
    build_candidate_id,
    build_summary,
    collect_default_evidence_refs,
    normalized_title_key,
    to_jsonable,
)
from ..domain.models import (
    BugCandidateArtifact,
    BugCandidateInput,
    CandidateConfig,
    CandidateGenerationResult,
    CandidateGovernanceFlags,
    CandidateSuppressionRecord,
    CandidateType,
    GenerationStatus,
    load_candidate_config_from_env,
)
from ..domain.rules import evaluate_bug_candidate_eligibility
from ..infrastructure.artifact_writer import CandidateArtifactWriter
from ..infrastructure.local_index_store import LocalCandidateIndexStore


class BugAutoGenerator:
    def __init__(
        self,
        *,
        config: CandidateConfig | None = None,
        governance: CandidateGovernanceFlags | None = None,
        dedupe_service: CandidateDedupService | None = None,
        writer: CandidateArtifactWriter | None = None,
        index_store: LocalCandidateIndexStore | None = None,
    ) -> None:
        self.config = config or load_candidate_config_from_env()
        self.governance = governance or CandidateGovernanceFlags(
            allow_auto_update_existing_candidate=self.config.candidate_allow_auto_update_existing,
            require_manual_review_for_ambiguous=self.config.candidate_require_manual_review_for_ambiguous,
        )
        self.index_store = index_store or LocalCandidateIndexStore(Path(self.config.root_dir))
        self.writer = writer or CandidateArtifactWriter(Path(self.config.root_dir), self.index_store)
        self.dedupe = dedupe_service or CandidateDedupService(
            allow_auto_update_existing_candidate=self.governance.allow_auto_update_existing_candidate
        )

    def evaluate_bug_candidate(self, input_obj: BugCandidateInput) -> tuple[bool, List[str]]:
        return evaluate_bug_candidate_eligibility(input_obj, self.config, self.governance)

    def build_bug_artifact(self, input_obj: BugCandidateInput, *, candidate_id: str, duplicate_of: str = "") -> BugCandidateArtifact:
        title = build_bug_title(input_obj)
        summary = build_summary(input_obj, candidate_type=CandidateType.BUG)
        owner = "qa_automation"
        if input_obj.decision_result and input_obj.decision_result.recommended_owner:
            owner = input_obj.decision_result.recommended_owner

        return BugCandidateArtifact(
            candidate_id=candidate_id,
            artifact_type=CandidateType.BUG.value,
            title=title,
            summary=summary,
            severity=input_obj.severity,
            confidence=input_obj.confidence,
            recurrence=input_obj.occurrence_count,
            recommended_owner=owner,
            evidence_refs=collect_default_evidence_refs(input_obj),
            rationale=[
                "Recurring non-transient issue passed deterministic bug candidate eligibility.",
                f"memory_resolution_type={input_obj.memory_resolution_type}",
            ],
            duplicate_of=duplicate_of,
            generation_status=GenerationStatus.CREATED.value,
            root_cause=input_obj.root_cause,
            metadata={
                "adapter_id": input_obj.adapter_id,
                "project_id": input_obj.project_id,
                "run_id": input_obj.run_id,
                "failure_id": input_obj.failure_id,
                "memory_id": input_obj.memory_id,
                "signature_hash": input_obj.signature_hash,
                "decision_primary": input_obj.decision_result.primary_decision.value if input_obj.decision_result else "",
                "self_healing_success": input_obj.self_healing_result.success if input_obj.self_healing_result else None,
            },
        )

    def _write_suppression(
        self,
        input_obj: BugCandidateInput,
        rationale: List[str],
    ) -> CandidateGenerationResult:
        suppression_id = build_candidate_id(
            CandidateType.SUPPRESSION,
            f"bug:{input_obj.adapter_id}:{input_obj.project_id}:{input_obj.memory_id}:{input_obj.signature_hash}:{'|'.join(rationale)}",
        )
        record = CandidateSuppressionRecord(
            suppression_id=suppression_id,
            candidate_type=CandidateType.BUG.value,
            adapter_id=input_obj.adapter_id,
            project_id=input_obj.project_id,
            run_id=input_obj.run_id,
            failure_id=input_obj.failure_id,
            memory_id=input_obj.memory_id,
            signature_hash=input_obj.signature_hash,
            rationale=rationale,
            metadata={"severity": input_obj.severity, "confidence": input_obj.confidence},
        )
        path = self.writer.write_suppression_record(record)
        return CandidateGenerationResult(
            generated=False,
            candidate_type=CandidateType.BUG.value,
            candidate_id="",
            artifact=to_jsonable(record),
            dedup_result=None,
            rationale=rationale,
            metadata={"suppression_path": path},
        )

    def generate_bug_candidate(self, input_obj: BugCandidateInput) -> CandidateGenerationResult:
        eligible, reasons = self.evaluate_bug_candidate(input_obj)
        if not eligible:
            return self._write_suppression(input_obj, reasons)

        title = build_bug_title(input_obj)
        title_key = normalized_title_key([title, input_obj.execution_path])
        candidate_key = self.dedupe.build_candidate_key(
            candidate_type=CandidateType.BUG,
            adapter_id=input_obj.adapter_id,
            project_id=input_obj.project_id,
            memory_id=input_obj.memory_id,
            signature_hash=input_obj.signature_hash,
            title_key=title_key,
        )
        existing = self.index_store.find_by_key("bug_index.json", candidate_key)
        dedup = self.dedupe.dedupe(candidate_key=candidate_key, existing_entry=existing)

        candidate_id = dedup.existing_candidate_id or build_candidate_id(CandidateType.BUG, candidate_key)
        artifact = self.build_bug_artifact(input_obj, candidate_id=candidate_id, duplicate_of=dedup.existing_candidate_id)

        if dedup.action == "skip":
            artifact.generation_status = GenerationStatus.DUPLICATE.value
            path = self.writer.write_suppression_record(
                CandidateSuppressionRecord(
                    suppression_id=build_candidate_id(CandidateType.SUPPRESSION, candidate_key + ":dup"),
                    candidate_type=CandidateType.BUG.value,
                    adapter_id=input_obj.adapter_id,
                    project_id=input_obj.project_id,
                    run_id=input_obj.run_id,
                    failure_id=input_obj.failure_id,
                    memory_id=input_obj.memory_id,
                    signature_hash=input_obj.signature_hash,
                    rationale=[dedup.rationale],
                    metadata={"duplicate_candidate_id": dedup.existing_candidate_id},
                )
            )
            return CandidateGenerationResult(
                generated=False,
                candidate_type=CandidateType.BUG.value,
                candidate_id=dedup.existing_candidate_id,
                artifact=to_jsonable(artifact),
                dedup_result=dedup,
                rationale=[dedup.rationale],
                metadata={"suppression_path": path},
            )

        if dedup.action == "update":
            artifact.generation_status = GenerationStatus.UPDATED.value
            path = self.writer.update_existing_candidate(
                candidate_type=CandidateType.BUG,
                candidate_id=candidate_id,
                artifact=artifact,
            )
        else:
            path = self.writer.write_candidate(candidate_type=CandidateType.BUG, artifact=artifact)

        self.writer.write_candidate_index(
            index_name="bug_index.json",
            entry={
                "candidate_key": candidate_key,
                "candidate_id": candidate_id,
                "status": "open",
                "title": artifact.title,
                "artifact_type": CandidateType.BUG.value,
                "memory_id": input_obj.memory_id,
                "signature_hash": input_obj.signature_hash,
                "adapter_id": input_obj.adapter_id,
                "project_id": input_obj.project_id,
                "artifact_path": path,
            },
        )

        return CandidateGenerationResult(
            generated=True,
            candidate_type=CandidateType.BUG.value,
            candidate_id=candidate_id,
            artifact=to_jsonable(artifact),
            dedup_result=dedup,
            rationale=reasons,
            metadata={"artifact_path": path},
        )
