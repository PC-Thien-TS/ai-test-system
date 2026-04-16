"""Parsing and normalization for requirement-aware generation inputs."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional, Sequence

import yaml

from orchestrator.advanced_qa.requirement_models import Requirement, RequirementSourceType
from orchestrator.advanced_qa.requirement_rules import dedupe_preserve_order, normalize_priority


class RequirementParser:
    """Parse raw requirement payloads into normalized Requirement objects."""

    _LIST_FIELDS = {
        "acceptance_criteria",
        "business_rules",
        "roles",
        "dependencies",
        "risk_hints",
        "related_flows",
    }

    _FIELD_ALIASES = {
        "id": "requirement_id",
        "requirement_id": "requirement_id",
        "title": "title",
        "name": "title",
        "description": "description",
        "summary": "description",
        "module": "module",
        "domain": "module",
        "submodule": "submodule",
        "component": "submodule",
        "source": "source_type",
        "source_type": "source_type",
        "source_ref": "source_ref",
        "source_path": "source_ref",
        "acceptance": "acceptance_criteria",
        "acceptance_criteria": "acceptance_criteria",
        "criteria": "acceptance_criteria",
        "business_rules": "business_rules",
        "rules": "business_rules",
        "roles": "roles",
        "actors": "roles",
        "dependencies": "dependencies",
        "depends_on": "dependencies",
        "priority": "priority",
        "risk_hints": "risk_hints",
        "risks": "risk_hints",
        "related_flows": "related_flows",
        "flows": "related_flows",
        "changed_area": "changed_area",
        "changed": "changed_area",
    }

    def parse(
        self,
        raw_input: Any,
        source_type: Optional[str] = None,
        source_ref: Optional[str] = None,
    ) -> List[Requirement]:
        """Parse raw requirement input into normalized requirements."""

        parsed_payload = self._decode_raw_input(raw_input)
        items = self._coerce_to_items(parsed_payload)

        requirements: List[Requirement] = []
        for index, item in enumerate(items, start=1):
            if isinstance(item, Requirement):
                requirements.append(item)
                continue

            if isinstance(item, dict):
                requirements.append(
                    self._from_dict(item, index=index, source_type=source_type, source_ref=source_ref)
                )
                continue

            if isinstance(item, str):
                requirements.extend(
                    self._parse_markdown_sections(
                        item,
                        source_type=source_type,
                        source_ref=source_ref,
                        start_index=index,
                    )
                )
                continue

            raise TypeError(f"Unsupported requirement item type: {type(item)!r}")

        return requirements

    def _decode_raw_input(self, raw_input: Any) -> Any:
        """Decode string payloads as JSON/YAML/markdown, preserving non-strings."""

        if not isinstance(raw_input, str):
            return raw_input

        text = raw_input.strip()
        if not text:
            return []

        # Parse markdown heading-based payloads before YAML; YAML treats "##" as comments.
        if re.search(r"^##\s+.+$", text, flags=re.MULTILINE):
            return text

        if text.startswith("{") or text.startswith("["):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass

        try:
            yaml_payload = yaml.safe_load(text)
            if isinstance(yaml_payload, (dict, list)):
                return yaml_payload
        except yaml.YAMLError:
            pass

        return text

    def _coerce_to_items(self, payload: Any) -> List[Any]:
        """Normalize decoded payload into an iterable list of requirement entries."""

        if payload is None:
            return []

        if isinstance(payload, list):
            return payload

        if isinstance(payload, tuple):
            return list(payload)

        if isinstance(payload, dict):
            requirements = payload.get("requirements")
            if isinstance(requirements, list):
                return requirements
            return [payload]

        if isinstance(payload, str):
            return self._parse_markdown_sections(payload)

        raise TypeError(f"Unsupported requirement payload type: {type(payload)!r}")

    def _from_dict(
        self,
        item: Dict[str, Any],
        index: int,
        source_type: Optional[str],
        source_ref: Optional[str],
    ) -> Requirement:
        """Normalize dictionary payload into Requirement."""

        normalized: Dict[str, Any] = {}
        metadata: Dict[str, Any] = {}

        for key, value in item.items():
            normalized_key = self._FIELD_ALIASES.get(str(key).strip().lower())
            if normalized_key:
                normalized[normalized_key] = value
            else:
                metadata[key] = value

        requirement_id = self._coerce_requirement_id(
            normalized.get("requirement_id"),
            index=index,
        )
        title = str(normalized.get("title") or f"Requirement {index}").strip()
        description = str(normalized.get("description") or "").strip()

        parsed_source_type = self._coerce_source_type(
            source_type or normalized.get("source_type")
        )

        requirement = Requirement(
            requirement_id=requirement_id,
            title=title,
            description=description,
            module=self._clean_optional_text(normalized.get("module")),
            submodule=self._clean_optional_text(normalized.get("submodule")),
            source_type=parsed_source_type,
            source_ref=self._clean_optional_text(source_ref or normalized.get("source_ref")),
            acceptance_criteria=self._coerce_list(normalized.get("acceptance_criteria")),
            business_rules=self._coerce_list(normalized.get("business_rules")),
            roles=self._coerce_list(normalized.get("roles")),
            dependencies=self._coerce_list(normalized.get("dependencies")),
            priority=normalize_priority(self._clean_optional_text(normalized.get("priority"))),
            risk_hints=self._coerce_list(normalized.get("risk_hints")),
            related_flows=self._coerce_list(normalized.get("related_flows")),
            changed_area=self._coerce_bool(normalized.get("changed_area", False)),
            metadata=metadata,
        )
        return requirement

    def _parse_markdown_sections(
        self,
        markdown_text: str,
        source_type: Optional[str] = None,
        source_ref: Optional[str] = None,
        start_index: int = 1,
    ) -> List[Requirement]:
        """Parse markdown/simple-section text into Requirement records."""

        lines = markdown_text.splitlines()
        sections: List[tuple[str, List[str]]] = []

        current_heading = "Requirement"
        current_lines: List[str] = []

        for line in lines:
            heading_match = re.match(r"^##\s+(.+)$", line.strip())
            if heading_match:
                if current_lines:
                    sections.append((current_heading, current_lines))
                current_heading = heading_match.group(1).strip()
                current_lines = []
            else:
                current_lines.append(line)

        if current_lines:
            sections.append((current_heading, current_lines))

        requirements: List[Requirement] = []
        for offset, (heading, section_lines) in enumerate(sections):
            idx = start_index + offset
            requirement_id, title = self._parse_heading(heading, idx)
            scalar_values: Dict[str, Any] = {}
            list_values: Dict[str, List[str]] = {field: [] for field in self._LIST_FIELDS}
            description_lines: List[str] = []

            current_list_field: Optional[str] = None

            for raw_line in section_lines:
                line = raw_line.strip()
                if not line:
                    continue

                bullet_match = re.match(r"^-\s+(.+)$", line)
                if bullet_match and current_list_field:
                    list_values[current_list_field].append(bullet_match.group(1).strip())
                    continue

                key_match = re.match(r"^([A-Za-z_ /-]+):\s*(.*)$", line)
                if key_match:
                    raw_key = key_match.group(1).strip().lower()
                    mapped_key = self._FIELD_ALIASES.get(raw_key)
                    raw_value = key_match.group(2).strip()

                    if mapped_key in self._LIST_FIELDS:
                        current_list_field = mapped_key
                        if raw_value:
                            list_values[mapped_key].extend(self._split_list_like_text(raw_value))
                    elif mapped_key:
                        current_list_field = None
                        scalar_values[mapped_key] = raw_value
                    else:
                        current_list_field = None
                        description_lines.append(line)
                    continue

                if line.startswith("- "):
                    description_lines.append(line[2:].strip())
                else:
                    description_lines.append(line)

            if "description" in scalar_values:
                description = str(scalar_values["description"]).strip()
            else:
                description = " ".join(description_lines).strip()

            requirement = Requirement(
                requirement_id=requirement_id,
                title=title,
                description=description,
                module=self._clean_optional_text(scalar_values.get("module")),
                submodule=self._clean_optional_text(scalar_values.get("submodule")),
                source_type=self._coerce_source_type(source_type or scalar_values.get("source_type")),
                source_ref=self._clean_optional_text(source_ref or scalar_values.get("source_ref")),
                acceptance_criteria=dedupe_preserve_order(list_values["acceptance_criteria"]),
                business_rules=dedupe_preserve_order(list_values["business_rules"]),
                roles=dedupe_preserve_order(list_values["roles"]),
                dependencies=dedupe_preserve_order(list_values["dependencies"]),
                priority=normalize_priority(self._clean_optional_text(scalar_values.get("priority"))),
                risk_hints=dedupe_preserve_order(list_values["risk_hints"]),
                related_flows=dedupe_preserve_order(list_values["related_flows"]),
                changed_area=self._coerce_bool(scalar_values.get("changed_area", False)),
                metadata={},
            )
            requirements.append(requirement)

        return requirements

    def _parse_heading(self, heading: str, index: int) -> tuple[str, str]:
        """Extract requirement_id/title from markdown heading content."""

        cleaned = heading.strip()

        bracket_match = re.match(r"^\[([^\]]+)\]\s*(.+)$", cleaned)
        if bracket_match:
            return bracket_match.group(1).strip(), bracket_match.group(2).strip()

        colon_match = re.match(r"^([A-Za-z0-9][A-Za-z0-9_-]*\d)\s*[:\-]\s*(.+)$", cleaned)
        if colon_match:
            return colon_match.group(1).strip(), colon_match.group(2).strip()

        requirement_id = f"RQ-{index:03d}"
        title = cleaned if cleaned and cleaned.lower() != "requirement" else f"Requirement {index}"
        return requirement_id, title

    def _coerce_requirement_id(self, raw_value: Any, index: int) -> str:
        """Normalize requirement IDs with deterministic fallback."""

        if raw_value is None:
            return f"RQ-{index:03d}"
        text = str(raw_value).strip()
        return text or f"RQ-{index:03d}"

    def _coerce_source_type(self, raw_value: Any) -> RequirementSourceType:
        """Normalize source type labels into RequirementSourceType."""

        if raw_value is None:
            return RequirementSourceType.UNKNOWN

        text = str(raw_value).strip().lower()
        for source_type in RequirementSourceType:
            if source_type.value == text:
                return source_type

        aliases = {
            "acceptance": RequirementSourceType.ACCEPTANCE,
            "api": RequirementSourceType.API_CONTRACT,
            "business_rule": RequirementSourceType.BUSINESS_RULE,
            "business_rules": RequirementSourceType.BUSINESS_RULE,
            "feature": RequirementSourceType.FEATURE_INVENTORY,
            "workflow_doc": RequirementSourceType.WORKFLOW,
        }
        return aliases.get(text, RequirementSourceType.UNKNOWN)

    def _coerce_list(self, value: Any) -> List[str]:
        """Normalize list-like values to list[str]."""

        if value is None:
            return []

        if isinstance(value, str):
            return self._split_list_like_text(value)

        if isinstance(value, (list, tuple, set)):
            return dedupe_preserve_order(str(item).strip() for item in value)

        return [str(value).strip()]

    def _split_list_like_text(self, value: str) -> List[str]:
        """Split simple list-like text into list[str]."""

        text = value.strip()
        if not text:
            return []

        if "\n" in text:
            items = [line.strip(" -\t") for line in text.splitlines()]
            return dedupe_preserve_order(items)

        if ";" in text:
            items = [item.strip() for item in text.split(";")]
            return dedupe_preserve_order(items)

        if "," in text:
            items = [item.strip() for item in text.split(",")]
            return dedupe_preserve_order(items)

        return [text]

    def _clean_optional_text(self, value: Any) -> Optional[str]:
        """Return cleaned string or None for empty values."""

        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _coerce_bool(self, value: Any) -> bool:
        """Normalize booleans from various representations."""

        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if value is None:
            return False

        text = str(value).strip().lower()
        return text in {"1", "true", "yes", "y", "changed"}
