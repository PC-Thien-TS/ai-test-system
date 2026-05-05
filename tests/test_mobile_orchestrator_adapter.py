from __future__ import annotations

import json
import uuid
from pathlib import Path

from mobile_appium import MobileRunArtifact, MobileRunService, MobileTestSettings
from orchestrator.mobile_adapter import (
    MOBILE_EXPLORATION_PLUGIN,
    MobileOrchestratorAdapter,
    execute_mobile_exploration_run,
)


def _workspace_artifact_path(test_name: str) -> Path:
    run_id = uuid.uuid4().hex
    return Path("artifacts") / "test_runtime" / "mobile_adapter_runs" / f"{test_name}_{run_id}.json"


def test_mobile_orchestrator_adapter_executes_successful_mock_run():
    adapter = MobileOrchestratorAdapter(service=MobileRunService(MobileTestSettings()))

    result = adapter.execute_exploration_run(
        start_screen="LoginScreen",
        username="demo",
        password="demo123",
        max_steps=8,
    )

    assert result["plugin"] == MOBILE_EXPLORATION_PLUGIN
    assert result["status"] == "passed"
    assert result["run_id"]
    assert result["summary"] == {
        "stop_reason": "coverage_threshold_reached",
        "coverage_score": result["artifact"]["coverage_score"],
        "policy_shape": "nested",
        "visited_screen_count": 3,
        "executed_action_count": 3,
    }
    assert result["artifact"]["passed"] is True
    assert result["artifact"]["visited_screens"] == [
        "AUTH_LOGIN",
        "CONTENT_LIST",
        "CONTENT_DETAIL",
    ]
    assert result["artifact"]["executed_actions"] == [
        "submit_login",
        "open_first_item",
        "go_back",
    ]
    assert result["artifact"]["error"] == ""


def test_mobile_orchestrator_adapter_maps_failed_artifact():
    class StubMobileRunService:
        def run_bounded_exploration(self, **kwargs):
            return MobileRunArtifact(
                run_id="mobile-run-failed",
                passed=False,
                stop_reason="execution_error",
                visited_screens=[],
                executed_actions=[],
                coverage_score=0.0,
                policy_shape="nested",
                started_at="2026-01-01T00:00:00Z",
                finished_at="2026-01-01T00:00:01Z",
                duration_ms=1000,
                error="RuntimeError: runner exploded",
            )

    adapter = MobileOrchestratorAdapter(service=StubMobileRunService())

    result = adapter.execute_exploration_run(start_screen="LoginScreen")

    assert result == {
        "plugin": MOBILE_EXPLORATION_PLUGIN,
        "status": "failed",
        "run_id": "mobile-run-failed",
        "summary": {
            "stop_reason": "execution_error",
            "coverage_score": 0.0,
            "policy_shape": "nested",
            "visited_screen_count": 0,
            "executed_action_count": 0,
        },
        "artifact": {
            "run_id": "mobile-run-failed",
            "passed": False,
            "stop_reason": "execution_error",
            "visited_screens": [],
            "executed_actions": [],
            "coverage_score": 0.0,
            "policy_shape": "nested",
            "started_at": "2026-01-01T00:00:00Z",
            "finished_at": "2026-01-01T00:00:01Z",
            "duration_ms": 1000,
            "error": "RuntimeError: runner exploded",
        },
    }


def test_mobile_orchestrator_adapter_passes_through_output_path():
    output_path = _workspace_artifact_path("mobile_adapter_run")
    adapter = MobileOrchestratorAdapter(service=MobileRunService(MobileTestSettings()))

    try:
        result = adapter.execute_exploration_run(
            start_screen="LoginScreen",
            username="demo",
            password="demo123",
            max_steps=8,
            output_path=output_path,
        )

        assert output_path.exists()
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert payload == result["artifact"]
    finally:
        output_path.unlink(missing_ok=True)


def test_execute_mobile_exploration_run_returns_platform_style_shape():
    result = execute_mobile_exploration_run(
        start_screen="LoginScreen",
        username="demo",
        password="demo123",
        max_steps=8,
        service=MobileRunService(MobileTestSettings()),
    )

    assert set(result) == {"plugin", "status", "run_id", "summary", "artifact"}
    assert set(result["summary"]) == {
        "stop_reason",
        "coverage_score",
        "policy_shape",
        "visited_screen_count",
        "executed_action_count",
    }
    assert set(result["artifact"]) == {
        "run_id",
        "passed",
        "stop_reason",
        "visited_screens",
        "executed_actions",
        "coverage_score",
        "policy_shape",
        "started_at",
        "finished_at",
        "duration_ms",
        "error",
    }
