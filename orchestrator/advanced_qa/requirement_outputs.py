"""Output generation for requirement-aware test artifacts."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List

from orchestrator.advanced_qa.requirement_models import (
    CoverageGapCandidate,
    GeneratedTestCase,
    GeneratedTestPlan,
    PlanBucket,
    Requirement,
    RequirementRiskMap,
    RiskLevel,
)
from orchestrator.advanced_qa.requirement_rules import (
    build_risk_signals,
    determine_risk_level,
    detect_roles,
    infer_plan_buckets,
    needs_negative_coverage,
    needs_state_transition_coverage,
    normalize_priority,
    tokenize_text,
)


class RequirementOutputBuilder:
    """Generate plans, test cases, coverage gaps, and risk maps."""

    _ROLE_REQUIRED_MODULES = {
        "Auth & Account",
        "Order Creation",
        "Payment",
        "Merchant Operations",
        "Admin Operations",
        "Permission / Security",
    }

    def generate_risk_maps(self, requirements: List[Requirement]) -> List[RequirementRiskMap]:
        """Generate requirement risk maps with rule-based scoring."""

        risk_maps: List[RequirementRiskMap] = []

        for requirement in requirements:
            text = tokenize_text(
                [
                    requirement.title,
                    requirement.description,
                    " ".join(requirement.acceptance_criteria),
                    " ".join(requirement.business_rules),
                    " ".join(requirement.risk_hints),
                    " ".join(requirement.related_flows),
                    requirement.module or "",
                ]
            )
            priority = normalize_priority(requirement.priority)
            risk_score, risk_signals = build_risk_signals(
                priority=priority,
                changed_area=requirement.changed_area,
                role_count=len(requirement.roles),
                text=text,
            )
            risk_level = determine_risk_level(risk_score)

            buckets = infer_plan_buckets(
                priority=priority,
                risk_level=risk_level,
                text=text,
                has_acceptance=bool(requirement.acceptance_criteria),
                role_count=len(requirement.roles),
                has_dependencies=bool(requirement.dependencies),
            )

            risk_maps.append(
                RequirementRiskMap(
                    requirement_id=requirement.requirement_id,
                    module=requirement.module or "Exploratory High-Risk Flows",
                    risk_level=risk_level,
                    risk_score=round(risk_score, 3),
                    risk_signals=risk_signals,
                    recommended_plan_buckets=buckets,
                )
            )

        return sorted(risk_maps, key=lambda item: item.requirement_id)

    def generate_test_plans(
        self,
        requirements: List[Requirement],
        risk_maps: List[RequirementRiskMap],
    ) -> List[GeneratedTestPlan]:
        """Generate grouped test plans based on requirement buckets."""

        risk_by_requirement = {risk.requirement_id: risk for risk in risk_maps}
        grouped: Dict[tuple[PlanBucket, str], List[Requirement]] = defaultdict(list)

        for requirement in requirements:
            risk = risk_by_requirement[requirement.requirement_id]
            grouped_buckets = risk.recommended_plan_buckets
            for bucket in grouped_buckets:
                grouped[(bucket, requirement.module or "Exploratory High-Risk Flows")].append(requirement)

        plans: List[GeneratedTestPlan] = []
        for (bucket, module_name), reqs in sorted(grouped.items(), key=lambda item: (item[0][0].value, item[0][1])):
            requirement_ids = sorted(req.requirement_id for req in reqs)
            plan_id = f"PLAN-{bucket.value.upper()}-{self._slug(module_name)}"
            plan_priority = self._highest_priority(req.priority for req in reqs)

            plans.append(
                GeneratedTestPlan(
                    plan_id=plan_id,
                    name=f"{module_name} {bucket.value.replace('_', ' ').title()} Plan",
                    bucket=bucket,
                    module=module_name,
                    requirement_ids=requirement_ids,
                    rationale=[
                        f"Covers {len(requirement_ids)} requirements in {module_name}.",
                        f"Bucket selected by rule-based heuristics for {bucket.value}.",
                    ],
                    priority=plan_priority,
                    tags=["requirement-aware", self._slug(module_name), bucket.value],
                )
            )

        return plans

    def generate_test_cases(
        self,
        requirements: List[Requirement],
        risk_maps: List[RequirementRiskMap],
    ) -> List[GeneratedTestCase]:
        """Generate deterministic test cases from normalized requirements."""

        risk_by_requirement = {risk.requirement_id: risk for risk in risk_maps}
        cases: List[GeneratedTestCase] = []

        for requirement in sorted(requirements, key=lambda item: item.requirement_id):
            risk = risk_by_requirement[requirement.requirement_id]
            module_name = requirement.module or "Exploratory High-Risk Flows"
            req_id = self._slug(requirement.requirement_id).upper()
            shared_tags = self._base_tags(requirement, risk)

            positive_steps = self._build_positive_steps(requirement)
            cases.append(
                GeneratedTestCase(
                    test_case_id=f"TC-{req_id}-POS",
                    title=f"{requirement.title} - positive path",
                    module=module_name,
                    submodule=requirement.submodule,
                    scenario_type="positive",
                    preconditions=self._build_preconditions(requirement),
                    steps=positive_steps,
                    expected_result=self._expected_result(requirement),
                    priority=normalize_priority(requirement.priority),
                    risk_level=risk.risk_level,
                    related_requirement_ids=[requirement.requirement_id],
                    tags=shared_tags + ["positive"],
                )
            )

            if requirement.business_rules:
                cases.append(
                    GeneratedTestCase(
                        test_case_id=f"TC-{req_id}-RULE",
                        title=f"{requirement.title} - business rule validation",
                        module=module_name,
                        submodule=requirement.submodule,
                        scenario_type="rule_validation",
                        preconditions=self._build_preconditions(requirement),
                        steps=[f"Validate business rule: {rule}" for rule in requirement.business_rules],
                        expected_result="All business rules are enforced without regressions.",
                        priority=normalize_priority(requirement.priority),
                        risk_level=risk.risk_level,
                        related_requirement_ids=[requirement.requirement_id],
                        tags=shared_tags + ["business_rule"],
                    )
                )

            text = tokenize_text(
                [
                    requirement.title,
                    requirement.description,
                    " ".join(requirement.acceptance_criteria),
                    " ".join(requirement.business_rules),
                    " ".join(requirement.risk_hints),
                ]
            )

            if needs_negative_coverage(text):
                cases.append(
                    GeneratedTestCase(
                        test_case_id=f"TC-{req_id}-NEG",
                        title=f"{requirement.title} - negative/error path",
                        module=module_name,
                        submodule=requirement.submodule,
                        scenario_type="negative",
                        preconditions=self._build_preconditions(requirement),
                        steps=[
                            "Trigger the error or boundary condition described in the requirement.",
                            "Verify system response and rollback/guard behavior.",
                        ],
                        expected_result="System handles the negative path safely and returns a controlled outcome.",
                        priority=normalize_priority(requirement.priority),
                        risk_level=risk.risk_level,
                        related_requirement_ids=[requirement.requirement_id],
                        tags=shared_tags + ["negative", "error_path"],
                    )
                )

            if needs_state_transition_coverage(text):
                cases.append(
                    GeneratedTestCase(
                        test_case_id=f"TC-{req_id}-STATE",
                        title=f"{requirement.title} - state transition validation",
                        module=module_name,
                        submodule=requirement.submodule,
                        scenario_type="state_transition",
                        preconditions=self._build_preconditions(requirement),
                        steps=[
                            "Prepare entity in required initial state.",
                            "Execute transition-triggering action.",
                            "Verify allowed next states and blocked invalid transitions.",
                        ],
                        expected_result="State transitions follow requirement rules and invalid transitions are blocked.",
                        priority=normalize_priority(requirement.priority),
                        risk_level=risk.risk_level,
                        related_requirement_ids=[requirement.requirement_id],
                        tags=shared_tags + ["state_transition"],
                    )
                )

        return cases

    def detect_coverage_gaps(
        self,
        requirements: List[Requirement],
        test_cases: List[GeneratedTestCase],
    ) -> List[CoverageGapCandidate]:
        """Detect requirement coverage gaps after test generation."""

        cases_by_requirement: Dict[str, List[GeneratedTestCase]] = defaultdict(list)
        for test_case in test_cases:
            for requirement_id in test_case.related_requirement_ids:
                cases_by_requirement[requirement_id].append(test_case)

        gaps: List[CoverageGapCandidate] = []
        for requirement in requirements:
            req_cases = cases_by_requirement.get(requirement.requirement_id, [])
            text = tokenize_text(
                [
                    requirement.title,
                    requirement.description,
                    " ".join(requirement.acceptance_criteria),
                    " ".join(requirement.business_rules),
                    " ".join(requirement.risk_hints),
                ]
            )

            if not requirement.acceptance_criteria:
                gaps.append(
                    CoverageGapCandidate(
                        gap_id=f"GAP-{self._slug(requirement.requirement_id).upper()}-ACCEPTANCE",
                        requirement_id=requirement.requirement_id,
                        gap_type="missing_acceptance_criteria",
                        severity=RiskLevel.MEDIUM,
                        description="Requirement does not provide explicit acceptance criteria.",
                        suggested_actions=["Add acceptance criteria to support test oracle quality."],
                    )
                )

            if not requirement.roles and requirement.module in self._ROLE_REQUIRED_MODULES:
                gaps.append(
                    CoverageGapCandidate(
                        gap_id=f"GAP-{self._slug(requirement.requirement_id).upper()}-ROLES",
                        requirement_id=requirement.requirement_id,
                        gap_type="missing_role_coverage",
                        severity=RiskLevel.MEDIUM,
                        description="Requirement lacks role definition for a role-sensitive module.",
                        suggested_actions=["Specify actor roles (user/merchant/admin/system)."],
                    )
                )

            if requirement.business_rules and not any(case.scenario_type == "rule_validation" for case in req_cases):
                gaps.append(
                    CoverageGapCandidate(
                        gap_id=f"GAP-{self._slug(requirement.requirement_id).upper()}-RULES",
                        requirement_id=requirement.requirement_id,
                        gap_type="business_rule_uncovered",
                        severity=RiskLevel.HIGH,
                        description="Business rules exist but no dedicated rule-validation test was generated.",
                        suggested_actions=["Add rule_validation test case for each rule."],
                    )
                )

            dependency_sensitive_flows = {
                "cart_to_checkout",
                "checkout_create_order",
                "order_to_payment_init",
                "payment_callback_retry_timeout",
            }
            if not requirement.dependencies and any(flow in dependency_sensitive_flows for flow in requirement.related_flows):
                gaps.append(
                    CoverageGapCandidate(
                        gap_id=f"GAP-{self._slug(requirement.requirement_id).upper()}-DEPENDENCY",
                        requirement_id=requirement.requirement_id,
                        gap_type="missing_flow_dependency",
                        severity=RiskLevel.MEDIUM,
                        description="Requirement flow implies dependencies but dependency list is empty.",
                        suggested_actions=["Add upstream/downstream dependency references."],
                    )
                )

            if needs_negative_coverage(text) and not any(case.scenario_type == "negative" for case in req_cases):
                gaps.append(
                    CoverageGapCandidate(
                        gap_id=f"GAP-{self._slug(requirement.requirement_id).upper()}-ERRORPATH",
                        requirement_id=requirement.requirement_id,
                        gap_type="missing_error_path_coverage",
                        severity=RiskLevel.HIGH,
                        description="Requirement implies error-path behavior but no negative test exists.",
                        suggested_actions=["Add negative/error-path test case."],
                    )
                )

            if needs_state_transition_coverage(text) and not any(case.scenario_type == "state_transition" for case in req_cases):
                gaps.append(
                    CoverageGapCandidate(
                        gap_id=f"GAP-{self._slug(requirement.requirement_id).upper()}-STATE",
                        requirement_id=requirement.requirement_id,
                        gap_type="missing_state_transition_coverage",
                        severity=RiskLevel.HIGH,
                        description="Requirement involves state transitions without dedicated transition tests.",
                        suggested_actions=["Add state transition validation case."],
                    )
                )

            inferred_roles = detect_roles(text)
            if inferred_roles and not requirement.roles:
                gaps.append(
                    CoverageGapCandidate(
                        gap_id=f"GAP-{self._slug(requirement.requirement_id).upper()}-ROLEHINT",
                        requirement_id=requirement.requirement_id,
                        gap_type="inferred_role_not_explicit",
                        severity=RiskLevel.LOW,
                        description="Role keywords were detected but roles are not explicitly structured.",
                        suggested_actions=["Populate explicit roles field for traceability."],
                    )
                )

        return sorted(gaps, key=lambda item: item.gap_id)

    def _highest_priority(self, priorities: List[str]) -> str:
        order = {"p0": 0, "p1": 1, "p2": 2, "p3": 3}
        normalized = [normalize_priority(priority) for priority in priorities]
        normalized.sort(key=lambda priority: order.get(priority, 99))
        return normalized[0] if normalized else "p2"

    def _expected_result(self, requirement: Requirement) -> str:
        if requirement.acceptance_criteria:
            return requirement.acceptance_criteria[0]
        return f"Requirement '{requirement.title}' is satisfied without regressions."

    def _build_preconditions(self, requirement: Requirement) -> List[str]:
        conditions = [f"Module context is available for {requirement.module or 'target flow'}." ]
        if requirement.roles:
            conditions.append(f"Actor roles prepared: {', '.join(requirement.roles)}.")
        if requirement.dependencies:
            conditions.append(f"Dependencies ready: {', '.join(requirement.dependencies)}.")
        return conditions

    def _build_positive_steps(self, requirement: Requirement) -> List[str]:
        steps = [
            f"Open flow for requirement {requirement.requirement_id}.",
            f"Execute scenario: {requirement.title}.",
        ]
        if requirement.acceptance_criteria:
            steps.extend(
                f"Verify acceptance criterion: {criterion}" for criterion in requirement.acceptance_criteria
            )
        else:
            steps.append("Validate observable behavior against requirement description.")
        return steps

    def _base_tags(self, requirement: Requirement, risk: RequirementRiskMap) -> List[str]:
        tags = [
            "requirement-aware",
            self._slug(requirement.module or "general"),
            normalize_priority(requirement.priority),
            risk.risk_level.value,
        ]
        tags.extend(self._slug(flow) for flow in requirement.related_flows)
        return list(dict.fromkeys(tags))

    def _slug(self, value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
