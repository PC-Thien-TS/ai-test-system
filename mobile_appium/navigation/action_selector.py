from __future__ import annotations

from dataclasses import dataclass

from mobile_appium.classifier import (
    SCREEN_TYPE_AUTH_LOGIN,
    SCREEN_TYPE_CONTENT_DETAIL,
    SCREEN_TYPE_CONTENT_LIST,
)


@dataclass(frozen=True)
class NavigationAction:
    action: str
    target_screen: str


def _deterministic_action(screen_type: str) -> NavigationAction | None:
    if screen_type == SCREEN_TYPE_AUTH_LOGIN:
        return NavigationAction(action="submit_login", target_screen="ListScreen")
    if screen_type == SCREEN_TYPE_CONTENT_LIST:
        return NavigationAction(action="open_first_item", target_screen="DetailScreen")
    if screen_type == SCREEN_TYPE_CONTENT_DETAIL:
        return NavigationAction(action="go_back", target_screen="ListScreen")
    return None


def select_next_action(
    screen_type: str,
    *,
    policy: dict | None = None,
    failure_count: int = 0,
) -> NavigationAction | None:
    deterministic_action = _deterministic_action(screen_type)
    if not isinstance(policy, dict) or not policy:
        return deterministic_action

    ranking = policy.get("action_ranking", {})
    if not isinstance(ranking, dict):
        return deterministic_action

    ranked_actions = ranking.get(screen_type, [])
    if not isinstance(ranked_actions, list) or not ranked_actions:
        return deterministic_action

    available_actions = {}
    if deterministic_action is not None:
        available_actions[deterministic_action.action] = deterministic_action

    fallback_behavior = policy.get("fallback_behavior", {})
    if not isinstance(fallback_behavior, dict):
        fallback_behavior = {}

    risky_action_mode = str(fallback_behavior.get("risky_action", "skip")).strip().lower() or "skip"
    no_valid_action_mode = str(fallback_behavior.get("no_valid_action", "stop")).strip().lower() or "stop"

    sorted_ranked_actions = sorted(
        [item for item in ranked_actions if isinstance(item, dict)],
        key=lambda item: int(item.get("rank", 0)),
        reverse=True,
    )

    if failure_count > 0:
        recovery_candidates = [item for item in sorted_ranked_actions if bool(item.get("recovery_action"))]
        if recovery_candidates:
            sorted_ranked_actions = recovery_candidates + [
                item for item in sorted_ranked_actions if item not in recovery_candidates
            ]

    for item in sorted_ranked_actions:
        action_name = str(item.get("action", "")).strip()
        if action_name not in available_actions:
            continue

        risk = str(item.get("risk", "normal")).strip().lower()
        if risk in {"high", "risky"} and risky_action_mode == "skip":
            continue

        return available_actions[action_name]

    if no_valid_action_mode in {"deterministic", "fallback_deterministic"}:
        return deterministic_action
    return None
