"""Risk prioritizer consuming requirement-aware outputs to build execution queue."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from orchestrator.advanced_qa.execution_queue import ExecutionQueueBuilder
from orchestrator.advanced_qa.requirement_models import (
    CoverageGapCandidate,
    GeneratedTestCase,
    GeneratedTestPlan,
    Requirement,
    RequirementGenerationResult,
    RequirementRiskMap,
)
from orchestrator.advanced_qa.requirement_rules import tokenize_text
from orchestrator.advanced_qa.risk_models import (
    BlastRadiusHint,
    ExecutionDepth,
    ExecutionDepthRecommendation,
    PrioritizedExecutionItem,
    PrioritizationResult,
    PriorityReason,
)
from orchestrator.advanced_qa.risk_rules import (
    CRITICAL_MODULES,
    map_score_to_priority_level,
    make_tiebreak_key,
    recommend_blast_radius,
    recommend_execution_depth,
    safe_bucket_weight,
    safe_gap_weight,
    safe_module_weight,
    safe_priority_weight,
    safe_risk_level_weight,
    should_flag_exploratory,
)


class RiskPrioritizer:
    """Deterministic risk-based prioritizer for execution-ready queue generation."""

    def __init__(self, queue_builder: Optional[ExecutionQueueBuilder] = None):
        self.queue_builder = queue_builder or ExecutionQueueBuilder()

    def prioritize(
        self,
        generation_result: RequirementGenerationResult,
        queue_id: str = "RISK-QUEUE-V1",
    ) -> PrioritizationResult:
        """Prioritize generated plans, test cases, and coverage gaps into execution queue."""

        requirements_by_id = {
            requirement.requirement_id: requirement
            for requirement in generation_result.requirements
        }
        risk_by_requirement = {
            risk.requirement_id: risk
            for risk in generation_result.risk_maps
        }
        gaps_by_requirement = self._index_gaps_by_requirement(generation_result.coverage_gaps)

        prioritized_items: List[PrioritizedExecutionItem] = []

        for plan in sorted(generation_result.test_plans, key=lambda item: item.plan_id):
            prioritized_items.append(
                self._prioritize_plan(
                    plan=plan,
                    requirements_by_id=requirements_by_id,
                    risk_by_requirement=risk_by_requirement,
                    gaps_by_requirement=gaps_by_requirement,
                )
            )

        for test_case in sorted(generation_result.test_cases, key=lambda item: item.test_case_id):
            prioritized_items.append(
                self._prioritize_test_case(
                    test_case=test_case,
                    requirements_by_id=requirements_by_id,
                    risk_by_requirement=risk_by_requirement,
                    gaps_by_requirement=gaps_by_requirement,
                )
            )

        for gap in sorted(generation_result.coverage_gaps, key=lambda item: item.gap_id):
            prioritized_items.append(
                self._prioritize_coverage_gap(
                    gap=gap,
                    requirements_by_id=requirements_by_id,
                    risk_by_requirement=risk_by_requirement,
                )
            )

        queue = self.queue_builder.build(queue_id=queue_id, items=prioritized_items)

        summary = self._build_summary(queue.items)
        return PrioritizationResult(execution_queue=queue, summary=summary)

    def _prioritize_plan(
        self,
        plan: GeneratedTestPlan,
        requirements_by_id: Dict[str, Requirement],
        risk_by_requirement: Dict[str, RequirementRiskMap],
        gaps_by_requirement: Dict[str, List[CoverageGapCandidate]],
    ) -> PrioritizedExecutionItem:
        related_requirements = [
            requirements_by_id[requirement_id]
            for requirement_id in plan.requirement_ids
            if requirement_id in requirements_by_id
        ]
        related_risks = [
            risk_by_requirement[requirement_id]
            for requirement_id in plan.requirement_ids
            if requirement_id in risk_by_requirement
        ]
        related_gaps = self._collect_related_gaps(plan.requirement_ids, gaps_by_requirement)

        score, reasons = self._calculate_score(
            source_type="plan",
            module=plan.module,
            related_requirements=related_requirements,
            related_risks=related_risks,
            related_gaps=related_gaps,
            plan_bucket=plan.bucket,
            text_fragments=[plan.name, " ".join(plan.tags), " ".join(plan.rationale)],
        )
        priority_level = map_score_to_priority_level(score)

        text_fragments = [
            plan.name,
            " ".join(plan.tags),
            " ".join(plan.rationale),
            " ".join(requirement.title for requirement in related_requirements),
            " ".join(flow for requirement in related_requirements for flow in requirement.related_flows),
        ]
        role_count = self._unique_role_count(related_requirements)
        dependency_count = self._unique_dependency_count(related_requirements)

        depth, depth_reasons = recommend_execution_depth(
            module=plan.module,
            text_fragments=text_fragments,
            score=score,
            priority_level=priority_level,
            source_type="plan",
        )
        blast_radius, blast_reasons = recommend_blast_radius(
            module=plan.module,
            text_fragments=text_fragments,
            score=score,
            role_count=role_count,
            dependency_count=dependency_count,
        )
        exploratory = should_flag_exploratory(
            text_fragments=text_fragments,
            module=plan.module,
            priority_level=priority_level,
            depth=depth,
            role_count=role_count,
        )

        tags = list(dict.fromkeys(plan.tags + [priority_level.value, depth.value, blast_radius.value]))
        if exploratory:
            tags.append("exploratory_follow_up")

        item_id = make_tiebreak_key(("PRI", "PLAN", plan.plan_id))
        return PrioritizedExecutionItem(
            item_id=item_id,
            source_type="plan",
            source_id=plan.plan_id,
            module=plan.module,
            submodule=None,
            priority_score=score,
            priority_level=priority_level,
            execution_depth=ExecutionDepthRecommendation(depth=depth, reasons=depth_reasons),
            blast_radius=BlastRadiusHint(level=blast_radius, reasons=blast_reasons),
            reasons=reasons,
            tags=tags,
            related_requirement_ids=sorted(plan.requirement_ids),
            exploratory_follow_up=exploratory,
        )

    def _prioritize_test_case(
        self,
        test_case: GeneratedTestCase,
        requirements_by_id: Dict[str, Requirement],
        risk_by_requirement: Dict[str, RequirementRiskMap],
        gaps_by_requirement: Dict[str, List[CoverageGapCandidate]],
    ) -> PrioritizedExecutionItem:
        related_requirements = [
            requirements_by_id[requirement_id]
            for requirement_id in test_case.related_requirement_ids
            if requirement_id in requirements_by_id
        ]
        related_risks = [
            risk_by_requirement[requirement_id]
            for requirement_id in test_case.related_requirement_ids
            if requirement_id in risk_by_requirement
        ]
        related_gaps = self._collect_related_gaps(test_case.related_requirement_ids, gaps_by_requirement)

        score, reasons = self._calculate_score(
            source_type="test_case",
            module=test_case.module,
            related_requirements=related_requirements,
            related_risks=related_risks,
            related_gaps=related_gaps,
            text_fragments=[
                test_case.title,
                test_case.scenario_type,
                " ".join(test_case.tags),
                " ".join(test_case.steps),
                test_case.expected_result,
            ],
        )

        # Scenario-specific adjustments to preserve deterministic policy intent.
        if test_case.scenario_type in {"negative", "state_transition"}:
            reasons.append(
                PriorityReason(
                    code="scenario_complexity",
                    description=f"Scenario type '{test_case.scenario_type}' requires stronger validation depth.",
                    weight=0.10,
                )
            )
            score = min(1.25, score + 0.10)

        if "permission" in test_case.scenario_type or "permission" in " ".join(test_case.tags):
            reasons.append(
                PriorityReason(
                    code="permission_sensitive_case",
                    description="Permission-sensitive scenario prioritized for security confidence.",
                    weight=0.08,
                )
            )
            score = min(1.25, score + 0.08)

        priority_level = map_score_to_priority_level(score)

        text_fragments = [
            test_case.title,
            test_case.scenario_type,
            " ".join(test_case.tags),
            " ".join(test_case.steps),
            test_case.expected_result,
        ]
        # Build related flow text separately to keep expression explicit.
        flow_fragments = [
            flow
            for requirement in related_requirements
            for flow in requirement.related_flows
        ]
        text_fragments.extend(flow_fragments)

        role_count = self._unique_role_count(related_requirements)
        dependency_count = self._unique_dependency_count(related_requirements)

        depth, depth_reasons = recommend_execution_depth(
            module=test_case.module,
            text_fragments=text_fragments,
            score=score,
            priority_level=priority_level,
            source_type="test_case",
        )
        blast_radius, blast_reasons = recommend_blast_radius(
            module=test_case.module,
            text_fragments=text_fragments,
            score=score,
            role_count=role_count,
            dependency_count=dependency_count,
        )

        # Permission-sensitive test cases should not drop below STANDARD depth.
        if (
            ("permission" in test_case.scenario_type or "permission" in " ".join(test_case.tags))
            and depth.value == "basic"
        ):
            depth, depth_reasons = recommend_execution_depth(
                module=test_case.module,
                text_fragments=["permission", *text_fragments],
                score=max(score, 0.60),
                priority_level=priority_level,
                source_type="test_case",
            )
            if depth.value == "basic":
                depth = ExecutionDepth.STANDARD
                depth_reasons = depth_reasons + ["permission_depth_floor"]

        exploratory = should_flag_exploratory(
            text_fragments=text_fragments,
            module=test_case.module,
            priority_level=priority_level,
            depth=depth,
            role_count=role_count,
        )

        tags = list(dict.fromkeys(test_case.tags + [test_case.scenario_type, priority_level.value, depth.value, blast_radius.value]))
        if exploratory:
            tags.append("exploratory_follow_up")

        item_id = make_tiebreak_key(("PRI", "CASE", test_case.test_case_id))
        return PrioritizedExecutionItem(
            item_id=item_id,
            source_type="test_case",
            source_id=test_case.test_case_id,
            module=test_case.module,
            submodule=test_case.submodule,
            priority_score=score,
            priority_level=priority_level,
            execution_depth=ExecutionDepthRecommendation(depth=depth, reasons=depth_reasons),
            blast_radius=BlastRadiusHint(level=blast_radius, reasons=blast_reasons),
            reasons=reasons,
            tags=tags,
            related_requirement_ids=sorted(test_case.related_requirement_ids),
            exploratory_follow_up=exploratory,
        )

    def _prioritize_coverage_gap(
        self,
        gap: CoverageGapCandidate,
        requirements_by_id: Dict[str, Requirement],
        risk_by_requirement: Dict[str, RequirementRiskMap],
    ) -> PrioritizedExecutionItem:
        requirement = requirements_by_id.get(gap.requirement_id)
        related_risk = risk_by_requirement.get(gap.requirement_id)

        module = requirement.module if requirement and requirement.module else "Exploratory High-Risk Flows"
        text_fragments = [
            gap.gap_type,
            gap.description,
            " ".join(gap.suggested_actions),
            requirement.title if requirement else "",
            requirement.description if requirement else "",
        ]

        score, reasons = self._calculate_score(
            source_type="coverage_gap",
            module=module,
            related_requirements=[requirement] if requirement else [],
            related_risks=[related_risk] if related_risk else [],
            related_gaps=[gap],
            text_fragments=text_fragments,
        )

        # Coverage gaps always carry explicit gap-severity influence.
        severity_weight = safe_risk_level_weight(gap.severity)
        reasons.append(
            PriorityReason(
                code="coverage_gap_severity",
                description=f"Coverage gap severity '{gap.severity.value}' escalates prioritization.",
                weight=severity_weight,
            )
        )
        score = min(1.25, score + severity_weight)

        priority_level = map_score_to_priority_level(score)

        role_count = len(requirement.roles) if requirement else 0
        dependency_count = len(requirement.dependencies) if requirement else 0

        depth, depth_reasons = recommend_execution_depth(
            module=module,
            text_fragments=text_fragments,
            score=score,
            priority_level=priority_level,
            source_type="coverage_gap",
        )
        blast_radius, blast_reasons = recommend_blast_radius(
            module=module,
            text_fragments=text_fragments,
            score=score,
            role_count=role_count,
            dependency_count=dependency_count,
        )
        exploratory = should_flag_exploratory(
            text_fragments=text_fragments,
            module=module,
            priority_level=priority_level,
            depth=depth,
            role_count=role_count,
        )

        tags = ["coverage_gap", gap.gap_type, priority_level.value, depth.value, blast_radius.value]
        if exploratory:
            tags.append("exploratory_follow_up")

        item_id = make_tiebreak_key(("PRI", "GAP", gap.gap_id))
        return PrioritizedExecutionItem(
            item_id=item_id,
            source_type="coverage_gap",
            source_id=gap.gap_id,
            module=module,
            submodule=requirement.submodule if requirement else None,
            priority_score=score,
            priority_level=priority_level,
            execution_depth=ExecutionDepthRecommendation(depth=depth, reasons=depth_reasons),
            blast_radius=BlastRadiusHint(level=blast_radius, reasons=blast_reasons),
            reasons=reasons,
            tags=tags,
            related_requirement_ids=[gap.requirement_id],
            exploratory_follow_up=exploratory,
        )

    def _calculate_score(
        self,
        source_type: str,
        module: str,
        related_requirements: Sequence[Requirement],
        related_risks: Sequence[RequirementRiskMap],
        related_gaps: Sequence[CoverageGapCandidate],
        text_fragments: Sequence[str],
        plan_bucket=None,
    ) -> Tuple[float, List[PriorityReason]]:
        """Calculate deterministic risk-priority score with auditable reason list."""

        reasons: List[PriorityReason] = []
        score = 0.0

        source_weight = self._source_base_weight(source_type)
        score += source_weight
        reasons.append(
            PriorityReason(
                code="source_base",
                description=f"Base weight for source_type '{source_type}'.",
                weight=source_weight,
            )
        )

        module_weight = safe_module_weight(module)
        score += module_weight
        reasons.append(
            PriorityReason(
                code="module_criticality",
                description=f"Module '{module}' contributes criticality weight.",
                weight=module_weight,
            )
        )

        if plan_bucket is not None:
            bucket_weight = safe_bucket_weight(plan_bucket)
            score += bucket_weight
            reasons.append(
                PriorityReason(
                    code="plan_bucket",
                    description=f"Plan bucket '{plan_bucket.value}' influences execution priority.",
                    weight=bucket_weight,
                )
            )

        if related_risks:
            average_risk_score = sum(risk.risk_score for risk in related_risks) / len(related_risks)
            risk_score_weight = round(average_risk_score * 0.40, 4)
            score += risk_score_weight
            reasons.append(
                PriorityReason(
                    code="requirement_risk_score",
                    description="Aggregated requirement risk score contribution.",
                    weight=risk_score_weight,
                )
            )

        if related_requirements:
            priority_weight = self._max_priority_weight(requirement.priority for requirement in related_requirements)
            score += priority_weight
            reasons.append(
                PriorityReason(
                    code="requirement_priority",
                    description="Highest linked requirement priority contribution.",
                    weight=priority_weight,
                )
            )

            changed_area_bonus = 0.12 if any(requirement.changed_area for requirement in related_requirements) else 0.0
            if changed_area_bonus:
                score += changed_area_bonus
                reasons.append(
                    PriorityReason(
                        code="changed_area",
                        description="Changed-area requirement receives elevated execution urgency.",
                        weight=changed_area_bonus,
                    )
                )

            role_count = self._unique_role_count(related_requirements)
            if role_count > 1:
                role_bonus = 0.10
                score += role_bonus
                reasons.append(
                    PriorityReason(
                        code="cross_role_complexity",
                        description="Cross-role interactions increase operational risk.",
                        weight=role_bonus,
                    )
                )

            dependency_count = self._unique_dependency_count(related_requirements)
            if dependency_count >= 2:
                dependency_bonus = 0.08
                score += dependency_bonus
                reasons.append(
                    PriorityReason(
                        code="dependency_chain",
                        description="Multiple dependencies increase blast potential.",
                        weight=dependency_bonus,
                    )
                )

        if related_gaps:
            gap_weight_total = sum(safe_gap_weight(gap.gap_type) for gap in related_gaps)
            gap_bonus = min(gap_weight_total * 0.25, 0.18)
            score += gap_bonus
            reasons.append(
                PriorityReason(
                    code="coverage_gap_influence",
                    description="Linked coverage gaps elevate execution priority.",
                    weight=gap_bonus,
                )
            )

        text = tokenize_text(text_fragments)
        keyword_bonus = 0.0
        for keyword, weight in {
            "payment": 0.08,
            "callback": 0.08,
            "webhook": 0.08,
            "retry": 0.06,
            "timeout": 0.06,
            "duplicate": 0.08,
            "state transition": 0.08,
            "permission": 0.08,
            "race": 0.08,
        }.items():
            if keyword in text:
                keyword_bonus += weight

        keyword_bonus = min(keyword_bonus, 0.20)
        if keyword_bonus:
            score += keyword_bonus
            reasons.append(
                PriorityReason(
                    code="critical_behavior_keywords",
                    description="Critical behavior keywords detected in scenario context.",
                    weight=keyword_bonus,
                )
            )

        if module in CRITICAL_MODULES and source_type == "coverage_gap":
            critical_gap_bonus = 0.10
            score += critical_gap_bonus
            reasons.append(
                PriorityReason(
                    code="critical_module_gap",
                    description="Coverage gap on critical module receives extra urgency.",
                    weight=critical_gap_bonus,
                )
            )

        score = round(min(score, 1.25), 4)
        return score, reasons

    def _source_base_weight(self, source_type: str) -> float:
        return {
            "plan": 0.08,
            "test_case": 0.10,
            "coverage_gap": 0.14,
        }.get(source_type, 0.08)

    def _max_priority_weight(self, priorities: Iterable[str]) -> float:
        values = [safe_priority_weight(priority) for priority in priorities]
        return max(values) if values else safe_priority_weight("p2")

    def _index_gaps_by_requirement(
        self,
        gaps: Sequence[CoverageGapCandidate],
    ) -> Dict[str, List[CoverageGapCandidate]]:
        indexed: Dict[str, List[CoverageGapCandidate]] = defaultdict(list)
        for gap in gaps:
            indexed[gap.requirement_id].append(gap)
        return indexed

    def _collect_related_gaps(
        self,
        requirement_ids: Sequence[str],
        gaps_by_requirement: Dict[str, List[CoverageGapCandidate]],
    ) -> List[CoverageGapCandidate]:
        gaps: List[CoverageGapCandidate] = []
        for requirement_id in requirement_ids:
            gaps.extend(gaps_by_requirement.get(requirement_id, []))
        return gaps

    def _unique_role_count(self, requirements: Sequence[Requirement]) -> int:
        roles = {
            role
            for requirement in requirements
            for role in requirement.roles
            if role
        }
        return len(roles)

    def _unique_dependency_count(self, requirements: Sequence[Requirement]) -> int:
        dependencies = {
            dependency
            for requirement in requirements
            for dependency in requirement.dependencies
            if dependency
        }
        return len(dependencies)

    def _build_summary(self, items: Sequence[PrioritizedExecutionItem]) -> Dict[str, object]:
        by_priority: Dict[str, int] = defaultdict(int)
        by_source: Dict[str, int] = defaultdict(int)
        exploratory_count = 0

        for item in items:
            by_priority[item.priority_level.value] += 1
            by_source[item.source_type] += 1
            if item.exploratory_follow_up:
                exploratory_count += 1

        return {
            "total_items": len(items),
            "by_priority": dict(sorted(by_priority.items())),
            "by_source_type": dict(sorted(by_source.items())),
            "exploratory_follow_up_items": exploratory_count,
        }
