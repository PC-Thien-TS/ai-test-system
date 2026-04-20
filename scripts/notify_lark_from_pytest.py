from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.connectors.lark.application.lark_service import LarkNotificationService
from orchestrator.failure_analysis.integration.pytest_bridge import (
    analyze_pytest_report_file,
    build_notification_group_lines,
    load_failure_analysis_report,
)


LOGGER = logging.getLogger("pytest-lark-notify")
PYTEST_REPORT_PATH = Path("artifacts/pytest/pytest_report.json")
FAILURE_ANALYSIS_PATH = Path("artifacts/failure_analysis/failure_analysis_report.json")
FAILURE_ANALYSIS_HISTORY_PATH = Path("artifacts/failure_analysis/history.json")


def _load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _stats(report_payload: Dict[str, Any]) -> Dict[str, int]:
    summary = report_payload.get("summary", {}) if isinstance(report_payload, dict) else {}
    return {
        "total": int(summary.get("total", 0)),
        "passed": int(summary.get("passed", 0)),
        "failed": int(summary.get("failed", 0)),
        "skipped": int(summary.get("skipped", 0)),
    }


def _failed_tests(report_payload: Dict[str, Any], *, limit: int = 5) -> List[str]:
    tests = report_payload.get("tests", []) if isinstance(report_payload, dict) else []
    rows: list[str] = []
    for item in tests:
        if not isinstance(item, dict):
            continue
        outcome = str(item.get("outcome", "")).lower()
        failed = outcome in {"failed", "error"}
        if not failed:
            for stage in ("call", "setup", "teardown"):
                stage_payload = item.get(stage)
                if isinstance(stage_payload, dict) and str(stage_payload.get("outcome", "")).lower() in {"failed", "error"}:
                    failed = True
                    break
        if not failed:
            continue
        nodeid = str(item.get("nodeid", "unknown_test"))
        message = _extract_message(item)
        rows.append(f"- {nodeid}: {message}")
        if len(rows) >= limit:
            break
    return rows


def _extract_message(test_item: Dict[str, Any]) -> str:
    for stage in ("call", "setup", "teardown"):
        payload = test_item.get(stage)
        if not isinstance(payload, dict):
            continue
        crash = payload.get("crash")
        if isinstance(crash, dict):
            message = str(crash.get("message", "")).strip()
            if message:
                return message
        longrepr = payload.get("longrepr")
        if isinstance(longrepr, str) and longrepr.strip():
            return longrepr.strip().splitlines()[0][:220]
    longrepr = test_item.get("longrepr")
    if isinstance(longrepr, str) and longrepr.strip():
        return longrepr.strip().splitlines()[0][:220]
    return "failure details unavailable"


def _github_actions_run_url() -> str:
    server = os.getenv("GITHUB_SERVER_URL", "").strip()
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    run_id = os.getenv("GITHUB_RUN_ID", "").strip()
    if server and repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return ""


def _severity_from_failed_count(failed: int) -> str:
    if failed >= 10:
        return "critical"
    if failed >= 5:
        return "high"
    return "medium"


def _build_analysis_or_none(pytest_report_path: Path) -> Dict[str, Any] | None:
    analysis = analyze_pytest_report_file(
        pytest_report_path=pytest_report_path,
        output_path=FAILURE_ANALYSIS_PATH,
        history_path=FAILURE_ANALYSIS_HISTORY_PATH,
        write_history=True,
    )
    if analysis is not None:
        return analysis.to_dict()
    return load_failure_analysis_report(FAILURE_ANALYSIS_PATH)


def _build_root_cause_from_analysis(analysis_payload: Dict[str, Any]) -> str:
    summary = analysis_payload.get("summary", {}) if isinstance(analysis_payload, dict) else {}
    lines = [
        (
            "Failure analysis: "
            f"groups={summary.get('total_groups', 0)} | "
            f"critical_groups={summary.get('critical_group_count', 0)} | "
            f"most_affected_area={summary.get('most_affected_area', 'unknown')}"
        )
    ]
    lines.append("Top failure groups:")
    lines.extend(build_notification_group_lines(analysis_payload, max_groups=3))
    top_categories = summary.get("top_categories", {})
    if isinstance(top_categories, dict) and top_categories:
        category_blob = ", ".join(f"{k}={v}" for k, v in top_categories.items())
        lines.append(f"Root cause categories: {category_blob}")
    return "\n".join(lines)


def _build_event(
    *,
    stats: Dict[str, int],
    analysis_payload: Dict[str, Any] | None,
    fallback_failures: List[str],
) -> Dict[str, Any]:
    project_name = os.getenv("PROJECT_NAME", "rankmate").strip() or "rankmate"
    adapter_id = os.getenv("AI_TESTING_ADAPTER", project_name).strip() or project_name
    dashboard_url = os.getenv("DASHBOARD_URL", "").strip()
    ci_run_url = _github_actions_run_url()

    if analysis_payload:
        summary = analysis_payload.get("summary", {}) if isinstance(analysis_payload, dict) else {}
        severity = str(summary.get("highest_severity", "")).lower() or _severity_from_failed_count(stats["failed"])
        root_cause = _build_root_cause_from_analysis(analysis_payload)
        top_groups = analysis_payload.get("groups", []) if isinstance(analysis_payload, dict) else []
        recommended_action = ""
        if isinstance(top_groups, list) and top_groups:
            recommended_action = str(top_groups[0].get("recommended_action", "")).strip()
        if not recommended_action:
            recommended_action = "Investigate top failure groups and prioritize critical categories."
    else:
        severity = _severity_from_failed_count(stats["failed"])
        root_cause = "Top failures:\n" + ("\n".join(fallback_failures) if fallback_failures else "- No failure details available")
        recommended_action = "Review failing tests and classify root causes."

    if ci_run_url:
        root_cause = f"{root_cause}\nGitHub Actions: {ci_run_url}"

    return {
        "event_type": "decision_result",
        "title": f"Pytest failures detected ({stats['failed']})",
        "project": project_name,
        "adapter": adapter_id,
        "severity": severity,
        "occurrence_count": stats["failed"],
        "confidence": 0.9 if severity == "critical" else 0.75 if severity == "high" else 0.6,
        "primary_decision": "BLOCK_RELEASE" if severity == "critical" else "RELEASE_WITH_CAUTION",
        "self_healing_status": "NOT_EXECUTED",
        "root_cause": root_cause,
        "action_required": recommended_action,
        "dashboard_url": dashboard_url or None,
        "metadata": {
            "pytest_report_path": str(PYTEST_REPORT_PATH),
            "failure_analysis_path": str(FAILURE_ANALYSIS_PATH),
            "stats": stats,
            "ci_run_url": ci_run_url,
        },
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[notify-lark] %(message)s")

    if not PYTEST_REPORT_PATH.exists():
        LOGGER.warning("pytest report not found: %s", PYTEST_REPORT_PATH)
        return 0

    try:
        report_payload = _load_json(PYTEST_REPORT_PATH)
    except Exception as exc:
        LOGGER.warning("failed to parse pytest report: %s", exc)
        return 0

    stats = _stats(report_payload)
    LOGGER.info(
        "pytest summary total=%s passed=%s failed=%s skipped=%s",
        stats["total"],
        stats["passed"],
        stats["failed"],
        stats["skipped"],
    )

    if stats["failed"] <= 0:
        LOGGER.info("no pytest failures; notification skipped")
        return 0

    analysis_payload: Dict[str, Any] | None = None
    try:
        analysis_payload = _build_analysis_or_none(PYTEST_REPORT_PATH)
        if analysis_payload:
            LOGGER.info(
                "failure analysis ready groups=%s highest=%s",
                analysis_payload.get("summary", {}).get("total_groups", 0),
                analysis_payload.get("summary", {}).get("highest_severity", "unknown"),
            )
    except Exception as exc:
        LOGGER.warning("failure analysis unavailable, fallback to basic summary: %s", exc)
        analysis_payload = None

    fallback_failures = _failed_tests(report_payload, limit=5)
    event = _build_event(stats=stats, analysis_payload=analysis_payload, fallback_failures=fallback_failures)

    service = LarkNotificationService()
    try:
        result = service.send(event)
        LOGGER.info(
            "lark notify attempted=%s sent=%s reason=%s dry_run=%s",
            result.attempted,
            result.sent,
            result.reason,
            result.dry_run,
        )
    except Exception as exc:
        LOGGER.warning("lark notify failed but remains non-blocking: %s", exc)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
