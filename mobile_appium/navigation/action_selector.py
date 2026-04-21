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


def select_next_action(screen_type: str) -> NavigationAction | None:
    if screen_type == SCREEN_TYPE_AUTH_LOGIN:
        return NavigationAction(action="submit_login", target_screen="ListScreen")
    if screen_type == SCREEN_TYPE_CONTENT_LIST:
        return NavigationAction(action="open_first_item", target_screen="DetailScreen")
    if screen_type == SCREEN_TYPE_CONTENT_DETAIL:
        return NavigationAction(action="go_back", target_screen="ListScreen")
    return None
