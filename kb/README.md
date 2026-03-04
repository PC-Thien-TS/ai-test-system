# Local KB (RAG)

This KB module builds and queries a fully local index from business docs under `requirements/<domain>/`.

## Offline Assumption

- Runtime is offline only.
- KB scripts never call OpenAI APIs.
- The embedding model must already exist locally, either:
  - at the configured `embedding_local_path`, or
  - in the local Hugging Face cache, loaded with `local_files_only=True`.

The scripts set `HF_HUB_OFFLINE=1` and `TRANSFORMERS_OFFLINE=1` before loading the model.

## Required Packages

Install locally in your own environment:

- `sentence-transformers`
- `python-docx`
- `PyYAML`
- `numpy`
- `faiss-cpu` or `hnswlib`

Windows note:
- If FAISS is difficult to install, set `index_backend: hnsw` in `kb/config.yaml` and install `hnswlib`.

## Input and Output

Input docs:
- `requirements/<domain>/*.docx`
- `requirements/<domain>/*.md`
- `requirements/<domain>/*.txt`

Index output:
- `kb/index/<domain>/faiss.index` or `kb/index/<domain>/hnsw.bin`
- `kb/index/<domain>/meta.jsonl`
- `kb/index/<domain>/manifest.json`
- `kb/index/<domain>/BUILD_REPORT.md`

## Commands

Build:

```powershell
python kb/build_kb.py --domain store_verify
```

Query:

```powershell
python kb/query_kb.py --domain store_verify --q "status transitions approve reject" --k 5
python kb/query_kb.py --domain store_verify --q "status transitions approve reject" --k 5 --json
```

Generate a step-specific context pack:

```powershell
python kb/prompt_pack.py --domain store_verify --step 03 --out outputs/store_verify/demo_verify/kb_context_step03.txt
```

## Retrieval Behavior

- DOCX content is extracted with `python-docx`.
- Markdown headings are preserved as chunk metadata.
- Text is chunked by character windows with overlap.
- Each chunk is embedded locally with a sentence-transformers model.
- Retrieval returns top-k relevant chunks.
- `prompt_pack.py` merges hits from curated step queries, trims to `max_pack_chars`, and writes a compact pack with citations.
