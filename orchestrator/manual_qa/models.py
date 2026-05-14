"""Deterministic Manual QA Phase 1 models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class ProjectProfile:
    """Manual QA project profile."""

    project_id: str
    name: str
    product_type: str
    description: str = ""
    owner: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedRequirement:
    """Normalized requirement used by downstream Manual QA generators."""

    requirement_id: str
    title: str
    description: str
    module: str = "General"
    priority: str = "Medium"
    roles: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    source_ref: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChecklistItem:
    """Manual tester checklist item derived from a requirement."""

    checklist_id: str
    requirement_id: str
    module: str
    title: str
    description: str
    priority: str
    checked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ManualTestCase:
    """Deterministic manual test case."""

    test_case_id: str
    requirement_ids: List[str]
    module: str
    title: str
    preconditions: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    expected_result: str = ""
    priority: str = "Medium"
    test_type: str = "Positive"
    status: str = "Not Run"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExportBundle:
    """Bundle used for stable exports."""

    project: ProjectProfile
    requirements: List[NormalizedRequirement] = field(default_factory=list)
    checklist_items: List[ChecklistItem] = field(default_factory=list)
    test_cases: List[ManualTestCase] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project": self.project.to_dict(),
            "requirements": [item.to_dict() for item in self.requirements],
            "checklist_items": [item.to_dict() for item in self.checklist_items],
            "test_cases": [item.to_dict() for item in self.test_cases],
            "metadata": dict(self.metadata),
        }
