from __future__ import annotations

from typing import Any


_ACTION_ALIASES = {
    "ACTION_SUBMIT": "submit_login",
    "NAVIGATION_BACK": "go_back",
    "NAVIGATION_DETAIL": "open_first_item",
    "submit_login": "submit_login",
    "open_first_item": "open_first_item",
    "go_back": "go_back",
}

_RISK_LEVELS = ("high", "medium", "low")


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _clean_str(value: Any) -> str:
    return str(value).strip()


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_ratio(value: Any, default: float) -> float:
    try:
        ratio = float(value)
    except (TypeError, ValueError):
        return default
    return ratio / 100.0 if ratio > 1 else ratio


def _resolve_threshold(value: Any, config: dict[str, Any], default: Any, *, ratio: bool = False) -> Any:
    resolved = config.get(value, default) if isinstance(value, str) else value
    if ratio:
        return _safe_ratio(resolved, default)
    if isinstance(default, int):
        return _safe_int(resolved, default)
    return resolved


def _mapped_action_name(action_name: Any) -> tuple[str, str | None]:
    source_action = _clean_str(action_name)
    return source_action, _ACTION_ALIASES.get(source_action)


def _collect_risk_policy(policy: dict[str, Any]) -> dict[str, list[str]]:
    risk_assessment = _as_dict(policy.get("risk_assessment"))
    normalized: dict[str, list[str]] = {}
    for level in _RISK_LEVELS:
        key = f"{level}_risk_actions"
        normalized[key] = [_clean_str(item) for item in _as_list(risk_assessment.get(key)) if _clean_str(item)]
    return normalized


def _infer_risk(
    *,
    source_action: str,
    explicit_risk: Any,
    screen_risky_actions: set[str],
    risk_policy: dict[str, list[str]],
) -> str:
    risk = _clean_str(explicit_risk).lower()
    if risk:
        return risk
    if source_action in screen_risky_actions or source_action in risk_policy.get("high_risk_actions", []):
        return "high"
    if source_action in risk_policy.get("medium_risk_actions", []):
        return "medium"
    if source_action in risk_policy.get("low_risk_actions", []):
        return "low"
    return "normal"


def _normalize_flat_action_ranking(
    raw_ranking: dict[str, Any],
    *,
    screen_risky_actions: dict[str, set[str]],
    risk_policy: dict[str, list[str]],
) -> dict[str, list[dict[str, Any]]]:
    normalized: dict[str, list[dict[str, Any]]] = {}
    for screen_type, items in raw_ranking.items():
        screen_key = _clean_str(screen_type)
        if not screen_key:
            continue
        ranked_actions: list[dict[str, Any]] = []
        for item in _as_list(items):
            payload = _as_dict(item)
            source_action, mapped_action = _mapped_action_name(payload.get("action"))
            if not source_action:
                continue
            ranked_actions.append(
                {
                    "action": mapped_action or source_action,
                    "source_action": source_action,
                    "supported": mapped_action is not None or source_action in _ACTION_ALIASES.values(),
                    "rank": _safe_int(payload.get("rank"), 0),
                    "risk": _infer_risk(
                        source_action=source_action,
                        explicit_risk=payload.get("risk"),
                        screen_risky_actions=screen_risky_actions.get(screen_key, set()),
                        risk_policy=risk_policy,
                    ),
                    "recovery_action": bool(payload.get("recovery_action")),
                }
            )
        normalized[screen_key] = ranked_actions
    return normalized


def _normalize_nested_action_ranking(
    raw_ranking: dict[str, Any],
    *,
    screen_risky_actions: dict[str, set[str]],
    risk_policy: dict[str, list[str]],
) -> dict[str, list[dict[str, Any]]]:
    normalized: dict[str, list[dict[str, Any]]] = {}
    group_base = {"primary": 3000, "secondary": 2000, "recovery": 1000}
    for screen_type, groups in raw_ranking.items():
        screen_key = _clean_str(screen_type)
        group_payload = _as_dict(groups)
        if not screen_key or not group_payload:
            continue
        ranked_actions: list[dict[str, Any]] = []
        for group_name, base_score in group_base.items():
            for index, item in enumerate(_as_list(group_payload.get(group_name)), start=1):
                payload = _as_dict(item)
                source_action, mapped_action = _mapped_action_name(payload.get("action"))
                if not source_action:
                    continue
                raw_rank = _safe_int(payload.get("rank"), index)
                ranked_actions.append(
                    {
                        "action": mapped_action or source_action,
                        "source_action": source_action,
                        "supported": mapped_action is not None,
                        "rank": base_score - raw_rank,
                        "risk": _infer_risk(
                            source_action=source_action,
                            explicit_risk=payload.get("risk"),
                            screen_risky_actions=screen_risky_actions.get(screen_key, set()),
                            risk_policy=risk_policy,
                        ),
                        "recovery_action": group_name == "recovery",
                        "policy_group": group_name,
                    }
                )
        normalized[screen_key] = ranked_actions
    return normalized


def _normalize_screen_priorities(
    policy: dict[str, Any],
) -> tuple[dict[str, int], dict[str, int], dict[str, set[str]], bool]:
    raw_priorities = policy.get("screen_priorities", {})
    screen_priorities: dict[str, int] = {}
    per_screen_step_limits: dict[str, int] = {}
    screen_risky_actions: dict[str, set[str]] = {}

    if isinstance(raw_priorities, dict):
        for screen_type, priority in raw_priorities.items():
            screen_key = _clean_str(screen_type)
            if not screen_key:
                continue
            screen_priorities[screen_key] = _safe_int(priority, 1)
            screen_risky_actions[screen_key] = set()
        return screen_priorities, per_screen_step_limits, screen_risky_actions, False

    if isinstance(raw_priorities, list):
        for item in raw_priorities:
            payload = _as_dict(item)
            screen_key = _clean_str(payload.get("screen_type"))
            if not screen_key:
                continue
            screen_priorities[screen_key] = _safe_int(payload.get("priority"), 1)
            if "max_steps" in payload:
                per_screen_step_limits[screen_key] = max(1, _safe_int(payload.get("max_steps"), 1))
            screen_risky_actions[screen_key] = {
                _clean_str(action)
                for action in _as_list(payload.get("risky_actions"))
                if _clean_str(action)
            }
        return screen_priorities, per_screen_step_limits, screen_risky_actions, True

    return screen_priorities, per_screen_step_limits, screen_risky_actions, False


def _normalize_coverage_strategy(
    policy: dict[str, Any],
    *,
    screen_priorities: dict[str, int],
    action_ranking: dict[str, list[dict[str, Any]]],
    nested_schema: bool,
) -> dict[str, Any]:
    coverage_strategy = _as_dict(policy.get("coverage_strategy"))
    exploration_order = [_clean_str(item) for item in _as_list(policy.get("exploration_order")) if _clean_str(item)]
    target_screen_types: list[str] = []
    target_actions: list[str] = []
    coverage_threshold = 1.0
    weight_by_screen_priority = False
    per_screen: dict[str, dict[str, Any]] = {}

    if not nested_schema:
        target_screen_types = [
            _clean_str(item) for item in _as_list(coverage_strategy.get("target_screen_types")) if _clean_str(item)
        ]
        target_actions = [_clean_str(item) for item in _as_list(coverage_strategy.get("target_actions")) if _clean_str(item)]
        coverage_threshold = _safe_ratio(coverage_strategy.get("coverage_threshold"), 1.0)
        weight_by_screen_priority = bool(coverage_strategy.get("weight_by_screen_priority"))
        return {
            "target_screen_types": target_screen_types,
            "target_actions": target_actions,
            "coverage_threshold": coverage_threshold,
            "weight_by_screen_priority": weight_by_screen_priority,
            "per_screen": per_screen,
        }

    for screen_type, screen_data in coverage_strategy.items():
        screen_key = _clean_str(screen_type)
        payload = _as_dict(screen_data)
        if not screen_key or not payload:
            continue
        per_screen[screen_key] = {
            "required_minimum_coverage": _safe_ratio(payload.get("required_minimum_coverage"), 0.0),
            "optional_coverage": _safe_ratio(payload.get("optional_coverage"), 0.0),
            "coverage_score_weight": _safe_ratio(payload.get("coverage_score_weight"), 0.0),
            "coverage_elements": [_clean_str(item) for item in _as_list(payload.get("coverage_elements")) if _clean_str(item)],
        }

    if exploration_order:
        target_screen_types = [screen_type for screen_type in exploration_order if screen_type in screen_priorities or screen_type in per_screen]
    if not target_screen_types:
        target_screen_types = list(per_screen) or list(screen_priorities)

    for screen_type in target_screen_types:
        for item in action_ranking.get(screen_type, []):
            action_name = _clean_str(item.get("action"))
            if not bool(item.get("supported")) or not action_name or action_name in target_actions:
                continue
            target_actions.append(action_name)

    stop_conditions = _as_dict(policy.get("stop_conditions"))
    config = _as_dict(policy.get("exploration_config"))
    for item in _as_list(stop_conditions.get("global")):
        payload = _as_dict(item)
        if _clean_str(payload.get("condition")) != "coverage_threshold_reached":
            continue
        coverage_threshold = _resolve_threshold(payload.get("threshold"), config, 0.9, ratio=True)
        break
    else:
        thresholds = _as_dict(_as_dict(policy.get("coverage_calculation")).get("thresholds"))
        coverage_threshold = _safe_ratio(thresholds.get("satisfactory"), 0.9)

    return {
        "target_screen_types": target_screen_types,
        "target_actions": target_actions,
        "coverage_threshold": coverage_threshold,
        "weight_by_screen_priority": True,
        "per_screen": per_screen,
    }


def _normalize_stop_conditions(
    policy: dict[str, Any],
    *,
    nested_schema: bool,
    per_screen_step_limits: dict[str, int],
) -> dict[str, Any]:
    stop_conditions = _as_dict(policy.get("stop_conditions"))
    if not nested_schema:
        cycle_detection = bool(stop_conditions.get("cycle_detection", True))
        return {
            "max_steps": max(1, _safe_int(stop_conditions.get("max_steps"), 8)),
            "max_cycles": 1 if cycle_detection else 0,
            "cycle_detection": cycle_detection,
            "stop_on_no_valid_action": bool(stop_conditions.get("stop_on_no_valid_action", True)),
            "stop_on_coverage_threshold": bool(stop_conditions.get("stop_on_coverage_threshold", False)),
            "repeated_failure_threshold": max(1, _safe_int(stop_conditions.get("repeated_failure_threshold"), 1)),
            "max_steps_per_screen": 0,
            "per_screen_step_limits": per_screen_step_limits,
        }

    config = _as_dict(policy.get("exploration_config"))
    normalized = {
        "max_steps": max(1, _safe_int(config.get("max_total_steps"), 8)),
        "max_cycles": max(1, _safe_int(config.get("max_cycles"), 1)),
        "cycle_detection": True,
        "stop_on_no_valid_action": True,
        "stop_on_coverage_threshold": False,
        "repeated_failure_threshold": 1,
        "max_steps_per_screen": max(1, _safe_int(config.get("max_steps_per_screen"), 1)),
        "per_screen_step_limits": dict(per_screen_step_limits),
    }

    for item in _as_list(stop_conditions.get("global")):
        payload = _as_dict(item)
        condition = _clean_str(payload.get("condition"))
        if condition == "max_steps_reached":
            normalized["max_steps"] = max(1, _resolve_threshold(payload.get("threshold"), config, normalized["max_steps"]))
        elif condition == "max_cycles_detected":
            normalized["max_cycles"] = max(1, _resolve_threshold(payload.get("threshold"), config, normalized["max_cycles"]))
        elif condition == "coverage_threshold_reached":
            normalized["stop_on_coverage_threshold"] = True
        elif condition == "repeated_failure_count":
            normalized["repeated_failure_threshold"] = max(
                1, _resolve_threshold(payload.get("threshold"), config, normalized["repeated_failure_threshold"])
            )
        elif condition == "no_valid_action_available":
            normalized["stop_on_no_valid_action"] = True

    for item in _as_list(stop_conditions.get("per_screen")):
        payload = _as_dict(item)
        condition = _clean_str(payload.get("condition"))
        if condition != "max_steps_per_screen_reached":
            continue
        normalized["max_steps_per_screen"] = max(
            1, _resolve_threshold(payload.get("threshold"), config, normalized["max_steps_per_screen"])
        )
        break

    return normalized


def _normalize_fallback_behavior(policy: dict[str, Any], *, nested_schema: bool) -> dict[str, Any]:
    fallback_behavior = _as_dict(policy.get("fallback_behavior"))
    if not nested_schema:
        return {
            "malformed_policy": _clean_str(fallback_behavior.get("malformed_policy")) or "deterministic",
            "no_valid_action": _clean_str(fallback_behavior.get("no_valid_action")).lower() or "stop",
            "risky_action": _clean_str(fallback_behavior.get("risky_action")).lower() or "skip",
        }

    no_valid_action = "stop"
    for item in _as_list(fallback_behavior.get("on_exhausted_actions")):
        action_name = _clean_str(_as_dict(item).get("action"))
        if action_name == "fallback_deterministic":
            no_valid_action = "deterministic"
            break

    return {
        "malformed_policy": "deterministic",
        "no_valid_action": no_valid_action,
        "risky_action": "skip",
    }


def normalize_exploration_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(policy, dict):
        policy = {}
    if bool(policy.get("__normalized_policy__")):
        return policy

    screen_priorities, per_screen_step_limits, screen_risky_actions, nested_schema = _normalize_screen_priorities(policy)
    risk_policy = _collect_risk_policy(policy)

    raw_ranking = _as_dict(policy.get("action_ranking"))
    if nested_schema:
        action_ranking = _normalize_nested_action_ranking(
            raw_ranking,
            screen_risky_actions=screen_risky_actions,
            risk_policy=risk_policy,
        )
    else:
        action_ranking = _normalize_flat_action_ranking(
            raw_ranking,
            screen_risky_actions=screen_risky_actions,
            risk_policy=risk_policy,
        )

    coverage_strategy = _normalize_coverage_strategy(
        policy,
        screen_priorities=screen_priorities,
        action_ranking=action_ranking,
        nested_schema=nested_schema,
    )
    stop_conditions = _normalize_stop_conditions(
        policy,
        nested_schema=nested_schema,
        per_screen_step_limits=per_screen_step_limits,
    )
    fallback_behavior = _normalize_fallback_behavior(policy, nested_schema=nested_schema)

    return {
        "__normalized_policy__": True,
        "policy_shape": "nested" if nested_schema else "flat",
        "screen_priorities": screen_priorities,
        "action_ranking": action_ranking,
        "coverage_strategy": coverage_strategy,
        "stop_conditions": stop_conditions,
        "fallback_behavior": fallback_behavior,
        "risk_policy": risk_policy,
    }
