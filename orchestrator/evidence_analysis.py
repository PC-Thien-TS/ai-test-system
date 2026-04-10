"""AI-assisted evidence analysis for anomaly detection and pattern grouping."""

from dataclasses import dataclass
from typing import List, Dict, Optional, Set
from datetime import datetime
from enum import Enum


class AnomalySeverity(Enum):
    """Severity levels for detected anomalies."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Anomaly:
    """Detected anomaly in evidence."""
    evidence_id: str
    anomaly_type: str
    severity: AnomalySeverity
    description: str
    confidence: float
    timestamp: str
    related_evidence: List[str]
    
    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "anomaly_type": self.anomaly_type,
            "severity": self.severity.value,
            "description": self.description,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "related_evidence": self.related_evidence,
        }


@dataclass
class EvidencePattern:
    """Pattern detected across multiple evidence items."""
    pattern_id: str
    pattern_type: str
    description: str
    evidence_ids: List[str]
    frequency: int
    confidence: float
    severity: AnomalySeverity
    
    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "description": self.description,
            "evidence_ids": self.evidence_ids,
            "frequency": self.frequency,
            "confidence": self.confidence,
            "severity": self.severity.value,
        }


@dataclass
class EvidenceRanking:
    """Suspiciousness ranking for evidence."""
    evidence_id: str
    suspicious_score: float
    rank: int
    reasons: List[str]
    
    def to_dict(self) -> dict:
        return {
            "evidence_id": self.evidence_id,
            "suspicious_score": self.suspicious_score,
            "rank": self.rank,
            "reasons": self.reasons,
        }


class EvidenceAnalyzer:
    """Analyzes evidence for anomalies, patterns, and suspicious items."""

    def __init__(self):
        self._anomaly_detectors = {
            "unexpected_response": self._detect_unexpected_response,
            "timeout_anomaly": self._detect_timeout_anomaly,
            "visual_regression": self._detect_visual_regression,
            "content_mismatch": self._detect_content_mismatch,
            "performance_degradation": self._detect_performance_degradation,
        }

    def analyze_evidence(
        self,
        evidence_items: List[dict],
        baseline_evidence: Optional[List[dict]] = None,
    ) -> Dict[str, any]:
        """
        Analyze evidence items for anomalies, patterns, and suspiciousness.

        Args:
            evidence_items: List of evidence items to analyze.
            baseline_evidence: Optional baseline evidence for comparison.

        Returns:
            Dictionary containing anomalies, patterns, and rankings.
        """
        anomalies = self._detect_anomalies(evidence_items, baseline_evidence)
        patterns = self._group_patterns(evidence_items)
        rankings = self._rank_suspiciousness(evidence_items, anomalies, patterns)

        return {
            "anomalies": [a.to_dict() for a in anomalies],
            "patterns": [p.to_dict() for p in patterns],
            "rankings": [r.to_dict() for r in rankings],
            "summary": {
                "total_evidence": len(evidence_items),
                "anomaly_count": len(anomalies),
                "pattern_count": len(patterns),
                "high_risk_count": sum(1 for a in anomalies if a.severity in (AnomalySeverity.CRITICAL, AnomalySeverity.HIGH)),
            }
        }

    def _detect_anomalies(
        self,
        evidence_items: List[dict],
        baseline_evidence: Optional[List[dict]] = None,
    ) -> List[Anomaly]:
        """Detect anomalies in evidence items."""
        anomalies = []

        for item in evidence_items:
            evidence_id = item.get("id", "unknown")
            evidence_type = item.get("type", "unknown")
            content = item.get("content", {})

            for detector_name, detector_func in self._anomaly_detectors.items():
                detected = detector_func(evidence_id, evidence_type, content, baseline_evidence)
                if detected:
                    anomalies.append(detected)

        return anomalies

    def _detect_unexpected_response(
        self,
        evidence_id: str,
        evidence_type: str,
        content: dict,
        baseline_evidence: Optional[List[dict]],
    ) -> Optional[Anomaly]:
        """Detect unexpected response codes or formats."""
        if evidence_type != "trace":
            return None

        status_code = content.get("status_code")
        if status_code and status_code >= 400:
            severity = AnomalySeverity.CRITICAL if status_code >= 500 else AnomalySeverity.HIGH
            return Anomaly(
                evidence_id=evidence_id,
                anomaly_type="unexpected_response",
                severity=severity,
                description=f"HTTP {status_code} response detected",
                confidence=0.9,
                timestamp=datetime.utcnow().isoformat(),
                related_evidence=[],
            )

        return None

    def _detect_timeout_anomaly(
        self,
        evidence_id: str,
        evidence_type: str,
        content: dict,
        baseline_evidence: Optional[List[dict]],
    ) -> Optional[Anomaly]:
        """Detect timeout anomalies."""
        duration = content.get("duration")
        if duration and duration > 10000:  # 10 seconds
            return Anomaly(
                evidence_id=evidence_id,
                anomaly_type="timeout_anomaly",
                severity=AnomalySeverity.HIGH,
                description=f"Slow response detected: {duration}ms",
                confidence=0.85,
                timestamp=datetime.utcnow().isoformat(),
                related_evidence=[],
            )

        return None

    def _detect_visual_regression(
        self,
        evidence_id: str,
        evidence_type: str,
        content: dict,
        baseline_evidence: Optional[List[dict]],
    ) -> Optional[Anomaly]:
        """Detect visual regression in screenshots."""
        if evidence_type != "screenshot":
            return None

        diff_score = content.get("diff_score")
        if diff_score and diff_score > 0.1:  # 10% difference
            severity = AnomalySeverity.CRITICAL if diff_score > 0.3 else AnomalySeverity.MEDIUM
            return Anomaly(
                evidence_id=evidence_id,
                anomaly_type="visual_regression",
                severity=severity,
                description=f"Visual difference detected: {diff_score:.1%}",
                confidence=0.8,
                timestamp=datetime.utcnow().isoformat(),
                related_evidence=[],
            )

        return None

    def _detect_content_mismatch(
        self,
        evidence_id: str,
        evidence_type: str,
        content: dict,
        baseline_evidence: Optional[List[dict]],
    ) -> Optional[Anomaly]:
        """Detect content mismatches from expected values."""
        expected = content.get("expected")
        actual = content.get("actual")

        if expected is not None and actual is not None and expected != actual:
            return Anomaly(
                evidence_id=evidence_id,
                anomaly_type="content_mismatch",
                severity=AnomalySeverity.HIGH,
                description=f"Content mismatch: expected '{expected}', got '{actual}'",
                confidence=0.95,
                timestamp=datetime.utcnow().isoformat(),
                related_evidence=[],
            )

        return None

    def _detect_performance_degradation(
        self,
        evidence_id: str,
        evidence_type: str,
        content: dict,
        baseline_evidence: Optional[List[dict]],
    ) -> Optional[Anomaly]:
        """Detect performance degradation compared to baseline."""
        if not baseline_evidence:
            return None

        current_duration = content.get("duration")
        if not current_duration:
            return None

        baseline_durations = [
            b.get("content", {}).get("duration")
            for b in baseline_evidence
            if b.get("type") == evidence_type
        ]
        baseline_durations = [d for d in baseline_durations if d is not None]

        if baseline_durations:
            avg_baseline = sum(baseline_durations) / len(baseline_durations)
            if current_duration > avg_baseline * 2:  # 2x slower
                return Anomaly(
                    evidence_id=evidence_id,
                    anomaly_type="performance_degradation",
                    severity=AnomalySeverity.MEDIUM,
                    description=f"Performance degraded: {current_duration}ms vs baseline {avg_baseline:.0f}ms",
                    confidence=0.75,
                    timestamp=datetime.utcnow().isoformat(),
                    related_evidence=[],
                )

        return None

    def _group_patterns(self, evidence_items: List[dict]) -> List[EvidencePattern]:
        """Group evidence items by detected patterns."""
        patterns = []

        # Group by error messages
        error_groups: Dict[str, List[str]] = {}
        for item in evidence_items:
            error = item.get("content", {}).get("error")
            if error:
                if error not in error_groups:
                    error_groups[error] = []
                error_groups[error].append(item.get("id", "unknown"))

        for error, ids in error_groups.items():
            if len(ids) >= 2:  # Pattern needs at least 2 occurrences
                patterns.append(EvidencePattern(
                    pattern_id=f"error_{hash(error)}",
                    pattern_type="error_pattern",
                    description=f"Repeated error: {error}",
                    evidence_ids=ids,
                    frequency=len(ids),
                    confidence=0.8,
                    severity=AnomalySeverity.HIGH,
                ))

        # Group by URL paths
        path_groups: Dict[str, List[str]] = {}
        for item in evidence_items:
            url = item.get("content", {}).get("url")
            if url:
                path = url.split("?")[0]  # Remove query params
                if path not in path_groups:
                    path_groups[path] = []
                path_groups[path].append(item.get("id", "unknown"))

        for path, ids in path_groups.items():
            if len(ids) >= 3:  # Pattern needs at least 3 occurrences
                patterns.append(EvidencePattern(
                    pattern_id=f"path_{hash(path)}",
                    pattern_type="frequent_path",
                    description=f"Frequently accessed path: {path}",
                    evidence_ids=ids,
                    frequency=len(ids),
                    confidence=0.7,
                    severity=AnomalySeverity.LOW,
                ))

        return patterns

    def _rank_suspiciousness(
        self,
        evidence_items: List[dict],
        anomalies: List[Anomaly],
        patterns: List[EvidencePattern],
    ) -> List[EvidenceRanking]:
        """Rank evidence items by suspiciousness."""
        rankings = []

        for item in evidence_items:
            evidence_id = item.get("id", "unknown")
            score = 0.0
            reasons = []

            # Check for anomalies
            item_anomalies = [a for a in anomalies if a.evidence_id == evidence_id]
            for anomaly in item_anomalies:
                if anomaly.severity == AnomalySeverity.CRITICAL:
                    score += 0.5
                    reasons.append(f"Critical anomaly: {anomaly.description}")
                elif anomaly.severity == AnomalySeverity.HIGH:
                    score += 0.3
                    reasons.append(f"High severity anomaly: {anomaly.description}")
                elif anomaly.severity == AnomalySeverity.MEDIUM:
                    score += 0.15
                    reasons.append(f"Medium severity anomaly: {anomaly.description}")
                else:
                    score += 0.05
                    reasons.append(f"Low severity anomaly: {anomaly.description}")

            # Check for patterns
            item_patterns = [p for p in patterns if evidence_id in p.evidence_ids]
            for pattern in item_patterns:
                if pattern.severity == AnomalySeverity.HIGH:
                    score += 0.2
                    reasons.append(f"Part of high-risk pattern: {pattern.description}")
                elif pattern.severity == AnomalySeverity.MEDIUM:
                    score += 0.1
                    reasons.append(f"Part of pattern: {pattern.description}")

            # Check for unusual content
            content = item.get("content", {})
            if content.get("status_code") and content["status_code"] >= 500:
                score += 0.3
                reasons.append("Server error response")

            if content.get("duration") and content["duration"] > 10000:
                score += 0.2
                reasons.append("Slow response time")

            if score > 0:
                rankings.append(EvidenceRanking(
                    evidence_id=evidence_id,
                    suspicious_score=min(score, 1.0),
                    rank=0,  # Will be set after sorting
                    reasons=reasons,
                ))

        # Sort by score and assign ranks
        rankings.sort(key=lambda r: r.suspicious_score, reverse=True)
        for i, ranking in enumerate(rankings):
            ranking.rank = i + 1

        return rankings
