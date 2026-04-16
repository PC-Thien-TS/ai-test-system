from __future__ import annotations

from orchestrator.adapters.base.models import DefectFamilyDefinition


DEFECT_FAMILIES: tuple[DefectFamilyDefinition, ...] = (
    DefectFamilyDefinition(
        family_id="DF-SAMPLE-PRODUCT-DEFECT",
        title="Sample active-path product defect family",
        family_type="product_defect",
        severity="P1",
        release_impact="release-critical",
        member_cases=("SAMPLE-001",),
        recommended_next_action="Replace with real project defect family mappings.",
    ),
    DefectFamilyDefinition(
        family_id="DF-SAMPLE-ENV-BLOCKER",
        title="Sample environment blocker family",
        family_type="env_blocker",
        severity="BLOCKER",
        release_impact="partial-surface",
        member_cases=("SAMPLE-BLK-001",),
        recommended_next_action="Replace with real env/runtime blocker families.",
    ),
    DefectFamilyDefinition(
        family_id="DF-SAMPLE-COVERAGE-GAP",
        title="Sample coverage gap for ecommerce flow depth",
        family_type="coverage_gap",
        severity="GAP",
        release_impact="partial-surface",
        member_cases=("catalog_discovery", "payment_integrity"),
        recommended_next_action="Replace with real seed/data/coverage gap families.",
    ),
)

