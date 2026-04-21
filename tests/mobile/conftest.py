from __future__ import annotations

import pytest

from mobile_appium.driver import create_android_driver, get_mobile_settings
from mobile_appium.screens.login_screen import LoginScreen


@pytest.fixture()
def mobile_settings():
    return get_mobile_settings()


@pytest.fixture()
def android_driver(mobile_settings):
    driver = create_android_driver(mobile_settings)
    try:
        yield driver
    finally:
        driver.quit()


@pytest.fixture()
def login_screen(android_driver, mobile_settings):
    return LoginScreen(android_driver, mobile_settings)
