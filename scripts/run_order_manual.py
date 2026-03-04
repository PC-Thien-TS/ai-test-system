from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.run_domain_manual import run_manual_flow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate manual Order pipeline prompts.")
    parser.add_argument(
        "--run-id",
        help="Resume or regenerate an existing run folder. If omitted, a new run id is created.",
    )
    parser.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Generate downstream prompts with pending-input markers instead of aborting on missing upstream artifacts.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = run_manual_flow(
        domain="order",
        run_id=args.run_id,
        allow_incomplete=args.allow_incomplete,
        runner_name="run_order_manual",
    )
    print(f"Run folder ready: {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
