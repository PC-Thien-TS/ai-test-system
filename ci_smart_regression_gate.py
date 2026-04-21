"""CI/CD Native Smart Regression Gate v1.

Coordinates:
- adapter validation
- change-aware trigger
- regression orchestrator
- release gate refresh
- optional dashboard refresh
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from orchestrator.adapters import get_active_adapter
from orchestrator.adapters.evidence_context import get_adapter_evidence_context
from orchestrator.adapters.validator import validate_adapter


REPO_ROOT = Path(__file__).resolve().parent


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _run_command(command: list[str], env: dict[str, str], timeout_ms: int = 180000) -> dict[str, Any]:
    started = time.perf_counter()
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout_ms / 1000,
    )
    duration = round(time.perf_counter() - started, 2)
    return {
        "command": " ".join(command),
        "returncode": completed.returncode,
        "duration_seconds": duration,
        "stdout_tail": "\n".join((completed.stdout or "").splitlines()[-20:]),
        "stderr_tail": "\n".join((completed.stderr or "").splitlines()[-20:]),
        "succeeded": completed.returncode == 0,
    }


def _git_diff_files() -> list[str]:
    commands = [
        ["git", "diff", "--name-only", "HEAD~1..HEAD"],
        ["git", "diff", "--name-only", "HEAD"],
        ["git", "diff", "--name-only"],
    ]
    for command in commands:
        try:
            result = subprocess.run(
                command,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception:
            continue
        if result.returncode != 0:
            continue
        files = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
        if files:
            return files
    return []


def _infer_intent_and_mode(adapter: Any, selected_flow_ids: list[str]) -> tuple[str, str]:
    intent_choices = set(adapter.get_intent_choices())
    default_intent = adapter.get_default_intent()
    default_mode = adapter.get_default_mode()

    if not selected_flow_ids:
        return default_intent, default_mode

    flow_text = " ".join(selected_flow_ids).lower()
    if "merchant_flow_regression" in intent_choices and any(token in flow_text for token in ("merchant", "operator")):
        return "merchant_flow_regression", "balanced"
    if "payment_regression" in intent_choices and any(token in flow_text for token in ("payment", "billing")):
        return "payment_regression", "balanced"
    if "search_store_regression" in intent_choices and any(
        token in flow_text for token in ("search", "store", "catalog", "discovery", "workspace")
    ):
        return "search_store_regression", "balanced"
    if "order_flow_regression" in intent_choices and any(
        token in flow_text for token in ("order", "reservation", "checkout", "cart")
    ):
        return "order_flow_regression", "balanced"

    intent_flow_base = adapter.get_intent_flow_base()
    chosen_intent = default_intent
    best_score = -1.0
    selected_set = set(selected_flow_ids)
    for intent, mapped_tuple in intent_flow_base.items():
        mapped_set = set(mapped_tuple)
        if intent == "full_app_fast_regression":
            continue
        if not mapped_set:
            continue
        overlap = len(selected_set & mapped_set)
        if overlap == 0:
            continue
        score = overlap / len(mapped_set)
        if score > best_score:
            best_score = score
            chosen_intent = intent
    if chosen_intent != default_intent:
        return chosen_intent, "balanced"
    if len(selected_flow_ids) > 2:
        return default_intent, "balanced"
    return default_intent, default_mode


def _build_ci_gate_status(
    *,
    adapter_validation_status: str,
    release_decision: str,
    execution_status: str,
    has_critical_failure: bool,
) -> str:
    if adapter_validation_status == "fail":
        return "fail"
    if has_critical_failure:
        return "fail"
    if release_decision == "insufficient_evidence":
        return "warning"
    if release_decision == "block_release":
        return "fail"
    if (
        adapter_validation_status == "pass_with_warnings"
        or release_decision == "release_with_caution"
        or execution_status == "not_executed"
    ):
        return "warning"
    return "pass"


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# CI_SMART_REGRESSION_GATE_REPORT",
        "",
        "## Active Adapter",
        "",
        f"- Adapter: `{payload['adapter']}`",
        "",
        "## Adapter Validation",
        "",
        f"- Status: `{payload['adapter_validation_status']}`",
        f"- Warnings: `{len(payload.get('adapter_warnings', []))}`",
        f"- Errors: `{len(payload.get('adapter_errors', []))}`",
        "",
        "## Changed Files Analyzed",
        "",
    ]
    changed_files = payload.get("changed_files", [])
    if changed_files:
        for row in changed_files:
            lines.append(f"- `{row}`")
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Selected Regression Intent",
            "",
            f"- Intent: `{payload.get('selected_intent')}`",
            f"- Mode: `{payload.get('selected_mode')}`",
            "",
            "## Regression Plan Summary",
            "",
            f"- Plan status: `{payload.get('regression_plan_status')}`",
            f"- Selected suites: `{len(payload.get('selected_suites', []))}`",
            f"- Suppressed suites: `{len(payload.get('suppressed_suites', []))}`",
            f"- Blocked suites: `{len(payload.get('blocked_suites', []))}`",
            "",
            "## Execution",
            "",
            f"- Execution status: `{payload.get('execution_status')}`",
            f"- Execute requested: `{payload.get('execute_requested')}`",
            "",
            "## Updated Release Decision",
            "",
            f"- Decision: `{payload.get('release_decision')}`",
            f"- Score: `{payload.get('release_score')}`",
            f"- Confidence: `{payload.get('confidence')}`",
            "",
            "## Final CI Gate Status",
            "",
            f"- CI gate status: `{payload.get('ci_gate_status')}`",
            f"- Summary: {payload.get('summary')}",
            "",
            "## Recommended Next Actions",
            "",
        ]
    )
    for row in payload.get("next_actions", []):
        lines.append(f"- {row}")
    if not payload.get("next_actions"):
        lines.append("- none")

    lines.extend(["", "## Recommended Commands", ""])
    for row in payload.get("recommended_commands", []):
        lines.append(f"- `{row}`")
    if not payload.get("recommended_commands"):
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CI/CD Native Smart Regression Gate v1")
    parser.add_argument("--git-diff", action="store_true", help="Use git diff to infer changed files.")
    parser.add_argument("--files", default="", help="Comma-separated changed files.")
    parser.add_argument("--execute", action="store_true", help="Execute selected regression plan commands.")
    parser.add_argument("--adapter", default="", help="Override active adapter id.")
    parser.add_argument("--strict-adapter", action="store_true", help="Use strict adapter validation.")
    parser.add_argument("--skip-dashboard-refresh", action="store_true", help="Skip dashboard refresh step.")
    parser.add_argument("--json", action="store_true", help="Print final gate payload as JSON.")
    return parser.parse_args()


@contextmanager
def _adapter_env(adapter_name: str) -> Any:
    prev = os.getenv("AI_TESTING_ADAPTER")
    os.environ["AI_TESTING_ADAPTER"] = adapter_name
    try:
        yield
    finally:
        if prev is None:
            os.environ.pop("AI_TESTING_ADAPTER", None)
        else:
            os.environ["AI_TESTING_ADAPTER"] = prev


def main() -> None:
    args = _parse_args()

    initial_adapter = args.adapter.strip().lower()
    if initial_adapter:
        os.environ["AI_TESTING_ADAPTER"] = initial_adapter
    adapter = get_active_adapter()
    adapter_name = adapter.get_adapter_id()
    evidence_ctx = get_adapter_evidence_context(adapter_name)
    output_json_path = evidence_ctx.get_ci_gate_result_path()
    output_report_name = "CI_SMART_REGRESSION_GATE_REPORT.md"

    changed_files = [item.strip() for item in args.files.split(",") if item.strip()]
    if not changed_files and args.git_diff:
        changed_files = _git_diff_files()
    if not changed_files and not args.files:
        changed_files = _git_diff_files()

    validation = validate_adapter(
        adapter_name,
        strict=args.strict_adapter,
        ci=True,
        verbose=False,
    )
    validation_payload = validation.to_dict()
    evidence_ctx.write_json("adapter_validation_report", validation_payload)

    result: dict[str, Any] = {
        "generated_at_utc": _now_utc(),
        "adapter": adapter_name,
        "adapter_validation_status": validation_payload.get("status", "fail"),
        "adapter_warnings": validation_payload.get("warnings", []),
        "adapter_errors": validation_payload.get("errors", []),
        "changed_files": changed_files,
        "selected_intent": None,
        "selected_mode": None,
        "regression_plan_status": "not_started",
        "execution_status": "not_executed",
        "execute_requested": bool(args.execute),
        "release_decision": None,
        "release_score": None,
        "confidence": None,
        "ci_gate_status": "fail",
        "summary": "",
        "next_actions": [],
        "recommended_commands": [],
        "selected_suites": [],
        "suppressed_suites": [],
        "blocked_suites": [],
        "step_results": [],
    }

    has_critical_failure = False
    env = os.environ.copy()
    env["AI_TESTING_ADAPTER"] = adapter_name

    if validation_payload.get("status") == "fail":
        result["regression_plan_status"] = "skipped_due_adapter_validation_fail"
        result["summary"] = "Adapter validation failed. CI smart regression gate stopped early."
        result["next_actions"] = validation_payload.get("recommendations", [])
        result["ci_gate_status"] = "fail"
        evidence_ctx.write_json("ci_regression_gate_result", result)
        evidence_ctx.write_report(output_report_name, _render_markdown(result))
        print(f"[ci-gate] adapter={adapter_name} validation={result['adapter_validation_status']}")
        print("[ci-gate] status=fail")
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        raise SystemExit(1)

    change_cmd = [
        os.sys.executable,
        "ai_change_aware_regression_trigger.py",
        "--files",
        ",".join(changed_files),
    ]
    change_step = _run_command(change_cmd, env=env)
    result["step_results"].append({"step": "change_aware_trigger", **change_step})
    if not change_step["succeeded"]:
        has_critical_failure = True
        result["regression_plan_status"] = "failed_change_aware_trigger"

    change_payload = evidence_ctx.load_json("change_aware_regression_plan")
    selected_flows = change_payload.get("selected_flows", []) if isinstance(change_payload.get("selected_flows"), list) else []
    selected_flow_ids = [str(item.get("flow_id", "")).strip() for item in selected_flows if isinstance(item, dict)]
    selected_flow_ids = [item for item in selected_flow_ids if item]

    selected_intent, selected_mode = _infer_intent_and_mode(adapter, selected_flow_ids)
    result["selected_intent"] = selected_intent
    result["selected_mode"] = selected_mode

    orchestrator_cmd = [
        os.sys.executable,
        "ai_regression_orchestrator.py",
        "--intent",
        selected_intent,
        "--mode",
        selected_mode,
    ]
    if args.execute:
        orchestrator_cmd.append("--execute")
    orchestrator_step = _run_command(orchestrator_cmd, env=env, timeout_ms=600000)
    result["step_results"].append({"step": "regression_orchestrator", **orchestrator_step})
    if not orchestrator_step["succeeded"]:
        has_critical_failure = True
        result["regression_plan_status"] = "failed_orchestrator"
    else:
        result["regression_plan_status"] = "generated"

    plan_payload = evidence_ctx.load_json("regression_execution_plan")
    result["selected_suites"] = plan_payload.get("selected_suites", [])
    result["suppressed_suites"] = plan_payload.get("suppressed_suites", [])
    result["blocked_suites"] = plan_payload.get("blocked_suites", [])
    result["recommended_commands"] = plan_payload.get("powershell_commands", [])

    if args.execute:
        execution_summary = plan_payload.get("execution_summary", {})
        if isinstance(execution_summary, dict) and execution_summary.get("failed", 0):
            result["execution_status"] = "executed_with_failures"
            has_critical_failure = True
        elif plan_payload.get("execution_mode") == "executed":
            result["execution_status"] = "executed_success"
        else:
            result["execution_status"] = "execution_error"
            has_critical_failure = True
    else:
        result["execution_status"] = "not_executed"

    release_step = _run_command([os.sys.executable, "release_decision_gate.py"], env=env)
    result["step_results"].append({"step": "release_gate_refresh", **release_step})
    if not release_step["succeeded"]:
        has_critical_failure = True

    if not args.skip_dashboard_refresh:
        dashboard_step = _run_command([os.sys.executable, "ai_qa_lead_dashboard.py"], env=env)
        result["step_results"].append({"step": "dashboard_refresh", **dashboard_step})
        if not dashboard_step["succeeded"]:
            has_critical_failure = True

    release_payload = evidence_ctx.load_json("release_decision")
    result["release_decision"] = release_payload.get("decision")
    result["release_score"] = release_payload.get("weighted_score")
    result["confidence"] = release_payload.get("confidence")

    result["ci_gate_status"] = _build_ci_gate_status(
        adapter_validation_status=result["adapter_validation_status"],
        release_decision=str(result["release_decision"] or ""),
        execution_status=result["execution_status"],
        has_critical_failure=has_critical_failure,
    )

    next_actions: list[str] = []
    if validation_payload.get("warnings"):
        next_actions.append("Address adapter validation warnings before production onboarding.")
    if result["release_decision"] == "insufficient_evidence":
        next_actions.append("Adapter is in bootstrap/insufficient-evidence mode; establish local baseline evidence first.")
    elif result["release_decision"] == "block_release":
        for action in release_payload.get("recommended_actions_before_release", [])[:3]:
            next_actions.append(str(action))
    elif result["release_decision"] == "release_with_caution":
        next_actions.append("Proceed with caution and keep high-risk flows in targeted rerun cycle.")
    if result["execution_status"] in {"not_executed", "execution_error"}:
        next_actions.append("Run selected regression commands to convert planning signal into execution signal.")
    if has_critical_failure:
        next_actions.append("Investigate failed CI gate steps in step_results before merge/release decisions.")
    result["next_actions"] = list(dict.fromkeys(next_actions))

    if result["ci_gate_status"] == "pass":
        result["summary"] = "Adapter is valid, smart regression plan completed, and release signal is healthy."
    elif result["ci_gate_status"] == "warning":
        result["summary"] = "Gate completed with caution-level signal (warnings and/or plan-only execution)."
    else:
        result["summary"] = "Gate detected blocking risk (adapter/step failure or block_release decision)."

    evidence_ctx.write_json("ci_regression_gate_result", result)
    evidence_ctx.write_report(output_report_name, _render_markdown(result))

    print(f"[ci-gate] adapter={adapter_name} validation={result['adapter_validation_status']}")
    print(f"[ci-gate] intent={result['selected_intent']} mode={result['selected_mode']}")
    print(
        f"[ci-gate] release={result['release_decision']} "
        f"score={result['release_score']} confidence={result['confidence']}"
    )
    print(f"[ci-gate] status={result['ci_gate_status']}")
    print(f"[ci-gate] result={output_json_path}")

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))

    if result["ci_gate_status"] == "fail":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
