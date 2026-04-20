from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run pytest and persist json report + stdout/stderr artifacts.")
    parser.add_argument(
        "--report-path",
        default="artifacts/pytest/pytest_report.json",
        help="Output path for pytest-json-report output.",
    )
    parser.add_argument(
        "--stdout-path",
        default="artifacts/pytest/pytest_stdout.txt",
        help="Output path for combined stdout/stderr.",
    )
    parser.add_argument(
        "pytest_args",
        nargs="*",
        help="Additional pytest arguments. Defaults to running full pytest discovery.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report_path = Path(args.report_path)
    stdout_path = Path(args.stdout_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    stdout_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--json-report",
        "--json-report-file",
        str(report_path),
    ]
    cmd.extend(args.pytest_args)

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    stdout_blob = (
        "=== PYTEST STDOUT ===\n"
        f"{proc.stdout}\n"
        "=== PYTEST STDERR ===\n"
        f"{proc.stderr}\n"
    )
    stdout_path.write_text(stdout_blob, encoding="utf-8")

    # Preserve normal command-line experience while persisting artifacts.
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, file=sys.stderr, end="")

    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())

