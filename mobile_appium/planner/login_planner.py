from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "schemas" / "mobile_app_manifest.yaml"


@dataclass(frozen=True)
class MobileActionStep:
    action: str
    value: str = ""


@dataclass(frozen=True)
class MobileFlowOracle:
    success_condition: str
    failure_condition: str


@dataclass(frozen=True)
class MobileFlowPlan:
    screen_type: str
    steps: list[MobileActionStep]
    oracle: MobileFlowOracle
    source: str


def load_mobile_manifest(path: Path | None = None) -> dict[str, Any]:
    manifest_path = path or DEFAULT_MANIFEST_PATH
    if not manifest_path.exists():
        return {}
    payload = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _fallback_login_definition() -> dict[str, Any]:
    return {
        "screen_type": "AUTH_LOGIN",
        "steps": [
            {"action": "enter_username"},
            {"action": "enter_password"},
            {"action": "tap_login"},
        ],
        "oracle": {
            "success_condition": "home_screen_visible",
            "failure_condition": "error_message_visible",
        },
    }


def _manifest_login_definition(manifest: dict[str, Any], screen_type: str) -> dict[str, Any] | None:
    screens = manifest.get("screens")
    if isinstance(screens, dict):
        screen = screens.get(screen_type)
        if isinstance(screen, dict):
            return screen
    if isinstance(screens, list):
        for screen in screens:
            if not isinstance(screen, dict):
                continue
            if str(screen.get("type", "")).upper() == screen_type:
                return screen
            if str(screen.get("screen_type", "")).upper() == screen_type:
                return screen
    return None


def _normalize_steps(definition: dict[str, Any], *, username: str, password: str) -> list[MobileActionStep]:
    planned_steps = definition.get("steps", [])
    if not isinstance(planned_steps, list):
        planned_steps = []

    steps: list[MobileActionStep] = []
    for step in planned_steps:
        if not isinstance(step, dict):
            continue
        action = str(step.get("action", "")).strip()
        if not action:
            continue
        if action == "enter_username":
            steps.append(MobileActionStep(action=action, value=username))
            continue
        if action == "enter_password":
            steps.append(MobileActionStep(action=action, value=password))
            continue
        steps.append(MobileActionStep(action=action, value=str(step.get("value", ""))))

    if steps:
        return steps

    return [
        MobileActionStep(action="enter_username", value=username),
        MobileActionStep(action="enter_password", value=password),
        MobileActionStep(action="tap_login"),
    ]


def _normalize_oracle(definition: dict[str, Any]) -> MobileFlowOracle:
    oracle = definition.get("oracle", {})
    if not isinstance(oracle, dict):
        oracle = {}
    success_condition = str(oracle.get("success_condition", "home_screen_visible")).strip() or "home_screen_visible"
    failure_condition = str(oracle.get("failure_condition", "error_message_visible")).strip() or "error_message_visible"
    return MobileFlowOracle(
        success_condition=success_condition,
        failure_condition=failure_condition,
    )


def plan_screen(
    screen_type: str,
    *,
    username: str,
    password: str,
    manifest_path: Path | None = None,
) -> MobileFlowPlan:
    normalized_screen_type = str(screen_type).strip().upper()
    manifest = load_mobile_manifest(manifest_path)
    definition = _manifest_login_definition(manifest, normalized_screen_type)
    source = str(manifest_path or DEFAULT_MANIFEST_PATH) if definition else "fallback_rule_map"

    if normalized_screen_type == "AUTH_LOGIN":
        definition = definition or _fallback_login_definition()
        return MobileFlowPlan(
            screen_type=normalized_screen_type,
            steps=_normalize_steps(definition, username=username, password=password),
            oracle=_normalize_oracle(definition),
            source=source,
        )

    raise ValueError(f"Unsupported screen type: {normalized_screen_type}")
