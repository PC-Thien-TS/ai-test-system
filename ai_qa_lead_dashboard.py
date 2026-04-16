"""AI QA Lead Dashboard v1 aggregator for RankMate Wave 1 intelligence."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.adapters import get_active_adapter
from orchestrator.adapters.evidence_context import get_adapter_evidence_context


REPO_ROOT = Path(__file__).resolve().parent
INPUT_LIFECYCLE_SEED = REPO_ROOT / "order_lifecycle_seed.json"
INPUT_MERCHANT_SEEDS = REPO_ROOT / "merchant_state_seeds.json"
ADAPTER = get_active_adapter()
EVIDENCE_CTX = get_adapter_evidence_context(ADAPTER.get_adapter_id())


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _normalize_phase_health(phase_snapshot: dict[str, Any]) -> dict[str, str]:
    expected = [
        "auth",
        "order_core",
        "search_store",
        "lifecycle",
        "admin_consistency",
        "merchant_depth",
        "payment_realism",
    ]
    normalized: dict[str, str] = {}
    for phase in expected:
        value = phase_snapshot.get(phase, "unknown")
        normalized[phase] = str(value)
    return normalized


def _family_status(family: dict[str, Any], updated_targets: list[dict[str, Any]]) -> str:
    family_type = str(family.get("type", "")).lower()
    family_id = str(family.get("family_id", ""))
    if family_type == "env_blocker":
        return "blocked"
    if family_type == "coverage_gap":
        return "blocked"
    if family_id == "DF-STORE-NEGATIVE-500":
        for row in updated_targets:
            if "test_search_store_api.py" in str(row.get("suite", "")) and bool(row.get("blocked")):
                return "suppressed"
    return "active"


def _severity_rank(severity: str) -> int:
    value = severity.upper().strip()
    if value == "P0":
        return 4
    if value == "P1":
        return 3
    if value == "P2":
        return 2
    return 1


def _risk_score_for_family(family: dict[str, Any], status: str) -> int:
    severity = str(family.get("severity_suggestion", "")).upper()
    severity_score = {"P0": 100, "P1": 80, "P2": 60}.get(severity, 40)
    release_impact = str(family.get("release_impact", "")).lower()
    impact_bonus = 20 if release_impact == "release-critical" else 10
    type_value = str(family.get("type", "")).lower()
    type_bonus = {"product_defect": 15, "env_blocker": 8, "coverage_gap": 5}.get(type_value, 0)
    status_adjust = {"active": 10, "blocked": 0, "suppressed": -10}.get(status, 0)
    return severity_score + impact_bonus + type_bonus + status_adjust


def _flow_name_for_family_id(family_id: str) -> str:
    flow_id = ADAPTER.infer_family_flow(family_id, family_id) or ""
    if flow_id:
        flow = ADAPTER.get_flow_registry().get(flow_id)
        if flow:
            return flow.title.lower()
    return "cross-surface quality operations"


def _build_dashboard() -> dict[str, Any]:
    release_data = EVIDENCE_CTX.load_json("release_decision")
    rerun_data = EVIDENCE_CTX.load_json("autonomous_rerun_plan")
    healing_data = EVIDENCE_CTX.load_json("defect_cluster_report")
    if ADAPTER.get_adapter_id() == "rankmate":
        lifecycle_seed = _read_json(INPUT_LIFECYCLE_SEED)
        merchant_seeds = _read_json(INPUT_MERCHANT_SEEDS)
    else:
        lifecycle_seed = {}
        merchant_seeds = {}

    bootstrap_state = bool(
        not release_data
        or not EVIDENCE_CTX.artifact_exists("release_decision")
        or not EVIDENCE_CTX.artifact_exists("defect_cluster_report")
        or not EVIDENCE_CTX.artifact_exists("autonomous_rerun_plan")
        or not EVIDENCE_CTX.artifact_exists("dashboard_snapshot")
        or
        str(release_data.get("decision", "")).strip().lower() == "insufficient_evidence"
        or release_data.get("bootstrap_state", {}).get("is_bootstrap") is True
    )

    phase_snapshot_raw = release_data.get("phase_snapshot", {})
    phase_snapshot = phase_snapshot_raw if isinstance(phase_snapshot_raw, dict) else {}
    quality_health = _normalize_phase_health(phase_snapshot)

    updated_targets = healing_data.get("updated_targets", [])
    if not isinstance(updated_targets, list):
        updated_targets = []

    families_raw = healing_data.get("defect_families", [])
    families = families_raw if isinstance(families_raw, list) else []

    active_families: list[dict[str, Any]] = []
    for family in families:
        if not isinstance(family, dict):
            continue
        status = _family_status(family, updated_targets)
        risk_score = _risk_score_for_family(family, status)
        active_families.append(
            {
                "family_id": family.get("family_id"),
                "title": family.get("title"),
                "type": family.get("type"),
                "suggested_severity": family.get("severity_suggestion"),
                "release_impact": family.get("release_impact"),
                "member_cases": family.get("member_cases", []),
                "status": status,
                "risk_score": risk_score,
                "recommended_next_action": family.get("recommended_next_action"),
            }
        )

    active_families.sort(
        key=lambda row: (
            -int(row.get("risk_score", 0)),
            -_severity_rank(str(row.get("suggested_severity", ""))),
            str(row.get("family_id", "")),
        )
    )

    highest_risk = active_families[0] if active_families else {}
    highest_risk_flow = _flow_name_for_family_id(str(highest_risk.get("family_id", "")))
    merchant_terminal_confirmed = (
        str(highest_risk.get("family_id", "")) == "DF-MERCHANT-STALE-TERMINAL-MUTATION"
        or any(
            str(item.get("family_id", "")) == "DF-MERCHANT-STALE-TERMINAL-MUTATION"
            for item in active_families
        )
    )

    env_blockers = [item for item in active_families if item.get("type") == "env_blocker"]
    coverage_gaps = [item for item in active_families if item.get("type") == "coverage_gap"]
    seed_state = healing_data.get("seed_state_delta", {})
    if not isinstance(seed_state, dict):
        seed_state = {}
    seed_blockers = [
        {
            "slot": slot,
            "reason": "missing deterministic seed",
        }
        for slot in seed_state.get("merchant_missing_slots_after", [])
    ]

    rerun_ops = {
        "rerun_action": healing_data.get("updated_rerun_action", rerun_data.get("rerun_action")),
        "target_suites": [row.get("suite") for row in updated_targets],
        "runnable_commands": healing_data.get("updated_powershell_commands", rerun_data.get("powershell_commands", [])),
        "blocked_reruns": [
            row
            for row in updated_targets
            if isinstance(row, dict) and bool(row.get("blocked"))
        ],
        "suppressions": healing_data.get("blocker_suppression_notes", []),
    }

    healing_actions = {
        "actions_run": healing_data.get("healing_actions_run", []),
        "actions_skipped": healing_data.get("healing_actions_skipped", []),
        "effect_summary": {
            "merchant_missing_slots_before": seed_state.get("merchant_missing_slots_before", []),
            "merchant_missing_slots_after": seed_state.get("merchant_missing_slots_after", []),
            "merchant_critical_missing_slots_after": seed_state.get("merchant_critical_missing_slots_after", []),
        },
        "new_seeds_unlocked": sorted(
            set(seed_state.get("merchant_missing_slots_before", []))
            - set(seed_state.get("merchant_missing_slots_after", []))
        ),
    }

    decision = str(release_data.get("decision", "insufficient_evidence" if bootstrap_state else "unknown"))
    should_block = decision == "block_release"
    should_caution = decision == "release_with_caution"

    ranked_actions = []
    if highest_risk.get("recommended_next_action"):
        ranked_actions.append(str(highest_risk["recommended_next_action"]))
    for rec in healing_data.get("release_gate_adjustment_recommendations", []):
        ranked_actions.append(str(rec))
    for rec in release_data.get("recommended_actions_before_release", []):
        ranked_actions.append(str(rec))
    dedup_ranked = []
    for item in ranked_actions:
        if item and item not in dedup_ranked:
            dedup_ranked.append(item)

    executive_summary = {
        "decision": decision,
        "weighted_score": release_data.get("weighted_score"),
        "max_score": release_data.get("max_score"),
        "confidence": release_data.get("confidence"),
        "top_reason_for_caution_or_block": (
            (release_data.get("decision_reasoning") or ["No explicit reasoning found."])[0]
            if isinstance(release_data.get("decision_reasoning"), list)
            else release_data.get("summary")
        ),
        "highest_risk_flow": highest_risk_flow,
        "last_generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "bootstrap_state": bootstrap_state,
    }

    release_manager_view = {
        "recommended_next_engineering_actions": dedup_ranked[:5],
        "recommended_next_qa_actions": [
            "After backend fix deploy, rerun: python -m pytest -q -rs tests/rankmate_wave1/test_merchant_transition_api.py",
            "Defer payment rerun until Stripe secret/signature alignment is confirmed.",
            "Rerun release gate after merchant rerun and any backend fixes to defect families.",
        ],
        "should_release_be_blocked": should_block,
        "should_release_with_caution": should_caution,
        "top_post_release_watch_items": release_data.get("recommended_actions_after_release", []),
        "risk_advisory": (
            "Adapter is in bootstrap mode with insufficient local evidence."
            if bootstrap_state
            else
            "Confirmed P1 merchant active-path defect (MER-API-021). Treat release as high caution; "
            "if merchant settlement is release-critical, consider temporary release block."
            if merchant_terminal_confirmed
            else "No new active-path merchant defect advisory."
        ),
    }

    evidence_sources = [
        str(path)
        for path in (
            EVIDENCE_CTX.get_release_decision_path(),
            EVIDENCE_CTX.get_rerun_plan_path(),
            EVIDENCE_CTX.get_defect_cluster_report_path(),
        )
        if path.exists()
    ]
    if ADAPTER.get_adapter_id() == "rankmate":
        for path in (INPUT_LIFECYCLE_SEED, INPUT_MERCHANT_SEEDS):
            if path.exists():
                evidence_sources.append(str(path))

    return {
        "adapter": {
            "adapter_id": ADAPTER.get_adapter_id(),
            "product_name": ADAPTER.get_product_name(),
        },
        "executive_summary": executive_summary,
        "quality_health": quality_health,
        "active_defect_families": active_families,
        "env_blockers": env_blockers,
        "coverage_gaps": coverage_gaps,
        "seed_blockers": seed_blockers,
        "rerun_operations": rerun_ops,
        "healing_actions": healing_actions,
        "release_manager_view": release_manager_view,
        "evidence_delta_since_previous_snapshot": release_data.get("evidence_delta_since_previous_snapshot", {}),
        "supporting_artifacts": {
            "lifecycle_seed_order_id": lifecycle_seed.get("order_id"),
            "lifecycle_seed_final_status": lifecycle_seed.get("final_status"),
            "merchant_seed_generated_at": merchant_seeds.get("generatedAtUtc"),
        },
        "bootstrap_state": bootstrap_state,
        "evidence_sources": evidence_sources,
    }


def _render_markdown(snapshot: dict[str, Any]) -> str:
    exec_summary = snapshot.get("executive_summary", {})
    quality = snapshot.get("quality_health", {})
    families = snapshot.get("active_defect_families", [])
    rerun = snapshot.get("rerun_operations", {})
    healing = snapshot.get("healing_actions", {})
    release_view = snapshot.get("release_manager_view", {})
    evidence_delta = snapshot.get("evidence_delta_since_previous_snapshot", {})

    lines: list[str] = []
    lines.extend(
        [
            "# AI_QA_LEAD_DASHBOARD_REPORT",
            "",
            "## Executive Summary",
            "",
            f"- Adapter: `{snapshot.get('adapter', {}).get('adapter_id')}` ({snapshot.get('adapter', {}).get('product_name')})",
            f"- Decision: `{exec_summary.get('decision')}`",
            f"- Score: `{exec_summary.get('weighted_score')}` / `{exec_summary.get('max_score')}`",
            f"- Confidence: `{exec_summary.get('confidence')}`",
            f"- Highest-risk flow: `{exec_summary.get('highest_risk_flow')}`",
            f"- Top reason: {exec_summary.get('top_reason_for_caution_or_block')}",
            f"- Generated at (UTC): `{exec_summary.get('last_generated_timestamp_utc')}`",
            "",
            "## Release Decision Snapshot",
            "",
            f"- Should release be blocked: `{release_view.get('should_release_be_blocked')}`",
            f"- Should release with caution: `{release_view.get('should_release_with_caution')}`",
            "",
            "## Current System Health By Phase",
            "",
            "| Phase | Health |",
            "|---|---|",
        ]
    )
    for phase, health in quality.items():
        lines.append(f"| `{phase}` | `{health}` |")

    lines.extend(
        [
            "",
            "## Top Active Defects",
            "",
            "| Family | Severity | Type | Impact | Status | Members |",
            "|---|---|---|---|---|---|",
        ]
    )
    for family in families[:5]:
        members = ", ".join(str(v) for v in family.get("member_cases", [])) or "none"
        lines.append(
            f"| `{family.get('family_id')}` | `{family.get('suggested_severity')}` | `{family.get('type')}` | "
            f"`{family.get('release_impact')}` | `{family.get('status')}` | {members} |"
        )

    lines.extend(["", "## Environment Blockers vs Product Defects", ""])
    env_blockers = snapshot.get("env_blockers", [])
    if env_blockers:
        lines.append("Environment blockers:")
        for item in env_blockers:
            lines.append(f"- `{item.get('family_id')}`: {item.get('title')}")
    else:
        lines.append("Environment blockers: none")
    lines.append("")
    lines.append("Product defects:")
    for item in [f for f in families if f.get("type") == "product_defect"]:
        lines.append(f"- `{item.get('family_id')}`: {item.get('title')} ({item.get('suggested_severity')})")
    if not [f for f in families if f.get("type") == "product_defect"]:
        lines.append("- none")

    lines.extend(["", "## Rerun and Healing Operations", ""])
    lines.append(f"- Current rerun action: `{rerun.get('rerun_action')}`")
    lines.append("- Target suites:")
    for suite in rerun.get("target_suites", []):
        lines.append(f"- `{suite}`")
    if not rerun.get("target_suites"):
        lines.append("- none")
    lines.append("- Runnable commands:")
    for cmd in rerun.get("runnable_commands", []):
        lines.append(f"- `{cmd}`")
    if not rerun.get("runnable_commands"):
        lines.append("- none")
    lines.append("- Blocked reruns:")
    for row in rerun.get("blocked_reruns", []):
        lines.append(f"- `{row.get('suite')}`: {row.get('blocker_reason')}")
    if not rerun.get("blocked_reruns"):
        lines.append("- none")
    lines.append("- Healing actions run:")
    for row in healing.get("actions_run", []):
        lines.append(f"- `{row.get('action_id')}` ({row.get('status')}): `{row.get('command')}`")
    if not healing.get("actions_run"):
        lines.append("- none")

    lines.extend(["", "## Recommended Next Engineering Actions", ""])
    for action in release_view.get("recommended_next_engineering_actions", []):
        lines.append(f"- {action}")
    if not release_view.get("recommended_next_engineering_actions"):
        lines.append("- none")

    lines.extend(["", "## Recommended Next QA Actions", ""])
    for action in release_view.get("recommended_next_qa_actions", []):
        lines.append(f"- {action}")

    lines.extend(["", "## Release Manager Advisory", ""])
    lines.append(f"- {release_view.get('risk_advisory')}")

    lines.extend(["", "## Evidence Delta Since Previous Snapshot", ""])
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
    if evidence_delta.get("risk_delta"):
        lines.append(f"- Risk delta: {evidence_delta.get('risk_delta')}")
    if not evidence_delta:
        lines.append("- none")

    lines.extend(["", "## Post-release Watch Items", ""])
    for item in release_view.get("top_post_release_watch_items", []):
        lines.append(f"- {item}")
    if not release_view.get("top_post_release_watch_items"):
        lines.append("- none")

    return "\n".join(lines)


def main() -> None:
    snapshot = _build_dashboard()
    output_json = EVIDENCE_CTX.write_json("dashboard_snapshot", snapshot)
    output_md = EVIDENCE_CTX.write_report("AI_QA_LEAD_DASHBOARD_REPORT.md", _render_markdown(snapshot))

    exec_summary = snapshot.get("executive_summary", {})
    highest_risk_flow = exec_summary.get("highest_risk_flow")
    next_action = (
        (snapshot.get("release_manager_view", {}).get("recommended_next_engineering_actions") or ["none"])[0]
    )

    print(
        f"[qa-dashboard] decision={exec_summary.get('decision')} "
        f"score={exec_summary.get('weighted_score')} confidence={exec_summary.get('confidence')}"
    )
    print(f"[qa-dashboard] top_risk={highest_risk_flow}")
    print(f"[qa-dashboard] next_action={next_action}")
    print(f"[qa-dashboard] json={output_json}")
    print(f"[qa-dashboard] report={output_md}")


if __name__ == "__main__":
    main()
