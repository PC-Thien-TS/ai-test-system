"""Run registry for managing test runs."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from orchestrator.models import GateResult, Run, RunStatus


class RunRegistry:
    """File-based registry for storing and retrieving test runs."""

    def __init__(self, storage_path: Path):
        """
        Initialize the run registry.
        
        Args:
            storage_path: Path to the directory where run data is stored.
        """
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._index_path = self.storage_path / "run_index.json"
        self._runs: Dict[str, Run] = {}
        self._load_index()

    def _load_index(self) -> None:
        """Load run index from disk."""
        if self._index_path.exists():
            try:
                data = json.loads(self._index_path.read_text(encoding="utf-8"))
                for run_id, run_data in data.items():
                    self._runs[run_id] = Run.from_dict(run_data)
            except (json.JSONDecodeError, KeyError, ValueError):
                # If index is corrupted, start fresh
                self._runs = {}

    def _save_index(self) -> None:
        """Save run index to disk."""
        data = {
            run_id: run.to_dict()
            for run_id, run in self._runs.items()
        }
        self._index_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )

    def create_run(
        self,
        project_id: str,
        output_path: Path,
    ) -> Run:
        """
        Create a new run.
        
        Args:
            project_id: The project ID this run belongs to.
            output_path: Path to the run output directory.
            
        Returns:
            The created Run instance.
        """
        run_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        run = Run(
            run_id=run_id,
            project_id=project_id,
            status=RunStatus.PENDING,
            started_at=now,
            output_path=output_path,
        )
        
        self._runs[run_id] = run
        self._save_index()
        return run

    def get_run(self, run_id: str) -> Optional[Run]:
        """
        Retrieve a run by ID.
        
        Args:
            run_id: The run ID to retrieve.
            
        Returns:
            The Run if found, None otherwise.
        """
        return self._runs.get(run_id)

    def list_runs(
        self,
        project_id: Optional[str] = None,
        status: Optional[RunStatus] = None,
        limit: int = 100,
    ) -> List[Run]:
        """
        List runs, optionally filtered.
        
        Args:
            project_id: Optional project ID to filter by.
            status: Optional status to filter by.
            limit: Maximum number of runs to return.
            
        Returns:
            List of matching runs, sorted by started_at descending.
        """
        runs = list(self._runs.values())
        
        if project_id:
            runs = [r for r in runs if r.project_id == project_id]
        
        if status:
            runs = [r for r in runs if r.status == status]
        
        # Sort by started_at descending
        runs.sort(key=lambda r: r.started_at, reverse=True)
        
        return runs[:limit]

    def update_run(
        self,
        run_id: str,
        status: Optional[RunStatus] = None,
        completed_at: Optional[datetime] = None,
        gate_result: Optional[GateResult] = None,
        flaky: Optional[bool] = None,
        metadata: Optional[Dict] = None,
    ) -> Optional[Run]:
        """
        Update an existing run.
        
        Args:
            run_id: The run ID to update.
            status: Optional new status.
            completed_at: Optional completion timestamp.
            gate_result: Optional quality gate result.
            flaky: Optional flaky flag.
            metadata: Optional metadata to merge.
            
        Returns:
            The updated Run if found, None otherwise.
        """
        run = self._runs.get(run_id)
        if not run:
            return None
        
        if status is not None:
            run.status = status
        if completed_at is not None:
            run.completed_at = completed_at
        if gate_result is not None:
            run.gate_result = gate_result
        if flaky is not None:
            run.flaky = flaky
        if metadata is not None:
            run.metadata.update(metadata)
        
        self._save_index()
        return run

    def list_runs_by_project(self, project_id: str, limit: int = 50) -> List[Run]:
        """
        List all runs for a specific project.
        
        Args:
            project_id: The project ID.
            limit: Maximum number of runs to return.
            
        Returns:
            List of runs for the project, sorted by started_at descending.
        """
        return self.list_runs(project_id=project_id, limit=limit)

    def get_latest_run(self, project_id: str) -> Optional[Run]:
        """
        Get the most recent run for a project.
        
        Args:
            project_id: The project ID.
            
        Returns:
            The latest Run if found, None otherwise.
        """
        runs = self.list_runs_by_project(project_id, limit=1)
        return runs[0] if runs else None

    def import_from_output_dir(self, output_dir: Path, project_id: str) -> Optional[Run]:
        """
        Import an existing run from an output directory.
        
        This provides backward compatibility with existing output structure.
        
        Args:
            output_dir: Path to the output directory (e.g., outputs/order/20260303_112020).
            project_id: The project ID to associate with this run.
            
        Returns:
            The created Run if successful, None otherwise.
        """
        if not output_dir.exists():
            return None
        
        # Extract run_id from directory name
        run_id = output_dir.name
        
        # Check if run already exists
        existing = self.get_run(run_id)
        if existing:
            return existing
        
        # Try to read run_meta.json for additional info
        meta_path = output_dir / "run_meta.json"
        metadata = {}
        status = RunStatus.COMPLETED
        completed_at = None
        
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                metadata = meta
                
                # Determine status from meta
                if "finished_at" in meta:
                    completed_at = datetime.fromisoformat(meta["finished_at"])
                    status = RunStatus.COMPLETED
                else:
                    status = RunStatus.RUNNING
            except (json.JSONDecodeError, ValueError, KeyError):
                pass
        
        # Create the run
        started_at = datetime.utcnow()
        if "started_at" in metadata:
            try:
                started_at = datetime.fromisoformat(metadata["started_at"])
            except (ValueError, KeyError):
                pass
        
        run = Run(
            run_id=run_id,
            project_id=project_id,
            status=status,
            started_at=started_at,
            output_path=output_dir,
            completed_at=completed_at,
            metadata=metadata,
        )
        
        self._runs[run_id] = run
        self._save_index()
        return run

    def get_run_statistics(self, project_id: str) -> Dict[str, int]:
        """
        Get statistics for runs of a project.
        
        Args:
            project_id: The project ID.
            
        Returns:
            Dictionary with run statistics.
        """
        runs = self.list_runs_by_project(project_id, limit=1000)
        
        stats = {
            "total": len(runs),
            "pending": 0,
            "running": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
            "flaky": 0,
        }
        
        for run in runs:
            stats[run.status.value] += 1
            if run.flaky:
                stats["flaky"] += 1
        
        return stats
