from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator.failure_analysis.integration.pytest_bridge import analyze_pytest_report_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze pytest json-report failures into grouped intelligence.")
    parser.add_argument(
        "--report",
        default="artifacts/pytest/pytest_report.json",
        help="Path to pytest-json-report file.",
    )
    parser.add_argument(
        "--out",
        default="artifacts/failure_analysis/failure_analysis_report.json",
        help="Path to write failure analysis report.",
    )
    parser.add_argument(
        "--history",
        default="artifacts/failure_analysis/history.json",
        help="Path to write failure analysis history.",
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Disable history append.",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="[failure-analysis] %(message)s")
    args = parse_args()

    report = analyze_pytest_report_file(
        pytest_report_path=Path(args.report),
        output_path=Path(args.out),
        history_path=Path(args.history),
        write_history=not args.no_history,
    )
    if report is None:
        logging.warning("pytest report not found: %s", args.report)
        return 1

    summary = report.summary
    logging.info(
        "failure_analysis_done | failed=%s | groups=%s | highest=%s",
        summary.total_failed,
        summary.total_groups,
        summary.highest_severity,
    )
    logging.info("output=%s", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
