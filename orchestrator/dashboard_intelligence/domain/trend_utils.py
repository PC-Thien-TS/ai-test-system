from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Iterable, List, Optional

from .models import TrendPoint


def parse_record_timestamp(record: Dict[str, object]) -> Optional[datetime]:
    keys = ("timestamp", "generated_at_utc", "created_at", "last_seen")
    for key in keys:
        raw = record.get(key)
        if not raw:
            continue
        try:
            txt = str(raw).replace("Z", "+00:00")
            dt = datetime.fromisoformat(txt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def filter_by_date_range(
    records: Iterable[Dict[str, object]],
    *,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> List[Dict[str, object]]:
    if start_date is None and end_date is None:
        return list(records)
    output: List[Dict[str, object]] = []
    for rec in records:
        ts = parse_record_timestamp(rec)
        if ts is None:
            continue
        if start_date is not None and ts < start_date:
            continue
        if end_date is not None and ts > end_date:
            continue
        output.append(rec)
    return output


def bucket_daily(
    records: Iterable[Dict[str, object]],
    *,
    value_selector: Callable[[Dict[str, object]], float] = lambda _: 1.0,
) -> Dict[str, float]:
    buckets: Counter[str] = Counter()
    for rec in records:
        ts = parse_record_timestamp(rec)
        if ts is None:
            continue
        key = ts.date().isoformat()
        buckets[key] += float(value_selector(rec))
    return dict(sorted(buckets.items(), key=lambda x: x[0]))


def build_trend_points(
    daily_buckets: Dict[str, float],
    *,
    label_prefix: str = "",
) -> List[TrendPoint]:
    points: List[TrendPoint] = []
    for day, value in daily_buckets.items():
        points.append(
            TrendPoint(
                timestamp=f"{day}T00:00:00+00:00",
                value=float(value),
                label=f"{label_prefix}{day}",
            )
        )
    return points


def trend_direction(points: List[TrendPoint]) -> str:
    if len(points) < 2:
        return "flat"
    diff = points[-1].value - points[-2].value
    if diff > 0:
        return "up"
    if diff < 0:
        return "down"
    return "flat"


def window_compare(
    records: Iterable[Dict[str, object]],
    *,
    now: Optional[datetime] = None,
    window_days: int = 7,
) -> Dict[str, float]:
    current_now = now or datetime.now(timezone.utc)
    current_start = current_now - timedelta(days=window_days)
    prev_start = current_start - timedelta(days=window_days)

    current_count = len(filter_by_date_range(records, start_date=current_start, end_date=current_now))
    prev_count = len(filter_by_date_range(records, start_date=prev_start, end_date=current_start))
    delta = current_count - prev_count
    return {
        "current": float(current_count),
        "previous": float(prev_count),
        "delta": float(delta),
        "direction": 1.0 if delta > 0 else -1.0 if delta < 0 else 0.0,
    }

