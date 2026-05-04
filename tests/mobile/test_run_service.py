from __future__ import annotations

import json
import uuid
from pathlib import Path

from mobile_appium import MobileRunService
from mobile_appium.exploration import ExplorationResult, ExplorationStepResult


def _workspace_artifact_path(test_name: str) -> Path:
    run_id = uuid.uuid4().hex
    return Path("artifacts") / "test_runtime" / "mobile_runs" / f"{test_name}_{run_id}.json"


def test_mobile_run_service_executes_successful_mock_run(mobile_settings):
    service = MobileRunService(mobile_settings)

    artifact = service.run_bounded_exploration(
        start_screen="LoginScreen",
        username=mobile_settings.valid_username,
        password=mobile_settings.valid_password,
        max_steps=8,
    )

    assert artifact.passed is True
    assert artifact.stop_reason == "coverage_threshold_reached"
    assert artifact.visited_screens == [
        "AUTH_LOGIN",
        "CONTENT_LIST",
        "CONTENT_DETAIL",
    ]
    assert artifact.executed_actions == [
        "submit_login",
        "open_first_item",
        "go_back",
    ]
    assert artifact.coverage_score > 0.0
    assert artifact.policy_shape == "nested"
    assert artifact.duration_ms >= 0
    assert artifact.error == ""
    assert artifact.run_id
    assert artifact.started_at
    assert artifact.finished_at


def test_mobile_run_service_writes_json_artifact(mobile_settings):
    output_path = _workspace_artifact_path("mobile_run")
    service = MobileRunService(mobile_settings)

    try:
        artifact = service.run_bounded_exploration(
            start_screen="LoginScreen",
            username=mobile_settings.valid_username,
            password=mobile_settings.valid_password,
            max_steps=8,
            output_path=output_path,
        )

        assert output_path.exists()
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert payload == artifact.to_dict()
        assert payload["run_id"]
        assert payload["passed"] is True
        assert payload["policy_shape"] == "nested"
        assert payload["stop_reason"] == "coverage_threshold_reached"
        assert payload["visited_screens"] == [
            "AUTH_LOGIN",
            "CONTENT_LIST",
            "CONTENT_DETAIL",
        ]
    finally:
        output_path.unlink(missing_ok=True)


def test_mobile_run_service_returns_failure_artifact_when_runner_raises(monkeypatch, mobile_settings):
    output_path = _workspace_artifact_path("mobile_run_failure")

    def _boom(self, *, start_screen, username="", password="", max_steps=None, policy_path=None):
        raise RuntimeError("runner exploded")

    monkeypatch.setattr("mobile_appium.run_service.MobileExplorationRunner.explore", _boom)

    try:
        service = MobileRunService(mobile_settings)
        artifact = service.run_bounded_exploration(
            start_screen="LoginScreen",
            username=mobile_settings.valid_username,
            password=mobile_settings.valid_password,
            max_steps=8,
            output_path=output_path,
        )

        assert artifact.passed is False
        assert artifact.stop_reason == "execution_error"
        assert artifact.visited_screens == []
        assert artifact.executed_actions == []
        assert artifact.coverage_score == 0.0
        assert artifact.policy_shape == "nested"
        assert "RuntimeError: runner exploded" in artifact.error
        assert output_path.exists()
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        assert payload["passed"] is False
        assert payload["stop_reason"] == "execution_error"
        assert "RuntimeError: runner exploded" in payload["error"]
    finally:
        output_path.unlink(missing_ok=True)


def test_mobile_run_service_preserves_exploration_result_shape(monkeypatch, mobile_settings):
    expected = ExplorationResult(
        steps=[
            ExplorationStepResult(screen_name="LoginScreen", screen_type="AUTH_LOGIN", passed=True),
            ExplorationStepResult(screen_name="ListScreen", screen_type="CONTENT_LIST", passed=True),
        ],
        passed=True,
        stop_reason="max_steps_reached",
        visited_screen_types=["AUTH_LOGIN", "CONTENT_LIST"],
        executed_actions=["submit_login"],
        coverage_score=0.5,
        coverage_progress={"policy_shape": "flat"},
    )

    def _stub(self, *, start_screen, username="", password="", max_steps=None, policy_path=None):
        return expected

    monkeypatch.setattr("mobile_appium.run_service.MobileExplorationRunner.explore", _stub)

    service = MobileRunService(mobile_settings)
    artifact = service.run_bounded_exploration(start_screen="LoginScreen", max_steps=2)

    assert artifact.passed is True
    assert artifact.stop_reason == "max_steps_reached"
    assert artifact.visited_screens == ["AUTH_LOGIN", "CONTENT_LIST"]
    assert artifact.executed_actions == ["submit_login"]
    assert artifact.coverage_score == 0.5
    assert artifact.policy_shape == "flat"
    assert artifact.error == ""
