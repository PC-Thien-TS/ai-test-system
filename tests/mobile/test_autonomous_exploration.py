from __future__ import annotations

import uuid
from pathlib import Path

import yaml

from mobile_appium.classifier import (
    SCREEN_TYPE_AUTH_LOGIN,
    SCREEN_TYPE_CONTENT_DETAIL,
    SCREEN_TYPE_CONTENT_LIST,
)
from mobile_appium.exploration import (
    MobileExplorationRunner,
    load_exploration_policy,
    normalize_exploration_policy,
)


def _write_policy(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _workspace_policy_path(test_name: str) -> Path:
    run_id = uuid.uuid4().hex
    return Path("artifacts") / "test_runtime" / "mobile_policy" / f"{test_name}_{run_id}.yaml"


def _legacy_flat_policy() -> dict:
    return {
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
            "coverage_threshold": 1.0,
            "weight_by_screen_priority": True,
        },
        "stop_conditions": {
            "max_steps": 8,
            "cycle_detection": True,
            "stop_on_no_valid_action": True,
            "stop_on_coverage_threshold": False,
            "repeated_failure_threshold": 1,
        },
        "fallback_behavior": {
            "malformed_policy": "deterministic",
            "no_valid_action": "stop",
            "risky_action": "skip",
        },
    }


def test_bounded_autonomous_exploration_with_default_nested_policy_visits_supported_screen_types(
    android_driver,
    mobile_settings,
):
    runner = MobileExplorationRunner(android_driver, mobile_settings)

    result = runner.explore(
        start_screen="LoginScreen",
        username=mobile_settings.valid_username,
        password=mobile_settings.valid_password,
        max_steps=8,
    )

    assert result.passed is True
    assert result.stop_reason == "coverage_threshold_reached"
    assert result.visited_screen_types == [
        SCREEN_TYPE_AUTH_LOGIN,
        SCREEN_TYPE_CONTENT_LIST,
        SCREEN_TYPE_CONTENT_DETAIL,
    ]
    assert result.coverage_score > 0.0
    assert result.coverage_progress["policy_shape"] == "nested"
    assert result.executed_actions == [
        "submit_login",
        "open_first_item",
        "go_back",
    ]
    assert [step.screen_type for step in result.steps] == [
        SCREEN_TYPE_AUTH_LOGIN,
        SCREEN_TYPE_CONTENT_LIST,
        SCREEN_TYPE_CONTENT_DETAIL,
        SCREEN_TYPE_CONTENT_LIST,
    ]


def test_default_nested_policy_normalizes_to_nonempty_priorities_and_targets():
    normalized = normalize_exploration_policy(load_exploration_policy())

    assert normalized["policy_shape"] == "nested"
    assert normalized["screen_priorities"] == {
        SCREEN_TYPE_AUTH_LOGIN: 1,
        SCREEN_TYPE_CONTENT_LIST: 2,
        SCREEN_TYPE_CONTENT_DETAIL: 3,
    }
    assert normalized["coverage_strategy"]["target_screen_types"] == [
        SCREEN_TYPE_AUTH_LOGIN,
        SCREEN_TYPE_CONTENT_LIST,
        SCREEN_TYPE_CONTENT_DETAIL,
    ]
    assert normalized["coverage_strategy"]["target_actions"] == [
        "submit_login",
        "open_first_item",
        "go_back",
    ]


def test_legacy_flat_policy_normalizes_to_nonempty_priorities_and_targets():
    normalized = normalize_exploration_policy(_legacy_flat_policy())

    assert normalized["policy_shape"] == "flat"
    assert normalized["screen_priorities"] == {
        SCREEN_TYPE_AUTH_LOGIN: 5,
        SCREEN_TYPE_CONTENT_LIST: 3,
        SCREEN_TYPE_CONTENT_DETAIL: 2,
    }
    assert normalized["coverage_strategy"]["target_screen_types"] == [
        SCREEN_TYPE_AUTH_LOGIN,
        SCREEN_TYPE_CONTENT_LIST,
        SCREEN_TYPE_CONTENT_DETAIL,
    ]
    assert normalized["coverage_strategy"]["target_actions"] == [
        "submit_login",
        "open_first_item",
        "go_back",
    ]


def test_bounded_autonomous_exploration_with_legacy_flat_policy_stops_on_cycle_detection(
    android_driver,
    mobile_settings,
):
    policy_path = _workspace_policy_path("legacy_cycle_detection")
    try:
        _write_policy(policy_path, _legacy_flat_policy())

        runner = MobileExplorationRunner(android_driver, mobile_settings)
        result = runner.explore(
            start_screen="LoginScreen",
            username=mobile_settings.valid_username,
            password=mobile_settings.valid_password,
            max_steps=8,
            policy_path=policy_path,
        )

        assert result.passed is True
        assert result.stop_reason == "cycle_detected"
        assert result.coverage_score > 0.0
        assert result.coverage_progress["policy_shape"] == "flat"
        assert result.visited_screen_types == [
            SCREEN_TYPE_AUTH_LOGIN,
            SCREEN_TYPE_CONTENT_LIST,
            SCREEN_TYPE_CONTENT_DETAIL,
        ]
        assert result.executed_actions == [
            "submit_login",
            "open_first_item",
            "go_back",
        ]
        assert [step.screen_type for step in result.steps] == [
            SCREEN_TYPE_AUTH_LOGIN,
            SCREEN_TYPE_CONTENT_LIST,
            SCREEN_TYPE_CONTENT_DETAIL,
            SCREEN_TYPE_CONTENT_LIST,
        ]
    finally:
        policy_path.unlink(missing_ok=True)
