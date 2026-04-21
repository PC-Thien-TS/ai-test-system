from __future__ import annotations

import argparse
import subprocess
import sys
from uuid import uuid4
from pathlib import Path


DEFAULT_BASETEMP_ROOT = Path(".pytest_tmp")
FALLBACK_BASETEMP_ROOT = Path("artifacts") / "pytest" / "tmp"
DEFAULT_IGNORES = (
    DEFAULT_BASETEMP_ROOT,
    FALLBACK_BASETEMP_ROOT,
    Path("tests") / "tmp_pytest_lark",
)


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
    args, pytest_args = parser.parse_known_args()
    args.pytest_args = pytest_args
    if args.pytest_args and args.pytest_args[0] == "--":
        args.pytest_args = args.pytest_args[1:]
    return args


def _has_option(pytest_args: list[str], option_name: str) -> bool:
    return any(arg == option_name or arg.startswith(f"{option_name}=") for arg in pytest_args)


def _safe_basetemp() -> Path:
    run_dir_name = f"run_pytest_with_report_{uuid4().hex}"
    try:
        DEFAULT_BASETEMP_ROOT.mkdir(parents=True, exist_ok=True)
        probe = DEFAULT_BASETEMP_ROOT / ".write_probe"
        probe.write_text("", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return DEFAULT_BASETEMP_ROOT / run_dir_name
    except OSError:
        FALLBACK_BASETEMP_ROOT.mkdir(parents=True, exist_ok=True)
        return FALLBACK_BASETEMP_ROOT / run_dir_name


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

    if not _has_option(args.pytest_args, "--basetemp"):
        cmd.extend(["--basetemp", str(_safe_basetemp())])

    existing_ignores = {
        arg.split("=", 1)[1] for arg in args.pytest_args if arg.startswith("--ignore=")
    }
    for ignore_path in DEFAULT_IGNORES:
        ignore_value = str(ignore_path)
        if ignore_value not in existing_ignores:
            cmd.extend(["--ignore", ignore_value])

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
