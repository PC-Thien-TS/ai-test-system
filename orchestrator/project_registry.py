"""Project registry for managing testing projects."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from orchestrator.models import Project, ProductType


class ProjectRegistry:
    """File-based registry for storing and retrieving projects."""

    def __init__(self, storage_path: Path):
        """
        Initialize the project registry.
        
        Args:
            storage_path: Path to the directory where project data is stored.
        """
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._index_path = self.storage_path / "project_index.json"
        self._projects: Dict[str, Project] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load project index from disk."""
        if self._index_path.exists():
            try:
                data = json.loads(self._index_path.read_text(encoding="utf-8"))
                for project_id, project_data in data.items():
                    self._projects[project_id] = Project.from_dict(project_data)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                # If index is corrupted, start fresh
                self._projects = {}

    def _save_index(self) -> None:
        """Save project index to disk."""
        data = {
            project_id: project.to_dict()
            for project_id, project in self._projects.items()
        }
        self._index_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def create_project(
        self,
        name: str,
        product_type: ProductType,
        manifest_path: Path,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        workspace_id: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> Project:
        """
        Create a new project.
        
        Args:
            name: Project name.
            product_type: Product type being tested.
            manifest_path: Path to the project manifest.
            description: Optional project description.
            tags: Optional project tags.
            workspace_id: Optional workspace ID for multi-tenant support.
            owner_id: Optional owner user ID.
            
        Returns:
            The created Project instance.
        """
        project_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        project = Project(
            project_id=project_id,
            name=name,
            product_type=product_type,
            manifest_path=manifest_path,
            description=description,
            tags=tags or [],
            workspace_id=workspace_id,
            owner_id=owner_id,
            created_at=now,
            updated_at=now,
            active=True,
        )
        
        self._projects[project_id] = project
        self._save_index()
        return project

    def get_project(self, project_id: str) -> Optional[Project]:
        """
        Retrieve a project by ID.
        
        Args:
            project_id: The project ID to retrieve.
            
        Returns:
            The Project if found, None otherwise.
        """
        return self._projects.get(project_id)

    def list_projects(
        self,
        workspace_id: Optional[str] = None,
        active_only: bool = True,
    ) -> List[Project]:
        """
        List projects, optionally filtered.
        
        Args:
            workspace_id: Optional workspace ID to filter by.
            active_only: If True, only return active projects.
            
        Returns:
            List of matching projects.
        """
        projects = list(self._projects.values())
        
        if workspace_id:
            projects = [p for p in projects if p.workspace_id == workspace_id]
        
        if active_only:
            projects = [p for p in projects if p.active]
        
        return projects

    def update_project(
        self,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        active: Optional[bool] = None,
    ) -> Optional[Project]:
        """
        Update an existing project.
        
        Args:
            project_id: The project ID to update.
            name: Optional new name.
            description: Optional new description.
            tags: Optional new tags.
            active: Optional new active status.
            
        Returns:
            The updated Project if found, None otherwise.
        """
        project = self._projects.get(project_id)
        if not project:
            return None
        
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if tags is not None:
            project.tags = tags
        if active is not None:
            project.active = active
        
        project.updated_at = datetime.utcnow()
        self._save_index()
        return project

    def delete_project(self, project_id: str) -> bool:
        """
        Delete a project (soft delete by setting active=False).
        
        Args:
            project_id: The project ID to delete.
            
        Returns:
            True if project was found and deleted, False otherwise.
        """
        project = self._projects.get(project_id)
        if not project:
            return False
        
        project.active = False
        project.updated_at = datetime.utcnow()
        self._save_index()
        return True

    def get_project_by_name(self, name: str, workspace_id: Optional[str] = None) -> Optional[Project]:
        """
        Find a project by name (and optionally workspace).
        
        Args:
            name: The project name to search for.
            workspace_id: Optional workspace ID to scope the search.
            
        Returns:
            The Project if found, None otherwise.
        """
        for project in self._projects.values():
            if project.name == name:
                if workspace_id is None or project.workspace_id == workspace_id:
                    return project
        return None

    def import_from_domain(self, domain: str, repo_root: Path) -> Optional[Project]:
        """
        Import an existing domain as a project.
        
        This provides backward compatibility with the existing domain-based system.
        
        Args:
            domain: The domain name (e.g., 'order', 'store_verify').
            repo_root: The repository root path.
            
        Returns:
            The created Project if successful, None otherwise.
        """
        domain_dir = repo_root / "domains" / domain
        if not domain_dir.exists():
            return None
        
        # Check if project already exists
        existing = self.get_project_by_name(domain)
        if existing:
            return existing
        
        # Map domain to product type
        product_type_map = {
            "order": ProductType.WORKFLOW,
            "store_verify": ProductType.WORKFLOW,
            "didaunao_release_audit": ProductType.WORKFLOW,
        }
        product_type = product_type_map.get(domain, ProductType.WORKFLOW)
        
        # Use the domain directory as the manifest path
        manifest_path = domain_dir / "design" / "state_machine.md"
        if not manifest_path.exists():
            manifest_path = domain_dir
        
        return self.create_project(
            name=domain,
            product_type=product_type,
            manifest_path=manifest_path,
            description=f"Domain-based testing for {domain}",
            tags=["domain", "legacy"],
        )
