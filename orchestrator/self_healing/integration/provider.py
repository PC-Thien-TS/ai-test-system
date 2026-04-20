from __future__ import annotations

from typing import Optional

from ..application.engine import MemoryOutcomeRecorder, SelfHealingEngine
from ..domain.models import SelfHealingConfig


def build_self_healing_engine(
    *,
    config: Optional[SelfHealingConfig] = None,
    memory_recorder: Optional[MemoryOutcomeRecorder] = None,
) -> SelfHealingEngine:
    return SelfHealingEngine(config=config, memory_recorder=memory_recorder)

