from __future__ import annotations

import uuid
from pathlib import Path

import yaml

from mobile_appium.classifier import (
    SCREEN_TYPE_AUTH_LOGIN,
    SCREEN_TYPE_CONTENT_DETAIL,
    SCREEN_TYPE_CONTENT_LIST,
)
from mobile_appium.exploration import MobileExplorationRunner, normalize_exploration_policy
from mobile_appium.navigation import select_next_action


def _write_policy(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _workspace_policy_path(test_name: str) -> Path:
    run_id = uuid.uuid4().hex
    return Path("artifacts") / "test_runtime" / "mobile_policy" / f"{test_name}_{run_id}.yaml"


def _nested_policy_payload(*, coverage_threshold: int = 80) -> dict:
    return {
        "version": 1.0,
        "exploration_config": {
            "max_total_steps": 8,
            "max_steps_per_screen": 4,
            "max_cycles": 2,
        },
        "screen_priorities": [
            {
                "screen_type": SCREEN_TYPE_AUTH_LOGIN,
                "priority": 1,
                "max_steps": 4,
                "risky_actions": ["NAVIGATION_FORGOT_PASSWORD"],
            },
            {
                "screen_type": SCREEN_TYPE_CONTENT_LIST,
                "priority": 2,
                "max_steps": 4,
                "risky_actions": ["NAVIGATION_DETAIL"],
            },
            {
                "screen_type": SCREEN_TYPE_CONTENT_DETAIL,
                "priority": 3,
                "max_steps": 4,
                "risky_actions": ["ACTION_SHARE"],
            },
        ],
        "action_ranking": {
            SCREEN_TYPE_AUTH_LOGIN: {
                "primary": [
                    {"action": "INPUT_USERNAME", "rank": 1},
                    {"action": "INPUT_PASSWORD", "rank": 2},
                    {"action": "ACTION_SUBMIT", "rank": 3},
                ],
                "recovery": [
                    {"action": "clear_error", "rank": 1},
                ],
            },
            SCREEN_TYPE_CONTENT_LIST: {
                "primary": [
                    {"action": "LIST_CONTENT", "rank": 1},
                    {"action": "open_first_item", "rank": 2},
                ],
                "secondary": [
                    {"action": "NAVIGATION_DETAIL", "rank": 3},
                ],
            },
            SCREEN_TYPE_CONTENT_DETAIL: {
                "primary": [
                    {"action": "ACTION_ADD_TO_CART", "rank": 1},
                    {"action": "NAVIGATION_BACK", "rank": 2},
                ],
                "secondary": [
                    {"action": "CONTENT_IMAGE", "rank": 3},
                ],
                "recovery": [
                    {"action": "NAVIGATION_BACK", "rank": 1},
                ],
            },
        },
        "coverage_strategy": {
            SCREEN_TYPE_AUTH_LOGIN: {
                "required_minimum_coverage": 100,
                "optional_coverage": 0,
                "coverage_score_weight": 0.4,
                "coverage_elements": ["INPUT_USERNAME", "INPUT_PASSWORD", "ACTION_SUBMIT"],
            },
            SCREEN_TYPE_CONTENT_LIST: {
                "required_minimum_coverage": 80,
                "optional_coverage": 20,
                "coverage_score_weight": 0.3,
                "coverage_elements": ["LIST_CONTENT", "open_first_item"],
            },
            SCREEN_TYPE_CONTENT_DETAIL: {
                "required_minimum_coverage": 80,
                "optional_coverage": 20,
                "coverage_score_weight": 0.3,
                "coverage_elements": ["ACTION_ADD_TO_CART", "NAVIGATION_BACK"],
            },
        },
        "stop_conditions": {
            "global": [
                {"condition": "max_steps_reached", "threshold": "max_total_steps"},
                {"condition": "max_cycles_detected", "threshold": "max_cycles"},
                {"condition": "coverage_threshold_reached", "threshold": coverage_threshold},
                {"condition": "repeated_failure_count", "threshold": 2},
                {"condition": "no_valid_action_available", "threshold": 0},
            ],
            "per_screen": [
                {"condition": "max_steps_per_screen_reached", "threshold": "max_steps_per_screen"},
            ],
        },
        "exploration_order": [
            SCREEN_TYPE_AUTH_LOGIN,
            SCREEN_TYPE_CONTENT_LIST,
            SCREEN_TYPE_CONTENT_DETAIL,
        ],
        "fallback_behavior": {
            "on_exhausted_actions": [
                {"action": "stop_exploration", "priority": True},
            ],
        },
        "risk_assessment": {
            "high_risk_actions": ["NAVIGATION_FORGOT_PASSWORD", "NAVIGATION_DETAIL", "ACTION_SHARE"],
            "medium_risk_actions": ["INPUT_SEARCH"],
            "low_risk_actions": ["ACTION_SUBMIT", "open_first_item", "NAVIGATION_BACK"],
        },
    }


def test_normalize_exploration_policy_preserves_flat_schema():
    policy = {
        "screen_priorities": {
            SCREEN_TYPE_AUTH_LOGIN: 5,
            SCREEN_TYPE_CONTENT_LIST: 3,
            SCREEN_TYPE_CONTENT_DETAIL: 2,
        },
        "action_ranking": {
            SCREEN_TYPE_CONTENT_LIST: [
                {"action": "open_first_item", "rank": 80, "risk": "normal"},
            ],
        },
        "coverage_strategy": {
            "target_screen_types": [SCREEN_TYPE_AUTH_LOGIN, SCREEN_TYPE_CONTENT_LIST],
            "target_actions": ["submit_login", "open_first_item"],
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
    }

    normalized = normalize_exploration_policy(policy)

    assert normalized["policy_shape"] == "flat"
    assert normalized["screen_priorities"] == {
        SCREEN_TYPE_AUTH_LOGIN: 5,
        SCREEN_TYPE_CONTENT_LIST: 3,
        SCREEN_TYPE_CONTENT_DETAIL: 2,
    }
    assert normalized["coverage_strategy"]["target_screen_types"] == [
        SCREEN_TYPE_AUTH_LOGIN,
        SCREEN_TYPE_CONTENT_LIST,
    ]
    assert normalized["coverage_strategy"]["target_actions"] == [
        "submit_login",
        "open_first_item",
    ]
    assert normalized["action_ranking"][SCREEN_TYPE_CONTENT_LIST][0]["supported"] is True


def test_normalize_exploration_policy_flattens_nested_schema():
    normalized = normalize_exploration_policy(_nested_policy_payload())

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
    auth_actions = normalized["action_ranking"][SCREEN_TYPE_AUTH_LOGIN]
    detail_actions = normalized["action_ranking"][SCREEN_TYPE_CONTENT_DETAIL]
    assert any(item["action"] == "submit_login" and item["supported"] is True for item in auth_actions)
    assert any(item["source_action"] == "INPUT_USERNAME" and item["supported"] is False for item in auth_actions)
    assert any(item["action"] == "go_back" and item["supported"] is True for item in detail_actions)


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


def test_nested_policy_action_selection_uses_supported_mapped_action():
    action = select_next_action(
        SCREEN_TYPE_AUTH_LOGIN,
        policy=_nested_policy_payload(),
        failure_count=0,
    )

    assert action is not None
    assert action.action == "submit_login"


def test_nested_policy_does_not_fallback_to_deterministic_when_all_ranked_actions_are_unsupported():
    policy = _nested_policy_payload()
    policy["action_ranking"][SCREEN_TYPE_CONTENT_LIST] = {
        "primary": [
            {"action": "LIST_CONTENT", "rank": 1},
            {"action": "INPUT_SEARCH", "rank": 2},
        ],
    }

    action = select_next_action(
        SCREEN_TYPE_CONTENT_LIST,
        policy=policy,
        failure_count=0,
    )

    assert action is None


def test_nested_policy_coverage_progress_is_meaningful():
    runner = MobileExplorationRunner(None)

    coverage_score, coverage_progress = runner._coverage_progress(
        policy=_nested_policy_payload(),
        visited_screen_types=[
            SCREEN_TYPE_AUTH_LOGIN,
            SCREEN_TYPE_CONTENT_LIST,
            SCREEN_TYPE_CONTENT_DETAIL,
        ],
        executed_actions=[
            "submit_login",
            "open_first_item",
        ],
    )

    assert coverage_progress["policy_shape"] == "nested"
    assert coverage_progress["screen_type_target_count"] == 3
    assert coverage_progress["action_target_count"] == 3
    assert coverage_progress["screen_type_coverage"] > 0.0
    assert coverage_progress["action_coverage"] > 0.0
    assert coverage_score > 0.0


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


def test_nested_strategy_driven_exploration_stops_on_coverage_threshold(android_driver, mobile_settings):
    policy_path = _workspace_policy_path("nested_coverage_threshold")
    try:
        _write_policy(policy_path, _nested_policy_payload(coverage_threshold=80))

        runner = MobileExplorationRunner(android_driver, mobile_settings)
        result = runner.explore(
            start_screen="LoginScreen",
            username=mobile_settings.valid_username,
            password=mobile_settings.valid_password,
            policy_path=policy_path,
        )

        assert result.passed is True
        assert result.stop_reason == "coverage_threshold_reached"
        assert result.coverage_progress["policy_shape"] == "nested"
        assert result.coverage_progress["screen_type_target_count"] == 3
        assert result.coverage_progress["action_target_count"] == 3
        assert result.coverage_score >= 0.8
        assert result.executed_actions == [
            "submit_login",
            "open_first_item",
        ]
    finally:
        policy_path.unlink(missing_ok=True)
