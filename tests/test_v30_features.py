"""Tests for v3.0 prediction, recommendation, and evidence analysis features."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from orchestrator.models import ExecutionPath, GateResult
from orchestrator.evidence_analysis import (
    EvidenceAnalyzer,
    Anomaly,
    AnomalySeverity,
    EvidencePattern,
    EvidenceRanking,
)
from orchestrator.escalation_prediction import (
    EscalationPredictor,
    EscalationPrediction,
    PredictionConfidence,
)
from orchestrator.policy_templates import (
    PolicyTemplateEngine,
    PolicyTemplate,
    PolicyTemplateType,
    PolicyRecommendation,
)
from orchestrator.escalation_analytics import (
    EscalationAnalytics,
    CrossProjectPattern,
    FailureMode,
    TimeToStableTrend,
    TrendDirection,
)


def test_evidence_analyzer_anomaly_detection():
    """Test evidence analyzer anomaly detection."""
    analyzer = EvidenceAnalyzer()
    
    evidence_items = [
        {
            "id": "ev1",
            "type": "trace",
            "content": {"status_code": 500, "duration": 5000},
        },
        {
            "id": "ev2",
            "type": "screenshot",
            "content": {"diff_score": 0.15},
        },
        {
            "id": "ev3",
            "type": "trace",
            "content": {"status_code": 200, "duration": 100},
        },
    ]
    
    result = analyzer.analyze_evidence(evidence_items)
    
    assert "anomalies" in result
    assert len(result["anomalies"]) >= 1
    assert result["summary"]["total_evidence"] == 3
    
    # Check for HTTP 500 anomaly
    http_anomalies = [a for a in result["anomalies"] if a["anomaly_type"] == "unexpected_response"]
    assert any(a["severity"] == "critical" for a in http_anomalies)


def test_evidence_anomaly_severity_levels():
    """Test different severity levels for anomalies."""
    analyzer = EvidenceAnalyzer()
    
    # Critical severity
    evidence = [{"id": "ev1", "type": "trace", "content": {"status_code": 500}}]
    result = analyzer.analyze_evidence(evidence)
    assert any(a["severity"] == "critical" for a in result["anomalies"])
    
    # High severity
    evidence = [{"id": "ev1", "type": "trace", "content": {"status_code": 404}}]
    result = analyzer.analyze_evidence(evidence)
    assert any(a["severity"] == "high" for a in result["anomalies"])


def test_evidence_pattern_grouping():
    """Test evidence pattern grouping."""
    analyzer = EvidenceAnalyzer()
    
    evidence_items = [
        {"id": "ev1", "type": "trace", "content": {"error": "Connection refused", "url": "/api/test"}},
        {"id": "ev2", "type": "trace", "content": {"error": "Connection refused", "url": "/api/users"}},
        {"id": "ev3", "type": "trace", "content": {"error": "Connection refused", "url": "/api/data"}},
    ]
    
    result = analyzer.analyze_evidence(evidence_items)
    
    assert "patterns" in result
    error_patterns = [p for p in result["patterns"] if p["pattern_type"] == "error_pattern"]
    assert len(error_patterns) >= 1
    assert error_patterns[0]["frequency"] == 3


def test_evidence_suspicious_ranking():
    """Test evidence suspiciousness ranking."""
    analyzer = EvidenceAnalyzer()
    
    evidence_items = [
        {"id": "ev1", "type": "trace", "content": {"status_code": 500}},
        {"id": "ev2", "type": "trace", "content": {"status_code": 200}},
        {"id": "ev3", "type": "trace", "content": {"status_code": 500, "duration": 15000}},
    ]
    
    result = analyzer.analyze_evidence(evidence_items)
    
    assert "rankings" in result
    assert len(result["rankings"]) >= 2
    
    # Highest ranked should have highest score
    rankings = result["rankings"]
    assert rankings[0]["rank"] == 1
    assert rankings[0]["suspicious_score"] >= rankings[1]["suspicious_score"]


def test_escalation_prediction_likelihood():
    """Test escalation likelihood prediction."""
    predictor = EscalationPredictor()
    
    prediction = predictor.predict_escalation(
        run_id="run-1",
        fallback_ratio=0.8,
        confidence_score=0.5,
        gate_result="fail",
        execution_path=ExecutionPath.STANDARD,
        flaky_history=[False, False, True],
        escalation_depth=1,
    )
    
    assert isinstance(prediction, EscalationPrediction)
    assert prediction.run_id == "run-1"
    assert 0.0 <= prediction.escalation_likelihood <= 1.0
    assert len(prediction.reasons) > 0


def test_escalation_prediction_high_likelihood():
    """Test high escalation likelihood scenario."""
    predictor = EscalationPredictor()
    
    prediction = predictor.predict_escalation(
        run_id="run-1",
        fallback_ratio=0.9,
        confidence_score=0.3,
        gate_result="fail",
        execution_path=ExecutionPath.SMOKE,
        flaky_history=[True, True, True],
        escalation_depth=0,
    )
    
    assert prediction.escalation_likelihood > 0.7
    assert prediction.prediction_confidence in [PredictionConfidence.HIGH, PredictionConfidence.MEDIUM]


def test_escalation_prediction_low_likelihood():
    """Test low escalation likelihood scenario."""
    predictor = EscalationPredictor()
    
    prediction = predictor.predict_escalation(
        run_id="run-1",
        fallback_ratio=0.2,
        confidence_score=0.9,
        gate_result="pass",
        execution_path=ExecutionPath.STANDARD,
        flaky_history=[False, False, False],
        escalation_depth=0,
    )
    
    assert prediction.escalation_likelihood < 0.5
    assert prediction.predicted_path is None


def test_escalation_path_prediction():
    """Test predicted escalation path."""
    predictor = EscalationPredictor()
    
    # Predict from smoke to standard
    prediction = predictor.predict_escalation(
        run_id="run-1",
        fallback_ratio=0.8,
        confidence_score=0.5,
        gate_result="fail",
        execution_path=ExecutionPath.SMOKE,
        flaky_history=[],
        escalation_depth=0,
    )
    
    assert prediction.predicted_path == ExecutionPath.STANDARD
    
    # Predict from standard to deep
    prediction = predictor.predict_escalation(
        run_id="run-2",
        fallback_ratio=0.8,
        confidence_score=0.5,
        gate_result="fail",
        execution_path=ExecutionPath.STANDARD,
        flaky_history=[],
        escalation_depth=0,
    )
    
    assert prediction.predicted_path == ExecutionPath.DEEP


def test_escalation_policy_recommendation():
    """Test policy recommendation from historical data."""
    predictor = EscalationPredictor()
    
    project_runs = [
        {"fallback_ratio": 0.6, "confidence_score": 0.7, "escalated": True},
        {"fallback_ratio": 0.5, "confidence_score": 0.8, "escalated": False},
        {"fallback_ratio": 0.7, "confidence_score": 0.6, "escalated": True},
    ]
    
    recommendation = predictor.get_policy_recommendation(project_runs, "web")
    
    assert "fallback_threshold" in recommendation
    assert "confidence_threshold" in recommendation
    assert "max_escalation_depth" in recommendation
    assert recommendation["based_on_historical_data"] is True


def test_policy_template_list():
    """Test listing policy templates."""
    engine = PolicyTemplateEngine()
    
    templates = engine.list_templates()
    
    assert len(templates) > 0
    assert all(isinstance(t, PolicyTemplate) for t in templates)


def test_policy_template_by_product_type():
    """Test filtering templates by product type."""
    engine = PolicyTemplateEngine()
    
    web_templates = engine.list_templates("web")
    model_templates = engine.list_templates("model")
    
    assert len(web_templates) > 0
    assert len(model_templates) > 0
    assert all("web" in t.product_types or "api" in t.product_types for t in web_templates)


def test_policy_recommendation():
    """Test policy recommendation engine."""
    engine = PolicyTemplateEngine()
    
    recommendation = engine.recommend_policy(
        product_type="web",
        historical_runs=None,
        stability_score=0.7,
    )
    
    assert isinstance(recommendation, PolicyRecommendation)
    assert "fallback_threshold" in recommendation.recommended_config
    assert "confidence_threshold" in recommendation.recommended_config
    assert 0.0 <= recommendation.confidence <= 1.0
    assert len(recommendation.reasons) > 0


def test_policy_recommendation_with_team_preferences():
    """Test policy recommendation with team preferences."""
    engine = PolicyTemplateEngine()
    
    recommendation = engine.recommend_policy(
        product_type="web",
        team_preferences={"escalation_preference": "conservative"},
    )
    
    assert recommendation.recommended_config["fallback_threshold"] >= 0.5
    assert "team preference" in " ".join(recommendation.reasons).lower()


def test_policy_recommendation_with_stability_score():
    """Test policy recommendation adjusted by stability score."""
    engine = PolicyTemplateEngine()
    
    # Low stability
    low_rec = engine.recommend_policy(
        product_type="web",
        stability_score=0.3,
    )
    
    # High stability
    high_rec = engine.recommend_policy(
        product_type="web",
        stability_score=0.9,
    )
    
    # Low stability should have lower thresholds (more aggressive)
    assert low_rec.recommended_config["fallback_threshold"] <= high_rec.recommended_config["fallback_threshold"]


def test_custom_policy_template_creation():
    """Test creating custom policy template."""
    engine = PolicyTemplateEngine()
    
    custom = engine.create_custom_template(
        name="My Custom Policy",
        description="Custom policy for testing",
        configuration={
            "fallback_threshold": 0.4,
            "confidence_threshold": 0.8,
            "max_escalation_depth": 2,
            "auto_escalate_on_fail": True,
            "auto_escalate_on_flaky": False,
            "plugin_overrides": {},
        },
        product_types=["web"],
    )
    
    assert custom.template_type == PolicyTemplateType.CUSTOM
    assert custom.name == "My Custom Policy"
    assert custom.configuration["fallback_threshold"] == 0.4


def test_policy_configuration_validation():
    """Test policy configuration validation."""
    engine = PolicyTemplateEngine()
    
    # Valid configuration
    valid_config = {
        "fallback_threshold": 0.5,
        "confidence_threshold": 0.7,
        "max_escalation_depth": 3,
        "auto_escalate_on_fail": True,
        "auto_escalate_on_flaky": True,
        "plugin_overrides": {},
    }
    is_valid, errors = engine.validate_configuration(valid_config)
    assert is_valid is True
    assert len(errors) == 0
    
    # Invalid configuration
    invalid_config = {
        "fallback_threshold": 1.5,  # Invalid: > 1.0
        "confidence_threshold": -0.1,  # Invalid: < 0.0
    }
    is_valid, errors = engine.validate_configuration(invalid_config)
    assert is_valid is False
    assert len(errors) > 0


def test_cross_project_pattern_detection():
    """Test cross-project pattern detection."""
    analytics = EscalationAnalytics()
    
    project_runs = {
        "proj1": [
            {"metadata": {"escalation_reason": "High fallback ratio"}},
            {"metadata": {"escalation_reason": "High fallback ratio"}},
        ],
        "proj2": [
            {"metadata": {"escalation_reason": "High fallback ratio"}},
        ],
        "proj3": [
            {"metadata": {"escalation_reason": "Low confidence"}},
        ],
    }
    
    patterns = analytics.analyze_cross_project_patterns(project_runs)
    
    # Should detect the common "High fallback ratio" pattern
    fallback_patterns = [p for p in patterns if "fallback" in p.description.lower()]
    assert len(fallback_patterns) >= 1
    assert fallback_patterns[0].frequency >= 2


def test_failure_mode_analysis():
    """Test failure mode analysis."""
    analytics = EscalationAnalytics()
    
    runs = [
        {"gate_result": "fail", "metadata": {"failure_type": "timeout"}},
        {"gate_result": "fail", "metadata": {"failure_type": "timeout"}},
        {"gate_result": "fail", "metadata": {"failure_type": "assertion"}},
        {"gate_result": "pass"},
        {"gate_result": "pass"},
    ]
    
    failure_modes = analytics.analyze_failure_modes(runs)
    
    assert len(failure_modes) >= 1
    assert failure_modes[0].mode_name == "timeout"
    assert failure_modes[0].occurrence_count == 2
    assert failure_modes[0].percentage == 40.0  # 2 out of 5


def test_time_to_stable_trends():
    """Test time-to-stable trend analysis."""
    analytics = EscalationAnalytics()
    
    now = datetime.utcnow()
    runs = [
        {
            "started_at": (now - timedelta(days=5)).isoformat(),
            "completed_at": (now - timedelta(days=5) + timedelta(seconds=100)).isoformat(),
        },
        {
            "started_at": (now - timedelta(days=10)).isoformat(),
            "completed_at": (now - timedelta(days=10) + timedelta(seconds=150)).isoformat(),
        },
    ]
    
    trends = analytics.analyze_time_to_stable_trends(runs, period_days=7)
    
    assert len(trends) >= 1
    assert trends[0].avg_time_to_stable > 0


def test_analytics_summary_generation():
    """Test comprehensive analytics summary generation."""
    analytics = EscalationAnalytics()
    
    project_runs = {
        "proj1": [
            {"gate_result": "fail", "metadata": {"failure_type": "timeout"}, "project_id": "proj1"},
            {"gate_result": "pass", "project_id": "proj1"},
        ],
        "proj2": [
            {"gate_result": "fail", "metadata": {"failure_type": "timeout"}, "project_id": "proj2"},
        ],
    }
    
    summary = analytics.generate_analytics_summary(project_runs)
    
    assert summary.total_runs == 3
    assert summary.escalation_rate >= 0
    assert len(summary.cross_project_patterns) >= 0
    assert len(summary.top_failure_modes) >= 0


def test_project_health_score():
    """Test project health score calculation."""
    analytics = EscalationAnalytics()
    
    now = datetime.utcnow()
    runs = [
        {
            "parent_run_id": None,
            "flaky": False,
            "started_at": (now - timedelta(days=1)).isoformat(),
            "completed_at": (now - timedelta(days=1) + timedelta(seconds=100)).isoformat(),
        },
        {
            "parent_run_id": "parent-1",
            "flaky": True,
            "metadata": {"escalation_depth": 1},
            "started_at": (now - timedelta(days=2)).isoformat(),
            "completed_at": (now - timedelta(days=2) + timedelta(seconds=200)).isoformat(),
        },
    ]
    
    health = analytics.get_project_health_score(runs)
    
    assert 0.0 <= health["health_score"] <= 1.0
    assert "factors" in health
    assert "metrics" in health
    assert health["metrics"]["escalation_rate"] == 0.5  # 1 out of 2


def test_websocket_manager_initialization():
    """Test WebSocket manager initialization."""
    from api.websocket_manager import WebSocketManager, RunIntelligenceMessage
    
    manager = WebSocketManager()
    
    assert manager.active_connections == {}
    assert manager.run_subscribers == {}


def test_run_intelligence_message_serialization():
    """Test RunIntelligenceMessage serialization."""
    from api.websocket_manager import RunIntelligenceMessage
    
    message = RunIntelligenceMessage(
        event_type="run_update",
        run_id="run-1",
        timestamp=datetime.utcnow().isoformat(),
        data={"status": "running"},
    )
    
    json_str = message.to_json()
    
    assert "run_update" in json_str
    assert "run-1" in json_str
