from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "artifacts" / "pytest"
REPORT_PATH = ARTIFACT_DIR / "pytest_report.json"
STDOUT_PATH = ARTIFACT_DIR / "pytest_stdout.txt"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )


def ensure_dirs() -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run pytest with pytest-json-report and persist stdout/report artifacts.",
        add_help=True,
    )
    parser.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Optional additional args passed directly to pytest.",
    )
    return parser.parse_args()


def build_pytest_cmd(extra_args: List[str]) -> List[str]:
    args = list(extra_args or [])
    if args and args[0] == "--":
        args = args[1:]
    return [
        sys.executable,
        "-m",
        "pytest",
        "--json-report",
        f"--json-report-file={REPORT_PATH}",
        *args,
    ]


def write_stdout_file(stdout: str, stderr: str, cmd: List[str], exit_code: int) -> None:
    content = [
        f"timestamp_utc={utc_now_iso()}",
        f"cmd={' '.join(cmd)}",
        f"exit_code={exit_code}",
        "",
        "=== STDOUT ===",
        stdout or "",
        "",
        "=== STDERR ===",
        stderr or "",
    ]
    STDOUT_PATH.write_text("\n".join(content), encoding="utf-8")


def write_fallback_report(exit_code: int, error: str = "") -> None:
    if REPORT_PATH.exists():
        return
    fallback: Dict[str, Any] = {
        "created": utc_now_iso(),
        "exitcode": exit_code,
        "summary": {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "error": 1 if exit_code != 0 else 0,
        },
        "tests": [],
        "internal_error": error,
    }
    REPORT_PATH.write_text(json.dumps(fallback, indent=2), encoding="utf-8")


def main() -> int:
    configure_logging()
    args = parse_args()
    ensure_dirs()

    cmd = build_pytest_cmd(args.pytest_args)
    logging.info("pytest_runner_start | report=%s | stdout=%s", REPORT_PATH, STDOUT_PATH)

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        logging.exception("pytest_runner_exception")
        write_stdout_file("", f"{type(exc).__name__}: {exc}", cmd, 2)
        write_fallback_report(2, error=f"{type(exc).__name__}: {exc}")
        return 2

    write_stdout_file(proc.stdout, proc.stderr, cmd, proc.returncode)
    write_fallback_report(proc.returncode)
    logging.info("pytest_runner_done | exit_code=%s | report_exists=%s", proc.returncode, REPORT_PATH.exists())
    return int(proc.returncode)


if __name__ == "__main__":
    raise SystemExit(main())

