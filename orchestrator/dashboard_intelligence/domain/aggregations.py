from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Tuple

from .models import (
    CandidateDashboardSummary,
    DecisionDashboardSummary,
    FailureMemoryDashboardSummary,
    GovernanceDashboardSummary,
    LeaderboardEntry,
    ReleaseReadinessSummary,
    SelfHealingDashboardSummary,
    StrategyEffectiveness,
)


def _safe_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def aggregate_top_recurring_failures(
    memory_records: Iterable[Dict[str, object]],
    *,
    limit: int = 10,
) -> List[LeaderboardEntry]:
    grouped: Dict[str, Dict[str, object]] = {}
    for rec in memory_records:
        key = str(rec.get("memory_id") or rec.get("signature_hash") or rec.get("root_cause") or "unknown")
        occ = _safe_int(rec.get("occurrence_count", 1), default=1)
        if key not in grouped:
            grouped[key] = {
                "count": 0,
                "label": str(rec.get("root_cause") or rec.get("signature_hash") or key),
                "severity": str(rec.get("severity", "")),
                "confidence": _safe_float(rec.get("confidence", 0.0)),
                "owner": str(rec.get("recommended_owner", "")),
            }
        grouped[key]["count"] = _safe_int(grouped[key]["count"]) + occ
        grouped[key]["confidence"] = max(_safe_float(grouped[key]["confidence"]), _safe_float(rec.get("confidence")))

    items = sorted(grouped.items(), key=lambda kv: _safe_int(kv[1]["count"]), reverse=True)[:limit]
    return [
        LeaderboardEntry(
            key=k,
            label=str(v["label"]),
            count=_safe_int(v["count"]),
            severity=str(v["severity"]),
            confidence=_safe_float(v["confidence"]),
            owner=str(v["owner"]),
        )
        for k, v in items
    ]


def aggregate_release_readiness(
    decision_records: Iterable[Dict[str, object]],
    incident_records: Iterable[Dict[str, object]],
    self_healing_records: Iterable[Dict[str, object]],
    release_records: Iterable[Dict[str, object]],
) -> ReleaseReadinessSummary:
    block_count = 0
    escalation_count = 0
    for rec in decision_records:
        p = str(rec.get("primary_decision", "")).upper()
        if p == "BLOCK_RELEASE":
            block_count += 1
        if p in {"ESCALATE", "BLOCK_RELEASE"}:
            escalation_count += 1

    active_incidents = sum(1 for i in incident_records if str(i.get("generation_status", "")).lower() != "resolved")
    unresolved_actions = sum(1 for s in self_healing_records if bool(s.get("executed")) and not bool(s.get("success")))

    penalty_total = 0
    for rel in release_records:
        penalty_total += _safe_int(rel.get("release_penalty", rel.get("release_penalty_recommendation", 0)))

    rationale: List[str] = []
    if block_count > 0:
        rationale.append("Active block-release decisions detected.")
    if active_incidents > 0:
        rationale.append("Unresolved incident candidates are active.")
    if unresolved_actions > 0:
        rationale.append("Self-healing has unresolved failed actions.")
    if not rationale:
        rationale.append("No active hard blockers found in current filtered scope.")

    risk_level = "low"
    if block_count > 0 or active_incidents > 0:
        risk_level = "high"
    elif escalation_count > 0 or unresolved_actions > 0:
        risk_level = "medium"

    return ReleaseReadinessSummary(
        risk_level=risk_level,
        active_blockers=block_count,
        active_incident_candidates=active_incidents,
        escalation_count=escalation_count,
        unresolved_actions=unresolved_actions,
        release_penalty_total=penalty_total,
        rationale=rationale,
    )


def aggregate_failure_memory_summary(
    memory_records: Iterable[Dict[str, object]],
    *,
    limit: int = 10,
) -> FailureMemoryDashboardSummary:
    root_cause_counts: Counter[str] = Counter()
    heatmap_counter: Counter[str] = Counter()
    recurring = 0
    high_conf = 0
    flaky = 0

    for rec in memory_records:
        root = str(rec.get("root_cause") or "unknown")
        root_cause_counts[root] += _safe_int(rec.get("occurrence_count", 1), default=1)
        if _safe_int(rec.get("occurrence_count", 1), default=1) >= 2:
            recurring += 1
        if _safe_float(rec.get("confidence", 0.0)) >= 0.75:
            high_conf += 1
        if bool(rec.get("flaky", False)):
            flaky += 1

        adapter = str(rec.get("adapter_id", "unknown"))
        project = str(rec.get("project_id", "unknown"))
        module = str(rec.get("module") or rec.get("execution_path") or "unknown")
        heatmap_counter[f"{adapter}|{project}|{module}"] += 1

    top_root = [
        LeaderboardEntry(key=rc, label=rc, count=cnt)
        for rc, cnt in root_cause_counts.most_common(limit)
    ]
    heatmap_data = [
        LeaderboardEntry(key=k, label=k, count=c)
        for k, c in heatmap_counter.most_common(limit)
    ]
    return FailureMemoryDashboardSummary(
        top_root_causes=top_root,
        recurring_failure_count=recurring,
        high_confidence_memory_count=high_conf,
        flaky_memory_count=flaky,
        heatmap_data=heatmap_data,
    )


def aggregate_decision_summary(decision_records: Iterable[Dict[str, object]]) -> DecisionDashboardSummary:
    counts: Counter[str] = Counter()
    rationale_buckets: Counter[str] = Counter()
    for rec in decision_records:
        p = str(rec.get("primary_decision", "UNKNOWN")).upper()
        counts[p] += 1
        for reason in rec.get("rationale", []) or []:
            txt = str(reason).lower()
            if "flaky" in txt:
                rationale_buckets["flaky"] += 1
            elif "release" in txt:
                rationale_buckets["release"] += 1
            elif "manual" in txt or "ambigu" in txt:
                rationale_buckets["manual_or_ambiguous"] += 1
            elif "rerun" in txt:
                rationale_buckets["rerun"] += 1
            else:
                rationale_buckets["other"] += 1

    return DecisionDashboardSummary(
        decision_counts=dict(counts),
        block_release_count=counts.get("BLOCK_RELEASE", 0),
        escalate_count=counts.get("ESCALATE", 0),
        suppress_count=counts.get("SUPPRESS_KNOWN_FLAKY", 0),
        rerun_count=counts.get("RERUN", 0) + counts.get("RERUN_WITH_STRATEGY", 0),
        manual_review_count=counts.get("MANUAL_INVESTIGATION", 0),
        rationale_buckets=dict(rationale_buckets),
    )


def aggregate_self_healing_summary(
    self_healing_records: Iterable[Dict[str, object]],
    *,
    limit: int = 10,
) -> SelfHealingDashboardSummary:
    records = list(self_healing_records)
    total = len(records)
    if total == 0:
        return SelfHealingDashboardSummary(
            total_actions=0,
            success_rate=0.0,
            avg_attempts=0.0,
            strategy_effectiveness=[],
            recovery_rate=0.0,
            top_failed_strategies=[],
        )

    success_count = sum(1 for r in records if bool(r.get("success", False)))
    avg_attempts = sum(_safe_int(r.get("attempts_used", 0)) for r in records) / float(total)

    by_strategy: Dict[str, Dict[str, int]] = defaultdict(lambda: {"success": 0, "failure": 0})
    for r in records:
        strategy = str(r.get("strategy") or r.get("metadata", {}).get("strategy") or "none")
        if bool(r.get("success", False)):
            by_strategy[strategy]["success"] += 1
        else:
            by_strategy[strategy]["failure"] += 1

    effectiveness: List[StrategyEffectiveness] = []
    failed_lb: List[LeaderboardEntry] = []
    for strategy, stats in by_strategy.items():
        s = stats["success"]
        f = stats["failure"]
        total_sf = s + f
        rate = (s / float(total_sf)) if total_sf else 0.0
        effectiveness.append(
            StrategyEffectiveness(
                strategy=strategy,
                success_count=s,
                failure_count=f,
                effectiveness_rate=rate,
            )
        )
        failed_lb.append(
            LeaderboardEntry(
                key=strategy,
                label=strategy,
                count=f,
            )
        )

    effectiveness.sort(key=lambda x: x.effectiveness_rate, reverse=True)
    failed_lb.sort(key=lambda x: x.count, reverse=True)

    recovery_rate = success_count / float(total)
    return SelfHealingDashboardSummary(
        total_actions=total,
        success_rate=recovery_rate,
        avg_attempts=avg_attempts,
        strategy_effectiveness=effectiveness,
        recovery_rate=recovery_rate,
        top_failed_strategies=failed_lb[:limit],
    )


def aggregate_candidate_summary(
    bug_records: Iterable[Dict[str, object]],
    incident_records: Iterable[Dict[str, object]],
    suppression_records: Iterable[Dict[str, object]],
    *,
    limit: int = 10,
) -> CandidateDashboardSummary:
    bugs = list(bug_records)
    incidents = list(incident_records)
    suppressions = list(suppression_records)

    duplicate_suppressions = 0
    for s in suppressions:
        text = " ".join(str(x) for x in (s.get("rationale", []) or []))
        if "duplicate" in text.lower() or s.get("metadata", {}).get("duplicate_candidate_id"):
            duplicate_suppressions += 1

    def _to_lb(records: List[Dict[str, object]], key_name: str) -> List[LeaderboardEntry]:
        ordered = sorted(records, key=lambda r: _safe_int(r.get("recurrence", 0)), reverse=True)
        out: List[LeaderboardEntry] = []
        for r in ordered[:limit]:
            out.append(
                LeaderboardEntry(
                    key=str(r.get("candidate_id", "")),
                    label=str(r.get("title", "")),
                    count=_safe_int(r.get("recurrence", 0)),
                    severity=str(r.get("severity", "")),
                    confidence=_safe_float(r.get("confidence", 0.0)),
                    owner=str(r.get("recommended_owner", "")),
                    metadata={key_name: str(r.get("candidate_id", ""))},
                )
            )
        return out

    owner_dist: Counter[str] = Counter()
    for r in bugs + incidents:
        owner = str(r.get("recommended_owner", "unknown"))
        owner_dist[owner] += 1

    return CandidateDashboardSummary(
        total_bug_candidates=len(bugs),
        total_incident_candidates=len(incidents),
        duplicate_suppression_count=duplicate_suppressions,
        top_bug_candidates=_to_lb(bugs, "bug_candidate_id"),
        top_incident_candidates=_to_lb(incidents, "incident_candidate_id"),
        owner_distribution=dict(owner_dist),
    )


def aggregate_governance_summary(
    suppression_records: Iterable[Dict[str, object]],
    decision_records: Iterable[Dict[str, object]],
    self_healing_records: Iterable[Dict[str, object]],
) -> GovernanceDashboardSummary:
    suppressions = list(suppression_records)
    decisions = list(decision_records)
    actions = list(self_healing_records)

    manual_reviews = 0
    for d in decisions:
        if str(d.get("primary_decision", "")).upper() == "MANUAL_INVESTIGATION":
            manual_reviews += 1

    guardrail_stops = 0
    reasons: Counter[str] = Counter()
    for a in actions:
        logs = a.get("logs", []) or []
        metadata = a.get("metadata", {}) or {}
        if metadata.get("guardrail") or any("guardrail" in str(line).lower() for line in logs):
            guardrail_stops += 1
            reason = str(metadata.get("guardrail", "guardrail_stop"))
            reasons[reason] += 1
        if str(a.get("instruction_type", "")).lower() == "manual_review":
            reasons["manual_review_instruction"] += 1

    for s in suppressions:
        for rs in s.get("rationale", []) or []:
            txt = str(rs).strip().lower() or "unknown"
            reasons[txt] += 1

    return GovernanceDashboardSummary(
        suppressed_candidate_count=len(suppressions),
        manual_review_count=manual_reviews,
        critical_path_guardrail_stops=guardrail_stops,
        automation_stop_reasons=dict(reasons),
    )

