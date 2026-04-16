"""Execution queue builder for prioritized items."""

from __future__ import annotations

from typing import List

from orchestrator.advanced_qa.risk_models import ExecutionQueue, PrioritizedExecutionItem
from orchestrator.advanced_qa.risk_rules import BLAST_RADIUS_SEVERITY, EXECUTION_DEPTH_SEVERITY


class ExecutionQueueBuilder:
    """Build deterministic execution queues for orchestrator consumption."""

    ORDERING_POLICY = "priority_score_desc,blast_radius_desc,execution_depth_desc,stable_id_asc"

    def build(self, queue_id: str, items: List[PrioritizedExecutionItem]) -> ExecutionQueue:
        """Build ordered queue with deterministic tie-breaking."""

        ordered_items = sorted(
            items,
            key=lambda item: (
                -item.priority_score,
                -BLAST_RADIUS_SEVERITY[item.blast_radius.level],
                -EXECUTION_DEPTH_SEVERITY[item.execution_depth.depth],
                item.item_id,
            ),
        )
        return ExecutionQueue(
            queue_id=queue_id,
            items=ordered_items,
            ordering_policy=self.ORDERING_POLICY,
        )
