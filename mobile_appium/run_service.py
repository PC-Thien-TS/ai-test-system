from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mobile_appium.driver import MobileTestSettings, create_android_driver, get_mobile_settings
from mobile_appium.exploration import MobileExplorationRunner, load_exploration_policy, normalize_exploration_policy


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat_utc(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class MobileRunArtifact:
    run_id: str
    passed: bool
    stop_reason: str
    visited_screens: list[str]
    executed_actions: list[str]
    coverage_score: float
    policy_shape: str
    started_at: str
    finished_at: str
    duration_ms: int
    error: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class MobileRunService:
    def __init__(self, settings: MobileTestSettings | None = None) -> None:
        self.settings = settings or get_mobile_settings()

    def _resolve_policy_shape(self) -> str:
        normalized = normalize_exploration_policy(load_exploration_policy())
        return str(normalized.get("policy_shape", "unknown")).strip() or "unknown"

    def _write_artifact(self, output_path: Path, artifact: MobileRunArtifact) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(artifact.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    def run_bounded_exploration(
        self,
        *,
        start_screen: str = "LoginScreen",
        username: str = "",
        password: str = "",
        max_steps: int | None = None,
        output_path: str | Path | None = None,
    ) -> MobileRunArtifact:
        run_id = uuid.uuid4().hex
        started_at = _utc_now()
        driver = None
        artifact: MobileRunArtifact | None = None
        policy_shape = self._resolve_policy_shape()

        try:
            driver = create_android_driver(self.settings)
            runner = MobileExplorationRunner(driver, self.settings)
            result = runner.explore(
                start_screen=start_screen,
                username=username,
                password=password,
                max_steps=max_steps,
            )
            finished_at = _utc_now()
            duration_ms = max(0, int((finished_at - started_at).total_seconds() * 1000))
            coverage_progress = result.coverage_progress if isinstance(result.coverage_progress, dict) else {}
            artifact = MobileRunArtifact(
                run_id=run_id,
                passed=bool(result.passed),
                stop_reason=str(result.stop_reason),
                visited_screens=list(result.visited_screen_types),
                executed_actions=list(result.executed_actions),
                coverage_score=float(result.coverage_score),
                policy_shape=str(coverage_progress.get("policy_shape", policy_shape)),
                started_at=_isoformat_utc(started_at),
                finished_at=_isoformat_utc(finished_at),
                duration_ms=duration_ms,
                error="",
            )
        except Exception as exc:
            finished_at = _utc_now()
            duration_ms = max(0, int((finished_at - started_at).total_seconds() * 1000))
            artifact = MobileRunArtifact(
                run_id=run_id,
                passed=False,
                stop_reason="execution_error",
                visited_screens=[],
                executed_actions=[],
                coverage_score=0.0,
                policy_shape=policy_shape,
                started_at=_isoformat_utc(started_at),
                finished_at=_isoformat_utc(finished_at),
                duration_ms=duration_ms,
                error=f"{type(exc).__name__}: {exc}",
            )
        finally:
            if driver is not None and hasattr(driver, "quit"):
                driver.quit()

        if output_path is not None:
            self._write_artifact(Path(output_path), artifact)
        return artifact

