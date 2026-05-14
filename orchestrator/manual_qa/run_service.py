"""Manual test run creation for Manual QA Phase 2."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Sequence

from orchestrator.manual_qa.models import TestResult, TestRun, TestSuite, aggregate_run_status


class TestRunService:
    """Create deterministic manual test runs with initialized results."""

    __test__ = False
    _BASE_TIME = datetime(2024, 1, 1, 0, 0, 0)

    def __init__(self) -> None:
        self._next_run_number = 1
        self._next_timestamp_offset = 0

    def create_test_run(
        self,
        *,
        project_id: str,
        suite: TestSuite | str,
        environment: str,
        build: str,
        tester: str,
        run_id: str | None = None,
        metadata: dict | None = None,
        test_case_ids: Sequence[str] | None = None,
    ) -> TestRun:
        clean_project_id = str(project_id or "").strip()
        if not clean_project_id:
            raise ValueError("project_id is required")

        suite_id, suite_case_ids = self._resolve_suite(suite, test_case_ids=test_case_ids)
        if not suite_case_ids:
            raise ValueError("test_case_ids must not be empty")

        resolved_run_id = str(run_id).strip() if run_id is not None else ""
        if not resolved_run_id:
            resolved_run_id = f"RUN-{self._next_run_number:03d}"
            self._next_run_number += 1

        results = [
            TestResult(
                result_id=f"RESULT-{index:03d}",
                run_id=resolved_run_id,
                test_case_id=test_case_id,
                status="Not Run",
            )
            for index, test_case_id in enumerate(suite_case_ids, start=1)
        ]

        started_at = self._next_timestamp()
        status = aggregate_run_status(results)

        return TestRun(
            run_id=resolved_run_id,
            project_id=clean_project_id,
            suite_id=suite_id,
            environment=str(environment or "").strip(),
            build=str(build or "").strip(),
            tester=str(tester or "").strip(),
            status=status,
            results=results,
            started_at=started_at,
            completed_at=None,
            metadata=dict(metadata or {}),
        )

    def _resolve_suite(
        self,
        suite: TestSuite | str,
        *,
        test_case_ids: Sequence[str] | None,
    ) -> tuple[str, list[str]]:
        if isinstance(suite, TestSuite):
            return suite.suite_id, list(suite.test_case_ids)

        suite_id = str(suite or "").strip()
        if not suite_id:
            raise ValueError("suite is required")
        if not test_case_ids:
            raise ValueError("test_case_ids are required when suite is provided as a suite_id")

        normalized = [str(test_case_id).strip() for test_case_id in test_case_ids if str(test_case_id).strip()]
        return suite_id, normalized

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"


_DEFAULT_RUN_SERVICE = TestRunService()


def create_test_run(**kwargs: object) -> TestRun:
    """Convenience wrapper for deterministic run creation."""

    return _DEFAULT_RUN_SERVICE.create_test_run(**kwargs)
