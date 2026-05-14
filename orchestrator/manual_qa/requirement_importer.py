"""Requirement import helpers for Manual QA Phase 1."""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional


class RequirementImporter:
    """Import raw requirements without external AI dependencies."""

    _KEY_ALIASES = {
        "id": "requirement_id",
        "requirement id": "requirement_id",
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
        "role": "roles",
        "roles": "roles",
        "acceptance criteria": "acceptance_criteria",
        "acceptance_criteria": "acceptance_criteria",
        "criteria": "acceptance_criteria",
        "expected result": "acceptance_criteria",
        "expected_result": "acceptance_criteria",
        "source ref": "source_ref",
        "source_ref": "source_ref",
    }

    _LIST_FIELDS = {"roles", "acceptance_criteria"}

    def import_requirements(
        self,
        payload: Any,
        *,
        source_ref: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if isinstance(payload, dict):
            items = payload.get("requirements") if isinstance(payload.get("requirements"), list) else [payload]
            return [self._normalize_raw_record(item, source_ref=source_ref) for item in items]

        if isinstance(payload, list):
            return [self._normalize_raw_record(item, source_ref=source_ref) for item in payload]

        if isinstance(payload, str):
            return self._import_from_text(payload, source_ref=source_ref)

        raise TypeError(f"Unsupported requirement payload type: {type(payload)!r}")

    def _normalize_raw_record(
        self,
        item: Any,
        *,
        source_ref: Optional[str],
    ) -> Dict[str, Any]:
        if isinstance(item, dict):
            record = dict(item)
            if source_ref and "source_ref" not in record:
                record["source_ref"] = source_ref
            return record

        if isinstance(item, str):
            records = self._import_from_text(item, source_ref=source_ref)
            return records[0] if records else {}

        raise TypeError(f"Unsupported requirement item type: {type(item)!r}")

    def _import_from_text(
        self,
        text: str,
        *,
        source_ref: Optional[str],
    ) -> List[Dict[str, Any]]:
        stripped = text.strip()
        if not stripped:
            return []

        sections = self._split_text_sections(stripped)
        records: List[Dict[str, Any]] = []
        for section in sections:
            record = self._parse_section(section, source_ref=source_ref)
            if record:
                records.append(record)
        return records

    def _split_text_sections(self, text: str) -> List[str]:
        heading_sections = self._split_by_headings(text)
        if len(heading_sections) > 1:
            return heading_sections

        bullet_sections = self._split_bullets(text)
        if len(bullet_sections) > 1:
            return bullet_sections

        paragraph_sections = [block.strip() for block in re.split(r"\n\s*\n+", text) if block.strip()]
        return paragraph_sections or [text]

    def _split_by_headings(self, text: str) -> List[str]:
        sections: List[str] = []
        current: List[str] = []

        for line in text.splitlines():
            if re.match(r"^#{1,6}\s+.+$", line.strip()):
                if current:
                    sections.append("\n".join(current).strip())
                current = [line]
                continue
            current.append(line)

        if current:
            sections.append("\n".join(current).strip())
        return [section for section in sections if section]

    def _split_bullets(self, text: str) -> List[str]:
        lines = [line.rstrip() for line in text.splitlines() if line.strip()]
        if not lines:
            return []
        if not all(re.match(r"^\s*[-*]\s+.+$", line) for line in lines):
            return []
        return [re.sub(r"^\s*[-*]\s+", "", line).strip() for line in lines]

    def _parse_section(
        self,
        section: str,
        *,
        source_ref: Optional[str],
    ) -> Dict[str, Any]:
        lines = [line.rstrip() for line in section.splitlines()]
        if not lines:
            return {}

        record: Dict[str, Any] = {}
        description_lines: List[str] = []
        current_list_field: Optional[str] = None

        first_line = lines[0].strip()
        body_lines = lines

        heading_match = re.match(r"^#{1,6}\s+(.+)$", first_line)
        if heading_match:
            self._apply_heading(record, heading_match.group(1).strip())
            body_lines = lines[1:]

        for raw_line in body_lines:
            line = raw_line.strip()
            if not line:
                continue

            bullet_match = re.match(r"^[-*]\s+(.+)$", line)
            if bullet_match and current_list_field:
                record.setdefault(current_list_field, []).append(bullet_match.group(1).strip())
                continue

            key_match = re.match(r"^([A-Za-z_ /-]+):\s*(.*)$", line)
            if key_match:
                normalized_key = self._KEY_ALIASES.get(key_match.group(1).strip().lower())
                raw_value = key_match.group(2).strip()
                if normalized_key in self._LIST_FIELDS:
                    current_list_field = normalized_key
                    if raw_value:
                        record.setdefault(normalized_key, []).extend(self._split_list_value(raw_value))
                    else:
                        record.setdefault(normalized_key, [])
                    continue
                if normalized_key:
                    current_list_field = None
                    record[normalized_key] = raw_value
                    continue

            current_list_field = None
            description_lines.append(re.sub(r"^[-*]\s+", "", line).strip())

        if "title" not in record:
            record["title"] = self._derive_title(first_line, description_lines)

        if "description" not in record:
            if description_lines:
                record["description"] = " ".join(description_lines).strip()
            elif "title" in record:
                record["description"] = record["title"]

        if source_ref and "source_ref" not in record:
            record["source_ref"] = source_ref

        for field in self._LIST_FIELDS:
            if field in record:
                record[field] = self._dedupe([item for item in record[field] if item])

        return record

    def _apply_heading(self, record: Dict[str, Any], heading_text: str) -> None:
        bracket_match = re.match(r"^\[([^\]]+)\]\s*(.+)$", heading_text)
        if bracket_match:
            record["requirement_id"] = bracket_match.group(1).strip()
            record["title"] = bracket_match.group(2).strip()
            return

        label_match = re.match(r"^([A-Za-z]+[-_ ]?\d+)\s*[:\-]\s*(.+)$", heading_text)
        if label_match:
            record["requirement_id"] = label_match.group(1).strip()
            record["title"] = label_match.group(2).strip()
            return

        record["title"] = heading_text

    def _derive_title(self, first_line: str, description_lines: Iterable[str]) -> str:
        cleaned_first = re.sub(r"^[-*]\s+", "", first_line).strip()
        if cleaned_first and not re.match(r"^([A-Za-z_ /-]+):\s*", cleaned_first):
            return cleaned_first[:80]

        description = " ".join(line.strip() for line in description_lines if line.strip()).strip()
        if not description:
            return "Requirement"

        sentence = re.split(r"(?<=[.!?])\s+", description, maxsplit=1)[0].strip()
        return sentence[:80] or "Requirement"

    def _split_list_value(self, value: str) -> List[str]:
        if ";" in value:
            return [item.strip() for item in value.split(";") if item.strip()]
        if "," in value:
            return [item.strip() for item in value.split(",") if item.strip()]
        return [value.strip()] if value.strip() else []

    def _dedupe(self, items: Iterable[str]) -> List[str]:
        seen = set()
        ordered: List[str] = []
        for item in items:
            if item not in seen:
                seen.add(item)
                ordered.append(item)
        return ordered
