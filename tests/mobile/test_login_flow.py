from __future__ import annotations

from mobile_appium.planner import MobileFlowPlan, plan_screen


def _execute_plan(login_screen, plan: MobileFlowPlan) -> None:
    for step in plan.steps:
        action = getattr(login_screen, step.action)
        if step.value:
            action(step.value)
            continue
        action()


def _oracle_result(login_screen, condition: str) -> bool:
    if condition == "home_screen_visible":
        return login_screen.is_home_screen_visible()
    if condition == "error_message_visible":
        return bool(login_screen.get_error_message())
    raise AssertionError(f"Unsupported oracle condition: {condition}")


def test_login_success_navigates_to_home(login_screen, mobile_settings):
    plan = plan_screen(
        "AUTH_LOGIN",
        username=mobile_settings.valid_username,
        password=mobile_settings.valid_password,
    )
    _execute_plan(login_screen, plan)

    assert _oracle_result(login_screen, plan.oracle.success_condition) is True
    assert _oracle_result(login_screen, plan.oracle.failure_condition) is False


def test_login_failure_shows_error(login_screen, mobile_settings):
    plan = plan_screen(
        "AUTH_LOGIN",
        username=mobile_settings.invalid_username,
        password=mobile_settings.invalid_password,
    )
    _execute_plan(login_screen, plan)

    assert _oracle_result(login_screen, plan.oracle.success_condition) is False
    assert _oracle_result(login_screen, plan.oracle.failure_condition) is True
