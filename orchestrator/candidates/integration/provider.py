from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ..application.bug_engine import BugAutoGenerator
from ..application.coordinator import CandidateGenerationCoordinator
from ..application.incident_engine import IncidentCandidateEngine
from ..domain.dedupe import CandidateDedupService
from ..domain.models import CandidateConfig, CandidateGovernanceFlags, load_candidate_config_from_env
from ..infrastructure.artifact_writer import CandidateArtifactWriter
from ..infrastructure.local_index_store import LocalCandidateIndexStore


def build_candidate_generation_coordinator(
    *,
    config: CandidateConfig | None = None,
    governance: CandidateGovernanceFlags | None = None,
    lark_notifier: Optional[Any] = None,
) -> CandidateGenerationCoordinator:
    resolved_config = config or load_candidate_config_from_env()
    resolved_governance = governance or CandidateGovernanceFlags(
        allow_auto_update_existing_candidate=resolved_config.candidate_allow_auto_update_existing,
        require_manual_review_for_ambiguous=resolved_config.candidate_require_manual_review_for_ambiguous,
    )

    index_store = LocalCandidateIndexStore(Path(resolved_config.root_dir))
    writer = CandidateArtifactWriter(Path(resolved_config.root_dir), index_store)
    dedupe = CandidateDedupService(
        allow_auto_update_existing_candidate=resolved_governance.allow_auto_update_existing_candidate
    )
    bug_engine = BugAutoGenerator(
        config=resolved_config,
        governance=resolved_governance,
        dedupe_service=dedupe,
        writer=writer,
        index_store=index_store,
    )
    incident_engine = IncidentCandidateEngine(
        config=resolved_config,
        governance=resolved_governance,
        dedupe_service=dedupe,
        writer=writer,
        index_store=index_store,
    )
    return CandidateGenerationCoordinator(
        bug_engine=bug_engine,
        incident_engine=incident_engine,
        lark_notifier=lark_notifier,
    )
