from __future__ import annotations

from mobile_appium.classifier import (
    SCREEN_TYPE_AUTH_LOGIN,
    SCREEN_TYPE_CONTENT_DETAIL,
    SCREEN_TYPE_CONTENT_LIST,
)
from mobile_appium.journey import MobileJourneyRunner


def test_login_list_detail_back_journey_passes(android_driver, mobile_settings):
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
    assert all(step.passed for step in result.steps)
