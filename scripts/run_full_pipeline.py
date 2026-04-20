from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"
ARTIFACTS_DIR = REPO_ROOT / "artifacts"

PYTEST_REPORT_PATH = ARTIFACTS_DIR / "pytest" / "pytest_report.json"
FAILURE_ANALYSIS_REPORT_PATH = ARTIFACTS_DIR / "failure_analysis" / "failure_analysis_report.json"
DECISION_RESULT_PATH = ARTIFACTS_DIR / "decision" / "decision_result.json"
SELF_HEALING_RESULT_PATH = ARTIFACTS_DIR / "self_healing" / "self_healing_result.json"
DASHBOARD_SNAPSHOT_PATH = ARTIFACTS_DIR / "dashboard" / "dashboard_snapshot.json"
PIPELINE_SUMMARY_PATH = ARTIFACTS_DIR / "pipeline" / "pipeline_run_summary.json"
DEFAULT_POLICY_PATHS = [
    REPO_ROOT / "config" / "decision_policy_v2.json",
    ARTIFACTS_DIR / "decision" / "policy_config.json",
]
DEFAULT_MEMORY_CONTEXT_PATHS = [
    ARTIFACTS_DIR / "memory" / "failure_memory_context.json",
    ARTIFACTS_DIR / "failure_memory" / "failure_memory_context.json",
]


class StepStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class PipelineStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


CRITICAL_STEPS = {"run_pytest", "analyze_failures", "decision_engine"}


@dataclass(slots=True)
class StepResult:
    step_name: str
    status: StepStatus
    started_at_utc: str
    finished_at_utc: str
    return_code: Optional[int] = None
    artifact_path: str = ""
    message: str = ""
    error: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_name": self.step_name,
            "status": self.status.value,
            "started_at_utc": self.started_at_utc,
            "finished_at_utc": self.finished_at_utc,
            "return_code": self.return_code,
            "artifact_path": self.artifact_path,
            "message": self.message,
            "error": self.error,
            "details": self.details,
        }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def mtime_ns(path: Path) -> Optional[int]:
    if not path.exists():
        return None
    return path.stat().st_mtime_ns


def artifact_fresh(path: Path, before_mtime_ns: Optional[int]) -> bool:
    if not path.exists():
        return False
    current = path.stat().st_mtime_ns
    if before_mtime_ns is None:
        return True
    return current != before_mtime_ns


def run_subprocess_step(
    *,
    step_name: str,
    command: List[str],
    expected_artifact: Optional[Path],
    critical: bool,
    extra_env: Optional[Dict[str, str]] = None,
) -> StepResult:
    started = utc_now_iso()
    before_mtime = mtime_ns(expected_artifact) if expected_artifact else None
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    try:
        proc = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
        )
    except Exception as exc:
        return StepResult(
            step_name=step_name,
            status=StepStatus.FAILED,
            started_at_utc=started,
            finished_at_utc=utc_now_iso(),
            return_code=None,
            artifact_path=str(expected_artifact) if expected_artifact else "",
            message="subprocess execution error",
            error=f"{type(exc).__name__}: {exc}",
        )

    stdout_tail = (proc.stdout or "").splitlines()[-8:]
    stderr_tail = (proc.stderr or "").splitlines()[-8:]
    artifact_exists = expected_artifact.exists() if expected_artifact else False
    artifact_is_fresh = artifact_fresh(expected_artifact, before_mtime) if expected_artifact else False

    details = {
        "command": command,
        "artifact_exists": artifact_exists,
        "artifact_fresh": artifact_is_fresh,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
    }

    if proc.returncode == 0:
        if expected_artifact and not artifact_exists:
            status = StepStatus.FAILED if critical else StepStatus.PARTIAL
            message = "command succeeded but expected artifact missing"
        else:
            status = StepStatus.SUCCESS
            message = "command completed"
    else:
        if expected_artifact and artifact_exists and artifact_is_fresh:
            status = StepStatus.PARTIAL
            message = "command returned non-zero but fresh artifact exists"
        else:
            status = StepStatus.FAILED if critical else StepStatus.PARTIAL
            message = "command returned non-zero"

    return StepResult(
        step_name=step_name,
        status=status,
        started_at_utc=started,
        finished_at_utc=utc_now_iso(),
        return_code=proc.returncode,
        artifact_path=str(expected_artifact) if expected_artifact else "",
        message=message,
        details=details,
    )


def parse_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def resolve_optional_paths(env_var: str, default_paths: List[Path]) -> List[Path]:
    env_path = os.getenv(env_var, "").strip()
    resolved: list[Path] = []
    if env_path:
        resolved.append(Path(env_path))
    resolved.extend(default_paths)
    return resolved


def load_optional_json(paths: List[Path]) -> tuple[Dict[str, Any], str]:
    for path in paths:
        if not path.exists():
            continue
        try:
            return read_json(path), str(path)
        except Exception:
            continue
    return {}, ""


def merge_policy(default_policy: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(default_policy)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            nested = dict(merged[key])
            nested.update(value)
            merged[key] = nested
        else:
            merged[key] = value
    return merged


def default_decision_policy() -> Dict[str, Any]:
    return {
        "policy_version": "decision_intelligence_v2",
        "release_critical_keywords": ["payment", "auth", "order"],
        "high_severity_groups_block_threshold": 2,
        "rerun_recommended_min_flaky_score": 0.40,
        "suppress_min_flaky_score": 0.75,
        "recurrence_rate_high_threshold": 0.40,
    }


def map_decision_confidence(decision: str, matched_rule: str, total_tests: int, total_groups: int) -> float:
    base_by_rule = {
        "no_failures": 0.98,
        "release_critical_high_or_critical": 0.92,
        "multiple_high_severity_groups": 0.88,
        "only_flaky_non_critical_suppress": 0.78,
        "only_flaky_non_critical_rerun": 0.75,
        "medium_low_non_critical_escalate": 0.82,
        "safe_fallback": 0.65,
    }
    score = base_by_rule.get(matched_rule, 0.65)
    if total_tests <= 0:
        score -= 0.10
    if total_groups <= 0 and decision != "PASS":
        score -= 0.08
    return round(clamp(score, 0.50, 0.99), 2)


def infer_risk_level(decision: str, highest_severity: str, fail_ratio: float) -> str:
    if decision == "BLOCK_RELEASE" or highest_severity in {"critical", "high"}:
        return "high"
    if decision in {"ESCALATE", "RERUN_RECOMMENDED"} or fail_ratio >= 0.10:
        return "medium"
    return "low"


def build_decision_payload(
    *,
    project: str,
    failure_analysis: Dict[str, Any],
    pytest_report: Dict[str, Any],
    memory_context: Dict[str, Any],
    policy_config: Dict[str, Any],
    memory_context_source: str,
    policy_source: str,
) -> Dict[str, Any]:
    groups = failure_analysis.get("groups", []) if isinstance(failure_analysis, dict) else []
    summary = failure_analysis.get("summary", {}) if isinstance(failure_analysis, dict) else {}
    pytest_summary = pytest_report.get("summary", {}) if isinstance(pytest_report, dict) else {}

    total_failed = parse_int(summary.get("total_failed"), parse_int(pytest_summary.get("failed"), 0))
    total_groups = parse_int(summary.get("total_groups"), len(groups))
    total_tests = parse_int(pytest_summary.get("total"), 0)
    total_passed = parse_int(pytest_summary.get("passed"), 0)
    total_skipped = parse_int(pytest_summary.get("skipped"), 0)

    pass_ratio = (total_passed / total_tests) if total_tests > 0 else 0.0
    fail_ratio = (total_failed / total_tests) if total_tests > 0 else 0.0

    severity_distribution = {"critical": 0, "high": 0, "medium": 0, "low": 0, "unknown": 0}
    high_or_critical_groups = 0
    high_or_critical_failures = 0
    repeated_failures = 0

    release_keywords = [str(x).lower() for x in policy_config.get("release_critical_keywords", [])]
    release_critical_hits: set[str] = set()

    for group in groups:
        if not isinstance(group, dict):
            continue
        sev = str(group.get("severity", "unknown")).lower()
        count = parse_int(group.get("count"), 1)
        if sev not in severity_distribution:
            sev = "unknown"
        severity_distribution[sev] += count
        if sev in {"critical", "high"}:
            high_or_critical_groups += 1
            high_or_critical_failures += count
        if count > 1:
            repeated_failures += (count - 1)

        searchable = " ".join(
            [
                str(group.get("module_family", "")),
                str(group.get("category", "")),
                str(group.get("message_pattern", "")),
                " ".join(str(x) for x in group.get("examples", [])[:3]) if isinstance(group.get("examples"), list) else "",
            ]
        ).lower()
        for keyword in release_keywords:
            if keyword and keyword in searchable:
                release_critical_hits.add(keyword)

    most_affected_area = str(summary.get("most_affected_area", "unknown"))
    for keyword in release_keywords:
        if keyword and keyword in most_affected_area.lower():
            release_critical_hits.add(keyword)

    recurrence_rate_default = (repeated_failures / total_failed) if total_failed > 0 else 0.0
    recurrence_rate = parse_float(memory_context.get("recurrence_rate"), recurrence_rate_default)
    flaky_score_default = severity_distribution["low"] / max(total_failed, 1)
    flaky_score = parse_float(memory_context.get("flaky_score"), flaky_score_default)
    flaky_signal = bool(memory_context.get("flaky_signal", False))
    only_non_critical = high_or_critical_groups == 0
    if only_non_critical and severity_distribution["medium"] + severity_distribution["low"] > 0 and flaky_score >= 0.40:
        flaky_signal = True

    decision = "ESCALATE"
    release_action = "HOLD_AND_REVIEW"
    matched_rule = "safe_fallback"
    fallback_used = True
    rationale: list[str] = []

    high_threshold = parse_int(policy_config.get("high_severity_groups_block_threshold"), 2)
    suppress_min_flaky = parse_float(policy_config.get("suppress_min_flaky_score"), 0.75)
    rerun_min_flaky = parse_float(policy_config.get("rerun_recommended_min_flaky_score"), 0.40)

    if total_failed <= 0:
        decision = "PASS"
        release_action = "ALLOW_RELEASE"
        matched_rule = "no_failures"
        fallback_used = False
        rationale.append("No failed tests detected.")
    elif release_critical_hits and high_or_critical_groups > 0:
        decision = "BLOCK_RELEASE"
        release_action = "BLOCK"
        matched_rule = "release_critical_high_or_critical"
        fallback_used = False
        rationale.append("High/Critical failures impact release-critical area (payment/auth/order).")
    elif high_or_critical_groups >= high_threshold:
        decision = "BLOCK_RELEASE"
        release_action = "BLOCK"
        matched_rule = "multiple_high_severity_groups"
        fallback_used = False
        rationale.append(f"Detected >= {high_threshold} high-severity failure groups.")
    elif only_non_critical and flaky_signal:
        if flaky_score >= suppress_min_flaky:
            decision = "SUPPRESS"
            release_action = "SUPPRESS_AND_MONITOR"
            matched_rule = "only_flaky_non_critical_suppress"
            fallback_used = False
            rationale.append("Only flaky non-critical failures detected; suppression eligible.")
        elif flaky_score >= rerun_min_flaky or recurrence_rate >= parse_float(policy_config.get("recurrence_rate_high_threshold"), 0.40):
            decision = "RERUN_RECOMMENDED"
            release_action = "RETRY_BEFORE_RELEASE"
            matched_rule = "only_flaky_non_critical_rerun"
            fallback_used = False
            rationale.append("Flaky non-critical failures detected; rerun recommended before release.")
    elif only_non_critical:
        decision = "ESCALATE"
        release_action = "HOLD_AND_REVIEW"
        matched_rule = "medium_low_non_critical_escalate"
        fallback_used = False
        rationale.append("Only medium/low non-critical failures detected; escalation required.")

    if fallback_used:
        rationale.append("No explicit rule matched cleanly; applying safe fallback ESCALATE.")

    rationale.extend(
        [
            f"total_failed={total_failed}",
            f"total_groups={total_groups}",
            f"most_affected_area={most_affected_area}",
            f"recurrence_rate={recurrence_rate:.2f}",
            f"flaky_score={flaky_score:.2f}",
            f"pass_ratio={pass_ratio:.2f}",
            f"fail_ratio={fail_ratio:.2f}",
        ]
    )

    confidence = map_decision_confidence(
        decision=decision,
        matched_rule=matched_rule,
        total_tests=total_tests,
        total_groups=total_groups,
    )
    risk_level = infer_risk_level(decision, str(summary.get("highest_severity", "unknown")).lower(), fail_ratio)

    recommended_actions: list[str] = []
    if decision == "PASS":
        recommended_actions.append("Proceed with release and continue baseline monitoring.")
    elif decision == "BLOCK_RELEASE":
        recommended_actions.extend(
            [
                "Block release and assign immediate owner for critical clusters.",
                "Prioritize fix for release-critical impacted area before next gate run.",
            ]
        )
    elif decision == "SUPPRESS":
        recommended_actions.extend(
            [
                "Suppress known flaky failures with monitoring guardrails.",
                "Track suppression trend and auto-expire suppression if pattern changes.",
            ]
        )
    elif decision == "RERUN_RECOMMENDED":
        recommended_actions.extend(
            [
                "Run targeted rerun on flaky clusters before final release gate.",
                "Compare rerun deltas to confirm transient behavior.",
            ]
        )
    else:
        recommended_actions.extend(
            [
                "Escalate to owning team for deterministic root-cause investigation.",
                "Hold release decision until cluster status converges.",
            ]
        )

    return {
        "generated_at": utc_now_iso(),
        "project": project,
        "decision": decision,
        "release_action": release_action,
        "confidence": confidence,
        "rationale": rationale,
        "decision_inputs": {
            "total_tests": total_tests,
            "total_passed": total_passed,
            "total_failed": total_failed,
            "total_skipped": total_skipped,
            "total_groups": total_groups,
            "pass_ratio": round(pass_ratio, 4),
            "fail_ratio": round(fail_ratio, 4),
            "severity_distribution": severity_distribution,
            "most_affected_area": most_affected_area,
            "recurrence_rate": round(recurrence_rate, 4),
            "flaky_signal": flaky_signal,
            "flaky_score": round(flaky_score, 4),
            "release_critical_hits": sorted(release_critical_hits),
        },
        "policy_evaluation": {
            "policy_version": str(policy_config.get("policy_version", "decision_intelligence_v2")),
            "matched_rule": matched_rule,
            "fallback_used": fallback_used,
            "source": policy_source or "default_policy",
            "thresholds": {
                "high_severity_groups_block_threshold": high_threshold,
                "suppress_min_flaky_score": suppress_min_flaky,
                "rerun_recommended_min_flaky_score": rerun_min_flaky,
                "recurrence_rate_high_threshold": parse_float(policy_config.get("recurrence_rate_high_threshold"), 0.40),
            },
        },
        "risk_summary": {
            "risk_level": risk_level,
            "highest_severity": str(summary.get("highest_severity", "unknown")).lower(),
            "high_or_critical_group_count": high_or_critical_groups,
            "high_or_critical_failure_count": high_or_critical_failures,
            "critical_group_count": parse_int(summary.get("critical_group_count"), 0),
        },
        "recommended_next_actions": recommended_actions,
        "memory_context": {
            "available": bool(memory_context),
            "source": memory_context_source,
            "recurrence_rate": round(recurrence_rate, 4),
            "flaky_signal": flaky_signal,
            "flaky_score": round(flaky_score, 4),
            "raw": memory_context,
        },
        "gating_signals": {
            "has_failures": total_failed > 0,
            "has_high_or_critical_groups": high_or_critical_groups > 0,
            "release_critical_area_impacted": bool(release_critical_hits),
            "only_non_critical": only_non_critical,
            "should_block_release": decision == "BLOCK_RELEASE",
            "should_retry_before_release": decision == "RERUN_RECOMMENDED",
            "should_suppress": decision == "SUPPRESS",
        },
    }


def step_decision_engine(*, project: str) -> StepResult:
    started = utc_now_iso()
    try:
        if not FAILURE_ANALYSIS_REPORT_PATH.exists():
            return StepResult(
                step_name="decision_engine",
                status=StepStatus.FAILED,
                started_at_utc=started,
                finished_at_utc=utc_now_iso(),
                artifact_path=str(DECISION_RESULT_PATH),
                message="failure analysis report missing",
            )

        analysis = read_json(FAILURE_ANALYSIS_REPORT_PATH)
        pytest_report = read_json(PYTEST_REPORT_PATH) if PYTEST_REPORT_PATH.exists() else {}
        policy_override, policy_source = load_optional_json(
            resolve_optional_paths("DECISION_POLICY_CONFIG_PATH", DEFAULT_POLICY_PATHS)
        )
        memory_context, memory_source = load_optional_json(
            resolve_optional_paths("FAILURE_MEMORY_CONTEXT_PATH", DEFAULT_MEMORY_CONTEXT_PATHS)
        )
        policy = merge_policy(default_decision_policy(), policy_override)
        decision_payload = build_decision_payload(
            project=project,
            failure_analysis=analysis,
            pytest_report=pytest_report,
            memory_context=memory_context,
            policy_config=policy,
            memory_context_source=memory_source,
            policy_source=policy_source,
        )
        write_json(DECISION_RESULT_PATH, decision_payload)

        return StepResult(
            step_name="decision_engine",
            status=StepStatus.SUCCESS,
            started_at_utc=started,
            finished_at_utc=utc_now_iso(),
            return_code=0,
            artifact_path=str(DECISION_RESULT_PATH),
            message="decision artifact generated",
            details={
                "decision": decision_payload["decision"],
                "release_action": decision_payload["release_action"],
                "matched_rule": decision_payload["policy_evaluation"]["matched_rule"],
                "confidence": decision_payload["confidence"],
            },
        )
    except Exception as exc:
        return StepResult(
            step_name="decision_engine",
            status=StepStatus.FAILED,
            started_at_utc=started,
            finished_at_utc=utc_now_iso(),
            artifact_path=str(DECISION_RESULT_PATH),
            message="decision engine execution error",
            error=f"{type(exc).__name__}: {exc}",
        )


def step_self_healing(*, project: str, enabled: bool) -> StepResult:
    started = utc_now_iso()
    try:
        decision = read_json(DECISION_RESULT_PATH) if DECISION_RESULT_PATH.exists() else {}
        if not enabled:
            payload = {
                "generated_at": utc_now_iso(),
                "project": project,
                "status": "SKIPPED",
                "enabled": False,
                "executed": False,
                "reason": "Self-healing hook disabled.",
                "decision_context": {
                    "decision": decision.get("decision", "UNKNOWN"),
                    "release_action": decision.get("release_action", "UNKNOWN"),
                },
                "next_integration_hook": "Enable --enable-self-healing to activate placeholder execution flow.",
            }
            write_json(SELF_HEALING_RESULT_PATH, payload)
            return StepResult(
                step_name="self_healing",
                status=StepStatus.SKIPPED,
                started_at_utc=started,
                finished_at_utc=utc_now_iso(),
                return_code=0,
                artifact_path=str(SELF_HEALING_RESULT_PATH),
                message="self-healing disabled; skipped with artifact",
            )

        payload = {
            "generated_at": utc_now_iso(),
            "project": project,
            "status": "PLACEHOLDER_EXECUTED",
            "enabled": True,
            "executed": False,
            "action": "NO_ACTION",
            "reason": "Self-healing placeholder executed; engine hook pending integration.",
            "decision_context": {
                "decision": decision.get("decision", "UNKNOWN"),
                "release_action": decision.get("release_action", "UNKNOWN"),
            },
            "next_integration_hook": "Replace placeholder with orchestrator.self_healing engine execution.",
        }
        write_json(SELF_HEALING_RESULT_PATH, payload)
        return StepResult(
            step_name="self_healing",
            status=StepStatus.SUCCESS,
            started_at_utc=started,
            finished_at_utc=utc_now_iso(),
            return_code=0,
            artifact_path=str(SELF_HEALING_RESULT_PATH),
            message="self-healing placeholder completed",
        )
    except Exception as exc:
        return StepResult(
            step_name="self_healing",
            status=StepStatus.FAILED,
            started_at_utc=started,
            finished_at_utc=utc_now_iso(),
            artifact_path=str(SELF_HEALING_RESULT_PATH),
            message="self-healing hook error",
            error=f"{type(exc).__name__}: {exc}",
        )


def compute_pipeline_status(step_results: List[StepResult]) -> PipelineStatus:
    critical_failed = any(
        result.step_name in CRITICAL_STEPS and result.status == StepStatus.FAILED for result in step_results
    )
    if critical_failed:
        return PipelineStatus.FAILED

    any_non_success = any(result.status != StepStatus.SUCCESS for result in step_results)
    if any_non_success:
        return PipelineStatus.PARTIAL
    return PipelineStatus.SUCCESS


def step_dashboard_snapshot(*, project: str, pipeline_status: PipelineStatus) -> StepResult:
    started = utc_now_iso()
    try:
        pytest_payload = read_json(PYTEST_REPORT_PATH) if PYTEST_REPORT_PATH.exists() else {}
        pytest_summary = pytest_payload.get("summary", {}) if isinstance(pytest_payload, dict) else {}

        analysis_payload = read_json(FAILURE_ANALYSIS_REPORT_PATH) if FAILURE_ANALYSIS_REPORT_PATH.exists() else {}
        analysis_summary = analysis_payload.get("summary", {}) if isinstance(analysis_payload, dict) else {}

        decision_payload = read_json(DECISION_RESULT_PATH) if DECISION_RESULT_PATH.exists() else {}

        snapshot = {
            "generated_at": utc_now_iso(),
            "project": project,
            "pipeline_status": pipeline_status.value,
            "decision": decision_payload.get("decision", "UNKNOWN"),
            "release_action": decision_payload.get("release_action", "UNKNOWN"),
            "pytest_summary": {
                "total": int(pytest_summary.get("total", 0)),
                "passed": int(pytest_summary.get("passed", 0)),
                "failed": int(pytest_summary.get("failed", 0)),
                "skipped": int(pytest_summary.get("skipped", 0)),
            },
            "failure_group_count": int(analysis_summary.get("total_groups", 0)),
            "highest_failure_severity": str(analysis_summary.get("highest_severity", "unknown")),
            "most_affected_area": str(analysis_summary.get("most_affected_area", "unknown")),
        }
        write_json(DASHBOARD_SNAPSHOT_PATH, snapshot)
        return StepResult(
            step_name="dashboard_snapshot",
            status=StepStatus.SUCCESS,
            started_at_utc=started,
            finished_at_utc=utc_now_iso(),
            return_code=0,
            artifact_path=str(DASHBOARD_SNAPSHOT_PATH),
            message="dashboard snapshot generated",
        )
    except Exception as exc:
        return StepResult(
            step_name="dashboard_snapshot",
            status=StepStatus.FAILED,
            started_at_utc=started,
            finished_at_utc=utc_now_iso(),
            artifact_path=str(DASHBOARD_SNAPSHOT_PATH),
            message="dashboard snapshot generation error",
            error=f"{type(exc).__name__}: {exc}",
        )


def should_strict_fail(step_results: List[StepResult]) -> bool:
    for result in step_results:
        if result.step_name in {"notify_lark", "dashboard_snapshot"} and result.status != StepStatus.SUCCESS:
            return True
    return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run full deterministic QA pipeline orchestration.")
    parser.add_argument("--project", default=os.getenv("PROJECT_NAME", "rankmate"), help="Project/workspace id.")
    parser.add_argument(
        "--real-send-lark",
        action="store_true",
        help="Send Lark notification in real mode (default: dry-run).",
    )
    parser.add_argument(
        "--enable-self-healing",
        action="store_true",
        help="Enable self-healing hook placeholder execution.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return non-zero when non-critical notify/dashboard steps are not SUCCESS.",
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Extra args forwarded to run_pytest_with_report.py (use `--` before args).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="[full-pipeline] %(message)s")
    logger = logging.getLogger("full-pipeline")

    started_at = utc_now_iso()
    step_results: List[StepResult] = []
    pipeline_status = PipelineStatus.FAILED
    fatal_error = ""
    exit_code = 1

    try:
        logger.info("pipeline start project=%s strict=%s", args.project, args.strict)

        pytest_cmd = [sys.executable, str(SCRIPTS_DIR / "run_pytest_with_report.py")]
        forwarded_args = list(args.pytest_args or [])
        if forwarded_args and forwarded_args[0] == "--":
            forwarded_args = forwarded_args[1:]
        pytest_cmd.extend(forwarded_args)

        step_results.append(
            run_subprocess_step(
                step_name="run_pytest",
                command=pytest_cmd,
                expected_artifact=PYTEST_REPORT_PATH,
                critical=True,
            )
        )

        step_results.append(
            run_subprocess_step(
                step_name="analyze_failures",
                command=[sys.executable, str(SCRIPTS_DIR / "analyze_pytest_failures.py")],
                expected_artifact=FAILURE_ANALYSIS_REPORT_PATH,
                critical=True,
            )
        )

        step_results.append(step_decision_engine(project=args.project))
        step_results.append(step_self_healing(project=args.project, enabled=args.enable_self_healing))

        notify_env = {
            "PROJECT_NAME": args.project,
            "LARK_DRY_RUN": "false" if args.real_send_lark else "true",
        }
        step_results.append(
            run_subprocess_step(
                step_name="notify_lark",
                command=[sys.executable, str(SCRIPTS_DIR / "notify_lark_from_pytest.py")],
                expected_artifact=None,
                critical=False,
                extra_env=notify_env,
            )
        )

        provisional_status = compute_pipeline_status(step_results)
        step_results.append(step_dashboard_snapshot(project=args.project, pipeline_status=provisional_status))

        pipeline_status = compute_pipeline_status(step_results)

        if pipeline_status == PipelineStatus.FAILED:
            exit_code = 1
        elif args.strict and should_strict_fail(step_results):
            exit_code = 2
        else:
            exit_code = 0

    except Exception as exc:
        fatal_error = f"{type(exc).__name__}: {exc}"
        logger.exception("pipeline fatal error")
        pipeline_status = PipelineStatus.FAILED
        exit_code = 1
    finally:
        summary_payload = {
            "started_at": started_at,
            "finished_at": utc_now_iso(),
            "project": args.project if "args" in locals() else "unknown",
            "pipeline_status": pipeline_status.value if isinstance(pipeline_status, PipelineStatus) else "FAILED",
            "strict_mode": bool(args.strict) if "args" in locals() else False,
            "steps": [step.to_dict() for step in step_results],
            "error": fatal_error,
            "artifacts": {
                "pytest_report": str(PYTEST_REPORT_PATH),
                "failure_analysis_report": str(FAILURE_ANALYSIS_REPORT_PATH),
                "decision_result": str(DECISION_RESULT_PATH),
                "self_healing_result": str(SELF_HEALING_RESULT_PATH),
                "dashboard_snapshot": str(DASHBOARD_SNAPSHOT_PATH),
                "pipeline_summary": str(PIPELINE_SUMMARY_PATH),
            },
        }
        try:
            write_json(PIPELINE_SUMMARY_PATH, summary_payload)
            logging.getLogger("full-pipeline").info("pipeline summary written: %s", PIPELINE_SUMMARY_PATH)
        except Exception as exc:
            logging.getLogger("full-pipeline").error("failed to write pipeline summary: %s", exc)
            # Final fail-safe: if summary cannot be written, force non-zero.
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
