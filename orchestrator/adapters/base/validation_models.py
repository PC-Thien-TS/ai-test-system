from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(frozen=True)
class ValidationCheck:
    name: str
    status: str  # pass | warn | fail
    details: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AdapterValidationReport:
    adapter_name: str
    status: str = "fail"  # pass | pass_with_warnings | fail
    generated_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    contract_checks: list[ValidationCheck] = field(default_factory=list)
    loader_checks: list[ValidationCheck] = field(default_factory=list)
    structure_checks: list[ValidationCheck] = field(default_factory=list)
    core_smoke_checks: list[ValidationCheck] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    strict_mode: bool = False
    ci_mode: bool = False

    def all_checks(self) -> list[ValidationCheck]:
        return (
            self.contract_checks
            + self.loader_checks
            + self.structure_checks
            + self.core_smoke_checks
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter_name": self.adapter_name,
            "status": self.status,
            "generated_at_utc": self.generated_at_utc,
            "contract_checks": [item.to_dict() for item in self.contract_checks],
            "loader_checks": [item.to_dict() for item in self.loader_checks],
            "structure_checks": [item.to_dict() for item in self.structure_checks],
            "core_smoke_checks": [item.to_dict() for item in self.core_smoke_checks],
            "warnings": self.warnings,
            "errors": self.errors,
            "recommendations": self.recommendations,
            "strict_mode": self.strict_mode,
            "ci_mode": self.ci_mode,
        }

