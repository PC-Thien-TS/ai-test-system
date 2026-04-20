from __future__ import annotations

from typing import Any

from ..application.engine import MemoryOutcomeRecorder
from ..domain.models import ActionContext, ActionOutcomeRecord


class FailureMemoryRecorderBridge(MemoryOutcomeRecorder):
    """
    Adapter bridge to Failure Memory Engine.
    Requires `failure_memory_engine.record_action_outcome(...)`.
    """

    def __init__(self, failure_memory_engine: Any) -> None:
        self.failure_memory_engine = failure_memory_engine

    def record_action_outcome(self, context: ActionContext, outcome: ActionOutcomeRecord) -> None:
        self.failure_memory_engine.record_action_outcome(context, outcome)

