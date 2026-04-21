from __future__ import annotations

from mobile_appium.classifier import (
    SCREEN_TYPE_AUTH_LOGIN,
    SCREEN_TYPE_CONTENT_DETAIL,
    SCREEN_TYPE_CONTENT_LIST,
)
from mobile_appium.journey import MobileJourneyRunner
from mobile_appium.navigation import select_next_action


def test_action_selector_returns_expected_guided_actions():
    assert select_next_action(SCREEN_TYPE_AUTH_LOGIN) is not None
    assert select_next_action(SCREEN_TYPE_AUTH_LOGIN).action == "submit_login"
    assert select_next_action(SCREEN_TYPE_CONTENT_LIST) is not None
    assert select_next_action(SCREEN_TYPE_CONTENT_LIST).action == "open_first_item"
    assert select_next_action(SCREEN_TYPE_CONTENT_DETAIL) is not None
    assert select_next_action(SCREEN_TYPE_CONTENT_DETAIL).action == "go_back"


def test_guided_auto_navigation_journey_passes(android_driver, mobile_settings):
    runner = MobileJourneyRunner(android_driver, mobile_settings)

    result = runner.run_login_list_detail_back(
        username=mobile_settings.valid_username,
        password=mobile_settings.valid_password,
    )

    assert result.passed is True
    assert [step.screen_type for step in result.steps] == [
        SCREEN_TYPE_AUTH_LOGIN,
        SCREEN_TYPE_CONTENT_LIST,
        SCREEN_TYPE_CONTENT_DETAIL,
        SCREEN_TYPE_CONTENT_LIST,
    ]
