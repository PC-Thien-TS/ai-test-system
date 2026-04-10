"""Project service layer unifying registry operations."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from orchestrator.compatibility import CompatibilityAnalyzer
from orchestrator.models import (
    CompatibilitySummary,
    GateResult,
    PluginMetadata,
    ProductType,
    Project,
    ProjectSummary,
    Run,
    RunStatus,
)
from orchestrator.platform_summary import PlatformSummaryGenerator
from orchestrator.project_registry import ProjectRegistry
from orchestrator.run_registry import RunRegistry


class ProjectService:
    """Service layer for project and run operations."""

    def __init__(
        self,
        repo_root: Path,
    ):
        """
        Initialize the project service.
        
        Args:
            repo_root: Repository root path.
        """
        self.repo_root = repo_root
        storage_path = repo_root / ".platform"
        
        self.project_registry = ProjectRegistry(storage_path / "projects")
        self.run_registry = RunRegistry(storage_path / "runs")
        self.compatibility_analyzer = CompatibilityAnalyzer()
        self.summary_generator = PlatformSummaryGenerator(
            self.project_registry,
            self.run_registry,
            self.compatibility_analyzer,
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
            The created Project.
        """
        return self.project_registry.create_project(
            name=name,
            product_type=product_type,
            manifest_path=manifest_path,
            description=description,
            tags=tags,
            workspace_id=workspace_id,
            owner_id=owner_id,
        )

    def get_project(self, project_id: str) -> Optional[Project]:
        """Get a project by ID."""
        return self.project_registry.get_project(project_id)

    def list_projects(
        self,
        workspace_id: Optional[str] = None,
        active_only: bool = True,
    ) -> List[Project]:
        """List projects with optional filters."""
        return self.project_registry.list_projects(
            workspace_id=workspace_id,
            active_only=active_only,
        )

    def trigger_run(
        self,
        project_id: str,
    ) -> Optional[Run]:
        """
        Trigger a test run for a project.
        
        This creates a run record. Actual execution is handled separately.
        
        Args:
            project_id: The project ID to run.
            
        Returns:
            The created Run if successful, None otherwise.
        """
        project = self.project_registry.get_project(project_id)
        if not project:
            return None
        
        # Create output directory using run_id (will be assigned by registry)
        output_base = self.repo_root / "outputs" / project.name
        output_base.mkdir(parents=True, exist_ok=True)
        
        # Use a timestamp-based directory name for the run
        import time
        run_dir_name = f"{int(time.time())}"
        output_dir = output_base / run_dir_name
        
        return self.run_registry.create_run(
            project_id=project_id,
            output_path=output_dir,
        )

    def get_run(self, run_id: str) -> Optional[Run]:
        """Get a run by ID."""
        return self.run_registry.get_run(run_id)

    def list_runs(
        self,
        project_id: Optional[str] = None,
        status: Optional[RunStatus] = None,
        limit: int = 100,
    ) -> List[Run]:
        """List runs with optional filters."""
        return self.run_registry.list_runs(
            project_id=project_id,
            status=status,
            limit=limit,
        )

    def update_run(
        self,
        run_id: str,
        status: Optional[RunStatus] = None,
        gate_result: Optional[GateResult] = None,
        flaky: Optional[bool] = None,
        metadata: Optional[Dict] = None,
    ) -> Optional[Run]:
        """Update a run."""
        return self.run_registry.update_run(
            run_id=run_id,
            status=status,
            gate_result=gate_result,
            flaky=flaky,
            metadata=metadata,
        )

    def get_project_summary(self, project_id: str) -> Optional[ProjectSummary]:
        """Get summary for a project."""
        return self.summary_generator.generate_project_summary(project_id)

    def get_project_runs(self, project_id: str, limit: int = 50) -> List[Run]:
        """Get runs for a project."""
        return self.run_registry.list_runs_by_project(project_id, limit=limit)

    def get_project_trends(self, project_id: str, limit: int = 50) -> List[Dict]:
        """Get trend data for a project."""
        return self.summary_generator.generate_trend_data(project_id, limit)

    def get_platform_summary(self):
        """Get platform-wide summary."""
        return self.summary_generator.generate_platform_summary()

    def get_latest_project_status(self) -> List[Dict]:
        """Get latest status for all projects."""
        return self.summary_generator.get_latest_project_status()

    def list_plugins(
        self,
        product_type: Optional[ProductType] = None,
    ) -> List[PluginMetadata]:
        """List available plugins."""
        return self.compatibility_analyzer.list_plugins(product_type=product_type)

    def get_plugin(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get plugin metadata."""
        return self.compatibility_analyzer.get_plugin(plugin_name)

    def analyze_plugin_compatibility(
        self,
        plugin_name: str,
    ) -> CompatibilitySummary:
        """Analyze plugin compatibility."""
        return self.compatibility_analyzer.analyze_plugin_compatibility(plugin_name)

    def import_existing_domains(self) -> List[Project]:
        """
        Import existing domains as projects.
        
        This provides backward compatibility with the domain-based system.
        
        Returns:
            List of imported projects.
        """
        imported = []
        domains = ["order", "store_verify", "didaunao_release_audit"]
        
        for domain in domains:
            project = self.project_registry.import_from_domain(domain, self.repo_root)
            if project:
                imported.append(project)
        
        # Also import existing output directories as runs
        outputs_dir = self.repo_root / "outputs"
        if outputs_dir.exists():
            for domain_dir in outputs_dir.iterdir():
                if domain_dir.is_dir():
                    project = self.project_registry.get_project_by_name(domain_dir.name)
                    if project:
                        for run_dir in domain_dir.iterdir():
                            if run_dir.is_dir():
                                self.run_registry.import_from_output_dir(run_dir, project.project_id)
        
        return imported

    def get_flaky_projects(self) -> List[ProjectSummary]:
        """Get projects with flaky runs."""
        return self.summary_generator.get_flaky_projects()

    def get_failing_projects(self) -> List[ProjectSummary]:
        """Get projects with failing runs."""
        return self.summary_generator.get_failing_projects()
