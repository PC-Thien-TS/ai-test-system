# Didaunao Release Audit Inputs

Place the source business-standard documents for this domain here before building the local KB.

Expected primary file:

- `产品上线自检手册_V3-行业通用版.docx`

Workflow:

1. Copy the DOCX into this folder.
2. Run `python kb/build_kb.py --domain didaunao_release_audit`.
3. Run `python scripts/run_domain_manual.py --domain didaunao_release_audit --run-id <run_id>`.

The KB pipeline is offline-only. The embedding model must already be available locally.
