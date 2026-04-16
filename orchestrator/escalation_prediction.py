"""Escalation prediction module for predicting escalation likelihood and paths."""

from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

from orchestrator.models import ExecutionPath


class PredictionConfidence(Enum):
    """Confidence levels for predictions."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class EscalationPrediction:
    """Prediction for escalation likelihood and path."""
    run_id: str
    escalation_likelihood: float  # 0.0 to 1.0
    predicted_path: Optional[ExecutionPath]
    prediction_confidence: PredictionConfidence
    reasons: List[str]
    timestamp: str
    
    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "escalation_likelihood": self.escalation_likelihood,
            "predicted_path": self.predicted_path.value if self.predicted_path else None,
            "prediction_confidence": self.prediction_confidence.value,
            "reasons": self.reasons,
            "timestamp": self.timestamp,
        }


@dataclass
class RiskFactor:
    """Risk factor contributing to escalation prediction."""
    factor_name: str
    impact: float  # 0.0 to 1.0
    description: str
    
    def to_dict(self) -> dict:
        return {
            "factor_name": self.factor_name,
            "impact": self.impact,
            "description": self.description,
        }


class EscalationPredictor:
    """Predicts escalation likelihood and recommends execution paths."""

    def __init__(self):
        self._risk_weights = {
            "fallback_ratio": 0.3,
            "confidence_score": 0.25,
            "flaky_history": 0.2,
            "gate_failure": 0.15,
            "escalation_depth": 0.1,
        }
        self._path_escalation_threshold = 0.4

    def predict_escalation(
        self,
        run_id: str,
        fallback_ratio: float,
        confidence_score: float,
        gate_result: Optional[str],
        execution_path: ExecutionPath,
        flaky_history: List[bool],
        escalation_depth: int = 0,
        project_policy: Optional[dict] = None,
    ) -> EscalationPrediction:
        """
        Predict escalation likelihood and recommended path.

        Args:
            run_id: The run ID.
            fallback_ratio: Current fallback ratio.
            confidence_score: Current confidence score.
            gate_result: Current gate result.
            execution_path: Current execution path.
            flaky_history: History of flaky results for this project.
            escalation_depth: Current escalation depth.
            project_policy: Project escalation policy if configured.

        Returns:
            EscalationPrediction with likelihood, path, and confidence.
        """
        risk_factors = self._calculate_risk_factors(
            fallback_ratio,
            confidence_score,
            gate_result,
            flaky_history,
            escalation_depth,
            project_policy,
        )

        escalation_likelihood = self._calculate_escalation_likelihood(risk_factors)
        predicted_path = self._predict_next_path(execution_path, escalation_likelihood, escalation_depth)
        prediction_confidence = self._determine_confidence(risk_factors, escalation_likelihood)
        reasons = self._generate_reasons(risk_factors, escalation_likelihood, predicted_path)

        return EscalationPrediction(
            run_id=run_id,
            escalation_likelihood=escalation_likelihood,
            predicted_path=predicted_path,
            prediction_confidence=prediction_confidence,
            reasons=reasons,
            timestamp=datetime.utcnow().isoformat(),
        )

    def _calculate_risk_factors(
        self,
        fallback_ratio: float,
        confidence_score: float,
        gate_result: Optional[str],
        flaky_history: List[bool],
        escalation_depth: int,
        project_policy: Optional[dict],
    ) -> Dict[str, RiskFactor]:
        """Calculate risk factors contributing to escalation."""
        factors = {}

        # Fallback ratio risk
        fallback_threshold = project_policy.get("fallback_threshold", 0.5) if project_policy else 0.5
        if fallback_ratio > fallback_threshold:
            impact = min((fallback_ratio - fallback_threshold) / (1.0 - fallback_threshold), 1.0)
            factors["fallback_ratio"] = RiskFactor(
                factor_name="fallback_ratio",
                impact=impact,
                description=f"Fallback ratio ({fallback_ratio:.2f}) exceeds threshold ({fallback_threshold})",
            )
        else:
            factors["fallback_ratio"] = RiskFactor(
                factor_name="fallback_ratio",
                impact=0.0,
                description=f"Fallback ratio ({fallback_ratio:.2f}) within threshold",
            )

        # Confidence score risk
        confidence_threshold = project_policy.get("confidence_threshold", 0.7) if project_policy else 0.7
        if confidence_score < confidence_threshold:
            impact = min((confidence_threshold - confidence_score) / confidence_threshold, 1.0)
            factors["confidence_score"] = RiskFactor(
                factor_name="confidence_score",
                impact=impact,
                description=f"Confidence score ({confidence_score:.2f}) below threshold ({confidence_threshold})",
            )
        else:
            factors["confidence_score"] = RiskFactor(
                factor_name="confidence_score",
                impact=0.0,
                description=f"Confidence score ({confidence_score:.2f}) meets threshold",
            )

        # Gate failure risk
        if gate_result == "fail":
            factors["gate_failure"] = RiskFactor(
                factor_name="gate_failure",
                impact=1.0,
                description="Gate test failed",
            )
        elif gate_result == "flaky":
            factors["gate_failure"] = RiskFactor(
                factor_name="gate_failure",
                impact=0.6,
                description="Gate test is flaky",
            )
        else:
            factors["gate_failure"] = RiskFactor(
                factor_name="gate_failure",
                impact=0.0,
                description="Gate test passed",
            )

        # Flaky history risk
        if flaky_history:
            flaky_rate = sum(flaky_history) / len(flaky_history)
            factors["flaky_history"] = RiskFactor(
                factor_name="flaky_history",
                impact=flaky_rate,
                description=f"Flaky rate: {flaky_rate:.1%}",
            )
        else:
            factors["flaky_history"] = RiskFactor(
                factor_name="flaky_history",
                impact=0.0,
                description="No flaky history available",
            )

        # Escalation depth risk (deeper escalations are riskier)
        max_depth = project_policy.get("max_escalation_depth", 3) if project_policy else 3
        if escalation_depth >= max_depth:
            factors["escalation_depth"] = RiskFactor(
                factor_name="escalation_depth",
                impact=1.0,
                description=f"Maximum escalation depth ({max_depth}) reached",
            )
        else:
            depth_risk = escalation_depth / max_depth
            factors["escalation_depth"] = RiskFactor(
                factor_name="escalation_depth",
                impact=depth_risk,
                description=f"Escalation depth: {escalation_depth}/{max_depth}",
            )

        return factors

    def _calculate_escalation_likelihood(self, risk_factors: Dict[str, RiskFactor]) -> float:
        """Calculate overall escalation likelihood from risk factors."""
        weighted_sum = 0.0
        total_weight = 0.0

        for factor_name, factor in risk_factors.items():
            weight = self._risk_weights.get(factor_name, 0.1)
            weighted_sum += factor.impact * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        return min(weighted_sum / total_weight, 1.0)

    def _predict_next_path(
        self,
        current_path: ExecutionPath,
        escalation_likelihood: float,
        escalation_depth: int,
    ) -> Optional[ExecutionPath]:
        """Predict the next execution path if escalation occurs."""
        if escalation_likelihood < self._path_escalation_threshold:
            return None  # Not likely to escalate

        path_order = [ExecutionPath.SMOKE, ExecutionPath.STANDARD, ExecutionPath.DEEP, ExecutionPath.INTELLIGENT]
        
        try:
            current_index = path_order.index(current_path)
        except ValueError:
            return ExecutionPath.STANDARD

        if current_index < len(path_order) - 1:
            return path_order[current_index + 1]
        
        return None  # Already at maximum path

    def _determine_confidence(
        self,
        risk_factors: Dict[str, RiskFactor],
        escalation_likelihood: float,
    ) -> PredictionConfidence:
        """Determine confidence level for the prediction."""
        # Count how many factors have high impact
        high_impact_count = sum(1 for f in risk_factors.values() if f.impact > 0.7)
        medium_impact_count = sum(1 for f in risk_factors.values() if 0.3 < f.impact <= 0.7)

        if high_impact_count >= 2 or (high_impact_count >= 1 and escalation_likelihood > 0.8):
            return PredictionConfidence.HIGH
        elif high_impact_count >= 1 or medium_impact_count >= 2:
            return PredictionConfidence.MEDIUM
        else:
            return PredictionConfidence.LOW

    def _generate_reasons(
        self,
        risk_factors: Dict[str, RiskFactor],
        escalation_likelihood: float,
        predicted_path: Optional[ExecutionPath],
    ) -> List[str]:
        """Generate human-readable reasons for the prediction."""
        reasons = []

        # Add high-impact factors
        for factor in risk_factors.values():
            if factor.impact > 0.3:
                reasons.append(factor.description)

        # Add escalation likelihood context
        if escalation_likelihood > 0.8:
            reasons.append("High escalation likelihood detected")
        elif escalation_likelihood > 0.5:
            reasons.append("Moderate escalation likelihood")
        else:
            reasons.append("Low escalation likelihood")

        # Add predicted path context
        if predicted_path:
            reasons.append(f"Recommended escalation path: {predicted_path.value}")
        else:
            reasons.append("No escalation recommended")

        return reasons

    def get_policy_recommendation(
        self,
        project_runs: List[dict],
        product_type: str,
    ) -> dict:
        """
        Generate recommended escalation policy based on historical patterns.

        Args:
            project_runs: Historical run data for the project.
            product_type: The project's product type.

        Returns:
            Recommended policy configuration.
        """
        if not project_runs:
            return self._get_default_policy_template(product_type)

        # Calculate historical metrics
        fallback_ratios = [r.get("fallback_ratio", 0) for r in project_runs if r.get("fallback_ratio") is not None]
        confidence_scores = [r.get("confidence_score", 0) for r in project_runs if r.get("confidence_score") is not None]
        escalation_rates = [r.get("escalated", False) for r in project_runs]

        avg_fallback = sum(fallback_ratios) / len(fallback_ratios) if fallback_ratios else 0.5
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.7
        escalation_rate = sum(escalation_rates) / len(escalation_rates) if escalation_rates else 0.0

        # Adjust thresholds based on historical patterns
        recommended_fallback_threshold = min(avg_fallback * 1.2, 0.8)  # 20% buffer
        recommended_confidence_threshold = max(avg_confidence * 0.9, 0.5)  # 10% tolerance

        return {
            "fallback_threshold": recommended_fallback_threshold,
            "confidence_threshold": recommended_confidence_threshold,
            "max_escalation_depth": 3 if escalation_rate < 0.3 else 5,
            "auto_escalate_on_fail": True,
            "auto_escalate_on_flaky": escalation_rate > 0.2,
            "plugin_overrides": {},
            "based_on_historical_data": True,
            "historical_metrics": {
                "avg_fallback_ratio": avg_fallback,
                "avg_confidence_score": avg_confidence,
                "escalation_rate": escalation_rate,
                "total_runs": len(project_runs),
            },
        }

    def _get_default_policy_template(self, product_type: str) -> dict:
        """Get default policy template based on product type."""
        templates = {
            "web": {
                "fallback_threshold": 0.5,
                "confidence_threshold": 0.7,
                "max_escalation_depth": 3,
                "auto_escalate_on_fail": True,
                "auto_escalate_on_flaky": True,
                "plugin_overrides": {},
            },
            "api": {
                "fallback_threshold": 0.4,
                "confidence_threshold": 0.8,
                "max_escalation_depth": 2,
                "auto_escalate_on_fail": True,
                "auto_escalate_on_flaky": False,
                "plugin_overrides": {},
            },
            "model": {
                "fallback_threshold": 0.6,
                "confidence_threshold": 0.6,
                "max_escalation_depth": 4,
                "auto_escalate_on_fail": True,
                "auto_escalate_on_flaky": True,
                "plugin_overrides": {},
            },
            "rag": {
                "fallback_threshold": 0.5,
                "confidence_threshold": 0.75,
                "max_escalation_depth": 3,
                "auto_escalate_on_fail": True,
                "auto_escalate_on_flaky": True,
                "plugin_overrides": {},
            },
            "llm_app": {
                "fallback_threshold": 0.55,
                "confidence_threshold": 0.7,
                "max_escalation_depth": 4,
                "auto_escalate_on_fail": True,
                "auto_escalate_on_flaky": True,
                "plugin_overrides": {},
            },
            "workflow": {
                "fallback_threshold": 0.4,
                "confidence_threshold": 0.8,
                "max_escalation_depth": 2,
                "auto_escalate_on_fail": True,
                "auto_escalate_on_flaky": False,
                "plugin_overrides": {},
            },
            "data_pipeline": {
                "fallback_threshold": 0.5,
                "confidence_threshold": 0.75,
                "max_escalation_depth": 3,
                "auto_escalate_on_fail": True,
                "auto_escalate_on_flaky": False,
                "plugin_overrides": {},
            },
        }

        return templates.get(product_type, templates["web"])
