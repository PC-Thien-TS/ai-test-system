"""Checklist generation for Manual QA Phase 1."""

from __future__ import annotations

from typing import Iterable, List

from orchestrator.manual_qa.models import ChecklistItem, NormalizedRequirement


class ChecklistGenerator:
    """Generate one or more deterministic checklist items per requirement."""

    def generate(self, requirements: Iterable[NormalizedRequirement]) -> List[ChecklistItem]:
        items: List[ChecklistItem] = []
        for index, requirement in enumerate(requirements, start=1):
            acceptance_text = ""
            if requirement.acceptance_criteria:
                acceptance_text = f" Validate: {requirement.acceptance_criteria[0]}"

            items.append(
                ChecklistItem(
                    checklist_id=f"CHK-{index:03d}",
                    requirement_id=requirement.requirement_id,
                    module=requirement.module,
                    title=f"Verify {requirement.title}",
                    description=(
                        f"Manually verify requirement {requirement.requirement_id} in module "
                        f"{requirement.module}.{acceptance_text}"
                    ).strip(),
                    priority=requirement.priority,
                )
            )
        return items
