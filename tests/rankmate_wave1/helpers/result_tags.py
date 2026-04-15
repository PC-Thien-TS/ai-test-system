"""Case metadata tagging helpers for Wave 1 tests."""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Callable, Sequence


@dataclass(frozen=True)
class CaseMetadata:
    case_id: str
    assertion_ids: tuple[str, ...]
    domain: str
    priority: str
    risk: str


def wave1_case(
    *,
    case_id: str,
    assertion_ids: Sequence[str],
    domain: str,
    priority: str,
    risk: str,
) -> Callable:
    """Attach machine-readable metadata to test callables."""

    metadata = CaseMetadata(
        case_id=case_id,
        assertion_ids=tuple(assertion_ids),
        domain=domain,
        priority=priority,
        risk=risk,
    )

    def decorator(func: Callable) -> Callable:
        setattr(func, "_wave1_case_metadata", metadata)
        return func

    return decorator


def attach_case_metadata_to_node(request) -> None:
    """Expose case metadata in pytest node user_properties for future ingestion."""

    metadata: CaseMetadata | None = getattr(request.function, "_wave1_case_metadata", None)
    if metadata is None:
        return

    payload = asdict(metadata)
    for key, value in payload.items():
        request.node.user_properties.append((key, value))
