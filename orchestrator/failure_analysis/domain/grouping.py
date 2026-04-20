from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from typing import Callable, Dict, Iterable, List

from .models import FailureCase, FailureGroup, FailureInference, SEVERITY_RANK

_RE_NUMBERS = re.compile(r"\b\d+\b")
_RE_HEX = re.compile(r"\b[0-9a-f]{8,}\b", re.IGNORECASE)
_RE_QUOTED_SINGLE = re.compile(r"'[^']{1,120}'")
_RE_QUOTED_DOUBLE = re.compile(r'"[^"]{1,120}"')
_RE_WS = re.compile(r"\s+")


def normalize_message_pattern(message: str) -> str:
    text = (message or "").strip().lower()
    text = _RE_HEX.sub("<id>", text)
    text = _RE_NUMBERS.sub("<num>", text)
    text = _RE_QUOTED_SINGLE.sub("<str>", text)
    text = _RE_QUOTED_DOUBLE.sub("<str>", text)
    text = _RE_WS.sub(" ", text)
    return text[:400]


def extract_module_family(nodeid: str) -> str:
    path = (nodeid or "").split("::", 1)[0].replace("\\", "/")
    if not path:
        return "unknown"
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 3 and parts[0] == "tests":
        return "/".join(parts[:3])
    if len(parts) >= 2:
        return "/".join(parts[:2])
    return parts[0]


def build_group_signature(category: str, module_family: str, message_pattern: str) -> str:
    stable = f"{category}|{module_family}|{message_pattern}"
    return hashlib.sha1(stable.encode("utf-8")).hexdigest()


def build_group_id(signature: str) -> str:
    return f"grp-{signature[:8]}"


def group_failures(
    failures: Iterable[FailureCase],
    *,
    infer: Callable[[str], FailureInference],
) -> List[FailureGroup]:
    grouped: Dict[str, Dict[str, object]] = defaultdict(dict)

    for failure in failures:
        module_family = failure.module_family or extract_module_family(failure.nodeid)
        inference = infer(failure.message)
        signature = build_group_signature(inference.category, module_family, inference.message_pattern)
        key = signature

        if key not in grouped:
            grouped[key] = {
                "group_id": build_group_id(signature),
                "category": inference.category,
                "severity": inference.severity,
                "owner": inference.owner,
                "count": 0,
                "examples": [],
                "message_pattern": inference.message_pattern,
                "module_family": module_family,
                "recommended_action": inference.recommended_action,
                "signature": signature,
                "metadata": {"matched_rule": inference.matched_rule},
            }

        entry = grouped[key]
        entry["count"] = int(entry["count"]) + 1
        if len(entry["examples"]) < 5:
            entry["examples"].append(failure.nodeid)

    output: list[FailureGroup] = []
    for entry in grouped.values():
        output.append(
            FailureGroup(
                group_id=str(entry["group_id"]),
                category=str(entry["category"]),
                severity=str(entry["severity"]),
                owner=str(entry["owner"]),
                count=int(entry["count"]),
                examples=list(entry["examples"]),
                message_pattern=str(entry["message_pattern"]),
                module_family=str(entry["module_family"]),
                recommended_action=str(entry["recommended_action"]),
                signature=str(entry["signature"]),
                metadata=dict(entry["metadata"]),
            )
        )

    output.sort(
        key=lambda grp: (
            -SEVERITY_RANK.get(grp.severity, 0),
            -grp.count,
            grp.category,
            grp.group_id,
        )
    )
    return output
