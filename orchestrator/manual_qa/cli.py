"""Thin argparse CLI adapter for Manual QA workflows."""

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from orchestrator.manual_qa.api_execution_sandbox_service import (
    APIExecutionSandboxService,
)
from orchestrator.manual_qa.api_execution_evidence_service import (
    APIExecutionEvidenceService,
)
from orchestrator.manual_qa.api_script_generator import APITestScriptGenerator
from orchestrator.manual_qa.api_script_packaging_service import APIScriptPackagingService
from orchestrator.manual_qa.api_script_validation_service import APIScriptValidationService
from orchestrator.manual_qa.automation_candidate_service import AutomationCandidateService
from orchestrator.manual_qa.bug_service import BugDraftService
from orchestrator.manual_qa.checklist_generator import ChecklistGenerator
from orchestrator.manual_qa.demo_service import DemoWorkflowService
from orchestrator.manual_qa.draft_package_dashboard_service import (
    UnifiedDraftPackageDashboardService,
)
from orchestrator.manual_qa.evidence_service import EvidenceService
from orchestrator.manual_qa.execution_preflight_service import (
    ExecutionPreflightService,
)
from orchestrator.manual_qa.execution_safety_service import (
    ExecutionSafetyService,
)
from orchestrator.manual_qa.exporters import ManualQAExporter
from orchestrator.manual_qa.failure_memory_service import FailureRecord, FailureSignature
from orchestrator.manual_qa.models import (
    APIScriptPackageManifest,
    APIScriptValidationIssue,
    APIScriptValidationResult,
    APITestScriptDraft,
    AutomationCandidate,
    BugDraft,
    ChecklistItem,
    Evidence,
    ManualTestCase,
    NormalizedRequirement,
    ProjectProfile,
    RunSummary,
    ScriptGenerationReadiness,
    TestResult,
    TestRun,
    TestSuite,
    WebPlaywrightPackageManifest,
    WebPlaywrightReadiness,
    WebPlaywrightScriptDraft,
    WebPlaywrightValidationIssue,
    WebPlaywrightValidationResult,
)
from orchestrator.manual_qa.project_service import ProjectProfileService
from orchestrator.manual_qa.requirement_importer import RequirementImporter
from orchestrator.manual_qa.requirement_normalizer import RequirementNormalizer
from orchestrator.manual_qa.result_service import TestResultService
from orchestrator.manual_qa.run_service import TestRunService
from orchestrator.manual_qa.summary_service import RunSummaryService
from orchestrator.manual_qa.suite_service import TestSuiteService
from orchestrator.manual_qa.script_readiness_service import ScriptReadinessService
from orchestrator.manual_qa.testcase_generator import ManualTestCaseGenerator
from orchestrator.manual_qa.web_playwright_packaging_service import WebPlaywrightPackagingService
from orchestrator.manual_qa.web_playwright_readiness_service import WebPlaywrightReadinessService
from orchestrator.manual_qa.web_playwright_script_generator import WebPlaywrightScriptGenerator
from orchestrator.manual_qa.web_playwright_validation_service import WebPlaywrightValidationService
from orchestrator.manual_qa.workspace_service import ManualQAWorkspaceService


class ManualQACLI:
    """Thin file-based CLI orchestrating existing Manual QA services."""

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
        self.api_script_generator = APITestScriptGenerator()
        self.api_script_validation_service = APIScriptValidationService()
        self.api_script_packaging_service = APIScriptPackagingService()
        self.script_readiness_service = ScriptReadinessService()
        self.web_playwright_readiness_service = WebPlaywrightReadinessService()
        self.web_playwright_script_generator = WebPlaywrightScriptGenerator()
        self.web_playwright_validation_service = WebPlaywrightValidationService()
        self.web_playwright_packaging_service = WebPlaywrightPackagingService()
        self.draft_package_dashboard_service = UnifiedDraftPackageDashboardService()
        self.execution_safety_service = ExecutionSafetyService()
        self.execution_preflight_service = ExecutionPreflightService()
        self.api_execution_sandbox_service = APIExecutionSandboxService()
        self.api_execution_evidence_service = APIExecutionEvidenceService()
        self.exporter = ManualQAExporter()
        self.demo_service = DemoWorkflowService()

    def run(self, argv: list[str] | None = None) -> int:
        parser = self._build_parser()
        args = parser.parse_args(argv)
        try:
            return args.handler(args)
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

    def _build_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(prog="manual_qa")
        subparsers = parser.add_subparsers(dest="command", required=True)

        init_parser = subparsers.add_parser("init-workspace")
        init_parser.add_argument("--path", required=True)
        init_parser.set_defaults(handler=self._handle_init_workspace)

        project_parser = subparsers.add_parser("create-project")
        project_parser.add_argument("--workspace", required=True)
        project_parser.add_argument("--name", required=True)
        project_parser.add_argument("--product-type", required=True)
        project_parser.add_argument("--description", default="")
        project_parser.add_argument("--owner", default="")
        project_parser.set_defaults(handler=self._handle_create_project)

        import_parser = subparsers.add_parser("import-requirements")
        import_parser.add_argument("--workspace", required=True)
        import_parser.add_argument("--input", required=True)
        import_parser.set_defaults(handler=self._handle_import_requirements)

        checklist_parser = subparsers.add_parser("generate-checklist")
        checklist_parser.add_argument("--workspace", required=True)
        checklist_parser.set_defaults(handler=self._handle_generate_checklist)

        testcase_parser = subparsers.add_parser("generate-testcases")
        testcase_parser.add_argument("--workspace", required=True)
        testcase_parser.set_defaults(handler=self._handle_generate_testcases)

        suite_parser = subparsers.add_parser("create-suite")
        suite_parser.add_argument("--workspace", required=True)
        suite_parser.add_argument("--name", required=True)
        suite_parser.add_argument("--scope", default="")
        suite_parser.add_argument("--owner", default="")
        suite_parser.set_defaults(handler=self._handle_create_suite)

        run_parser = subparsers.add_parser("create-run")
        run_parser.add_argument("--workspace", required=True)
        run_parser.add_argument("--suite", required=True)
        run_parser.add_argument("--env", required=True)
        run_parser.add_argument("--build", required=True)
        run_parser.add_argument("--tester", required=True)
        run_parser.set_defaults(handler=self._handle_create_run)

        update_parser = subparsers.add_parser("update-result")
        update_parser.add_argument("--workspace", required=True)
        update_parser.add_argument("--run", required=True)
        update_parser.add_argument("--case", required=True)
        update_parser.add_argument("--status", required=True)
        update_parser.add_argument("--actual", default=None)
        update_parser.add_argument("--notes", default=None)
        update_parser.set_defaults(handler=self._handle_update_result)

        evidence_parser = subparsers.add_parser("attach-evidence")
        evidence_parser.add_argument("--workspace", required=True)
        evidence_parser.add_argument("--run", required=True)
        evidence_parser.add_argument("--case", required=True)
        evidence_parser.add_argument("--type", required=True)
        evidence_parser.add_argument("--path", required=True)
        evidence_parser.add_argument("--description", default=None)
        evidence_parser.add_argument("--content-type", default=None)
        evidence_parser.set_defaults(handler=self._handle_attach_evidence)

        bug_parser = subparsers.add_parser("generate-bug")
        bug_parser.add_argument("--workspace", required=True)
        bug_parser.add_argument("--run", required=True)
        bug_parser.add_argument("--case", required=True)
        bug_parser.set_defaults(handler=self._handle_generate_bug)

        automation_parser = subparsers.add_parser("score-automation")
        automation_parser.add_argument("--workspace", required=True)
        automation_parser.set_defaults(handler=self._handle_score_automation)

        readiness_parser = subparsers.add_parser("script-readiness")
        readiness_parser.add_argument("--workspace", required=True)
        readiness_parser.set_defaults(handler=self._handle_script_readiness)

        web_readiness_parser = subparsers.add_parser("web-playwright-readiness")
        web_readiness_parser.add_argument("--workspace", required=True)
        web_readiness_parser.set_defaults(handler=self._handle_web_playwright_readiness)

        web_drafts_parser = subparsers.add_parser("generate-web-playwright-drafts")
        web_drafts_parser.add_argument("--workspace", required=True)
        web_drafts_parser.set_defaults(handler=self._handle_generate_web_playwright_drafts)

        validate_web_drafts_parser = subparsers.add_parser("validate-web-playwright-drafts")
        validate_web_drafts_parser.add_argument("--workspace", required=True)
        validate_web_drafts_parser.set_defaults(handler=self._handle_validate_web_playwright_drafts)

        api_drafts_parser = subparsers.add_parser("generate-api-drafts")
        api_drafts_parser.add_argument("--workspace", required=True)
        api_drafts_parser.set_defaults(handler=self._handle_generate_api_drafts)

        validate_api_drafts_parser = subparsers.add_parser("validate-api-drafts")
        validate_api_drafts_parser.add_argument("--workspace", required=True)
        validate_api_drafts_parser.set_defaults(handler=self._handle_validate_api_drafts)

        validate_parser = subparsers.add_parser("validate-workspace")
        validate_parser.add_argument("--workspace", required=True)
        validate_parser.set_defaults(handler=self._handle_validate_workspace)

        summary_parser = subparsers.add_parser("workspace-summary")
        summary_parser.add_argument("--workspace", required=True)
        summary_parser.set_defaults(handler=self._handle_workspace_summary)

        draft_package_summary_parser = subparsers.add_parser("draft-package-summary")
        draft_package_summary_parser.add_argument("--workspace", required=True)
        draft_package_summary_parser.set_defaults(handler=self._handle_draft_package_summary)

        execution_preflight_parser = subparsers.add_parser("execution-preflight")
        execution_preflight_parser.add_argument("--workspace", required=True)
        execution_preflight_parser.add_argument("--policy", choices=["default", "strict"], default="default")
        execution_preflight_parser.add_argument("--allow-localhost-only", action="store_true")
        execution_preflight_parser.add_argument("--dry-run-only", action="store_true")
        execution_preflight_parser.set_defaults(handler=self._handle_execution_preflight)

        execute_api_sandbox_parser = subparsers.add_parser("execute-api-sandbox")
        execute_api_sandbox_parser.add_argument("--workspace", required=True)
        execute_api_sandbox_parser.add_argument("--dry-run", action="store_true")
        execute_api_sandbox_parser.add_argument("--allow-localhost", action="store_true")
        execute_api_sandbox_parser.add_argument("--allow-write-methods", action="store_true")
        execute_api_sandbox_parser.add_argument("--allow-delete-methods", action="store_true")
        execute_api_sandbox_parser.add_argument("--override-base-url", default="")
        execute_api_sandbox_parser.add_argument("--approve", action="store_true")
        execute_api_sandbox_parser.set_defaults(handler=self._handle_execute_api_sandbox)

        api_execution_evidence_parser = subparsers.add_parser("api-execution-evidence")
        api_execution_evidence_parser.add_argument("--workspace", required=True)
        api_execution_evidence_parser.set_defaults(handler=self._handle_api_execution_evidence)

        demo_parser = subparsers.add_parser("demo-workflow")
        demo_parser.add_argument("--workspace", required=True)
        demo_parser.add_argument("--project-name", default="Manual QA Demo")
        demo_parser.add_argument("--product-type", default="web")
        demo_parser.set_defaults(handler=self._handle_demo_workflow)

        return parser

    def _handle_init_workspace(self, args: argparse.Namespace) -> int:
        workspace = self.workspace_service.create_workspace(args.path)
        print(f"Workspace initialized at {workspace}")
        return 0

    def _handle_create_project(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        project = self.project_service.create_project_profile(
            name=args.name,
            product_type=args.product_type,
            description=args.description,
            owner=args.owner,
        )
        output_path = workspace / "project.json"
        self.workspace_service.write_json(output_path, project.to_dict())
        self.workspace_service.update_workspace_manifest(workspace, project=project)
        print(f"Project written to {output_path}")
        return 0

    def _handle_import_requirements(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        input_path = Path(args.input)
        raw_text = self.workspace_service.read_text(input_path)
        raw_records = self.importer.import_requirements(raw_text, source_ref=str(input_path))
        normalized = self.normalizer.normalize_requirements(raw_records)
        output_path = workspace / "requirements" / "normalized_requirements.json"
        self.workspace_service.write_json(output_path, [item.to_dict() for item in normalized])
        self.workspace_service.update_workspace_manifest(workspace)
        print(f"Normalized requirements written to {output_path}")
        return 0

    def _handle_generate_checklist(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        requirements = self._load_requirements(workspace / "requirements" / "normalized_requirements.json")
        checklist = self.checklist_generator.generate(requirements)
        json_path = workspace / "checklists" / "checklist.json"
        md_path = workspace / "checklists" / "checklist.md"
        self.workspace_service.write_json(json_path, [item.to_dict() for item in checklist])
        self.workspace_service.write_markdown(md_path, self._render_checklist_markdown(checklist))
        self.workspace_service.update_workspace_manifest(workspace)
        print(f"Checklist written to {json_path}")
        return 0

    def _handle_generate_testcases(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        requirements = self._load_requirements(workspace / "requirements" / "normalized_requirements.json")
        test_cases = self.testcase_generator.generate(requirements)
        json_path = workspace / "testcases" / "testcases.json"
        md_path = workspace / "testcases" / "testcases.md"
        self.workspace_service.write_json(json_path, [item.to_dict() for item in test_cases])
        self.workspace_service.write_markdown(md_path, self._render_testcases_markdown(test_cases))
        self.workspace_service.update_workspace_manifest(workspace)
        print(f"Test cases written to {json_path}")
        return 0

    def _handle_create_suite(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        project = self._load_project(workspace / "project.json")
        test_cases = self._load_test_cases(workspace / "testcases" / "testcases.json")
        suite = self.suite_service.create_test_suite(
            project_id=project.project_id,
            name=args.name,
            test_cases=[case.test_case_id for case in test_cases],
            scope=args.scope,
            owner=args.owner,
        )
        suite_slug = self._slug(args.name) or suite.suite_id.lower()
        json_path = workspace / "suites" / f"{suite_slug}.json"
        md_path = workspace / "suites" / f"{suite_slug}.md"
        self.workspace_service.write_json(json_path, suite.to_dict())
        self.workspace_service.write_markdown(md_path, self.exporter.export_markdown_string(suite))
        self.workspace_service.update_workspace_manifest(workspace)
        print(f"Suite written to {json_path}")
        return 0

    def _handle_create_run(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        project = self._load_project(workspace / "project.json")
        suite = self._load_suite(self._resolve_workspace_path(workspace, args.suite))
        test_run = self.run_service.create_test_run(
            project_id=project.project_id,
            suite=suite,
            environment=args.env,
            build=args.build,
            tester=args.tester,
        )
        json_path = workspace / "runs" / f"{test_run.run_id}.json"
        md_path = workspace / "runs" / f"{test_run.run_id}.md"
        self.workspace_service.write_json(json_path, test_run.to_dict())
        self.workspace_service.write_markdown(md_path, self.exporter.export_markdown_string(test_run))
        self.workspace_service.update_workspace_manifest(workspace)
        print(f"Run written to {json_path}")
        return 0

    def _handle_update_result(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        run_path = self._resolve_workspace_path(workspace, args.run)
        test_run = self._load_run(run_path)
        updated_run = self.result_service.update_test_result(
            test_run,
            args.case,
            args.status,
            actual_result=args.actual,
            notes=args.notes,
        )
        summary = self.summary_service.summarize_test_run(updated_run)
        self.workspace_service.write_json(run_path, updated_run.to_dict())
        summary_json = workspace / "runs" / f"{updated_run.run_id}-summary.json"
        summary_md = workspace / "runs" / f"{updated_run.run_id}-summary.md"
        self.workspace_service.write_json(summary_json, summary.to_dict())
        self.workspace_service.write_markdown(summary_md, self.exporter.export_markdown_string(summary))
        self.workspace_service.update_workspace_manifest(workspace)
        print(f"Run updated at {run_path}")
        return 0

    def _handle_attach_evidence(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        run_path = self._resolve_workspace_path(workspace, args.run)
        test_run = self._load_run(run_path)
        evidence = self.evidence_service.attach_evidence(
            test_run,
            args.case,
            args.type,
            args.path,
            description=args.description,
            content_type=args.content_type,
        )
        evidence_json = workspace / "evidence" / f"{evidence.evidence_id}.json"
        evidence_md = workspace / "evidence" / f"{evidence.evidence_id}.md"
        self.workspace_service.write_json(evidence_json, evidence.to_dict())
        self.workspace_service.write_markdown(evidence_md, self.exporter.export_markdown_string(evidence))
        self.workspace_service.write_json(run_path, test_run.to_dict())
        self.workspace_service.update_workspace_manifest(workspace)
        print(f"Evidence written to {evidence_json}")
        return 0

    def _handle_generate_bug(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        run_path = self._resolve_workspace_path(workspace, args.run)
        test_run = self._load_run(run_path)
        test_case = self._find_test_case(workspace, args.case)
        evidence = self._find_evidence_for_case(workspace, test_run.run_id, args.case)
        bug = self.bug_service.generate_bug_draft(
            test_run,
            args.case,
            test_case=test_case,
            evidence=evidence,
        )
        bug_json = workspace / "bugs" / f"{bug.bug_id}.json"
        bug_md = workspace / "bugs" / f"{bug.bug_id}.md"
        self.workspace_service.write_json(bug_json, bug.to_dict())
        self.workspace_service.write_markdown(bug_md, self.exporter.export_markdown_string(bug))
        self.workspace_service.update_workspace_manifest(workspace)
        print(f"Bug draft written to {bug_json}")
        return 0

    def _handle_score_automation(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        test_cases = self._load_test_cases(workspace / "testcases" / "testcases.json")
        failure_records = self._load_failure_records(workspace / "failure_memory")
        candidates = self.automation_service.score_automation_candidates(
            test_cases,
            failure_records=failure_records,
        )
        json_path = workspace / "automation_candidates" / "candidates.json"
        md_path = workspace / "automation_candidates" / "candidates.md"
        self.workspace_service.write_json(json_path, [item.to_dict() for item in candidates])
        self.workspace_service.write_markdown(md_path, self.exporter.export_markdown_string(candidates))
        self.workspace_service.update_workspace_manifest(workspace)
        print(f"Automation candidates written to {json_path}")
        return 0

    def _handle_script_readiness(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        test_cases = self._load_test_cases(workspace / "testcases" / "testcases.json")
        project = self._load_project(workspace / "project.json") if (workspace / "project.json").exists() else None
        automation_candidates = self._load_automation_candidates(
            workspace / "automation_candidates" / "candidates.json"
        )
        readiness_items = self.script_readiness_service.analyze_script_readiness_batch(
            test_cases,
            automation_candidates=automation_candidates,
            project_type_hint=project.product_type if project is not None else None,
        )
        json_path = workspace / "reports" / "script_readiness.json"
        md_path = workspace / "reports" / "script_readiness.md"
        self.workspace_service.write_json(json_path, [item.to_dict() for item in readiness_items])
        self.workspace_service.write_markdown(md_path, self.exporter.export_markdown_string(readiness_items))
        self.workspace_service.update_workspace_manifest(workspace)
        ready = len([item for item in readiness_items if item.readiness_status == "Ready"])
        needs_more_data = len([item for item in readiness_items if item.readiness_status == "Needs More Data"])
        not_suitable = len([item for item in readiness_items if item.readiness_status == "Not Suitable"])
        print(
            "Script readiness:"
            f" total={len(readiness_items)}"
            f" ready={ready}"
            f" needs_more_data={needs_more_data}"
            f" not_suitable={not_suitable}"
        )
        return 0

    def _handle_web_playwright_readiness(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        test_cases = self._load_test_cases(workspace / "testcases" / "testcases.json")
        project = self._load_project(workspace / "project.json") if (workspace / "project.json").exists() else None
        automation_candidates = self._load_automation_candidates(
            workspace / "automation_candidates" / "candidates.json"
        )
        script_readiness_items = self._load_script_readiness_items(
            workspace / "reports" / "script_readiness.json"
        )
        readiness_items = self.web_playwright_readiness_service.analyze_web_playwright_readiness_batch(
            test_cases,
            script_readiness_items=script_readiness_items,
            automation_candidates=automation_candidates,
            project_type_hint=project.product_type if project is not None else None,
        )
        json_path = workspace / "reports" / "web_playwright_readiness.json"
        md_path = workspace / "reports" / "web_playwright_readiness.md"
        self.workspace_service.write_json(json_path, [item.to_dict() for item in readiness_items])
        self.workspace_service.write_markdown(md_path, self.exporter.export_markdown_string(readiness_items))
        self.workspace_service.update_workspace_manifest(workspace)
        ready = len([item for item in readiness_items if item.readiness_status == "Ready"])
        needs_more_data = len(
            [item for item in readiness_items if item.readiness_status == "Needs More Data"]
        )
        not_suitable = len([item for item in readiness_items if item.readiness_status == "Not Suitable"])
        print(
            "Web Playwright readiness:"
            f" total_evaluated={len(readiness_items)}"
            f" ready={ready}"
            f" needs_more_data={needs_more_data}"
            f" not_suitable={not_suitable}"
        )
        return 0

    def _handle_generate_api_drafts(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        test_cases = self._load_test_cases(workspace / "testcases" / "testcases.json")
        readiness_items = self._load_script_readiness_items(workspace / "reports" / "script_readiness.json")
        drafts = self.api_script_generator.generate_api_script_drafts(
            test_cases,
            readiness_items=readiness_items,
        )
        output_dir = workspace / "script_drafts" / "api"
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "api_script_drafts.json"
        md_path = output_dir / "api_script_drafts.md"
        self.workspace_service.write_json(json_path, [item.to_dict() for item in drafts])
        self.workspace_service.write_markdown(md_path, self.exporter.export_markdown_string(drafts))
        for draft in drafts:
            self.workspace_service.write_markdown(output_dir / draft.file_name, draft.script_content)
        self.workspace_service.update_workspace_manifest(workspace)
        warning_count = sum(len(item.warnings) for item in drafts)
        skipped = len(test_cases) - len(drafts)
        print(
            "API script drafts:"
            f" total_test_cases={len(test_cases)}"
            f" generated_drafts={len(drafts)}"
            f" skipped_cases={skipped}"
            f" warnings={warning_count}"
        )
        return 0

    def _handle_generate_web_playwright_drafts(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        test_cases = self._load_test_cases(workspace / "testcases" / "testcases.json")
        readiness_items = self._load_web_playwright_readiness_items(
            workspace / "reports" / "web_playwright_readiness.json"
        )
        drafts = self.web_playwright_script_generator.generate_web_playwright_script_drafts(
            test_cases,
            readiness_items=readiness_items,
        )
        output_dir = workspace / "script_drafts" / "web_playwright"
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "web_playwright_script_drafts.json"
        md_path = output_dir / "web_playwright_script_drafts.md"
        self.workspace_service.write_json(json_path, [item.to_dict() for item in drafts])
        self.workspace_service.write_markdown(md_path, self.exporter.export_markdown_string(drafts))
        for draft in drafts:
            self.workspace_service.write_markdown(output_dir / draft.file_name, draft.script_content)
        self.workspace_service.update_workspace_manifest(workspace)
        warning_count = sum(len(item.warnings) for item in drafts)
        skipped = len(test_cases) - len(drafts)
        print(
            "Web Playwright script drafts:"
            f" total_test_cases={len(test_cases)}"
            f" generated_drafts={len(drafts)}"
            f" skipped_cases={skipped}"
            f" warnings={warning_count}"
        )
        return 0

    def _handle_validate_web_playwright_drafts(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        output_dir = workspace / "script_drafts" / "web_playwright"
        drafts = self._load_web_playwright_script_drafts(output_dir / "web_playwright_script_drafts.json")
        validation_results = self.web_playwright_validation_service.validate_web_playwright_script_drafts(drafts)
        validation_json = output_dir / "web_playwright_validation.json"
        validation_md = output_dir / "web_playwright_validation.md"
        package_json = output_dir / "web_playwright_package_manifest.json"
        package_md = output_dir / "web_playwright_package_manifest.md"
        self.workspace_service.write_json(validation_json, [item.to_dict() for item in validation_results])
        self.workspace_service.write_markdown(
            validation_md,
            self.exporter.export_markdown_string(validation_results),
        )
        package_manifest = self.web_playwright_packaging_service.build_web_playwright_package(
            drafts,
            validation_results,
            validation_report_files=[
                "script_drafts/web_playwright/web_playwright_validation.json",
                "script_drafts/web_playwright/web_playwright_validation.md",
            ],
        )
        self.workspace_service.write_json(package_json, package_manifest.to_dict())
        self.workspace_service.write_markdown(
            package_md,
            self.exporter.export_markdown_string(package_manifest),
        )
        self.workspace_service.update_workspace_manifest(workspace)
        print(
            "Web Playwright draft validation:"
            f" draft_count={package_manifest.draft_count}"
            f" valid_count={package_manifest.valid_count}"
            f" invalid_count={package_manifest.invalid_count}"
            f" warning_count={package_manifest.warning_count}"
            f" status={package_manifest.status}"
        )
        return 0

    def _handle_validate_api_drafts(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        output_dir = workspace / "script_drafts" / "api"
        drafts = self._load_api_script_drafts(output_dir / "api_script_drafts.json")
        validation_results = self.api_script_validation_service.validate_api_script_drafts(drafts)
        validation_json = output_dir / "api_script_validation.json"
        validation_md = output_dir / "api_script_validation.md"
        package_json = output_dir / "api_script_package_manifest.json"
        package_md = output_dir / "api_script_package_manifest.md"
        self.workspace_service.write_json(validation_json, [item.to_dict() for item in validation_results])
        self.workspace_service.write_markdown(
            validation_md,
            self.exporter.export_markdown_string(validation_results),
        )
        package_manifest = self.api_script_packaging_service.build_api_script_package(
            drafts,
            validation_results,
            validation_report_files=[
                "script_drafts/api/api_script_validation.json",
                "script_drafts/api/api_script_validation.md",
            ],
        )
        self.workspace_service.write_json(package_json, package_manifest.to_dict())
        self.workspace_service.write_markdown(
            package_md,
            self.exporter.export_markdown_string(package_manifest),
        )
        self.workspace_service.update_workspace_manifest(workspace)
        print(
            "API draft validation:"
            f" draft_count={package_manifest.draft_count}"
            f" valid_count={package_manifest.valid_count}"
            f" invalid_count={package_manifest.invalid_count}"
            f" warning_count={package_manifest.warning_count}"
            f" status={package_manifest.status}"
        )
        return 0

    def _handle_validate_workspace(self, args: argparse.Namespace) -> int:
        workspace = Path(args.workspace)
        validation = self.workspace_service.validate_workspace(workspace)
        print(
            "Workspace validation:"
            f" valid={validation.is_valid}"
            f" missing_folders={len(validation.missing_folders)}"
            f" missing_files={len(validation.missing_files)}"
        )
        if not workspace.exists() or validation.missing_folders:
            return 1
        return 0

    def _handle_workspace_summary(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        manifest = self.workspace_service.update_workspace_manifest(workspace)
        validation = self.workspace_service.validate_workspace(workspace)
        listing = self.workspace_service.list_workspace_artifacts(workspace)
        summary = {
            "project_id": manifest.get("project_id", ""),
            "project_name": manifest.get("project_name", ""),
            "product_type": manifest.get("product_type", ""),
            "artifact_counts": listing["artifact_counts"],
            "validation_result": validation.to_dict(),
            "metadata": {
                "workspace_version": manifest.get("workspace_version", ""),
                "updated_at": manifest.get("updated_at", ""),
            },
        }
        json_path = workspace / "reports" / "workspace_summary.json"
        md_path = workspace / "reports" / "workspace_summary.md"
        self.workspace_service.write_json(json_path, summary)
        self.workspace_service.write_markdown(md_path, self._render_workspace_summary(summary))
        self.workspace_service.update_workspace_manifest(workspace)
        print(f"Workspace summary written to {json_path}")
        return 0

    def _handle_draft_package_summary(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        summary = self.draft_package_dashboard_service.summarize_draft_packages(workspace)
        json_path = workspace / "reports" / "draft_package_summary.json"
        md_path = workspace / "reports" / "draft_package_summary.md"
        self.exporter.export_json_file(summary, json_path)
        self.exporter.export_markdown_file(summary, md_path)
        self.workspace_service.update_workspace_manifest(workspace)
        print(
            "Draft package summary:"
            f" overall_status={summary.overall_status}"
            f" total_drafts={summary.total_drafts}"
            f" total_valid={summary.total_valid}"
            f" total_invalid={summary.total_invalid}"
            f" total_warnings={summary.total_warnings}"
            f" recommended_next_step={summary.recommended_next_step}"
        )
        if summary.overall_status == "Missing":
            print("No API or Web draft package manifests were found. Generate and validate draft packages first.")
        return 0

    def _handle_execution_preflight(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        if args.policy == "strict":
            policy = self.execution_safety_service.create_strict_execution_safety_policy(
                dry_run_only=bool(args.dry_run_only or True),
                metadata={"allow_localhost_only": True},
            )
        else:
            policy = self.execution_safety_service.create_default_execution_safety_policy(
                allow_localhost_only=bool(args.allow_localhost_only),
                dry_run_only=bool(args.dry_run_only or True),
            )

        plan = self.execution_preflight_service.build_execution_plan_from_workspace(
            workspace,
            policy=policy,
        )
        json_path = workspace / "reports" / "execution_preflight_plan.json"
        md_path = workspace / "reports" / "execution_preflight_plan.md"
        self.exporter.export_json_file(plan, json_path)
        self.exporter.export_markdown_file(plan, md_path)
        self.workspace_service.update_workspace_manifest(workspace)
        print(
            "Execution preflight:"
            f" overall_decision={plan.overall_decision}"
            f" total_targets={plan.total_targets}"
            f" allowed_count={plan.allowed_count}"
            f" blocked_count={plan.blocked_count}"
            f" needs_approval_count={plan.needs_approval_count}"
            f" dry_run_only={plan.dry_run_only}"
            f" recommended_next_step={plan.recommended_next_step}"
        )
        if plan.overall_decision == "Missing Draft Packages":
            print("No draft packages were found. Generate and validate API/Web draft packages first.")
        return 0

    def _handle_execute_api_sandbox(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        base_policy = self.execution_safety_service.create_default_execution_safety_policy(
            allow_localhost_only=bool(args.allow_localhost),
            dry_run_only=True,
        )
        localhost_prefixes = ("http://localhost", "http://127.0.0.1")
        actual_execution_enabled = (
            not bool(args.dry_run)
            and bool(args.approve)
            and bool(args.allow_localhost)
            and str(args.override_base_url or "").startswith(localhost_prefixes)
        )
        policy = replace(
            base_policy,
            allow_execution=actual_execution_enabled,
            allow_write_methods=bool(args.allow_write_methods),
            allow_delete_methods=bool(args.allow_delete_methods),
            dry_run_only=not actual_execution_enabled,
            metadata={
                **dict(base_policy.metadata),
                "cli_actual_execution_enabled": actual_execution_enabled,
            },
        )
        results = self.api_execution_sandbox_service.execute_api_sandbox_from_workspace(
            workspace,
            policy=policy,
            override_base_url=str(args.override_base_url or "") or None,
            dry_run=not actual_execution_enabled or bool(args.dry_run),
            approved=bool(args.approve),
        )
        json_path = workspace / "script_drafts" / "api" / "api_execution_results.json"
        md_path = workspace / "script_drafts" / "api" / "api_execution_results.md"
        self.exporter.export_json_file(results, json_path)
        self.exporter.export_markdown_file(results, md_path)
        self.workspace_service.update_workspace_manifest(workspace)
        print(
            "API sandbox execution:"
            f" total={len(results)}"
            f" dry_run={len([item for item in results if item.status == 'Dry Run'])}"
            f" blocked={len([item for item in results if item.status == 'Blocked'])}"
            f" passed={len([item for item in results if item.status == 'Passed'])}"
            f" failed={len([item for item in results if item.status == 'Failed'])}"
            f" error={len([item for item in results if item.status == 'Error'])}"
        )
        return 0

    def _handle_api_execution_evidence(self, args: argparse.Namespace) -> int:
        workspace = self._workspace(args.workspace)
        report = self.api_execution_evidence_service.build_api_execution_evidence_report_from_workspace(workspace)
        summary = report["summary"]
        bug_suggestions = report["bug_suggestions"]
        failure_signatures = report["failure_signatures"]
        print(
            "API execution evidence:"
            f" total={summary.total}"
            f" passed={summary.passed}"
            f" failed={summary.failed}"
            f" blocked={summary.blocked}"
            f" dry_run={summary.dry_run}"
            f" error={summary.error}"
            f" status={summary.status}"
            f" bug_suggestions={len(bug_suggestions)}"
            f" failure_signatures={len(failure_signatures)}"
        )
        return 0

    def _handle_demo_workflow(self, args: argparse.Namespace) -> int:
        report = self.demo_service.run_demo_workflow(
            args.workspace,
            project_name=args.project_name,
            product_type=args.product_type,
        )
        print(
            "Demo workflow completed:"
            f" project={report['project_id']}"
            f" run={report['run_id']}"
            f" bug={report['bug_id']}"
        )
        return 0

    def _workspace(self, path: str) -> Path:
        workspace = Path(path)
        if not workspace.exists():
            raise FileNotFoundError(f"Workspace does not exist: {workspace}")
        return workspace

    def _resolve_workspace_path(self, workspace: Path, value: str) -> Path:
        candidate = Path(value)
        return candidate if candidate.is_absolute() else workspace / candidate

    def _load_project(self, path: Path) -> ProjectProfile:
        data = self.workspace_service.read_json(path)
        return ProjectProfile(**data)

    def _load_requirements(self, path: Path) -> list[NormalizedRequirement]:
        data = self.workspace_service.read_json(path)
        return [NormalizedRequirement(**item) for item in data]

    def _load_test_cases(self, path: Path) -> list[ManualTestCase]:
        data = self.workspace_service.read_json(path)
        return [ManualTestCase(**item) for item in data]

    def _load_suite(self, path: Path) -> TestSuite:
        data = self.workspace_service.read_json(path)
        return TestSuite(**data)

    def _load_run(self, path: Path) -> TestRun:
        data = self.workspace_service.read_json(path)
        results = [TestResult(**item) for item in data.get("results", [])]
        payload = dict(data)
        payload["results"] = results
        return TestRun(**payload)

    def _load_failure_records(self, directory: Path) -> list[FailureRecord]:
        if not directory.exists():
            return []

        records: list[FailureRecord] = []
        for path in sorted(directory.glob("*.json")):
            data = self.workspace_service.read_json(path)
            if isinstance(data, list):
                records.extend(self._deserialize_failure_records(data))
                continue
            if "record_id" not in data or "signature" not in data:
                continue
            records.extend(self._deserialize_failure_records([data]))
        return records

    def _load_automation_candidates(self, path: Path) -> list[AutomationCandidate]:
        if not path.exists():
            return []
        data = self.workspace_service.read_json(path)
        if not isinstance(data, list):
            return []
        return [AutomationCandidate(**item) for item in data if isinstance(item, dict)]

    def _load_api_script_drafts(self, path: Path) -> list[APITestScriptDraft]:
        data = self.workspace_service.read_json(path)
        if not isinstance(data, list):
            return []
        return [APITestScriptDraft(**item) for item in data if isinstance(item, dict)]

    def _load_script_readiness_items(self, path: Path) -> list[ScriptGenerationReadiness]:
        if not path.exists():
            return []
        data = self.workspace_service.read_json(path)
        if not isinstance(data, list):
            return []
        items: list[ScriptGenerationReadiness] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            gaps = item.get("gaps", [])
            payload = dict(item)
            payload["gaps"] = gaps
            items.append(ScriptGenerationReadiness(**payload))
        return items

    def _load_web_playwright_readiness_items(self, path: Path) -> list[WebPlaywrightReadiness]:
        if not path.exists():
            return []
        data = self.workspace_service.read_json(path)
        if not isinstance(data, list):
            return []
        items: list[WebPlaywrightReadiness] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            payload = dict(item)
            payload["gaps"] = item.get("gaps", [])
            items.append(WebPlaywrightReadiness(**payload))
        return items

    def _load_web_playwright_script_drafts(self, path: Path) -> list[WebPlaywrightScriptDraft]:
        data = self.workspace_service.read_json(path)
        if not isinstance(data, list):
            return []
        return [WebPlaywrightScriptDraft(**item) for item in data if isinstance(item, dict)]

    def _load_api_script_validation_results(self, path: Path) -> list[APIScriptValidationResult]:
        if not path.exists():
            return []
        data = self.workspace_service.read_json(path)
        if not isinstance(data, list):
            return []
        results: list[APIScriptValidationResult] = []
        for item in data:
            if not isinstance(item, dict):
                continue
            issues = [
                APIScriptValidationIssue(**issue)
                for issue in item.get("issues", [])
                if isinstance(issue, dict)
            ]
            payload = dict(item)
            payload["issues"] = issues
            results.append(APIScriptValidationResult(**payload))
        return results

    def _deserialize_failure_records(self, items: list[dict[str, Any]]) -> list[FailureRecord]:
        records: list[FailureRecord] = []
        for item in items:
            signature = FailureSignature(**item["signature"])
            payload = dict(item)
            payload["signature"] = signature
            records.append(FailureRecord(**payload))
        return records

    def _find_test_case(self, workspace: Path, test_case_id: str) -> ManualTestCase | None:
        path = workspace / "testcases" / "testcases.json"
        if not path.exists():
            return None
        for test_case in self._load_test_cases(path):
            if test_case.test_case_id == test_case_id:
                return test_case
        return None

    def _find_evidence_for_case(self, workspace: Path, run_id: str, test_case_id: str) -> list[Evidence]:
        evidence_dir = workspace / "evidence"
        if not evidence_dir.exists():
            return []

        evidence_items: list[Evidence] = []
        for path in sorted(evidence_dir.glob("*.json")):
            data = self.workspace_service.read_json(path)
            if data.get("run_id") != run_id or data.get("test_case_id") != test_case_id:
                continue
            evidence_items.append(Evidence(**data))
        return evidence_items

    def _render_checklist_markdown(self, checklist: list[ChecklistItem]) -> str:
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

    def _render_testcases_markdown(self, test_cases: list[ManualTestCase]) -> str:
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

    def _slug(self, value: str) -> str:
        text = "".join(char.lower() if char.isalnum() else "-" for char in value.strip())
        while "--" in text:
            text = text.replace("--", "-")
        return text.strip("-")

    def _render_workspace_summary(self, summary: dict[str, Any]) -> str:
        validation = summary["validation_result"]
        lines = [
            "# Workspace Summary",
            "",
            f"- Project ID: {summary['project_id'] or 'N/A'}",
            f"- Project Name: {summary['project_name'] or 'N/A'}",
            f"- Product Type: {summary['product_type'] or 'N/A'}",
            f"- Workspace Version: {summary['metadata']['workspace_version'] or 'N/A'}",
            f"- Valid: {validation['is_valid']}",
            "",
            "## Artifact Counts",
        ]
        lines.extend(
            f"- {folder}: {count}"
            for folder, count in summary["artifact_counts"].items()
        )
        lines.extend(
            [
                "",
                "## Validation",
                f"- Missing Folders: {', '.join(validation['missing_folders']) or 'None'}",
                f"- Missing Files: {', '.join(validation['missing_files']) or 'None'}",
                f"- Warnings: {', '.join(validation['warnings']) or 'None'}",
                "",
            ]
        )
        return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    return ManualQACLI().run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
