from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class GeneratedScriptArtifact:
    script: str
    script_type: str
    framework: str
    generated_test_names: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AutomationScriptGenerator:
    """Generate deterministic API pytest skeletons from structured test cases."""

    def generate(self, test_cases: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> dict[str, Any]:
        normalized_cases = self._normalize_cases(test_cases)
        generated_test_names = [self._build_test_name(case) for case in normalized_cases]

        lines: list[str] = [
            "import os",
            "",
            "import pytest",
            "import requests",
            "",
            'BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")',
            "",
        ]

        for case, test_name in zip(normalized_cases, generated_test_names):
            lines.extend(self._build_test_function(case, test_name))
            lines.append("")

        script = "\n".join(lines).rstrip() + "\n"
        return GeneratedScriptArtifact(
            script=script,
            script_type="api_pytest",
            framework="pytest",
            generated_test_names=generated_test_names,
        ).to_dict()

    def _normalize_cases(self, test_cases: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        if isinstance(test_cases, Mapping):
            return [self._normalize_case(test_cases)]
        if isinstance(test_cases, Sequence) and not isinstance(test_cases, (str, bytes)):
            return [self._normalize_case(case) for case in test_cases]
        raise TypeError("test_cases must be a mapping or sequence of mappings")

    def _normalize_case(self, case: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(case, Mapping):
            raise TypeError("each test case must be a mapping")
        return {
            "test_case_id": self._as_str(case.get("test_case_id")) or "TC-UNKNOWN-001",
            "requirement_id": self._as_str(case.get("requirement_id")) or "REQ-UNKNOWN",
            "title": self._as_str(case.get("title")) or "Untitled Test Case",
            "priority": self._as_str(case.get("priority")) or "p2",
            "preconditions": self._as_list(case.get("preconditions")),
            "steps": self._as_list(case.get("steps")),
            "expected_result": self._as_str(case.get("expected_result")) or "Expected result not provided.",
            "test_type": self._as_str(case.get("test_type")) or "fallback",
            "automation_candidate": bool(case.get("automation_candidate", False)),
            "risk_level": self._as_str(case.get("risk_level")) or "low",
            "source": self._as_str(case.get("source")) or "unknown",
            "endpoint": self._as_str(case.get("endpoint")),
            "method": self._as_str(case.get("method")).upper(),
        }

    def _build_test_name(self, case: dict[str, Any]) -> str:
        slug_base = f"{case['test_case_id']}_{case['title']}"
        slug = re.sub(r"[^a-z0-9]+", "_", slug_base.lower()).strip("_")
        slug = re.sub(r"_+", "_", slug)
        return f"test_{slug}" if slug else "test_generated_case"

    def _build_test_function(self, case: dict[str, Any], test_name: str) -> list[str]:
        lines = [f"def {test_name}():"]
        lines.append(f'    """Generated from {case["test_case_id"]}."""')
        lines.append(f'    # requirement_id: {self._py_string(case["requirement_id"])}')
        lines.append(f'    # priority: {self._py_string(case["priority"])} | risk_level: {self._py_string(case["risk_level"])}')
        lines.append(f'    # test_type: {self._py_string(case["test_type"])} | source: {self._py_string(case["source"])}')

        if case["preconditions"]:
            lines.append("    # Preconditions:")
            for item in case["preconditions"]:
                lines.append(f"    # - {item}")
        else:
            lines.append("    # Preconditions: none provided")

        if case["steps"]:
            lines.append("    # Steps:")
            for idx, step in enumerate(case["steps"], start=1):
                lines.append(f"    # {idx}. {step}")
        else:
            lines.append("    # Steps: no deterministic steps were provided")

        lines.append(f'    # Expected result: {case["expected_result"]}')

        endpoint = case["endpoint"]
        method = case["method"]
        if endpoint and method:
            lines.append(f'    url = f"{{BASE_URL}}{endpoint}"')
            lines.append(f'    response = requests.request("{method}", url, timeout=30)')
            lines.append("    assert response is not None")
            lines.append("    # TODO: add request payload, response assertions, and status-code expectations.")
        else:
            lines.append('    pytest.skip("No API endpoint/method metadata provided for this generated skeleton.")')

        return lines

    def _as_str(self, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _as_list(self, value: Any) -> list[str]:
        if isinstance(value, list):
            return [self._as_str(item) for item in value if self._as_str(item)]
        if value is None:
            return []
        text = self._as_str(value)
        return [text] if text else []

    def _py_string(self, value: str) -> str:
        return value.replace("\n", " ").strip()


def generate_pytest_script(test_cases: Mapping[str, Any] | Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Generate a deterministic pytest API skeleton script from one or more test cases."""
    return AutomationScriptGenerator().generate(test_cases)
