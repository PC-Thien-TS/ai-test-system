from __future__ import annotations

from orchestrator.manual_qa.requirement_importer import RequirementImporter


def test_imports_plain_text():
    importer = RequirementImporter()
    payload = """
User can log in with email and password.

Admin can review locked accounts before reactivation.
""".strip()

    records = importer.import_requirements(payload, source_ref="plain-text.txt")

    assert len(records) == 2
    assert records[0]["title"] == "User can log in with email and password."
    assert records[0]["source_ref"] == "plain-text.txt"
    assert "locked accounts" in records[1]["description"]


def test_imports_markdown_style_text():
    importer = RequirementImporter()
    payload = """
## [REQ-LOGIN-001] Login success
Module: Auth
Priority: High
Acceptance Criteria:
- User reaches the dashboard.

## Permissions error
Description: Users without permission cannot access admin pages.
Roles: user, admin
Expected Result:
- Access is denied.
""".strip()

    records = importer.import_requirements(payload, source_ref="requirements.md")

    assert len(records) == 2
    assert records[0]["requirement_id"] == "REQ-LOGIN-001"
    assert records[0]["module"] == "Auth"
    assert records[0]["acceptance_criteria"] == ["User reaches the dashboard."]
    assert records[1]["title"] == "Permissions error"
    assert records[1]["roles"] == ["user", "admin"]
    assert records[1]["source_ref"] == "requirements.md"


def test_imports_dict_payload():
    importer = RequirementImporter()
    payload = {
        "id": "REQ-100",
        "title": "Profile update",
        "description": "User can update profile details.",
    }

    records = importer.import_requirements(payload)

    assert records == [payload]


def test_imports_list_dict_payload():
    importer = RequirementImporter()
    payload = [
        {"id": "REQ-200", "title": "Create order"},
        {"id": "REQ-201", "title": "Cancel order"},
    ]

    records = importer.import_requirements(payload)

    assert len(records) == 2
    assert records[0]["id"] == "REQ-200"
    assert records[1]["id"] == "REQ-201"


def test_preserves_provided_ids_when_present():
    importer = RequirementImporter()
    payload = """
## [REQ-CUSTOM-001] Custom heading id
Description: Keep the supplied requirement identifier.
""".strip()

    records = importer.import_requirements(payload)

    assert records[0]["requirement_id"] == "REQ-CUSTOM-001"
