from __future__ import annotations

import uuid
from pathlib import Path

import yaml

from mobile_appium.classifier import (
    SCREEN_TYPE_AUTH_LOGIN,
    SCREEN_TYPE_CONTENT_DETAIL,
    SCREEN_TYPE_CONTENT_LIST,
)
from mobile_appium.exploration import MobileExplorationRunner
from mobile_appium.navigation import select_next_action


def _write_policy(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _workspace_policy_path(test_name: str) -> Path:
    run_id = uuid.uuid4().hex
    return Path("artifacts") / "test_runtime" / "mobile_policy" / f"{test_name}_{run_id}.yaml"


def test_strategy_driven_action_selection_prefers_safe_ranked_action():
    policy = {
        "action_ranking": {
            SCREEN_TYPE_CONTENT_LIST: [
                {"action": "unsupported_recovery", "rank": 100, "risk": "high", "recovery_action": True},
                {"action": "open_first_item", "rank": 80, "risk": "normal"},
            ]
        },
        "fallback_behavior": {
            "no_valid_action": "stop",
            "risky_action": "skip",
        },
    }

    action = select_next_action(
        SCREEN_TYPE_CONTENT_LIST,
        policy=policy,
        failure_count=1,
    )

    assert action is not None
    assert action.action == "open_first_item"


def test_strategy_driven_exploration_stops_on_coverage_threshold(android_driver, mobile_settings):
    policy_path = _workspace_policy_path("coverage_threshold")
    try:
        _write_policy(
            policy_path,
            {
                "screen_priorities": {
                    SCREEN_TYPE_AUTH_LOGIN: 5,
                    SCREEN_TYPE_CONTENT_LIST: 3,
                    SCREEN_TYPE_CONTENT_DETAIL: 2,
                },
                "action_ranking": {
                    SCREEN_TYPE_AUTH_LOGIN: [{"action": "submit_login", "rank": 100, "risk": "normal"}],
                    SCREEN_TYPE_CONTENT_LIST: [{"action": "open_first_item", "rank": 100, "risk": "normal"}],
                    SCREEN_TYPE_CONTENT_DETAIL: [{"action": "go_back", "rank": 90, "risk": "low"}],
                },
                "coverage_strategy": {
                    "target_screen_types": [
                        SCREEN_TYPE_AUTH_LOGIN,
                        SCREEN_TYPE_CONTENT_LIST,
                        SCREEN_TYPE_CONTENT_DETAIL,
                    ],
                    "target_actions": [
                        "submit_login",
                        "open_first_item",
                        "go_back",
                    ],
                    "coverage_threshold": 0.8,
                    "weight_by_screen_priority": True,
                },
                "stop_conditions": {
                    "max_steps": 8,
                    "cycle_detection": True,
                    "stop_on_no_valid_action": True,
                    "stop_on_coverage_threshold": True,
                    "repeated_failure_threshold": 1,
                },
                "fallback_behavior": {
                    "malformed_policy": "deterministic",
                    "no_valid_action": "stop",
                    "risky_action": "skip",
                },
            },
        )

        runner = MobileExplorationRunner(android_driver, mobile_settings)
        result = runner.explore(
            start_screen="LoginScreen",
            username=mobile_settings.valid_username,
            password=mobile_settings.valid_password,
            policy_path=policy_path,
        )

        assert result.passed is True
        assert result.stop_reason == "coverage_threshold_reached"
        assert result.coverage_score >= 0.8
        assert result.visited_screen_types == [
            SCREEN_TYPE_AUTH_LOGIN,
            SCREEN_TYPE_CONTENT_LIST,
            SCREEN_TYPE_CONTENT_DETAIL,
        ]
        assert result.executed_actions == [
            "submit_login",
            "open_first_item",
        ]
    finally:
        policy_path.unlink(missing_ok=True)
