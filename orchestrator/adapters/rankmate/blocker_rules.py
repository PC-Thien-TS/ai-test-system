from __future__ import annotations

import json
from typing import Any

from orchestrator.adapters.base.models import BlockerClassification


def classify_blocker(finding: Any) -> BlockerClassification:
    if isinstance(finding, dict):
        text = json.dumps(finding, ensure_ascii=False).lower()
    else:
        text = str(finding).lower()

    if any(token in text for token in ("stripe", "secret", "signature", "runtime", "env", "credential")):
        return BlockerClassification(blocker_type="env_blocker", reason="Runtime/environment dependency not aligned.")
    if any(token in text for token in ("seed", "missing slot", "data gap")):
        return BlockerClassification(blocker_type="coverage_gap", reason="Deterministic seed/data prerequisite missing.")
    if any(token in text for token in ("500", "defect", "regression", "state-machine")):
        return BlockerClassification(blocker_type="product_defect", reason="Behavior indicates backend product defect.")
    return BlockerClassification(blocker_type="unknown", reason="Unable to classify blocker from current evidence.")

