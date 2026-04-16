"""Tests for requirement parsing and normalization."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from orchestrator.advanced_qa.requirement_models import RequirementSourceType
from orchestrator.advanced_qa.requirement_parser import RequirementParser


FIXTURE_DIR = Path(__file__).parent / "shared" / "fixtures"


def test_parse_markdown_structured_sections():
    """Parses markdown section-based requirements consistently."""

    parser = RequirementParser()
    markdown_payload = (FIXTURE_DIR / "rankmate_requirements.md").read_text(encoding="utf-8")

    requirements = parser.parse(
        markdown_payload,
        source_ref="tests/shared/fixtures/rankmate_requirements.md",
    )

    assert len(requirements) == 2
    assert requirements[0].requirement_id == "RM-MD-001"
    assert requirements[0].module == "Payment"
    assert requirements[0].source_type == RequirementSourceType.API_CONTRACT
    assert "Callback retries transient failure up to 3 times." in requirements[0].acceptance_criteria
    assert requirements[1].roles == ["merchant", "user"]


def test_parse_yaml_and_json_structured_inputs():
    """Parses yaml and json structures into normalized requirements."""

    parser = RequirementParser()
    yaml_payload = yaml.safe_load((FIXTURE_DIR / "rankmate_requirements.yaml").read_text(encoding="utf-8"))

    yaml_requirements = parser.parse(yaml_payload)
    assert len(yaml_requirements) == 10
    assert yaml_requirements[0].source_type == RequirementSourceType.PRD

    json_payload = json.dumps(
        {
            "requirements": [
                {
                    "id": "RM-JSON-001",
                    "title": "Verify email token",
                    "description": "Token validation is mandatory.",
                    "source_type": "acceptance_criteria",
                    "acceptance": ["Expired token is rejected"],
                    "roles": ["user"],
                    "priority": "high",
                }
            ]
        }
    )
    json_requirements = parser.parse(json_payload)

    assert len(json_requirements) == 1
    assert json_requirements[0].requirement_id == "RM-JSON-001"
    assert json_requirements[0].priority == "p1"
    assert json_requirements[0].source_type == RequirementSourceType.ACCEPTANCE


def test_normalize_requirement_fields_consistently():
    """Normalizes aliases and mixed field styles into canonical requirement fields."""

    parser = RequirementParser()
    raw_payload = {
        "requirements": [
            {
                "requirement_id": "RM-NORM-001",
                "name": "Duplicate checkout guard",
                "summary": "Prevent duplicate order creation under repeated submit.",
                "domain": "Order Creation",
                "component": "Checkout",
                "source": "srs",
                "source_path": "requirements/rankmate/srs.md",
                "criteria": "One request one order; Duplicate request reuses existing order",
                "rules": ["Idempotency key must be unique"],
                "actors": ["user"],
                "depends_on": ["Payment"],
                "priority": "critical",
                "risks": ["duplicate", "payment"],
                "flows": ["checkout_create_order"],
                "changed": "true",
            }
        ]
    }

    requirement = parser.parse(raw_payload)[0]

    assert requirement.requirement_id == "RM-NORM-001"
    assert requirement.title == "Duplicate checkout guard"
    assert requirement.description.startswith("Prevent duplicate")
    assert requirement.module == "Order Creation"
    assert requirement.submodule == "Checkout"
    assert requirement.source_type == RequirementSourceType.SRS
    assert requirement.source_ref == "requirements/rankmate/srs.md"
    assert requirement.acceptance_criteria == ["One request one order", "Duplicate request reuses existing order"]
    assert requirement.business_rules == ["Idempotency key must be unique"]
    assert requirement.roles == ["user"]
    assert requirement.dependencies == ["Payment"]
    assert requirement.priority == "p0"
    assert requirement.risk_hints == ["duplicate", "payment"]
    assert requirement.related_flows == ["checkout_create_order"]
    assert requirement.changed_area is True
