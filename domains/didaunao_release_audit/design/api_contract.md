# Didaunao Release Audit API and Metrics Notes

This file is a code-facts helper for the release-audit domain.

- Business truth must still come from the KB context pack generated from `requirements/didaunao_release_audit/`.
- `python scripts/collect_release_evidence.py --run-dir outputs/didaunao_release_audit/<run_id>` can regenerate this file from local source repos listed in `evidence_sources.yaml`.
- Use this file only for implementation facts such as endpoint surfaces, route names, controller exposure, and authorization hints.
- If the KB context does not state a business fact, mark it as `UNKNOWN`.
