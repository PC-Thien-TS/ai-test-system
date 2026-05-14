"""Requirement normalization for Manual QA Phase 1."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping

from orchestrator.manual_qa.models import NormalizedRequirement


class RequirementNormalizer:
    """Normalize raw requirement dictionaries into Manual QA requirements."""

    _ALIASES = {
        "id": "requirement_id",
        "requirement_id": "requirement_id",
        "req_id": "requirement_id",
        "title": "title",
        "name": "title",
        "description": "description",
        "requirement": "description",
        "text": "description",
        "module": "module",
        "feature": "module",
        "priority": "priority",
        "roles": "roles",
        "role": "roles",
        "acceptance_criteria": "acceptance_criteria",
        "criteria": "acceptance_criteria",
        "expected_result": "acceptance_criteria",
        "source_ref": "source_ref",
        "metadata": "metadata",
    }

    def normalize_requirements(self, records: Iterable[Mapping[str, Any]]) -> List[NormalizedRequirement]:
        normalized: List[NormalizedRequirement] = []
        generated_index = 1

        for record in records:
            item = self._normalize_record(record)
            requirement_id = self._as_text(item.get("requirement_id"))
            if not requirement_id:
                requirement_id = f"REQ-{generated_index:03d}"
                generated_index += 1

            title = self._as_text(item.get("title")) or requirement_id
            description = self._as_text(item.get("description")) or title
            module = self._as_text(item.get("module")) or "General"
            priority = self._normalize_priority(self._as_text(item.get("priority")))
            roles = self._as_list(item.get("roles"))
            acceptance_criteria = self._as_list(item.get("acceptance_criteria"))
            source_ref = self._as_text(item.get("source_ref"))
            metadata = item.get("metadata")
            metadata_dict = dict(metadata) if isinstance(metadata, dict) else {}

            normalized.append(
                NormalizedRequirement(
                    requirement_id=requirement_id,
                    title=title,
                    description=description,
                    module=module,
                    priority=priority,
                    roles=roles,
                    acceptance_criteria=acceptance_criteria,
                    source_ref=source_ref,
                    metadata=metadata_dict,
                )
            )

        return normalized

    def _normalize_record(self, record: Mapping[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        for key, value in record.items():
            alias = self._ALIASES.get(str(key).strip().lower())
            if alias:
                normalized[alias] = value
        return normalized

    def _normalize_priority(self, value: str) -> str:
        if not value:
            return "Medium"

        cleaned = value.strip().lower()
        aliases = {
            "p0": "Critical",
            "p1": "High",
            "p2": "Medium",
            "p3": "Low",
            "critical": "Critical",
            "high": "High",
            "medium": "Medium",
            "low": "Low",
        }
        return aliases.get(cleaned, value.strip().title())

    def _as_text(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _as_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, str):
            if "\n" in value:
                items = [line.strip(" -\t") for line in value.splitlines()]
            elif ";" in value:
                items = [item.strip() for item in value.split(";")]
            elif "," in value:
                items = [item.strip() for item in value.split(",")]
            else:
                items = [value.strip()]
            return [item for item in self._dedupe(items) if item]
        if isinstance(value, (list, tuple, set)):
            return [item for item in self._dedupe(self._as_text(item) for item in value) if item]
        text = self._as_text(value)
        return [text] if text else []

    def _dedupe(self, items: Iterable[str]) -> List[str]:
        seen = set()
        ordered: List[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered
