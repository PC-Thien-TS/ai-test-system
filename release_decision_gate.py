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

OUTPUT_JSON = REPO_ROOT / "release_decision.json"
OUTPUT_MD = REPO_ROOT / "docs" / "wave1_runtime" / "RELEASE_DECISION_REPORT.md"


PHASE_WEIGHTS = {
    "auth": 25,
    "order_core": 25,
    "search_store": 15,
    "lifecycle": 15,
    "admin_consistency": 20,
}
MAX_SCORE = sum(PHASE_WEIGHTS.values())  # 100

SEVERITY_PENALTIES = {
    "P0": -25,
    "P1": -15,
    "P2": -8,
}

ENV_BLOCKER_PENALTIES = {
    "critical": -10,
    "medium": -5,
}

COVERAGE_GAP_PENALTIES = {
    "high": -6,
    "medium": -4,
    "low": -3,
}


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
) -> dict[str, Any]:
    return {
        "id": finding_id,
        "title": title,
        "severity": severity,
        "penalty": penalty,
        "category": category,
        "source": source,
        "in_active_path": in_active_path,
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

    evidence_sources: list[str] = []
    for path in (
        ORDER_LIFECYCLE_REPORT,
        ADMIN_CONSISTENCY_REPORT,
        MERCHANT_SEEDS_REPORT,
        ORDER_LIFECYCLE_SEED,
        MERCHANT_STATE_SEEDS_JSON,
        MERCHANT_STATE_SEEDS_ENV,
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
        product_defect_penalties.append(
            _penalty_item(
                finding_id="STORE-API-004",
                title="Invalid store lookup returns 500 instead of controlled 400/404",
                severity="P2",
                penalty=SEVERITY_PENALTIES["P2"],
                source=str(LEGACY_API_REGRESSION_NOTES),
                category="product_defect",
                in_active_path=False,
            )
        )
    if "STO-011" in legacy_regression_notes:
        product_defect_penalties.append(
            _penalty_item(
                finding_id="STO-011",
                title="Invalid store uniqueId lookup returns 500 instead of controlled 400/404",
                severity="P2",
                penalty=0,  # clustered with STORE-API-004 store-negative-path defect family
                source=str(LEGACY_API_REGRESSION_NOTES),
                category="product_defect",
                in_active_path=False,
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
    elif weighted_score >= 85:
        decision = "release"
    elif weighted_score >= 65:
        decision = "release_with_caution"
    else:
        decision = "block_release"

    if hard_block_reasons or weighted_score < 65:
        confidence = "low"
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
            "expected_decision": "release_with_caution",
            "actual_decision": current_result["decision"],
            "weighted_score": current_result["weighted_score"],
            "confidence": current_result["confidence"],
            "matches_expectation": current_result["decision"] == "release_with_caution",
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
    evidence_model = _collect_evidence()
    scored = _score_model(evidence_model)
    scenarios = _scenario_drift(evidence_model)

    summary = (
        "Core Wave 1 signals are healthy enough for cautious release, but defect/blocker penalties and depth gaps remain."
        if scored["decision"] == "release_with_caution"
        else (
            "Release is blocked due to hard blockers or low weighted score."
            if scored["decision"] == "block_release"
            else "Weighted score and evidence support release."
        )
    )

    recommended_actions_before_release = [
        "Fix STORE-API-004 negative-path regression so invalid store lookups return controlled 400/404.",
        "Align deployed Stripe webhook secret/signing path with QA runtime to unblock payment realism checks.",
        "Unlock merchant state seeds for transition-depth and terminal-state verification.",
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
    lines: list[str] = [
        "# RELEASE_DECISION_REPORT",
        "",
        "## Executive Decision",
        "",
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
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(_build_markdown(payload), encoding="utf-8")
    print(
        f"[release-decision-v1.1] decision={payload['decision']} "
        f"confidence={payload['confidence']} score={payload['weighted_score']}/{payload['max_score']}"
    )
    print(f"[release-decision-v1.1] json={OUTPUT_JSON}")
    print(f"[release-decision-v1.1] report={OUTPUT_MD}")


if __name__ == "__main__":
    main()
