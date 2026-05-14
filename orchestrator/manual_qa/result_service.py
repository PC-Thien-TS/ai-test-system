"""Manual test result updates for Manual QA Phase 2."""

from __future__ import annotations

from datetime import datetime, timedelta

from orchestrator.manual_qa.models import RESULT_STATUSES, TestRun, aggregate_run_status


class TestResultService:
    """Update manual test results deterministically."""

    __test__ = False
    _BASE_TIME = datetime(2024, 1, 1, 12, 0, 0)

    def __init__(self) -> None:
        self._next_timestamp_offset = 0

    def update_test_result(
        self,
        test_run: TestRun,
        test_case_id: str,
        status: str,
        actual_result: str | None = None,
        notes: str | None = None,
        metadata: dict | None = None,
    ) -> TestRun:
        normalized_status = str(status or "").strip()
        if normalized_status not in RESULT_STATUSES:
            supported = ", ".join(RESULT_STATUSES)
            raise ValueError(f"Unsupported status '{normalized_status}'. Supported values: {supported}")

        target_id = str(test_case_id or "").strip()
        if not target_id:
            raise ValueError("test_case_id is required")

        for result in test_run.results:
            if result.test_case_id != target_id:
                continue

            result.status = normalized_status
            if actual_result is not None:
                result.actual_result = str(actual_result)
            if notes is not None:
                result.notes = str(notes)
            if metadata is not None:
                updated_metadata = dict(result.metadata)
                updated_metadata.update(dict(metadata))
                result.metadata = updated_metadata
            result.updated_at = self._next_timestamp()
            test_run.status = aggregate_run_status(test_run.results)
            test_run.completed_at = self._resolve_completed_at(test_run)
            return test_run

        raise ValueError(f"test_case_id '{target_id}' does not exist in run '{test_run.run_id}'")

    def _next_timestamp(self) -> str:
        timestamp = self._BASE_TIME + timedelta(minutes=self._next_timestamp_offset)
        self._next_timestamp_offset += 1
        return timestamp.isoformat() + "Z"

    def _resolve_completed_at(self, test_run: TestRun) -> str | None:
        if test_run.status in {"Passed", "Failed", "Blocked"}:
            return self._next_timestamp()
        return None


_DEFAULT_RESULT_SERVICE = TestResultService()


def update_test_result(
    test_run: TestRun,
    test_case_id: str,
    status: str,
    actual_result: str | None = None,
    notes: str | None = None,
    metadata: dict | None = None,
) -> TestRun:
    """Convenience wrapper for deterministic result updates."""

    return _DEFAULT_RESULT_SERVICE.update_test_result(
        test_run,
        test_case_id,
        status,
        actual_result=actual_result,
        notes=notes,
        metadata=metadata,
    )
