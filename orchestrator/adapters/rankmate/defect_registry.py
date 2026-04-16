from __future__ import annotations

from orchestrator.adapters.base.models import DefectFamilyDefinition


DEFECT_FAMILIES: tuple[DefectFamilyDefinition, ...] = (
    DefectFamilyDefinition(
        family_id="DF-STORE-NEGATIVE-500",
        title="Store invalid lookup negative-path returns 500",
        family_type="product_defect",
        severity="P2",
        release_impact="release-critical",
        member_cases=("STORE-API-004", "STO-011"),
        recommended_next_action="Fix invalid store/uniqueId handlers to return controlled 4xx envelopes.",
    ),
    DefectFamilyDefinition(
        family_id="DF-MERCHANT-STALE-TERMINAL-MUTATION",
        title="Merchant stale/double complete mutation safety defect",
        family_type="product_defect",
        severity="P1",
        release_impact="release-critical",
        member_cases=("MER-API-021",),
        recommended_next_action="Reject repeat complete on terminal orders with controlled 4xx.",
    ),
    DefectFamilyDefinition(
        family_id="DF-STRIPE-WEBHOOK-ENV-BLOCKER",
        title="Stripe webhook realism blocked by runtime secret/signature mismatch",
        family_type="env_blocker",
        severity="BLOCKER",
        release_impact="partial-surface",
        member_cases=("PAY-API-003", "PAY-API-004", "PAY-API-007", "PAY-API-008", "PAY-API-011"),
        recommended_next_action="Align deployed Stripe webhook secret/signing with QA runtime.",
    ),
    DefectFamilyDefinition(
        family_id="DF-MERCHANT-SEED-COVERAGE-GAP",
        title="Merchant transition seed coverage gap",
        family_type="coverage_gap",
        severity="GAP",
        release_impact="partial-surface",
        member_cases=(),
        recommended_next_action="Regenerate deterministic merchant state seeds before depth reruns.",
    ),
)

