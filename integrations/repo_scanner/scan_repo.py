from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    "bin",
    "build",
    "dist",
    "node_modules",
    "obj",
}
COUNTED_EXTENSIONS = {
    ".cs": "cs",
    ".dart": "dart",
    ".js": "js",
    ".json": "json",
    ".md": "md",
    ".ts": "ts",
    ".yaml": "yml",
    ".yml": "yml",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan a local source repository for release evidence.")
    parser.add_argument("--name", required=True, help="Logical source name, for example backend or app.")
    parser.add_argument("--path", required=True, help="Local filesystem path to scan.")
    parser.add_argument("--out", required=True, help="Output JSON path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = scan_repo(args.name, Path(args.path))
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Repo scan written: {out_path}")
    return 0


def scan_repo(name: str, repo_path: Path) -> dict[str, object]:
    path = repo_path.expanduser().resolve()
    payload: dict[str, object] = {
        "name": name,
        "path": str(path),
        "exists": path.exists(),
        "is_git": False,
        "git_head": None,
        "git_branch": None,
        "tech_stack": [],
        "file_counts": {
            "total": 0,
            "cs": 0,
            "dart": 0,
            "ts": 0,
            "js": 0,
            "yml": 0,
            "json": 0,
            "md": 0,
        },
        "key_files": [],
        "controller_files": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    if not path.exists():
        return payload

    git_info = read_git_info(path)
    payload["is_git"] = git_info["is_git"]
    payload["git_head"] = git_info["git_head"]
    payload["git_branch"] = git_info["git_branch"]

    key_files: list[dict[str, str]] = []
    controller_files: list[str] = []
    seen_key_files: set[tuple[str, str]] = set()
    seen_names: set[str] = set()
    seen_suffixes: set[str] = set()
    has_package_json = False
    has_pubspec = False
    has_docker = False
    has_compose = False
    has_react_signal = False

    file_counts = dict(payload["file_counts"])
    for file_path in iter_files(path):
        rel = file_path.relative_to(path).as_posix()
        suffix = file_path.suffix.lower()
        name_lower = file_path.name.lower()
        seen_names.add(name_lower)
        if suffix:
            seen_suffixes.add(suffix)

        file_counts["total"] += 1
        count_key = COUNTED_EXTENSIONS.get(suffix)
        if count_key is not None:
            file_counts[count_key] += 1

        if name_lower == "package.json":
            has_package_json = True
        if name_lower == "pubspec.yaml":
            has_pubspec = True
        if name_lower == "dockerfile" or name_lower.endswith(".dockerfile"):
            has_docker = True
        if is_compose_file(name_lower):
            has_compose = True
        if name_lower.endswith((".tsx", ".jsx")) or file_path.suffixes[-2:] == [".d", ".ts"]:
            has_react_signal = True
        if rel.lower().startswith(".github/workflows/"):
            add_key_file(key_files, seen_key_files, rel, "ci")

        key_kind = classify_key_file(file_path)
        if key_kind is not None:
            add_key_file(key_files, seen_key_files, rel, key_kind)

        if suffix == ".cs" and file_path.name.endswith("Controller.cs"):
            controller_files.append(rel)

    tech_stack = detect_tech_stack(
        seen_suffixes=seen_suffixes,
        seen_names=seen_names,
        has_package_json=has_package_json,
        has_pubspec=has_pubspec,
        has_docker=has_docker,
        has_compose=has_compose,
        has_react_signal=has_react_signal,
        controller_files=controller_files,
    )

    payload["file_counts"] = file_counts
    payload["tech_stack"] = tech_stack
    payload["key_files"] = sorted(key_files, key=lambda item: (item["kind"], item["rel"]))
    payload["controller_files"] = sorted(controller_files) if "dotnet" in tech_stack else []
    return payload


def iter_files(root: Path) -> Iterable[Path]:
    for current_root, dirs, files in root.walk():
        dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRS]
        current_path = Path(current_root)
        for file_name in files:
            yield current_path / file_name


def read_git_info(path: Path) -> dict[str, object]:
    inside = run_git(path, "rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0:
        return {"is_git": False, "git_head": None, "git_branch": None}

    head = run_git(path, "rev-parse", "HEAD")
    branch = run_git(path, "rev-parse", "--abbrev-ref", "HEAD")
    return {
        "is_git": True,
        "git_head": head.stdout.strip() or None,
        "git_branch": branch.stdout.strip() or None,
    }


def run_git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(path), *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return subprocess.CompletedProcess(args=["git", *args], returncode=1, stdout="", stderr="")


def classify_key_file(path: Path) -> str | None:
    rel = path.as_posix().lower()
    name = path.name.lower()
    if name == "dockerfile" or name.endswith(".dockerfile"):
        return "dockerfile"
    if is_compose_file(name):
        return "compose"
    if name in {".env.example", ".env.sample", ".env.template"}:
        return "env_example"
    if name.startswith("readme"):
        return "readme"
    if name in {".gitlab-ci.yml", "azure-pipelines.yml", "azure-pipeline.yml"}:
        return "ci"
    if rel.startswith(".github/workflows/"):
        return "ci"
    if name in {
        "appsettings.json",
        "appsettings.development.json",
        "package.json",
        "tsconfig.json",
        "pubspec.yaml",
        "vite.config.js",
        "vite.config.ts",
        "next.config.js",
        "next.config.mjs",
        "web.config",
    }:
        return "config"
    return None


def is_compose_file(name: str) -> bool:
    return name in {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}


def add_key_file(
    key_files: list[dict[str, str]],
    seen_key_files: set[tuple[str, str]],
    rel: str,
    kind: str,
) -> None:
    key = (rel, kind)
    if key in seen_key_files:
        return
    seen_key_files.add(key)
    key_files.append({"rel": rel, "kind": kind})


def detect_tech_stack(
    *,
    seen_suffixes: set[str],
    seen_names: set[str],
    has_package_json: bool,
    has_pubspec: bool,
    has_docker: bool,
    has_compose: bool,
    has_react_signal: bool,
    controller_files: list[str],
) -> list[str]:
    stack: list[str] = []
    if controller_files or ".csproj" in seen_suffixes or ".sln" in seen_suffixes or ".cs" in seen_suffixes:
        stack.append("dotnet")
    if has_pubspec or ".dart" in seen_suffixes:
        stack.append("flutter")
    if has_package_json and (has_react_signal or "vite.config.ts" in seen_names or "vite.config.js" in seen_names):
        stack.append("react")
    elif has_package_json:
        stack.append("node")
    if has_docker or has_compose:
        stack.append("docker")
    return stack


if __name__ == "__main__":
    raise SystemExit(main())
