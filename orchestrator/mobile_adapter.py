from __future__ import annotations

from pathlib import Path
from typing import Any

from mobile_appium import MobileRunArtifact, MobileRunService

MOBILE_EXPLORATION_PLUGIN = "mobile_exploration"


class MobileOrchestratorAdapter:
    """Translate mobile bounded exploration runs into a platform-style result."""

    def __init__(self, service: MobileRunService | None = None) -> None:
        self.service = service or MobileRunService()

    def execute_exploration_run(
        self,
        *,
        start_screen: str = "LoginScreen",
        username: str = "",
        password: str = "",
        max_steps: int | None = None,
        output_path: str | Path | None = None,
    ) -> dict[str, Any]:
        artifact = self.service.run_bounded_exploration(
            start_screen=start_screen,
            username=username,
            password=password,
            max_steps=max_steps,
            output_path=output_path,
        )
        return self._to_platform_result(artifact)

    def _to_platform_result(self, artifact: MobileRunArtifact) -> dict[str, Any]:
        return {
            "plugin": MOBILE_EXPLORATION_PLUGIN,
            "status": "passed" if artifact.passed else "failed",
            "run_id": artifact.run_id,
            "summary": {
                "stop_reason": artifact.stop_reason,
                "coverage_score": artifact.coverage_score,
                "policy_shape": artifact.policy_shape,
                "visited_screen_count": len(artifact.visited_screens),
                "executed_action_count": len(artifact.executed_actions),
            },
            "artifact": artifact.to_dict(),
        }


def execute_mobile_exploration_run(
    *,
    start_screen: str = "LoginScreen",
    username: str = "",
    password: str = "",
    max_steps: int | None = None,
    output_path: str | Path | None = None,
    service: MobileRunService | None = None,
) -> dict[str, Any]:
    """Convenience entry point for orchestrator callers."""
    return MobileOrchestratorAdapter(service=service).execute_exploration_run(
        start_screen=start_screen,
        username=username,
        password=password,
        max_steps=max_steps,
        output_path=output_path,
    )
