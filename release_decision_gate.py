"""Release Decision Gate v1 for RankMate Wave 1 evidence.

Reads existing Wave 1 runtime artifacts and produces:
- release_decision.json
- docs/wave1_runtime/RELEASE_DECISION_REPORT.md
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
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


@dataclass(frozen=True)
class Signal:
    name: str
    status: str
    note: str
    source: str


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
    value = value.strip()
    if not value or value.lower() == "none":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _as_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"true", "1", "yes"}:
        return True
    if lowered in {"false", "0", "no"}:
        return False
    return None


def _status_from_report_markers(text: str) -> str:
    if not text:
        return "missing"
    if "Execution mode: `blocked`" in text:
        return "blocked"
    return "present"


def _build_release_decision() -> dict[str, Any]:
    now_utc = datetime.now(timezone.utc).isoformat()

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

    signals: list[Signal] = []
    known_product_defects: list[str] = []
    env_blockers: list[str] = []
    coverage_gaps: list[str] = []
    risk_factors: list[str] = []
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

    order_report_status = _status_from_report_markers(order_report)
    admin_report_status = _status_from_report_markers(admin_report)

    lifecycle_order_id = _as_int(_extract_backtick_value(order_report, "Main order id"))
    lifecycle_store_id = _as_int(_extract_backtick_value(order_report, "Store id"))
    lifecycle_user_visible = _as_bool(_extract_backtick_value(order_report, "User visible"))
    lifecycle_merchant_visible = _as_bool(_extract_backtick_value(order_report, "Merchant visible"))
    lifecycle_final_status = _extract_backtick_value(order_report, "Final status")

    lifecycle_seed_order_id = order_seed.get("order_id")
    if isinstance(lifecycle_seed_order_id, int):
        signals.append(
            Signal(
                name="lifecycle_seed_order_available",
                status="green",
                note=f"Lifecycle seed provides deterministic order_id={lifecycle_seed_order_id}.",
                source=str(ORDER_LIFECYCLE_SEED),
            )
        )
    elif lifecycle_order_id is not None:
        signals.append(
            Signal(
                name="lifecycle_order_report_available",
                status="green",
                note=f"Lifecycle report includes order_id={lifecycle_order_id}.",
                source=str(ORDER_LIFECYCLE_REPORT),
            )
        )
    else:
        signals.append(
            Signal(
                name="lifecycle_seed_order_available",
                status="blocked",
                note="Lifecycle deterministic order_id not found in seed/report.",
                source=str(ORDER_LIFECYCLE_REPORT),
            )
        )

    order_core_green = bool(
        order_report_status == "present"
        and (lifecycle_order_id is not None or isinstance(lifecycle_seed_order_id, int))
        and lifecycle_store_id is not None
        and lifecycle_user_visible is True
    )
    if order_core_green:
        signals.append(
            Signal(
                name="order_core_phase",
                status="green",
                note="Order lifecycle report shows successful order creation and user visibility.",
                source=str(ORDER_LIFECYCLE_REPORT),
            )
        )
    else:
        risk_factors.append("Order core signal is incomplete or blocked in available evidence.")

    admin_consistency_green = bool(
        admin_report_status == "present"
        and "| user |" in admin_report
        and "| merchant |" in admin_report
        and "| admin |" in admin_report
        and "\n- none\n" in admin_report
    )
    if admin_consistency_green:
        signals.append(
            Signal(
                name="admin_consistency_phase",
                status="green",
                note="Admin consistency report shows no cross-surface inconsistency findings.",
                source=str(ADMIN_CONSISTENCY_REPORT),
            )
        )
    else:
        risk_factors.append("Admin consistency signal is incomplete or contains unresolved findings.")

    # Auth green is inferred from successful cross-surface consistency checks using user/merchant/admin endpoints.
    auth_green = bool(admin_consistency_green and "Lifecycle artifact used: `True`" in admin_report)
    if auth_green:
        signals.append(
            Signal(
                name="auth_phase",
                status="green",
                note="Cross-surface user/merchant/admin checks imply role auth paths were functional in captured run.",
                source=str(ADMIN_CONSISTENCY_REPORT),
            )
        )
    else:
        risk_factors.append("Auth readiness is not strongly evidenced by current runtime reports.")

    # Merchant transition depth / seed readiness
    missing_seed_slots = 0
    if merchant_seeds_json:
        for row in merchant_seeds_json.get("results", []):
            if isinstance(row, dict) and row.get("source") == "missing":
                missing_seed_slots += 1
    elif merchant_seeds_env:
        missing_seed_slots = merchant_seeds_env.count("MISSING")

    if missing_seed_slots > 0:
        coverage_gaps.append(
            f"Merchant transition seed coverage is incomplete ({missing_seed_slots} seed slots missing)."
        )

    if "customer_login=" in merchant_seed_report and "request failed" in merchant_seed_report:
        env_blockers.append(
            "Merchant seed builder diagnostics show runtime connectivity/auth failures while discovering merchant state seeds."
        )

    if "BLK-W1-003" in blocker_doc:
        env_blockers.append(
            "Stripe webhook integrity remains environment-blocked by missing runtime secret/signing alignment."
        )
        coverage_gaps.append("Payment webhook realism coverage is incomplete until Stripe secret alignment is fixed.")

    if "BLK-W1-006" in blocker_doc:
        env_blockers.append(
            "Payment sandbox/gateway wiring inconsistency risk remains for callback-realism coverage."
        )

    # Known product defects (evidence-backed from repo notes + Wave1 case definitions)
    if "STORE-API-004" in search_store_test and "assert_status(response, {400, 404}" in search_store_test:
        if "invalid store id returns `500`" in legacy_regression_notes:
            known_product_defects.append(
                "STORE-API-004 (aligned with STO-009 evidence): invalid store lookup returns 500 instead of controlled 400/404."
            )
        else:
            known_product_defects.append(
                "STORE-API-004 is tracked as critical negative-path guard and should remain monitored for invalid-store 500 regressions."
            )

    if "STO-011" in legacy_regression_notes:
        known_product_defects.append(
            "STO-011: invalid store unique-id lookup returns 500 instead of controlled 400/404 (from regression evidence)."
        )

    # Build core summary
    core_green = auth_green and order_core_green and admin_consistency_green
    has_core_block = not core_green
    critical_product_bug_in_core = False

    # Rule-based decision
    if has_core_block or critical_product_bug_in_core:
        decision = "block_release"
    elif known_product_defects or env_blockers or coverage_gaps:
        decision = "release_with_caution"
    else:
        decision = "release"

    if not risk_factors:
        if known_product_defects:
            risk_factors.append("Known backend defects remain open in store negative-path handling.")
        if env_blockers:
            risk_factors.append("Environment/runtime constraints still block full merchant/payment realism coverage.")
        if coverage_gaps:
            risk_factors.append("Coverage depth for merchant terminal transitions and webhook integrity is incomplete.")

    # Confidence scoring
    score = 0
    if auth_green:
        score += 3
    if order_core_green:
        score += 3
    if admin_consistency_green:
        score += 3
    if lifecycle_merchant_visible is True and lifecycle_final_status is not None:
        score += 1
    score -= min(len(known_product_defects), 2)
    score -= min(len(env_blockers), 2)
    score -= min(len(coverage_gaps), 2)

    if score >= 7:
        confidence = "high"
    elif score >= 4:
        confidence = "medium"
    else:
        confidence = "low"

    critical_green_signals = [f"{s.name}: {s.note}" for s in signals if s.status == "green"]

    if decision == "block_release":
        summary = (
            "Release is blocked because core decision signals are incomplete or high-risk unresolved findings remain."
        )
    elif decision == "release_with_caution":
        summary = (
            "Core Wave 1 signals are healthy enough for cautious release, but known defects and environment/coverage blockers remain."
        )
    else:
        summary = "Core Wave 1 signals are healthy and no blocking risk was detected from available evidence."

    recommended_actions_before_release = [
        "Fix invalid-store lookup regression so negative store-path behavior returns controlled 400/404.",
        "Align deployed Stripe webhook secret/signing path with QA runtime to unblock payment integrity realism checks.",
        "Regenerate merchant state seeds to unlock deeper merchant transition and terminal-state coverage.",
    ]
    if decision == "release":
        recommended_actions_before_release = [
            "Run one final smoke pass for Auth, Order core, and Admin consistency against target release environment."
        ]

    recommended_actions_after_release = [
        "Monitor invalid-store error-rate and 5xx signals for store lookup endpoints.",
        "Track payment callback anomalies until webhook realism coverage is fully unlocked.",
        "Schedule merchant transition depth rerun after deterministic seed slots are filled.",
    ]

    return {
        "decision": decision,
        "confidence": confidence,
        "generated_at_utc": now_utc,
        "summary": summary,
        "critical_green_signals": critical_green_signals,
        "known_product_defects": known_product_defects,
        "env_blockers": env_blockers,
        "coverage_gaps": coverage_gaps,
        "release_risk_factors": risk_factors,
        "evidence_sources": evidence_sources,
        "recommended_actions_before_release": recommended_actions_before_release,
        "recommended_actions_after_release": recommended_actions_after_release,
        "phase_snapshot": {
            "auth": "green" if auth_green else "unknown_or_blocked",
            "order_core": "green" if order_core_green else "unknown_or_blocked",
            "order_lifecycle": "usable" if lifecycle_order_id is not None else "blocked_or_missing",
            "admin_consistency": "green" if admin_consistency_green else "unknown_or_blocked",
            "merchant_transition": "partial_seed_blocked" if missing_seed_slots > 0 else "ready",
            "payment_webhook_realism": "blocked_by_runtime_config" if "BLK-W1-003" in blocker_doc else "unknown",
            "search_store": "known_backend_regression_present" if known_product_defects else "no_known_regression_evidence",
        },
    }


def _build_markdown_report(decision_payload: dict[str, Any]) -> str:
    def _bullets(values: list[str]) -> list[str]:
        return [f"- {value}" for value in values] if values else ["- none"]

    phase = decision_payload.get("phase_snapshot", {})
    lines: list[str] = [
        "# RELEASE_DECISION_REPORT",
        "",
        "## Executive Summary",
        "",
        f"- Decision: `{decision_payload['decision']}`",
        f"- Confidence: `{decision_payload['confidence']}`",
        f"- Generated at: `{decision_payload['generated_at_utc']}`",
        f"- Summary: {decision_payload['summary']}",
        "",
        "## Current Tested Phases",
        "",
        "| Phase | Status |",
        "|---|---|",
        f"| Auth | `{phase.get('auth')}` |",
        f"| Order Core | `{phase.get('order_core')}` |",
        f"| Order Lifecycle | `{phase.get('order_lifecycle')}` |",
        f"| Admin Consistency | `{phase.get('admin_consistency')}` |",
        f"| Merchant Transition | `{phase.get('merchant_transition')}` |",
        f"| Payment Webhook Realism | `{phase.get('payment_webhook_realism')}` |",
        f"| Search + Store | `{phase.get('search_store')}` |",
        "",
        "## What Is Green",
        "",
        *_bullets(decision_payload.get("critical_green_signals", [])),
        "",
        "## Known Product Defects",
        "",
        *_bullets(decision_payload.get("known_product_defects", [])),
        "",
        "## Environment Blockers",
        "",
        *_bullets(decision_payload.get("env_blockers", [])),
        "",
        "## Coverage Gaps",
        "",
        *_bullets(decision_payload.get("coverage_gaps", [])),
        "",
        "## Release Recommendation",
        "",
        f"- `{decision_payload['decision']}` with `{decision_payload['confidence']}` confidence.",
        "",
        "## Rationale",
        "",
        *_bullets(decision_payload.get("release_risk_factors", [])),
        "",
        "## Required Next Actions Before Release",
        "",
        *_bullets(decision_payload.get("recommended_actions_before_release", [])),
        "",
        "## Recommended Actions After Release",
        "",
        *_bullets(decision_payload.get("recommended_actions_after_release", [])),
        "",
        "## Evidence Sources",
        "",
        *_bullets(decision_payload.get("evidence_sources", [])),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    payload = _build_release_decision()
    OUTPUT_JSON.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    OUTPUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD.write_text(_build_markdown_report(payload), encoding="utf-8")
    print(f"[release-decision] decision={payload['decision']} confidence={payload['confidence']}")
    print(f"[release-decision] json={OUTPUT_JSON}")
    print(f"[release-decision] report={OUTPUT_MD}")


if __name__ == "__main__":
    main()
