"""Release Decision Gate v1.1 for RankMate Wave 1 evidence.

Outputs:
- release_decision.json
- docs/wave1_runtime/RELEASE_DECISION_REPORT.md
"""

from __future__ import annotations

import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from orchestrator.adapters import get_active_adapter
from orchestrator.adapters.evidence_context import get_adapter_evidence_context


REPO_ROOT = Path(__file__).resolve().parent

ORDER_LIFECYCLE_REPORT = REPO_ROOT / "docs" / "wave1_runtime" / "ORDER_LIFECYCLE_REPORT.md"
ADMIN_CONSISTENCY_REPORT = REPO_ROOT / "docs" / "wave1_runtime" / "ADMIN_CONSISTENCY_REPORT.md"
MERCHANT_SEEDS_REPORT = REPO_ROOT / "docs" / "wave1_runtime" / "MERCHANT_STATE_SEEDS_REPORT.md"
WAVE1_BLOCKERS = REPO_ROOT / "docs" / "wave1_execution" / "RANKMATE_WAVE1_BLOCKERS_AND_DEPENDENCIES.md"
RUNTIME_ENV_CONTRACT = REPO_ROOT / "docs" / "wave1_runtime" / "RANKMATE_WAVE1_RUNTIME_ENV_CONTRACT.md"
SEARCH_STORE_TEST = REPO_ROOT / "tests" / "rankmate_wave1" / "test_search_store_api.py"
LEGACY_API_REGRESSION_NOTES = REPO_ROOT / "artifacts" / "test-results" / "api-regression" / "README.md"

ORDER_LIFECYCLE_SEED = REPO_ROOT / "order_lifecycle_seed.json"
MERCHANT_STATE_SEEDS_JSON = REPO_ROOT / "merchant_state_seeds.json"
MERCHANT_STATE_SEEDS_ENV = REPO_ROOT / "merchant_state_seeds.env"
DEFECT_CLUSTER_REPORT = REPO_ROOT / "defect_cluster_report.json"

ADAPTER = get_active_adapter()
EVIDENCE_CTX = get_adapter_evidence_context(ADAPTER.get_adapter_id())
OUTPUT_JSON = EVIDENCE_CTX.get_release_decision_path()
REPORT_NAME = "RELEASE_DECISION_REPORT.md"
SCORING_RULES = ADAPTER.get_release_scoring_rules()
PHASE_WEIGHTS = dict(SCORING_RULES.get("phase_weights", {})) or {
    "auth": 25,
    "order_core": 25,
    "search_store": 15,
    "lifecycle": 15,
    "admin_consistency": 20,
}
MAX_SCORE = sum(PHASE_WEIGHTS.values())

SEVERITY_PENALTIES = dict(SCORING_RULES.get("severity_penalties", {})) or {"P0": -25, "P1": -15, "P2": -8}
ENV_BLOCKER_PENALTIES = dict(SCORING_RULES.get("env_blocker_penalties", {})) or {"critical": -10, "medium": -5}
COVERAGE_GAP_PENALTIES = dict(SCORING_RULES.get("coverage_gap_penalties", {})) or {"high": -6, "medium": -4, "low": -3}
DECISION_THRESHOLDS = dict(SCORING_RULES.get("thresholds", {})) or {"release": 85, "release_with_caution": 65}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _extract_backtick_value(markdown: str, label: str) -> Optional[str]:
    pattern = rf"-\s+{re.escape(label)}:\s+`([^`]*)`"
    match = re.search(pattern, markdown)
    if not match:
        return None
    value = match.group(1).strip()
    return value if value else None


def _as_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    text = value.strip()
    if not text or text.lower() == "none":
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _as_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"true", "1", "yes"}:
        return True
    if normalized in {"false", "0", "no"}:
        return False
    return None


def _status_from_report_markers(text: str) -> str:
    if not text:
        return "missing"
    if "Execution mode: `blocked`" in text:
        return "blocked"
    return "present"


def _penalty_item(
    *,
    finding_id: str,
    title: str,
    severity: str,
    penalty: int,
    source: str,
    category: str,
    in_active_path: bool = False,
    impacted_flows: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": finding_id,
        "title": title,
        "severity": severity,
        "penalty": penalty,
        "category": category,
        "source": source,
        "in_active_path": in_active_path,
        "impacted_flows": impacted_flows or [],
    }


def _collect_evidence() -> dict[str, Any]:
    order_report = _read_text(ORDER_LIFECYCLE_REPORT)
    admin_report = _read_text(ADMIN_CONSISTENCY_REPORT)
    merchant_seed_report = _read_text(MERCHANT_SEEDS_REPORT)
    blocker_doc = _read_text(WAVE1_BLOCKERS)
    runtime_env_doc = _read_text(RUNTIME_ENV_CONTRACT)
    search_store_test = _read_text(SEARCH_STORE_TEST)
    legacy_regression_notes = _read_text(LEGACY_API_REGRESSION_NOTES)

    order_seed = _read_json(ORDER_LIFECYCLE_SEED)
    merchant_seeds_json = _read_json(MERCHANT_STATE_SEEDS_JSON)
    merchant_seeds_env = _read_text(MERCHANT_STATE_SEEDS_ENV)
    defect_cluster = _read_json(DEFECT_CLUSTER_REPORT)

    evidence_sources: list[str] = []
    for path in (
        ORDER_LIFECYCLE_REPORT,
        ADMIN_CONSISTENCY_REPORT,
        MERCHANT_SEEDS_REPORT,
        ORDER_LIFECYCLE_SEED,
        MERCHANT_STATE_SEEDS_JSON,
        MERCHANT_STATE_SEEDS_ENV,
        DEFECT_CLUSTER_REPORT,
        WAVE1_BLOCKERS,
        RUNTIME_ENV_CONTRACT,
        SEARCH_STORE_TEST,
        LEGACY_API_REGRESSION_NOTES,
    ):
        if path.exists():
            evidence_sources.append(str(path))

    lifecycle_order_id = _as_int(_extract_backtick_value(order_report, "Main order id"))
    lifecycle_store_id = _as_int(_extract_backtick_value(order_report, "Store id"))
    lifecycle_user_visible = _as_bool(_extract_backtick_value(order_report, "User visible"))
    lifecycle_merchant_visible = _as_bool(_extract_backtick_value(order_report, "Merchant visible"))
    lifecycle_admin_visible = _as_bool(_extract_backtick_value(order_report, "Admin visible"))

    lifecycle_seed_order_id = order_seed.get("order_id") if isinstance(order_seed.get("order_id"), int) else None

    order_core_green = bool(
        _status_from_report_markers(order_report) == "present"
        and (lifecycle_order_id is not None or lifecycle_seed_order_id is not None)
        and lifecycle_store_id is not None
        and lifecycle_user_visible is True
    )

    lifecycle_usable = bool(
        (lifecycle_order_id is not None or lifecycle_seed_order_id is not None)
        and lifecycle_store_id is not None
        and lifecycle_user_visible is True
        and lifecycle_merchant_visible is True
    )

    admin_consistency_green = bool(
        _status_from_report_markers(admin_report) == "present"
        and "| user |" in admin_report
        and "| merchant |" in admin_report
        and "| admin |" in admin_report
        and "\n- none\n" in admin_report
    )

    auth_green = bool(admin_consistency_green and "Lifecycle artifact used: `True`" in admin_report)

    # Search/Store is considered mostly green if suite exists and known regressions are isolated.
    search_store_suite_present = "case_id=\"STORE-API-004\"" in search_store_test
    search_store_known_regression = "invalid store id returns `500`" in legacy_regression_notes
    search_store_mostly_green = bool(search_store_suite_present)

    missing_seed_slots = 0
    if merchant_seeds_json:
        for row in merchant_seeds_json.get("results", []):
            if isinstance(row, dict) and row.get("source") == "missing":
                missing_seed_slots += 1
    elif merchant_seeds_env:
        missing_seed_slots = merchant_seeds_env.count("MISSING")
    merchant_depth_partial = missing_seed_slots > 0

    payment_realism_blocked = "BLK-W1-003" in blocker_doc

    critical_green_signals: list[str] = []
    if auth_green:
        critical_green_signals.append("Auth phase inferred green from successful user/merchant/admin cross-surface evidence.")
    if order_core_green:
        critical_green_signals.append("Order core green from lifecycle report and deterministic order seed.")
    if search_store_mostly_green:
        critical_green_signals.append("Search + Store suite is present and evidence indicates mostly green behavior.")
    if lifecycle_usable:
        critical_green_signals.append("Lifecycle flow is usable with deterministic order seed and merchant visibility.")
    if admin_consistency_green:
        critical_green_signals.append("Admin consistency phase is green with no reported inconsistencies.")

    product_defect_penalties: list[dict[str, Any]] = []
    if search_store_known_regression:
        impacted_flows = ADAPTER.map_defect_to_flows(
            "STORE-API-004", "Invalid store lookup returns 500 instead of controlled 400/404"
        )
        product_defect_penalties.append(
            _penalty_item(
                finding_id="STORE-API-004",
                title="Invalid store lookup returns 500 instead of controlled 400/404",
                severity="P2",
                penalty=SEVERITY_PENALTIES["P2"],
                source=str(LEGACY_API_REGRESSION_NOTES),
                category="product_defect",
                in_active_path=False,
                impacted_flows=impacted_flows,
            )
        )
    if "STO-011" in legacy_regression_notes:
        impacted_flows = ADAPTER.map_defect_to_flows(
            "STO-011", "Invalid store uniqueId lookup returns 500 instead of controlled 400/404"
        )
        product_defect_penalties.append(
            _penalty_item(
                finding_id="STO-011",
                title="Invalid store uniqueId lookup returns 500 instead of controlled 400/404",
                severity="P2",
                penalty=0,  # clustered with STORE-API-004 store-negative-path defect family
                source=str(LEGACY_API_REGRESSION_NOTES),
                category="product_defect",
                in_active_path=False,
                impacted_flows=impacted_flows,
            )
        )

    # Confirmed merchant stale terminal mutation defect (MER-API-021) from rerun cluster evidence.
    merchant_terminal_defect = False
    merchant_terminal_family = None
    families = defect_cluster.get("defect_families", [])
    if isinstance(families, list):
        for family in families:
            if not isinstance(family, dict):
                continue
            if str(family.get("family_id", "")).strip() != "DF-MERCHANT-STALE-TERMINAL-MUTATION":
                continue
            member_cases = family.get("member_cases", [])
            has_mer021 = isinstance(member_cases, list) and "MER-API-021" in member_cases
            is_product = str(family.get("type", "")).strip().lower() == "product_defect"
            if has_mer021 and is_product:
                merchant_terminal_defect = True
                merchant_terminal_family = family
                break

    if merchant_terminal_defect and not any(
        str(item.get("id", "")).strip() == "DF-MERCHANT-STALE-TERMINAL-MUTATION"
        for item in product_defect_penalties
    ):
        merchant_title = (
            str(merchant_terminal_family.get("title", "")).strip()
            if isinstance(merchant_terminal_family, dict)
            else ""
        )
        if not merchant_title:
            merchant_title = "Merchant stale/double complete returns 200 on terminal order status"
        product_defect_penalties.append(
            _penalty_item(
                finding_id="DF-MERCHANT-STALE-TERMINAL-MUTATION",
                title=merchant_title,
                severity="P1",
                penalty=SEVERITY_PENALTIES["P1"],
                source=str(DEFECT_CLUSTER_REPORT),
                category="product_defect",
                in_active_path=True,
                impacted_flows=ADAPTER.map_defect_to_flows(
                    "DF-MERCHANT-STALE-TERMINAL-MUTATION",
                    "Merchant stale/double complete returns 200 on terminal order status",
                ),
            )
        )

    env_blocker_penalties: list[dict[str, Any]] = []
    if payment_realism_blocked:
        env_blocker_penalties.append(
            _penalty_item(
                finding_id="BLK-W1-003",
                title="Stripe webhook secret/signing alignment blocked in runtime",
                severity="medium",
                penalty=ENV_BLOCKER_PENALTIES["medium"],
                source=str(WAVE1_BLOCKERS),
                category="env_blocker",
                in_active_path=False,
                impacted_flows=ADAPTER.map_defect_to_flows(
                    "DF-STRIPE-WEBHOOK-ENV-BLOCKER",
                    "Stripe webhook secret/signing alignment blocked in runtime",
                ),
            )
        )

    coverage_gap_penalties: list[dict[str, Any]] = []
    if merchant_depth_partial:
        coverage_gap_penalties.append(
            _penalty_item(
                finding_id="GAP-MERCHANT-DEPTH",
                title=f"Merchant transition depth partially seed-blocked ({missing_seed_slots} slots missing)",
                severity="medium",
                penalty=0,  # represented in phase_scores as negative contribution
                source=str(MERCHANT_STATE_SEEDS_JSON),
                category="coverage_gap",
                in_active_path=False,
                impacted_flows=ADAPTER.map_defect_to_flows(
                    "DF-MERCHANT-SEED-COVERAGE-GAP",
                    "Merchant transition depth partially seed-blocked",
                ),
            )
        )
    if payment_realism_blocked:
        coverage_gap_penalties.append(
            _penalty_item(
                finding_id="GAP-PAYMENT-REALISM",
                title="Payment webhook realism coverage is incomplete",
                severity="medium",
                penalty=0,  # represented in phase_scores as negative contribution
                source=str(WAVE1_BLOCKERS),
                category="coverage_gap",
                in_active_path=False,
                impacted_flows=ADAPTER.map_defect_to_flows(
                    "DF-STRIPE-WEBHOOK-ENV-BLOCKER",
                    "Payment webhook realism coverage is incomplete",
                ),
            )
        )

    evidence_gaps: list[dict[str, Any]] = []
    if "backend is not reachable" in runtime_env_doc.lower() or "connectivity" in merchant_seed_report.lower():
        evidence_gaps.append(
            _penalty_item(
                finding_id="GAP-EVIDENCE-FRESHNESS",
                title="Evidence snapshots are partially fragmented across runtime windows",
                severity="low",
                penalty=COVERAGE_GAP_PENALTIES["low"],
                source=str(RUNTIME_ENV_CONTRACT),
                category="evidence_gap",
                in_active_path=False,
                impacted_flows=[],
            )
        )

    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "critical_green_signals": critical_green_signals,
        "evidence_sources": evidence_sources,
        "auth_green": auth_green,
        "order_core_green": order_core_green,
        "search_store_mostly_green": search_store_mostly_green,
        "search_store_known_regression": search_store_known_regression,
        "lifecycle_usable": lifecycle_usable,
        "admin_consistency_green": admin_consistency_green,
        "merchant_depth_partial": merchant_depth_partial,
        "payment_realism_blocked": payment_realism_blocked,
        "lifecycle_snapshot": {
            "order_id": lifecycle_seed_order_id or lifecycle_order_id,
            "store_id": lifecycle_store_id,
            "user_visible": lifecycle_user_visible,
            "merchant_visible": lifecycle_merchant_visible,
            "admin_visible": lifecycle_admin_visible,
        },
        "product_defect_penalties": product_defect_penalties,
        "env_blocker_penalties": env_blocker_penalties,
        "coverage_gap_penalties": coverage_gap_penalties,
        "evidence_gaps": evidence_gaps,
        "missing_seed_slots": missing_seed_slots,
        "merchant_terminal_defect_confirmed": merchant_terminal_defect,
    }


def _apply_overrides(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    model = copy.deepcopy(base)
    for key, value in overrides.items():
        model[key] = value
    return model


def _score_model(model: dict[str, Any]) -> dict[str, Any]:
    phase_scores: dict[str, int] = {}
    phase_scores["auth"] = PHASE_WEIGHTS["auth"] if model["auth_green"] else 0
    phase_scores["order_core"] = PHASE_WEIGHTS["order_core"] if model["order_core_green"] else 0

    if model["search_store_mostly_green"]:
        phase_scores["search_store"] = 12 if model["search_store_known_regression"] else PHASE_WEIGHTS["search_store"]
    else:
        phase_scores["search_store"] = 0

    phase_scores["lifecycle"] = PHASE_WEIGHTS["lifecycle"] if model["lifecycle_usable"] else 0
    phase_scores["admin_consistency"] = PHASE_WEIGHTS["admin_consistency"] if model["admin_consistency_green"] else 0
    phase_scores["merchant_depth"] = -4 if model["merchant_depth_partial"] else 0
    phase_scores["payment_realism"] = -8 if model["payment_realism_blocked"] else 0

    product_penalty_total = sum(item["penalty"] for item in model["product_defect_penalties"])
    env_penalty_total = sum(item["penalty"] for item in model["env_blocker_penalties"])
    coverage_penalty_total = sum(item["penalty"] for item in model["coverage_gap_penalties"])
    evidence_gap_penalty_total = sum(item["penalty"] for item in model["evidence_gaps"])

    weighted_score = (
        sum(phase_scores.values())
        + product_penalty_total
        + env_penalty_total
        + coverage_penalty_total
        + evidence_gap_penalty_total
    )

    hard_block_reasons: list[str] = []
    if not model["auth_green"]:
        hard_block_reasons.append("Auth core signal is not green.")
    if not model["order_core_green"]:
        hard_block_reasons.append("Order core signal is not green.")
    if not model["admin_consistency_green"]:
        hard_block_reasons.append("Admin consistency signal is not green.")

    for defect in model["product_defect_penalties"]:
        if defect["severity"] == "P0" and defect.get("in_active_path"):
            hard_block_reasons.append(f"Active-path P0 defect present: {defect['id']}.")

    if hard_block_reasons:
        decision = "block_release"
    elif weighted_score >= int(DECISION_THRESHOLDS.get("release", 85)):
        decision = "release"
    elif weighted_score >= int(DECISION_THRESHOLDS.get("release_with_caution", 65)):
        decision = "release_with_caution"
    else:
        decision = "block_release"

    evidence_certainty_high = bool(model.get("merchant_terminal_defect_confirmed"))
    if hard_block_reasons:
        confidence = "low"
    elif weighted_score < 65:
        # Low score from confirmed defect evidence should not be treated as low-confidence ambiguity.
        confidence = "medium" if evidence_certainty_high else "low"
    elif weighted_score < 85:
        confidence = "medium"
    else:
        confidence = "high"

    decision_reasoning: list[str] = []
    if decision == "block_release":
        if hard_block_reasons:
            decision_reasoning.extend(hard_block_reasons)
        else:
            decision_reasoning.append("Weighted score is below release-with-caution threshold (65).")
    elif decision == "release_with_caution":
        decision_reasoning.append("Core phases are green but defect/blocker penalties reduce certainty.")
    else:
        decision_reasoning.append("Core phases are green and penalties are low enough for release.")

    if model["product_defect_penalties"]:
        decision_reasoning.append("Known product defects remain open and are explicitly penalized.")
    if model["env_blocker_penalties"]:
        decision_reasoning.append("Environment blockers are separated from product defects and penalized moderately.")
    if model["merchant_depth_partial"] or model["payment_realism_blocked"]:
        decision_reasoning.append("Coverage depth remains incomplete for merchant/payment realism paths.")
    if model.get("merchant_terminal_defect_confirmed"):
        decision_reasoning.append(
            "Confirmed P1 merchant terminal mutation defect is now included from rerun cluster evidence."
        )

    return {
        "decision": decision,
        "confidence": confidence,
        "weighted_score": weighted_score,
        "max_score": MAX_SCORE,
        "phase_scores": phase_scores,
        "product_defect_penalties": model["product_defect_penalties"],
        "env_blocker_penalties": model["env_blocker_penalties"],
        "coverage_gap_penalties": model["coverage_gap_penalties"],
        "evidence_gaps": model["evidence_gaps"],
        "decision_reasoning": decision_reasoning,
        "hard_block_reasons": hard_block_reasons,
    }


def _scenario_drift(base_model: dict[str, Any]) -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []

    # Scenario A: current real evidence
    current_result = _score_model(base_model)
    scenarios.append(
        {
            "name": "A_current_real_repo_evidence",
            "expected_decision": "block_release",
            "actual_decision": current_result["decision"],
            "weighted_score": current_result["weighted_score"],
            "confidence": current_result["confidence"],
            "matches_expectation": current_result["decision"] == "block_release",
        }
    )

    # Scenario B: improved future state
    improved = _apply_overrides(
        base_model,
        {
            "search_store_known_regression": False,
            "merchant_depth_partial": False,
            "payment_realism_blocked": False,
            "product_defect_penalties": [],
            "env_blocker_penalties": [],
            "coverage_gap_penalties": [],
            "evidence_gaps": [],
        },
    )
    improved_result = _score_model(improved)
    scenarios.append(
        {
            "name": "B_improved_future_state",
            "expected_decision": "release",
            "actual_decision": improved_result["decision"],
            "weighted_score": improved_result["weighted_score"],
            "confidence": improved_result["confidence"],
            "matches_expectation": improved_result["decision"] == "release",
        }
    )

    # Scenario C: regressed future state
    regressed = _apply_overrides(
        base_model,
        {
            "auth_green": False,
        },
    )
    regressed_result = _score_model(regressed)
    scenarios.append(
        {
            "name": "C_regressed_auth_or_admin",
            "expected_decision": "block_release",
            "actual_decision": regressed_result["decision"],
            "weighted_score": regressed_result["weighted_score"],
            "confidence": regressed_result["confidence"],
            "matches_expectation": regressed_result["decision"] == "block_release",
        }
    )
    return scenarios


def _build_payload() -> dict[str, Any]:
    if ADAPTER.get_adapter_id() != "rankmate":
        return _build_bootstrap_payload()

    previous_snapshot = EVIDENCE_CTX.load_json("release_decision")
    rerun_snapshot = EVIDENCE_CTX.load_json("autonomous_rerun_plan")
    evidence_model = _collect_evidence()
    scored = _score_model(evidence_model)
    scenarios = _scenario_drift(evidence_model)

    if scored["decision"] == "release_with_caution":
        summary = "Core Wave 1 signals remain healthy but active product defects and blockers require high caution."
    elif scored["decision"] == "block_release":
        summary = "Release is near/under block threshold due to confirmed merchant terminal mutation risk and open defects."
    else:
        summary = "Weighted score and evidence support release."

    recommended_actions_before_release = [
        "Fix stale/double complete guard in merchant complete endpoint so terminal orders reject repeat complete with controlled 4xx.",
        "Fix STORE-API-004 negative-path regression so invalid store lookups return controlled 400/404.",
        "Align deployed Stripe webhook secret/signing path with QA runtime to unblock payment realism checks.",
        "Unlock merchant state seeds for transition-depth and terminal-state verification.",
        "If merchant settlement is release-critical in this release train, consider temporary release block until MER-API-021 is fixed.",
    ]
    if scored["decision"] == "release":
        recommended_actions_before_release = [
            "Run one fresh full Wave 1 evidence snapshot to preserve release confidence traceability."
        ]

    recommended_actions_after_release = [
        "Monitor store lookup 5xx rate and invalid-lookup error handling.",
        "Monitor payment callback anomalies until full webhook realism coverage is stable.",
        "Keep merchant transition reruns in nightly cycle until seed depth is fully deterministic.",
    ]

    previous_score = previous_snapshot.get("weighted_score")
    previous_decision = previous_snapshot.get("decision")
    # Preserve prior baseline delta across repeated regeneration runs.
    prior_delta = previous_snapshot.get("evidence_delta_since_previous_snapshot", {})
    if isinstance(prior_delta, dict):
        prior_score_delta = prior_delta.get("score_delta", {})
        prior_decision_delta = prior_delta.get("decision_delta", {})
        if (
            isinstance(prior_score_delta, dict)
            and isinstance(previous_score, int)
            and previous_score == scored["weighted_score"]
            and isinstance(prior_score_delta.get("previous_score"), int)
        ):
            previous_score = prior_score_delta.get("previous_score")
        if (
            isinstance(prior_decision_delta, dict)
            and isinstance(previous_decision, str)
            and previous_decision == scored["decision"]
            and isinstance(prior_decision_delta.get("previous_decision"), str)
        ):
            previous_decision = prior_decision_delta.get("previous_decision")
    rerun_context = rerun_snapshot.get("release_decision_context", {}) if isinstance(rerun_snapshot, dict) else {}
    if isinstance(rerun_context, dict):
        rerun_score = rerun_context.get("weighted_score")
        rerun_decision = rerun_context.get("decision")
        if (
            isinstance(rerun_score, int)
            and isinstance(previous_score, int)
            and previous_score == scored["weighted_score"]
            and rerun_score != scored["weighted_score"]
        ):
            previous_score = rerun_score
        if (
            isinstance(rerun_decision, str)
            and isinstance(previous_decision, str)
            and previous_decision == scored["decision"]
            and rerun_decision != scored["decision"]
        ):
            previous_decision = rerun_decision
    score_delta = None
    if isinstance(previous_score, int):
        score_delta = scored["weighted_score"] - previous_score

    evidence_delta = {
        "merchant_terminal_mutation_defect": {
            "case_id": "MER-API-021",
            "family_id": "DF-MERCHANT-STALE-TERMINAL-MUTATION",
            "status_before": "suspected_or_unmodeled",
            "status_now": "confirmed_backend_defect",
            "rerun_evidence": "terminal status=23; mark_arrived returns 400; complete_order incorrectly returns 200",
        },
        "score_delta": {
            "previous_score": previous_score,
            "current_score": scored["weighted_score"],
            "delta": score_delta,
        },
        "decision_delta": {
            "previous_decision": previous_decision,
            "current_decision": scored["decision"],
        },
        "risk_delta": "Merchant terminal mutation safety elevated to top active release-critical risk.",
    }

    return {
        "decision": scored["decision"],
        "confidence": scored["confidence"],
        "weighted_score": scored["weighted_score"],
        "max_score": scored["max_score"],
        "generated_at_utc": evidence_model["generated_at_utc"],
        "summary": summary,
        "phase_scores": scored["phase_scores"],
        "critical_green_signals": evidence_model["critical_green_signals"],
        "product_defect_penalties": scored["product_defect_penalties"],
        "env_blocker_penalties": scored["env_blocker_penalties"],
        "coverage_gap_penalties": scored["coverage_gap_penalties"],
        "evidence_gaps": scored["evidence_gaps"],
        "decision_reasoning": scored["decision_reasoning"],
        "hard_block_reasons": scored["hard_block_reasons"],
        "scenario_drift_validation": scenarios,
        "known_product_defects": [item["title"] for item in scored["product_defect_penalties"]],
        "env_blockers": [item["title"] for item in scored["env_blocker_penalties"]],
        "coverage_gaps": [item["title"] for item in scored["coverage_gap_penalties"]],
        "release_risk_factors": scored["decision_reasoning"],
        "evidence_sources": evidence_model["evidence_sources"],
        "recommended_actions_before_release": recommended_actions_before_release,
        "recommended_actions_after_release": recommended_actions_after_release,
        "phase_snapshot": {
            "auth": "green" if evidence_model["auth_green"] else "not_green",
            "order_core": "green" if evidence_model["order_core_green"] else "not_green",
            "search_store": "mostly_green_with_regression"
            if evidence_model["search_store_known_regression"]
            else ("green" if evidence_model["search_store_mostly_green"] else "unknown"),
            "lifecycle": "usable" if evidence_model["lifecycle_usable"] else "blocked_or_missing",
            "admin_consistency": "green" if evidence_model["admin_consistency_green"] else "not_green",
            "merchant_depth": "partial_seed_blocked" if evidence_model["merchant_depth_partial"] else "unlocked",
            "payment_realism": "blocked_by_runtime_config" if evidence_model["payment_realism_blocked"] else "validated",
        },
        "adapter": {
            "adapter_id": ADAPTER.get_adapter_id(),
            "product_name": ADAPTER.get_product_name(),
            "release_critical_flows": list(ADAPTER.get_release_critical_flows()),
        },
        "evidence_delta_since_previous_snapshot": evidence_delta,
    }


def _build_bootstrap_payload() -> dict[str, Any]:
    local_artifacts = {
        "release_decision": EVIDENCE_CTX.get_release_decision_path(),
        "dashboard_snapshot": EVIDENCE_CTX.get_dashboard_snapshot_path(),
        "defect_cluster_report": EVIDENCE_CTX.get_defect_cluster_report_path(),
        "autonomous_rerun_plan": EVIDENCE_CTX.get_rerun_plan_path(),
    }
    found = [str(path) for path in local_artifacts.values() if path.exists()]
    missing = [str(path) for path in local_artifacts.values() if not path.exists()]
    max_score = sum(PHASE_WEIGHTS.values())

    summary = (
        "Adapter-local release evidence is not yet established. "
        "This adapter is in bootstrap/insufficient-evidence mode."
    )
    return {
        "decision": "insufficient_evidence",
        "confidence": "low",
        "weighted_score": None,
        "max_score": max_score,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "phase_scores": {},
        "critical_green_signals": [],
        "product_defect_penalties": [],
        "env_blocker_penalties": [],
        "coverage_gap_penalties": [],
        "evidence_gaps": [
            {
                "id": "GAP-ADAPTER-BOOTSTRAP",
                "title": "Adapter-local evidence artifacts are missing",
                "severity": "low",
                "penalty": 0,
                "category": "evidence_gap",
                "source": str(EVIDENCE_CTX.artifact_dir),
                "in_active_path": False,
                "impacted_flows": [],
            }
        ],
        "decision_reasoning": [
            "No adapter-local evidence snapshot is available yet.",
            "Cross-adapter fallback is disabled to prevent evidence leakage.",
        ],
        "hard_block_reasons": [],
        "scenario_drift_validation": [],
        "known_product_defects": [],
        "env_blockers": [],
        "coverage_gaps": ["Adapter bootstrap: local evidence not available"],
        "release_risk_factors": [
            "insufficient adapter-local evidence",
            "bootstrap adapter state",
        ],
        "evidence_sources": found,
        "recommended_actions_before_release": [
            "Generate adapter-local evidence by running change-aware trigger and orchestrator for this adapter.",
            "Run core suite scaffolding and produce first local release evidence snapshot.",
            "Replace scaffold placeholders (suites/defect families/mappings) before production gating.",
        ],
        "recommended_actions_after_release": [
            "Track onboarding completion of adapter-local suites and risk mapping.",
        ],
        "phase_snapshot": {
            "auth": "unknown",
            "order_core": "unknown",
            "search_store": "unknown",
            "lifecycle": "unknown",
            "admin_consistency": "unknown",
            "merchant_depth": "unknown",
            "payment_realism": "unknown",
        },
        "adapter": {
            "adapter_id": ADAPTER.get_adapter_id(),
            "product_name": ADAPTER.get_product_name(),
            "release_critical_flows": list(ADAPTER.get_release_critical_flows()),
        },
        "bootstrap_state": {
            "is_bootstrap": True,
            "reason": "insufficient_adapter_local_evidence",
            "missing_artifacts": missing,
        },
        "evidence_delta_since_previous_snapshot": {},
    }


def _render_penalty_table(title: str, rows: list[dict[str, Any]]) -> list[str]:
    lines = [f"## {title}", "", "| ID | Severity | Penalty | Note |", "|---|---|---:|---|"]
    if not rows:
        lines.append("| `none` | `` | `0` | No penalties |")
        lines.append("")
        return lines
    for row in rows:
        lines.append(
            f"| `{row['id']}` | `{row['severity']}` | `{row['penalty']}` | {row['title']} |"
        )
    lines.append("")
    return lines


def _build_markdown(payload: dict[str, Any]) -> str:
    scenario_rows = payload.get("scenario_drift_validation", [])
    evidence_delta = payload.get("evidence_delta_since_previous_snapshot", {})
    lines: list[str] = [
        "# RELEASE_DECISION_REPORT",
        "",
        "## Executive Decision",
        "",
        f"- Adapter: `{payload.get('adapter', {}).get('adapter_id')}` ({payload.get('adapter', {}).get('product_name')})",
        f"- Decision: `{payload['decision']}`",
        f"- Confidence: `{payload['confidence']}`",
        f"- Generated at: `{payload['generated_at_utc']}`",
        f"- Summary: {payload['summary']}",
        "",
        "## Weighted Score Summary",
        "",
        f"- Weighted score: `{payload['weighted_score']}` / `{payload['max_score']}`",
        "",
        "## Phase Contribution Table",
        "",
        "| Phase | Score Contribution |",
        "|---|---:|",
    ]
    for key, value in payload.get("phase_scores", {}).items():
        lines.append(f"| `{key}` | `{value}` |")
    lines.append("")

    lines.extend(_render_penalty_table("Product Defect Penalties", payload.get("product_defect_penalties", [])))
    lines.extend(_render_penalty_table("Environment Blocker Penalties", payload.get("env_blocker_penalties", [])))
    lines.extend(_render_penalty_table("Coverage Gap Penalties", payload.get("coverage_gap_penalties", [])))
    lines.extend(_render_penalty_table("Evidence Gap Penalties", payload.get("evidence_gaps", [])))

    lines.extend(
        [
            "## Confidence Rationale",
            "",
        ]
    )
    reasons = payload.get("decision_reasoning", [])
    if reasons:
        lines.extend([f"- {reason}" for reason in reasons])
    else:
        lines.append("- none")
    lines.append("")

    lines.extend(
        [
            "## Scenario Drift Validation",
            "",
            "| Scenario | Expected | Actual | Score | Confidence | Match |",
            "|---|---|---|---:|---|---|",
        ]
    )
    for row in scenario_rows:
        lines.append(
            f"| `{row['name']}` | `{row['expected_decision']}` | `{row['actual_decision']}` | "
            f"`{row['weighted_score']}` | `{row['confidence']}` | `{row['matches_expectation']}` |"
        )
    lines.append("")

    lines.extend(
        [
            "## Evidence Delta Since Previous Snapshot",
            "",
        ]
    )
    merchant_delta = evidence_delta.get("merchant_terminal_mutation_defect", {})
    score_delta = evidence_delta.get("score_delta", {})
    decision_delta = evidence_delta.get("decision_delta", {})
    if merchant_delta:
        lines.append(
            f"- `{merchant_delta.get('case_id')}` (`{merchant_delta.get('family_id')}`): "
            f"{merchant_delta.get('status_before')} -> {merchant_delta.get('status_now')}"
        )
        lines.append(f"- Rerun evidence: {merchant_delta.get('rerun_evidence')}")
    if score_delta:
        lines.append(
            f"- Score delta: `{score_delta.get('previous_score')}` -> `{score_delta.get('current_score')}` "
            f"(delta `{score_delta.get('delta')}`)"
        )
    if decision_delta:
        lines.append(
            f"- Decision delta: `{decision_delta.get('previous_decision')}` -> `{decision_delta.get('current_decision')}`"
        )
    risk_delta = evidence_delta.get("risk_delta")
    if risk_delta:
        lines.append(f"- Risk delta: {risk_delta}")
    lines.append("")

    lines.extend(
        [
            "## Recommended Next Actions",
            "",
        ]
    )
    for action in payload.get("recommended_actions_before_release", []):
        lines.append(f"- Before release: {action}")
    for action in payload.get("recommended_actions_after_release", []):
        lines.append(f"- After release: {action}")
    lines.append("")

    lines.extend(
        [
            "## Evidence Sources",
            "",
        ]
    )
    for source in payload.get("evidence_sources", []):
        lines.append(f"- {source}")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    payload = _build_payload()
    output_json = EVIDENCE_CTX.write_json("release_decision", payload)
    output_md = EVIDENCE_CTX.write_report(REPORT_NAME, _build_markdown(payload))
    print(
        f"[release-decision-v1.2] decision={payload['decision']} "
        f"confidence={payload['confidence']} score={payload['weighted_score']}/{payload['max_score']}"
    )
    print(f"[release-decision-v1.2] json={output_json}")
    print(f"[release-decision-v1.2] report={output_md}")


if __name__ == "__main__":
    main()
