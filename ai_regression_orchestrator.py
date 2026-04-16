"""AI Regression Orchestrator v1 for fast, product-centric regression planning.

Outputs:
- regression_execution_plan.json
- docs/wave1_runtime/AI_REGRESSION_ORCHESTRATOR_REPORT.md
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.adapters import get_active_adapter
from orchestrator.adapters.evidence_context import get_adapter_evidence_context


REPO_ROOT = Path(__file__).resolve().parent
ARTIFACT_MERCHANT_SEEDS = REPO_ROOT / "merchant_state_seeds.json"
ARTIFACT_LIFECYCLE_SEED = REPO_ROOT / "order_lifecycle_seed.json"


@dataclass(frozen=True)
class ProductFlow:
    flow_id: str
    title: str
    suites: tuple[str, ...]
    description: str


ADAPTER = get_active_adapter()
ADAPTER_ID = ADAPTER.get_adapter_id()
ADAPTER_PRODUCT = ADAPTER.get_product_name()
EVIDENCE_CTX = get_adapter_evidence_context(ADAPTER_ID)

FLOW_MODEL: dict[str, ProductFlow] = {
    flow_id: ProductFlow(
        flow_id=flow.flow_id,
        title=flow.title,
        suites=flow.suites,
        description=flow.description,
    )
    for flow_id, flow in ADAPTER.get_flow_registry().items()
}

FLOW_ORDER = ADAPTER.get_flow_order()
CORE_ANCHOR_FLOWS = ADAPTER.get_core_anchor_flows()
INTENT_CHOICES = ADAPTER.get_intent_choices()
MODE_CHOICES = ADAPTER.get_mode_choices()
INTENT_FLOW_BASE = ADAPTER.get_intent_flow_base()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _contains_any(text: str, tokens: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(token.lower() in lowered for token in tokens)


def _flow_for_risk_text(top_risk: str) -> str | None:
    return ADAPTER.map_risk_text_to_flow(top_risk)


def _infer_context() -> dict[str, Any]:
    release = EVIDENCE_CTX.load_json("release_decision")
    snapshot = EVIDENCE_CTX.load_json("dashboard_snapshot")
    cluster = EVIDENCE_CTX.load_json("defect_cluster_report")
    rerun = EVIDENCE_CTX.load_json("autonomous_rerun_plan")
    merchant_seeds = _read_json(ARTIFACT_MERCHANT_SEEDS)
    lifecycle_seed = _read_json(ARTIFACT_LIFECYCLE_SEED)

    exec_summary = _as_dict(snapshot.get("executive_summary"))
    rerun_ops = _as_dict(snapshot.get("rerun_operations"))

    decision = str(exec_summary.get("decision", release.get("decision", "unknown")))
    score = exec_summary.get("weighted_score", release.get("weighted_score"))
    confidence = str(exec_summary.get("confidence", release.get("confidence", "unknown")))
    top_risk = str(exec_summary.get("highest_risk_flow", "unknown"))

    active_families = _as_list(snapshot.get("active_defect_families")) or _as_list(cluster.get("defect_families"))

    blocked_suite_map: dict[str, str] = {}
    for item in _as_list(rerun_ops.get("blocked_reruns")):
        row = _as_dict(item)
        suite = str(row.get("suite", "")).strip()
        reason = str(row.get("blocker_reason", "blocked")).strip()
        if suite:
            blocked_suite_map[suite] = reason

    for item in _as_list(rerun.get("suite_plan")):
        row = _as_dict(item)
        if not bool(row.get("blocked")):
            continue
        suite = str(row.get("suite", "")).strip()
        reason = str(row.get("blocker_reason", "blocked")).strip()
        if suite and suite not in blocked_suite_map:
            blocked_suite_map[suite] = reason

    suppressions = [str(s) for s in _as_list(rerun_ops.get("suppressions"))]
    env_blockers = _as_list(snapshot.get("env_blockers")) or _as_list(release.get("env_blockers"))
    coverage_gaps = _as_list(snapshot.get("coverage_gaps")) or _as_list(release.get("coverage_gaps"))

    payment_env_blocked = False
    for blocker in env_blockers:
        text = blocker if isinstance(blocker, str) else json.dumps(blocker, ensure_ascii=False)
        if _contains_any(text, ("stripe", "webhook", "secret", "signature")):
            payment_env_blocked = True
            break
    if not payment_env_blocked:
        for suite, reason in blocked_suite_map.items():
            if suite.endswith("test_payment_api.py") and _contains_any(reason, ("stripe", "secret", "signature", "env")):
                payment_env_blocked = True
                break

    search_known_defect_impact = False
    for family in active_families:
        row = _as_dict(family)
        fid = str(row.get("family_id", ""))
        title = str(row.get("title", ""))
        impact = str(row.get("release_impact", ""))
        if fid == "DF-STORE-NEGATIVE-500" or (
            _contains_any(title, ("store", "lookup", "negative")) and _contains_any(impact, ("release", "critical"))
        ):
            search_known_defect_impact = True
            break

    missing_merchant_slots: list[str] = []
    for row_any in _as_list(merchant_seeds.get("results")):
        row = _as_dict(row_any)
        source = str(row.get("source", "")).lower()
        order_id = row.get("orderId")
        if source == "missing" or order_id is None:
            slot = str(row.get("slot", "")).strip()
            if slot:
                missing_merchant_slots.append(slot)

    lifecycle_seed_available = isinstance(lifecycle_seed.get("order_id"), int)

    return {
        "generated_at_utc": _now_utc(),
        "decision": decision,
        "score": score,
        "confidence": confidence,
        "top_risk": top_risk,
        "active_families": active_families,
        "blocked_suite_map": blocked_suite_map,
        "suppressions": suppressions,
        "env_blockers": env_blockers,
        "coverage_gaps": coverage_gaps,
        "payment_env_blocked": payment_env_blocked,
        "search_known_defect_impact": search_known_defect_impact,
        "missing_merchant_slots": missing_merchant_slots,
        "lifecycle_seed_available": lifecycle_seed_available,
        "release_artifact": release,
        "snapshot_artifact": snapshot,
        "rerun_artifact": rerun,
        "bootstrap_state": bool(
            not release
            or not EVIDENCE_CTX.artifact_exists("release_decision")
            or str(release.get("decision", "")).strip().lower() == "insufficient_evidence"
        ),
    }


def _ordered_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


def _flow_sequence(flow_ids: set[str]) -> list[str]:
    ordered: list[str] = []
    for flow_id in FLOW_ORDER:
        if flow_id in flow_ids:
            ordered.append(flow_id)
    for flow_id in sorted(flow_ids):
        if flow_id not in ordered:
            ordered.append(flow_id)
    return ordered


def _build_flow_selection(intent: str, mode: str, ctx: dict[str, Any]) -> tuple[list[str], dict[str, str]]:
    selected: set[str] = set(INTENT_FLOW_BASE.get(intent, ()))
    reasons: dict[str, str] = {}

    def add_flow(flow_id: str, reason: str) -> None:
        if flow_id not in FLOW_MODEL:
            return
        selected.add(flow_id)
        reasons.setdefault(flow_id, reason)

    if intent == "full_app_fast_regression":
        if ctx.get("bootstrap_state"):
            for flow_id in CORE_ANCHOR_FLOWS:
                add_flow(flow_id, "Bootstrap adapter evidence: collecting baseline confidence anchors.")
            ordered_bootstrap = _flow_sequence(selected)
            return ordered_bootstrap, reasons
        for flow_id in CORE_ANCHOR_FLOWS:
            add_flow(flow_id, "Core confidence anchor.")
        mapped_risk_flow = _flow_for_risk_text(ctx["top_risk"])
        if mapped_risk_flow:
            add_flow(mapped_risk_flow, f"Top active risk flow: {ctx['top_risk']}.")
        if ctx["search_known_defect_impact"]:
            add_flow("search_discovery", "Known release-impacting store/search defect family present.")
        if mode in {"balanced", "deep"}:
            add_flow("merchant_handling", "Balanced/deep mode includes merchant active-path validation.")
            if not ctx["payment_env_blocked"] or mode == "deep":
                add_flow("payment_integrity", "Balanced/deep mode includes payment integrity flow.")
        if mode == "deep":
            for flow_id in FLOW_MODEL:
                add_flow(flow_id, "Deep mode includes all product flows.")
    elif intent == "release_gate_regression":
        for flow_id in CORE_ANCHOR_FLOWS:
            add_flow(flow_id, "Release-gate baseline anchor.")
        mapped_risk_flow = _flow_for_risk_text(ctx["top_risk"])
        if mapped_risk_flow:
            add_flow(mapped_risk_flow, f"Top risk flow targeted for gate refresh: {ctx['top_risk']}.")
        if mode in {"balanced", "deep"}:
            add_flow("search_discovery", "Balanced/deep release-gate includes discovery risk coverage.")
            add_flow("merchant_handling", "Balanced/deep release-gate includes merchant risk flow.")
            if not ctx["payment_env_blocked"] or mode == "deep":
                add_flow("payment_integrity", "Payment added for release-gate depth.")
        if mode == "deep":
            for flow_id in FLOW_MODEL:
                add_flow(flow_id, "Deep mode includes all product flows.")
    else:
        for flow_id in CORE_ANCHOR_FLOWS:
            if flow_id in selected:
                reasons.setdefault(flow_id, "Requested intent baseline.")
        if mode in {"balanced", "deep"}:
            for flow_id in CORE_ANCHOR_FLOWS:
                add_flow(flow_id, "Balanced/deep mode adds core anchors.")
            mapped_risk_flow = _flow_for_risk_text(ctx["top_risk"])
            if mapped_risk_flow:
                add_flow(mapped_risk_flow, f"Top active risk included: {ctx['top_risk']}.")
        if mode == "deep":
            for flow_id in FLOW_MODEL:
                add_flow(flow_id, "Deep mode includes all product flows.")

    # Intent-specific hard includes.
    if intent == "payment_regression" and mode != "fast":
        add_flow("order_core", "Payment verification depends on order core continuity.")
    if intent == "merchant_flow_regression":
        add_flow("order_core", "Merchant flow requires fresh order-state context.")
    if intent == "order_flow_regression":
        add_flow("auth_foundation", "Order flow anchored by auth contract.")

    ordered_flows = _flow_sequence(selected)
    return ordered_flows, reasons


def _suite_product_flow(suite: str) -> str | None:
    for flow in FLOW_MODEL.values():
        if suite in flow.suites:
            return flow.flow_id
    return None


def _suite_should_be_suppressed(
    suite: str,
    *,
    intent: str,
    mode: str,
    ctx: dict[str, Any],
    blocked_reason: str | None,
) -> tuple[bool, str]:
    # Keep payment out of fast plans if blocker is unchanged env-only and intent is not payment-specific.
    if suite.endswith("test_payment_api.py") and ctx["payment_env_blocked"]:
        if intent != "payment_regression" and mode in {"fast", "balanced"}:
            return True, "Suppressed: unchanged Stripe env blocker limits new signal in this mode."

    # Deprioritize known unchanged search/store defect reruns unless explicitly targeted.
    if suite.endswith("test_search_store_api.py") and blocked_reason:
        if _contains_any(blocked_reason, ("unchanged", "deprioritized", "duplicate churn")):
            if intent not in {"search_store_regression", "release_gate_regression"} and mode == "fast":
                return True, "Suppressed: known unchanged store defect family with low new-signal value."

    return False, ""


def _build_suite_plan(
    selected_flow_ids: list[str],
    *,
    intent: str,
    mode: str,
    ctx: dict[str, Any],
) -> dict[str, Any]:
    candidate_suites: list[str] = []
    for flow_id in selected_flow_ids:
        candidate_suites.extend(FLOW_MODEL[flow_id].suites)
    candidate_suites = _ordered_unique(candidate_suites)

    selected_suites: list[str] = []
    suppressed_suites: list[dict[str, Any]] = []
    blocked_suites: list[dict[str, Any]] = []
    powershell_commands: list[str] = []

    blocked_map: dict[str, str] = ctx["blocked_suite_map"]
    missing_slots: list[str] = ctx["missing_merchant_slots"]

    for suite in candidate_suites:
        blocked_reason = blocked_map.get(suite)
        suppress, suppress_reason = _suite_should_be_suppressed(
            suite,
            intent=intent,
            mode=mode,
            ctx=ctx,
            blocked_reason=blocked_reason,
        )
        if suppress:
            suppressed_suites.append(
                {
                    "suite": suite,
                    "reason": suppress_reason,
                    "flow_id": _suite_product_flow(suite),
                }
            )
            continue

        if blocked_reason and _contains_any(blocked_reason, ("stripe", "secret", "signature", "env blocker")):
            blocked_suites.append(
                {
                    "suite": suite,
                    "reason": blocked_reason,
                    "flow_id": _suite_product_flow(suite),
                    "blocked_type": "env_blocker",
                }
            )
            continue

        if suite.endswith("test_merchant_transition_api.py") and missing_slots:
            # Keep merchant suite runnable for partial signal, but record blocker detail.
            blocked_suites.append(
                {
                    "suite": suite,
                    "reason": f"Partial seed blocker: {', '.join(missing_slots)}",
                    "flow_id": _suite_product_flow(suite),
                    "blocked_type": "seed_blocker_partial",
                }
            )

        selected_suites.append(suite)
        powershell_commands.append(f"python -m pytest -q -rs {suite}")

    return {
        "selected_suites": selected_suites,
        "suppressed_suites": suppressed_suites,
        "blocked_suites": blocked_suites,
        "powershell_commands": powershell_commands,
    }


def _risk_partition(selected_flow_ids: list[str], ctx: dict[str, Any]) -> tuple[list[str], list[str]]:
    included: list[str] = []
    deferred: list[str] = []
    flow_set = set(selected_flow_ids)

    for raw in ctx["active_families"]:
        family = _as_dict(raw)
        family_id = str(family.get("family_id", "unknown"))
        title = str(family.get("title", "N/A"))
        risk_text = f"{family_id}: {title}"

        mapped_flow = ADAPTER.infer_family_flow(family_id, title)

        if mapped_flow and mapped_flow in flow_set:
            included.append(risk_text)
        else:
            deferred.append(risk_text)

    return included, deferred


def _expected_release_impact(intent: str, mode: str, selected_flows: list[str], ctx: dict[str, Any]) -> str:
    if intent == "full_app_fast_regression":
        return (
            "High-signal fast pack for current product state: validates core anchors and current top-risk flow "
            "while suppressing low-signal blocked reruns."
        )
    if intent == "merchant_flow_regression":
        return "Merchant workflow confidence refresh with core context anchors."
    if intent == "order_flow_regression":
        return "Order lifecycle and contract confidence refresh."
    if intent == "search_store_regression":
        return "Discovery funnel and store-contract confidence refresh."
    if intent == "payment_regression":
        if ctx["payment_env_blocked"]:
            return "Payment regression intent is blocker-limited; expected signal focuses on non-blocked payment paths."
        return "Payment integrity confidence refresh across init/verify/retry paths."
    if intent == "release_gate_regression":
        return "Release-gate oriented evidence refresh for top risks and core product stability."
    return f"{mode.capitalize()} regression impact over selected flows: {', '.join(selected_flows)}."


def _build_plan(intent: str, mode: str) -> dict[str, Any]:
    ctx = _infer_context()
    selected_flow_ids, flow_reason_map = _build_flow_selection(intent, mode, ctx)
    suite_plan = _build_suite_plan(selected_flow_ids, intent=intent, mode=mode, ctx=ctx)
    known_included, known_deferred = _risk_partition(selected_flow_ids, ctx)

    selected_flows = [
        {
            "flow_id": flow_id,
            "title": FLOW_MODEL[flow_id].title,
            "description": FLOW_MODEL[flow_id].description,
            "suites": list(FLOW_MODEL[flow_id].suites),
            "selection_reason": flow_reason_map.get(flow_id, "Selected by intent/mode mapping."),
        }
        for flow_id in selected_flow_ids
    ]

    return {
        "generated_at_utc": ctx["generated_at_utc"],
        "intent": intent,
        "mode": mode,
        "selected_flows": selected_flows,
        "selected_suites": suite_plan["selected_suites"],
        "suppressed_suites": suite_plan["suppressed_suites"],
        "blocked_suites": suite_plan["blocked_suites"],
        "powershell_commands": suite_plan["powershell_commands"],
        "expected_release_impact": _expected_release_impact(intent, mode, selected_flow_ids, ctx),
        "known_risks_included": known_included,
        "known_risks_deferred": known_deferred,
        "release_context": {
            "decision": ctx["decision"],
            "confidence": ctx["confidence"],
            "score": ctx["score"],
            "top_risk": ctx["top_risk"],
        },
        "artifacts_used": [
            str(EVIDENCE_CTX.get_release_decision_path()),
            str(EVIDENCE_CTX.get_dashboard_snapshot_path()),
            str(EVIDENCE_CTX.get_defect_cluster_report_path()),
            str(EVIDENCE_CTX.get_rerun_plan_path()),
            str(ARTIFACT_MERCHANT_SEEDS),
            str(ARTIFACT_LIFECYCLE_SEED),
        ],
        "execution_mode": "plan_only",
        "adapter": {
            "adapter_id": ADAPTER_ID,
            "product_name": ADAPTER_PRODUCT,
        },
        "bootstrap_state": ctx.get("bootstrap_state", False),
    }


def _run_commands(commands: list[str]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for command in commands:
        started = time.perf_counter()
        completed = subprocess.run(
            command,
            shell=True,
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        elapsed = round(time.perf_counter() - started, 2)
        stdout_tail = "\n".join(completed.stdout.splitlines()[-25:])
        stderr_tail = "\n".join(completed.stderr.splitlines()[-25:])
        results.append(
            {
                "command": command,
                "exit_code": completed.returncode,
                "duration_seconds": elapsed,
                "stdout_tail": stdout_tail,
                "stderr_tail": stderr_tail,
            }
        )
    return results


def _render_report(plan: dict[str, Any]) -> str:
    lines: list[str] = [
        "# AI_REGRESSION_ORCHESTRATOR_REPORT",
        "",
        "## Requested Regression Intent",
        "",
        f"- Adapter: `{ADAPTER_ID}` ({ADAPTER_PRODUCT})",
        f"- Intent: `{plan['intent']}`",
        f"- Mode: `{plan['mode']}`",
        f"- Generated at: `{plan['generated_at_utc']}`",
        "",
        "## Selected Product Flows",
        "",
    ]

    for flow in plan["selected_flows"]:
        lines.append(f"- `{flow['title']}` (`{flow['flow_id']}`)")
        lines.append(f"  - Why: {flow['selection_reason']}")
        lines.append(f"  - Suites: {', '.join(flow['suites'])}")
    if not plan["selected_flows"]:
        lines.append("- none")
    lines.append("")

    lines.extend(
        [
            "## Selected Suites And Why",
            "",
        ]
    )
    if plan["selected_suites"]:
        for suite in plan["selected_suites"]:
            flow_id = _suite_product_flow(suite) or "unknown"
            flow_title = FLOW_MODEL[flow_id].title if flow_id in FLOW_MODEL else "Unknown flow"
            lines.append(f"- `{suite}` ({flow_title})")
    else:
        lines.append("- none")
    lines.append("")

    lines.extend(
        [
            "## Suppressed Suites And Why",
            "",
        ]
    )
    if plan["suppressed_suites"]:
        for item in plan["suppressed_suites"]:
            lines.append(f"- `{item['suite']}`: {item['reason']}")
    else:
        lines.append("- none")
    lines.append("")

    lines.extend(
        [
            "## Blocked Suites And Why",
            "",
        ]
    )
    if plan["blocked_suites"]:
        for item in plan["blocked_suites"]:
            lines.append(f"- `{item['suite']}`: {item['reason']}")
    else:
        lines.append("- none")
    lines.append("")

    lines.extend(
        [
            "## Runnable Commands",
            "",
        ]
    )
    if plan["powershell_commands"]:
        for cmd in plan["powershell_commands"]:
            lines.append(f"- `{cmd}`")
    else:
        lines.append("- none")
    lines.append("")

    lines.extend(
        [
            "## Expected Release Confidence Impact",
            "",
            f"- {plan['expected_release_impact']}",
            "",
            "## Known Unresolved Risks After This Regression",
            "",
            "- Included in this pack:",
        ]
    )
    included = plan["known_risks_included"]
    deferred = plan["known_risks_deferred"]
    if included:
        lines.extend([f"  - {risk}" for risk in included])
    else:
        lines.append("  - none")

    lines.append("- Deferred from this pack:")
    if deferred:
        lines.extend([f"  - {risk}" for risk in deferred])
    else:
        lines.append("  - none")
    lines.append("")

    lines.extend(
        [
            "## Recommended Next Action After Run",
            "",
        ]
    )
    if plan["execution_mode"] == "executed":
        lines.append("- Recompute release decision and dashboard snapshot using fresh rerun evidence.")
    else:
        lines.append("- Execute planned suites, then rerun release gate and dashboard refresh.")
    lines.append("")

    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Regression Orchestrator v1")
    parser.add_argument(
        "--intent",
        choices=INTENT_CHOICES,
        default=ADAPTER.get_default_intent(),
        help="Regression intent to orchestrate.",
    )
    parser.add_argument(
        "--mode",
        choices=MODE_CHOICES,
        default=ADAPTER.get_default_mode(),
        help="Execution mode: fast, balanced, or deep.",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Execute selected suites sequentially. Default is plan-only.",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Force plan-only behavior (default).",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    execute = bool(args.execute and not args.print_only)

    plan = _build_plan(args.intent, args.mode)
    if execute:
        execution_results = _run_commands(plan["powershell_commands"])
        plan["execution_mode"] = "executed"
        plan["execution_results"] = execution_results
        plan["execution_summary"] = {
            "total": len(execution_results),
            "passed": sum(1 for item in execution_results if item["exit_code"] == 0),
            "failed": sum(1 for item in execution_results if item["exit_code"] != 0),
        }

    output_plan = EVIDENCE_CTX.write_json("regression_execution_plan", plan)
    output_report = EVIDENCE_CTX.write_report("AI_REGRESSION_ORCHESTRATOR_REPORT.md", _render_report(plan))

    print(
        f"[ai-regression-orchestrator-v1] intent={plan['intent']} mode={plan['mode']} "
        f"selected_suites={len(plan['selected_suites'])} suppressed={len(plan['suppressed_suites'])} "
        f"blocked={len(plan['blocked_suites'])} execute={execute}"
    )
    print(f"[ai-regression-orchestrator-v1] plan={output_plan}")
    print(f"[ai-regression-orchestrator-v1] report={output_report}")
    if plan["powershell_commands"]:
        print("[ai-regression-orchestrator-v1] runnable commands:")
        for cmd in plan["powershell_commands"]:
            print(f"  - {cmd}")
    else:
        print("[ai-regression-orchestrator-v1] no runnable commands selected.")


if __name__ == "__main__":
    main()
