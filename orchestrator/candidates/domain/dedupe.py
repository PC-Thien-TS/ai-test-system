from __future__ import annotations

from dataclasses import dataclass

from .models import CandidateDedupResult, CandidateType


@dataclass
class CandidateDedupService:
    allow_auto_update_existing_candidate: bool = True

    def build_candidate_key(
        self,
        *,
        candidate_type: CandidateType,
        adapter_id: str,
        project_id: str,
        memory_id: str,
        signature_hash: str,
        title_key: str,
    ) -> str:
        stable_identity = memory_id or signature_hash
        return f"{candidate_type.value}:{adapter_id}:{project_id}:{stable_identity}:{title_key}"

    def dedupe(self, *, candidate_key: str, existing_entry: dict | None) -> CandidateDedupResult:
        if not existing_entry:
            return CandidateDedupResult(
                is_duplicate=False,
                existing_candidate_id="",
                action="create",
                rationale="No existing candidate for key; creating new artifact.",
            )
        status = str(existing_entry.get("status", "open")).lower()
        cid = str(existing_entry.get("candidate_id", ""))
        if self.allow_auto_update_existing_candidate and status in {"open", "active", "triaged"}:
            return CandidateDedupResult(
                is_duplicate=True,
                existing_candidate_id=cid,
                action="update",
                rationale="Existing active candidate found; updating existing artifact.",
            )
        return CandidateDedupResult(
            is_duplicate=True,
            existing_candidate_id=cid,
            action="skip",
            rationale="Duplicate candidate exists and auto-update is disabled/inapplicable.",
        )

