"""Core data models for the Universal Testing Platform v2.0+."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ProductType(str, Enum):
    """Supported product types for testing."""
    WEB = "web"
    API = "api"
    MODEL = "model"
    RAG = "rag"
    LLM_APP = "llm_app"
    WORKFLOW = "workflow"
    DATA_PIPELINE = "data_pipeline"


class RunStatus(str, Enum):
    """Status of a test run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GateResult(str, Enum):
    """Quality gate result."""
    PASS = "pass"
    FAIL = "fail"
    WARN = "warn"
    UNKNOWN = "unknown"


class SupportLevel(str, Enum):
    """Plugin support level."""
    FULL = "full"
    USABLE = "usable"
    PARTIAL = "partial"
    FALLBACK = "fallback"
    NONE = "none"


class ExecutionPath(str, Enum):
    """Execution path types."""
    SMOKE = "smoke"
    STANDARD = "standard"
    DEEP = "deep"
    INTELLIGENT = "intelligent"


@dataclass
class PluginMetadata:
    """Metadata about a testing plugin."""
    name: str
    version: str
    description: str
    product_types: List[ProductType]
    capabilities: List[str]
    support_level: SupportLevel
    dependencies: Optional[List[str]] = None
    min_platform_version: Optional[str] = None
    execution_depth_score: float = 0.0  # 0.0 to 1.0, depth of real execution vs fallback
    evidence_richness_score: float = 0.0  # 0.0 to 1.0, richness of evidence collected
    confidence_score: float = 0.0  # 0.0 to 1.0, confidence in results


@dataclass
class Project:
    """A testing project in the platform."""
    project_id: str
    name: str
    product_type: ProductType
    manifest_path: Path
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    workspace_id: Optional[str] = None
    owner_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "project_id": self.project_id,
            "name": self.name,
            "product_type": self.product_type.value,
            "manifest_path": str(self.manifest_path),
            "description": self.description,
            "tags": self.tags,
            "workspace_id": self.workspace_id,
            "owner_id": self.owner_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "active": self.active,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Project":
        """Create from dictionary."""
        return cls(
            project_id=data["project_id"],
            name=data["name"],
            product_type=ProductType(data["product_type"]),
            manifest_path=Path(data["manifest_path"]),
            description=data.get("description"),
            tags=data.get("tags", []),
            workspace_id=data.get("workspace_id"),
            owner_id=data.get("owner_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            active=data.get("active", True),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Run:
    """A test run for a project."""
    run_id: str
    project_id: str
    status: RunStatus
    started_at: datetime
    output_path: Path
    completed_at: Optional[datetime] = None
    gate_result: Optional[GateResult] = None
    flaky: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    fallback_ratio: float = 0.0  # 0.0 to 1.0, ratio of fallback executions
    real_execution_ratio: float = 0.0  # 0.0 to 1.0, ratio of real executions
    execution_path: ExecutionPath = ExecutionPath.STANDARD  # Execution path used
    parent_run_id: Optional[str] = None  # Parent run if this is an escalation rerun
    confidence_score: float = 0.0  # Overall confidence score

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "project_id": self.project_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "output_path": str(self.output_path),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "gate_result": self.gate_result.value if self.gate_result else None,
            "flaky": self.flaky,
            "metadata": self.metadata,
            "fallback_ratio": self.fallback_ratio,
            "real_execution_ratio": self.real_execution_ratio,
            "execution_path": self.execution_path.value,
            "parent_run_id": self.parent_run_id,
            "confidence_score": self.confidence_score,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Run":
        """Create from dictionary."""
        return cls(
            run_id=data["run_id"],
            project_id=data["project_id"],
            status=RunStatus(data["status"]),
            started_at=datetime.fromisoformat(data["started_at"]),
            output_path=Path(data["output_path"]),
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            gate_result=GateResult(data["gate_result"]) if data.get("gate_result") else None,
            flaky=data.get("flaky", False),
            metadata=data.get("metadata", {}),
            fallback_ratio=data.get("fallback_ratio", 0.0),
            real_execution_ratio=data.get("real_execution_ratio", 0.0),
            execution_path=ExecutionPath(data.get("execution_path", "standard")),
            parent_run_id=data.get("parent_run_id"),
            confidence_score=data.get("confidence_score", 0.0),
        )


@dataclass
class EscalationChain:
    """Tracks escalation chain for a run."""
    original_run_id: str
    current_run_id: str
    escalation_path: List[Dict[str, Any]]  # List of {run_id, path, reason, timestamp}
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add_escalation(self, run_id: str, path: ExecutionPath, reason: str):
        """Add an escalation step to the chain."""
        self.escalation_path.append({
            "run_id": run_id,
            "path": path.value,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self.current_run_id = run_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_run_id": self.original_run_id,
            "current_run_id": self.current_run_id,
            "escalation_path": self.escalation_path,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EscalationChain":
        """Create from dictionary."""
        return cls(
            original_run_id=data["original_run_id"],
            current_run_id=data["current_run_id"],
            escalation_path=data["escalation_path"],
            created_at=datetime.fromisoformat(data["created_at"]),
        )


@dataclass
class CompatibilitySummary:
    """Summary of plugin compatibility analysis."""
    plugin_name: str
    platform_version: str
    compatible: bool
    support_level: SupportLevel
    notes: List[str] = field(default_factory=list)
    blockers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plugin_name": self.plugin_name,
            "platform_version": self.platform_version,
            "compatible": self.compatible,
            "support_level": self.support_level.value,
            "notes": self.notes,
            "blockers": self.blockers,
        }


@dataclass
class ProjectSummary:
    """Summary of a project's testing status."""
    project_id: str
    project_name: str
    product_type: ProductType
    latest_run_id: Optional[str] = None
    latest_status: Optional[RunStatus] = None
    gate_result: Optional[GateResult] = None
    total_runs: int = 0
    passed_runs: int = 0
    failed_runs: int = 0
    flaky_runs: int = 0
    last_updated: Optional[datetime] = None
    avg_execution_depth_score: float = 0.0  # Average across all runs
    avg_evidence_richness_score: float = 0.0  # Average across all runs
    avg_confidence_score: float = 0.0  # Average across all runs
    avg_fallback_ratio: float = 0.0  # Average across all runs
    avg_real_execution_ratio: float = 0.0  # Average across all runs

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "product_type": self.product_type.value,
            "latest_run_id": self.latest_run_id,
            "latest_status": self.latest_status.value if self.latest_status else None,
            "gate_result": self.gate_result.value if self.gate_result else None,
            "total_runs": self.total_runs,
            "passed_runs": self.passed_runs,
            "failed_runs": self.failed_runs,
            "flaky_runs": self.flaky_runs,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "avg_execution_depth_score": self.avg_execution_depth_score,
            "avg_evidence_richness_score": self.avg_evidence_richness_score,
            "avg_confidence_score": self.avg_confidence_score,
            "avg_fallback_ratio": self.avg_fallback_ratio,
            "avg_real_execution_ratio": self.avg_real_execution_ratio,
        }


@dataclass
class PlatformSummary:
    """Platform-wide summary across all projects."""
    generated_at: datetime
    total_projects: int
    active_projects: int
    total_runs: int
    failing_projects: int
    flaky_projects: int
    avg_execution_depth_score: float = 0.0
    avg_evidence_richness_score: float = 0.0
    avg_confidence_score: float = 0.0
    avg_fallback_ratio: float = 0.0
    avg_real_execution_ratio: float = 0.0
    plugin_maturity_trend: Dict[str, float] = field(default_factory=dict)
    gate_overview: Dict[str, int] = field(default_factory=dict)
    plugin_usage: Dict[str, int] = field(default_factory=dict)
    confidence_trend: List[Dict[str, Any]] = field(default_factory=list)
    plugin_depth_scores: List[Dict[str, Any]] = field(default_factory=list)
    fallback_ratios: List[Dict[str, Any]] = field(default_factory=list)
    plugin_maturity_scores: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_projects": self.total_projects,
            "active_projects": self.active_projects,
            "total_runs": self.total_runs,
            "failing_projects": self.failing_projects,
            "flaky_projects": self.flaky_projects,
            "gate_overview": {k.value: v for k, v in self.gate_overview.items()},
            "plugin_usage": self.plugin_usage,
            "generated_at": self.generated_at.isoformat(),
            "avg_execution_depth_score": self.avg_execution_depth_score,
            "avg_evidence_richness_score": self.avg_evidence_richness_score,
            "avg_confidence_score": self.avg_confidence_score,
            "avg_fallback_ratio": self.avg_fallback_ratio,
            "avg_real_execution_ratio": self.avg_real_execution_ratio,
            "plugin_maturity_trend": self.plugin_maturity_trend,
            "confidence_trend": self.confidence_trend,
            "plugin_depth_scores": self.plugin_depth_scores,
            "fallback_ratios": self.fallback_ratios,
            "plugin_maturity_scores": self.plugin_maturity_scores,
        }
