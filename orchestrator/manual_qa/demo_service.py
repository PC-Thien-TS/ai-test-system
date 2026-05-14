"""Deterministic end-to-end demo workflow for the Manual QA workspace."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.manual_qa.automation_candidate_service import AutomationCandidateService
from orchestrator.manual_qa.bug_service import BugDraftService
from orchestrator.manual_qa.checklist_generator import ChecklistGenerator
from orchestrator.manual_qa.evidence_service import EvidenceService
from orchestrator.manual_qa.exporters import ManualQAExporter
from orchestrator.manual_qa.project_service import ProjectProfileService
from orchestrator.manual_qa.requirement_importer import RequirementImporter
from orchestrator.manual_qa.requirement_normalizer import RequirementNormalizer
from orchestrator.manual_qa.result_service import TestResultService
from orchestrator.manual_qa.run_service import TestRunService
from orchestrator.manual_qa.summary_service import RunSummaryService
from orchestrator.manual_qa.suite_service import TestSuiteService
from orchestrator.manual_qa.testcase_generator import ManualTestCaseGenerator
from orchestrator.manual_qa.workspace_service import ManualQAWorkspaceService


DEMO_REQUIREMENTS_TEXT = "\n".join(
    [
        "## [REQ-001] Login success",
        "Module: Authentication",
        "Priority: High",
        "Acceptance Criteria:",
        "- User reaches the dashboard after valid credentials.",
        "",
        "## [REQ-002] Search rejects empty query",
        "Module: Search",
        "Priority: Medium",
        "Acceptance Criteria:",
        "- Empty query shows a validation message.",
    ]
)


class DemoWorkflowService:
    """Compose the existing Manual QA services into a stable local demo workflow."""

    def __init__(self) -> None:
        self.workspace_service = ManualQAWorkspaceService()
        self.project_service = ProjectProfileService()
        self.importer = RequirementImporter()
        self.normalizer = RequirementNormalizer()
        self.checklist_generator = ChecklistGenerator()
        self.testcase_generator = ManualTestCaseGenerator()
        self.suite_service = TestSuiteService()
        self.run_service = TestRunService()
        self.result_service = TestResultService()
        self.summary_service = RunSummaryService()
        self.evidence_service = EvidenceService()
        self.bug_service = BugDraftService()
        self.automation_service = AutomationCandidateService()
        self.exporter = ManualQAExporter()

    def run_demo_workflow(
        self,
        workspace_path: str | Path,
        project_name: str = "Manual QA Demo",
        product_type: str = "web",
    ) -> dict[str, Any]:
        workspace = self.workspace_service.create_workspace(workspace_path)
        output_files: list[str] = []

        project = self.project_service.create_project_profile(
            name=project_name,
            product_type=product_type,
            description="Deterministic local demo project for the Manual QA workflow.",
            owner="Manual QA CLI",
            metadata={"source": "demo_workflow"},
        )
        project_path = workspace / "project.json"
        self.workspace_service.write_json(project_path, project.to_dict())
        output_files.append(self._relative(workspace, project_path))
        self.workspace_service.update_workspace_manifest(
            workspace,
            project=project,
            metadata={"demo_workflow": True},
        )

        raw_requirements = self.importer.import_requirements(
            DEMO_REQUIREMENTS_TEXT,
            source_ref="built-in-demo",
        )
        requirements = self.normalizer.normalize_requirements(raw_requirements)
        requirements_path = workspace / "requirements" / "normalized_requirements.json"
        self.workspace_service.write_json(
            requirements_path,
            [item.to_dict() for item in requirements],
        )
        output_files.append(self._relative(workspace, requirements_path))

        checklist = self.checklist_generator.generate(requirements)
        checklist_json = workspace / "checklists" / "checklist.json"
        checklist_md = workspace / "checklists" / "checklist.md"
        self.workspace_service.write_json(checklist_json, [item.to_dict() for item in checklist])
        self.workspace_service.write_markdown(
            checklist_md,
            self._render_checklist_markdown(checklist),
        )
        output_files.extend(
            [
                self._relative(workspace, checklist_json),
                self._relative(workspace, checklist_md),
            ]
        )

        test_cases = self.testcase_generator.generate(requirements)
        testcases_json = workspace / "testcases" / "testcases.json"
        testcases_md = workspace / "testcases" / "testcases.md"
        self.workspace_service.write_json(testcases_json, [item.to_dict() for item in test_cases])
        self.workspace_service.write_markdown(
            testcases_md,
            self._render_testcases_markdown(test_cases),
        )
        output_files.extend(
            [
                self._relative(workspace, testcases_json),
                self._relative(workspace, testcases_md),
            ]
        )

        suite = self.suite_service.create_test_suite(
            project_id=project.project_id,
            name="demo-smoke",
            test_cases=[case.test_case_id for case in test_cases],
            scope="demo",
            owner="Manual QA CLI",
        )
        suite_json = workspace / "suites" / "demo-smoke.json"
        suite_md = workspace / "suites" / "demo-smoke.md"
        self.workspace_service.write_json(suite_json, suite.to_dict())
        self.workspace_service.write_markdown(
            suite_md,
            self.exporter.export_markdown_string(suite),
        )
        output_files.extend(
            [
                self._relative(workspace, suite_json),
                self._relative(workspace, suite_md),
            ]
        )

        test_run = self.run_service.create_test_run(
            project_id=project.project_id,
            suite=suite,
            environment="demo-staging",
            build="demo-build-1",
            tester="Manual QA CLI",
        )
        failed_case = test_cases[0]
        updated_run = self.result_service.update_test_result(
            test_run,
            failed_case.test_case_id,
            "Fail",
            actual_result="Login error message is incorrect.",
            notes="Deterministic demo failure.",
        )
        summary = self.summary_service.summarize_test_run(updated_run)
        run_json = workspace / "runs" / f"{updated_run.run_id}.json"
        run_md = workspace / "runs" / f"{updated_run.run_id}.md"
        summary_json = workspace / "runs" / f"{updated_run.run_id}-summary.json"
        summary_md = workspace / "runs" / f"{updated_run.run_id}-summary.md"
        self.workspace_service.write_json(run_json, updated_run.to_dict())
        self.workspace_service.write_markdown(run_md, self.exporter.export_markdown_string(updated_run))
        self.workspace_service.write_json(summary_json, summary.to_dict())
        self.workspace_service.write_markdown(summary_md, self.exporter.export_markdown_string(summary))
        output_files.extend(
            [
                self._relative(workspace, run_json),
                self._relative(workspace, run_md),
                self._relative(workspace, summary_json),
                self._relative(workspace, summary_md),
            ]
        )

        evidence = self.evidence_service.attach_evidence(
            updated_run,
            failed_case.test_case_id,
            "screenshot",
            "evidence/demo_login_error.png",
            description="Demo login failure screenshot",
            content_type="image/png",
        )
        evidence_json = workspace / "evidence" / f"{evidence.evidence_id}.json"
        evidence_md = workspace / "evidence" / f"{evidence.evidence_id}.md"
        self.workspace_service.write_json(run_json, updated_run.to_dict())
        self.workspace_service.write_json(evidence_json, evidence.to_dict())
        self.workspace_service.write_markdown(
            evidence_md,
            self.exporter.export_markdown_string(evidence),
        )
        output_files.extend(
            [
                self._relative(workspace, evidence_json),
                self._relative(workspace, evidence_md),
            ]
        )

        bug = self.bug_service.generate_bug_draft(
            updated_run,
            failed_case.test_case_id,
            test_case=failed_case,
            evidence=[evidence],
        )
        bug_json = workspace / "bugs" / f"{bug.bug_id}.json"
        bug_md = workspace / "bugs" / f"{bug.bug_id}.md"
        self.workspace_service.write_json(bug_json, bug.to_dict())
        self.workspace_service.write_markdown(bug_md, self.exporter.export_markdown_string(bug))
        output_files.extend(
            [
                self._relative(workspace, bug_json),
                self._relative(workspace, bug_md),
            ]
        )

        candidates = self.automation_service.score_automation_candidates(test_cases)
        candidates_json = workspace / "automation_candidates" / "candidates.json"
        candidates_md = workspace / "automation_candidates" / "candidates.md"
        self.workspace_service.write_json(
            candidates_json,
            [item.to_dict() for item in candidates],
        )
        self.workspace_service.write_markdown(
            candidates_md,
            self.exporter.export_markdown_string(candidates),
        )
        output_files.extend(
            [
                self._relative(workspace, candidates_json),
                self._relative(workspace, candidates_md),
            ]
        )

        self.workspace_service.update_workspace_manifest(
            workspace,
            project=project,
            metadata={
                "demo_workflow": True,
                "suite_id": suite.suite_id,
                "run_id": updated_run.run_id,
            },
        )
        validation_result = self.workspace_service.validate_workspace(workspace)

        report = {
            "project_id": project.project_id,
            "requirement_count": len(requirements),
            "checklist_count": len(checklist),
            "test_case_count": len(test_cases),
            "suite_id": suite.suite_id,
            "run_id": updated_run.run_id,
            "failed_case_id": failed_case.test_case_id,
            "evidence_id": evidence.evidence_id,
            "bug_id": bug.bug_id,
            "candidate_count": len(candidates),
            "output_files": output_files,
            "validation_result": validation_result.to_dict(),
            "metadata": {
                "next_recommended_action": "Review the bug draft and triage automation candidates.",
                "product_type": project.product_type,
            },
        }
        report_json = workspace / "reports" / "demo_workflow_report.json"
        report_md = workspace / "reports" / "demo_workflow_report.md"
        self.workspace_service.write_json(report_json, report)
        self.workspace_service.write_markdown(report_md, self._render_demo_report(project, report))
        output_files.extend(
            [
                self._relative(workspace, report_json),
                self._relative(workspace, report_md),
            ]
        )
        report["output_files"] = output_files
        self.workspace_service.write_json(report_json, report)
        self.workspace_service.update_workspace_manifest(
            workspace,
            project=project,
            metadata={"last_demo_report": "reports/demo_workflow_report.json"},
        )
        return report

    def _render_checklist_markdown(self, checklist: list[Any]) -> str:
        lines = ["# Checklist", ""]
        for item in checklist:
            lines.extend(
                [
                    f"- {item.checklist_id} [{item.requirement_id}] {item.title}",
                    f"  Description: {item.description}",
                ]
            )
        lines.append("")
        return "\n".join(lines)

    def _render_testcases_markdown(self, test_cases: list[Any]) -> str:
        lines = ["# Manual Test Cases", ""]
        for case in test_cases:
            lines.extend(
                [
                    f"- {case.test_case_id} [{', '.join(case.requirement_ids)}] {case.title}",
                    f"  Expected: {case.expected_result}",
                ]
            )
        lines.append("")
        return "\n".join(lines)

    def _render_demo_report(self, project: Any, report: dict[str, Any]) -> str:
        validation = report["validation_result"]
        output_files = report["output_files"] + [
            "reports/demo_workflow_report.json",
            "reports/demo_workflow_report.md",
        ]
        lines = [
            "# Demo Workflow Report",
            "",
            "## Project",
            f"- Project ID: {project.project_id}",
            f"- Project Name: {project.name}",
            f"- Product Type: {project.product_type}",
            "",
            "## Counts",
            f"- Requirement Count: {report['requirement_count']}",
            f"- Checklist Count: {report['checklist_count']}",
            f"- Test Case Count: {report['test_case_count']}",
            f"- Automation Candidate Count: {report['candidate_count']}",
            "",
            "## Execution",
            f"- Suite ID: {report['suite_id']}",
            f"- Run ID: {report['run_id']}",
            f"- Failed Case ID: {report['failed_case_id']}",
            f"- Evidence ID: {report['evidence_id']}",
            f"- Bug ID: {report['bug_id']}",
            "",
            "## Workspace Validation",
            f"- Is Valid: {validation['is_valid']}",
            f"- Missing Folders: {', '.join(validation['missing_folders']) or 'None'}",
            f"- Missing Files: {', '.join(validation['missing_files']) or 'None'}",
            "",
            "## Output Files Generated",
        ]
        lines.extend(f"- {path}" for path in output_files)
        lines.extend(
            [
                "",
                "## Next Recommended Action",
                f"- {report['metadata']['next_recommended_action']}",
                "",
            ]
        )
        return "\n".join(lines)

    def _relative(self, workspace: Path, path: Path) -> str:
        return str(path.relative_to(workspace)).replace("\\", "/")


def run_demo_workflow(
    workspace_path: str | Path,
    project_name: str = "Manual QA Demo",
    product_type: str = "web",
) -> dict[str, Any]:
    return DemoWorkflowService().run_demo_workflow(
        workspace_path,
        project_name=project_name,
        product_type=product_type,
    )
