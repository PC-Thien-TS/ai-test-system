from __future__ import annotations

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


def test_bounded_autonomous_exploration_visits_supported_screen_types(android_driver, mobile_settings):
    runner = MobileExplorationRunner(android_driver, mobile_settings)

    result = runner.explore(
        start_screen="LoginScreen",
        username=mobile_settings.valid_username,
        password=mobile_settings.valid_password,
        max_steps=8,
    )

    assert result.passed is True
    assert result.stop_reason == "cycle_detected"
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


def test_default_flat_policy_normalizes_to_nonempty_priorities_and_targets():
    normalized = normalize_exploration_policy(load_exploration_policy())

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
