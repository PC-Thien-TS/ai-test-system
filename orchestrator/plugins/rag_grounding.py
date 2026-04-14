"""RAG Grounding plugin for RAG system validation with real execution."""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass

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
class RAGGroundingConfig:
    """Configuration for RAG grounding evaluation."""
    embedding_model: str = "all-MiniLM-L6-v2"
    similarity_threshold: float = 0.7
    top_k: int = 5
    grounding_threshold: float = 0.6
    enable_multi_hop: bool = False
    enable_contradiction_detection: bool = False


class RAGGroundingPlugin(BasePlugin):
    """RAG Grounding plugin with real execution for RAG system validation."""
    
    def __init__(self):
        super().__init__()
        self._config: Optional[RAGGroundingConfig] = None
        self._retriever: Optional[Any] = None
        self._embedding_model: Optional[Any] = None
    
    @property
    def name(self) -> str:
        return "rag_grounding"
    
    @property
    def version(self) -> str:
        return "3.0.0"
    
    @property
    def supported_product_types(self) -> List[str]:
        return [ProductType.RAG.value]
    
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
        Initialize RAG grounding with configuration.
        
        Args:
            context: Execution context.
            
        Returns:
            True if initialization successful, False otherwise.
        """
        try:
            config = context.config
            
            self._config = RAGGroundingConfig(
                embedding_model=config.get("embedding_model", "all-MiniLM-L6-v2"),
                similarity_threshold=config.get("similarity_threshold", 0.7),
                top_k=config.get("top_k", 5),
                grounding_threshold=config.get("grounding_threshold", 0.6),
                enable_multi_hop=config.get("enable_multi_hop", False),
                enable_contradiction_detection=config.get("enable_contradiction_detection", False),
            )
            
            # Try to load embedding model if available, otherwise use fallback
            try:
                from sentence_transformers import SentenceTransformer
                self._embedding_model = SentenceTransformer(self._config.embedding_model)
            except ImportError:
                # Fallback to simple similarity without embeddings
                self._embedding_model = None
            
            self._initialized = True
            return True
            
        except Exception as e:
            print(f"RAG Grounding plugin initialization error: {e}")
            return False
    
    async def execute(self, context: ExecutionContext) -> PluginExecutionResult:
        """
        Execute RAG grounding evaluation based on execution path.
        
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
            # Get queries and responses from context
            queries = context.metadata.get("queries", [])
            responses = context.metadata.get("responses", [])
            knowledge_base = context.metadata.get("knowledge_base", [])
            
            evidence_items = []
            assertions_passed = 0
            assertions_failed = 0
            metrics_dict = {}
            
            # Get evaluation scope based on execution path
            evaluation_scope = self._get_evaluation_scope(context.execution_path, context.config)
            
            # Run evaluation based on scope
            if "basic_grounding" in evaluation_scope:
                grounding_evidence, ground_passed, ground_failed = self._evaluate_basic_grounding(
                    context, queries, responses, knowledge_base
                )
                evidence_items.extend(grounding_evidence)
                assertions_passed += ground_passed
                assertions_failed += ground_failed
            
            if "citation_verification" in evaluation_scope:
                citation_evidence, cit_passed, cit_failed = self._evaluate_citation_verification(
                    context, queries, responses, knowledge_base
                )
                evidence_items.extend(citation_evidence)
                assertions_passed += cit_passed
                assertions_failed += cit_failed
            
            if "retrieval_consistency" in evaluation_scope:
                consistency_evidence, cons_passed, cons_failed = self._evaluate_retrieval_consistency(
                    context, queries, responses, knowledge_base
                )
                evidence_items.extend(consistency_evidence)
                assertions_passed += cons_passed
                assertions_failed += cons_failed
            
            if "unsupported_claims" in evaluation_scope:
                unsupported_evidence, unsup_passed, unsup_failed = self._evaluate_unsupported_claims(
                    context, queries, responses, knowledge_base
                )
                evidence_items.extend(unsupported_evidence)
                assertions_passed += unsup_passed
                assertions_failed += unsup_failed
            
            if "chunk_overlap" in evaluation_scope:
                overlap_evidence = self._evaluate_chunk_overlap(context, knowledge_base)
                evidence_items.extend(overlap_evidence)
            
            if "hallucination_heuristic" in evaluation_scope:
                hallucination_evidence = self._evaluate_hallucination_heuristic(
                    context, queries, responses, knowledge_base
                )
                evidence_items.extend(hallucination_evidence)
            
            if "multi_hop" in evaluation_scope:
                multi_hop_evidence, hop_passed, hop_failed = self._evaluate_multi_hop_grounding(
                    context, queries, responses, knowledge_base
                )
                evidence_items.extend(multi_hop_evidence)
                assertions_passed += hop_passed
                assertions_failed += hop_failed
            
            if "contradiction_detection" in evaluation_scope:
                contradiction_evidence, contra_passed, contra_failed = self._evaluate_contradiction_detection(
                    context, queries, responses, knowledge_base
                )
                evidence_items.extend(contradiction_evidence)
                assertions_passed += contra_passed
                assertions_failed += contra_failed
            
            if "anomaly_ranking" in evaluation_scope:
                anomaly_evidence = self._evaluate_anomaly_ranking(
                    context, queries, responses, knowledge_base
                )
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
                "queries_evaluated": len(queries),
                "responses_evaluated": len(responses),
                "knowledge_base_size": len(knowledge_base),
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
        Clean up RAG grounding resources.
        
        Args:
            context: Execution context.
            
        Returns:
            True if cleanup successful, False otherwise.
        """
        try:
            self._config = None
            self._retriever = None
            self._embedding_model = None
            return True
        except Exception as e:
            print(f"RAG Grounding plugin cleanup error: {e}")
            return False
    
    async def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate RAG Grounding plugin configuration.
        
        Args:
            config: Configuration to validate.
            
        Returns:
            Tuple of (is_valid, error_messages).
        """
        errors = []
        
        similarity_threshold = config.get("similarity_threshold", 0.7)
        if not isinstance(similarity_threshold, (int, float)) or not (0 <= similarity_threshold <= 1):
            errors.append("Invalid similarity_threshold: must be between 0 and 1")
        
        top_k = config.get("top_k", 5)
        if not isinstance(top_k, int) or top_k < 1:
            errors.append("Invalid top_k: must be at least 1")
        
        grounding_threshold = config.get("grounding_threshold", 0.6)
        if not isinstance(grounding_threshold, (int, float)) or not (0 <= grounding_threshold <= 1):
            errors.append("Invalid grounding_threshold: must be between 0 and 1")
        
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
            return scope_config.get("smoke", ["basic_grounding"])
        elif execution_path == ExecutionPath.STANDARD:
            return scope_config.get("standard", ["basic_grounding", "citation_verification", "retrieval_consistency"])
        elif execution_path == ExecutionPath.DEEP:
            return scope_config.get("deep", [
                "basic_grounding", "citation_verification", "retrieval_consistency",
                "unsupported_claims", "chunk_overlap", "hallucination_heuristic"
            ])
        elif execution_path == ExecutionPath.INTELLIGENT:
            return scope_config.get("intelligent", [
                "basic_grounding", "citation_verification", "retrieval_consistency",
                "unsupported_claims", "chunk_overlap", "hallucination_heuristic",
                "multi_hop", "contradiction_detection", "anomaly_ranking"
            ])
        
        return ["basic_grounding"]
    
    def _evaluate_basic_grounding(
        self,
        context: ExecutionContext,
        queries: List[str],
        responses: List[str],
        knowledge_base: List[str]
    ) -> Tuple[List[EvidenceItem], int, int]:
        """Evaluate basic grounding checks."""
        evidence = []
        passed = 0
        failed = 0
        
        for i, (query, response) in enumerate(zip(queries, responses)):
            # Calculate grounding score
            grounding_score = self._calculate_grounding_score(response, knowledge_base)
            
            is_grounded = grounding_score >= self._config.grounding_threshold
            
            evidence.append(EvidenceItem(
                evidence_type=EvidenceType.ASSERTION,
                content={
                    "assertion": "basic_grounding",
                    "query": query,
                    "response": response,
                    "grounding_score": grounding_score,
                    "threshold": self._config.grounding_threshold,
                    "passed": is_grounded,
                },
                severity="critical" if not is_grounded else "info",
                source="rag_grounding",
            ))
            
            if is_grounded:
                passed += 1
            else:
                failed += 1
        
        return evidence, passed, failed
    
    def _evaluate_citation_verification(
        self,
        context: ExecutionContext,
        queries: List[str],
        responses: List[str],
        knowledge_base: List[str]
    ) -> Tuple[List[EvidenceItem], int, int]:
        """Evaluate citation verification."""
        evidence = []
        passed = 0
        failed = 0
        
        for i, (query, response) in enumerate(zip(queries, responses)):
            # Extract citations from response (placeholder logic)
            citations = self._extract_citations(response)
            
            # Verify citations against knowledge base
            verified_citations = []
            for citation in citations:
                is_valid = self._verify_citation(citation, knowledge_base)
                verified_citations.append({
                    "citation": citation,
                    "valid": is_valid,
                })
                if is_valid:
                    passed += 1
                else:
                    failed += 1
            
            evidence.append(EvidenceItem(
                evidence_type=EvidenceType.ASSERTION,
                content={
                    "assertion": "citation_verification",
                    "query": query,
                    "response": response,
                    "citations": verified_citations,
                    "total_citations": len(citations),
                    "valid_citations": sum(1 for c in verified_citations if c["valid"]),
                },
                severity="high" if failed > 0 else "info",
                source="rag_grounding",
            ))
        
        return evidence, passed, failed
    
    def _evaluate_retrieval_consistency(
        self,
        context: ExecutionContext,
        queries: List[str],
        responses: List[str],
        knowledge_base: List[str]
    ) -> Tuple[List[EvidenceItem], int, int]:
        """Evaluate retrieval-response consistency."""
        evidence = []
        passed = 0
        failed = 0
        
        for i, (query, response) in enumerate(zip(queries, responses)):
            # Retrieve relevant chunks
            retrieved_chunks = self._retrieve_chunks(query, knowledge_base, self._config.top_k)
            
            # Check if response is consistent with retrieved chunks
            consistency_score = self._calculate_consistency_score(response, retrieved_chunks)
            
            is_consistent = consistency_score >= self._config.similarity_threshold
            
            evidence.append(EvidenceItem(
                evidence_type=EvidenceType.ASSERTION,
                content={
                    "assertion": "retrieval_consistency",
                    "query": query,
                    "response": response,
                    "retrieved_chunks": retrieved_chunks,
                    "consistency_score": consistency_score,
                    "threshold": self._config.similarity_threshold,
                    "passed": is_consistent,
                },
                severity="critical" if not is_consistent else "info",
                source="rag_grounding",
            ))
            
            if is_consistent:
                passed += 1
            else:
                failed += 1
        
        return evidence, passed, failed
    
    def _evaluate_unsupported_claims(
        self,
        context: ExecutionContext,
        queries: List[str],
        responses: List[str],
        knowledge_base: List[str]
    ) -> Tuple[List[EvidenceItem], int, int]:
        """Evaluate unsupported claim detection."""
        evidence = []
        passed = 0
        failed = 0
        
        for i, (query, response) in enumerate(zip(queries, responses)):
            # Extract claims from response (placeholder logic)
            claims = self._extract_claims(response)
            
            unsupported_claims = []
            for claim in claims:
                is_supported = self._verify_claim_support(claim, knowledge_base)
                if not is_supported:
                    unsupported_claims.append(claim)
                    failed += 1
                else:
                    passed += 1
            
            evidence.append(EvidenceItem(
                evidence_type=EvidenceType.ASSERTION,
                content={
                    "assertion": "unsupported_claims",
                    "query": query,
                    "response": response,
                    "total_claims": len(claims),
                    "unsupported_claims": unsupported_claims,
                    "unsupported_count": len(unsupported_claims),
                },
                severity="high" if len(unsupported_claims) > 0 else "info",
                source="rag_grounding",
            ))
        
        return evidence, passed, failed
    
    def _evaluate_chunk_overlap(self, context: ExecutionContext, knowledge_base: List[str]) -> List[EvidenceItem]:
        """Evaluate chunk overlap in knowledge base."""
        evidence = []
        
        # Calculate overlap between adjacent chunks (placeholder)
        overlap_scores = []
        for i in range(len(knowledge_base) - 1):
            overlap = self._calculate_overlap(knowledge_base[i], knowledge_base[i + 1])
            overlap_scores.append(overlap)
        
        avg_overlap = sum(overlap_scores) / len(overlap_scores) if overlap_scores else 0
        
        evidence.append(EvidenceItem(
            evidence_type=EvidenceType.METRIC,
            content={
                "metric": "chunk_overlap",
                "overlap_scores": overlap_scores,
                "average_overlap": avg_overlap,
                "total_chunks": len(knowledge_base),
            },
            severity="info",
            source="rag_grounding",
        ))
        
        return evidence
    
    def _evaluate_hallucination_heuristic(
        self,
        context: ExecutionContext,
        queries: List[str],
        responses: List[str],
        knowledge_base: List[str]
    ) -> List[EvidenceItem]:
        """Evaluate hallucination heuristics."""
        evidence = []
        
        for i, (query, response) in enumerate(zip(queries, responses)):
            # Calculate hallucination score based on grounding
            grounding_score = self._calculate_grounding_score(response, knowledge_base)
            hallucination_score = 1.0 - grounding_score
            
            evidence.append(EvidenceItem(
                evidence_type=EvidenceType.ASSERTION,
                content={
                    "assertion": "hallucination_heuristic",
                    "query": query,
                    "response": response,
                    "hallucination_score": hallucination_score,
                    "grounding_score": grounding_score,
                    "threshold": 1.0 - self._config.grounding_threshold,
                },
                severity="high" if hallucination_score > (1.0 - self._config.grounding_threshold) else "info",
                source="rag_grounding",
            ))
        
        return evidence
    
    def _evaluate_multi_hop_grounding(
        self,
        context: ExecutionContext,
        queries: List[str],
        responses: List[str],
        knowledge_base: List[str]
    ) -> Tuple[List[EvidenceItem], int, int]:
        """Evaluate multi-hop grounding."""
        evidence = []
        passed = 0
        failed = 0
        
        for i, (query, response) in enumerate(zip(queries, responses)):
            # Multi-hop: check if response requires multiple sources
            multi_hop_score = self._calculate_multi_hop_score(response, knowledge_base)
            
            is_multi_hop_grounded = multi_hop_score >= self._config.grounding_threshold
            
            evidence.append(EvidenceItem(
                evidence_type=EvidenceType.ASSERTION,
                content={
                    "assertion": "multi_hop_grounding",
                    "query": query,
                    "response": response,
                    "multi_hop_score": multi_hop_score,
                    "threshold": self._config.grounding_threshold,
                    "passed": is_multi_hop_grounded,
                },
                severity="critical" if not is_multi_hop_grounded else "info",
                source="rag_grounding",
            ))
            
            if is_multi_hop_grounded:
                passed += 1
            else:
                failed += 1
        
        return evidence, passed, failed
    
    def _evaluate_contradiction_detection(
        self,
        context: ExecutionContext,
        queries: List[str],
        responses: List[str],
        knowledge_base: List[str]
    ) -> Tuple[List[EvidenceItem], int, int]:
        """Evaluate contradiction detection."""
        evidence = []
        passed = 0
        failed = 0
        
        for i, (query, response) in enumerate(zip(queries, responses)):
            # Check for contradictions with knowledge base
            contradictions = self._detect_contradictions(response, knowledge_base)
            
            has_contradiction = len(contradictions) > 0
            
            evidence.append(EvidenceItem(
                evidence_type=EvidenceType.ASSERTION,
                content={
                    "assertion": "contradiction_detection",
                    "query": query,
                    "response": response,
                    "contradictions": contradictions,
                    "has_contradiction": has_contradiction,
                },
                severity="critical" if has_contradiction else "info",
                source="rag_grounding",
            ))
            
            if not has_contradiction:
                passed += 1
            else:
                failed += 1
        
        return evidence, passed, failed
    
    def _evaluate_anomaly_ranking(
        self,
        context: ExecutionContext,
        queries: List[str],
        responses: List[str],
        knowledge_base: List[str]
    ) -> List[EvidenceItem]:
        """Evaluate anomaly ranking."""
        evidence = []
        
        anomaly_scores = []
        for i, (query, response) in enumerate(zip(queries, responses)):
            # Calculate anomaly score based on multiple factors
            grounding_score = self._calculate_grounding_score(response, knowledge_base)
            contradiction_count = len(self._detect_contradictions(response, knowledge_base))
            
            anomaly_score = (1.0 - grounding_score) * 0.7 + (contradiction_count * 0.3)
            anomaly_scores.append(anomaly_score)
        
        # Rank by anomaly score
        ranked_indices = sorted(range(len(anomaly_scores)), key=lambda i: anomaly_scores[i], reverse=True)
        
        evidence.append(EvidenceItem(
            evidence_type=EvidenceType.METRIC,
            content={
                "metric": "anomaly_ranking",
                "anomaly_scores": anomaly_scores,
                "ranked_indices": ranked_indices,
                "top_anomalies": ranked_indices[:5],
            },
            severity="info",
            source="rag_grounding",
        ))
        
        return evidence
    
    # Helper methods
    
    def _calculate_grounding_score(self, response: str, knowledge_base: List[str]) -> float:
        """Calculate grounding score for a response."""
        if self._embedding_model is None:
            # Fallback: simple keyword overlap
            response_words = set(response.lower().split())
            kb_words = set(" ".join(knowledge_base).lower().split())
            overlap = len(response_words & kb_words)
            return overlap / len(response_words) if response_words else 0.0
        
        # Use embeddings for semantic similarity
        try:
            response_embedding = self._embedding_model.encode([response])
            kb_embeddings = self._embedding_model.encode(knowledge_base)
            
            # Calculate max similarity
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity(response_embedding, kb_embeddings)[0]
            return float(max(similarities))
        except Exception:
            return 0.5  # Fallback score
    
    def _retrieve_chunks(self, query: str, knowledge_base: List[str], top_k: int) -> List[str]:
        """Retrieve top-k relevant chunks from knowledge base."""
        if self._embedding_model is None:
            # Fallback: return all chunks
            return knowledge_base[:top_k]
        
        try:
            query_embedding = self._embedding_model.encode([query])
            kb_embeddings = self._embedding_model.encode(knowledge_base)
            
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity(query_embedding, kb_embeddings)[0]
            
            top_indices = sorted(range(len(similarities)), key=lambda i: similarities[i], reverse=True)[:top_k]
            return [knowledge_base[i] for i in top_indices]
        except Exception:
            return knowledge_base[:top_k]
    
    def _calculate_consistency_score(self, response: str, retrieved_chunks: List[str]) -> float:
        """Calculate consistency score between response and retrieved chunks."""
        if not retrieved_chunks:
            return 0.0
        
        if self._embedding_model is None:
            # Fallback: simple keyword overlap
            response_words = set(response.lower().split())
            kb_words = set(" ".join(retrieved_chunks).lower().split())
            overlap = len(response_words & kb_words)
            return overlap / len(response_words) if response_words else 0.0
        
        try:
            response_embedding = self._embedding_model.encode([response])
            chunk_embeddings = self._embedding_model.encode(retrieved_chunks)
            
            from sklearn.metrics.pairwise import cosine_similarity
            similarities = cosine_similarity(response_embedding, chunk_embeddings)[0]
            return float(max(similarities))
        except Exception:
            return 0.5
    
    def _calculate_overlap(self, chunk1: str, chunk2: str) -> float:
        """Calculate overlap between two chunks."""
        words1 = set(chunk1.lower().split())
        words2 = set(chunk2.lower().split())
        overlap = len(words1 & words2)
        return overlap / len(words1) if words1 else 0.0
    
    def _extract_citations(self, response: str) -> List[str]:
        """Extract citations from response (placeholder)."""
        # Simple pattern matching for [1], [2], etc.
        pattern = r'\[(\d+)\]'
        matches = re.findall(pattern, response)
        return matches
    
    def _verify_citation(self, citation: str, knowledge_base: List[str]) -> bool:
        """Verify citation against knowledge base (placeholder)."""
        # Placeholder: always return True
        return True
    
    def _extract_claims(self, response: str) -> List[str]:
        """Extract claims from response (placeholder)."""
        # Simple sentence splitting
        sentences = response.split('.')
        return [s.strip() for s in sentences if s.strip()]
    
    def _verify_claim_support(self, claim: str, knowledge_base: List[str]) -> bool:
        """Verify claim support in knowledge base (placeholder)."""
        # Simple keyword overlap check
        claim_words = set(claim.lower().split())
        for chunk in knowledge_base:
            chunk_words = set(chunk.lower().split())
            if len(claim_words & chunk_words) > len(claim_words) * 0.5:
                return True
        return False
    
    def _calculate_multi_hop_score(self, response: str, knowledge_base: List[str]) -> float:
        """Calculate multi-hop grounding score (placeholder)."""
        # Placeholder: use grounding score
        return self._calculate_grounding_score(response, knowledge_base)
    
    def _detect_contradictions(self, response: str, knowledge_base: List[str]) -> List[str]:
        """Detect contradictions with knowledge base (placeholder)."""
        # Placeholder: simple negation detection
        contradictions = []
        response_lower = response.lower()
        
        for chunk in knowledge_base:
            chunk_lower = chunk.lower()
            # Check for negation patterns
            if "not" in response_lower and "not" not in chunk_lower:
                if any(word in chunk_lower for word in response_lower.split() if len(word) > 3):
                    contradictions.append(chunk)
        
        return contradictions
