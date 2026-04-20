from __future__ import annotations

import hashlib
import re
from typing import Dict, List, Tuple

from .models import FailureCase, FailureGroup
from .rules import infer_failure


_MULTISPACE_RE = re.compile(r"\s+")
_DIGIT_RE = re.compile(r"\b\d+\b")
_HEX_RE = re.compile(r"\b[0-9a-f]{8,}\b")
_QUOTED_RE = re.compile(r"\"[^\"]*\"|'[^']*'")


def normalize_message(message: str) -> str:
    value = (message or "").strip().lower()
    if not value:
        return "no_failure_message"
    value = _HEX_RE.sub("<id>", value)
    value = _DIGIT_RE.sub("<n>", value)
    value = _QUOTED_RE.sub("<str>", value)
    value = _MULTISPACE_RE.sub(" ", value)
    return value[:220]


def module_family_from_nodeid(nodeid: str) -> str:
    return nodeid.split("::", 1)[0].replace("\\", "/")


def build_group_signature(case: FailureCase) -> Tuple[str, str, str]:
    inference = infer_failure(case.nodeid, case.message)
    module_family = module_family_from_nodeid(case.nodeid)
    message_pattern = normalize_message(case.message)
    signature = f"{inference.category}|{module_family}|{message_pattern}"
    return signature, message_pattern, module_family


def stable_group_id(signature: str) -> str:
    digest = hashlib.sha1(signature.encode("utf-8")).hexdigest()[:8]
    return f"grp-{digest}"


def group_failures(cases: List[FailureCase]) -> List[FailureGroup]:
    buckets: Dict[str, Dict[str, object]] = {}

    for case in cases:
        inference = infer_failure(case.nodeid, case.message)
        signature, message_pattern, _module = build_group_signature(case)
        if signature not in buckets:
            buckets[signature] = {
                "inference": inference,
                "count": 0,
                "examples": [],
                "message_pattern": message_pattern,
                "sample_message": case.message.strip()[:400],
            }
        bucket = buckets[signature]
        bucket["count"] = int(bucket["count"]) + 1
        examples = bucket["examples"]
        if isinstance(examples, list) and len(examples) < 5:
            examples.append(case.nodeid)

    groups: List[FailureGroup] = []
    for signature, bucket in buckets.items():
        inference = bucket["inference"]
        groups.append(
            FailureGroup(
                group_id=stable_group_id(signature),
                category=inference.category,
                severity=inference.severity,
                owner=inference.owner,
                count=int(bucket["count"]),
                examples=list(bucket["examples"]),
                message_pattern=str(bucket["message_pattern"]),
                recommended_action=inference.recommended_action,
                signature=signature,
                most_affected_area=inference.area,
                sample_message=str(bucket["sample_message"]),
            )
        )

    groups.sort(key=lambda g: (-g.count, g.category, g.group_id))
    return groups

