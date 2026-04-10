"""Plugin execution base interface and contracts."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from orchestrator.models import ExecutionPath, Run


class ExecutionStatus(Enum):
    """Status of plugin execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


class EvidenceType(Enum):
    """Types of evidence a plugin can collect."""
    SCREENSHOT = "screenshot"
    TRACE = "trace"
    CONSOLE_LOG = "console_log"
    NETWORK_LOG = "network_log"
    ASSERTION = "assertion"
    METRIC = "metric"
    VIDEO = "video"
    HAR = "har"
    CUSTOM = "custom"


@dataclass
class ExecutionContext:
    """Context provided to plugin during execution."""
    run_id: str
    project_id: str
    execution_path: ExecutionPath
    output_path: Path
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timeout_seconds: Optional[int] = None
    retry_count: int = 0
    max_retries: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "project_id": self.project_id,
            "execution_path": self.execution_path.value,
            "output_path": str(self.output_path),
            "config": self.config,
            "metadata": self.metadata,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }


@dataclass
class EvidenceItem:
    """Single evidence item collected by plugin."""
    evidence_type: EvidenceType
    content: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    severity: str = "info"  # critical, high, medium, low, info
    source: str = ""
    confidence: float = 1.0
    related_evidence_ids: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_type": self.evidence_type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "severity": self.severity,
            "source": self.source,
            "confidence": self.confidence,
            "related_evidence_ids": self.related_evidence_ids,
        }


@dataclass
class PluginExecutionResult:
    """Result of plugin execution."""
    plugin_name: str
    status: ExecutionStatus
    success: bool
    evidence: List[EvidenceItem] = field(default_factory=list)
    metrics: Dict[str, Union[int, float]] = field(default_factory=dict)
    error_message: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    duration_seconds: float = 0.0
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_name": self.plugin_name,
            "status": self.status.value,
            "success": self.success,
            "evidence": [e.to_dict() for e in self.evidence],
            "metrics": self.metrics,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "duration_seconds": self.duration_seconds,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
    
    def mark_completed(self):
        """Mark execution as completed."""
        self.completed_at = datetime.utcnow()
        self.duration_seconds = (self.completed_at - self.started_at).total_seconds()


class BasePlugin(ABC):
    """Base interface for all execution plugins."""
    
    def __init__(self):
        self._initialized = False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin name."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin version."""
        pass
    
    @property
    @abstractmethod
    def supported_product_types(self) -> List[str]:
        """List of supported product types."""
        pass
    
    @property
    @abstractmethod
    def supported_execution_paths(self) -> List[ExecutionPath]:
        """List of supported execution paths."""
        pass
    
    @abstractmethod
    async def initialize(self, context: ExecutionContext) -> bool:
        """
        Initialize the plugin with execution context.
        
        Args:
            context: Execution context.
            
        Returns:
            True if initialization successful, False otherwise.
        """
        pass
    
    @abstractmethod
    async def execute(self, context: ExecutionContext) -> PluginExecutionResult:
        """
        Execute the plugin with given context.
        
        Args:
            context: Execution context.
            
        Returns:
            PluginExecutionResult with evidence and metrics.
        """
        pass
    
    @abstractmethod
    async def cleanup(self, context: ExecutionContext) -> bool:
        """
        Clean up resources after execution.
        
        Args:
            context: Execution context.
            
        Returns:
            True if cleanup successful, False otherwise.
        """
        pass
    
    async def validate_config(self, config: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate plugin configuration.
        
        Args:
            config: Configuration to validate.
            
        Returns:
            Tuple of (is_valid, error_messages).
        """
        # Default implementation - subclasses can override
        return True, []
    
    def get_execution_path_config(
        self,
        execution_path: ExecutionPath,
        base_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get configuration for specific execution path.
        
        Args:
            execution_path: The execution path.
            base_config: Base configuration.
            
        Returns:
            Configuration adjusted for the execution path.
        """
        config = base_config.copy()
        
        # Default path-specific adjustments
        if execution_path == ExecutionPath.SMOKE:
            config["depth"] = config.get("depth", 1)
            config["timeout_multiplier"] = config.get("timeout_multiplier", 1.0)
        elif execution_path == ExecutionPath.STANDARD:
            config["depth"] = config.get("depth", 2)
            config["timeout_multiplier"] = config.get("timeout_multiplier", 1.5)
        elif execution_path == ExecutionPath.DEEP:
            config["depth"] = config.get("depth", 3)
            config["timeout_multiplier"] = config.get("timeout_multiplier", 2.0)
        elif execution_path == ExecutionPath.INTELLIGENT:
            config["depth"] = config.get("depth", 4)
            config["timeout_multiplier"] = config.get("timeout_multiplier", 3.0)
        
        return config
    
    def supports_execution_path(self, execution_path: ExecutionPath) -> bool:
        """
        Check if plugin supports a given execution path.
        
        Args:
            execution_path: The execution path to check.
            
        Returns:
            True if supported, False otherwise.
        """
        return execution_path in self.supported_execution_paths
