from __future__ import annotations

from collections import Counter
from dataclasses import asdict
from typing import Any, Dict, List

from ..domain.grouping import group_failures, module_family_from_nodeid
from ..domain.models import (
    FailureAnalysisReport,
    FailureAnalysisSummary,
    FailureCase,
)
from ..domain.rules import highest_severity, infer_area_from_nodeid


class FailureAnalyzer:
    def analyze_pytest_report(self, pytest_report: Dict[str, Any]) -> FailureAnalysisReport:
        failed_cases = self._extract_failed_cases(pytest_report)
        groups = group_failures(failed_cases)

        area_counter = Counter(g.most_affected_area for g in groups)
        most_affected_area = area_counter.most_common(1)[0][0] if area_counter else "unknown_area"
        severities = [g.severity for g in groups]
        summary = FailureAnalysisSummary(
            total_failed=len(failed_cases),
            total_groups=len(groups),
            highest_severity=highest_severity(severities),
            critical_group_count=sum(1 for g in groups if g.severity == "critical"),
            most_affected_area=most_affected_area,
        )

        return FailureAnalysisReport(
            summary=summary,
            groups=groups,
            metadata={
                "source": "pytest_json_report",
                "has_report": bool(pytest_report),
            },
        )

    def _extract_failed_cases(self, pytest_report: Dict[str, Any]) -> List[FailureCase]:
        tests = pytest_report.get("tests", []) or []
        cases: List[FailureCase] = []

        for test in tests:
            outcome = str(test.get("outcome", "")).lower()
            if outcome not in {"failed", "error"}:
                continue
            nodeid = str(test.get("nodeid", "unknown_test"))
            message = self._extract_failure_message(test)
            cases.append(
                FailureCase(
                    nodeid=nodeid,
                    outcome=outcome,
                    message=message,
                    module_path=module_family_from_nodeid(nodeid),
                    raw=test if isinstance(test, dict) else {},
                )
            )

        # Fallback when plugin summary reports failures but test list is empty.
        if not cases:
            summary = pytest_report.get("summary", {}) or {}
            failed = int(summary.get("failed", 0)) + int(summary.get("error", 0))
            if failed > 0:
                fallback_message = str(pytest_report.get("internal_error") or "pytest failure details unavailable")
                for idx in range(failed):
                    nodeid = f"unknown::failure_{idx + 1}"
                    cases.append(
                        FailureCase(
                            nodeid=nodeid,
                            outcome="error",
                            message=fallback_message,
                            module_path=infer_area_from_nodeid(nodeid),
                            raw={},
                        )
                    )
        return cases

    @staticmethod
    def _extract_failure_message(test: Dict[str, Any]) -> str:
        for phase in ("call", "setup", "teardown"):
            phase_data = test.get(phase, {}) or {}
            crash = phase_data.get("crash", {}) or {}
            message = crash.get("message")
            if message:
                return str(message)
            longrepr = phase_data.get("longrepr")
            if isinstance(longrepr, str) and longrepr.strip():
                return longrepr.strip().splitlines()[-1]
        longrepr = test.get("longrepr")
        if isinstance(longrepr, str) and longrepr.strip():
            return longrepr.strip().splitlines()[-1]
        return "failure details unavailable"

    @staticmethod
    def to_dict(report: FailureAnalysisReport) -> Dict[str, Any]:
        return asdict(report)

