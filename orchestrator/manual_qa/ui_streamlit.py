"""Simple local Streamlit UI for the Manual QA workspace workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.manual_qa.automation_candidate_service import AutomationCandidateService
from orchestrator.manual_qa.bug_service import BugDraftService
from orchestrator.manual_qa.checklist_generator import ChecklistGenerator
from orchestrator.manual_qa.demo_service import DemoWorkflowService
from orchestrator.manual_qa.evidence_service import EvidenceService
from orchestrator.manual_qa.exporters import ManualQAExporter
from orchestrator.manual_qa.failure_memory_service import FailureRecord, FailureSignature
from orchestrator.manual_qa.models import Evidence, ManualTestCase, NormalizedRequirement, TestResult, TestRun, TestSuite
from orchestrator.manual_qa.project_service import ProjectProfileService, SUPPORTED_PRODUCT_TYPES
from orchestrator.manual_qa.requirement_importer import RequirementImporter
from orchestrator.manual_qa.requirement_normalizer import RequirementNormalizer
from orchestrator.manual_qa.result_service import TestResultService
from orchestrator.manual_qa.run_service import TestRunService
from orchestrator.manual_qa.summary_service import RunSummaryService
from orchestrator.manual_qa.suite_service import TestSuiteService
from orchestrator.manual_qa.testcase_generator import ManualTestCaseGenerator
from orchestrator.manual_qa.ui_helpers import (
    format_artifact_count_summary,
    get_workspace_summary,
    load_automation_candidates,
    load_bugs,
    load_checklist,
    load_failure_memory_records,
    load_project,
    load_requirements,
    load_runs,
    load_suites,
    load_testcases,
    resolve_workspace,
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
        self.evidence_service = EvidenceService()
        self.bug_service = BugDraftService()
        self.automation_service = AutomationCandidateService()
        self.demo_service = DemoWorkflowService()
        self.exporter = ManualQAExporter()

    def render(self, st: Any) -> None:
        st.set_page_config(page_title="Manual QA Workspace", layout="wide")
        st.title("Manual QA Workspace")

        workspace_input = st.sidebar.text_input(
            "Workspace path",
            value="artifacts/manual_qa_demo",
        )
        workspace = resolve_workspace(workspace_input)

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

        summary = get_workspace_summary(workspace)
        st.sidebar.markdown("### Workspace Summary")
        st.sidebar.caption(str(workspace))
        st.sidebar.write(summary["artifact_count_summary"])
        st.sidebar.write(summary["validation"]["message"])

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

    def _render_project_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Project")
            project_name = st.text_input("Project name", value="Manual QA Demo")
            product_type = st.selectbox(
                "Product type",
                options=sorted(SUPPORTED_PRODUCT_TYPES),
                index=sorted(SUPPORTED_PRODUCT_TYPES).index("web"),
            )
            if st.button("Create project"):
                self.workspace_service.create_workspace(workspace)
                project = self.project_service.create_project_profile(
                    name=project_name,
                    product_type=product_type,
                )
                self.workspace_service.write_json(workspace / "project.json", project.to_dict())
                self.workspace_service.update_workspace_manifest(workspace, project=project)
                st.success("Project created.")

            project = load_project(workspace)
            if project:
                st.json(project)
            else:
                st.info("No project.json found yet.")

    def _render_requirements_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Requirements")
            requirement_text = st.text_area("Requirement text", height=220)
            uploaded_file = st.file_uploader("Optional requirements file", type=["txt", "md"])
            if st.button("Import requirements"):
                payload = requirement_text
                if uploaded_file is not None:
                    payload = uploaded_file.getvalue().decode("utf-8")
                if not str(payload or "").strip():
                    st.warning("Provide requirement text or upload a .txt/.md file.")
                else:
                    self.workspace_service.create_workspace(workspace)
                    raw_records = self.importer.import_requirements(payload, source_ref="streamlit-ui")
                    requirements = self.normalizer.normalize_requirements(raw_records)
                    output_path = workspace / "requirements" / "normalized_requirements.json"
                    self.workspace_service.write_json(output_path, [item.to_dict() for item in requirements])
                    self.workspace_service.update_workspace_manifest(workspace)
                    st.success(f"Imported {len(requirements)} normalized requirements.")

            requirements = load_requirements(workspace)
            if requirements:
                st.write(requirements)
            else:
                st.info("No normalized requirements found yet.")

    def _render_checklist_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Checklist")
            if st.button("Generate checklist"):
                requirements = load_requirements(workspace)
                if not requirements:
                    st.warning("Import requirements first.")
                else:
                    checklist = self.checklist_generator.generate(self._load_requirement_models(workspace))
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
            if checklist:
                st.write(checklist)
            else:
                st.info("No checklist artifacts found yet.")
            markdown_path = workspace / "checklists" / "checklist.md"
            if markdown_path.exists():
                st.code(self.workspace_service.read_text(markdown_path), language="markdown")

    def _render_testcases_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Test Cases")
            if st.button("Generate test cases"):
                requirements = load_requirements(workspace)
                if not requirements:
                    st.warning("Import requirements first.")
                else:
                    test_cases = self.testcase_generator.generate(self._load_requirement_models(workspace))
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
            if test_cases:
                st.write(test_cases)
            else:
                st.info("No test case artifacts found yet.")
            markdown_path = workspace / "testcases" / "testcases.md"
            if markdown_path.exists():
                st.code(self.workspace_service.read_text(markdown_path), language="markdown")

    def _render_suites_runs_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Suites & Runs")
            suite_name = st.text_input("Suite name", value="smoke")
            if st.button("Create suite from all test cases"):
                project_payload = load_project(workspace)
                test_case_payloads = load_testcases(workspace)
                if not project_payload or not test_case_payloads:
                    st.warning("Create a project and generate test cases first.")
                else:
                    suite = self.suite_service.create_test_suite(
                        project_id=project_payload["project_id"],
                        name=suite_name,
                        test_cases=[item["test_case_id"] for item in test_case_payloads],
                    )
                    slug = self._slug(suite_name) or suite.suite_id.lower()
                    self.workspace_service.write_json(workspace / "suites" / f"{slug}.json", suite.to_dict())
                    self.workspace_service.write_markdown(
                        workspace / "suites" / f"{slug}.md",
                        self.exporter.export_markdown_string(suite),
                    )
                    self.workspace_service.update_workspace_manifest(workspace)
                    st.success(f"Created suite {suite.suite_id}.")

            suite_files = self._artifact_options(workspace, "suites")
            selected_suite = st.selectbox("Suite file", options=suite_files) if suite_files else None
            if not suite_files:
                st.info("No suite files found yet.")
            environment = st.text_input("Environment", value="staging")
            build = st.text_input("Build", value="v1.0.0")
            tester = st.text_input("Tester", value="Manual QA")
            if st.button("Create run"):
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

            run_files = self._artifact_options(workspace, "runs", suffix=".json", exclude_suffix="-summary.json")
            selected_run = st.selectbox("Run file", options=run_files) if run_files else None
            selected_run_payload = self._load_run_payload(workspace / selected_run) if selected_run else {}
            case_options = [item["test_case_id"] for item in selected_run_payload.get("results", [])]
            selected_case = st.selectbox("Test case ID", options=case_options) if case_options else None
            result_status = st.selectbox(
                "Status",
                options=["Not Run", "Pass", "Fail", "Blocked", "Skipped", "Retest"],
            )
            actual_result = st.text_area("Actual result", height=120)
            if st.button("Update result"):
                if not selected_run or not selected_case:
                    st.warning("Create or select a run and test case first.")
                else:
                    run_model = self._load_run_model(workspace / selected_run)
                    updated_run = self.result_service.update_test_result(
                        run_model,
                        selected_case,
                        result_status,
                        actual_result=actual_result,
                    )
                    summary = self.summary_service.summarize_test_run(updated_run)
                    run_path = workspace / selected_run
                    self.workspace_service.write_json(run_path, updated_run.to_dict())
                    self.workspace_service.write_json(
                        workspace / "runs" / f"{updated_run.run_id}-summary.json",
                        summary.to_dict(),
                    )
                    self.workspace_service.write_markdown(
                        workspace / "runs" / f"{updated_run.run_id}-summary.md",
                        self.exporter.export_markdown_string(summary),
                    )
                    self.workspace_service.update_workspace_manifest(workspace)
                    st.success(f"Updated {selected_case} in run {updated_run.run_id}.")

            if selected_run:
                run_model = self._load_run_model(workspace / selected_run)
                summary = self.summary_service.summarize_test_run(run_model)
                st.write(summary.to_dict())

    def _render_evidence_bugs_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Evidence & Bugs")
            run_files = self._artifact_options(workspace, "runs", suffix=".json", exclude_suffix="-summary.json")
            selected_run = st.selectbox("Run file for evidence/bug", options=run_files) if run_files else None
            selected_run_payload = self._load_run_payload(workspace / selected_run) if selected_run else {}
            case_options = [item["test_case_id"] for item in selected_run_payload.get("results", [])]
            selected_case = st.selectbox("Test case for evidence/bug", options=case_options) if case_options else None
            evidence_type = st.selectbox(
                "Evidence type",
                options=["screenshot", "video", "log", "api_response", "note", "url", "file"],
            )
            evidence_path = st.text_input("Evidence path or URL", value="")
            evidence_description = st.text_input("Evidence description", value="")

            if st.button("Attach evidence"):
                if not selected_run or not selected_case or not evidence_path.strip():
                    st.warning("Select a run, case, and evidence reference.")
                else:
                    run_model = self._load_run_model(workspace / selected_run)
                    evidence = self.evidence_service.attach_evidence(
                        run_model,
                        selected_case,
                        evidence_type,
                        evidence_path,
                        description=evidence_description,
                    )
                    self.workspace_service.write_json(workspace / selected_run, run_model.to_dict())
                    self.workspace_service.write_json(
                        workspace / "evidence" / f"{evidence.evidence_id}.json",
                        evidence.to_dict(),
                    )
                    self.workspace_service.write_markdown(
                        workspace / "evidence" / f"{evidence.evidence_id}.md",
                        self.exporter.export_markdown_string(evidence),
                    )
                    self.workspace_service.update_workspace_manifest(workspace)
                    st.success(f"Attached evidence {evidence.evidence_id}.")

            if st.button("Generate bug draft"):
                if not selected_run or not selected_case:
                    st.warning("Select a run and test case first.")
                else:
                    run_model = self._load_run_model(workspace / selected_run)
                    test_case = self._find_test_case(workspace, selected_case)
                    evidence_items = self._find_evidence_for_case(workspace, run_model.run_id, selected_case)
                    bug = self.bug_service.generate_bug_draft(
                        run_model,
                        selected_case,
                        test_case=test_case,
                        evidence=evidence_items,
                    )
                    self.workspace_service.write_json(workspace / "bugs" / f"{bug.bug_id}.json", bug.to_dict())
                    self.workspace_service.write_markdown(
                        workspace / "bugs" / f"{bug.bug_id}.md",
                        self.exporter.export_markdown_string(bug),
                    )
                    self.workspace_service.update_workspace_manifest(workspace)
                    st.success(f"Generated bug draft {bug.bug_id}.")

            bugs = load_bugs(workspace)
            if bugs:
                st.write(bugs)
            else:
                st.info("No bug drafts found yet.")

    def _render_failure_memory_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Failure Memory")
            records = load_failure_memory_records(workspace)
            if records:
                st.write(records)
            else:
                st.info("No failure memory artifacts found. This tab is read-only in Phase 6A.")

    def _render_automation_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Automation Candidates")
            if st.button("Score automation candidates"):
                test_cases = [ManualTestCase(**item) for item in load_testcases(workspace)]
                if not test_cases:
                    st.warning("Generate test cases first.")
                else:
                    failure_records = self._load_failure_record_models(workspace)
                    candidates = self.automation_service.score_automation_candidates(
                        test_cases,
                        failure_records=failure_records,
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
            if candidates:
                st.write(candidates)
            else:
                st.info("No automation candidate artifacts found yet.")
            markdown_path = workspace / "automation_candidates" / "candidates.md"
            if markdown_path.exists():
                st.code(self.workspace_service.read_text(markdown_path), language="markdown")

    def _render_reports_tab(self, st: Any, tab: Any, workspace: Path) -> None:
        with tab:
            st.subheader("Reports")
            if st.button("Workspace summary"):
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

            summary = get_workspace_summary(workspace)
            st.write(format_artifact_count_summary(summary["artifact_counts"]))
            report_files = summary["reports"]
            if report_files:
                st.write(report_files)
            else:
                st.info("No report artifacts found yet.")

            demo_report_path = workspace / "reports" / "demo_workflow_report.md"
            if demo_report_path.exists():
                st.code(self.workspace_service.read_text(demo_report_path), language="markdown")

    def _artifact_options(
        self,
        workspace: Path,
        folder: str,
        *,
        suffix: str = ".json",
        exclude_suffix: str | None = None,
    ) -> list[str]:
        listing = self.workspace_service.list_workspace_artifacts(workspace)
        options = []
        for item in listing["artifacts"].get(folder, []):
            if suffix and not item.endswith(suffix):
                continue
            if exclude_suffix and item.endswith(exclude_suffix):
                continue
            options.append(item)
        return options

    def _load_suite_model(self, path: Path) -> TestSuite:
        return TestSuite(**self.workspace_service.read_json(path))

    def _load_requirement_models(self, workspace: Path) -> list[NormalizedRequirement]:
        return [NormalizedRequirement(**payload) for payload in load_requirements(workspace)]

    def _load_run_payload(self, path: Path | None) -> dict[str, Any]:
        if path is None or not path.exists():
            return {}
        payload = self.workspace_service.read_json(path)
        return payload if isinstance(payload, dict) else {}

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

    def _find_evidence_for_case(self, workspace: Path, run_id: str, test_case_id: str) -> list[Any]:
        evidence_dir = workspace / "evidence"
        items: list[Evidence] = []
        if not evidence_dir.exists():
            return items
        for path in sorted(evidence_dir.glob("*.json")):
            payload = self.workspace_service.read_json(path)
            if payload.get("run_id") == run_id and payload.get("test_case_id") == test_case_id:
                items.append(Evidence(**payload))
        return items

    def _load_failure_record_models(self, workspace: Path) -> list[FailureRecord]:
        records = []
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
            f"- Artifact Counts: {summary['artifact_count_summary']}",
            f"- Validation: {validation['message']}",
            "",
        ]
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
