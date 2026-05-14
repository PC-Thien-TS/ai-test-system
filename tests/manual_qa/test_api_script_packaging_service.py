from __future__ import annotations

from orchestrator.manual_qa.api_script_packaging_service import APIScriptPackagingService
from orchestrator.manual_qa.api_script_validation_service import APIScriptValidationService
from orchestrator.manual_qa.models import APITestScriptDraft


def _draft(draft_id: str, file_name: str, script_content: str) -> APITestScriptDraft:
    return APITestScriptDraft(
        draft_id=draft_id,
        test_case_id=f"TC-{draft_id[-3:]}",
        requirement_ids=["REQ-001"],
        module="Order API",
        title="Draft",
        file_name=file_name,
        script_content=script_content,
    )


def _valid_script() -> str:
    return (
        'import os\nimport requests\nBASE_URL = os.getenv("API_BASE_URL", "http://localhost")\n\n'
        'def test_ok():\n'
        '    """Draft only. Not executed."""\n'
        '    response = requests.get(BASE_URL)\n'
        '    assert response.status_code == 200\n'
    )


def test_builds_package_manifest_from_drafts_and_validation_results():
    validator = APIScriptValidationService()
    packager = APIScriptPackagingService()
    drafts = [_draft("API-DRAFT-001", "test_one.py", _valid_script())]
    results = validator.validate_api_script_drafts(drafts)

    manifest = packager.build_api_script_package(
        drafts,
        results,
        validation_report_files=["script_drafts/api/api_script_validation.json"],
    )

    assert manifest.package_name == "api-script-drafts"
    assert manifest.draft_count == 1
    assert manifest.draft_files == ["test_one.py"]
    assert manifest.validation_report_files == ["script_drafts/api/api_script_validation.json"]


def test_counts_valid_invalid_warnings_correctly():
    validator = APIScriptValidationService()
    packager = APIScriptPackagingService()
    drafts = [
        _draft("API-DRAFT-001", "test_one.py", _valid_script()),
        _draft(
            "API-DRAFT-002",
            "test_two.py",
            _valid_script().replace("BASE_URL)", 'f"{BASE_URL}/TODO_ENDPOINT")'),
        ),
        _draft("API-DRAFT-003", "test_three.py", "def test_bad(:\n    pass\n"),
    ]
    results = validator.validate_api_script_drafts(drafts)

    manifest = packager.build_api_script_package(drafts, results)

    assert manifest.valid_count == 2
    assert manifest.invalid_count == 1
    assert manifest.warning_count >= 1


def test_status_ready_for_review_when_no_errors_or_warnings():
    validator = APIScriptValidationService()
    packager = APIScriptPackagingService()
    drafts = [_draft("API-DRAFT-001", "test_one.py", _valid_script())]
    results = validator.validate_api_script_drafts(drafts)

    manifest = packager.build_api_script_package(drafts, results)

    assert manifest.status == "Ready for Review"


def test_status_needs_attention_when_warnings_exist():
    validator = APIScriptValidationService()
    packager = APIScriptPackagingService()
    drafts = [
        _draft(
            "API-DRAFT-001",
            "test_one.py",
            _valid_script().replace("BASE_URL)", 'f"{BASE_URL}/TODO_ENDPOINT")'),
        )
    ]
    results = validator.validate_api_script_drafts(drafts)

    manifest = packager.build_api_script_package(drafts, results)

    assert manifest.status == "Needs Attention"


def test_status_invalid_when_errors_exist():
    validator = APIScriptValidationService()
    packager = APIScriptPackagingService()
    drafts = [_draft("API-DRAFT-001", "test_bad.py", "def test_bad(:\n    pass\n")]
    results = validator.validate_api_script_drafts(drafts)

    manifest = packager.build_api_script_package(drafts, results)

    assert manifest.status == "Invalid"


def test_does_not_zip_or_execute_files():
    validator = APIScriptValidationService()
    packager = APIScriptPackagingService()
    drafts = [_draft("API-DRAFT-001", "test_one.py", _valid_script())]
    results = validator.validate_api_script_drafts(drafts)

    manifest = packager.build_api_script_package(drafts, results)

    assert ".zip" not in "".join(manifest.draft_files)
    assert manifest.metadata["all_syntax_valid"] is True
