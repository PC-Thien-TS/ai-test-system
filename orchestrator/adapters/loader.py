from __future__ import annotations

import importlib
import inspect
import os

from orchestrator.adapters.base.adapter_contract import ProjectAdapter
from orchestrator.adapters.rankmate.adapter import RankMateAdapter
from orchestrator.adapters.sample_ecommerce.adapter import SampleEcommerceAdapter


_ADAPTERS: dict[str, type[ProjectAdapter]] = {
    "rankmate": RankMateAdapter,
    "sample_ecommerce": SampleEcommerceAdapter,
}
_DYNAMIC_CACHE: dict[str, type[ProjectAdapter] | None] = {}


def _to_camel_case(value: str) -> str:
    return "".join(token.capitalize() for token in value.split("_") if token)


def _load_dynamic_adapter(adapter_id: str) -> type[ProjectAdapter] | None:
    if adapter_id in _DYNAMIC_CACHE:
        return _DYNAMIC_CACHE[adapter_id]

    try:
        module = importlib.import_module(f"orchestrator.adapters.{adapter_id}.adapter")
    except Exception:
        _DYNAMIC_CACHE[adapter_id] = None
        return None

    expected_name = f"{_to_camel_case(adapter_id)}Adapter"
    candidate = getattr(module, expected_name, None)
    if inspect.isclass(candidate) and issubclass(candidate, ProjectAdapter):
        _DYNAMIC_CACHE[adapter_id] = candidate
        return candidate

    for _, member in inspect.getmembers(module, inspect.isclass):
        if member is ProjectAdapter:
            continue
        if issubclass(member, ProjectAdapter):
            _DYNAMIC_CACHE[adapter_id] = member
            return member

    _DYNAMIC_CACHE[adapter_id] = None
    return None


def get_active_adapter_id() -> str:
    raw = (os.getenv("AI_TESTING_ADAPTER") or "rankmate").strip().lower()
    if raw in _ADAPTERS:
        return raw
    return raw if _load_dynamic_adapter(raw) is not None else "rankmate"


def get_active_adapter() -> ProjectAdapter:
    adapter_id = get_active_adapter_id()
    adapter_cls = _ADAPTERS.get(adapter_id) or _load_dynamic_adapter(adapter_id) or RankMateAdapter
    return adapter_cls()
