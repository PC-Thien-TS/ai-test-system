"""Requirement-to-domain mapping for RankMate requirement-aware generation."""

from __future__ import annotations

from typing import List

from orchestrator.advanced_qa.requirement_models import Requirement
from orchestrator.advanced_qa.requirement_rules import (
    dedupe_preserve_order,
    detect_flows,
    detect_modules,
    detect_roles,
    normalize_module_name,
    tokenize_text,
)


class RequirementMapper:
    """Map normalized requirements to RankMate modules and flow families."""

    def map_requirement(self, requirement: Requirement) -> Requirement:
        """Map a single requirement to canonical modules and related flows."""

        text = tokenize_text(
            [
                requirement.title,
                requirement.description,
                " ".join(requirement.acceptance_criteria),
                " ".join(requirement.business_rules),
                " ".join(requirement.risk_hints),
                " ".join(requirement.related_flows),
                requirement.module or "",
                requirement.submodule or "",
            ]
        )

        mapped_modules: List[str] = []

        if requirement.module:
            normalized_existing = normalize_module_name(requirement.module)
            if normalized_existing:
                mapped_modules.append(normalized_existing)

        mapped_modules.extend(detect_modules(text))
        mapped_modules = dedupe_preserve_order(mapped_modules)

        if not mapped_modules:
            mapped_modules = ["Exploratory High-Risk Flows"]

        requirement.module = mapped_modules[0]
        requirement.metadata["mapped_modules"] = mapped_modules

        if requirement.roles:
            role_values = dedupe_preserve_order(requirement.roles)
        else:
            role_values = []

        role_values.extend(detect_roles(text))
        requirement.roles = dedupe_preserve_order(role_values)

        mapped_flows: List[str] = []
        mapped_flows.extend(requirement.related_flows)
        mapped_flows.extend(detect_flows(text))
        requirement.related_flows = dedupe_preserve_order(mapped_flows)

        if requirement.submodule:
            requirement.submodule = requirement.submodule.strip()
        else:
            requirement.submodule = self._derive_submodule(text)

        return requirement

    def map_requirements(self, requirements: List[Requirement]) -> List[Requirement]:
        """Map a list of requirements to modules and flows."""

        return [self.map_requirement(requirement) for requirement in requirements]

    def _derive_submodule(self, text: str) -> str | None:
        """Derive a simple submodule label from requirement text."""

        candidates = {
            "callback": "Callback",
            "checkout": "Checkout",
            "cart": "Cart",
            "search": "Search",
            "verification": "Verification",
            "confirm": "Confirmation",
            "reject": "Rejection",
            "state transition": "State Transition",
            "payment": "Payment",
        }

        for keyword, label in candidates.items():
            if keyword in text:
                return label

        return None
