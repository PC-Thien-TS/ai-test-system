from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from mobile_appium.driver import MobileTestSettings, get_mobile_settings
from mobile_appium.journey import MobileJourneyRunner
from mobile_appium.navigation import select_next_action


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EXPLORATION_POLICY_PATH = REPO_ROOT / "schemas" / "exploration_policy.yaml"


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
    coverage_score: float
    coverage_progress: dict[str, Any]


def _load_yaml_document(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def load_exploration_policy(path: Path | None = None) -> dict[str, Any]:
    return _load_yaml_document(path or DEFAULT_EXPLORATION_POLICY_PATH)


class MobileExplorationRunner:
    def __init__(self, driver, settings: MobileTestSettings | None = None) -> None:
        self.driver = driver
        self.settings = settings or get_mobile_settings()
        self.journey_runner = MobileJourneyRunner(driver, self.settings)

    def _screen_priorities(self, policy: dict[str, Any]) -> dict[str, int]:
        priorities = policy.get("screen_priorities", {})
        if not isinstance(priorities, dict):
            return {}
        normalized: dict[str, int] = {}
        for key, value in priorities.items():
            try:
                normalized[str(key).strip()] = int(value)
            except (TypeError, ValueError):
                continue
        return normalized

    def _coverage_progress(
        self,
        *,
        policy: dict[str, Any],
        visited_screen_types: list[str],
        executed_actions: list[str],
    ) -> tuple[float, dict[str, Any]]:
        coverage_strategy = policy.get("coverage_strategy", {})
        if not isinstance(coverage_strategy, dict):
            coverage_strategy = {}

        target_screen_types = coverage_strategy.get("target_screen_types", [])
        if not isinstance(target_screen_types, list):
            target_screen_types = []
        target_screen_types = [str(item).strip() for item in target_screen_types if str(item).strip()]

        target_actions = coverage_strategy.get("target_actions", [])
        if not isinstance(target_actions, list):
            target_actions = []
        target_actions = [str(item).strip() for item in target_actions if str(item).strip()]

        screen_priorities = self._screen_priorities(policy)
        weight_by_screen_priority = bool(coverage_strategy.get("weight_by_screen_priority"))

        visited_screen_set = set(visited_screen_types)
        executed_action_set = set(executed_actions)

        if target_screen_types:
            if weight_by_screen_priority:
                total_priority = sum(screen_priorities.get(screen_type, 1) for screen_type in target_screen_types)
                covered_priority = sum(
                    screen_priorities.get(screen_type, 1)
                    for screen_type in target_screen_types
                    if screen_type in visited_screen_set
                )
                screen_coverage = (covered_priority / total_priority) if total_priority > 0 else 0.0
            else:
                screen_coverage = len(visited_screen_set.intersection(target_screen_types)) / len(target_screen_types)
        else:
            screen_coverage = 0.0

        if target_actions:
            action_coverage = len(executed_action_set.intersection(target_actions)) / len(target_actions)
        else:
            action_coverage = 0.0

        if target_screen_types and target_actions:
            coverage_score = (screen_coverage + action_coverage) / 2.0
        elif target_screen_types:
            coverage_score = screen_coverage
        elif target_actions:
            coverage_score = action_coverage
        else:
            coverage_score = 0.0

        return round(coverage_score, 4), {
            "screen_types_visited": visited_screen_types,
            "screen_type_target_count": len(target_screen_types),
            "screen_type_coverage": round(screen_coverage, 4),
            "actions_executed": executed_actions,
            "action_target_count": len(target_actions),
            "action_coverage": round(action_coverage, 4),
        }

    def explore(
        self,
        *,
        start_screen: str,
        username: str = "",
        password: str = "",
        max_steps: int | None = None,
        policy_path: Path | None = None,
    ) -> ExplorationResult:
        policy = load_exploration_policy(policy_path)
        stop_conditions = policy.get("stop_conditions", {}) if isinstance(policy, dict) else {}
        if not isinstance(stop_conditions, dict):
            stop_conditions = {}
        coverage_strategy = policy.get("coverage_strategy", {}) if isinstance(policy, dict) else {}
        if not isinstance(coverage_strategy, dict):
            coverage_strategy = {}

        effective_max_steps = max_steps
        if effective_max_steps is None:
            try:
                effective_max_steps = int(stop_conditions.get("max_steps", 8))
            except (TypeError, ValueError):
                effective_max_steps = 8
        effective_max_steps = max(1, effective_max_steps)

        cycle_detection_enabled = bool(stop_conditions.get("cycle_detection", True))
        stop_on_no_valid_action = bool(stop_conditions.get("stop_on_no_valid_action", True))
        stop_on_coverage_threshold = bool(stop_conditions.get("stop_on_coverage_threshold", False))
        try:
            coverage_threshold = float(coverage_strategy.get("coverage_threshold", 1.0))
        except (TypeError, ValueError):
            coverage_threshold = 1.0
        try:
            repeated_failure_threshold = int(stop_conditions.get("repeated_failure_threshold", 1))
        except (TypeError, ValueError):
            repeated_failure_threshold = 1
        repeated_failure_threshold = max(1, repeated_failure_threshold)

        current_screen = start_screen
        steps: list[ExplorationStepResult] = []
        visited_screen_types: list[str] = []
        executed_actions: list[str] = []
        visited_actions: set[tuple[str, str]] = set()
        repeated_failures = 0
        stop_reason = "max_steps_reached"
        coverage_score = 0.0
        coverage_progress: dict[str, Any] = {
            "screen_types_visited": [],
            "screen_type_target_count": 0,
            "screen_type_coverage": 0.0,
            "actions_executed": [],
            "action_target_count": 0,
            "action_coverage": 0.0,
        }

        for index in range(effective_max_steps):
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

            if screen_result.passed:
                repeated_failures = 0
            else:
                repeated_failures += 1

            coverage_score, coverage_progress = self._coverage_progress(
                policy=policy,
                visited_screen_types=visited_screen_types,
                executed_actions=executed_actions,
            )

            if repeated_failures >= repeated_failure_threshold:
                stop_reason = "repeated_failure_threshold_reached"
                break

            if stop_on_coverage_threshold and coverage_score >= coverage_threshold:
                stop_reason = "coverage_threshold_reached"
                break

            action = select_next_action(
                screen_result.screen_type,
                policy=policy,
                failure_count=repeated_failures,
            )
            if action is None:
                stop_reason = "no_valid_action" if stop_on_no_valid_action else "no_action_available"
                break

            cycle_key = (screen_result.screen_name, action.action)
            if cycle_detection_enabled and cycle_key in visited_actions:
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
            coverage_score=coverage_score,
            coverage_progress=coverage_progress,
        )
