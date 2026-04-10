"""WebSocket manager for real-time run intelligence updates."""

import json
import asyncio
from typing import Dict, Set, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass, asdict


@dataclass
class RunIntelligenceMessage:
    """Message structure for run intelligence updates."""
    event_type: str
    run_id: str
    timestamp: str
    data: dict

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.run_subscribers: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        if client_id not in self.active_connections:
            self.active_connections[client_id] = set()
        self.active_connections[client_id].add(websocket)

    def disconnect(self, websocket: WebSocket, client_id: str):
        """Remove a WebSocket connection."""
        if client_id in self.active_connections:
            self.active_connections[client_id].discard(websocket)
            if not self.active_connections[client_id]:
                del self.active_connections[client_id]
        
        # Remove from run subscriptions
        for run_id, subscribers in self.run_subscribers.items():
            subscribers.discard(websocket)
            if not subscribers:
                del self.run_subscribers[run_id]

    async def subscribe_to_run(self, websocket: WebSocket, run_id: str):
        """Subscribe a client to updates for a specific run."""
        if run_id not in self.run_subscribers:
            self.run_subscribers[run_id] = set()
        self.run_subscribers[run_id].add(websocket)

    async def unsubscribe_from_run(self, websocket: WebSocket, run_id: str):
        """Unsubscribe a client from updates for a specific run."""
        if run_id in self.run_subscribers:
            self.run_subscribers[run_id].discard(websocket)
            if not self.run_subscribers[run_id]:
                del self.run_subscribers[run_id]

    async def broadcast_to_run(self, run_id: str, message: RunIntelligenceMessage):
        """Broadcast a message to all subscribers of a specific run."""
        if run_id in self.run_subscribers:
            disconnected = set()
            for connection in self.run_subscribers[run_id]:
                try:
                    await connection.send_text(message.to_json())
                except Exception:
                    disconnected.add(connection)
            
            # Clean up disconnected connections
            for connection in disconnected:
                self.run_subscribers[run_id].discard(connection)

    async def broadcast_to_all(self, message: RunIntelligenceMessage):
        """Broadcast a message to all connected clients."""
        disconnected = set()
        for client_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_text(message.to_json())
                except Exception:
                    disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            for client_id in list(self.active_connections.keys()):
                self.active_connections[client_id].discard(connection)

    async def send_run_update(
        self,
        run_id: str,
        status: str,
        confidence_score: Optional[float] = None,
        fallback_ratio: Optional[float] = None,
        execution_path: Optional[str] = None,
        escalation_state: Optional[dict] = None,
    ):
        """Send a run status update."""
        message = RunIntelligenceMessage(
            event_type="run_update",
            run_id=run_id,
            timestamp=datetime.utcnow().isoformat(),
            data={
                "status": status,
                "confidence_score": confidence_score,
                "fallback_ratio": fallback_ratio,
                "execution_path": execution_path,
                "escalation_state": escalation_state,
            }
        )
        await self.broadcast_to_run(run_id, message)

    async def send_evidence_update(
        self,
        run_id: str,
        evidence_type: str,
        count: int,
        analysis: Optional[dict] = None,
    ):
        """Send an evidence update with analysis."""
        message = RunIntelligenceMessage(
            event_type="evidence_update",
            run_id=run_id,
            timestamp=datetime.utcnow().isoformat(),
            data={
                "evidence_type": evidence_type,
                "count": count,
                "analysis": analysis,
            }
        )
        await self.broadcast_to_run(run_id, message)

    async def send_escalation_prediction(
        self,
        run_id: str,
        escalation_likelihood: float,
        predicted_path: Optional[str],
        prediction_confidence: float,
        reasons: list,
    ):
        """Send an escalation prediction update."""
        message = RunIntelligenceMessage(
            event_type="escalation_prediction",
            run_id=run_id,
            timestamp=datetime.utcnow().isoformat(),
            data={
                "escalation_likelihood": escalation_likelihood,
                "predicted_path": predicted_path,
                "prediction_confidence": prediction_confidence,
                "reasons": reasons,
            }
        )
        await self.broadcast_to_run(run_id, message)

    async def send_anomaly_detected(
        self,
        run_id: str,
        anomaly_type: str,
        severity: str,
        description: str,
        evidence_id: Optional[str] = None,
    ):
        """Send an anomaly detection alert."""
        message = RunIntelligenceMessage(
            event_type="anomaly_detected",
            run_id=run_id,
            timestamp=datetime.utcnow().isoformat(),
            data={
                "anomaly_type": anomaly_type,
                "severity": severity,
                "description": description,
                "evidence_id": evidence_id,
            }
        )
        await self.broadcast_to_run(run_id, message)


# Global WebSocket manager instance
manager = WebSocketManager()
