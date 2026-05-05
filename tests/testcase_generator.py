from __future__ import annotations

import json

from orchestrator.requirement_ingestion import ingest_requirement
from orchestrator.testcase_generator import generate_test_cases


def test_generating_test_cases_from_login_requirement():
    requirement = ingest_requirement(
        """
# Login Requirement
Feature: Authentication
Actor: User
Preconditions:
- User account exists
- User is on the login screen
Business Flow:
1. Enter username and password
2. Submit login request
Acceptance Criteria:
- Valid credentials redirect the user to the dashboard.
Priority: High
""",
        source_id="LOGIN-REQ-001",
    )

    cases = generate_test_cases(requirement)

    assert cases
    happy_path = cases[0]
    assert happy_path["test_case_id"] == "TC-LOGIN-REQ-001-001"
    assert happy_path["requirement_id"] == "LOGIN-REQ-001"
    assert happy_path["test_type"] == "happy_path"
    assert happy_path["automation_candidate"] is True
    assert happy_path["steps"] == [
        "Enter username and password",
        "Submit login request",
    ]
    assert happy_path["priority"] == "p1"


def test_acceptance_criteria_mapping_generates_acceptance_cases():
    requirement = ingest_requirement(
        """
# Login Requirement
Business Flow:
- Enter username and password
- Submit login request
Acceptance Criteria:
- Valid credentials redirect the user to the dashboard.
- Invalid credentials show an error message.
""",
        source_id="LOGIN-REQ-002",
    )

    cases = generate_test_cases(requirement)
    acceptance_cases = [case for case in cases if case["source"] == "acceptance_criteria"]

    assert len(acceptance_cases) == 2
    assert acceptance_cases[0]["expected_result"] == "Valid credentials redirect the user to the dashboard."
    assert acceptance_cases[1]["expected_result"] == "Invalid credentials show an error message."
    assert all(case["test_type"] == "acceptance" for case in acceptance_cases)


def test_scenario_mapping_generates_scenario_cases():
    requirement = {
        "requirement_id": "REQ-SCN-001",
        "title": "Checkout login gate",
        "feature": "Auth & Account",
        "actor": "user",
        "preconditions": ["User is logged out"],
        "business_flow": ["Open checkout", "Attempt to continue"],
        "acceptance_criteria": [],
        "test_scenarios": [
            "Positive path validates Checkout login gate.",
            "Negative path covers: Unauthenticated checkout is blocked",
        ],
        "priority": "p2",
        "risk_level": "medium",
        "unknowns": [],
    }

    cases = generate_test_cases(requirement)
    scenario_cases = [case for case in cases if case["source"] == "test_scenarios"]

    assert len(scenario_cases) == 2
    assert scenario_cases[0]["test_type"] == "scenario"
    assert scenario_cases[1]["expected_result"] == "Unauthenticated checkout is blocked"
    assert all(case["automation_candidate"] is True for case in scenario_cases)


def test_sparse_requirement_fallback_is_safe():
    requirement = ingest_requirement("", source_id="REQ-SPARSE-001")

    cases = generate_test_cases(requirement)

    assert len(cases) == 1
    assert cases[0]["test_case_id"] == "TC-REQ-SPARSE-001-001"
    assert cases[0]["test_type"] == "fallback"
    assert cases[0]["automation_candidate"] is False
    assert cases[0]["requirement_id"] == "REQ-SPARSE-001"


def test_generated_test_cases_are_json_serializable_and_schema_stable():
    requirement = ingest_requirement(
        """
# Search Requirement
Business Flow:
- Enter a query
- Submit search
""",
        source_id="REQ-SEARCH-001",
    )

    cases = generate_test_cases(requirement)

    assert cases
    assert set(cases[0]) == {
        "test_case_id",
        "requirement_id",
        "title",
        "priority",
        "preconditions",
        "steps",
        "expected_result",
        "test_type",
        "automation_candidate",
        "risk_level",
        "source",
    }
    assert json.loads(json.dumps(cases)) == cases
