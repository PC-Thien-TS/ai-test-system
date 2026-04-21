from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "schemas" / "mobile_app_manifest.yaml"
DEFAULT_ORACLE_MAPPING_PATH = REPO_ROOT / "schemas" / "oracle_mapping_auth_login.yaml"


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
    screen_name: str
    screen_type: str
    steps: list[MobileActionStep]
    oracle: MobileFlowOracle
    source: str


def _load_yaml_document(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def load_mobile_manifest(path: Path | None = None) -> dict[str, Any]:
    return _load_yaml_document(path or DEFAULT_MANIFEST_PATH)


def load_oracle_mapping(path: Path | None = None) -> dict[str, Any]:
    return _load_yaml_document(path or DEFAULT_ORACLE_MAPPING_PATH)


def _fallback_login_definition() -> dict[str, Any]:
    return {
        "screen_name": "LoginScreen",
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


def _resolve_manifest_screen(manifest: dict[str, Any], screen_name: str) -> dict[str, Any] | None:
    screens = manifest.get("screens")
    if isinstance(screens, list):
        for screen in screens:
            if not isinstance(screen, dict):
                continue
            if str(screen.get("name", "")).strip() == screen_name:
                return screen
            if str(screen.get("screen_id", "")).strip() == screen_name:
                return screen
    return None


def _extract_feature_ids(manifest: dict[str, Any], screen_id: str) -> list[str]:
    features = manifest.get("features", [])
    if not isinstance(features, list):
        return []
    feature_ids: list[str] = []
    for feature in features:
        if not isinstance(feature, dict):
            continue
        screens = feature.get("screens", [])
        if isinstance(screens, list) and screen_id in screens:
            feature_id = str(feature.get("feature_id", "")).strip()
            if feature_id:
                feature_ids.append(feature_id)
    return feature_ids


def _extract_oracle_refs(manifest: dict[str, Any], screen_id: str) -> list[str]:
    obligations = manifest.get("test_obligations", [])
    if not isinstance(obligations, list):
        return []
    refs: list[str] = []
    for obligation in obligations:
        if not isinstance(obligation, dict):
            continue
        if str(obligation.get("screen_id", "")).strip() != screen_id:
            continue
        criteria = obligation.get("criteria", [])
        if not isinstance(criteria, list):
            continue
        for item in criteria:
            if not isinstance(item, dict):
                continue
            oracle_id = str(item.get("oracle_id", "")).strip()
            if oracle_id and oracle_id not in refs:
                refs.append(oracle_id)
    return refs


def _manifest_login_definition(manifest: dict[str, Any], screen_name: str) -> dict[str, Any] | None:
    screen = _resolve_manifest_screen(manifest, screen_name)
    if not isinstance(screen, dict):
        return None

    screen_id = str(screen.get("screen_id", "")).strip()
    elements = screen.get("elements", [])
    if not isinstance(elements, list):
        elements = []

    return {
        "screen_name": str(screen.get("name", screen_name)).strip() or screen_name,
        "screen_type": str(screen.get("type", "")).strip().upper(),
        "screen_id": screen_id,
        "elements": elements,
        "feature_ids": _extract_feature_ids(manifest, screen_id),
        "oracle_refs": _extract_oracle_refs(manifest, screen_id),
    }


def _normalize_steps(definition: dict[str, Any], *, username: str, password: str) -> list[MobileActionStep]:
    elements = definition.get("elements", [])
    if not isinstance(elements, list):
        elements = []

    role_to_step = {
        "INPUT_USERNAME": MobileActionStep(action="enter_username", value=username),
        "INPUT_PASSWORD": MobileActionStep(action="enter_password", value=password),
        "ACTION_SUBMIT": MobileActionStep(action="tap_login"),
    }

    steps: list[MobileActionStep] = []
    for element in elements:
        if not isinstance(element, dict):
            continue
        role = str(element.get("role", "")).strip().upper()
        step = role_to_step.get(role)
        if step:
            steps.append(step)

    if steps:
        return steps

    planned_steps = definition.get("steps", [])
    if isinstance(planned_steps, list):
        fallback_steps: list[MobileActionStep] = []
        for step in planned_steps:
            if not isinstance(step, dict):
                continue
            action = str(step.get("action", "")).strip()
            if not action:
                continue
            if action == "enter_username":
                fallback_steps.append(MobileActionStep(action=action, value=username))
                continue
            if action == "enter_password":
                fallback_steps.append(MobileActionStep(action=action, value=password))
                continue
            fallback_steps.append(MobileActionStep(action=action, value=str(step.get("value", ""))))
        if fallback_steps:
            return fallback_steps

    return [
        role_to_step["INPUT_USERNAME"],
        role_to_step["INPUT_PASSWORD"],
        role_to_step["ACTION_SUBMIT"],
    ]


def _condition_to_runtime_oracle(condition: dict[str, Any], *, default: str) -> str:
    expected_signals = condition.get("expected_signals", [])
    if isinstance(expected_signals, list):
        normalized = {str(signal).strip().upper() for signal in expected_signals}
        if "NAVIGATION_HOME" in normalized:
            return "home_screen_visible"
        if "SIGNAL_ERROR" in normalized:
            return "error_message_visible"

    expected_ui_state = condition.get("expected_ui_state", {})
    if isinstance(expected_ui_state, dict):
        error_message_state = str(expected_ui_state.get("error_message", "")).strip().lower()
        if error_message_state in {"present", "network_error", "network_unavailable"}:
            return "error_message_visible"
        if error_message_state == "absent":
            return "home_screen_visible"

    return default


def _normalize_oracle(definition: dict[str, Any], oracle_mapping: dict[str, Any]) -> MobileFlowOracle:
    success_condition = "home_screen_visible"
    failure_condition = "error_message_visible"

    success_conditions = oracle_mapping.get("success_conditions", [])
    if isinstance(success_conditions, list):
        for condition in success_conditions:
            if not isinstance(condition, dict):
                continue
            success_condition = _condition_to_runtime_oracle(condition, default=success_condition)
            if success_condition == "home_screen_visible":
                break

    failure_conditions = oracle_mapping.get("failure_conditions", [])
    if isinstance(failure_conditions, list):
        for condition in failure_conditions:
            if not isinstance(condition, dict):
                continue
            failure_condition = _condition_to_runtime_oracle(condition, default=failure_condition)
            if failure_condition == "error_message_visible":
                break

    oracle = definition.get("oracle", {})
    if not isinstance(oracle, dict):
        oracle = {}

    success_condition = str(oracle.get("success_condition", success_condition)).strip() or success_condition
    failure_condition = str(oracle.get("failure_condition", failure_condition)).strip() or failure_condition
    return MobileFlowOracle(
        success_condition=success_condition,
        failure_condition=failure_condition,
    )


def plan_screen(
    screen_name: str,
    *,
    username: str,
    password: str,
    manifest_path: Path | None = None,
    oracle_mapping_path: Path | None = None,
) -> MobileFlowPlan:
    manifest = load_mobile_manifest(manifest_path)
    definition = _manifest_login_definition(manifest, screen_name)
    if definition:
        resolved_screen_type = str(definition.get("screen_type", "")).strip().upper()
        if resolved_screen_type == "AUTH_LOGIN":
            oracle_mapping = load_oracle_mapping(oracle_mapping_path)
            source = str(manifest_path or DEFAULT_MANIFEST_PATH)
            return MobileFlowPlan(
                screen_name=str(definition.get("screen_name", screen_name)).strip() or screen_name,
                screen_type=resolved_screen_type,
                steps=_normalize_steps(definition, username=username, password=password),
                oracle=_normalize_oracle(definition, oracle_mapping),
                source=source,
            )

    fallback = _fallback_login_definition()
    return MobileFlowPlan(
        screen_name=str(fallback.get("screen_name", "LoginScreen")),
        screen_type=str(fallback.get("screen_type", "AUTH_LOGIN")),
        steps=_normalize_steps(fallback, username=username, password=password),
        oracle=_normalize_oracle(fallback, {}),
        source="fallback_rule_map",
    )
