# Manual QA Streamlit UI Usage

## Run
If Streamlit is not installed yet:

```powershell
pip install streamlit
```

Run the local UI:

```powershell
streamlit run orchestrator/manual_qa/ui_streamlit.py
```

## Recommended Workspace Path
Use a local workspace such as:

```text
artifacts/manual_qa_demo
```

## Expected Workflow
Use the UI in this order:

1. Initialize workspace
2. Create project
3. Import requirements
4. Generate checklist
5. Generate test cases
6. Create suite
7. Create run
8. Update one or more results
9. Attach evidence
10. Generate bug draft
11. Score automation candidates

You can also use the sidebar `Run demo workflow` action to generate a deterministic local demo workspace.

## Notes
- The UI is local-only.
- There is no authentication.
- There is no API server dependency.
- There is no automation script generation or automation execution in this phase.
- Workspace persistence is limited to local JSON and Markdown artifacts.
