"""JSON and Markdown exporters for Manual QA Phase 1."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from orchestrator.manual_qa.models import ExportBundle


class ManualQAExporter:
    """Export Manual QA bundle content as JSON or Markdown."""

    def export_json_string(self, bundle: ExportBundle) -> str:
        return json.dumps(bundle.to_dict(), indent=2, ensure_ascii=False, sort_keys=True)

    def export_json_file(self, bundle: ExportBundle, path: Path | str) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.export_json_string(bundle), encoding="utf-8")
        return output_path

    def export_markdown_string(
        self,
        bundle: ExportBundle,
        *,
        title: Optional[str] = None,
    ) -> str:
        heading = title or f"Manual QA Export - {bundle.project.name}"
        lines = [
            f"# {heading}",
            "",
            "## Project",
            f"- Project ID: {bundle.project.project_id}",
            f"- Name: {bundle.project.name}",
            f"- Product Type: {bundle.project.product_type}",
            "",
            "## Requirements",
        ]

        for requirement in bundle.requirements:
            lines.extend(
                [
                    f"- {requirement.requirement_id}: {requirement.title}",
                    f"  Module: {requirement.module}",
                    f"  Priority: {requirement.priority}",
                ]
            )

        lines.extend(["", "## Checklist"])
        for item in bundle.checklist_items:
            lines.extend(
                [
                    f"- {item.checklist_id} [{item.requirement_id}] {item.title}",
                    f"  Priority: {item.priority}",
                    f"  Description: {item.description}",
                ]
            )

        lines.extend(["", "## Manual Test Cases"])
        for case in bundle.test_cases:
            lines.extend(
                [
                    f"- {case.test_case_id} [{', '.join(case.requirement_ids)}] {case.title}",
                    f"  Type: {case.test_type}",
                    f"  Status: {case.status}",
                    f"  Expected: {case.expected_result}",
                ]
            )

        lines.append("")
        return "\n".join(lines)

    def export_markdown_file(
        self,
        bundle: ExportBundle,
        path: Path | str,
        *,
        title: Optional[str] = None,
    ) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(self.export_markdown_string(bundle, title=title), encoding="utf-8")
        return output_path


def export_bundle_to_json_string(bundle: ExportBundle) -> str:
    return ManualQAExporter().export_json_string(bundle)


def export_bundle_to_json_file(bundle: ExportBundle, path: Path | str) -> Path:
    return ManualQAExporter().export_json_file(bundle, path)


def export_bundle_to_markdown_string(bundle: ExportBundle, *, title: Optional[str] = None) -> str:
    return ManualQAExporter().export_markdown_string(bundle, title=title)


def export_bundle_to_markdown_file(
    bundle: ExportBundle,
    path: Path | str,
    *,
    title: Optional[str] = None,
) -> Path:
    return ManualQAExporter().export_markdown_file(bundle, path, title=title)
