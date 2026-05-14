"""In-memory project profile service for Manual QA Phase 1."""

from __future__ import annotations

import re
from typing import Dict, Iterable, Optional

from orchestrator.manual_qa.models import ProjectProfile


SUPPORTED_PRODUCT_TYPES = {
    "web",
    "api",
    "mobile",
    "model",
    "llm_app",
    "workflow",
    "data_pipeline",
}


class ProjectProfileService:
    """Create deterministic in-memory project profiles."""

    def create_project_profile(
        self,
        *,
        name: str,
        product_type: str,
        description: str = "",
        owner: str = "",
        tags: Optional[Iterable[str]] = None,
        metadata: Optional[Dict[str, object]] = None,
        project_id: Optional[str] = None,
    ) -> ProjectProfile:
        clean_name = str(name).strip()
        clean_product_type = str(product_type).strip().lower()

        if not clean_name:
            raise ValueError("name is required")
        if not clean_product_type:
            raise ValueError("product_type is required")
        if clean_product_type not in SUPPORTED_PRODUCT_TYPES:
            supported = ", ".join(sorted(SUPPORTED_PRODUCT_TYPES))
            raise ValueError(
                f"Unsupported product_type '{clean_product_type}'. Supported values: {supported}"
            )

        resolved_project_id = str(project_id).strip() if project_id is not None else ""
        if not resolved_project_id:
            resolved_project_id = self._normalize_project_id(clean_name)

        return ProjectProfile(
            project_id=resolved_project_id,
            name=clean_name,
            product_type=clean_product_type,
            description=str(description or "").strip(),
            owner=str(owner or "").strip(),
            tags=[str(tag).strip() for tag in tags or [] if str(tag).strip()],
            metadata=dict(metadata or {}),
        )

    def create_project(self, **kwargs: object) -> ProjectProfile:
        """Compatibility alias for simple callers."""

        return self.create_project_profile(**kwargs)

    def _normalize_project_id(self, name: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
        return slug or "manual-qa-project"

