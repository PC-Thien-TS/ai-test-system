from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..domain.models import BugCandidateInput, CandidateGenerationResult, IncidentCandidateInput
from .bug_engine import BugAutoGenerator
from .incident_engine import IncidentCandidateEngine


@dataclass
class CandidateGenerationCoordinator:
    bug_engine: BugAutoGenerator
    incident_engine: IncidentCandidateEngine
    lark_notifier: Optional[Any] = None

    def generate_all(
        self,
        *,
        bug_input: BugCandidateInput,
        incident_input: IncidentCandidateInput,
    ) -> Dict[str, CandidateGenerationResult]:
        bug_result = self.bug_engine.generate_bug_candidate(bug_input)
        incident_result = self.incident_engine.generate_incident_candidate(incident_input)
        if self.lark_notifier is not None:
            try:
                self.lark_notifier.notify_candidate(candidate_result=bug_result, candidate_input=bug_input)
            except Exception:
                pass
            try:
                self.lark_notifier.notify_candidate(candidate_result=incident_result, candidate_input=incident_input)
            except Exception:
                pass
        return {
            "bug": bug_result,
            "incident": incident_result,
        }
