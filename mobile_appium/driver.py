from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from appium import webdriver
from appium.options.android import UiAutomator2Options
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException


@dataclass(frozen=True)
class MobileTestSettings:
    mode: str = "mock"
    server_url: str = "http://127.0.0.1:4723"
    platform_name: str = "Android"
    automation_name: str = "UiAutomator2"
    device_name: str = "Android Emulator"
    app: str = ""
    app_package: str = ""
    app_activity: str = ""
    username_id: str = "com.example:id/username"
    password_id: str = "com.example:id/password"
    login_button_id: str = "com.example:id/login"
    error_message_id: str = "com.example:id/error_message"
    home_marker_id: str = "com.example:id/home_screen"
    login_activity: str = ".LoginActivity"
    home_activity: str = ".HomeActivity"
    valid_username: str = "demo"
    valid_password: str = "demo123"
    invalid_username: str = "bad-user"
    invalid_password: str = "bad-pass"


def get_mobile_settings() -> MobileTestSettings:
    return MobileTestSettings(
        mode=os.getenv("MOBILE_TEST_MODE", "mock").strip().lower() or "mock",
        server_url=os.getenv("MOBILE_APPIUM_SERVER_URL", "http://127.0.0.1:4723"),
        platform_name=os.getenv("MOBILE_PLATFORM_NAME", "Android"),
        automation_name=os.getenv("MOBILE_AUTOMATION_NAME", "UiAutomator2"),
        device_name=os.getenv("MOBILE_DEVICE_NAME", "Android Emulator"),
        app=os.getenv("MOBILE_APP", ""),
        app_package=os.getenv("MOBILE_APP_PACKAGE", ""),
        app_activity=os.getenv("MOBILE_APP_ACTIVITY", ""),
        username_id=os.getenv("MOBILE_LOGIN_USERNAME_ID", "com.example:id/username"),
        password_id=os.getenv("MOBILE_LOGIN_PASSWORD_ID", "com.example:id/password"),
        login_button_id=os.getenv("MOBILE_LOGIN_BUTTON_ID", "com.example:id/login"),
        error_message_id=os.getenv("MOBILE_LOGIN_ERROR_ID", "com.example:id/error_message"),
        home_marker_id=os.getenv("MOBILE_HOME_MARKER_ID", "com.example:id/home_screen"),
        login_activity=os.getenv("MOBILE_LOGIN_ACTIVITY", ".LoginActivity"),
        home_activity=os.getenv("MOBILE_HOME_ACTIVITY", ".HomeActivity"),
        valid_username=os.getenv("MOBILE_LOGIN_USERNAME", "demo"),
        valid_password=os.getenv("MOBILE_LOGIN_PASSWORD", "demo123"),
        invalid_username=os.getenv("MOBILE_INVALID_USERNAME", "bad-user"),
        invalid_password=os.getenv("MOBILE_INVALID_PASSWORD", "bad-pass"),
    )


class FakeMobileElement:
    def __init__(self, driver: "FakeAndroidDriver", element_id: str) -> None:
        self.driver = driver
        self.element_id = element_id

    @property
    def text(self) -> str:
        if self.element_id == self.driver.settings.error_message_id:
            return self.driver.error_message
        if self.element_id == self.driver.settings.home_marker_id:
            return "Home"
        return self.driver.values.get(self.element_id, "")

    def clear(self) -> None:
        self.driver.values[self.element_id] = ""

    def send_keys(self, value: str) -> None:
        self.driver.values[self.element_id] = value

    def click(self) -> None:
        if self.element_id == self.driver.settings.login_button_id:
            self.driver.submit_login()

    def is_displayed(self) -> bool:
        if self.element_id == self.driver.settings.error_message_id:
            return bool(self.driver.error_message)
        if self.element_id == self.driver.settings.home_marker_id:
            return self.driver.logged_in
        return True


class FakeAndroidDriver:
    def __init__(self, settings: MobileTestSettings) -> None:
        self.settings = settings
        self.values = {
            settings.username_id: "",
            settings.password_id: "",
        }
        self.current_activity = settings.login_activity
        self.error_message = ""
        self.logged_in = False

    def find_element(self, by: str, value: str) -> FakeMobileElement:
        if by != AppiumBy.ID:
            raise NoSuchElementException(f"Unsupported locator strategy: {by}")
        allowed_ids = {
            self.settings.username_id,
            self.settings.password_id,
            self.settings.login_button_id,
        }
        if value in allowed_ids:
            return FakeMobileElement(self, value)
        if value == self.settings.error_message_id and self.error_message:
            return FakeMobileElement(self, value)
        if value == self.settings.home_marker_id and self.logged_in:
            return FakeMobileElement(self, value)
        raise NoSuchElementException(f"Element not found: {value}")

    def submit_login(self) -> None:
        username = self.values.get(self.settings.username_id, "")
        password = self.values.get(self.settings.password_id, "")
        if username == self.settings.valid_username and password == self.settings.valid_password:
            self.logged_in = True
            self.error_message = ""
            self.current_activity = self.settings.home_activity
            return
        self.logged_in = False
        self.current_activity = self.settings.login_activity
        self.error_message = "Invalid username or password"

    def quit(self) -> None:
        return None


def _build_real_android_driver(settings: MobileTestSettings) -> webdriver.Remote:
    options = UiAutomator2Options()
    capabilities: dict[str, Any] = {
        "platformName": settings.platform_name,
        "appium:automationName": settings.automation_name,
        "appium:deviceName": settings.device_name,
    }
    if settings.app:
        capabilities["appium:app"] = settings.app
    if settings.app_package:
        capabilities["appium:appPackage"] = settings.app_package
    if settings.app_activity:
        capabilities["appium:appActivity"] = settings.app_activity
    if not any([settings.app, settings.app_package, settings.app_activity]):
        raise ValueError(
            "Real Appium mode requires MOBILE_APP or MOBILE_APP_PACKAGE/MOBILE_APP_ACTIVITY to be configured."
        )
    options.load_capabilities(capabilities)
    return webdriver.Remote(settings.server_url, options=options)


def create_android_driver(settings: MobileTestSettings | None = None) -> Any:
    resolved = settings or get_mobile_settings()
    if resolved.mode == "appium":
        return _build_real_android_driver(resolved)
    return FakeAndroidDriver(resolved)
