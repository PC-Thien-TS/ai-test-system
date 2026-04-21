"""Idempotency key helpers for Wave 1 API testing."""

from __future__ import annotations

from datetime import datetime, timezone
import uuid


def generate_idempotency_key(case_id: str) -> str:
    """Generate stable-debuggable idempotency key."""
    stamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d%H%M%S")
    suffix = uuid.uuid4().hex[:10]
    clean_case = case_id.replace(" ", "-").lower()
    return f"wave1-{clean_case}-{stamp}-{suffix}"


class IdempotencyRegistry:
    """Small in-memory key registry to support replay checks in one test run."""

    def __init__(self) -> None:
        self._keys: dict[str, str] = {}

    def get_or_create(self, logical_name: str, case_id: str) -> str:
        if logical_name not in self._keys:
            self._keys[logical_name] = generate_idempotency_key(case_id)
        return self._keys[logical_name]
