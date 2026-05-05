from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any

from orchestrator.advanced_qa.requirement_models import RiskLevel
from orchestrator.advanced_qa.requirement_rules import (
    build_risk_signals,
    dedupe_preserve_order,
    detect_modules,
    detect_roles,
    determine_risk_level,
    normalize_priority,
    tokenize_text,
)


@dataclass(frozen=True)
class NormalizedRequirementIngestion:
    requirement_id: str
    title: str
    feature: str
    actor: str
    preconditions: list[str]
    business_flow: list[str]
    acceptance_criteria: list[str]
    test_scenarios: list[str]
    priority: str
    risk_level: str
    unknowns: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RequirementIngestionParser:
    """Deterministically normalize raw requirement text into a stable JSON shape."""

    _LIST_SECTIONS = {
        "preconditions": "preconditions",
        "precondition": "preconditions",
        "business flow": "business_flow",
        "flow": "business_flow",
        "user flow": "business_flow",
        "acceptance criteria": "acceptance_criteria",
        "acceptance": "acceptance_criteria",
        "criteria": "acceptance_criteria",
    }

    _SCALAR_FIELDS = {
        "title": "title",
        "feature": "feature",
        "actor": "actor",
        "priority": "priority",
        "risk level": "risk_level",
        "risk": "risk_level",
    }

    def parse(
        self,
        raw_text: str,
        *,
        source_id: str | None = None,
        source_name: str | None = None,
    ) -> NormalizedRequirementIngestion:
        text = raw_text if isinstance(raw_text, str) else ""
        stripped = text.strip()

        title = self._extract_title(stripped)
        sections = self._extract_sections(stripped)
        story_actor, story_goal = self._extract_user_story(stripped)

        feature = self._clean_text(sections["feature"]) or self._infer_feature(stripped, source_name=source_name)
        actor = self._clean_text(sections["actor"]) or story_actor or self._infer_actor(stripped)
        preconditions = self._normalize_list(sections["preconditions"])
        business_flow = self._normalize_list(sections["business_flow"])
        acceptance_criteria = self._normalize_list(sections["acceptance_criteria"])

        gherkin_preconditions, gherkin_acceptance = self._extract_gherkin_lines(stripped)
        if not preconditions:
            preconditions = gherkin_preconditions
        else:
            preconditions = dedupe_preserve_order([*preconditions, *gherkin_preconditions])

        if not acceptance_criteria:
            acceptance_criteria = gherkin_acceptance
        else:
            acceptance_criteria = dedupe_preserve_order([*acceptance_criteria, *gherkin_acceptance])

        if not business_flow:
            business_flow = self._infer_business_flow(stripped, story_goal=story_goal, title=title)

        priority = normalize_priority(self._clean_text(sections["priority"]))
        risk_level = self._normalize_risk_level(
            self._clean_text(sections["risk_level"]),
            title=title,
            feature=feature,
            actor=actor,
            business_flow=business_flow,
            acceptance_criteria=acceptance_criteria,
            priority=priority,
        )
        requirement_id = self._build_requirement_id(
            stripped,
            source_id=source_id,
            source_name=source_name,
            title=title,
        )
        test_scenarios = self._build_test_scenarios(
            title=title,
            acceptance_criteria=acceptance_criteria,
            business_flow=business_flow,
        )
        unknowns = self._build_unknowns(
            raw_text=stripped,
            feature=feature,
            actor=actor,
            preconditions=preconditions,
            business_flow=business_flow,
            acceptance_criteria=acceptance_criteria,
        )

        return NormalizedRequirementIngestion(
            requirement_id=requirement_id,
            title=title,
            feature=feature,
            actor=actor,
            preconditions=preconditions,
            business_flow=business_flow,
            acceptance_criteria=acceptance_criteria,
            test_scenarios=test_scenarios,
            priority=priority,
            risk_level=risk_level,
            unknowns=unknowns,
        )

    def _extract_title(self, text: str) -> str:
        if not text:
            return "Untitled Requirement"

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            heading_match = re.match(r"^#{1,6}\s+(.+)$", stripped)
            if heading_match:
                return heading_match.group(1).strip()
            labeled = re.match(r"^title:\s*(.+)$", stripped, flags=re.IGNORECASE)
            if labeled:
                return labeled.group(1).strip()
            if not re.match(r"^[A-Za-z _-]+:\s*", stripped):
                return self._truncate_sentence(stripped)

        return "Untitled Requirement"

    def _extract_sections(self, text: str) -> dict[str, Any]:
        sections = {
            "title": "",
            "feature": "",
            "actor": "",
            "priority": "",
            "risk_level": "",
            "preconditions": [],
            "business_flow": [],
            "acceptance_criteria": [],
        }
        if not text:
            return sections

        current_list_field = ""
        for raw_line in text.splitlines():
            stripped = raw_line.strip()
            if not stripped:
                continue

            heading_match = re.match(r"^##+\s+(.+)$", stripped)
            if heading_match:
                normalized = self._normalize_section_name(heading_match.group(1))
                current_list_field = self._LIST_SECTIONS.get(normalized, "")
                continue

            label_match = re.match(r"^([A-Za-z][A-Za-z /_-]+):\s*(.*)$", stripped)
            if label_match:
                label = self._normalize_section_name(label_match.group(1))
                value = label_match.group(2).strip()
                if label in self._SCALAR_FIELDS:
                    sections[self._SCALAR_FIELDS[label]] = value
                    current_list_field = ""
                    continue
                list_field = self._LIST_SECTIONS.get(label)
                if list_field:
                    current_list_field = list_field
                    if value:
                        sections[list_field].extend(self._split_inline_list(value))
                    continue
                current_list_field = ""

            bullet_match = re.match(r"^(?:[-*]|\d+\.)\s+(.+)$", stripped)
            if bullet_match and current_list_field:
                sections[current_list_field].append(bullet_match.group(1).strip())
                continue

            if current_list_field:
                sections[current_list_field].append(stripped)

        return sections

    def _extract_user_story(self, text: str) -> tuple[str, str]:
        story_match = re.search(
            r"\bas an? (?P<actor>[^,.\n]+),\s*i want to (?P<goal>[^.\n]+)",
            text,
            flags=re.IGNORECASE,
        )
        if not story_match:
            return "", ""
        actor = self._clean_text(story_match.group("actor"))
        goal = self._clean_text(story_match.group("goal"))
        return actor, goal

    def _extract_gherkin_lines(self, text: str) -> tuple[list[str], list[str]]:
        preconditions: list[str] = []
        acceptance: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if re.match(r"^given\b", stripped, flags=re.IGNORECASE):
                preconditions.append(stripped)
            elif re.match(r"^(when|then|and)\b", stripped, flags=re.IGNORECASE):
                acceptance.append(stripped)
        return dedupe_preserve_order(preconditions), dedupe_preserve_order(acceptance)

    def _infer_feature(self, text: str, *, source_name: str | None) -> str:
        modules = detect_modules(text.lower()) if text else []
        if modules:
            return modules[0]
        return self._clean_text(source_name)

    def _infer_actor(self, text: str) -> str:
        roles = detect_roles(text.lower()) if text else []
        if not roles:
            return ""
        if roles[0] == "system" and not re.search(r"\bas a system\b|\bsystem service\b|\bscheduler\b|\bworker\b", text, flags=re.IGNORECASE):
            return ""
        return roles[0]

    def _infer_business_flow(self, text: str, *, story_goal: str, title: str) -> list[str]:
        if story_goal:
            return [f"User attempts to {story_goal}."]

        sentences = self._split_sentences(text)
        filtered = []
        for sentence in sentences:
            lowered = sentence.lower()
            if lowered.startswith("as a ") or lowered.startswith("as an "):
                continue
            if re.match(r"^[A-Za-z][A-Za-z /_-]+:\s*", sentence):
                continue
            filtered.append(sentence)

        if filtered:
            return filtered[:3]
        if title and title != "Untitled Requirement":
            return [f"Execute the business flow for {title}."]
        return []

    def _normalize_risk_level(
        self,
        explicit: str,
        *,
        title: str,
        feature: str,
        actor: str,
        business_flow: list[str],
        acceptance_criteria: list[str],
        priority: str,
    ) -> str:
        explicit_text = explicit.lower()
        aliases = {
            "low": RiskLevel.LOW.value,
            "medium": RiskLevel.MEDIUM.value,
            "high": RiskLevel.HIGH.value,
            "critical": RiskLevel.CRITICAL.value,
        }
        if explicit_text in aliases:
            return aliases[explicit_text]

        text = tokenize_text(
            [
                title,
                feature,
                actor,
                " ".join(business_flow),
                " ".join(acceptance_criteria),
            ]
        )
        score, _ = build_risk_signals(
            priority=priority,
            changed_area=False,
            role_count=1 if actor else 0,
            text=text,
        )
        return determine_risk_level(score).value

    def _build_requirement_id(
        self,
        text: str,
        *,
        source_id: str | None,
        source_name: str | None,
        title: str,
    ) -> str:
        if source_id and self._clean_text(source_id):
            return self._clean_text(source_id).replace(" ", "_")

        basis = "|".join(
            part for part in [self._clean_text(source_name), title, text] if part
        ) or "empty_requirement"
        digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:10].upper()
        return f"REQ-{digest}"

    def _build_test_scenarios(
        self,
        *,
        title: str,
        acceptance_criteria: list[str],
        business_flow: list[str],
    ) -> list[str]:
        scenarios: list[str] = []
        if title and title != "Untitled Requirement":
            scenarios.append(f"Positive path validates {title}.")

        for criterion in acceptance_criteria:
            lowered = criterion.lower()
            if any(token in lowered for token in ["invalid", "error", "reject", "fail", "denied", "unauthorized"]):
                scenarios.append(f"Negative path covers: {criterion}")
            else:
                scenarios.append(f"Acceptance validation: {criterion}")

        if not acceptance_criteria and business_flow:
            scenarios.append(f"Business flow coverage: {business_flow[0]}")

        return dedupe_preserve_order(scenarios)

    def _build_unknowns(
        self,
        *,
        raw_text: str,
        feature: str,
        actor: str,
        preconditions: list[str],
        business_flow: list[str],
        acceptance_criteria: list[str],
    ) -> list[str]:
        unknowns: list[str] = []
        if not raw_text:
            unknowns.append("empty_input")
        if not feature:
            unknowns.append("feature")
        if not actor:
            unknowns.append("actor")
        if not preconditions:
            unknowns.append("preconditions")
        if not business_flow:
            unknowns.append("business_flow")
        if not acceptance_criteria:
            unknowns.append("acceptance_criteria")
        return unknowns

    def _normalize_list(self, items: list[str]) -> list[str]:
        return dedupe_preserve_order(self._clean_text(item) for item in items)

    def _split_inline_list(self, value: str) -> list[str]:
        if ";" in value:
            return [item.strip() for item in value.split(";")]
        if "," in value:
            return [item.strip() for item in value.split(",")]
        return [value.strip()]

    def _split_sentences(self, text: str) -> list[str]:
        parts = re.split(r"(?<=[.!?])\s+|\n+", text)
        return [self._clean_text(part) for part in parts if self._clean_text(part)]

    def _truncate_sentence(self, value: str, *, max_len: int = 90) -> str:
        cleaned = self._clean_text(value)
        if len(cleaned) <= max_len:
            return cleaned
        return cleaned[: max_len - 3].rstrip() + "..."

    def _normalize_section_name(self, value: str) -> str:
        return re.sub(r"\s+", " ", self._clean_text(value).lower())

    def _clean_text(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()


def ingest_requirement(
    raw_text: str,
    *,
    source_id: str | None = None,
    source_name: str | None = None,
) -> dict[str, Any]:
    """Parse raw requirement text into a JSON-serializable normalized requirement payload."""
    return RequirementIngestionParser().parse(
        raw_text,
        source_id=source_id,
        source_name=source_name,
    ).to_dict()


def requirement_to_json(
    raw_text: str,
    *,
    source_id: str | None = None,
    source_name: str | None = None,
) -> str:
    """Serialize normalized requirement payload as JSON."""
    return json.dumps(
        ingest_requirement(raw_text, source_id=source_id, source_name=source_name),
        ensure_ascii=False,
        indent=2,
    )
