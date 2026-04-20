from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.failure_analysis.integration.pytest_bridge import (  # noqa: E402
    DEFAULT_ANALYSIS_REPORT,
    DEFAULT_PYTEST_REPORT,
    analyze_pytest_report_file,
)


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze pytest JSON failures into grouped failure intelligence.")
    parser.add_argument(
        "--report",
        default=str(DEFAULT_PYTEST_REPORT),
        help="Path to pytest report JSON",
    )
    parser.add_argument(
        "--out",
        default=str(DEFAULT_ANALYSIS_REPORT),
        help="Path to failure analysis output JSON",
    )
    parser.add_argument(
        "--no-history",
        action="store_true",
        help="Disable writing history artifact",
    )
    return parser.parse_args()


def main() -> int:
    configure_logging()
    args = parse_args()
    report_path = Path(args.report)
    output_path = Path(args.out)
    try:
        result = analyze_pytest_report_file(
            pytest_report_path=report_path,
            output_path=output_path,
            write_history=not args.no_history,
        )
        summary = result.get("summary", {})
        logging.info(
            "failure_analysis_done | failed=%s | groups=%s | highest=%s | output=%s",
            summary.get("total_failed"),
            summary.get("total_groups"),
            summary.get("highest_severity"),
            output_path,
        )
        return 0
    except Exception as exc:
        logging.exception("failure_analysis_failed | error=%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

