from __future__ import annotations

import json

from orchestrator.requirement_ingestion import ingest_requirement


def test_parse_simple_login_requirement():
    payload = """
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
- Invalid credentials show an error message.
Priority: High
"""

    result = ingest_requirement(payload, source_id="LOGIN-REQ-001")

    assert result["requirement_id"] == "LOGIN-REQ-001"
    assert result["title"] == "Login Requirement"
    assert result["feature"] == "Authentication"
    assert result["actor"] == "User"
    assert result["preconditions"] == [
        "User account exists",
        "User is on the login screen",
    ]
    assert result["business_flow"] == [
        "Enter username and password",
        "Submit login request",
    ]
    assert result["acceptance_criteria"] == [
        "Valid credentials redirect the user to the dashboard.",
        "Invalid credentials show an error message.",
    ]
    assert result["priority"] == "p1"
    assert result["risk_level"] == "medium"
    assert result["unknowns"] == []
    assert result["test_scenarios"]


def test_parse_requirement_with_acceptance_criteria_and_user_story_inference():
    payload = """
As a user, I want to log in so that I can access my account.

## Acceptance Criteria
- Given a registered account
- When valid credentials are submitted
- Then the dashboard is displayed
- And invalid credentials are rejected with a clear message
"""

    result = ingest_requirement(payload, source_name="Authentication")

    assert result["title"] == "As a user, I want to log in so that I can access my account."
    assert result["feature"] == "Auth & Account"
    assert result["actor"] == "user"
    assert result["acceptance_criteria"] == [
        "Given a registered account",
        "When valid credentials are submitted",
        "Then the dashboard is displayed",
        "And invalid credentials are rejected with a clear message",
    ]
    assert result["business_flow"] == [
        "User attempts to log in so that I can access my account."
    ]
    assert "preconditions" in result["unknowns"]
    assert any("Negative path covers:" in scenario for scenario in result["test_scenarios"])


def test_parse_missing_or_ambiguous_input_safely():
    result = ingest_requirement("System should be easy to use.")

    assert result["title"] == "System should be easy to use."
    assert result["feature"] == ""
    assert result["actor"] == ""
    assert result["preconditions"] == []
    assert result["acceptance_criteria"] == []
    assert result["priority"] == "p2"
    assert result["risk_level"] == "low"
    assert set(result["unknowns"]) >= {
        "feature",
        "actor",
        "preconditions",
        "acceptance_criteria",
    }


def test_requirement_ingestion_output_schema_is_stable_and_serializable():
    result = ingest_requirement("", source_name="SRS")

    assert set(result) == {
        "requirement_id",
        "title",
        "feature",
        "actor",
        "preconditions",
        "business_flow",
        "acceptance_criteria",
        "test_scenarios",
        "priority",
        "risk_level",
        "unknowns",
    }
    assert result["title"] == "Untitled Requirement"
    assert "empty_input" in result["unknowns"]
    assert json.loads(json.dumps(result)) == result
