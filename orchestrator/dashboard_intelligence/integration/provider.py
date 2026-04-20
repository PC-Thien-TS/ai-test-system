from __future__ import annotations

import os
from pathlib import Path

from ..application.service import DashboardIntelligenceService
from ..infrastructure.local_readers import LocalDashboardArtifactReader
from ..infrastructure.query_repository import DashboardQueryRepository


def build_dashboard_intelligence_service(*, artifact_root: Path | None = None) -> DashboardIntelligenceService:
    resolved_root = artifact_root or Path(os.getenv("DASHBOARD_ARTIFACT_ROOT", "artifacts"))
    reader = LocalDashboardArtifactReader(resolved_root)
    repo = DashboardQueryRepository(reader=reader)
    return DashboardIntelligenceService(query_repository=repo)

