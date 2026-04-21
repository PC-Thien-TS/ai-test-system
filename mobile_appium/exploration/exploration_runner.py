from __future__ import annotations

from dataclasses import dataclass

from mobile_appium.driver import MobileTestSettings, get_mobile_settings
from mobile_appium.journey import MobileJourneyRunner
from mobile_appium.navigation import select_next_action


@dataclass(frozen=True)
class ExplorationStepResult:
    screen_name: str
    screen_type: str
    passed: bool


@dataclass(frozen=True)
class ExplorationResult:
    steps: list[ExplorationStepResult]
    passed: bool
    stop_reason: str
    visited_screen_types: list[str]
    executed_actions: list[str]


class MobileExplorationRunner:
    def __init__(self, driver, settings: MobileTestSettings | None = None) -> None:
        self.driver = driver
        self.settings = settings or get_mobile_settings()
        self.journey_runner = MobileJourneyRunner(driver, self.settings)

    def explore(
        self,
        *,
        start_screen: str,
        username: str = "",
        password: str = "",
        max_steps: int = 8,
    ) -> ExplorationResult:
        current_screen = start_screen
        steps: list[ExplorationStepResult] = []
        visited_screen_types: list[str] = []
        executed_actions: list[str] = []
        visited_actions: set[tuple[str, str]] = set()
        stop_reason = "max_steps_reached"

        for index in range(max_steps):
            screen_result = self.journey_runner._evaluate_screen(
                current_screen,
                username=username if index == 0 else "",
                password=password if index == 0 else "",
            )
            steps.append(
                ExplorationStepResult(
                    screen_name=screen_result.screen_name,
                    screen_type=screen_result.screen_type,
                    passed=screen_result.passed,
                )
            )
            if screen_result.screen_type not in visited_screen_types:
                visited_screen_types.append(screen_result.screen_type)

            action = select_next_action(screen_result.screen_type)
            if action is None:
                stop_reason = "no_action_available"
                break

            cycle_key = (screen_result.screen_name, action.action)
            if cycle_key in visited_actions:
                stop_reason = "cycle_detected"
                break

            visited_actions.add(cycle_key)
            executed_actions.append(action.action)
            current_screen = self.journey_runner._execute_navigation_action(action)
        else:
            stop_reason = "max_steps_reached"

        return ExplorationResult(
            steps=steps,
            passed=all(step.passed for step in steps),
            stop_reason=stop_reason,
            visited_screen_types=visited_screen_types,
            executed_actions=executed_actions,
        )
