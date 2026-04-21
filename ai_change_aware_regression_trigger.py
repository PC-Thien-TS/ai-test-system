"""Adapter-aware change-to-flow regression trigger."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from orchestrator.adapters import get_active_adapter
from orchestrator.adapters.evidence_context import get_adapter_evidence_context


REPO_ROOT = Path(__file__).resolve().parent


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="AI Change-aware Regression Trigger")
    parser.add_argument(
        "--files",
        default="",
        help="Comma-separated changed files.",
    )
    return parser.parse_args()


def _render_report(payload: dict) -> str:
    lines = [
        "# CHANGE_AWARE_TRIGGER_REPORT",
        "",
        f"- Adapter: `{payload['adapter']['adapter_id']}` ({payload['adapter']['product_name']})",
        f"- Generated at: `{payload['generated_at_utc']}`",
        "",
        "## Changed Files",
        "",
    ]
    changed_files = payload.get("changed_files", [])
    if changed_files:
        for item in changed_files:
            lines.append(f"- `{item}`")
    else:
        lines.append("- none")

    lines.extend(["", "## Selected Flows", ""])
    selected_flows = payload.get("selected_flows", [])
    if selected_flows:
        for row in selected_flows:
            lines.append(f"- `{row['flow_id']}` ({row['title']})")
            lines.append(f"  - Matched files: {', '.join(row['matched_files'])}")
    else:
        lines.append("- none")

    lines.extend(["", "## Runnable Commands", ""])
    commands = payload.get("powershell_commands", [])
    if commands:
        for cmd in commands:
            lines.append(f"- `{cmd}`")
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    args = _parse_args()
    adapter = get_active_adapter()
    ctx = get_adapter_evidence_context(adapter.get_adapter_id())
    flow_registry = adapter.get_flow_registry()
    files = [item.strip() for item in args.files.split(",") if item.strip()]
    mapped = adapter.map_changed_files_to_flows(files)

    selected_flows = []
    commands = []
    for flow_id in adapter.get_flow_order():
        matched_files = mapped.get(flow_id, [])
        if not matched_files:
            continue
        flow = flow_registry.get(flow_id)
        if flow is None:
            continue
        selected_flows.append(
            {
                "flow_id": flow.flow_id,
                "title": flow.title,
                "matched_files": matched_files,
                "suites": list(flow.suites),
            }
        )
        for suite in flow.suites:
            commands.append(f"python -m pytest -q -rs {suite}")

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "adapter": {
            "adapter_id": adapter.get_adapter_id(),
            "product_name": adapter.get_product_name(),
        },
        "changed_files": files,
        "selected_flows": selected_flows,
        "powershell_commands": list(dict.fromkeys(commands)),
    }

    output_json = ctx.write_json("change_aware_regression_plan", payload)
    output_md = ctx.write_report("CHANGE_AWARE_TRIGGER_REPORT.md", _render_report(payload))

    print(
        f"[change-aware-trigger] adapter={adapter.get_adapter_id()} files={len(files)} "
        f"selected_flows={len(selected_flows)}"
    )
    if selected_flows:
        print("[change-aware-trigger] flows:")
        for row in selected_flows:
            print(f"  - {row['flow_id']}")
    else:
        print("[change-aware-trigger] no mapped flows.")
    print(f"[change-aware-trigger] json={output_json}")
    print(f"[change-aware-trigger] report={output_md}")


if __name__ == "__main__":
    main()
