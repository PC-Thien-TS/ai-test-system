from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from mobile_appium.classifier import (
    SCREEN_TYPE_AUTH_LOGIN,
    SCREEN_TYPE_CONTENT_DETAIL,
    SCREEN_TYPE_CONTENT_LIST,
    classify_screen,
    resolve_manifest_screen,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MANIFEST_PATH = REPO_ROOT / "schemas" / "mobile_app_manifest.yaml"
DEFAULT_ORACLE_MAPPING_PATHS = {
    SCREEN_TYPE_AUTH_LOGIN: REPO_ROOT / "schemas" / "oracle_mapping_auth_login.yaml",
    SCREEN_TYPE_CONTENT_LIST: REPO_ROOT / "schemas" / "oracle_mapping_content_list.yaml",
    SCREEN_TYPE_CONTENT_DETAIL: REPO_ROOT / "schemas" / "oracle_mapping_content_detail.yaml",
}
DEFAULT_OBLIGATION_PATHS = {
    SCREEN_TYPE_CONTENT_LIST: REPO_ROOT / "taxonomy" / "test_obligations_content_list.yaml",
    SCREEN_TYPE_CONTENT_DETAIL: REPO_ROOT / "taxonomy" / "test_obligations_content_detail.yaml",
}


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


def load_oracle_mapping(screen_type: str, path: Path | None = None) -> dict[str, Any]:
    default_path = DEFAULT_ORACLE_MAPPING_PATHS.get(screen_type)
    return _load_yaml_document(path or default_path) if default_path or path else {}


def load_test_obligations(screen_type: str, path: Path | None = None) -> dict[str, Any]:
    default_path = DEFAULT_OBLIGATION_PATHS.get(screen_type)
    return _load_yaml_document(path or default_path) if default_path or path else {}


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


def _fallback_unknown_definition(screen_name: str) -> dict[str, Any]:
    return {
        "screen_name": screen_name,
        "screen_type": "UNKNOWN",
        "steps": [],
        "oracle": {
            "success_condition": "screen_loaded",
            "failure_condition": "error_message_visible",
        },
    }


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
    screen = resolve_manifest_screen(manifest, screen_name)
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


def _normalize_auth_login_steps(definition: dict[str, Any], *, username: str, password: str) -> list[MobileActionStep]:
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


def _pick_primary_test_case(obligations: dict[str, Any], preferred_name: str) -> dict[str, Any]:
    test_cases = obligations.get("test_cases", [])
    if not isinstance(test_cases, list):
        return {}

    required_names = obligations.get("required_obligations", [])
    if isinstance(required_names, list) and preferred_name in required_names:
        for test_case in test_cases:
            if isinstance(test_case, dict) and str(test_case.get("name", "")).strip() == preferred_name:
                return test_case

    for test_case in test_cases:
        if isinstance(test_case, dict) and str(test_case.get("name", "")).strip() == preferred_name:
            return test_case

    for test_case in test_cases:
        if isinstance(test_case, dict) and bool(test_case.get("automated")):
            return test_case
    return {}


def _normalize_content_list_steps(definition: dict[str, Any], obligations: dict[str, Any]) -> list[MobileActionStep]:
    elements = definition.get("elements", [])
    if not isinstance(elements, list):
        elements = []

    roles = {str(element.get("role", "")).strip().upper() for element in elements if isinstance(element, dict)}
    test_case = _pick_primary_test_case(obligations, preferred_name="happy_path_load")
    expected_signals = test_case.get("expected_signals", []) if isinstance(test_case, dict) else []
    expected_ui = test_case.get("expected_ui", {}) if isinstance(test_case, dict) else {}
    if not isinstance(expected_signals, list):
        expected_signals = []
    if not isinstance(expected_ui, dict):
        expected_ui = {}

    steps: list[MobileActionStep] = []
    if "SIGNAL_LOADING" in {str(signal).strip().upper() for signal in expected_signals} or roles.intersection(
        {"SIGNAL_LOADING", "SIGNAL_REFRESH"}
    ):
        steps.append(MobileActionStep(action="validate_list_loaded"))

    if (
        str(expected_ui.get("list_content", "")).strip().lower() in {"present", "filtered", "refreshed"}
        or str(expected_ui.get("item_count", "")).strip()
        or roles.intersection({"ITEM_CARD", "ITEM_TITLE", "CONTENT_LIST", "LIST_CONTAINER", "LIST_CONTENT"})
    ):
        steps.append(MobileActionStep(action="validate_list_items_visible"))

    return steps or [MobileActionStep(action="validate_list_loaded")]


def _normalize_content_detail_steps(definition: dict[str, Any], obligations: dict[str, Any]) -> list[MobileActionStep]:
    elements = definition.get("elements", [])
    if not isinstance(elements, list):
        elements = []

    roles = {str(element.get("role", "")).strip().upper() for element in elements if isinstance(element, dict)}
    test_case = _pick_primary_test_case(obligations, preferred_name="happy_path_load")
    expected_signals = test_case.get("expected_signals", []) if isinstance(test_case, dict) else []
    expected_ui = test_case.get("expected_ui", {}) if isinstance(test_case, dict) else {}
    if not isinstance(expected_signals, list):
        expected_signals = []
    if not isinstance(expected_ui, dict):
        expected_ui = {}

    steps: list[MobileActionStep] = []
    if "SIGNAL_LOADING" in {str(signal).strip().upper() for signal in expected_signals} or roles.intersection(
        {"SIGNAL_LOADING"}
    ):
        steps.append(MobileActionStep(action="validate_detail_loaded"))

    detail_ui_keys = {"content_image", "content_title", "content_price", "content_description"}
    if any(str(expected_ui.get(key, "")).strip().lower() == "present" for key in detail_ui_keys) or roles.intersection(
        {"CONTENT_TITLE", "CONTENT_BODY", "DETAIL_CONTAINER", "CONTENT_IMAGE", "CONTENT_DESCRIPTION", "CONTENT_PRICE"}
    ):
        steps.append(MobileActionStep(action="validate_detail_content_visible"))

    return steps or [MobileActionStep(action="validate_detail_loaded")]


def _normalize_steps(
    definition: dict[str, Any],
    *,
    username: str,
    password: str,
    screen_type: str,
    obligations: dict[str, Any] | None = None,
) -> list[MobileActionStep]:
    if screen_type == SCREEN_TYPE_AUTH_LOGIN:
        return _normalize_auth_login_steps(definition, username=username, password=password)
    if screen_type == SCREEN_TYPE_CONTENT_LIST:
        return _normalize_content_list_steps(definition, obligations or {})
    if screen_type == SCREEN_TYPE_CONTENT_DETAIL:
        return _normalize_content_detail_steps(definition, obligations or {})
    return []


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
        list_content_state = str(expected_ui_state.get("list_content", "")).strip().lower()
        if list_content_state in {"present", "filtered", "refreshed"}:
            return "list_items_visible"

        detail_ui_keys = {"content_image", "content_title", "content_price", "content_description"}
        if any(str(expected_ui_state.get(key, "")).strip().lower() == "present" for key in detail_ui_keys):
            return "detail_content_visible"

        error_message_state = str(expected_ui_state.get("error_message", "")).strip().lower()
        if error_message_state in {"present", "network_error", "network_unavailable"}:
            return "error_message_visible"
        if error_message_state == "absent":
            return "home_screen_visible"

    return default


def _normalize_oracle(definition: dict[str, Any], oracle_mapping: dict[str, Any]) -> MobileFlowOracle:
    success_condition = str(definition.get("default_success_condition", "home_screen_visible")).strip() or "home_screen_visible"
    failure_condition = (
        str(definition.get("default_failure_condition", "error_message_visible")).strip() or "error_message_visible"
    )

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


def _default_oracle_for_screen_type(screen_type: str) -> MobileFlowOracle:
    if screen_type == SCREEN_TYPE_CONTENT_LIST:
        return MobileFlowOracle(
            success_condition="list_items_visible",
            failure_condition="error_message_visible",
        )
    if screen_type == SCREEN_TYPE_CONTENT_DETAIL:
        return MobileFlowOracle(
            success_condition="detail_content_visible",
            failure_condition="error_message_visible",
        )
    if screen_type == SCREEN_TYPE_AUTH_LOGIN:
        return MobileFlowOracle(
            success_condition="home_screen_visible",
            failure_condition="error_message_visible",
        )
    return MobileFlowOracle(
        success_condition="screen_loaded",
        failure_condition="error_message_visible",
    )


def _definition_with_defaults(definition: dict[str, Any], screen_type: str) -> dict[str, Any]:
    enriched = dict(definition)
    default_oracle = _default_oracle_for_screen_type(screen_type)
    enriched["default_success_condition"] = default_oracle.success_condition
    enriched["default_failure_condition"] = default_oracle.failure_condition
    return enriched


def plan_screen(
    screen_name: str,
    *,
    username: str,
    password: str,
    manifest_path: Path | None = None,
    oracle_mapping_path: Path | None = None,
) -> MobileFlowPlan:
    manifest = load_mobile_manifest(manifest_path)
    classification = classify_screen(
        screen_name,
        manifest=manifest,
        manifest_path=manifest_path,
    )
    if classification.screen_type in {
        SCREEN_TYPE_AUTH_LOGIN,
        SCREEN_TYPE_CONTENT_LIST,
        SCREEN_TYPE_CONTENT_DETAIL,
    }:
        definition = _manifest_login_definition(manifest, screen_name)
        if definition:
            definition = _definition_with_defaults(definition, classification.screen_type)
            obligations = load_test_obligations(classification.screen_type)
            oracle_mapping = load_oracle_mapping(classification.screen_type, oracle_mapping_path)
            oracle = _normalize_oracle(definition, oracle_mapping)
            source = str(manifest_path or DEFAULT_MANIFEST_PATH)
            return MobileFlowPlan(
                screen_name=str(definition.get("screen_name", classification.screen_name)).strip()
                or classification.screen_name,
                screen_type=classification.screen_type,
                steps=_normalize_steps(
                    definition,
                    username=username,
                    password=password,
                    screen_type=classification.screen_type,
                    obligations=obligations,
                ),
                oracle=oracle,
                source=source,
            )

    fallback = _fallback_login_definition() if str(screen_name).strip() == "LoginScreen" else _fallback_unknown_definition(screen_name)
    fallback_screen_type = str(fallback.get("screen_type", "UNKNOWN")).strip().upper()
    fallback = _definition_with_defaults(fallback, fallback_screen_type)
    return MobileFlowPlan(
        screen_name=str(fallback.get("screen_name", screen_name)),
        screen_type=fallback_screen_type,
        steps=_normalize_steps(
            fallback,
            username=username,
            password=password,
            screen_type=fallback_screen_type,
        ),
        oracle=_normalize_oracle(fallback, {})
        if fallback_screen_type == SCREEN_TYPE_AUTH_LOGIN
        else _default_oracle_for_screen_type(fallback_screen_type),
        source="fallback_rule_map",
    )
