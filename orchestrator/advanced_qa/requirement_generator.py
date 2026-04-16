"""Top-level requirement-aware generation pipeline."""

from __future__ import annotations

from typing import Any, List, Optional

from orchestrator.advanced_qa.requirement_mapper import RequirementMapper
from orchestrator.advanced_qa.requirement_models import RequirementGenerationResult
from orchestrator.advanced_qa.requirement_outputs import RequirementOutputBuilder
from orchestrator.advanced_qa.requirement_parser import RequirementParser


class RequirementAwareGenerator:
    """Backend-first requirement-aware generation orchestrator."""

    def __init__(
        self,
        parser: Optional[RequirementParser] = None,
        mapper: Optional[RequirementMapper] = None,
        output_builder: Optional[RequirementOutputBuilder] = None,
    ):
        self.parser = parser or RequirementParser()
        self.mapper = mapper or RequirementMapper()
        self.output_builder = output_builder or RequirementOutputBuilder()

    def generate(
        self,
        raw_input: Any,
        source_type: Optional[str] = None,
        source_ref: Optional[str] = None,
    ) -> RequirementGenerationResult:
        """Generate requirement-aware outputs from raw requirement input."""

        requirements = self.parser.parse(raw_input, source_type=source_type, source_ref=source_ref)
        mapped_requirements = self.mapper.map_requirements(requirements)
        risk_maps = self.output_builder.generate_risk_maps(mapped_requirements)
        test_plans = self.output_builder.generate_test_plans(mapped_requirements, risk_maps)
        test_cases = self.output_builder.generate_test_cases(mapped_requirements, risk_maps)
        coverage_gaps = self.output_builder.detect_coverage_gaps(mapped_requirements, test_cases)

        return RequirementGenerationResult(
            requirements=mapped_requirements,
            test_plans=test_plans,
            test_cases=test_cases,
            coverage_gaps=coverage_gaps,
            risk_maps=risk_maps,
        )
