from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_PATH = ROOT / "artifacts" / "pytest" / "pytest_report.json"

from orchestrator.connectors.lark import (  # noqa: E402
    LarkNotificationEvent,
    LarkNotificationEventType,
    LarkNotificationService,
)
from orchestrator.failure_analysis.integration.pytest_bridge import (  # noqa: E402
    analyze_pytest_report_file,
    build_notification_group_lines,
)


ANALYSIS_PATH = ROOT / "artifacts" / "failure_analysis" / "failure_analysis_report.json"


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def load_report(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"pytest report not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def parse_summary(report: Dict[str, Any]) -> Dict[str, int]:
    summary = report.get("summary", {}) or {}
    total = int(summary.get("total", 0))
    passed = int(summary.get("passed", 0))
    failed = int(summary.get("failed", 0))
    skipped = int(summary.get("skipped", 0))
    errors = int(summary.get("error", 0))
    failed_total = failed + errors
    return {
        "total": total,
        "passed": passed,
        "failed": failed_total,
        "skipped": skipped,
    }


def extract_failure_summaries(report: Dict[str, Any], limit: int = 5) -> List[str]:
    tests = report.get("tests", []) or []
    collected: List[str] = []
    for test in tests:
        outcome = str(test.get("outcome", "")).lower()
        if outcome not in {"failed", "error"}:
            continue
        nodeid = str(test.get("nodeid", "unknown_test"))
        crash_msg = ""
        for phase in ("call", "setup", "teardown"):
            phase_data = test.get(phase, {}) or {}
            crash = phase_data.get("crash", {}) or {}
            if crash.get("message"):
                crash_msg = str(crash.get("message"))
                break
            longrepr = phase_data.get("longrepr")
            if isinstance(longrepr, str) and longrepr.strip():
                crash_msg = longrepr.strip().splitlines()[-1]
                break
        if not crash_msg:
            crash_msg = "failure details unavailable"
        crash_msg = " ".join(crash_msg.split())
        collected.append(f"{nodeid}: {crash_msg}")
        if len(collected) >= limit:
            break
    return collected


def infer_severity(failed_count: int) -> str:
    if failed_count >= 10:
        return "critical"
    if failed_count >= 1:
        return "high"
    return "low"


def build_github_run_link() -> str:
    server = os.getenv("GITHUB_SERVER_URL", "").strip()
    repo = os.getenv("GITHUB_REPOSITORY", "").strip()
    run_id = os.getenv("GITHUB_RUN_ID", "").strip()
    if server and repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return ""


def to_log_dict(obj: Any) -> Dict[str, Any]:
    if is_dataclass(obj):
        return asdict(obj)
    if isinstance(obj, dict):
        return obj
    return {"value": str(obj)}


def main() -> int:
    configure_logging()
    logging.info("lark_pytest_notify_start | report=%s", REPORT_PATH)

    try:
        report = load_report(REPORT_PATH)
    except Exception as exc:
        logging.error("lark_pytest_notify_no_report | error=%s", exc)
        return 0

    summary = parse_summary(report)
    if summary["failed"] <= 0:
        logging.info("lark_pytest_notify_skip | reason=no_failures | summary=%s", summary)
        return 0

    failure_summaries = extract_failure_summaries(report, limit=5)
    severity = infer_severity(summary["failed"])
    project_name = os.getenv("PROJECT_NAME", "ai_test_system").strip() or "ai_test_system"
    dashboard_url = os.getenv("DASHBOARD_URL", "").strip() or None
    github_run_url = build_github_run_link()

    analysis_report: Dict[str, Any] | None = None
    try:
        analysis_report = analyze_pytest_report_file(
            pytest_report_path=REPORT_PATH,
            output_path=ANALYSIS_PATH,
            write_history=True,
        )
        logging.info("lark_pytest_notify_analysis_ready | path=%s", ANALYSIS_PATH)
    except Exception as exc:
        logging.warning("lark_pytest_notify_analysis_fallback | error=%s", exc)

    root_cause_lines = [
        f"pytest failures detected in project {project_name}",
        f"stats: total={summary['total']} passed={summary['passed']} failed={summary['failed']} skipped={summary['skipped']}",
    ]
    action_lines = ["Review failing tests and logs in artifacts/pytest."]

    if analysis_report:
        analysis_summary = analysis_report.get("summary", {}) or {}
        top_groups = build_notification_group_lines(analysis_report, top_n=3)
        highest = str(analysis_summary.get("highest_severity", severity)).strip().lower()
        if highest:
            severity = highest
        root_cause_lines.extend(
            [
                f"grouped_failures: groups={analysis_summary.get('total_groups', 0)} "
                f"critical_groups={analysis_summary.get('critical_group_count', 0)}",
                f"most_affected_area: {analysis_summary.get('most_affected_area', 'unknown_area')}",
                "",
                "top_groups:",
                *(top_groups or ["- unavailable"]),
            ]
        )
        groups = list(analysis_report.get("groups", []) or [])
        categories = [str(g.get("category", "unknown")) for g in groups[:3]]
        if categories:
            root_cause_lines.append("")
            root_cause_lines.append("root_cause_categories:")
            root_cause_lines.extend([f"- {cat}" for cat in categories])
        if groups:
            top_action = str(groups[0].get("recommended_action", "")).strip()
            if top_action:
                action_lines.append(top_action)
    else:
        root_cause_lines.extend(
            [
                "",
                "top_failures:",
                *[f"- {line}" for line in failure_summaries],
            ]
        )
    if github_run_url:
        action_lines.append(f"GitHub Actions run: {github_run_url}")

    event = LarkNotificationEvent(
        event_type=LarkNotificationEventType.DECISION_RESULT,
        title=f"Pytest failures detected ({summary['failed']})",
        project=project_name,
        adapter=project_name,
        severity=severity,
        occurrence_count=summary["failed"],
        confidence=None,
        primary_decision="BLOCK_RELEASE",
        self_healing_status="FAILED",
        root_cause="\n".join(root_cause_lines),
        action_required="\n".join(action_lines),
        dashboard_url=dashboard_url,
        metadata={
            "summary": summary,
            "top_failures": failure_summaries,
            "github_run_url": github_run_url,
            "report_path": str(REPORT_PATH),
            "failure_analysis_path": str(ANALYSIS_PATH),
            "failure_analysis_summary": (analysis_report or {}).get("summary", {}),
        },
    )

    service = LarkNotificationService()
    try:
        result = service.send(event)
    except Exception as exc:
        logging.exception("lark_pytest_notify_send_exception | error=%s", exc)
        return 0

    logging.info("lark_pytest_notify_done | result=%s", to_log_dict(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
