from __future__ import annotations

import json

from orchestrator.requirement_ingestion import ingest_requirement
from orchestrator.script_generator import generate_pytest_script
from orchestrator.testcase_generator import generate_test_cases


def test_generate_script_from_login_test_case():
    requirement = ingest_requirement(
        """
# Login Requirement
Business Flow:
- Enter username and password
- Submit login request
Acceptance Criteria:
- Valid credentials redirect the user to the dashboard.
""",
        source_id="LOGIN-REQ-001",
    )
    case = generate_test_cases(requirement)[0]

    result = generate_pytest_script(case)
    script = result["script"]

    assert "import pytest" in script
    assert "import requests" in script
    assert 'BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")' in script
    assert "def test_tc_login_req_001_001_login_requirement_happy_path():" in script
    assert "# Preconditions:" in script
    assert "# Steps:" in script
    assert "# Expected result:" in script
    assert 'pytest.skip("No API endpoint/method metadata provided for this generated skeleton.")' in script


def test_generate_script_from_multiple_test_cases():
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

    result = generate_pytest_script(cases)

    assert len(result["generated_test_names"]) == len(cases)
    assert result["script"].count("def test_") == len(cases)


def test_sparse_input_fallback_is_handled_safely():
    sparse_case = {
        "test_case_id": "TC-SPARSE-001",
        "requirement_id": "REQ-SPARSE-001",
        "title": "Sparse fallback",
        "priority": "p2",
        "preconditions": [],
        "steps": [],
        "expected_result": "",
        "test_type": "fallback",
        "automation_candidate": False,
        "risk_level": "low",
        "source": "fallback",
    }

    result = generate_pytest_script(sparse_case)

    assert "def test_tc_sparse_001_sparse_fallback():" in result["script"]
    assert "# Preconditions: none provided" in result["script"]
    assert "# Steps: no deterministic steps were provided" in result["script"]


def test_generated_script_compiles():
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
    result = generate_pytest_script(cases)

    compile(result["script"], "<generated_script>", "exec")


def test_generated_script_metadata_shape_is_stable():
    requirement = ingest_requirement(
        """
# Checkout Requirement
Business Flow:
- Open checkout
- Submit order
""",
        source_id="REQ-CHECKOUT-001",
    )
    case = generate_test_cases(requirement)[0]

    result = generate_pytest_script(case)

    assert set(result) == {
        "script",
        "script_type",
        "framework",
        "generated_test_names",
    }
    assert result["script_type"] == "api_pytest"
    assert result["framework"] == "pytest"
    assert isinstance(result["generated_test_names"], list)
    assert json.loads(json.dumps(result)) == result
