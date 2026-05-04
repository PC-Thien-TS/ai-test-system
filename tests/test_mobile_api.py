"""Tests for mobile run API endpoints."""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from mobile_appium import MobileRunArtifact


@pytest.fixture
def temp_repo_root():
    repo_root = Path("artifacts") / "test_runtime" / "api_repo_roots" / uuid.uuid4().hex
    repo_root.mkdir(parents=True, exist_ok=True)
    try:
        yield repo_root.resolve()
    finally:
        shutil.rmtree(repo_root, ignore_errors=True)


@pytest.fixture
def client(temp_repo_root):
    import sys

    sys.modules["api.deps"].REPO_ROOT = temp_repo_root
    app = create_app()
    return TestClient(app)


def test_trigger_mobile_exploration_run_success(client):
    response = client.post(
        "/mobile/runs/exploration",
        json={
            "start_screen": "LoginScreen",
            "username": "demo",
            "password": "demo123",
            "max_steps": 8,
        },
        headers={"X-User-ID": "test-user", "X-User-Role": "maintainer"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["run_id"]
    assert data["passed"] is True
    assert data["stop_reason"] == "coverage_threshold_reached"
    assert data["visited_screens"] == [
        "AUTH_LOGIN",
        "CONTENT_LIST",
        "CONTENT_DETAIL",
    ]
    assert data["executed_actions"] == [
        "submit_login",
        "open_first_item",
        "go_back",
    ]
    assert data["coverage_score"] > 0.0
    assert data["policy_shape"] == "nested"
    assert data["duration_ms"] >= 0
    assert data["error"] == ""


def test_trigger_mobile_exploration_run_failure_shape(client, monkeypatch):
    def _fake_failure(self, *, start_screen="LoginScreen", username="", password="", max_steps=None, output_path=None):
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

    monkeypatch.setattr("api.routes.mobile.MobileRunService.run_bounded_exploration", _fake_failure)

    response = client.post(
        "/mobile/runs/exploration",
        json={"start_screen": "LoginScreen"},
        headers={"X-User-ID": "test-user", "X-User-Role": "maintainer"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data == {
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
    }


def test_trigger_mobile_exploration_run_response_schema_and_safe_output_path(client, temp_repo_root):
    response = client.post(
        "/mobile/runs/exploration",
        json={
            "start_screen": "LoginScreen",
            "username": "demo",
            "password": "demo123",
            "max_steps": 8,
            "output_path": "artifacts/mobile_runs/api_mobile_run.json",
        },
        headers={"X-User-ID": "test-user", "X-User-Role": "maintainer"},
    )

    assert response.status_code == 200
    data = response.json()
    assert set(data) == {
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
    assert data["run_id"]
    assert isinstance(data["visited_screens"], list)
    assert isinstance(data["executed_actions"], list)
    assert isinstance(data["coverage_score"], float)

    artifact_path = temp_repo_root / "artifacts" / "mobile_runs" / "api_mobile_run.json"
    assert artifact_path.exists()
    artifact_path.unlink(missing_ok=True)
