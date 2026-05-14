"""Manual test suite creation for Manual QA Phase 2."""

from __future__ import annotations

from typing import Iterable, List, Sequence

from orchestrator.manual_qa.models import ManualTestCase, TestSuite


class TestSuiteService:
    """Create deterministic manual test suites."""

    __test__ = False

    def __init__(self) -> None:
        self._next_suite_number = 1

    def create_test_suite(
        self,
        *,
        project_id: str,
        name: str,
        test_cases: Sequence[ManualTestCase | str],
        scope: str = "",
        owner: str = "",
        tags: Iterable[str] | None = None,
        metadata: dict | None = None,
        suite_id: str | None = None,
    ) -> TestSuite:
        clean_project_id = str(project_id or "").strip()
        clean_name = str(name or "").strip()

        if not clean_project_id:
            raise ValueError("project_id is required")
        if not clean_name:
            raise ValueError("suite name is required")

        test_case_ids = self._normalize_test_case_ids(test_cases)
        if not test_case_ids:
            raise ValueError("test_cases must not be empty")

        resolved_suite_id = str(suite_id).strip() if suite_id is not None else ""
        if not resolved_suite_id:
            resolved_suite_id = f"SUITE-{self._next_suite_number:03d}"
            self._next_suite_number += 1

        return TestSuite(
            suite_id=resolved_suite_id,
            project_id=clean_project_id,
            name=clean_name,
            test_case_ids=test_case_ids,
            scope=str(scope or "").strip(),
            owner=str(owner or "").strip(),
            tags=[str(tag).strip() for tag in tags or [] if str(tag).strip()],
            metadata=dict(metadata or {}),
        )

    def _normalize_test_case_ids(self, test_cases: Sequence[ManualTestCase | str]) -> List[str]:
        normalized: List[str] = []
        for item in test_cases:
            if isinstance(item, ManualTestCase):
                normalized.append(item.test_case_id)
                continue

            test_case_id = str(item or "").strip()
            if not test_case_id:
                raise ValueError("test_case_id must not be empty")
            normalized.append(test_case_id)

        return normalized


_DEFAULT_SUITE_SERVICE = TestSuiteService()


def create_test_suite(**kwargs: object) -> TestSuite:
    """Convenience wrapper for deterministic suite creation."""

    return _DEFAULT_SUITE_SERVICE.create_test_suite(**kwargs)
