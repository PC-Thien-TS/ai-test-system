from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from ..domain.grouping import extract_module_family, group_failures
from ..domain.models import (
    FailureAnalysisReport,
    FailureAnalysisSummary,
    FailureCase,
    max_severity,
    utc_now_iso,
)
from ..domain.rules import infer_failure


class FailureAnalyzer:
    """Deterministic analyzer for pytest-json-report failure payloads."""

    def analyze_pytest_report(
        self,
        report: Mapping[str, Any],
        *,
        source_report_path: str = "",
    ) -> FailureAnalysisReport:
        failed_cases = self._extract_failed_cases(report)
        groups = group_failures(failed_cases, infer=infer_failure)
        summary = self._build_summary(groups=groups, failed_count=len(failed_cases))
        return FailureAnalysisReport(
            generated_at_utc=utc_now_iso(),
            source_report_path=source_report_path,
            summary=summary,
            groups=groups,
            metadata={"report_summary": dict(report.get("summary", {}) or {})},
        )

    def analyze_pytest_report_file(
        self,
        report_path: Path,
        *,
        output_path: Path | None = None,
    ) -> FailureAnalysisReport:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        analysis = self.analyze_pytest_report(payload, source_report_path=str(report_path))
        if output_path is not None:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(analysis.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return analysis

    def _extract_failed_cases(self, report: Mapping[str, Any]) -> List[FailureCase]:
        tests = report.get("tests", []) or []
        failed: list[FailureCase] = []
        for idx, test_item in enumerate(tests, start=1):
            if not isinstance(test_item, Mapping):
                continue
            nodeid = str(test_item.get("nodeid", f"unknown::test_{idx}"))
            outcome = str(test_item.get("outcome", "unknown"))
            failed_stage = self._resolve_failed_stage(test_item)
            if outcome not in {"failed", "error"} and failed_stage is None:
                continue

            message, longrepr = self._extract_failure_message(test_item, failed_stage)
            if not message:
                message = "unknown failure"
            failed.append(
                FailureCase(
                    nodeid=nodeid,
                    outcome=outcome if outcome in {"failed", "error"} else "failed",
                    message=message,
                    longrepr=longrepr,
                    module_family=extract_module_family(nodeid),
                    metadata={"failed_stage": failed_stage or outcome},
                )
            )

        # Fallback for reports that only provide summary counts.
        summary_failed = int((report.get("summary", {}) or {}).get("failed", 0))
        if summary_failed > len(failed):
            missing = summary_failed - len(failed)
            for i in range(missing):
                nodeid = f"unknown::failure_{i + 1}"
                failed.append(
                    FailureCase(
                        nodeid=nodeid,
                        outcome="failed",
                        message="unknown failure pattern from summary-only report",
                        longrepr="",
                        module_family="unknown",
                    )
                )

        return failed

    def _resolve_failed_stage(self, test_item: Mapping[str, Any]) -> str | None:
        for stage in ("call", "setup", "teardown"):
            payload = test_item.get(stage)
            if isinstance(payload, Mapping) and str(payload.get("outcome", "")).lower() in {"failed", "error"}:
                return stage
        return None

    def _extract_failure_message(self, test_item: Mapping[str, Any], failed_stage: str | None) -> tuple[str, str]:
        candidate_stages = [failed_stage] if failed_stage else []
        candidate_stages.extend(["call", "setup", "teardown"])

        seen: set[str] = set()
        for stage in candidate_stages:
            if not stage or stage in seen:
                continue
            seen.add(stage)
            payload = test_item.get(stage)
            if not isinstance(payload, Mapping):
                continue

            crash = payload.get("crash")
            if isinstance(crash, Mapping):
                message = str(crash.get("message", "")).strip()
                if message:
                    longrepr = self._to_text(payload.get("longrepr"))
                    return message, longrepr

            longrepr = self._to_text(payload.get("longrepr"))
            if longrepr:
                first_line = longrepr.splitlines()[0].strip() or longrepr[:280].strip()
                return first_line, longrepr

        test_longrepr = self._to_text(test_item.get("longrepr"))
        if test_longrepr:
            first_line = test_longrepr.splitlines()[0].strip() or test_longrepr[:280].strip()
            return first_line, test_longrepr

        return "", ""

    def _to_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (list, tuple)):
            return "\n".join(self._to_text(part) for part in value if part is not None).strip()
        if isinstance(value, Mapping):
            # pytest-json-report may store structured longrepr; compact json keeps deterministic text.
            try:
                return json.dumps(value, ensure_ascii=False, sort_keys=True)
            except TypeError:
                return str(value).strip()
        return str(value).strip()

    def _build_summary(self, *, groups: Iterable, failed_count: int) -> FailureAnalysisSummary:
        group_list = list(groups)
        highest = "low"
        critical_group_count = 0
        top_categories: Counter[str] = Counter()
        area_counter: Counter[str] = Counter()

        for group in group_list:
            highest = max_severity(highest, group.severity)
            if group.severity == "critical":
                critical_group_count += 1
            top_categories[group.category] += group.count
            area_counter[group.module_family] += group.count

        most_affected_area = "unknown"
        if area_counter:
            most_affected_area = area_counter.most_common(1)[0][0]

        return FailureAnalysisSummary(
            total_failed=failed_count,
            total_groups=len(group_list),
            highest_severity=highest if group_list else "low",
            critical_group_count=critical_group_count,
            most_affected_area=most_affected_area,
            top_categories=dict(top_categories.most_common(5)),
        )
