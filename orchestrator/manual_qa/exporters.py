"""JSON and Markdown exporters for Manual QA models."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from orchestrator.manual_qa.models import (
    APITestScriptDraft,
    AutomationCandidate,
    BugDraft,
    Evidence,
    ExportBundle,
    FailureRecord,
    FailureSignature,
    RunSummary,
    ScriptGenerationGap,
    ScriptGenerationReadiness,
    TestRun,
    TestSuite,
)


class ManualQAExporter:
    """Export Manual QA content as JSON or Markdown."""

    def export_json_string(
        self,
        payload: ExportBundle | TestSuite | TestRun | RunSummary | Evidence | BugDraft | FailureSignature | FailureRecord | AutomationCandidate | ScriptGenerationGap | ScriptGenerationReadiness | APITestScriptDraft | list[FailureRecord] | list[AutomationCandidate] | list[ScriptGenerationReadiness] | list[APITestScriptDraft],
    ) -> str:
        if isinstance(payload, list):
            return json.dumps([item.to_dict() for item in payload], indent=2, ensure_ascii=False, sort_keys=True)
        return json.dumps(payload.to_dict(), indent=2, ensure_ascii=False, sort_keys=True)

    def export_json_file(
        self,
        payload: ExportBundle | TestSuite | TestRun | RunSummary | Evidence | BugDraft | FailureSignature | FailureRecord | AutomationCandidate | ScriptGenerationGap | ScriptGenerationReadiness | APITestScriptDraft | list[FailureRecord] | list[AutomationCandidate] | list[ScriptGenerationReadiness] | list[APITestScriptDraft],
        path: Path | str,
    ) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.export_json_string(payload), encoding="utf-8")
        return output_path

    def export_markdown_string(
        self,
        payload: ExportBundle | TestSuite | TestRun | RunSummary | Evidence | BugDraft | FailureSignature | FailureRecord | AutomationCandidate | ScriptGenerationGap | ScriptGenerationReadiness | APITestScriptDraft | list[FailureRecord] | list[AutomationCandidate] | list[ScriptGenerationReadiness] | list[APITestScriptDraft],
        *,
        title: Optional[str] = None,
    ) -> str:
        if isinstance(payload, list):
            if not payload:
                return f"# {title or 'Export'}\n"
            first_item = payload[0]
            if isinstance(first_item, FailureRecord):
                return self._export_failure_record_list_markdown(payload, title=title)
            if isinstance(first_item, ScriptGenerationReadiness):
                return self._export_script_readiness_list_markdown(payload, title=title)
            if isinstance(first_item, APITestScriptDraft):
                return self._export_api_script_draft_list_markdown(payload, title=title)
            return self._export_automation_candidate_list_markdown(payload, title=title)
        if isinstance(payload, ExportBundle):
            return self._export_bundle_markdown(payload, title=title)
        if isinstance(payload, TestSuite):
            return self._export_suite_markdown(payload, title=title)
        if isinstance(payload, TestRun):
            return self._export_run_markdown(payload, title=title)
        if isinstance(payload, Evidence):
            return self._export_evidence_markdown(payload, title=title)
        if isinstance(payload, BugDraft):
            return self._export_bug_draft_markdown(payload, title=title)
        if isinstance(payload, FailureSignature):
            return self._export_failure_signature_markdown(payload, title=title)
        if isinstance(payload, FailureRecord):
            return self._export_failure_record_markdown(payload, title=title)
        if isinstance(payload, ScriptGenerationGap):
            return self._export_script_gap_markdown(payload, title=title)
        if isinstance(payload, ScriptGenerationReadiness):
            return self._export_script_readiness_markdown(payload, title=title)
        if isinstance(payload, APITestScriptDraft):
            return self._export_api_script_draft_markdown(payload, title=title)
        if isinstance(payload, AutomationCandidate):
            return self._export_automation_candidate_markdown(payload, title=title)
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

    def _export_evidence_markdown(
        self,
        evidence: Evidence,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Evidence - {evidence.evidence_id}"
        lines = [
            f"# {heading}",
            "",
            "## Evidence",
            f"- Evidence ID: {evidence.evidence_id}",
            f"- Run ID: {evidence.run_id}",
            f"- Test Case ID: {evidence.test_case_id}",
            f"- Type: {evidence.evidence_type or 'N/A'}",
            f"- Reference: {evidence.path_or_url or 'N/A'}",
            f"- Description: {evidence.description or 'N/A'}",
            f"- Content Type: {evidence.content_type or 'N/A'}",
            f"- Created At: {evidence.created_at or 'N/A'}",
            "",
        ]
        return "\n".join(lines)

    def _export_bug_draft_markdown(
        self,
        bug_draft: BugDraft,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Bug Draft - {bug_draft.bug_id}"
        steps = bug_draft.steps_to_reproduce or ["No explicit steps provided."]
        evidence_ids = bug_draft.evidence_ids or ["None"]
        lines = [
            f"# {heading}",
            "",
            "## Title",
            bug_draft.title,
            "",
            "## Test Case ID",
            bug_draft.test_case_id,
            "",
            "## Severity",
            bug_draft.severity,
            "",
            "## Priority",
            bug_draft.priority,
            "",
            "## Environment",
            bug_draft.environment or "N/A",
            "",
            "## Build",
            bug_draft.build or "N/A",
            "",
            "## Steps to Reproduce",
        ]
        for step in steps:
            lines.append(f"- {step}")
        lines.extend(
            [
                "",
                "## Expected Result",
                bug_draft.expected_result or "N/A",
                "",
                "## Actual Result",
                bug_draft.actual_result or "N/A",
                "",
                "## Evidence IDs",
            ]
        )
        for evidence_id in evidence_ids:
            lines.append(f"- {evidence_id}")
        lines.extend(
            [
                "",
                "## Status",
                bug_draft.status,
                "",
            ]
        )
        return "\n".join(lines)

    def _export_failure_signature_markdown(
        self,
        signature: FailureSignature,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Failure Signature - {signature.signature_id}"
        lines = [
            f"# {heading}",
            "",
            "## Signature",
            f"- Signature ID: {signature.signature_id}",
            f"- Fingerprint: {signature.fingerprint}",
            f"- Module: {signature.module or 'N/A'}",
            f"- Test Case ID: {signature.test_case_id or 'N/A'}",
            f"- Title: {signature.title or 'N/A'}",
            f"- Symptom: {signature.symptom or 'N/A'}",
            f"- Expected Result: {signature.expected_result or 'N/A'}",
            f"- Actual Result: {signature.actual_result or 'N/A'}",
            f"- Environment: {signature.environment or 'N/A'}",
            f"- Build: {signature.build or 'N/A'}",
            f"- Severity: {signature.severity or 'N/A'}",
            f"- Priority: {signature.priority or 'N/A'}",
            f"- Source Bug ID: {signature.source_bug_id or 'N/A'}",
            "",
        ]
        return "\n".join(lines)

    def _export_failure_record_markdown(
        self,
        record: FailureRecord,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Failure Record - {record.record_id}"
        signature = record.signature
        lines = [
            f"# {heading}",
            "",
            "## Failure Record",
            f"- Record ID: {record.record_id}",
            f"- Signature ID: {signature.signature_id}",
            f"- Fingerprint: {signature.fingerprint}",
            f"- Module: {signature.module or 'N/A'}",
            f"- Test Case ID: {signature.test_case_id or 'N/A'}",
            f"- Title: {signature.title or 'N/A'}",
            f"- Symptom: {signature.symptom or 'N/A'}",
            f"- Expected Result: {signature.expected_result or 'N/A'}",
            f"- Actual Result: {signature.actual_result or 'N/A'}",
            f"- Severity: {signature.severity or 'N/A'}",
            f"- Priority: {signature.priority or 'N/A'}",
            f"- Occurrence Count: {record.occurrence_count}",
            f"- Related Bug IDs: {', '.join(record.related_bug_ids) if record.related_bug_ids else 'None'}",
            f"- Related Run IDs: {', '.join(record.related_run_ids) if record.related_run_ids else 'None'}",
            f"- Related Test Case IDs: {', '.join(record.related_test_case_ids) if record.related_test_case_ids else 'None'}",
            "",
        ]
        return "\n".join(lines)

    def _export_failure_record_list_markdown(
        self,
        records: list[FailureRecord],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "Failure Records"
        lines = [f"# {heading}", ""]
        for record in records:
            lines.extend(
                [
                    f"## {record.record_id}",
                    f"- Signature ID: {record.signature.signature_id}",
                    f"- Fingerprint: {record.signature.fingerprint}",
                    f"- Occurrence Count: {record.occurrence_count}",
                    f"- Actual Result: {record.signature.actual_result or 'N/A'}",
                    f"- Related Bug IDs: {', '.join(record.related_bug_ids) if record.related_bug_ids else 'None'}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_automation_candidate_markdown(
        self,
        candidate: AutomationCandidate,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Automation Candidate - {candidate.candidate_id}"
        reasons = candidate.reasons or ["None"]
        blockers = candidate.blockers or ["None"]
        related_records = candidate.related_failure_record_ids or ["None"]
        lines = [
            f"# {heading}",
            "",
            "## Candidate",
            f"- Candidate ID: {candidate.candidate_id}",
            f"- Test Case ID: {candidate.test_case_id}",
            f"- Module: {candidate.module or 'N/A'}",
            f"- Title: {candidate.title or 'N/A'}",
            f"- Score: {candidate.score}",
            f"- Recommendation: {candidate.recommendation}",
            f"- Suggested Automation Type: {candidate.suggested_automation_type}",
            "",
            "## Reasons",
        ]
        for reason in reasons:
            lines.append(f"- {reason}")
        lines.extend(["", "## Blockers"])
        for blocker in blockers:
            lines.append(f"- {blocker}")
        lines.extend(["", "## Related Failure Record IDs"])
        for record_id in related_records:
            lines.append(f"- {record_id}")
        lines.append("")
        return "\n".join(lines)

    def _export_automation_candidate_list_markdown(
        self,
        candidates: list[AutomationCandidate],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "Automation Candidates"
        lines = [f"# {heading}", ""]
        for candidate in candidates:
            lines.extend(
                [
                    f"## {candidate.candidate_id}",
                    f"- Test Case ID: {candidate.test_case_id}",
                    f"- Score: {candidate.score}",
                    f"- Recommendation: {candidate.recommendation}",
                    f"- Suggested Automation Type: {candidate.suggested_automation_type}",
                    f"- Reasons: {', '.join(candidate.reasons) if candidate.reasons else 'None'}",
                    f"- Blockers: {', '.join(candidate.blockers) if candidate.blockers else 'None'}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_script_gap_markdown(
        self,
        gap: ScriptGenerationGap,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Script Readiness Gap - {gap.gap_id}"
        lines = [
            f"# {heading}",
            "",
            "## Gap",
            f"- Gap ID: {gap.gap_id}",
            f"- Test Case ID: {gap.test_case_id}",
            f"- Gap Type: {gap.gap_type}",
            f"- Severity: {gap.severity}",
            f"- Message: {gap.message}",
            f"- Recommendation: {gap.recommendation}",
            "",
        ]
        return "\n".join(lines)

    def _export_script_readiness_markdown(
        self,
        readiness: ScriptGenerationReadiness,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Script Readiness - {readiness.readiness_id}"
        strengths = readiness.strengths or ["None"]
        gaps = readiness.gaps or []
        lines = [
            f"# {heading}",
            "",
            "## Readiness",
            f"- Readiness ID: {readiness.readiness_id}",
            f"- Test Case ID: {readiness.test_case_id}",
            f"- Module: {readiness.module or 'N/A'}",
            f"- Title: {readiness.title or 'N/A'}",
            f"- Target Type: {readiness.target_type}",
            f"- Readiness Status: {readiness.readiness_status}",
            f"- Readiness Score: {readiness.readiness_score}",
            f"- Automation Candidate ID: {readiness.automation_candidate_id or 'N/A'}",
            "",
            "## Strengths",
        ]
        for strength in strengths:
            lines.append(f"- {strength}")
        lines.extend(["", "## Gaps"])
        if not gaps:
            lines.append("- None")
        for gap in gaps:
            lines.append(
                f"- {gap.gap_id} [{gap.severity}] {gap.gap_type}: {gap.message} | Recommendation: {gap.recommendation}"
            )
        lines.extend(
            [
                "",
                "## Suggested Next Step",
                readiness.suggested_next_step or "N/A",
                "",
            ]
        )
        return "\n".join(lines)

    def _export_script_readiness_list_markdown(
        self,
        items: list[ScriptGenerationReadiness],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "Script Readiness Report"
        lines = [f"# {heading}", ""]
        for item in items:
            lines.extend(
                [
                    f"## {item.readiness_id}",
                    f"- Test Case ID: {item.test_case_id}",
                    f"- Target Type: {item.target_type}",
                    f"- Readiness Status: {item.readiness_status}",
                    f"- Readiness Score: {item.readiness_score}",
                    f"- Strengths: {', '.join(item.strengths) if item.strengths else 'None'}",
                    f"- Gaps: {', '.join(gap.gap_type for gap in item.gaps) if item.gaps else 'None'}",
                    f"- Suggested Next Step: {item.suggested_next_step}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _export_api_script_draft_markdown(
        self,
        draft: APITestScriptDraft,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"API Script Draft - {draft.draft_id}"
        warnings = draft.warnings or ["None"]
        assumptions = draft.assumptions or ["None"]
        lines = [
            f"# {heading}",
            "",
            "## Draft",
            f"- Draft ID: {draft.draft_id}",
            f"- Test Case ID: {draft.test_case_id}",
            f"- Requirement IDs: {', '.join(draft.requirement_ids) if draft.requirement_ids else 'None'}",
            f"- Title: {draft.title or 'N/A'}",
            f"- Readiness ID: {draft.readiness_id or 'N/A'}",
            f"- Framework: {draft.framework}",
            f"- Language: {draft.language}",
            f"- File Name: {draft.file_name}",
            f"- Status: {draft.status}",
            "",
            "## Warnings",
        ]
        for item in warnings:
            lines.append(f"- {item}")
        lines.extend(["", "## Assumptions"])
        for item in assumptions:
            lines.append(f"- {item}")
        lines.extend(["", "## Script Content", "```python", draft.script_content, "```", ""])
        return "\n".join(lines)

    def _export_api_script_draft_list_markdown(
        self,
        drafts: list[APITestScriptDraft],
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or "API Script Drafts"
        lines = [f"# {heading}", ""]
        for draft in drafts:
            lines.extend(
                [
                    f"## {draft.draft_id}",
                    f"- Test Case ID: {draft.test_case_id}",
                    f"- Readiness ID: {draft.readiness_id or 'N/A'}",
                    f"- File Name: {draft.file_name}",
                    f"- Status: {draft.status}",
                    f"- Warnings: {', '.join(draft.warnings) if draft.warnings else 'None'}",
                    "",
                ]
            )
        return "\n".join(lines)

    def export_markdown_file(
        self,
        payload: ExportBundle | TestSuite | TestRun | RunSummary | Evidence | BugDraft | FailureSignature | FailureRecord | AutomationCandidate | ScriptGenerationGap | ScriptGenerationReadiness | APITestScriptDraft | list[FailureRecord] | list[AutomationCandidate] | list[ScriptGenerationReadiness] | list[APITestScriptDraft],
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


def export_evidence_to_json_string(evidence: Evidence) -> str:
    return ManualQAExporter().export_json_string(evidence)


def export_evidence_to_json_file(evidence: Evidence, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(evidence, path)


def export_evidence_to_markdown_string(evidence: Evidence, *, title: Optional[str] = None) -> str:
    return ManualQAExporter().export_markdown_string(evidence, title=title)


def export_evidence_to_markdown_file(
    evidence: Evidence,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(evidence, path, title=title)


def export_bug_draft_to_json_string(bug_draft: BugDraft) -> str:
    return ManualQAExporter().export_json_string(bug_draft)


def export_bug_draft_to_json_file(bug_draft: BugDraft, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(bug_draft, path)


def export_bug_draft_to_markdown_string(
    bug_draft: BugDraft,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(bug_draft, title=title)


def export_bug_draft_to_markdown_file(
    bug_draft: BugDraft,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(bug_draft, path, title=title)


def export_failure_signature_to_json_string(signature: FailureSignature) -> str:
    return ManualQAExporter().export_json_string(signature)


def export_failure_signature_to_json_file(signature: FailureSignature, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(signature, path)


def export_failure_signature_to_markdown_string(
    signature: FailureSignature,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(signature, title=title)


def export_failure_signature_to_markdown_file(
    signature: FailureSignature,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(signature, path, title=title)


def export_failure_record_to_json_string(record: FailureRecord) -> str:
    return ManualQAExporter().export_json_string(record)


def export_failure_record_to_json_file(record: FailureRecord, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(record, path)


def export_failure_record_to_markdown_string(
    record: FailureRecord,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(record, title=title)


def export_failure_record_to_markdown_file(
    record: FailureRecord,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(record, path, title=title)


def export_failure_records_to_json_string(records: list[FailureRecord]) -> str:
    return ManualQAExporter().export_json_string(records)


def export_failure_records_to_json_file(records: list[FailureRecord], path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(records, path)


def export_failure_records_to_markdown_string(
    records: list[FailureRecord],
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(records, title=title)


def export_failure_records_to_markdown_file(
    records: list[FailureRecord],
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(records, path, title=title)


def export_automation_candidate_to_json_string(candidate: AutomationCandidate) -> str:
    return ManualQAExporter().export_json_string(candidate)


def export_automation_candidate_to_json_file(candidate: AutomationCandidate, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(candidate, path)


def export_automation_candidate_to_markdown_string(
    candidate: AutomationCandidate,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(candidate, title=title)


def export_automation_candidate_to_markdown_file(
    candidate: AutomationCandidate,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(candidate, path, title=title)


def export_automation_candidates_to_json_string(candidates: list[AutomationCandidate]) -> str:
    return ManualQAExporter().export_json_string(candidates)


def export_automation_candidates_to_json_file(candidates: list[AutomationCandidate], path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(candidates, path)


def export_automation_candidates_to_markdown_string(
    candidates: list[AutomationCandidate],
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(candidates, title=title)


def export_automation_candidates_to_markdown_file(
    candidates: list[AutomationCandidate],
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(candidates, path, title=title)


def export_script_gap_to_json_string(gap: ScriptGenerationGap) -> str:
    return ManualQAExporter().export_json_string(gap)


def export_script_gap_to_json_file(gap: ScriptGenerationGap, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(gap, path)


def export_script_gap_to_markdown_string(
    gap: ScriptGenerationGap,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(gap, title=title)


def export_script_gap_to_markdown_file(
    gap: ScriptGenerationGap,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(gap, path, title=title)


def export_script_readiness_to_json_string(readiness: ScriptGenerationReadiness) -> str:
    return ManualQAExporter().export_json_string(readiness)


def export_script_readiness_to_json_file(readiness: ScriptGenerationReadiness, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(readiness, path)


def export_script_readiness_to_markdown_string(
    readiness: ScriptGenerationReadiness,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(readiness, title=title)


def export_script_readiness_to_markdown_file(
    readiness: ScriptGenerationReadiness,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(readiness, path, title=title)


def export_script_readiness_list_to_json_string(items: list[ScriptGenerationReadiness]) -> str:
    return ManualQAExporter().export_json_string(items)


def export_script_readiness_list_to_json_file(items: list[ScriptGenerationReadiness], path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(items, path)


def export_script_readiness_list_to_markdown_string(
    items: list[ScriptGenerationReadiness],
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(items, title=title)


def export_script_readiness_list_to_markdown_file(
    items: list[ScriptGenerationReadiness],
    path: Path | str,
    *,
    title: Optional[str] = None,
    ) -> Path:
        return ManualQAExporter().export_markdown_file(items, path, title=title)


def export_api_script_draft_to_json_string(draft: APITestScriptDraft) -> str:
    return ManualQAExporter().export_json_string(draft)


def export_api_script_draft_to_json_file(draft: APITestScriptDraft, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(draft, path)


def export_api_script_draft_to_markdown_string(
    draft: APITestScriptDraft,
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(draft, title=title)


def export_api_script_draft_to_markdown_file(
    draft: APITestScriptDraft,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(draft, path, title=title)


def export_api_script_drafts_to_json_string(drafts: list[APITestScriptDraft]) -> str:
    return ManualQAExporter().export_json_string(drafts)


def export_api_script_drafts_to_json_file(drafts: list[APITestScriptDraft], path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(drafts, path)


def export_api_script_drafts_to_markdown_string(
    drafts: list[APITestScriptDraft],
    *,
    title: Optional[str] = None,
) -> str:
    return ManualQAExporter().export_markdown_string(drafts, title=title)


def export_api_script_drafts_to_markdown_file(
    drafts: list[APITestScriptDraft],
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(drafts, path, title=title)


def export_api_script_draft_to_python_file(draft: APITestScriptDraft, path: Path | str) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(draft.script_content, encoding="utf-8")
    return output_path
