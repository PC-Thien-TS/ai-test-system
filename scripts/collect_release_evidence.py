from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from integrations.repo_scanner.dotnet_api_extract import extract_dotnet_api
from integrations.repo_scanner.scan_repo import scan_repo


DEFAULT_DOTNET_GLOB = "CoreV2.MVC/Api/**/*Controller.cs"


@dataclass(frozen=True)
class EvidenceCollectionResult:
    warnings: list[str]
    source_outputs: list[dict[str, Any]]
    api_contract_updated: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect source-backed release evidence for a run.")
    parser.add_argument("--run-dir", required=True, help="Path to outputs/didaunao_release_audit/<run_id>")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir).resolve()
    try:
        result = collect_release_evidence(run_dir)
    except (FileNotFoundError, ValueError) as exc:
        print(f"[FAIL] {exc}")
        return 1

    for warning in result.warnings:
        print(f"[WARN] {warning}")
    print(f"Evidence collection finished: {run_dir / 'evidence'}")
    return 0


def collect_release_evidence(run_dir: Path) -> EvidenceCollectionResult:
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory does not exist: {run_dir}")

    meta = read_json_if_present(run_dir / "run_meta.json")
    domain = str(meta.get("domain") or run_dir.parent.name)
    if domain != "didaunao_release_audit":
        raise ValueError(
            "collect_release_evidence.py currently supports only outputs/didaunao_release_audit/<run_id>."
        )

    config_path = REPO_ROOT / "evidence_sources.yaml"
    if not config_path.exists():
        return EvidenceCollectionResult(
            warnings=["evidence_sources.yaml is missing. Source-backed evidence was skipped."],
            source_outputs=[],
            api_contract_updated=False,
        )

    config = load_sources_config(config_path)
    warnings: list[str] = []
    source_outputs: list[dict[str, Any]] = []
    evidence_dir = run_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    for source in config:
        source_name = str(source.get("name") or "").strip()
        raw_path = str(source.get("path") or "").strip()
        source_kind = str(source.get("kind") or "").strip().lower()
        if not source_name or not raw_path:
            warnings.append("One evidence source entry is missing 'name' or 'path'; it was skipped.")
            continue

        local_path = Path(raw_path).expanduser()
        source_dir = evidence_dir / source_name
        source_dir.mkdir(parents=True, exist_ok=True)

        snapshot = scan_repo(source_name, local_path)
        write_json(source_dir / "repo_snapshot.json", snapshot)

        dotnet_payload = None
        if source_kind == "dotnet" and snapshot["exists"]:
            glob_pattern = str(source.get("glob") or source.get("controller_glob") or DEFAULT_DOTNET_GLOB)
            dotnet_payload = extract_dotnet_api(local_path, glob_pattern)
            write_json(source_dir / "dotnet_endpoints.json", dotnet_payload)

        if not snapshot["exists"]:
            warnings.append(f"Source '{source_name}' path does not exist: {local_path}")

        source_outputs.append(
            {
                "name": source_name,
                "kind": source_kind or "unknown",
                "snapshot": snapshot,
                "dotnet": dotnet_payload,
            }
        )

    api_contract_updated = update_api_contract(source_outputs)
    write_code_facts_summary(source_outputs, warnings)
    return EvidenceCollectionResult(
        warnings=warnings,
        source_outputs=source_outputs,
        api_contract_updated=api_contract_updated,
    )


def load_sources_config(path: Path) -> list[dict[str, Any]]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Failed to parse {path.name}: {exc}") from exc

    if isinstance(payload, list):
        sources = payload
    elif isinstance(payload, dict):
        raw_sources = payload.get("sources", [])
        if not isinstance(raw_sources, list):
            raise ValueError(f"{path.name} must contain a top-level 'sources' list.")
        sources = raw_sources
    else:
        raise ValueError(f"{path.name} must be a mapping or a list.")

    normalized = [item for item in sources if isinstance(item, dict)]
    if not normalized:
        raise ValueError(f"{path.name} does not contain any usable source entries.")
    return normalized


def update_api_contract(source_outputs: list[dict[str, Any]]) -> bool:
    backend_source = None
    for item in source_outputs:
        if item["kind"] == "dotnet" and item["dotnet"] is not None and item["snapshot"].get("exists"):
            if item["name"] == "backend":
                backend_source = item
                break
            if backend_source is None:
                backend_source = item

    if backend_source is None:
        return False

    snapshot = backend_source["snapshot"]
    dotnet_payload = backend_source["dotnet"]
    api_contract_json = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_name": backend_source["name"],
        "repo_path": snapshot["path"],
        "git_branch": snapshot["git_branch"],
        "git_head": snapshot["git_head"],
        "tech_stack": snapshot["tech_stack"],
        "summary": dotnet_payload["summary"],
        "endpoints": dotnet_payload["endpoints"],
    }

    design_dir = REPO_ROOT / "domains" / "didaunao_release_audit" / "design"
    write_json(design_dir / "api_contract.json", api_contract_json)
    (design_dir / "api_contract.md").write_text(
        build_api_contract_markdown(snapshot, dotnet_payload),
        encoding="utf-8",
    )
    return True


def build_api_contract_markdown(snapshot: dict[str, Any], dotnet_payload: dict[str, Any]) -> str:
    summary = dotnet_payload["summary"]
    highlighted = [
        endpoint
        for endpoint in dotnet_payload["endpoints"]
        if any(flag in endpoint["route"].lower() for flag in ("/verify", "/approve", "/reject"))
    ]

    lines = [
        "# Didaunao Release Audit API and Metrics Notes",
        "",
        "This file is auto-generated from local source evidence.",
        "",
        "- Business truth must still come from the KB context pack generated from `requirements/didaunao_release_audit/`.",
        "- Use this file only for implementation facts such as endpoint surfaces, route names, controller exposure, and authorization hints.",
        "- If the KB context does not state a business fact, mark it as `UNKNOWN`.",
        "",
        "## Backend Snapshot",
        "",
        f"- Path: `{snapshot['path']}`",
        f"- Git branch: `{snapshot.get('git_branch') or 'UNKNOWN'}`",
        f"- Git head: `{snapshot.get('git_head') or 'UNKNOWN'}`",
        f"- Tech stack: `{', '.join(snapshot.get('tech_stack') or ['unknown'])}`",
        f"- Controller files: `{len(snapshot.get('controller_files') or [])}`",
        f"- Extracted endpoints: `{summary.get('endpoints', 0)}`",
        f"- Anonymous endpoints: `{summary.get('anonymous_endpoints', 0)}`",
        "",
        "## HTTP Method Counts",
        "",
    ]
    for method, count in sorted((summary.get("methods") or {}).items()):
        lines.append(f"- `{method}`: {count}")

    lines.extend(["", "## Notable Review Endpoints", ""])
    if highlighted:
        for endpoint in highlighted[:25]:
            lines.append(
                f"- `{endpoint['http_method']} {endpoint['route']}` "
                f"(controller=`{endpoint['controller']}`, auth=`{endpoint['auth']}`, binding=`{endpoint['binding']}`)"
            )
    else:
        lines.append("- No `/verify`, `/approve`, or `/reject` routes were detected in the scanned controller set.")

    lines.extend(["", "## Endpoint Sample", ""])
    for endpoint in dotnet_payload["endpoints"][:20]:
        lines.append(
            f"- `{endpoint['http_method']} {endpoint['route']}` "
            f"(action=`{endpoint['action']}`, auth=`{endpoint['auth']}`, binding=`{endpoint['binding']}`)"
        )

    return "\n".join(lines).strip() + "\n"


def write_code_facts_summary(source_outputs: list[dict[str, Any]], warnings: list[str]) -> None:
    out_dir = REPO_ROOT / "requirements" / "didaunao_release_audit" / "code_facts"
    out_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Auto-generated code facts summary",
        "",
        f"- Generated at: `{datetime.now(timezone.utc).isoformat()}`",
        "- Purpose: compact local source evidence for release-audit prompt preparation.",
        "",
    ]
    for item in source_outputs:
        snapshot = item["snapshot"]
        tech_stack = ", ".join(snapshot.get("tech_stack") or ["unknown"])
        branch = snapshot.get("git_branch") or "UNKNOWN"
        head = (snapshot.get("git_head") or "UNKNOWN")[:12]
        lines.append(
            f"- `{item['name']}`: exists=`{snapshot['exists']}`, tech_stack=`{tech_stack}`, branch=`{branch}`, head=`{head}`."
        )
        if item["dotnet"] is not None:
            summary = item["dotnet"]["summary"]
            lines.append(
                f"- `{item['name']}` API: controllers=`{summary['controllers']}`, endpoints=`{summary['endpoints']}`, "
                f"anonymous=`{summary['anonymous_endpoints']}`."
            )

    if warnings:
        lines.extend(["", "## Warnings", ""])
        for warning in warnings:
            lines.append(f"- {warning}")

    (out_dir / "00_evidence_summary.md").write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json_if_present(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


if __name__ == "__main__":
    raise SystemExit(main())
