from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..application.analyzer import FailureAnalyzer
from ..domain.models import FailureAnalysisReport, utc_now_iso


DEFAULT_PYTEST_REPORT = Path("artifacts/pytest/pytest_report.json")
DEFAULT_ANALYSIS_REPORT = Path("artifacts/failure_analysis/failure_analysis_report.json")
DEFAULT_HISTORY_REPORT = Path("artifacts/failure_analysis/history.json")


def analyze_pytest_report_file(
    *,
    pytest_report_path: Path = DEFAULT_PYTEST_REPORT,
    output_path: Path = DEFAULT_ANALYSIS_REPORT,
    history_path: Path = DEFAULT_HISTORY_REPORT,
    write_history: bool = True,
) -> Optional[FailureAnalysisReport]:
    if not pytest_report_path.exists():
        return None

    analyzer = FailureAnalyzer()
    analysis = analyzer.analyze_pytest_report_file(pytest_report_path, output_path=output_path)

    if write_history:
        _append_history(history_path=history_path, report=analysis)
    return analysis


def load_failure_analysis_report(path: Path = DEFAULT_ANALYSIS_REPORT) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def build_notification_group_lines(analysis_payload: Dict[str, Any], *, max_groups: int = 3) -> List[str]:
    groups = analysis_payload.get("groups", []) if isinstance(analysis_payload, dict) else []
    lines: list[str] = []
    for idx, group in enumerate(groups[:max_groups], start=1):
        category = str(group.get("category", "unknown_failure_pattern"))
        count = int(group.get("count", 0))
        severity = str(group.get("severity", "medium")).upper()
        owner = str(group.get("owner", "qa_lead"))
        sample = ""
        examples = group.get("examples", []) if isinstance(group.get("examples", []), list) else []
        if examples:
            sample = str(examples[0])
        line = (
            f"{idx}. {category} | count={count} | severity={severity} | "
            f"owner={owner} | sample={sample}"
        )
        lines.append(line)
    return lines


def _append_history(*, history_path: Path, report: FailureAnalysisReport) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    payload: list[dict] = []
    if history_path.exists():
        try:
            loaded = json.loads(history_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                payload = loaded
        except json.JSONDecodeError:
            payload = []

    payload.append(
        {
            "timestamp": utc_now_iso(),
            "summary": asdict(report.summary),
            "source_report_path": report.source_report_path,
        }
    )
    payload = payload[-200:]
    history_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
