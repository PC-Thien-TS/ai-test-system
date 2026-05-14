"""Manual test case generation for Manual QA Phase 1."""

from __future__ import annotations

from typing import Iterable, List

from orchestrator.manual_qa.models import ManualTestCase, NormalizedRequirement


class ManualTestCaseGenerator:
    """Generate deterministic positive and negative manual test cases."""

    _NEGATIVE_HINTS = (
        "invalid",
        "error",
        "required",
        "validation",
        "permission",
        "role",
        "unauthorized",
        "forbidden",
        "limit",
        "locked",
        "fail",
        "failed",
        "empty",
        "missing",
    )

    def generate(self, requirements: Iterable[NormalizedRequirement]) -> List[ManualTestCase]:
        cases: List[ManualTestCase] = []
        case_index = 1

        for requirement in requirements:
            cases.append(self._build_positive_case(requirement, case_index))
            case_index += 1

            if self._needs_negative_case(requirement):
                cases.append(self._build_negative_case(requirement, case_index))
                case_index += 1

        return cases

    def _build_positive_case(self, requirement: NormalizedRequirement, index: int) -> ManualTestCase:
        expected_result = (
            requirement.acceptance_criteria[0]
            if requirement.acceptance_criteria
            else f"{requirement.title} works as described."
        )
        steps = [
            f"Open the {requirement.module} flow for requirement {requirement.requirement_id}.",
            f"Perform the primary user action for: {requirement.title}.",
        ]
        if requirement.acceptance_criteria:
            steps.extend(
                f"Confirm acceptance criterion: {criterion}."
                for criterion in requirement.acceptance_criteria
            )
        else:
            steps.append("Verify the observed behavior matches the requirement description.")

        preconditions = [f"Tester can access the {requirement.module} module."]
        if requirement.roles:
            preconditions.append(f"Relevant roles are available: {', '.join(requirement.roles)}.")

        return ManualTestCase(
            test_case_id=f"TC-{index:03d}",
            requirement_ids=[requirement.requirement_id],
            module=requirement.module,
            title=f"{requirement.title} - positive path",
            preconditions=preconditions,
            steps=steps,
            expected_result=expected_result,
            priority=requirement.priority,
            test_type="Positive",
            metadata={"generated_from": requirement.requirement_id},
        )

    def _build_negative_case(self, requirement: NormalizedRequirement, index: int) -> ManualTestCase:
        return ManualTestCase(
            test_case_id=f"TC-{index:03d}",
            requirement_ids=[requirement.requirement_id],
            module=requirement.module,
            title=f"{requirement.title} - negative or validation path",
            preconditions=[f"Tester can trigger an invalid or restricted action in {requirement.module}."],
            steps=[
                f"Navigate to the flow for requirement {requirement.requirement_id}.",
                "Submit invalid, empty, restricted, or otherwise disallowed input.",
                "Observe the system response and verify guard behavior.",
            ],
            expected_result="System rejects the invalid or restricted action with a controlled result.",
            priority=requirement.priority,
            test_type="Negative",
            metadata={"generated_from": requirement.requirement_id, "reason": "negative_hint_detected"},
        )

    def _needs_negative_case(self, requirement: NormalizedRequirement) -> bool:
        text = " ".join(
            [
                requirement.title,
                requirement.description,
                " ".join(requirement.acceptance_criteria),
                " ".join(requirement.roles),
            ]
        ).lower()
        return any(hint in text for hint in self._NEGATIVE_HINTS)
