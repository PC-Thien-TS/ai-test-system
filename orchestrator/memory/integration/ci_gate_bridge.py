from __future__ import annotations

from typing import Any

from orchestrator.storage.domain.repositories import MemoryRepository


def derive_ci_memory_signal(
    *,
    memory_repository: MemoryRepository,
    adapter_id: str,
    critical_severities: tuple[str, ...] = ("p0", "critical", "p1"),
    recurrence_block_threshold: int = 5,
) -> dict[str, Any]:
    rows = memory_repository.list_recent(adapter_id=adapter_id, limit=200)
    critical = [row for row in rows if (row.severity or "").lower() in critical_severities]
    recurring = [row for row in rows if row.occurrence_count >= recurrence_block_threshold]
    return {
        "adapter_id": adapter_id,
        "critical_memory_count": len(critical),
        "recurring_memory_count": len(recurring),
        "top_recurring": [
            {
                "memory_id": row.memory_id,
                "severity": row.severity,
                "occurrence_count": row.occurrence_count,
                "root_cause": row.root_cause,
                "confidence": row.confidence,
            }
            for row in sorted(rows, key=lambda x: x.occurrence_count, reverse=True)[:10]
        ],
        "suggest_block_release": bool(
            any((row.severity or "").lower() in {"p0", "critical"} for row in recurring)
            or len([row for row in recurring if (row.severity or "").lower() in {"p1"}]) >= 2
        ),
    }
