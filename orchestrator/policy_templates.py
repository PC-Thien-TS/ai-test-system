"""Escalation policy templates and recommendation engine."""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


class PolicyTemplateType(Enum):
    """Types of policy templates."""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    CUSTOM = "custom"


@dataclass
class PolicyTemplate:
    """Template for escalation policy configuration."""
    template_id: str
    template_type: PolicyTemplateType
    name: str
    description: str
    product_types: List[str]
    configuration: dict
    
    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "template_type": self.template_type.value,
            "name": self.name,
            "description": self.description,
            "product_types": self.product_types,
            "configuration": self.configuration,
        }


@dataclass
class PolicyRecommendation:
    """Recommended policy configuration."""
    recommended_config: dict
    confidence: float  # 0.0 to 1.0
    reasons: List[str]
    alternative_templates: List[str]
    
    def to_dict(self) -> dict:
        return {
            "recommended_config": self.recommended_config,
            "confidence": self.confidence,
            "reasons": self.reasons,
            "alternative_templates": self.alternative_templates,
        }


class PolicyTemplateEngine:
    """Engine for managing and recommending escalation policy templates."""

    def __init__(self):
        self._templates = self._initialize_default_templates()

    def _initialize_default_templates(self) -> Dict[str, PolicyTemplate]:
        """Initialize default policy templates."""
        templates = {}

        # Conservative template - high thresholds, low escalation
        templates["conservative_web"] = PolicyTemplate(
            template_id="conservative_web",
            template_type=PolicyTemplateType.CONSERVATIVE,
            name="Conservative Web Testing",
            description="Minimize escalations with high thresholds. Best for stable production systems.",
            product_types=["web", "api"],
            configuration={
                "fallback_threshold": 0.7,
                "confidence_threshold": 0.85,
                "max_escalation_depth": 2,
                "auto_escalate_on_fail": True,
                "auto_escalate_on_flaky": False,
                "plugin_overrides": {},
            }
        )

        # Balanced template - moderate thresholds
        templates["balanced_web"] = PolicyTemplate(
            template_id="balanced_web",
            template_type=PolicyTemplateType.BALANCED,
            name="Balanced Web Testing",
            description="Balanced approach with moderate thresholds. Good for most development environments.",
            product_types=["web", "api", "workflow", "data_pipeline"],
            configuration={
                "fallback_threshold": 0.5,
                "confidence_threshold": 0.7,
                "max_escalation_depth": 3,
                "auto_escalate_on_fail": True,
                "auto_escalate_on_flaky": True,
                "plugin_overrides": {},
            }
        )

        # Aggressive template - low thresholds, quick escalation
        templates["aggressive_model"] = PolicyTemplate(
            template_id="aggressive_model",
            template_type=PolicyTemplateType.AGGRESSIVE,
            name="Aggressive Model Testing",
            description="Quick escalation to ensure thorough testing. Best for experimental or rapidly changing systems.",
            product_types=["model", "rag", "llm_app"],
            configuration={
                "fallback_threshold": 0.3,
                "confidence_threshold": 0.5,
                "max_escalation_depth": 5,
                "auto_escalate_on_fail": True,
                "auto_escalate_on_flaky": True,
                "plugin_overrides": {},
            }
        )

        # API-specific template
        templates["api_strict"] = PolicyTemplate(
            template_id="api_strict",
            template_type=PolicyTemplateType.CONSERVATIVE,
            name="Strict API Testing",
            description="Strict thresholds for API contracts to ensure reliability.",
            product_types=["api"],
            configuration={
                "fallback_threshold": 0.4,
                "confidence_threshold": 0.8,
                "max_escalation_depth": 2,
                "auto_escalate_on_fail": True,
                "auto_escalate_on_flaky": False,
                "plugin_overrides": {
                    "api_contract": {
                        "fallback_threshold": 0.3,
                        "confidence_threshold": 0.9,
                    }
                },
            }
        )

        # Model-specific template
        templates["model_comprehensive"] = PolicyTemplate(
            template_id="model_comprehensive",
            template_type=PolicyTemplateType.BALANCED,
            name="Comprehensive Model Testing",
            description="Thorough testing for ML models with confidence-based escalation.",
            product_types=["model", "rag", "llm_app"],
            configuration={
                "fallback_threshold": 0.5,
                "confidence_threshold": 0.6,
                "max_escalation_depth": 4,
                "auto_escalate_on_fail": True,
                "auto_escalate_on_flaky": True,
                "plugin_overrides": {
                    "model_eval": {
                        "confidence_threshold": 0.55,
                        "max_escalation_depth": 5,
                    }
                },
            }
        )

        return templates

    def get_template(self, template_id: str) -> Optional[PolicyTemplate]:
        """Get a specific template by ID."""
        return self._templates.get(template_id)

    def list_templates(self, product_type: Optional[str] = None) -> List[PolicyTemplate]:
        """List available templates, optionally filtered by product type."""
        if product_type:
            return [t for t in self._templates.values() if product_type in t.product_types]
        return list(self._templates.values())

    def recommend_policy(
        self,
        product_type: str,
        historical_runs: Optional[List[dict]] = None,
        stability_score: Optional[float] = None,
        team_preferences: Optional[dict] = None,
    ) -> PolicyRecommendation:
        """
        Recommend a policy configuration based on project characteristics.

        Args:
            product_type: The project's product type.
            historical_runs: Historical run data for the project.
            stability_score: Stability score (0.0 to 1.0) if available.
            team_preferences: Team preferences (e.g., "conservative", "balanced", "aggressive").

        Returns:
            PolicyRecommendation with recommended configuration and confidence.
        """
        reasons = []
        confidence = 0.7
        recommended_config = {}
        alternative_templates = []

        # Check for team preferences
        if team_preferences:
            preference = team_preferences.get("escalation_preference", "balanced")
            template = self._find_template_by_preference(preference, product_type)
            if template:
                recommended_config = template.configuration.copy()
                reasons.append(f"Based on team preference: {preference}")
                confidence = 0.8
                alternative_templates = [t.template_id for t in self._templates.values() if t.template_id != template.template_id]
        else:
            # Use product type as primary factor
            product_templates = self.list_templates(product_type)
            if product_templates:
                # Prefer balanced templates
                balanced = [t for t in product_templates if t.template_type == PolicyTemplateType.BALANCED]
                if balanced:
                    recommended_config = balanced[0].configuration.copy()
                    reasons.append(f"Balanced policy recommended for {product_type}")
                else:
                    recommended_config = product_templates[0].configuration.copy()
                    reasons.append(f"Default policy for {product_type}")
                alternative_templates = [t.template_id for t in product_templates[1:]]
            else:
                # Fallback to general balanced template
                recommended_config = self._templates["balanced_web"].configuration.copy()
                reasons.append("Using general balanced policy as fallback")
                alternative_templates = [t.template_id for t in self._templates.values()]

        # Adjust based on stability score
        if stability_score is not None:
            if stability_score < 0.5:
                # Low stability - use more aggressive escalation
                recommended_config["fallback_threshold"] = max(recommended_config["fallback_threshold"] - 0.2, 0.2)
                recommended_config["confidence_threshold"] = max(recommended_config["confidence_threshold"] - 0.2, 0.3)
                recommended_config["max_escalation_depth"] = min(recommended_config["max_escalation_depth"] + 1, 5)
                reasons.append("Adjusted for low stability: lowered thresholds")
                confidence = 0.6
            elif stability_score > 0.8:
                # High stability - use more conservative escalation
                recommended_config["fallback_threshold"] = min(recommended_config["fallback_threshold"] + 0.1, 0.9)
                recommended_config["confidence_threshold"] = min(recommended_config["confidence_threshold"] + 0.1, 0.95)
                reasons.append("Adjusted for high stability: raised thresholds")
                confidence = 0.9

        # Adjust based on historical data
        if historical_runs:
            escalation_rate = sum(1 for r in historical_runs if r.get("escalated", False)) / len(historical_runs)
            
            if escalation_rate > 0.5:
                # High escalation rate - adjust thresholds
                recommended_config["fallback_threshold"] = min(recommended_config["fallback_threshold"] + 0.15, 0.85)
                recommended_config["confidence_threshold"] = min(recommended_config["confidence_threshold"] + 0.15, 0.9)
                reasons.append(f"Adjusted for high historical escalation rate: {escalation_rate:.1%}")
                confidence = 0.85
            elif escalation_rate < 0.1:
                # Low escalation rate - could be too conservative
                recommended_config["fallback_threshold"] = max(recommended_config["fallback_threshold"] - 0.1, 0.3)
                recommended_config["confidence_threshold"] = max(recommended_config["confidence_threshold"] - 0.1, 0.5)
                reasons.append(f"Adjusted for low historical escalation rate: {escalation_rate:.1%}")
                confidence = 0.75

        return PolicyRecommendation(
            recommended_config=recommended_config,
            confidence=confidence,
            reasons=reasons,
            alternative_templates=alternative_templates,
        )

    def _find_template_by_preference(self, preference: str, product_type: str) -> Optional[PolicyTemplate]:
        """Find a template matching the given preference and product type."""
        preference_map = {
            "conservative": PolicyTemplateType.CONSERVATIVE,
            "balanced": PolicyTemplateType.BALANCED,
            "aggressive": PolicyTemplateType.AGGRESSIVE,
        }
        
        template_type = preference_map.get(preference)
        if not template_type:
            return None

        product_templates = self.list_templates(product_type)
        matching = [t for t in product_templates if t.template_type == template_type]
        
        return matching[0] if matching else None

    def create_custom_template(
        self,
        name: str,
        description: str,
        configuration: dict,
        product_types: List[str],
    ) -> PolicyTemplate:
        """
        Create a custom policy template.

        Args:
            name: Template name.
            description: Template description.
            configuration: Policy configuration.
            product_types: Applicable product types.

        Returns:
            The created PolicyTemplate.
        """
        template_id = f"custom_{name.lower().replace(' ', '_')}_{hash(name)}"
        
        template = PolicyTemplate(
            template_id=template_id,
            template_type=PolicyTemplateType.CUSTOM,
            name=name,
            description=description,
            product_types=product_types,
            configuration=configuration,
        )
        
        self._templates[template_id] = template
        return template

    def validate_configuration(self, configuration: dict) -> tuple[bool, List[str]]:
        """
        Validate a policy configuration.

        Args:
            configuration: The configuration to validate.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        errors = []

        # Validate fallback threshold
        fallback = configuration.get("fallback_threshold")
        if fallback is None:
            errors.append("Missing fallback_threshold")
        elif not isinstance(fallback, (int, float)) or fallback < 0 or fallback > 1:
            errors.append("fallback_threshold must be between 0.0 and 1.0")

        # Validate confidence threshold
        confidence = configuration.get("confidence_threshold")
        if confidence is None:
            errors.append("Missing confidence_threshold")
        elif not isinstance(confidence, (int, float)) or confidence < 0 or confidence > 1:
            errors.append("confidence_threshold must be between 0.0 and 1.0")

        # Validate max escalation depth
        max_depth = configuration.get("max_escalation_depth")
        if max_depth is None:
            errors.append("Missing max_escalation_depth")
        elif not isinstance(max_depth, int) or max_depth < 1 or max_depth > 10:
            errors.append("max_escalation_depth must be an integer between 1 and 10")

        # Validate boolean fields
        for field in ["auto_escalate_on_fail", "auto_escalate_on_flaky"]:
            value = configuration.get(field)
            if value is not None and not isinstance(value, bool):
                errors.append(f"{field} must be a boolean")

        # Validate plugin overrides
        plugin_overrides = configuration.get("plugin_overrides", {})
        if not isinstance(plugin_overrides, dict):
            errors.append("plugin_overrides must be a dictionary")

        return (len(errors) == 0, errors)
