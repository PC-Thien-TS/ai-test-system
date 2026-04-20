from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from ..application.analyzer import FailureAnalyzer


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PYTEST_REPORT = ROOT / "artifacts" / "pytest" / "pytest_report.json"
DEFAULT_ANALYSIS_REPORT = ROOT / "artifacts" / "failure_analysis" / "failure_analysis_report.json"
DEFAULT_HISTORY_PATH = ROOT / "artifacts" / "failure_analysis" / "history.json"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_failure_analysis_report(payload: Dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def append_history(report: Dict[str, Any], history_path: Path) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    current: List[Dict[str, Any]] = []
    if history_path.exists():
        try:
            loaded = json.loads(history_path.read_text(encoding="utf-8"))
            if isinstance(loaded, list):
                current = loaded
        except Exception:
            current = []
    summary = report.get("summary", {}) or {}
    current.append(
        {
            "generated_at_utc": summary.get("generated_at_utc", ""),
            "total_failed": int(summary.get("total_failed", 0)),
            "total_groups": int(summary.get("total_groups", 0)),
            "highest_severity": str(summary.get("highest_severity", "low")),
            "critical_group_count": int(summary.get("critical_group_count", 0)),
            "most_affected_area": str(summary.get("most_affected_area", "unknown_area")),
        }
    )
    history_path.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")


def analyze_pytest_report_file(
    pytest_report_path: Path | str = DEFAULT_PYTEST_REPORT,
    output_path: Path | str = DEFAULT_ANALYSIS_REPORT,
    *,
    write_history: bool = True,
    history_path: Path | str = DEFAULT_HISTORY_PATH,
) -> Dict[str, Any]:
    pytest_path = Path(pytest_report_path)
    out_path = Path(output_path)
    history = Path(history_path)
    report_data = load_json(pytest_path)

    analyzer = FailureAnalyzer()
    analysis_obj = analyzer.analyze_pytest_report(report_data)
    analysis = analyzer.to_dict(analysis_obj)
    write_failure_analysis_report(analysis, out_path)
    if write_history:
        append_history(analysis, history)
    return analysis


def load_failure_analysis_report(path: Path | str = DEFAULT_ANALYSIS_REPORT) -> Dict[str, Any]:
    return load_json(Path(path))


def build_notification_group_lines(analysis_report: Dict[str, Any], top_n: int = 3) -> List[str]:
    groups = list(analysis_report.get("groups", []) or [])
    groups.sort(key=lambda g: (-int(g.get("count", 0)), str(g.get("category", ""))))
    lines: List[str] = []
    for group in groups[: max(0, top_n)]:
        examples = group.get("examples", []) or []
        sample = str(examples[0]) if examples else "unknown_test"
        lines.append(
            f"- [{str(group.get('severity', 'medium')).upper()}] "
            f"{group.get('category', 'unknown')} | count={int(group.get('count', 0))} | "
            f"owner={group.get('owner', 'qa_lead')} | sample={sample}"
        )
    return lines

