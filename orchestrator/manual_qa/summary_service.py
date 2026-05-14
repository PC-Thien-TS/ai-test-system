"""Manual test run summaries for Manual QA Phase 2."""

from __future__ import annotations

from orchestrator.manual_qa.models import RunSummary, TestRun, count_result_statuses


class RunSummaryService:
    """Summarize manual test run progress and outcome."""

    def summarize_test_run(self, test_run: TestRun) -> RunSummary:
        counts = count_result_statuses(test_run.results)
        total = len(test_run.results)
        pass_rate = round((counts["Pass"] / total) * 100, 2) if total else 0.0

        return RunSummary(
            run_id=test_run.run_id,
            total=total,
            passed=counts["Pass"],
            failed=counts["Fail"],
            blocked=counts["Blocked"],
            skipped=counts["Skipped"],
            not_run=counts["Not Run"],
            retest=counts["Retest"],
            pass_rate=pass_rate,
            status=test_run.status,
            metadata={
                "project_id": test_run.project_id,
                "suite_id": test_run.suite_id,
                "environment": test_run.environment,
                "build": test_run.build,
                "tester": test_run.tester,
            },
        )


_DEFAULT_SUMMARY_SERVICE = RunSummaryService()


def summarize_test_run(test_run: TestRun) -> RunSummary:
    """Convenience wrapper for deterministic run summaries."""

    return _DEFAULT_SUMMARY_SERVICE.summarize_test_run(test_run)
