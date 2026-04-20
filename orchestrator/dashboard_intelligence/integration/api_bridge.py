from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any


def to_response(payload: Any) -> Any:
    if isinstance(payload, Enum):
        return payload.value
    if is_dataclass(payload):
        return {k: to_response(v) for k, v in asdict(payload).items()}
    if isinstance(payload, dict):
        return {str(k): to_response(v) for k, v in payload.items()}
    if isinstance(payload, (list, tuple, set)):
        return [to_response(v) for v in payload]
    return payload

