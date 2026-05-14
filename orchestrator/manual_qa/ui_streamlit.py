"""Simple local Streamlit UI for the Manual QA workspace workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.manual_qa.api_script_generator import APITestScriptGenerator
from orchestrator.manual_qa.api_script_packaging_service import APIScriptPackagingService
from orchestrator.manual_qa.api_script_validation_service import APIScriptValidationService
from orchestrator.manual_qa.automation_candidate_service import AutomationCandidateService
from orchestrator.manual_qa.bug_service import BugDraftService
from orchestrator.manual_qa.checklist_generator import ChecklistGenerator
from orchestrator.manual_qa.demo_service import DemoWorkflowService
from orchestrator.manual_qa.evidence_service import EvidenceService
from orchestrator.manual_qa.exporters import ManualQAExporter
from orchestrator.manual_qa.failure_memory_service import FailureRecord, FailureSignature
from orchestrator.manual_qa.models import (
    APITestScriptDraft,
    AutomationCandidate,
    Evidence,
    ManualTestCase,
    NormalizedRequirement,
    ScriptGenerationReadiness,
    TestResult,
    TestRun,
    TestSuite,
)
from orchestrator.manual_qa.project_service import ProjectProfileService, SUPPORTED_PRODUCT_TYPES
from orchestrator.manual_qa.requirement_importer import RequirementImporter
from orchestrator.manual_qa.requirement_normalizer import RequirementNormalizer
from orchestrator.manual_qa.result_service import TestResultService
from orchestrator.manual_qa.run_service import TestRunService
from orchestrator.manual_qa.script_readiness_service import ScriptReadinessService
from orchestrator.manual_qa.summary_service import RunSummaryService
from orchestrator.manual_qa.suite_service import TestSuiteService
from orchestrator.manual_qa.testcase_generator import ManualTestCaseGenerator
from orchestrator.manual_qa.ui_helpers import (
    format_artifact_count_summary,
    get_artifact_preview,
    get_next_recommended_actions,
    get_workspace_health,
    get_workspace_summary,
    list_bug_files,
    list_candidate_files,
    list_api_draft_files,
    list_api_validation_files,
    list_report_files,
    list_run_files,
    list_suite_files,
    load_automation_candidates,
    load_bugs,
    load_checklist,
    load_failure_memory_records,
    load_api_script_drafts,
    load_api_script_package_manifest,
    load_api_script_validation_results,
    load_project,
    load_requirements,
    load_runs,
    load_script_readiness_items,
    load_testcases,
    resolve_workspace,
    safe_load_json_artifact,
    summarize_bugs_for_ui,
    summarize_candidates_for_ui,
    summarize_run_for_ui,
    validate_workspace_for_ui,
)
from orchestrator.manual_qa.workspace_service import ManualQAWorkspaceService


class ManualQAStreamlitUI:
    """Thin Streamlit adapter over the local Manual QA services."""

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
        self.script_readiness_service = ScriptReadinessService()
        self.evidence_service = EvidenceService()
        self.bug_service = BugDraftService()
        self.automation_service = AutomationCandidateService()
        self.api_script_generator = APITestScriptGenerator()
        self.api_script_validation_service = APIScriptValidationService()
        self.api_script_packaging_service = APIScriptPackagingService()
        self.demo_service = DemoWorkflowService()
        self.exporter = ManualQAExporter()

    def render(self, st: Any) -> None:
        st.set_page_config(page_title="Manual QA Workspace", layout="wide")
        st.title("Manual QA Workspace")

        workspace_input = st.sidebar.text_input("Workspace path", value="artifacts/manual_qa_demo")
        workspace = resolve_workspace(workspace_input)

        self._render_sidebar(st, workspace)

        tabs = st.tabs(
            [
                "Project",
                "Requirements",
                "Checklist",
                "Test Cases",
                "Suites & Runs",
                "Evidence & Bugs",
                "Failure Memory",
                "Automation Candidates",
                "Reports",
            ]
        )

        self._render_project_tab(st, tabs[0], workspace)
        self._render_requirements_tab(st, tabs[1], workspace)
        self._render_checklist_tab(st, tabs[2], workspace)
        self._render_testcases_tab(st, tabs[3], workspace)
        self._render_suites_runs_tab(st, tabs[4], workspace)
        self._render_evidence_bugs_tab(st, tabs[5], workspace)
        self._render_failure_memory_tab(st, tabs[6], workspace)
        self._render_automation_tab(st, tabs[7], workspace)
        self._render_reports_tab(st, tabs[8], workspace)

    def _render_sidebar(self, st: Any, workspace: Path) -> None:
        if st.sidebar.button("Initialize workspace", use_container_width=True):
            self.workspace_service.create_workspace(workspace)
            st.sidebar.success(f"Workspace initialized at {workspace}")

        if st.sidebar.button("Validate workspace", use_container_width=True):
            validation = validate_workspace_for_ui(workspace)
            if validation["is_valid"]:
                st.sidebar.success(validation["message"])
            else:
                st.sidebar.warning(validation["message"])

        if st.sidebar.button("Run demo workflow", use_container_width=True):
            report = self.demo_service.run_demo_workflow(workspace)
            st.sidebar.success(f"Demo workflow completed for {report['project_id']}")

        if st.sidebar.button("Refresh workspace", use_container_width=True):
            st.rerun()

        summary = get_workspace_summary(workspace)
        health = get_workspace_health(workspace)
        actions = get_next_recommended_actions(workspace)

        st.sidebar.markdown("### Workspace")
        st.sidebar.caption(str(workspace))
        st.sidebar.write(f"Status: `{health['health_level']}`")
        st.sidebar.write(health["message"])
        st.sidebar.write(summary["artifact_count_summary"])

        st.sidebar.markdown("### Next Actions")
        for action in actions:
            st.sidebar.write(f"- {action}")

    def _render_project_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Project")
            project = load_project(workspace)
            if project:
                with st.container(border=True):
                    st.write(f"Project ID: `{project.get('project_id', '')}`")
                    st.write(f"Name: {project.get('name', 'N/A')}")
                    st.write(f"Product Type: {project.get('product_type', 'N/A')}")
                    st.write(f"Owner: {project.get('owner', 'N/A') or 'N/A'}")
            else:
                st.info("No project profile found yet. Create one to anchor the workspace.")

            with st.form("create_project_form"):
                project_name = st.text_input("Project name", value=project.get("name", "Manual QA Demo"))
                product_type_options = sorted(SUPPORTED_PRODUCT_TYPES)
                default_index = product_type_options.index(project.get("product_type", "web")) if project.get("product_type", "web") in product_type_options else product_type_options.index("web")
                product_type = st.selectbox("Product type", options=product_type_options, index=default_index)
                submitted = st.form_submit_button("Create project")
                if submitted:
                    self.workspace_service.create_workspace(workspace)
                    created = self.project_service.create_project_profile(
                        name=project_name,
                        product_type=product_type,
                    )
                    self.workspace_service.write_json(workspace / "project.json", created.to_dict())
                    self.workspace_service.update_workspace_manifest(workspace, project=created)
                    st.success(f"Project created: {created.project_id}")

            if project:
                st.expander("project.json preview").code(get_artifact_preview(workspace / "project.json"), language="json")

    def _render_requirements_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Requirements")
            with st.form("import_requirements_form"):
                requirement_text = st.text_area("Requirement input", height=220)
                uploaded_file = st.file_uploader("Optional .txt or .md file", type=["txt", "md"])
                submitted = st.form_submit_button("Import requirements")
                if submitted:
                    payload = requirement_text
                    if uploaded_file is not None:
                        payload = uploaded_file.getvalue().decode("utf-8")
                    if not str(payload or "").strip():
                        st.warning("Provide requirement text or upload a requirement file.")
                    else:
                        self.workspace_service.create_workspace(workspace)
                        raw_records = self.importer.import_requirements(payload, source_ref="streamlit-ui")
                        normalized = self.normalizer.normalize_requirements(raw_records)
                        self.workspace_service.write_json(
                            workspace / "requirements" / "normalized_requirements.json",
                            [item.to_dict() for item in normalized],
                        )
                        self.workspace_service.update_workspace_manifest(workspace)
                        st.success(f"Imported {len(normalized)} normalized requirements.")

            requirements = load_requirements(workspace)
            st.caption(f"Normalized requirements: {len(requirements)}")
            if requirements:
                st.dataframe(requirements, use_container_width=True)
                st.expander("normalized_requirements.json preview").code(
                    get_artifact_preview(workspace / "requirements" / "normalized_requirements.json"),
                    language="json",
                )
            else:
                st.info("No normalized requirements found yet.")

    def _render_checklist_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Checklist")
            if st.button("Generate checklist"):
                requirements = self._load_requirement_models(workspace)
                if not requirements:
                    st.warning("Import requirements first.")
                else:
                    checklist = self.checklist_generator.generate(requirements)
                    self.workspace_service.write_json(
                        workspace / "checklists" / "checklist.json",
                        [item.to_dict() for item in checklist],
                    )
                    self.workspace_service.write_markdown(
                        workspace / "checklists" / "checklist.md",
                        self._render_checklist_markdown(checklist),
                    )
                    self.workspace_service.update_workspace_manifest(workspace)
                    st.success(f"Generated {len(checklist)} checklist items.")

            checklist = load_checklist(workspace)
            st.caption(f"Checklist items: {len(checklist)}")
            if checklist:
                st.dataframe(checklist, use_container_width=True)
            else:
                st.info("No checklist artifacts found yet.")

            markdown_path = workspace / "checklists" / "checklist.md"
            if markdown_path.exists():
                st.expander("Checklist Markdown preview").code(get_artifact_preview(markdown_path), language="markdown")

    def _render_testcases_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Test Cases")
            if st.button("Generate test cases"):
                requirements = self._load_requirement_models(workspace)
                if not requirements:
                    st.warning("Import requirements first.")
                else:
                    test_cases = self.testcase_generator.generate(requirements)
                    self.workspace_service.write_json(
                        workspace / "testcases" / "testcases.json",
                        [item.to_dict() for item in test_cases],
                    )
                    self.workspace_service.write_markdown(
                        workspace / "testcases" / "testcases.md",
                        self._render_testcases_markdown(test_cases),
                    )
                    self.workspace_service.update_workspace_manifest(workspace)
                    st.success(f"Generated {len(test_cases)} manual test cases.")

            test_cases = load_testcases(workspace)
            st.caption(f"Manual test cases: {len(test_cases)}")
            if test_cases:
                st.dataframe(
                    [
                        {
                            "test_case_id": item.get("test_case_id", ""),
                            "module": item.get("module", ""),
                            "title": item.get("title", ""),
                            "priority": item.get("priority", ""),
                            "test_type": item.get("test_type", ""),
                            "status": item.get("status", ""),
                        }
                        for item in test_cases
                    ],
                    use_container_width=True,
                )
            else:
                st.info("No test cases found yet.")

            markdown_path = workspace / "testcases" / "testcases.md"
            if markdown_path.exists():
                st.expander("Test case Markdown preview").code(get_artifact_preview(markdown_path), language="markdown")

    def _render_suites_runs_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Suites & Runs")

            suite_files = list_suite_files(workspace)
            run_files = list_run_files(workspace)
            col1, col2 = st.columns(2)
            col1.write(f"Suite files: {len(suite_files)}")
            col2.write(f"Run files: {len(run_files)}")

            with st.form("create_suite_form"):
                suite_name = st.text_input("Suite name", value="smoke")
                create_suite = st.form_submit_button("Create suite from all test cases")
                if create_suite:
                    project_payload = load_project(workspace)
                    test_case_payloads = load_testcases(workspace)
                    if not project_payload:
                        st.warning("Create a project first.")
                    elif not test_case_payloads:
                        st.warning("Generate test cases first.")
                    else:
                        suite = self.suite_service.create_test_suite(
                            project_id=project_payload["project_id"],
                            name=suite_name,
                            test_cases=[item["test_case_id"] for item in test_case_payloads],
                        )
                        suite_slug = self._slug(suite_name) or suite.suite_id.lower()
                        self.workspace_service.write_json(workspace / "suites" / f"{suite_slug}.json", suite.to_dict())
                        self.workspace_service.write_markdown(
                            workspace / "suites" / f"{suite_slug}.md",
                            self.exporter.export_markdown_string(suite),
                        )
                        self.workspace_service.update_workspace_manifest(workspace)
                        st.success(f"Created suite {suite.suite_id}.")

            if suite_files:
                selected_suite = st.selectbox("Available suite files", options=suite_files)
                st.expander("Selected suite preview").code(
                    get_artifact_preview(workspace / selected_suite),
                    language="json",
                )
            else:
                selected_suite = None
                st.info("No suite files found yet.")

            with st.form("create_run_form"):
                environment = st.text_input("Environment", value="staging")
                build = st.text_input("Build", value="v1.0.0")
                tester = st.text_input("Tester", value="Manual QA")
                create_run = st.form_submit_button("Create run")
                if create_run:
                    if not selected_suite:
                        st.warning("Create or select a suite first.")
                    else:
                        project_payload = load_project(workspace)
                        suite = self._load_suite_model(workspace / selected_suite)
                        test_run = self.run_service.create_test_run(
                            project_id=project_payload.get("project_id", ""),
                            suite=suite,
                            environment=environment,
                            build=build,
                            tester=tester,
                        )
                        self.workspace_service.write_json(workspace / "runs" / f"{test_run.run_id}.json", test_run.to_dict())
                        self.workspace_service.write_markdown(
                            workspace / "runs" / f"{test_run.run_id}.md",
                            self.exporter.export_markdown_string(test_run),
                        )
                        self.workspace_service.update_workspace_manifest(workspace)
                        st.success(f"Created run {test_run.run_id}.")

            runs = load_runs(workspace)
            if runs:
                selected_run_file = st.selectbox("Available run files", options=list_run_files(workspace))
                selected_run_payload = safe_load_json_artifact(workspace / selected_run_file)
                run_summary = summarize_run_for_ui(selected_run_payload)
                with st.container(border=True):
                    st.write(f"Run ID: `{run_summary['run_id']}`")
                    st.write(f"Status: `{run_summary['status']}`")
                    st.write(
                        f"Results: total={run_summary['total']}, pass={run_summary['passed']}, "
                        f"fail={run_summary['failed']}, blocked={run_summary['blocked']}, "
                        f"skipped={run_summary['skipped']}, not_run={run_summary['not_run']}, "
                        f"retest={run_summary['retest']}"
                    )
                    st.write(f"Pass rate: {run_summary['pass_rate']}%")

                case_options = [
                    item.get("test_case_id", "")
                    for item in selected_run_payload.get("results", [])
                    if isinstance(item, dict) and item.get("test_case_id")
                ]
                with st.form("update_result_form"):
                    selected_case = st.selectbox("Test case ID", options=case_options) if case_options else None
                    status = st.selectbox(
                        "Status",
                        options=["Not Run", "Pass", "Fail", "Blocked", "Skipped", "Retest"],
                    )
                    actual_result = st.text_area("Actual result", height=120)
                    submitted = st.form_submit_button("Update result")
                    if submitted:
                        if not selected_case:
                            st.warning("Select a test case first.")
                        else:
                            run_model = self._load_run_model(workspace / selected_run_file)
                            updated_run = self.result_service.update_test_result(
                                run_model,
                                selected_case,
                                status,
                                actual_result=actual_result,
                            )
                            summary = self.summary_service.summarize_test_run(updated_run)
                            self.workspace_service.write_json(workspace / selected_run_file, updated_run.to_dict())
                            self.workspace_service.write_json(
                                workspace / "runs" / f"{updated_run.run_id}-summary.json",
                                summary.to_dict(),
                            )
                            self.workspace_service.write_markdown(
                                workspace / "runs" / f"{updated_run.run_id}-summary.md",
                                self.exporter.export_markdown_string(summary),
                            )
                            self.workspace_service.update_workspace_manifest(workspace)
                            st.success(f"Updated {selected_case} in {updated_run.run_id}.")

                st.expander("Selected run JSON preview").code(
                    get_artifact_preview(workspace / selected_run_file),
                    language="json",
                )
            else:
                st.info("No runs found yet. Create a suite, then create a run.")

    def _render_evidence_bugs_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Evidence & Bugs")
            run_files = list_run_files(workspace)
            if not run_files:
                st.info("No run files are available yet. Create a run before attaching evidence or generating bugs.")
            else:
                selected_run_file = st.selectbox("Run file", options=run_files)
                selected_run_payload = safe_load_json_artifact(workspace / selected_run_file)
                case_options = [
                    item.get("test_case_id", "")
                    for item in selected_run_payload.get("results", [])
                    if isinstance(item, dict) and item.get("test_case_id")
                ]
                selected_case = st.selectbox("Test case ID", options=case_options) if case_options else None

                with st.form("attach_evidence_form"):
                    evidence_type = st.selectbox(
                        "Evidence type",
                        options=["screenshot", "video", "log", "api_response", "note", "url", "file"],
                    )
                    evidence_path = st.text_input("Evidence path or URL")
                    evidence_description = st.text_input("Description")
                    attach = st.form_submit_button("Attach evidence")
                    if attach:
                        if not selected_case or not evidence_path.strip():
                            st.warning("Select a test case and provide an evidence path or URL.")
                        else:
                            run_model = self._load_run_model(workspace / selected_run_file)
                            evidence = self.evidence_service.attach_evidence(
                                run_model,
                                selected_case,
                                evidence_type,
                                evidence_path,
                                description=evidence_description,
                            )
                            self.workspace_service.write_json(workspace / selected_run_file, run_model.to_dict())
                            self.workspace_service.write_json(workspace / "evidence" / f"{evidence.evidence_id}.json", evidence.to_dict())
                            self.workspace_service.write_markdown(
                                workspace / "evidence" / f"{evidence.evidence_id}.md",
                                self.exporter.export_markdown_string(evidence),
                            )
                            self.workspace_service.update_workspace_manifest(workspace)
                            st.success(f"Attached evidence {evidence.evidence_id}.")

                if st.button("Generate bug draft"):
                    if not selected_case:
                        st.warning("Select a test case first.")
                    else:
                        run_model = self._load_run_model(workspace / selected_run_file)
                        test_case = self._find_test_case(workspace, selected_case)
                        evidence_items = self._find_evidence_for_case(workspace, run_model.run_id, selected_case)
                        try:
                            bug = self.bug_service.generate_bug_draft(
                                run_model,
                                selected_case,
                                test_case=test_case,
                                evidence=evidence_items,
                            )
                        except ValueError as exc:
                            st.warning(str(exc))
                        else:
                            self.workspace_service.write_json(workspace / "bugs" / f"{bug.bug_id}.json", bug.to_dict())
                            self.workspace_service.write_markdown(
                                workspace / "bugs" / f"{bug.bug_id}.md",
                                self.exporter.export_markdown_string(bug),
                            )
                            self.workspace_service.update_workspace_manifest(workspace)
                            st.success(f"Generated bug draft {bug.bug_id}.")

            bugs = load_bugs(workspace)
            bug_summary = summarize_bugs_for_ui(bugs)
            st.caption(f"Bug drafts: {bug_summary['count']}")
            if bugs:
                st.dataframe(
                    [
                        {
                            "bug_id": item.get("bug_id", ""),
                            "test_case_id": item.get("test_case_id", ""),
                            "severity": item.get("severity", ""),
                            "priority": item.get("priority", ""),
                            "status": item.get("status", ""),
                            "title": item.get("title", ""),
                        }
                        for item in bugs
                    ],
                    use_container_width=True,
                )
                bug_files = list_bug_files(workspace)
                selected_bug_file = st.selectbox("Bug file", options=bug_files)
                st.expander("Bug Markdown preview").code(
                    get_artifact_preview(workspace / selected_bug_file.replace(".json", ".md")),
                    language="markdown",
                )
            else:
                st.info("No bug drafts found yet.")

    def _render_failure_memory_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Failure Memory")
            st.caption("Phase 3B keeps failure memory local and file-based. This tab is read-only in the UI prototype.")
            records = load_failure_memory_records(workspace)
            if records:
                st.dataframe(records, use_container_width=True)
            else:
                st.info("No failure memory artifacts found yet.")

    def _render_automation_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Automation Candidates")
            if st.button("Score automation candidates"):
                test_cases = [ManualTestCase(**item) for item in load_testcases(workspace)]
                if not test_cases:
                    st.warning("Generate test cases first.")
                else:
                    candidates = self.automation_service.score_automation_candidates(
                        test_cases,
                        failure_records=self._load_failure_record_models(workspace),
                    )
                    self.workspace_service.write_json(
                        workspace / "automation_candidates" / "candidates.json",
                        [item.to_dict() for item in candidates],
                    )
                    self.workspace_service.write_markdown(
                        workspace / "automation_candidates" / "candidates.md",
                        self.exporter.export_markdown_string(candidates),
                    )
                    self.workspace_service.update_workspace_manifest(workspace)
                    st.success(f"Scored {len(candidates)} automation candidates.")

            candidates = load_automation_candidates(workspace)
            candidate_summary = summarize_candidates_for_ui(candidates)
            st.caption(
                f"Candidates: {candidate_summary['count']} | Average score: {candidate_summary['average_score']}"
            )
            if candidates:
                st.dataframe(
                    [
                        {
                            "candidate_id": item.get("candidate_id", ""),
                            "test_case_id": item.get("test_case_id", ""),
                            "score": item.get("score", 0),
                            "recommendation": item.get("recommendation", ""),
                            "suggested_automation_type": item.get("suggested_automation_type", ""),
                            "reasons": "; ".join(item.get("reasons", [])),
                            "blockers": "; ".join(item.get("blockers", [])),
                        }
                        for item in candidates
                    ],
                    use_container_width=True,
                )
                candidate_files = list_candidate_files(workspace)
                selected_candidate_file = st.selectbox("Candidate artifact", options=candidate_files)
                st.expander("Candidate artifact preview").code(
                    get_artifact_preview(workspace / selected_candidate_file),
                    language="json",
                )
                markdown_path = workspace / "automation_candidates" / "candidates.md"
                if markdown_path.exists():
                    st.expander("Candidate Markdown preview").code(
                        get_artifact_preview(markdown_path),
                        language="markdown",
                    )
            else:
                st.info("No automation candidates found yet.")

    def _render_reports_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Reports")
            if st.button("Write workspace summary report"):
                summary = get_workspace_summary(workspace)
                output = {
                    "workspace_path": summary["workspace_path"],
                    "project": summary["project"],
                    "manifest": summary["manifest"],
                    "artifact_counts": summary["artifact_counts"],
                    "validation": summary["validation"],
                }
                self.workspace_service.write_json(workspace / "reports" / "workspace_summary.json", output)
                self.workspace_service.write_markdown(
                    workspace / "reports" / "workspace_summary.md",
                    self._render_workspace_summary_markdown(summary),
                )
                self.workspace_service.update_workspace_manifest(workspace)
                st.success("Workspace summary report written.")

            report_files = list_report_files(workspace)
            if report_files:
                selected_report = st.selectbox("Report file", options=report_files)
                preview_path = workspace / selected_report
                language = "markdown" if selected_report.endswith(".md") else "json"
                st.code(get_artifact_preview(preview_path), language=language)
            else:
                st.info("No reports found yet.")

            if st.button("Generate script readiness report"):
                test_cases = [ManualTestCase(**item) for item in load_testcases(workspace)]
                if not test_cases:
                    st.warning("Generate manual test cases first.")
                else:
                    candidates = [AutomationCandidate(**item) for item in load_automation_candidates(workspace)]
                    project = load_project(workspace)
                    readiness_items = self.script_readiness_service.analyze_script_readiness_batch(
                        test_cases,
                        automation_candidates=candidates,
                        project_type_hint=project.get("product_type", ""),
                    )
                    self.workspace_service.write_json(
                        workspace / "reports" / "script_readiness.json",
                        [item.to_dict() for item in readiness_items],
                    )
                    self.workspace_service.write_markdown(
                        workspace / "reports" / "script_readiness.md",
                        self.exporter.export_markdown_string(readiness_items),
                    )
                    self.workspace_service.update_workspace_manifest(workspace)
                    st.success(f"Generated script readiness report for {len(readiness_items)} test cases.")

            readiness_items = load_script_readiness_items(workspace)
            if readiness_items:
                ready = len([item for item in readiness_items if item.get("readiness_status") == "Ready"])
                needs_more_data = len(
                    [item for item in readiness_items if item.get("readiness_status") == "Needs More Data"]
                )
                not_suitable = len(
                    [item for item in readiness_items if item.get("readiness_status") == "Not Suitable"]
                )
                st.caption(
                    f"Script readiness: total={len(readiness_items)}, ready={ready}, "
                    f"needs_more_data={needs_more_data}, not_suitable={not_suitable}"
                )

            if st.button("Generate API script drafts"):
                test_cases = [ManualTestCase(**item) for item in load_testcases(workspace)]
                readiness_payloads = load_script_readiness_items(workspace)
                readiness_items = [
                    ScriptGenerationReadiness(**{
                        **item,
                        "gaps": item.get("gaps", []),
                    })
                    for item in readiness_payloads
                    if isinstance(item, dict)
                ]
                drafts = self.api_script_generator.generate_api_script_drafts(
                    test_cases,
                    readiness_items=readiness_items,
                )
                output_dir = workspace / "script_drafts" / "api"
                output_dir.mkdir(parents=True, exist_ok=True)
                self.workspace_service.write_json(
                    output_dir / "api_script_drafts.json",
                    [item.to_dict() for item in drafts],
                )
                self.workspace_service.write_markdown(
                    output_dir / "api_script_drafts.md",
                    self.exporter.export_markdown_string(drafts),
                )
                for draft in drafts:
                    self.workspace_service.write_markdown(output_dir / draft.file_name, draft.script_content)
                self.workspace_service.update_workspace_manifest(workspace)
                st.success(f"Generated {len(drafts)} API draft artifacts.")

            if st.button("Validate API drafts"):
                draft_payloads = load_api_script_drafts(workspace)
                if not draft_payloads:
                    st.warning("No API draft artifacts were found.")
                else:
                    drafts = [APITestScriptDraft(**item) for item in draft_payloads if isinstance(item, dict)]
                    validation_results = self.api_script_validation_service.validate_api_script_drafts(drafts)
                    output_dir = workspace / "script_drafts" / "api"
                    output_dir.mkdir(parents=True, exist_ok=True)
                    self.workspace_service.write_json(
                        output_dir / "api_script_validation.json",
                        [item.to_dict() for item in validation_results],
                    )
                    self.workspace_service.write_markdown(
                        output_dir / "api_script_validation.md",
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
                    self.workspace_service.write_json(
                        output_dir / "api_script_package_manifest.json",
                        package_manifest.to_dict(),
                    )
                    self.workspace_service.write_markdown(
                        output_dir / "api_script_package_manifest.md",
                        self.exporter.export_markdown_string(package_manifest),
                    )
                    self.workspace_service.update_workspace_manifest(workspace)
                    st.success(
                        f"Validated {len(validation_results)} API draft artifacts. "
                        f"Package status: {package_manifest.status}"
                    )

            api_draft_files = list_api_draft_files(workspace)
            api_drafts = load_api_script_drafts(workspace)
            if api_drafts:
                st.caption(f"API script drafts: {len(api_drafts)}")
            if api_draft_files:
                selected_api_draft = st.selectbox("API draft artifact", options=api_draft_files)
                language = "python" if selected_api_draft.endswith(".py") else ("markdown" if selected_api_draft.endswith(".md") else "json")
                st.code(get_artifact_preview(workspace / selected_api_draft), language=language)

            validation_results = load_api_script_validation_results(workspace)
            package_manifest = load_api_script_package_manifest(workspace)
            if validation_results:
                st.caption(f"API draft validation results: {len(validation_results)}")
            if package_manifest:
                st.write(f"API draft package status: `{package_manifest.get('status', 'Unknown')}`")
            validation_files = list_api_validation_files(workspace)
            if validation_files:
                selected_validation_file = st.selectbox("API validation artifact", options=validation_files)
                language = "markdown" if selected_validation_file.endswith(".md") else "json"
                st.code(get_artifact_preview(workspace / selected_validation_file), language=language)

    def _load_suite_model(self, path: Path) -> TestSuite:
        return TestSuite(**self.workspace_service.read_json(path))

    def _load_requirement_models(self, workspace: Path) -> list[NormalizedRequirement]:
        return [NormalizedRequirement(**payload) for payload in load_requirements(workspace)]

    def _load_run_model(self, path: Path) -> TestRun:
        payload = self.workspace_service.read_json(path)
        results = [TestResult(**item) for item in payload.get("results", [])]
        data = dict(payload)
        data["results"] = results
        return TestRun(**data)

    def _find_test_case(self, workspace: Path, test_case_id: str) -> ManualTestCase | None:
        for payload in load_testcases(workspace):
            if payload.get("test_case_id") == test_case_id:
                return ManualTestCase(**payload)
        return None

    def _find_evidence_for_case(self, workspace: Path, run_id: str, test_case_id: str) -> list[Evidence]:
        evidence_dir = workspace / "evidence"
        items: list[Evidence] = []
        if not evidence_dir.exists():
            return items
        for path in sorted(evidence_dir.glob("*.json")):
            payload = safe_load_json_artifact(path)
            if payload.get("run_id") == run_id and payload.get("test_case_id") == test_case_id:
                items.append(Evidence(**payload))
        return items

    def _load_failure_record_models(self, workspace: Path) -> list[FailureRecord]:
        records: list[FailureRecord] = []
        for payload in load_failure_memory_records(workspace):
            if "record_id" not in payload or "signature" not in payload:
                continue
            signature = FailureSignature(**payload["signature"])
            data = dict(payload)
            data["signature"] = signature
            records.append(FailureRecord(**data))
        return records

    def _render_workspace_summary_markdown(self, summary: dict[str, Any]) -> str:
        validation = summary["validation"]
        lines = [
            "# Workspace Summary",
            "",
            f"- Workspace Path: {summary['workspace_path']}",
            f"- Exists: {summary['exists']}",
            f"- Artifact Counts: {format_artifact_count_summary(summary['artifact_counts'])}",
            f"- Validation: {validation['message']}",
            "",
            "## Next Recommended Actions",
        ]
        lines.extend(f"- {action}" for action in get_next_recommended_actions(summary["workspace_path"]))
        lines.append("")
        return "\n".join(lines)

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

    def _slug(self, value: str) -> str:
        text = "".join(char.lower() if char.isalnum() else "-" for char in value.strip())
        while "--" in text:
            text = text.replace("--", "-")
        return text.strip("-")


def _require_streamlit() -> Any:
    try:
        import streamlit as st  # type: ignore
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Streamlit is not installed. Install it with `pip install streamlit`, then run "
            "`streamlit run orchestrator/manual_qa/ui_streamlit.py`."
        ) from exc
    return st


def main() -> int:
    try:
        st = _require_streamlit()
    except RuntimeError as exc:
        print(str(exc))
        return 1

    ManualQAStreamlitUI().render(st)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
