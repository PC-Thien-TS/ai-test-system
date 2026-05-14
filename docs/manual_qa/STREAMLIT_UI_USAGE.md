# Manual QA Streamlit UI Usage

## Install
If Streamlit is not installed yet:

```powershell
pip install streamlit
```

## Run
Start the local UI:

```powershell
streamlit run orchestrator/manual_qa/ui_streamlit.py
```

## Recommended Workspace Path
Use a local workspace such as:

```text
artifacts/manual_qa_demo
```

## Step-by-Step UI Workflow
Use the UI in this order:

1. Initialize workspace from the sidebar.
2. Create a project in the `Project` tab.
3. Import requirements in the `Requirements` tab.
4. Generate checklist items in the `Checklist` tab.
5. Generate manual test cases in the `Test Cases` tab.
6. Create a suite in `Suites & Runs`.
7. Create a run in `Suites & Runs`.
8. Update one or more results in `Suites & Runs`.
9. Attach evidence metadata in `Evidence & Bugs`.
10. Generate bug drafts in `Evidence & Bugs`.
11. Score automation candidates in `Automation Candidates`.
12. Review workspace reports in `Reports`.

## Demo Workflow
The sidebar includes `Run demo workflow`.

This creates a deterministic local demo workspace with:
- project
- normalized requirements
- checklist
- manual test cases
- suite
- run
- failed result
- evidence metadata
- bug draft
- automation candidates
- demo report

Use this when you want a working sample workspace quickly.

## Troubleshooting
- If the workspace does not exist yet, use `Initialize workspace` first.
- If a tab shows a friendly empty state, complete the previous workflow step first.
- If Streamlit is missing, install it with `pip install streamlit`.
- If a preview is missing, confirm the related JSON or Markdown artifact has been generated.
- If bug draft generation warns about status, update the run result to `Fail`, `Blocked`, or `Retest` first.

## Notes and Limitations
- This UI is local-only.
- There is no authentication.
- There is no API server dependency.
- There is no multi-user or concurrency handling.
- Persistence is limited to local JSON and Markdown artifacts.
- Automation candidates are recommendations only.
- No automation scripts are generated in this phase.
- No automation is executed in this phase.
