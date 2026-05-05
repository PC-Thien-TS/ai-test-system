from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from orchestrator.advanced_qa.requirement_rules import dedupe_preserve_order, normalize_priority


@dataclass(frozen=True)
class GeneratedRequirementTestCase:
    test_case_id: str
    requirement_id: str
    title: str
    priority: str
    preconditions: list[str]
    steps: list[str]
    expected_result: str
    test_type: str
    automation_candidate: bool
    risk_level: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TestCaseGenerator:
    """Deterministically generate structured test cases from normalized requirements."""

    def generate(self, requirement: Mapping[str, Any]) -> list[dict[str, Any]]:
        normalized = self._normalize_requirement(requirement)
        cases: list[GeneratedRequirementTestCase] = []
        index = 1

        if normalized["business_flow"]:
            cases.append(
                self._build_case(
                    normalized,
                    index=index,
                    title=f"{normalized['title']} - happy path",
                    steps=self._build_happy_path_steps(normalized),
                    expected_result=self._happy_path_expected_result(normalized),
                    test_type="happy_path",
                    source="business_flow",
                    automation_candidate=True,
                )
            )
            index += 1

        for criterion in normalized["acceptance_criteria"]:
            cases.append(
                self._build_case(
                    normalized,
                    index=index,
                    title=f"{normalized['title']} - acceptance criteria",
                    steps=self._build_acceptance_steps(normalized, criterion),
                    expected_result=criterion,
                    test_type="acceptance",
                    source="acceptance_criteria",
                    automation_candidate=True,
                )
            )
            index += 1

        for scenario in normalized["test_scenarios"]:
            cases.append(
                self._build_case(
                    normalized,
                    index=index,
                    title=f"{normalized['title']} - scenario",
                    steps=self._build_scenario_steps(normalized, scenario),
                    expected_result=self._scenario_expected_result(normalized, scenario),
                    test_type="scenario",
                    source="test_scenarios",
                    automation_candidate=self._scenario_is_automation_candidate(normalized, scenario),
                )
            )
            index += 1

        if not cases:
            cases.append(
                self._build_case(
                    normalized,
                    index=index,
                    title=f"{normalized['title']} - exploratory fallback",
                    steps=self._build_fallback_steps(normalized),
                    expected_result="Requirement details need clarification before deterministic verification.",
                    test_type="fallback",
                    source="fallback",
                    automation_candidate=False,
                )
            )

        return [case.to_dict() for case in cases]

    def _normalize_requirement(self, requirement: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(requirement, Mapping):
            raise TypeError("requirement must be a mapping")

        return {
            "requirement_id": self._as_str(requirement.get("requirement_id")) or "REQ-UNKNOWN",
            "title": self._as_str(requirement.get("title")) or "Untitled Requirement",
            "priority": normalize_priority(self._as_str(requirement.get("priority"))),
            "preconditions": self._as_list(requirement.get("preconditions")),
            "business_flow": self._as_list(requirement.get("business_flow")),
            "acceptance_criteria": self._as_list(requirement.get("acceptance_criteria")),
            "test_scenarios": self._as_list(requirement.get("test_scenarios")),
            "risk_level": self._as_str(requirement.get("risk_level")).lower() or "low",
            "feature": self._as_str(requirement.get("feature")),
            "unknowns": self._as_list(requirement.get("unknowns")),
        }

    def _build_case(
        self,
        requirement: dict[str, Any],
        *,
        index: int,
        title: str,
        steps: list[str],
        expected_result: str,
        test_type: str,
        source: str,
        automation_candidate: bool,
    ) -> GeneratedRequirementTestCase:
        return GeneratedRequirementTestCase(
            test_case_id=f"TC-{requirement['requirement_id']}-{index:03d}",
            requirement_id=requirement["requirement_id"],
            title=title,
            priority=requirement["priority"],
            preconditions=requirement["preconditions"],
            steps=steps,
            expected_result=expected_result,
            test_type=test_type,
            automation_candidate=automation_candidate,
            risk_level=requirement["risk_level"],
            source=source,
        )

    def _build_happy_path_steps(self, requirement: dict[str, Any]) -> list[str]:
        return dedupe_preserve_order(requirement["business_flow"])

    def _happy_path_expected_result(self, requirement: dict[str, Any]) -> str:
        if requirement["acceptance_criteria"]:
            return requirement["acceptance_criteria"][0]
        return f"{requirement['title']} completes successfully."

    def _build_acceptance_steps(self, requirement: dict[str, Any], criterion: str) -> list[str]:
        steps = []
        if requirement["business_flow"]:
            steps.extend(requirement["business_flow"])
        else:
            steps.append(f"Execute the flow for {requirement['title']}.")
        steps.append(f"Verify acceptance criterion: {criterion}")
        return dedupe_preserve_order(steps)

    def _build_scenario_steps(self, requirement: dict[str, Any], scenario: str) -> list[str]:
        steps = []
        if requirement["business_flow"]:
            steps.extend(requirement["business_flow"])
        else:
            steps.append(f"Prepare the system for {requirement['title']}.")
        steps.append(f"Execute scenario: {scenario}")
        return dedupe_preserve_order(steps)

    def _scenario_expected_result(self, requirement: dict[str, Any], scenario: str) -> str:
        if scenario.startswith("Acceptance validation: "):
            return scenario.removeprefix("Acceptance validation: ").strip()
        if scenario.startswith("Negative path covers: "):
            return scenario.removeprefix("Negative path covers: ").strip()
        if scenario.startswith("Business flow coverage: "):
            return f"The business flow succeeds for {requirement['title']}."
        return scenario

    def _scenario_is_automation_candidate(self, requirement: dict[str, Any], scenario: str) -> bool:
        if requirement["unknowns"] and not requirement["business_flow"] and not requirement["acceptance_criteria"]:
            return False
        return True

    def _build_fallback_steps(self, requirement: dict[str, Any]) -> list[str]:
        return [
            f"Review the requirement details for {requirement['title']}.",
            "Clarify missing business flow, acceptance criteria, and preconditions before execution.",
        ]

    def _as_str(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _as_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return dedupe_preserve_order(self._as_str(item) for item in value)
        if value is None:
            return []
        return dedupe_preserve_order([self._as_str(value)])


def generate_test_cases(requirement: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Generate deterministic test cases from a normalized requirement payload."""
    return TestCaseGenerator().generate(requirement)
