from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from orchestrator.decision.domain.models import DecisionStrategy


@dataclass(frozen=True)
class StrategyConfig:
    max_attempts: int
    use_backoff: bool = False
    timeout_multiplier: Optional[float] = None
    isolate: bool = False
    rerun_subset: bool = False
    quarantine: bool = False
    block_and_escalate: bool = False


STRATEGY_DEFAULTS: Dict[DecisionStrategy, StrategyConfig] = {
    DecisionStrategy.RETRY_3X: StrategyConfig(max_attempts=3),
    DecisionStrategy.RETRY_WITH_BACKOFF: StrategyConfig(max_attempts=3, use_backoff=True),
    DecisionStrategy.INCREASE_TIMEOUT: StrategyConfig(max_attempts=2, timeout_multiplier=1.5),
    DecisionStrategy.RERUN_SUBSET: StrategyConfig(max_attempts=1, rerun_subset=True),
    DecisionStrategy.ISOLATE_TEST: StrategyConfig(max_attempts=1, isolate=True),
    DecisionStrategy.QUARANTINE_TEST: StrategyConfig(max_attempts=0, quarantine=True),
    DecisionStrategy.BLOCK_AND_ESCALATE: StrategyConfig(max_attempts=0, block_and_escalate=True),
    DecisionStrategy.INVESTIGATE_BACKEND: StrategyConfig(max_attempts=0),
    DecisionStrategy.INVESTIGATE_INFRA: StrategyConfig(max_attempts=0),
    DecisionStrategy.INVESTIGATE_DATA: StrategyConfig(max_attempts=0),
}


def resolve_strategy_config(
    strategy: Optional[DecisionStrategy],
    *,
    fallback_max_attempts: int,
    timeout_multiplier: float,
) -> StrategyConfig:
    if strategy is None:
        return StrategyConfig(max_attempts=max(1, fallback_max_attempts))
    base = STRATEGY_DEFAULTS.get(strategy, StrategyConfig(max_attempts=max(1, fallback_max_attempts)))
    tm = base.timeout_multiplier if base.timeout_multiplier is not None else timeout_multiplier
    return StrategyConfig(
        max_attempts=max(0, min(base.max_attempts, max(1, fallback_max_attempts))),
        use_backoff=base.use_backoff,
        timeout_multiplier=tm,
        isolate=base.isolate,
        rerun_subset=base.rerun_subset,
        quarantine=base.quarantine,
        block_and_escalate=base.block_and_escalate,
    )

