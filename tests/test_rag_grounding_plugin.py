"""Tests for RAG Grounding plugin."""

import pytest
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from orchestrator.models import ExecutionPath, ProductType
from orchestrator.plugins.base import (
    ExecutionContext,
    EvidenceItem,
    EvidenceType,
    ExecutionStatus,
    PluginExecutionResult,
)
from orchestrator.plugins.rag_grounding import RAGGroundingPlugin
from orchestrator.plugins.registry import PluginRegistry
from orchestrator.plugins.integration import PluginOrchestrator, initialize_plugin_system


def test_rag_grounding_plugin_properties():
    """Test RAG Grounding plugin properties."""
    plugin = RAGGroundingPlugin()
    
    assert plugin.name == "rag_grounding"
    assert plugin.version == "3.0.0"
    assert ProductType.RAG.value in plugin.supported_product_types
    assert ExecutionPath.SMOKE in plugin.supported_execution_paths
    assert ExecutionPath.STANDARD in plugin.supported_execution_paths
    assert ExecutionPath.DEEP in plugin.supported_execution_paths
    assert ExecutionPath.INTELLIGENT in plugin.supported_execution_paths


def test_rag_grounding_plugin_config_validation():
    """Test RAG Grounding plugin configuration validation."""
    plugin = RAGGroundingPlugin()
    
    # Valid config
    valid_config = {
        "similarity_threshold": 0.7,
        "top_k": 5,
        "grounding_threshold": 0.6,
    }
    is_valid, errors = plugin.validate_config(valid_config)
    assert is_valid is True
    assert len(errors) == 0
    
    # Invalid config - similarity_threshold out of range
    invalid_config = {"similarity_threshold": 1.5}
    is_valid, errors = plugin.validate_config(invalid_config)
    assert is_valid is False
    assert "Invalid similarity_threshold" in errors[0]
    
    # Invalid config - top_k too low
    invalid_config = {"top_k": 0}
    is_valid, errors = plugin.validate_config(invalid_config)
    assert is_valid is False
    assert "Invalid top_k" in errors[0]
    
    # Invalid config - grounding_threshold out of range
    invalid_config = {"grounding_threshold": -0.5}
    is_valid, errors = plugin.validate_config(invalid_config)
    assert is_valid is False
    assert "Invalid grounding_threshold" in errors[0]


def test_rag_grounding_plugin_get_evaluation_scope_smoke():
    """Test getting evaluation scope for SMOKE execution path."""
    plugin = RAGGroundingPlugin()
    
    config = {
        "evaluation_scope": {
            "smoke": ["basic_grounding"]
        }
    }
    
    scope = plugin._get_evaluation_scope(ExecutionPath.SMOKE, config)
    assert scope == ["basic_grounding"]


def test_rag_grounding_plugin_get_evaluation_scope_standard():
    """Test getting evaluation scope for STANDARD execution path."""
    plugin = RAGGroundingPlugin()
    
    config = {
        "evaluation_scope": {
            "standard": ["basic_grounding", "citation_verification"]
        }
    }
    
    scope = plugin._get_evaluation_scope(ExecutionPath.STANDARD, config)
    assert scope == ["basic_grounding", "citation_verification"]


def test_rag_grounding_plugin_get_evaluation_scope_deep():
    """Test getting evaluation scope for DEEP execution path."""
    plugin = RAGGroundingPlugin()
    
    config = {
        "evaluation_scope": {
            "deep": ["basic_grounding", "unsupported_claims", "chunk_overlap"]
        }
    }
    
    scope = plugin._get_evaluation_scope(ExecutionPath.DEEP, config)
    assert "unsupported_claims" in scope
    assert "chunk_overlap" in scope


def test_rag_grounding_plugin_get_evaluation_scope_intelligent():
    """Test getting evaluation scope for INTELLIGENT execution path."""
    plugin = RAGGroundingPlugin()
    
    config = {
        "evaluation_scope": {
            "intelligent": ["basic_grounding", "multi_hop", "contradiction_detection", "anomaly_ranking"]
        }
    }
    
    scope = plugin._get_evaluation_scope(ExecutionPath.INTELLIGENT, config)
    assert "multi_hop" in scope
    assert "contradiction_detection" in scope
    assert "anomaly_ranking" in scope


def test_rag_grounding_plugin_get_evaluation_scope_default():
    """Test default evaluation scope when not configured."""
    plugin = RAGGroundingPlugin()
    
    smoke_scope = plugin._get_evaluation_scope(ExecutionPath.SMOKE, {})
    assert "basic_grounding" in smoke_scope
    
    standard_scope = plugin._get_evaluation_scope(ExecutionPath.STANDARD, {})
    assert "citation_verification" in standard_scope


@pytest.mark.asyncio
async def test_rag_grounding_plugin_initialize():
    """Test RAG Grounding plugin initialization."""
    plugin = RAGGroundingPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
            config={
                "embedding_model": "all-MiniLM-L6-v2",
                "similarity_threshold": 0.7,
            },
        )
        
        result = await plugin.initialize(context)
        assert result is True
        assert plugin._config is not None
        assert plugin._config.similarity_threshold == 0.7


@pytest.mark.asyncio
async def test_rag_grounding_plugin_cleanup():
    """Test RAG Grounding plugin cleanup."""
    plugin = RAGGroundingPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
            config={},
        )
        
        await plugin.initialize(context)
        result = await plugin.cleanup(context)
        assert result is True
        assert plugin._config is None
        assert plugin._embedding_model is None


@pytest.mark.asyncio
async def test_rag_grounding_plugin_execute_smoke():
    """Test RAG Grounding plugin execution with SMOKE path."""
    plugin = RAGGroundingPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.SMOKE,
            output_path=Path(tmpdir),
            config={
                "grounding_threshold": 0.6,
            },
            metadata={
                "queries": ["What is the capital of France?"],
                "responses": ["The capital of France is Paris."],
                "knowledge_base": ["Paris is the capital of France.", "France is a country in Europe."],
            },
        )
        
        await plugin.initialize(context)
        result = await plugin.execute(context)
        
        assert result.plugin_name == "rag_grounding"
        assert result.status == ExecutionStatus.COMPLETED
        assert result.metrics["queries_evaluated"] == 1
        assert result.metrics["responses_evaluated"] == 1


@pytest.mark.asyncio
async def test_rag_grounding_plugin_execute_standard():
    """Test RAG Grounding plugin execution with STANDARD path."""
    plugin = RAGGroundingPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.STANDARD,
            output_path=Path(tmpdir),
            config={
                "similarity_threshold": 0.7,
                "grounding_threshold": 0.6,
            },
            metadata={
                "queries": ["What is the capital of France?"],
                "responses": ["The capital of France is Paris [1]."],
                "knowledge_base": ["Paris is the capital of France.", "France is a country in Europe."],
            },
        )
        
        await plugin.initialize(context)
        result = await plugin.execute(context)
        
        assert result.status == ExecutionStatus.COMPLETED
        assert result.metrics["queries_evaluated"] == 1


@pytest.mark.asyncio
async def test_rag_grounding_plugin_execute_deep():
    """Test RAG Grounding plugin execution with DEEP path."""
    plugin = RAGGroundingPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.DEEP,
            output_path=Path(tmpdir),
            config={
                "grounding_threshold": 0.6,
            },
            metadata={
                "queries": ["What is the capital of France?"],
                "responses": ["The capital of France is Paris."],
                "knowledge_base": ["Paris is the capital of France.", "France is a country in Europe."],
            },
        )
        
        await plugin.initialize(context)
        result = await plugin.execute(context)
        
        assert result.status == ExecutionStatus.COMPLETED
        # Should include chunk overlap evidence
        overlap_evidence = [e for e in result.evidence if e.evidence_type == EvidenceType.METRIC and e.content.get("metric") == "chunk_overlap"]
        assert len(overlap_evidence) > 0


@pytest.mark.asyncio
async def test_rag_grounding_plugin_execute_intelligent():
    """Test RAG Grounding plugin execution with INTELLIGENT path."""
    plugin = RAGGroundingPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.INTELLIGENT,
            output_path=Path(tmpdir),
            config={
                "grounding_threshold": 0.6,
            },
            metadata={
                "queries": ["What is the capital of France?"],
                "responses": ["The capital of France is Paris."],
                "knowledge_base": ["Paris is the capital of France.", "France is a country in Europe."],
            },
        )
        
        await plugin.initialize(context)
        result = await plugin.execute(context)
        
        assert result.status == ExecutionStatus.COMPLETED
        # Should include anomaly ranking evidence
        anomaly_evidence = [e for e in result.evidence if e.evidence_type == EvidenceType.METRIC and e.content.get("metric") == "anomaly_ranking"]
        assert len(anomaly_evidence) > 0


def test_rag_grounding_plugin_calculate_grounding_score():
    """Test grounding score calculation."""
    plugin = RAGGroundingPlugin()
    
    response = "The capital of France is Paris."
    knowledge_base = ["Paris is the capital of France.", "France is a country in Europe."]
    
    score = plugin._calculate_grounding_score(response, knowledge_base)
    
    assert 0.0 <= score <= 1.0


def test_rag_grounding_plugin_retrieve_chunks():
    """Test chunk retrieval."""
    plugin = RAGGroundingPlugin()
    
    query = "What is the capital of France?"
    knowledge_base = ["Paris is the capital of France.", "France is a country in Europe.", "Berlin is the capital of Germany."]
    
    chunks = plugin._retrieve_chunks(query, knowledge_base, top_k=2)
    
    assert len(chunks) <= 2
    assert isinstance(chunks, list)


def test_rag_grounding_plugin_calculate_consistency_score():
    """Test consistency score calculation."""
    plugin = RAGGroundingPlugin()
    
    response = "The capital of France is Paris."
    retrieved_chunks = ["Paris is the capital of France.", "France is a country in Europe."]
    
    score = plugin._calculate_consistency_score(response, retrieved_chunks)
    
    assert 0.0 <= score <= 1.0


def test_rag_grounding_plugin_extract_citations():
    """Test citation extraction."""
    plugin = RAGGroundingPlugin()
    
    response = "The capital of France is Paris [1]. France is in Europe [2]."
    
    citations = plugin._extract_citations(response)
    
    assert "1" in citations
    assert "2" in citations


def test_rag_grounding_plugin_extract_claims():
    """Test claim extraction."""
    plugin = RAGGroundingPlugin()
    
    response = "The capital of France is Paris. France is a country in Europe."
    
    claims = plugin._extract_claims(response)
    
    assert len(claims) > 0
    assert "The capital of France is Paris" in claims[0]


def test_rag_grounding_plugin_verify_claim_support():
    """Test claim support verification."""
    plugin = RAGGroundingPlugin()
    
    claim = "Paris is the capital of France"
    knowledge_base = ["Paris is the capital of France.", "France is a country in Europe."]
    
    is_supported = plugin._verify_claim_support(claim, knowledge_base)
    
    assert isinstance(is_supported, bool)


def test_rag_grounding_plugin_calculate_overlap():
    """Test chunk overlap calculation."""
    plugin = RAGGroundingPlugin()
    
    chunk1 = "Paris is the capital of France."
    chunk2 = "France is a beautiful country in Europe."
    
    overlap = plugin._calculate_overlap(chunk1, chunk2)
    
    assert 0.0 <= overlap <= 1.0


def test_rag_grounding_plugin_detect_contradictions():
    """Test contradiction detection."""
    plugin = RAGGroundingPlugin()
    
    response = "Paris is not the capital of France."
    knowledge_base = ["Paris is the capital of France."]
    
    contradictions = plugin._detect_contradictions(response, knowledge_base)
    
    assert isinstance(contradictions, list)


def test_rag_grounding_plugin_registry_registration():
    """Test RAG Grounding plugin registration in registry."""
    registry = PluginRegistry()
    registry.register_plugin_class(RAGGroundingPlugin)
    
    assert registry.is_plugin_executable("rag_grounding")
    
    plugin = registry.get_plugin("rag_grounding")
    assert plugin is not None
    assert plugin.name == "rag_grounding"


def test_rag_grounding_plugin_orchestrator_integration():
    """Test RAG Grounding plugin integration with PluginOrchestrator."""
    orchestrator = PluginOrchestrator()
    
    # Check that RAG Grounding plugin is registered
    assert orchestrator.registry.is_plugin_executable("rag_grounding")


def test_rag_grounding_plugin_initialize_system():
    """Test RAG Grounding plugin in system initialization."""
    registry = initialize_plugin_system()
    
    assert registry.is_plugin_executable("rag_grounding")


def test_rag_grounding_plugin_evidence_types():
    """Test evidence types collected by RAG Grounding plugin."""
    plugin = RAGGroundingPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.STANDARD,
            output_path=Path(tmpdir),
            config={
                "grounding_threshold": 0.6,
            },
            metadata={
                "queries": ["What is the capital of France?"],
                "responses": ["The capital of France is Paris."],
                "knowledge_base": ["Paris is the capital of France."],
            },
        )
        
        plugin._config = plugin.RAGGroundingConfig(grounding_threshold=0.6)
        
        # Test basic grounding evaluation
        evidence, passed, failed = plugin._evaluate_basic_grounding(
            context,
            context.metadata["queries"],
            context.metadata["responses"],
            context.metadata["knowledge_base"]
        )
        
        # Check for ASSERTION evidence
        assert len(evidence) > 0
        assert evidence[0].evidence_type == EvidenceType.ASSERTION
        assert evidence[0].content.get("assertion") == "basic_grounding"


def test_rag_grounding_plugin_metrics_integration():
    """Test RAG Grounding plugin metrics integration with PluginOrchestrator."""
    orchestrator = PluginOrchestrator()
    
    # Create a mock result
    result = PluginExecutionResult(
        plugin_name="rag_grounding",
        status=ExecutionStatus.COMPLETED,
        success=True,
        metrics={
            "assertions_passed": 5,
            "assertions_failed": 0,
            "queries_evaluated": 3,
            "responses_evaluated": 3,
            "knowledge_base_size": 10,
        },
    )
    
    # Test metrics calculation
    metrics = orchestrator.calculate_plugin_metrics({"rag_grounding": result})
    
    assert metrics["rag_grounding"]["success"] is True
    assert metrics["rag_grounding"]["metrics"]["queries_evaluated"] == 3


def test_rag_grounding_plugin_metadata_compatibility():
    """Test RAG Grounding plugin metadata compatibility with existing metadata."""
    from orchestrator.compatibility import BUILTIN_PLUGINS
    
    # Check that rag_grounding metadata exists
    assert "rag_grounding" in BUILTIN_PLUGINS
    
    metadata = BUILTIN_PLUGINS["rag_grounding"]
    assert metadata.name == "rag_grounding"
    assert metadata.version == "2.0.0"  # Existing metadata version
    assert metadata.execution_depth_score == 0.78
    assert metadata.evidence_richness_score == 0.88
    assert metadata.confidence_score == 0.83


def test_rag_grounding_plugin_multi_hop_score():
    """Test multi-hop grounding score calculation."""
    plugin = RAGGroundingPlugin()
    
    response = "The capital of France is Paris, which is located in Europe."
    knowledge_base = ["Paris is the capital of France.", "France is located in Europe."]
    
    score = plugin._calculate_multi_hop_score(response, knowledge_base)
    
    assert 0.0 <= score <= 1.0


def test_rag_grounding_plugin_hallucination_heuristic():
    """Test hallucination heuristic evaluation."""
    plugin = RAGGroundingPlugin()
    
    with TemporaryDirectory() as tmpdir:
        context = ExecutionContext(
            run_id="run-1",
            project_id="proj-1",
            execution_path=ExecutionPath.DEEP,
            output_path=Path(tmpdir),
            config={
                "grounding_threshold": 0.6,
            },
            metadata={
                "queries": ["What is the capital of France?"],
                "responses": ["The capital of France is Paris."],
                "knowledge_base": ["Paris is the capital of France."],
            },
        )
        
        plugin._config = plugin.RAGGroundingConfig(grounding_threshold=0.6)
        
        evidence = plugin._evaluate_hallucination_heuristic(
            context,
            context.metadata["queries"],
            context.metadata["responses"],
            context.metadata["knowledge_base"]
        )
        
        # Check for ASSERTION evidence
        assert len(evidence) > 0
        assert evidence[0].evidence_type == EvidenceType.ASSERTION
        assert evidence[0].content.get("assertion") == "hallucination_heuristic"
