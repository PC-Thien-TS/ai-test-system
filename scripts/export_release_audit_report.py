from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PLACEHOLDER_MARKER = "MANUAL OUTPUT PLACEHOLDER"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export a Didaunao release-audit run into a single Markdown report."
    )
    parser.add_argument("run_dir", help="Path to outputs/didaunao_release_audit/<run_id>")
    parser.add_argument(
        "--out",
        help="Optional output Markdown path. Defaults to <run_dir>/release_audit_report.md",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir).resolve()
    if not run_dir.exists():
        print(f"[FAIL] Run directory does not exist: {run_dir}")
        return 1

    meta = read_json_if_present(run_dir / "run_meta.json")
    domain = str(meta.get("domain") or run_dir.parent.name)
    if domain != "didaunao_release_audit":
        print(
            "[FAIL] This exporter is intended for outputs/didaunao_release_audit/<run_id> "
            f"but received domain '{domain}'."
        )
        return 1

    artifacts = collect_artifacts(run_dir)
    report = build_report(run_dir, meta, artifacts)
    out_path = Path(args.out).resolve() if args.out else (run_dir / "release_audit_report.md")
    out_path.write_text(report, encoding="utf-8")
    print(f"Release audit report written: {out_path}")
    return 0


def collect_artifacts(run_dir: Path) -> dict[str, object]:
    state_machine = read_json_if_present(run_dir / "01_state_machine.json")
    refined_cases = read_json_if_present(run_dir / "04_testcases_refined.json")
    regression = read_json_if_present(run_dir / "05_regression_suite.json")
    checklist = read_text_if_present(run_dir / "06_release_checklist.md")
    return {
        "state_machine": state_machine,
        "refined_cases": refined_cases,
        "regression": regression,
        "checklist": checklist,
    }


def build_report(run_dir: Path, meta: dict, artifacts: dict[str, object]) -> str:
    summary = executive_summary(artifacts)
    risks = risk_lines(artifacts)
    checklist_lines = mandatory_checklist_lines(artifacts)
    week_plan = weekly_test_plan(artifacts)
    upgrade_plan = optimization_plan(artifacts)
    run_id = meta.get("run_id") or run_dir.name

    lines = [
        "# Didaunao Release Audit Report",
        "",
        f"- Run ID: {run_id}",
        f"- Domain: didaunao_release_audit",
        "",
        "## Executive Summary (GO/NO-GO)",
        "",
        summary,
        "",
        "## Mandatory Checklist Results",
        "",
    ]
    lines.extend(f"- {line}" for line in checklist_lines)
    lines.extend(
        [
            "",
            "## Risks & Gaps",
            "",
        ]
    )
    lines.extend(f"- {line}" for line in risks)
    lines.extend(
        [
            "",
            "## Testing Plan For This Week",
            "",
        ]
    )
    lines.extend(f"- {line}" for line in week_plan)
    lines.extend(
        [
            "",
            "## Optimization & Upgrade Plan (2-4 Weeks)",
            "",
        ]
    )
    lines.extend(f"- {line}" for line in upgrade_plan)

    checklist = artifacts["checklist"]
    if isinstance(checklist, str) and checklist.strip():
        lines.extend(
            [
                "",
                "## Source Release Checklist",
                "",
                checklist.strip(),
            ]
        )
    return "\n".join(lines).strip() + "\n"


def executive_summary(artifacts: dict[str, object]) -> str:
    incomplete = find_incomplete_artifacts(artifacts)
    if incomplete:
        return (
            "Current recommendation: NO-GO. "
            f"Evidence is incomplete in: {', '.join(incomplete)}."
        )

    unknown_count = count_unknowns(artifacts)
    if unknown_count > 0:
        return (
            "Current recommendation: NO-GO until UNKNOWN business truths are resolved. "
            f"Detected UNKNOWN markers: {unknown_count}."
        )

    regression = artifacts["regression"]
    selected = 0
    if isinstance(regression, dict):
        selected = len(regression.get("regression_ids") or [])
    return (
        "Current recommendation: GO candidate pending final human sign-off. "
        f"Regression selection contains {selected} testcase ids and no obvious placeholder evidence remains."
    )


def mandatory_checklist_lines(artifacts: dict[str, object]) -> list[str]:
    lines = []
    lines.extend(
        summarize_artifact_presence(
            "State machine evidence",
            artifacts["state_machine"],
            extra=_state_machine_summary(artifacts["state_machine"]),
        )
    )
    lines.extend(
        summarize_artifact_presence(
            "Refined testcase suite",
            artifacts["refined_cases"],
            extra=_testcase_summary(artifacts["refined_cases"]),
        )
    )
    lines.extend(
        summarize_artifact_presence(
            "Regression suite",
            artifacts["regression"],
            extra=_regression_summary(artifacts["regression"]),
        )
    )
    lines.extend(
        summarize_artifact_presence(
            "Release checklist",
            artifacts["checklist"],
            extra=_checklist_summary(artifacts["checklist"]),
        )
    )
    return lines


def risk_lines(artifacts: dict[str, object]) -> list[str]:
    lines = []
    incomplete = find_incomplete_artifacts(artifacts)
    for name in incomplete:
        lines.append(f"{name} is incomplete or still contains placeholder content.")

    state_machine = artifacts["state_machine"]
    if isinstance(state_machine, dict):
        unknowns = state_machine.get("unknowns") or []
        for item in unknowns[:8]:
            lines.append(f"Unknown business truth from state machine extraction: {item}")

    checklist = artifacts["checklist"]
    if isinstance(checklist, str):
        for line in checklist.splitlines():
            if "UNKNOWN" in line.upper():
                lines.append(f"Checklist contains unresolved unknown: {line.strip()}")
            if len(lines) >= 12:
                break

    if not lines:
        lines.append("No explicit unresolved gaps were auto-detected. Manual reviewer confirmation is still required.")
    return lines


def weekly_test_plan(artifacts: dict[str, object]) -> list[str]:
    refined_cases = artifacts["refined_cases"]
    regression = artifacts["regression"]
    lines: list[str] = []

    if isinstance(regression, dict):
        regression_ids = regression.get("regression_ids") or []
        lines.append(f"Execute the selected regression subset first: {len(regression_ids)} cases.")
    else:
        lines.append("Generate or finalize the regression suite before scheduling execution.")

    if isinstance(refined_cases, dict):
        testcases = refined_cases.get("testcases") or []
        p0_count = sum(1 for case in testcases if isinstance(case, dict) and case.get("priority") == "P0")
        focus_tags = top_tags(testcases, limit=5)
        lines.append(f"Prioritize all P0 release blockers this week: {p0_count} cases.")
        if focus_tags:
            lines.append(f"Primary focus areas by tag: {', '.join(focus_tags)}.")
    else:
        lines.append("Complete testcase refinement, then group this week's execution by release gate risk.")

    lines.append("Reserve one run for rollback rehearsal and one run for monitoring/alert verification.")
    lines.append("Track open UNKNOWN items daily and convert each one into an owner-assigned closure task.")
    return lines


def optimization_plan(artifacts: dict[str, object]) -> list[str]:
    lines = [
        "Strengthen release evidence automation for performance, crash/ANR, security, observability, and rollback checks.",
        "Convert repeated manual gate checks into reusable dashboards or scripts to reduce audit drift.",
        "Close UNKNOWN business rules in the KB source document and rebuild the index before the next release cycle.",
    ]

    refined_cases = artifacts["refined_cases"]
    if isinstance(refined_cases, dict):
        focus_tags = top_tags(refined_cases.get("testcases") or [], limit=4)
        if focus_tags:
            lines.append(f"Increase durable coverage in these high-signal areas: {', '.join(focus_tags)}.")
    else:
        lines.append("After testcase refinement is complete, rebalance long-term coverage across release-critical categories.")
    return lines


def summarize_artifact_presence(name: str, payload: object, *, extra: str | None = None) -> list[str]:
    if payload is None:
        return [f"{name}: missing."]
    if isinstance(payload, str) and is_placeholder_text(payload):
        return [f"{name}: placeholder or pending."]
    summary = f"{name}: present."
    if extra:
        summary = f"{summary} {extra}"
    return [summary]


def _state_machine_summary(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    states = payload.get("states") or []
    unknowns = payload.get("unknowns") or []
    return f"States={len(states)}, unknowns={len(unknowns)}."


def _testcase_summary(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    cases = payload.get("testcases") or []
    p0_count = sum(1 for case in cases if isinstance(case, dict) and case.get("priority") == "P0")
    return f"Cases={len(cases)}, P0={p0_count}."


def _regression_summary(payload: object) -> str | None:
    if not isinstance(payload, dict):
        return None
    regression_ids = payload.get("regression_ids") or []
    return f"Selected regression cases={len(regression_ids)}."


def _checklist_summary(payload: object) -> str | None:
    if not isinstance(payload, str):
        return None
    line_count = len([line for line in payload.splitlines() if line.strip()])
    return f"Checklist lines={line_count}."


def top_tags(testcases: list[object], limit: int) -> list[str]:
    counts: dict[str, int] = {}
    for case in testcases:
        if not isinstance(case, dict):
            continue
        for tag in case.get("tags") or []:
            if isinstance(tag, str) and tag.strip():
                counts[tag.strip()] = counts.get(tag.strip(), 0) + 1
    return [tag for tag, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def count_unknowns(artifacts: dict[str, object]) -> int:
    count = 0
    state_machine = artifacts["state_machine"]
    if isinstance(state_machine, dict):
        count += len(state_machine.get("unknowns") or [])
    checklist = artifacts["checklist"]
    if isinstance(checklist, str):
        count += checklist.upper().count("UNKNOWN")
    return count


def find_incomplete_artifacts(artifacts: dict[str, object]) -> list[str]:
    missing = []
    for name, payload in artifacts.items():
        if payload is None:
            missing.append(name)
        elif isinstance(payload, str) and is_placeholder_text(payload):
            missing.append(name)
        elif isinstance(payload, dict) and not payload:
            missing.append(name)
    return missing


def read_json_if_present(path: Path) -> dict | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if is_placeholder_text(text):
        return None
    try:
        return json.loads(strip_fenced_block(text))
    except json.JSONDecodeError:
        return None


def read_text_if_present(path: Path) -> str | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if is_placeholder_text(text):
        return text
    return strip_fenced_block(text)


def is_placeholder_text(text: str) -> bool:
    normalized = text.lstrip()
    return normalized.startswith(PLACEHOLDER_MARKER) or normalized.startswith("[PENDING INPUT:")


def strip_fenced_block(text: str) -> str:
    normalized = text.lstrip("\ufeff").strip()
    if not normalized.startswith("```"):
        return normalized
    lines = normalized.splitlines()
    if len(lines) >= 2 and lines[-1].strip() == "```":
        return "\n".join(lines[1:-1]).strip()
    return normalized


if __name__ == "__main__":
    sys.exit(main())
