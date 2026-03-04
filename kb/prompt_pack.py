from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from kb._lib.paths import load_kb_config
from kb._lib.types import SearchHit
from kb.query_kb import search_domain


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a compact KB context pack for a pipeline step.")
    parser.add_argument("--domain", required=True, help="Domain name.")
    parser.add_argument("--step", required=True, help="Step number, for example 01.")
    parser.add_argument("--out", required=True, help="Output file path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    content = generate_prompt_pack(args.domain, normalize_step(args.step))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    print(f"KB context pack written: {out_path}")
    return 0


def generate_prompt_pack(domain: str, step: str) -> str:
    cfg = load_kb_config(domain)
    queries = cfg.domain.step_queries.get(step, [])
    top_k = cfg.domain.top_k_per_step.get(step, cfg.default_top_k)
    merged: dict[str, SearchHit] = {}
    for query in queries:
        for hit in search_domain(domain, query, top_k):
            existing = merged.get(hit.chunk_id)
            if existing is None or hit.score > existing.score:
                merged[hit.chunk_id] = hit

    hits = sorted(merged.values(), key=lambda item: item.score, reverse=True)
    if not hits:
        return "\n".join(
            [
                f"KB context pack for {domain} step {step}",
                "",
                "- No relevant KB excerpts were found for the configured queries.",
                "",
                "Use UNKNOWN for business facts that are not present in the KB context.",
                "",
            ]
        )

    summary_lines = summarize_hits(hits[:5])
    body = [
        f"KB context pack for {domain} step {step}",
        "",
        "Summary:",
    ]
    body.extend(f"- {line}" for line in summary_lines)
    body.extend(["", "Excerpts:"])
    max_chars = cfg.max_pack_chars
    current_len = sum(len(line) + 1 for line in body)
    for hit in hits:
        block = format_excerpt(hit)
        addition = len(block) + 2
        if current_len + addition > max_chars and current_len > 0:
            continue
        body.extend(["", block])
        current_len += addition
    return "\n".join(body).strip() + "\n"


def summarize_hits(hits: list[SearchHit]) -> list[str]:
    summaries: list[str] = []
    seen = set()
    for hit in hits:
        if hit.headings:
            summary = " > ".join(hit.headings)
        else:
            summary = first_sentence(hit.text)
        summary = summary.strip()
        if not summary or summary in seen:
            continue
        seen.add(summary)
        summaries.append(summary)
    return summaries or ["Relevant business excerpts retrieved from the local KB."]


def format_excerpt(hit: SearchHit) -> str:
    headings = " > ".join(hit.headings) if hit.headings else "(no headings)"
    return "\n".join(
        [
            "-----",
            hit.text.strip(),
            f"[SOURCE: {hit.source_file} | CHUNK: {hit.chunk_id} | SCORE: {hit.score:.4f} | HEADINGS: {headings}]",
        ]
    )


def first_sentence(text: str) -> str:
    for separator in (". ", "\n", "; "):
        if separator in text:
            return text.split(separator, 1)[0].strip()
    return text.strip()[:120]


def normalize_step(step: str) -> str:
    return f"{int(step):02d}"


if __name__ == "__main__":
    sys.exit(main())
