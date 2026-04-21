from __future__ import annotations

from dataclasses import dataclass

from mobile_appium.classifier import classify_screen
from mobile_appium.driver import MobileTestSettings, get_mobile_settings
from mobile_appium.planner import MobileFlowPlan, plan_screen
from mobile_appium.screens.login_screen import LoginScreen


@dataclass(frozen=True)
class JourneyScreenResult:
    screen_name: str
    screen_type: str
    success_condition: str
    failure_condition: str
    passed: bool


@dataclass(frozen=True)
class JourneyResult:
    steps: list[JourneyScreenResult]
    passed: bool


class MobileJourneyRunner:
    def __init__(self, driver, settings: MobileTestSettings | None = None) -> None:
        self.driver = driver
        self.settings = settings or get_mobile_settings()
        self.login_screen = LoginScreen(driver, self.settings)

    def _execute_plan(self, plan: MobileFlowPlan) -> None:
        for step in plan.steps:
            if step.action == "enter_username":
                self.login_screen.enter_username(step.value)
                continue
            if step.action == "enter_password":
                self.login_screen.enter_password(step.value)
                continue
            if step.action == "tap_login":
                self.login_screen.tap_login()
                continue
            if step.action == "validate_list_loaded":
                if not self._is_screen_loaded("ListScreen"):
                    raise AssertionError("List screen is not loaded.")
                continue
            if step.action == "validate_list_items_visible":
                if not self._oracle_result("list_items_visible"):
                    raise AssertionError("List items are not visible.")
                continue
            if step.action == "validate_detail_loaded":
                if not self._is_screen_loaded("DetailScreen"):
                    raise AssertionError("Detail screen is not loaded.")
                continue
            if step.action == "validate_detail_content_visible":
                if not self._oracle_result("detail_content_visible"):
                    raise AssertionError("Detail content is not visible.")
                continue
            raise AssertionError(f"Unsupported journey step action: {step.action}")

    def _is_screen_loaded(self, screen_name: str) -> bool:
        if hasattr(self.driver, "is_screen_loaded"):
            return bool(self.driver.is_screen_loaded(screen_name))
        return False

    def _oracle_result(self, condition: str) -> bool:
        if condition == "home_screen_visible":
            return self.login_screen.is_home_screen_visible()
        if condition == "error_message_visible":
            return bool(self.login_screen.get_error_message())
        if condition == "list_items_visible":
            if hasattr(self.driver, "has_list_items"):
                return bool(self.driver.has_list_items())
            return False
        if condition == "detail_content_visible":
            if hasattr(self.driver, "has_detail_content"):
                return bool(self.driver.has_detail_content())
            return False
        if condition == "screen_loaded":
            return bool(getattr(self.driver, "current_screen_name", ""))
        raise AssertionError(f"Unsupported oracle condition: {condition}")

    def _evaluate_screen(
        self,
        screen_name: str,
        *,
        username: str = "",
        password: str = "",
    ) -> JourneyScreenResult:
        classification = classify_screen(screen_name)
        plan = plan_screen(screen_name, username=username, password=password)
        if classification.screen_type != plan.screen_type:
            raise AssertionError(
                f"Planner/classifier mismatch for {screen_name}: {classification.screen_type} != {plan.screen_type}"
            )

        self._execute_plan(plan)
        passed = self._oracle_result(plan.oracle.success_condition) and not self._oracle_result(plan.oracle.failure_condition)
        return JourneyScreenResult(
            screen_name=plan.screen_name,
            screen_type=plan.screen_type,
            success_condition=plan.oracle.success_condition,
            failure_condition=plan.oracle.failure_condition,
            passed=passed,
        )

    def _open_detail(self) -> None:
        if not hasattr(self.driver, "open_detail"):
            raise AssertionError("Driver does not support opening detail screen.")
        self.driver.open_detail()

    def _back_to_list(self) -> None:
        if not hasattr(self.driver, "back_to_list"):
            raise AssertionError("Driver does not support returning to list screen.")
        self.driver.back_to_list()

    def run_login_list_detail_back(self, *, username: str, password: str) -> JourneyResult:
        results = [
            self._evaluate_screen("LoginScreen", username=username, password=password),
            self._evaluate_screen("ListScreen"),
        ]

        self._open_detail()
        results.append(self._evaluate_screen("DetailScreen"))

        self._back_to_list()
        results.append(self._evaluate_screen("ListScreen"))

        return JourneyResult(
            steps=results,
            passed=all(result.passed for result in results),
        )
