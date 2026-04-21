"""Adapter Contract Validator + CI Smoke Validation v1."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from orchestrator.adapters.evidence_context import get_adapter_evidence_context
from orchestrator.adapters.validator import validate_adapter


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate project adapter contract and smoke compatibility.")
    parser.add_argument("--name", required=True, help="Adapter name to validate.")
    parser.add_argument("--json", action="store_true", help="Print JSON report to stdout.")
    parser.add_argument("--strict", action="store_true", help="Escalate warnings to fail.")
    parser.add_argument("--ci", action="store_true", help="Enable CI fail-fast style validation.")
    parser.add_argument("--verbose", action="store_true", help="Print detailed check lines.")
    return parser.parse_args()


def _print_human_summary(report_dict: dict, output_path: Path) -> None:
    print(f"[adapter-validation] adapter={report_dict['adapter_name']}")
    print(f"[adapter-validation] status={report_dict['status']} strict={report_dict['strict_mode']} ci={report_dict['ci_mode']}")
    print(
        "[adapter-validation] checks="
        f"contract:{len(report_dict['contract_checks'])} "
        f"loader:{len(report_dict['loader_checks'])} "
        f"structure:{len(report_dict['structure_checks'])} "
        f"core_smoke:{len(report_dict['core_smoke_checks'])}"
    )
    print(f"[adapter-validation] warnings={len(report_dict['warnings'])} errors={len(report_dict['errors'])}")
    if report_dict["warnings"]:
        print("[adapter-validation] top warnings:")
        for warning in report_dict["warnings"][:5]:
            print(f"  - {warning}")
    if report_dict["errors"]:
        print("[adapter-validation] top errors:")
        for error in report_dict["errors"][:5]:
            print(f"  - {error}")
    if report_dict["recommendations"]:
        print("[adapter-validation] recommendations:")
        for item in report_dict["recommendations"][:5]:
            print(f"  - {item}")
    print(f"[adapter-validation] json={output_path}")


def main() -> None:
    args = _parse_args()
    adapter_name = args.name.strip().lower()
    report = validate_adapter(
        adapter_name,
        strict=args.strict,
        ci=args.ci,
        verbose=args.verbose,
    )
    payload = report.to_dict()
    ctx = get_adapter_evidence_context(adapter_name)
    output_path = ctx.write_json("adapter_validation_report", payload)

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        _print_human_summary({**payload}, output_path)

    if payload["status"] == "fail":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
