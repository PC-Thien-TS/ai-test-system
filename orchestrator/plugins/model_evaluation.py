"""Model Evaluation plugin for ML/AI model quality validation with real execution."""

import json
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from dataclasses import dataclass

from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    roc_auc_score,
    precision_recall_curve,
    roc_curve,
)
from sklearn.calibration import calibration_curve
from sklearn.preprocessing import label_binarize

from orchestrator.models import ExecutionPath, ProductType
from orchestrator.plugins.base import (
    BasePlugin,
    ExecutionContext,
    EvidenceItem,
    EvidenceType,
    ExecutionStatus,
    PluginExecutionResult,
)


@dataclass
class ModelEvaluationConfig:
    """Configuration for model evaluation."""
    model_type: str = "binary"  # binary, multiclass
    threshold: float = 0.5
    positive_label: int = 1
    num_classes: int = 2
    calibration_bins: int = 10


class ModelEvaluationPlugin(BasePlugin):
    """Model Evaluation plugin with real execution using scikit-learn + numpy."""
    ModelEvaluationConfig = ModelEvaluationConfig
    
    def __init__(self):
        super().__init__()
        self._config: Optional[ModelEvaluationConfig] = None
        self._predictions: Optional[np.ndarray] = None
        self._labels: Optional[np.ndarray] = None
        self._probabilities: Optional[np.ndarray] = None
    
    @property
    def name(self) -> str:
        return "model_evaluation"
    
    @property
    def version(self) -> str:
        return "3.0.0"
    
    @property
    def supported_product_types(self) -> List[str]:
        return [ProductType.MODEL.value]
    
    @property
    def supported_execution_paths(self) -> List[ExecutionPath]:
        return [
            ExecutionPath.SMOKE,
            ExecutionPath.STANDARD,
            ExecutionPath.DEEP,
            ExecutionPath.INTELLIGENT,
        ]
    
    async def initialize(self, context: ExecutionContext) -> bool:
        """
        Initialize model evaluation with configuration.
        
        Args:
            context: Execution context.
            
        Returns:
            True if initialization successful, False otherwise.
        """
        try:
            config = context.config
            
            self._config = ModelEvaluationConfig(
                model_type=config.get("model_type", "binary"),
                threshold=config.get("threshold", 0.5),
                positive_label=config.get("positive_label", 1),
                num_classes=config.get("num_classes", 2),
                calibration_bins=config.get("calibration_bins", 10),
            )
            
            # Load predictions and labels from context or files
            if "predictions" in context.metadata:
                self._predictions = np.array(context.metadata["predictions"])
            elif "predictions_path" in context.config:
                predictions_path = Path(context.config["predictions_path"])
                self._predictions = np.load(predictions_path)
            
            if "labels" in context.metadata:
                self._labels = np.array(context.metadata["labels"])
            elif "labels_path" in context.config:
                labels_path = Path(context.config["labels_path"])
                self._labels = np.load(labels_path)
            
            if "probabilities" in context.metadata:
                self._probabilities = np.array(context.metadata["probabilities"])
            elif "probabilities_path" in context.config:
                probabilities_path = Path(context.config["probabilities_path"])
                self._probabilities = np.load(probabilities_path)
            
            # Validate data
            if self._predictions is None or self._labels is None:
                return False
            
            if len(self._predictions) != len(self._labels):
                return False
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"Model Evaluation plugin initialization error: {e}")
            return False
    
    async def execute(self, context: ExecutionContext) -> PluginExecutionResult:
        """
        Execute model evaluation based on execution path.
        
        Args:
            context: Execution context.
            
        Returns:
            PluginExecutionResult with evidence and metrics.
        """
        result = PluginExecutionResult(
            plugin_name=self.name,
            status=ExecutionStatus.RUNNING,
            success=False,
        )
        
        try:
            evidence_items = []
            assertions_passed = 0
            assertions_failed = 0
            metrics_dict = {}
            
            # Get evaluation scope based on execution path
            evaluation_scope = self._get_evaluation_scope(context.execution_path, context.config)
            
            # Run evaluation based on scope
            if "accuracy" in evaluation_scope:
                accuracy, accuracy_evidence, acc_passed, acc_failed = self._evaluate_accuracy(context)
                evidence_items.extend(accuracy_evidence)
                assertions_passed += acc_passed
                assertions_failed += acc_failed
                metrics_dict["accuracy"] = accuracy
            
            if "precision" in evaluation_scope:
                precision, precision_evidence, prec_passed, prec_failed = self._evaluate_precision(context)
                evidence_items.extend(precision_evidence)
                assertions_passed += prec_passed
                assertions_failed += prec_failed
                metrics_dict["precision"] = precision
            
            if "recall" in evaluation_scope:
                recall, recall_evidence, rec_passed, rec_failed = self._evaluate_recall(context)
                evidence_items.extend(recall_evidence)
                assertions_passed += rec_passed
                assertions_failed += rec_failed
                metrics_dict["recall"] = recall
            
            if "f1" in evaluation_scope:
                f1, f1_evidence, f1_passed, f1_failed = self._evaluate_f1(context)
                evidence_items.extend(f1_evidence)
                assertions_passed += f1_passed
                assertions_failed += f1_failed
                metrics_dict["f1"] = f1
            
            if "confusion_matrix" in evaluation_scope:
                cm_evidence = self._evaluate_confusion_matrix(context)
                evidence_items.extend(cm_evidence)
                metrics_dict["confusion_matrix"] = True
            
            if "threshold_sweep" in evaluation_scope:
                threshold_evidence = self._evaluate_threshold_sweep(context)
                evidence_items.extend(threshold_evidence)
                metrics_dict["threshold_sweep"] = True
            
            if "calibration" in evaluation_scope:
                calibration_evidence = self._evaluate_calibration(context)
                evidence_items.extend(calibration_evidence)
            
            if "per_class" in evaluation_scope:
                per_class_metrics, per_class_evidence = self._evaluate_per_class(context)
                evidence_items.extend(per_class_evidence)
                metrics_dict["per_class_metrics"] = per_class_metrics
            
            if "drift_detection" in evaluation_scope:
                drift_evidence = self._evaluate_drift(context)
                evidence_items.extend(drift_evidence)
            
            if "dataset_comparison" in evaluation_scope:
                comparison_evidence = self._evaluate_dataset_comparison(context)
                evidence_items.extend(comparison_evidence)
            
            if "anomaly_ranking" in evaluation_scope:
                anomaly_evidence = self._evaluate_anomalies(context)
                evidence_items.extend(anomaly_evidence)
            
            # Determine success
            success = assertions_failed == 0
            
            result.success = success
            result.status = ExecutionStatus.COMPLETED
            result.evidence = evidence_items
            result.metrics = {
                "assertions_passed": assertions_passed,
                "assertions_failed": assertions_failed,
                "total_assertions": assertions_passed + assertions_failed,
                **metrics_dict,
            }
            
            if not success:
                result.error_message = f"{assertions_failed} assertions failed"
                result.error_details = {"failed_assertions": assertions_failed}
            
        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.success = False
            result.error_message = str(e)
            result.error_details = {"exception_type": type(e).__name__}
        
        return result
    
    async def cleanup(self, context: ExecutionContext) -> bool:
        """
        Clean up model evaluation resources.
        
        Args:
            context: Execution context.
            
        Returns:
            True if cleanup successful, False otherwise.
        """
        try:
            self._config = None
            self._predictions = None
            self._labels = None
            self._probabilities = None
            return True
        except Exception as e:
            print(f"Model Evaluation plugin cleanup error: {e}")
            return False
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate Model Evaluation plugin configuration.
        
        Args:
            config: Configuration to validate.
            
        Returns:
            Tuple of (is_valid, error_messages).
        """
        errors = []
        
        model_type = config.get("model_type", "binary")
        if model_type not in ["binary", "multiclass"]:
            errors.append("Invalid model_type: must be 'binary' or 'multiclass'")
        
        threshold = config.get("threshold", 0.5)
        if not isinstance(threshold, (int, float)) or not (0 <= threshold <= 1):
            errors.append("Invalid threshold: must be between 0 and 1")
        
        num_classes = config.get("num_classes", 2)
        if not isinstance(num_classes, int) or num_classes < 2:
            errors.append("Invalid num_classes: must be at least 2")
        
        return (len(errors) == 0, errors)
    
    def _get_evaluation_scope(self, execution_path: ExecutionPath, config: Dict[str, Any]) -> List[str]:
        """
        Get evaluation scope based on execution path.
        
        Args:
            execution_path: The execution path.
            config: Plugin configuration.
            
        Returns:
            List of evaluation components to run.
        """
        scope_config = config.get("evaluation_scope", {})
        
        if execution_path == ExecutionPath.SMOKE:
            return scope_config.get("smoke", ["accuracy", "threshold"])
        elif execution_path == ExecutionPath.STANDARD:
            return scope_config.get("standard", ["accuracy", "precision", "recall", "f1", "confusion_matrix"])
        elif execution_path == ExecutionPath.DEEP:
            return scope_config.get("deep", [
                "accuracy", "precision", "recall", "f1", "confusion_matrix",
                "threshold_sweep", "calibration", "per_class"
            ])
        elif execution_path == ExecutionPath.INTELLIGENT:
            return scope_config.get("intelligent", [
                "accuracy", "precision", "recall", "f1", "confusion_matrix",
                "threshold_sweep", "calibration", "per_class",
                "drift_detection", "dataset_comparison", "anomaly_ranking"
            ])
        
        return ["accuracy"]
    
    def _evaluate_accuracy(
        self,
        context: ExecutionContext
    ) -> Tuple[float, List[EvidenceItem], int, int]:
        """Evaluate model accuracy."""
        threshold = context.config.get("threshold", 0.8)
        
        accuracy = accuracy_score(self._labels, self._predictions)
        
        evidence = [
            EvidenceItem(
                evidence_type=EvidenceType.METRIC,
                content={
                    "metric": "accuracy",
                    "value": float(accuracy),
                    "threshold": threshold,
                    "passed": accuracy >= threshold,
                },
                severity="critical" if accuracy < threshold else "info",
                source="model_evaluation",
            )
        ]
        
        passed = 1 if accuracy >= threshold else 0
        failed = 1 if accuracy < threshold else 0
        
        return accuracy, evidence, passed, failed
    
    def _evaluate_precision(
        self,
        context: ExecutionContext
    ) -> Tuple[float, List[EvidenceItem], int, int]:
        """Evaluate model precision."""
        threshold = context.config.get("precision_threshold", 0.7)
        average = "binary" if self._config.model_type == "binary" else "weighted"
        
        try:
            precision = precision_score(self._labels, self._predictions, average=average, zero_division=0)
        except Exception:
            precision = 0.0
        
        evidence = [
            EvidenceItem(
                evidence_type=EvidenceType.METRIC,
                content={
                    "metric": "precision",
                    "value": float(precision),
                    "threshold": threshold,
                    "average": average,
                    "passed": precision >= threshold,
                },
                severity="critical" if precision < threshold else "info",
                source="model_evaluation",
            )
        ]
        
        passed = 1 if precision >= threshold else 0
        failed = 1 if precision < threshold else 0
        
        return precision, evidence, passed, failed
    
    def _evaluate_recall(
        self,
        context: ExecutionContext
    ) -> Tuple[float, List[EvidenceItem], int, int]:
        """Evaluate model recall."""
        threshold = context.config.get("recall_threshold", 0.7)
        average = "binary" if self._config.model_type == "binary" else "weighted"
        
        try:
            recall = recall_score(self._labels, self._predictions, average=average, zero_division=0)
        except Exception:
            recall = 0.0
        
        evidence = [
            EvidenceItem(
                evidence_type=EvidenceType.METRIC,
                content={
                    "metric": "recall",
                    "value": float(recall),
                    "threshold": threshold,
                    "average": average,
                    "passed": recall >= threshold,
                },
                severity="critical" if recall < threshold else "info",
                source="model_evaluation",
            )
        ]
        
        passed = 1 if recall >= threshold else 0
        failed = 1 if recall < threshold else 0
        
        return recall, evidence, passed, failed
    
    def _evaluate_f1(
        self,
        context: ExecutionContext
    ) -> Tuple[float, List[EvidenceItem], int, int]:
        """Evaluate model F1 score."""
        threshold = context.config.get("f1_threshold", 0.7)
        average = "binary" if self._config.model_type == "binary" else "weighted"
        
        try:
            f1 = f1_score(self._labels, self._predictions, average=average, zero_division=0)
        except Exception:
            f1 = 0.0
        
        evidence = [
            EvidenceItem(
                evidence_type=EvidenceType.METRIC,
                content={
                    "metric": "f1",
                    "value": float(f1),
                    "threshold": threshold,
                    "average": average,
                    "passed": f1 >= threshold,
                },
                severity="critical" if f1 < threshold else "info",
                source="model_evaluation",
            )
        ]
        
        passed = 1 if f1 >= threshold else 0
        failed = 1 if f1 < threshold else 0
        
        return f1, evidence, passed, failed
    
    def _evaluate_confusion_matrix(self, context: ExecutionContext) -> List[EvidenceItem]:
        """Evaluate and collect confusion matrix."""
        cm = confusion_matrix(self._labels, self._predictions)
        
        evidence = [
            EvidenceItem(
                evidence_type=EvidenceType.METRIC,
                content={
                    "metric": "confusion_matrix",
                    "matrix": cm.tolist(),
                    "num_classes": self._config.num_classes,
                },
                severity="info",
                source="model_evaluation",
            )
        ]
        
        return evidence
    
    def _evaluate_threshold_sweep(self, context: ExecutionContext) -> List[EvidenceItem]:
        """Evaluate threshold sweep (for binary classification)."""
        if self._config.model_type != "binary" or self._probabilities is None:
            return []
        
        thresholds = np.linspace(0, 1, 100)
        precisions = []
        recalls = []
        f1s = []
        
        for threshold in thresholds:
            preds = (self._probabilities >= threshold).astype(int)
            precisions.append(precision_score(self._labels, preds, zero_division=0))
            recalls.append(recall_score(self._labels, preds, zero_division=0))
            f1s.append(f1_score(self._labels, preds, zero_division=0))
        
        evidence = [
            EvidenceItem(
                evidence_type=EvidenceType.METRIC,
                content={
                    "metric": "threshold_sweep",
                    "thresholds": thresholds.tolist(),
                    "precisions": precisions,
                    "recalls": recalls,
                    "f1s": f1s,
                    "optimal_threshold": float(thresholds[np.argmax(f1s)]),
                },
                severity="info",
                source="model_evaluation",
            )
        ]
        
        return evidence
    
    def _evaluate_calibration(self, context: ExecutionContext) -> List[EvidenceItem]:
        """Evaluate model calibration."""
        if self._probabilities is None:
            return []
        
        try:
            prob_true, prob_pred = calibration_curve(
                self._labels,
                self._probabilities,
                n_bins=self._config.calibration_bins,
            )
            
            evidence = [
                EvidenceItem(
                    evidence_type=EvidenceType.METRIC,
                    content={
                        "metric": "calibration",
                        "prob_true": prob_true.tolist(),
                        "prob_pred": prob_pred.tolist(),
                        "num_bins": self._config.calibration_bins,
                    },
                    severity="info",
                    source="model_evaluation",
                )
            ]
        except Exception:
            evidence = []
        
        return evidence
    
    def _evaluate_per_class(self, context: ExecutionContext) -> Tuple[Dict[str, Any], List[EvidenceItem]]:
        """Evaluate per-class metrics."""
        if self._config.model_type == "binary":
            return {}, []
        
        try:
            precision_per_class = precision_score(
                self._labels, self._predictions, average=None, zero_division=0
            )
            recall_per_class = recall_score(
                self._labels, self._predictions, average=None, zero_division=0
            )
            f1_per_class = f1_score(
                self._labels, self._predictions, average=None, zero_division=0
            )
            
            per_class_metrics = {
                "precision": precision_per_class.tolist(),
                "recall": recall_per_class.tolist(),
                "f1": f1_per_class.tolist(),
            }
            
            evidence = [
                EvidenceItem(
                    evidence_type=EvidenceType.METRIC,
                    content={
                        "metric": "per_class_metrics",
                        "per_class_metrics": per_class_metrics,
                        "num_classes": self._config.num_classes,
                    },
                    severity="info",
                    source="model_evaluation",
                )
            ]
        except Exception:
            per_class_metrics = {}
            evidence = []
        
        return per_class_metrics, evidence
    
    def _evaluate_drift(self, context: ExecutionContext) -> List[EvidenceItem]:
        """Evaluate model drift (placeholder for actual drift detection)."""
        # In a real implementation, this would compare with baseline metrics
        # For now, we'll create placeholder evidence
        
        baseline_accuracy = context.config.get("baseline_accuracy", 0.85)
        current_accuracy = accuracy_score(self._labels, self._predictions)
        drift = baseline_accuracy - current_accuracy
        
        evidence = [
            EvidenceItem(
                evidence_type=EvidenceType.ASSERTION,
                content={
                    "assertion": "drift_detection",
                    "baseline_accuracy": baseline_accuracy,
                    "current_accuracy": float(current_accuracy),
                    "drift": float(drift),
                    "drift_threshold": context.config.get("drift_threshold", 0.05),
                    "passed": drift <= context.config.get("drift_threshold", 0.05),
                },
                severity="high" if drift > context.config.get("drift_threshold", 0.05) else "info",
                source="model_evaluation",
            )
        ]
        
        return evidence
    
    def _evaluate_dataset_comparison(self, context: ExecutionContext) -> List[EvidenceItem]:
        """Evaluate dataset comparison (placeholder)."""
        # In a real implementation, this would compare feature distributions
        evidence = [
            EvidenceItem(
                evidence_type=EvidenceType.METRIC,
                content={
                    "metric": "dataset_comparison",
                    "num_samples": len(self._labels),
                    "num_features": context.config.get("num_features", 0),
                },
                severity="info",
                source="model_evaluation",
            )
        ]
        
        return evidence
    
    def _evaluate_anomalies(self, context: ExecutionContext) -> List[EvidenceItem]:
        """Evaluate anomaly ranking (placeholder)."""
        # In a real implementation, this would identify anomalous predictions
        if self._probabilities is None:
            return []
        
        # Simple anomaly detection: low confidence predictions
        confidence = np.max(self._probabilities, axis=1) if self._probabilities.ndim > 1 else self._probabilities
        low_confidence_indices = np.where(confidence < 0.5)[0]
        
        evidence = [
            EvidenceItem(
                evidence_type=EvidenceType.ASSERTION,
                content={
                    "assertion": "anomaly_ranking",
                    "low_confidence_count": int(len(low_confidence_indices)),
                    "low_confidence_indices": low_confidence_indices.tolist()[:10],  # Limit to 10
                    "total_samples": len(self._labels),
                },
                severity="info",
                source="model_evaluation",
            )
        ]
        
        return evidence
