"""JSON and Markdown exporters for Manual QA models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from orchestrator.manual_qa.models import ExportBundle, RunSummary, TestRun, TestSuite


class ManualQAExporter:
    """Export Manual QA content as JSON or Markdown."""

    def export_json_string(self, payload: ExportBundle | TestSuite | TestRun | RunSummary) -> str:
        return json.dumps(payload.to_dict(), indent=2, ensure_ascii=False, sort_keys=True)

    def export_json_file(
        self,
        payload: ExportBundle | TestSuite | TestRun | RunSummary,
        path: Path | str,
    ) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.export_json_string(payload), encoding="utf-8")
        return output_path

    def export_markdown_string(
        self,
        payload: ExportBundle | TestSuite | TestRun | RunSummary,
        *,
        title: Optional[str] = None,
    ) -> str:
        if isinstance(payload, ExportBundle):
            return self._export_bundle_markdown(payload, title=title)
        if isinstance(payload, TestSuite):
            return self._export_suite_markdown(payload, title=title)
        if isinstance(payload, TestRun):
            return self._export_run_markdown(payload, title=title)
        return self._export_summary_markdown(payload, title=title)

    def _export_bundle_markdown(
        self,
        bundle: ExportBundle,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Manual QA Export - {bundle.project.name}"
        lines = [
            f"# {heading}",
            "",
            "## Project",
            f"- Project ID: {bundle.project.project_id}",
            f"- Name: {bundle.project.name}",
            f"- Product Type: {bundle.project.product_type}",
            "",
            "## Requirements",
        ]

        for requirement in bundle.requirements:
            lines.extend(
                [
                    f"- {requirement.requirement_id}: {requirement.title}",
                    f"  Module: {requirement.module}",
                    f"  Priority: {requirement.priority}",
                ]
            )

        lines.extend(["", "## Checklist"])
        for item in bundle.checklist_items:
            lines.extend(
                [
                    f"- {item.checklist_id} [{item.requirement_id}] {item.title}",
                    f"  Priority: {item.priority}",
                    f"  Description: {item.description}",
                ]
            )

        lines.extend(["", "## Manual Test Cases"])
        for case in bundle.test_cases:
            lines.extend(
                [
                    f"- {case.test_case_id} [{', '.join(case.requirement_ids)}] {case.title}",
                    f"  Type: {case.test_type}",
                    f"  Status: {case.status}",
                    f"  Expected: {case.expected_result}",
                ]
            )

        lines.append("")
        return "\n".join(lines)

    def _export_suite_markdown(
        self,
        suite: TestSuite,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Manual Test Suite - {suite.name}"
        lines = [
            f"# {heading}",
            "",
            "## Suite",
            f"- Suite ID: {suite.suite_id}",
            f"- Project ID: {suite.project_id}",
            f"- Name: {suite.name}",
            f"- Scope: {suite.scope or 'N/A'}",
            f"- Owner: {suite.owner or 'N/A'}",
            "",
            "## Test Cases",
        ]
        for test_case_id in suite.test_case_ids:
            lines.append(f"- {test_case_id}")
        lines.append("")
        return "\n".join(lines)

    def _export_run_markdown(
        self,
        test_run: TestRun,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Manual Test Run - {test_run.run_id}"
        lines = [
            f"# {heading}",
            "",
            "## Run",
            f"- Run ID: {test_run.run_id}",
            f"- Project ID: {test_run.project_id}",
            f"- Suite ID: {test_run.suite_id}",
            f"- Environment: {test_run.environment or 'N/A'}",
            f"- Build: {test_run.build or 'N/A'}",
            f"- Tester: {test_run.tester or 'N/A'}",
            f"- Status: {test_run.status}",
            "",
            "## Results",
        ]
        for result in test_run.results:
            lines.extend(
                [
                    f"- {result.result_id} [{result.test_case_id}] {result.status}",
                    f"  Actual: {result.actual_result or 'N/A'}",
                    f"  Notes: {result.notes or 'N/A'}",
                ]
            )
        lines.append("")
        return "\n".join(lines)

    def _export_summary_markdown(
        self,
        summary: RunSummary,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Manual Test Run Summary - {summary.run_id}"
        lines = [
            f"# {heading}",
            "",
            "## Summary",
            f"- Run ID: {summary.run_id}",
            f"- Status: {summary.status}",
            f"- Total: {summary.total}",
            f"- Passed: {summary.passed}",
            f"- Failed: {summary.failed}",
            f"- Blocked: {summary.blocked}",
            f"- Skipped: {summary.skipped}",
            f"- Not Run: {summary.not_run}",
            f"- Retest: {summary.retest}",
            f"- Pass Rate: {summary.pass_rate}%",
            "",
        ]
        return "\n".join(lines)

    def export_markdown_file(
        self,
        payload: ExportBundle | TestSuite | TestRun | RunSummary,
        path: Path | str,
        *,
        title: Optional[str] = None,
    ) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.export_markdown_string(payload, title=title), encoding="utf-8")
        return output_path


def export_bundle_to_json_string(bundle: ExportBundle) -> str:
    return ManualQAExporter().export_json_string(bundle)


def export_bundle_to_json_file(bundle: ExportBundle, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(bundle, path)


def export_bundle_to_markdown_string(bundle: ExportBundle, *, title: Optional[str] = None) -> str:
    return ManualQAExporter().export_markdown_string(bundle, title=title)


def export_bundle_to_markdown_file(
    bundle: ExportBundle,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(bundle, path, title=title)


def export_suite_to_json_string(suite: TestSuite) -> str:
    return ManualQAExporter().export_json_string(suite)


def export_suite_to_json_file(suite: TestSuite, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(suite, path)


def export_suite_to_markdown_string(suite: TestSuite, *, title: Optional[str] = None) -> str:
    return ManualQAExporter().export_markdown_string(suite, title=title)


def export_suite_to_markdown_file(
    suite: TestSuite,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(suite, path, title=title)


def export_run_to_json_string(test_run: TestRun) -> str:
    return ManualQAExporter().export_json_string(test_run)


def export_run_to_json_file(test_run: TestRun, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(test_run, path)


def export_run_to_markdown_string(test_run: TestRun, *, title: Optional[str] = None) -> str:
    return ManualQAExporter().export_markdown_string(test_run, title=title)


def export_run_to_markdown_file(
    test_run: TestRun,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(test_run, path, title=title)


def export_summary_to_json_string(summary: RunSummary) -> str:
    return ManualQAExporter().export_json_string(summary)


def export_summary_to_json_file(summary: RunSummary, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(summary, path)


def export_summary_to_markdown_string(summary: RunSummary, *, title: Optional[str] = None) -> str:
    return ManualQAExporter().export_markdown_string(summary, title=title)


def export_summary_to_markdown_file(
    summary: RunSummary,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(summary, path, title=title)
