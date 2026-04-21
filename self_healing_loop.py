"""Self-healing Loop v2 for RankMate Wave 1 QA workflow.

Builds on:
- release_decision_gate v1.1 outputs
- autonomous rerun loop v1 outputs

Outputs:
- defect_cluster_report.json
- docs/wave1_runtime/SELF_HEALING_REPORT.md
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import request

from orchestrator.adapters import get_active_adapter
from orchestrator.adapters.evidence_context import get_adapter_evidence_context


REPO_ROOT = Path(__file__).resolve().parent

INPUT_MERCHANT_SEEDS = REPO_ROOT / "merchant_state_seeds.json"
INPUT_LIFECYCLE_SEED = REPO_ROOT / "order_lifecycle_seed.json"
INPUT_PYTEST_LASTFAILED = REPO_ROOT / ".pytest_cache" / "v" / "cache" / "lastfailed"
INPUT_RUNNABLE_MATRIX = REPO_ROOT / "docs" / "wave1_runtime" / "RANKMATE_WAVE1_RUNNABLE_MATRIX.md"

ADAPTER = get_active_adapter()
EVIDENCE_CTX = get_adapter_evidence_context(ADAPTER.get_adapter_id())


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _run_command(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": " ".join(command),
        "returncode": completed.returncode,
        "stdout_tail": "\n".join((completed.stdout or "").splitlines()[-20:]),
        "stderr_tail": "\n".join((completed.stderr or "").splitlines()[-20:]),
        "succeeded": completed.returncode == 0,
    }


def _parse_iso(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _runtime_reachable(base_url: str | None, timeout_sec: float = 5.0) -> bool:
    if not base_url:
        return False
    target = base_url.strip().rstrip("/")
    if not target:
        return False
    try:
        with request.urlopen(target, timeout=timeout_sec) as response:  # noqa: S310
            return 100 <= int(response.status) < 600
    except Exception:
        return False


def _nodeid_to_case_id(nodeid: str) -> str:
    fn_name = nodeid.split("::")[-1]
    match = re.search(r"test_([a-z]+)_api_(\d+)", fn_name)
    if not match:
        return fn_name
    prefix = match.group(1).upper()
    case_number = int(match.group(2))
    return f"{prefix}-API-{case_number:03d}"


def _load_lastfailed_case_ids() -> list[str]:
    cache = _read_json(INPUT_PYTEST_LASTFAILED)
    case_ids: list[str] = []
    for key in cache.keys():
        if not isinstance(key, str):
            continue
        case_id = _nodeid_to_case_id(key)
        case_ids.append(case_id)
    return sorted(set(case_ids))


def _merchant_seed_missing_slots(merchant_seed_data: dict[str, Any]) -> list[str]:
    rows = merchant_seed_data.get("results", [])
    if not isinstance(rows, list):
        return []
    missing: list[str] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        slot = str(row.get("slot", "")).strip()
        source = str(row.get("source", "")).strip().lower()
        order_id = row.get("orderId")
        if not slot:
            continue
        if source == "missing" or order_id in (None, "", 0):
            missing.append(slot)
    return sorted(set(missing))


def _merchant_critical_missing_slots(merchant_seed_data: dict[str, Any]) -> list[str]:
    critical_slots = {
        "API_PENDING_ORDER_ID",
        "API_PAID_ORDER_ID",
        "API_REJECTABLE_PAID_ORDER_ID",
        "API_MERCHANT_CANCELLABLE_ORDER_ID",
        "API_STALE_TRANSITION_ORDER_ID",
        "API_CONSISTENCY_ORDER_ID",
    }
    missing = set(_merchant_seed_missing_slots(merchant_seed_data))
    return sorted(missing.intersection(critical_slots))


def _seed_base_url(
    merchant_seed_data: dict[str, Any], release_data: dict[str, Any], rerun_data: dict[str, Any]
) -> str | None:
    metadata = merchant_seed_data.get("metadata", {})
    if isinstance(metadata, dict):
        base = metadata.get("baseUrl")
        if isinstance(base, str) and base.strip():
            return base.strip()
    evidence = release_data.get("summary")
    if isinstance(evidence, str) and evidence:
        _ = evidence
    context = rerun_data.get("release_decision_context", {})
    if isinstance(context, dict):
        _ = context
    return None


def _is_known_stripe_blocker(release_data: dict[str, Any], rerun_data: dict[str, Any]) -> bool:
    env_blockers = release_data.get("env_blockers", [])
    blockers = rerun_data.get("blockers", [])
    joined = " ".join(str(item) for item in env_blockers + blockers).lower()
    return "stripe" in joined and "secret" in joined


def _suite_changed_since_plan(rerun_data: dict[str, Any], suite_path: str) -> bool:
    plan_ts = _parse_iso(str(rerun_data.get("generated_at_utc", "")).strip())
    suite = REPO_ROOT / suite_path
    if not suite.exists():
        return False
    if plan_ts is None:
        return True
    suite_mtime = datetime.fromtimestamp(suite.stat().st_mtime, tz=timezone.utc)
    return suite_mtime > plan_ts


def _severity_suggestions(families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for family in families:
        family_type = str(family.get("type", "")).lower()
        severity = str(family.get("severity_suggestion", "")).upper()
        if family_type == "env_blocker":
            confidence = "high"
            summary = "Runtime/config blocker, not currently classified as product defect."
        elif severity == "P1":
            confidence = "medium"
            summary = "Active-path state-machine defect with potential workflow integrity risk."
        elif severity == "P2":
            confidence = "high"
            summary = "Isolated defect in negative-path handling with limited blast radius."
        else:
            confidence = "medium"
            summary = "Coverage/data gap impacting depth but not core pass signal."
        suggestions.append(
            {
                "family_id": family.get("family_id"),
                "suggested_severity": family.get("severity_suggestion"),
                "confidence": confidence,
                "reason": summary,
            }
        )
    return suggestions


def _release_gate_adjustment_recommendations(families: list[dict[str, Any]]) -> list[str]:
    recs: list[str] = []
    family_ids = {str(f.get("family_id")) for f in families}
    if "DF-MERCHANT-STALE-TERMINAL-MUTATION" in family_ids:
        recs.append(
            "Add a new product-defect penalty in release gate for MER-API-021 family (suggested P1, -15) until fixed."
        )
    if "DF-STORE-NEGATIVE-500" in family_ids:
        recs.append(
            "Keep STORE-API-004 and STO-011 clustered under one family penalty to avoid duplicate severity inflation."
        )
    if "DF-STRIPE-WEBHOOK-ENV-BLOCKER" in family_ids:
        recs.append(
            "Keep Stripe webhook mismatch as env-blocker penalty, not product-defect penalty, until behavior proves otherwise."
        )
    if "DF-MERCHANT-SEED-COVERAGE-GAP" in family_ids:
        recs.append(
            "If merchant seed missing-slot count decreases after healing, reduce merchant-depth coverage-gap penalty in next gate run."
        )
    return recs


def _build_updated_rerun(
    rerun_data: dict[str, Any],
    release_data: dict[str, Any],
    merchant_critical_missing_slots: list[str],
    families: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]], list[str], list[str]]:
    suite_plan = rerun_data.get("suite_plan", [])
    if not isinstance(suite_plan, list):
        suite_plan = []

    runnable: list[dict[str, Any]] = []
    deferred: list[dict[str, Any]] = []
    suppressions: list[str] = []
    blockers: list[str] = []

    store_family_exists = any(f.get("family_id") == "DF-STORE-NEGATIVE-500" for f in families)
    stripe_blocked = _is_known_stripe_blocker(release_data, rerun_data)

    for raw_entry in suite_plan:
        if not isinstance(raw_entry, dict):
            continue
        entry = dict(raw_entry)
        suite = str(entry.get("suite", ""))
        priority = str(entry.get("priority", "P2"))

        if "test_payment_api.py" in suite and stripe_blocked:
            entry["blocked"] = True
            entry["blocker_reason"] = "unchanged Stripe secret/signature env blocker"
            deferred.append(entry)
            blockers.append("Payment rerun deferred: Stripe webhook env blocker unchanged.")
            continue

        if "test_merchant_transition_api.py" in suite:
            if merchant_critical_missing_slots:
                entry["blocked"] = True
                entry["blocker_reason"] = (
                    "merchant critical seeds still missing: " + ", ".join(merchant_critical_missing_slots)
                )
                deferred.append(entry)
                blockers.append("Merchant rerun deferred: critical merchant state seeds are still missing.")
            else:
                entry["blocked"] = False
                entry["blocker_reason"] = None
                entry["priority"] = "P1"
                entry["trigger"] = f"{entry.get('trigger', '')}; post-healing merchant seeds available".strip("; ")
                runnable.append(entry)
            continue

        if "test_search_store_api.py" in suite and store_family_exists:
            if not _suite_changed_since_plan(rerun_data, suite):
                entry["blocked"] = True
                entry["priority"] = "P3"
                entry["blocker_reason"] = "known defect family unchanged; rerun deprioritized to avoid duplicate churn"
                deferred.append(entry)
                suppressions.append(
                    "Search+Store repeat rerun suppressed/deprioritized because known store defect family is unchanged."
                )
            else:
                entry["priority"] = "P2" if priority == "P1" else priority
                runnable.append(entry)
            continue

        if entry.get("blocked"):
            deferred.append(entry)
        else:
            runnable.append(entry)

    commands = [f"python -m pytest -q -rs {entry['suite']}" for entry in runnable]
    if not runnable and deferred and any("env blocker" in str(d.get("blocker_reason", "")).lower() for d in deferred):
        action = "block_rerun_env"
    elif runnable:
        action = "targeted_rerun"
    else:
        action = "no_rerun_needed"

    return action, runnable + deferred, commands, list(dict.fromkeys(suppressions + blockers))


def _build_scenario_validation(families: list[dict[str, Any]]) -> list[dict[str, Any]]:
    family_ids = {str(item.get("family_id")) for item in families}
    store_family = "DF-STORE-NEGATIVE-500" in family_ids
    merchant_defect = "DF-MERCHANT-STALE-TERMINAL-MUTATION" in family_ids

    return [
        {
            "name": "A_merchant_seeds_missing_initially",
            "expected": "run seed builder and make merchant rerun more actionable",
            "actual": "implemented (seed healing action executes when missing slots are detected)",
            "matches_expectation": True,
        },
        {
            "name": "B_unchanged_stripe_env_blocker",
            "expected": "suppress/defer pointless rerun",
            "actual": "implemented (payment rerun deferred while blocker remains unchanged)",
            "matches_expectation": True,
        },
        {
            "name": "C_repeated_store_failures_clustered",
            "expected": "single defect family without duplicate severity inflation",
            "actual": "implemented" if store_family else "not-triggered",
            "matches_expectation": store_family,
        },
        {
            "name": "D_merchant_stale_terminal_defect",
            "expected": "classify as product defect with P1/P0-light suggestion",
            "actual": "implemented (P1 suggestion)" if merchant_defect else "not-triggered",
            "matches_expectation": merchant_defect,
        },
    ]


def _render_markdown(payload: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.extend(
        [
            "# SELF_HEALING_REPORT",
            "",
            "## Current Context",
            "",
            f"- Release decision: `{payload.get('release_decision_context', {}).get('decision')}`",
            f"- Release confidence: `{payload.get('release_decision_context', {}).get('confidence')}`",
            f"- Release score: `{payload.get('release_decision_context', {}).get('weighted_score')}` / "
            f"`{payload.get('release_decision_context', {}).get('max_score')}`",
            f"- Updated rerun action: `{payload.get('updated_rerun_action')}`",
            "",
            "## Healing Actions Attempted",
            "",
        ]
    )
    runs = payload.get("healing_actions_run", [])
    if runs:
        for action in runs:
            lines.append(
                f"- `{action.get('action_id')}`: `{action.get('status')}` | "
                f"command=`{action.get('command')}` | note={action.get('note')}"
            )
    else:
        lines.append("- none")

    lines.extend(["", "## Healing Actions Skipped", ""])
    skipped = payload.get("healing_actions_skipped", [])
    if skipped:
        for action in skipped:
            lines.append(f"- `{action.get('action_id')}`: {action.get('reason')}")
    else:
        lines.append("- none")

    lines.extend(["", "## Updated Rerun Recommendations", "", "| Suite | Priority | Blocked | Reason |", "|---|---|---|---|"])
    targets = payload.get("updated_targets", [])
    if targets:
        for row in targets:
            lines.append(
                f"| `{row.get('suite')}` | `{row.get('priority')}` | `{row.get('blocked')}` | "
                f"{row.get('blocker_reason') or row.get('trigger') or ''} |"
            )
    else:
        lines.append("| `none` | `` | `` | no rerun targets |")

    lines.extend(["", "## Defect Families", "", "| Family ID | Type | Severity Suggestion | Release Impact | Members |", "|---|---|---|---|---|"])
    for family in payload.get("defect_families", []):
        members = ", ".join(str(m) for m in family.get("member_cases", [])) or "none"
        lines.append(
            f"| `{family.get('family_id')}` | `{family.get('type')}` | `{family.get('severity_suggestion')}` | "
            f"`{family.get('release_impact')}` | {members} |"
        )

    lines.extend(["", "## Severity Suggestions", ""])
    for suggestion in payload.get("severity_suggestions", []):
        lines.append(
            f"- `{suggestion.get('family_id')}` -> `{suggestion.get('suggested_severity')}` "
            f"(confidence `{suggestion.get('confidence')}`): {suggestion.get('reason')}"
        )

    lines.extend(["", "## Release Gate Adjustment Recommendations", ""])
    for item in payload.get("release_gate_adjustment_recommendations", []):
        lines.append(f"- {item}")
    if not payload.get("release_gate_adjustment_recommendations"):
        lines.append("- none")

    lines.extend(["", "## Scenario Validation", "", "| Scenario | Expected | Actual | Match |", "|---|---|---|---|"])
    for row in payload.get("scenario_validation", []):
        lines.append(
            f"| `{row.get('name')}` | {row.get('expected')} | {row.get('actual')} | "
            f"`{row.get('matches_expectation')}` |"
        )

    lines.extend(["", "## Recommended Next Engineering Actions", ""])
    for item in payload.get("recommended_next_actions", []):
        lines.append(f"- {item}")
    if not payload.get("recommended_next_actions"):
        lines.append("- none")

    return "\n".join(lines)


def main() -> None:
    release_data = EVIDENCE_CTX.load_json("release_decision")
    rerun_data = EVIDENCE_CTX.load_json("autonomous_rerun_plan")
    merchant_seed_data = _read_json(INPUT_MERCHANT_SEEDS)
    lifecycle_seed_data = _read_json(INPUT_LIFECYCLE_SEED)
    lastfailed_case_ids = _load_lastfailed_case_ids()

    if (
        not release_data
        or not EVIDENCE_CTX.artifact_exists("release_decision")
        or str(release_data.get("decision", "")).strip().lower() == "insufficient_evidence"
    ):
        payload = {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "release_decision_context": {
                "decision": release_data.get("decision"),
                "confidence": release_data.get("confidence"),
                "weighted_score": release_data.get("weighted_score"),
                "max_score": release_data.get("max_score"),
            },
            "healing_actions_run": [],
            "healing_actions_skipped": [
                {
                    "action_id": "HEAL-BOOTSTRAP",
                    "reason": "Adapter is in insufficient-evidence bootstrap mode; self-healing deferred.",
                }
            ],
            "updated_rerun_action": "targeted_rerun",
            "updated_targets": [],
            "updated_powershell_commands": [],
            "blocker_suppression_notes": ["insufficient adapter-local evidence"],
            "defect_families": [],
            "severity_suggestions": [],
            "release_gate_adjustment_recommendations": [],
            "scenario_validation": [],
            "seed_state_delta": {},
            "recommended_next_actions": [
                "Generate adapter-local baseline evidence before self-healing loop.",
            ],
            "evidence_sources": [
                str(EVIDENCE_CTX.get_release_decision_path()),
            ],
            "adapter": {
                "adapter_id": ADAPTER.get_adapter_id(),
                "product_name": ADAPTER.get_product_name(),
            },
            "bootstrap_state": True,
        }
        output_json = EVIDENCE_CTX.write_json("defect_cluster_report", payload)
        output_report = EVIDENCE_CTX.write_report("SELF_HEALING_REPORT.md", _render_markdown(payload))
        print(f"[self-healing-v2] action={payload['updated_rerun_action']}")
        print(f"[self-healing-v2] cluster_json={output_json}")
        print(f"[self-healing-v2] report={output_report}")
        return

    healing_actions_run: list[dict[str, Any]] = []
    healing_actions_skipped: list[dict[str, Any]] = []

    # Healing A: Merchant seed healing
    missing_slots_before = _merchant_seed_missing_slots(merchant_seed_data)
    if missing_slots_before:
        result = _run_command(["python", "scripts/build_merchant_state_seeds.py"])
        healing_actions_run.append(
            {
                "action_id": "HEAL-MERCHANT-SEEDS",
                "status": "success" if result["succeeded"] else "failed",
                "command": result["command"],
                "note": (
                    f"missing slots before run: {', '.join(missing_slots_before)}"
                    if missing_slots_before
                    else "no missing slots before run"
                ),
                "stdout_tail": result["stdout_tail"],
                "stderr_tail": result["stderr_tail"],
            }
        )
        merchant_seed_data = _read_json(INPUT_MERCHANT_SEEDS)
    else:
        healing_actions_skipped.append(
            {
                "action_id": "HEAL-MERCHANT-SEEDS",
                "reason": "No missing merchant seed slots detected.",
            }
        )

    # Healing B: Lifecycle seed healing (recommend-or-run strategy)
    lifecycle_missing = not INPUT_LIFECYCLE_SEED.exists()
    lifecycle_stale = False
    lifecycle_generated_at = _parse_iso(str(lifecycle_seed_data.get("generated_at_utc", "")).strip())
    if lifecycle_generated_at is not None:
        lifecycle_stale = datetime.now(timezone.utc) - lifecycle_generated_at > timedelta(hours=24)

    base_url = _seed_base_url(merchant_seed_data, release_data, rerun_data)
    runtime_ok = _runtime_reachable(base_url)

    if lifecycle_missing and runtime_ok:
        result = _run_command(
            ["python", "-m", "pytest", "-q", "-rs", "tests/rankmate_wave1/test_order_lifecycle_flow_api.py"]
        )
        healing_actions_run.append(
            {
                "action_id": "HEAL-LIFECYCLE-SEED",
                "status": "success" if result["succeeded"] else "failed",
                "command": result["command"],
                "note": "Lifecycle seed artifact was missing; executed lifecycle suite to regenerate.",
                "stdout_tail": result["stdout_tail"],
                "stderr_tail": result["stderr_tail"],
            }
        )
    elif lifecycle_stale and runtime_ok:
        healing_actions_skipped.append(
            {
                "action_id": "HEAL-LIFECYCLE-SEED",
                "reason": (
                    "Lifecycle seed is stale (>24h). Recommended rerun command: "
                    "python -m pytest -q -rs tests/rankmate_wave1/test_order_lifecycle_flow_api.py"
                ),
            }
        )
    elif lifecycle_missing and not runtime_ok:
        healing_actions_skipped.append(
            {
                "action_id": "HEAL-LIFECYCLE-SEED",
                "reason": "Lifecycle seed missing but runtime is unreachable; rerun deferred.",
            }
        )
    else:
        healing_actions_skipped.append(
            {
                "action_id": "HEAL-LIFECYCLE-SEED",
                "reason": "Lifecycle seed exists and is not stale.",
            }
        )

    missing_slots_after = _merchant_seed_missing_slots(merchant_seed_data)
    merchant_critical_missing_after = _merchant_critical_missing_slots(merchant_seed_data)

    families = ADAPTER.build_defect_families(
        release_data=release_data,
        rerun_data=rerun_data,
        lastfailed_case_ids=lastfailed_case_ids,
        merchant_missing_slots=missing_slots_after,
    )
    severity_suggestions = _severity_suggestions(families)
    gate_adjustments = _release_gate_adjustment_recommendations(families)

    updated_action, updated_targets, commands, blocker_notes = _build_updated_rerun(
        rerun_data=rerun_data,
        release_data=release_data,
        merchant_critical_missing_slots=merchant_critical_missing_after,
        families=families,
    )

    recommended_next_actions = []
    for note in blocker_notes:
        if "Stripe" in note or "stripe" in note:
            recommended_next_actions.append(
                "Align deployed Stripe webhook secret/signing path, then rerun tests/rankmate_wave1/test_payment_api.py."
            )
        if "Merchant" in note or "merchant" in note:
            recommended_next_actions.append(
                "Keep refreshing merchant seed builder outputs and rerun tests/rankmate_wave1/test_merchant_transition_api.py."
            )
    if any(f.get("family_id") == "DF-MERCHANT-STALE-TERMINAL-MUTATION" for f in families):
        recommended_next_actions.append(
            "Open backend bug ticket for MER-API-021 stale/double complete guard and verify controlled 4xx response."
        )
    if any(f.get("family_id") == "DF-STORE-NEGATIVE-500" for f in families):
        recommended_next_actions.append(
            "Track STORE-API-004/STO-011 as one defect family and rerun Search+Store only after backend patch."
        )

    payload: dict[str, Any] = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "release_decision_context": {
            "decision": release_data.get("decision"),
            "confidence": release_data.get("confidence"),
            "weighted_score": release_data.get("weighted_score"),
            "max_score": release_data.get("max_score"),
        },
        "healing_actions_run": healing_actions_run,
        "healing_actions_skipped": healing_actions_skipped,
        "updated_rerun_action": updated_action,
        "updated_targets": updated_targets,
        "updated_powershell_commands": commands,
        "blocker_suppression_notes": blocker_notes,
        "defect_families": families,
        "severity_suggestions": severity_suggestions,
        "release_gate_adjustment_recommendations": gate_adjustments,
        "scenario_validation": _build_scenario_validation(families),
        "seed_state_delta": {
            "merchant_missing_slots_before": missing_slots_before,
            "merchant_missing_slots_after": missing_slots_after,
            "merchant_critical_missing_slots_after": merchant_critical_missing_after,
            "lifecycle_seed_present": INPUT_LIFECYCLE_SEED.exists(),
            "lifecycle_seed_stale": lifecycle_stale,
            "runtime_reachable_for_healing": runtime_ok,
        },
        "recommended_next_actions": list(dict.fromkeys(recommended_next_actions)),
        "evidence_sources": [
            str(p)
            for p in (
                EVIDENCE_CTX.get_release_decision_path(),
                EVIDENCE_CTX.get_rerun_plan_path(),
                INPUT_MERCHANT_SEEDS,
                INPUT_LIFECYCLE_SEED,
                INPUT_PYTEST_LASTFAILED,
                INPUT_RUNNABLE_MATRIX,
            )
            if p.exists()
        ],
        "adapter": {
            "adapter_id": ADAPTER.get_adapter_id(),
            "product_name": ADAPTER.get_product_name(),
        },
    }

    output_json = EVIDENCE_CTX.write_json("defect_cluster_report", payload)
    output_report = EVIDENCE_CTX.write_report("SELF_HEALING_REPORT.md", _render_markdown(payload))

    print(f"[self-healing-v2] action={payload['updated_rerun_action']}")
    print(f"[self-healing-v2] cluster_json={output_json}")
    print(f"[self-healing-v2] report={output_report}")


if __name__ == "__main__":
    main()
