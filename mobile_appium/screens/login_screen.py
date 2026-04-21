from __future__ import annotations

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException

from mobile_appium.driver import MobileTestSettings, get_mobile_settings


class LoginScreen:
    def __init__(self, driver, settings: MobileTestSettings | None = None) -> None:
        self.driver = driver
        self.settings = settings or get_mobile_settings()

    def enter_username(self, username: str) -> None:
        field = self.driver.find_element(AppiumBy.ID, self.settings.username_id)
        field.clear()
        field.send_keys(username)

    def enter_password(self, password: str) -> None:
        field = self.driver.find_element(AppiumBy.ID, self.settings.password_id)
        field.clear()
        field.send_keys(password)

    def tap_login(self) -> None:
        self.driver.find_element(AppiumBy.ID, self.settings.login_button_id).click()

    def login(self, username: str, password: str) -> None:
        self.enter_username(username)
        self.enter_password(password)
        self.tap_login()

    def is_home_screen_visible(self) -> bool:
        try:
            marker = self.driver.find_element(AppiumBy.ID, self.settings.home_marker_id)
            return marker.is_displayed()
        except NoSuchElementException:
            return getattr(self.driver, "current_activity", "") == self.settings.home_activity

    def get_error_message(self) -> str:
        try:
            return self.driver.find_element(AppiumBy.ID, self.settings.error_message_id).text
        except NoSuchElementException:
            return ""
