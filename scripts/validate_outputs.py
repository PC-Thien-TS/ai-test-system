from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, List


PLACEHOLDER_MARKER = "MANUAL OUTPUT PLACEHOLDER"
PENDING_INPUT_PREFIX = "[PENDING INPUT:"
GENERIC_TESTCASE_ID_PATTERN = re.compile(r"^TC-[A-Z0-9-]+-[0-9]{3}$")
PRIORITIES = {"P0", "P1", "P2", "P3"}
TEST_TYPES = {"smoke", "regression"}
ROOT_KEYS = {"feature", "testcases"}
FEATURE_KEYS = {"name", "scope"}
REGRESSION_ROOT_KEYS = {"feature", "regression_ids", "notes"}
REGRESSION_FEATURE_KEYS = {"name"}
TESTCASE_KEYS = {
    "id",
    "title",
    "preconditions",
    "steps",
    "expected",
    "priority",
    "type",
    "tags",
    "notes",
}


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    message: str


@dataclass(frozen=True)
class ValidationContext:
    run_dir: Path
    domain: str
    testcase_prefix: str
    allow_incomplete: bool | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate manual pipeline outputs.")
    parser.add_argument("run_dir", help="Path to outputs/<domain>/<run_id>")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir).resolve()
    repo_root = Path(__file__).resolve().parents[1]
    testcase_schema_path = repo_root / "schemas" / "test_case.schema.json"
    regression_schema_path = repo_root / "schemas" / "regression.schema.json"

    if not run_dir.exists():
        print(f"[FAIL] Run directory does not exist: {run_dir}")
        return 1

    for schema_path in (testcase_schema_path, regression_schema_path):
        if not schema_path.exists():
            print(f"[FAIL] Missing schema file: {schema_path}")
            return 1
        try:
            json.loads(schema_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(
                f"[FAIL] Schema file is not valid JSON: {schema_path} "
                f"(line {exc.lineno}, column {exc.colno})"
            )
            return 1

    ctx = build_context(run_dir)
    placeholder_ok = validate_prompt_placeholders(ctx)
    raw_ok, _ = validate_file(
        "03_testcases_raw.json",
        run_dir / "03_testcases_raw.json",
        validator_name="test_case",
        ctx=ctx,
    )
    refined_ok, refined_data = validate_file(
        "04_testcases_refined.json",
        run_dir / "04_testcases_refined.json",
        validator_name="test_case",
        ctx=ctx,
    )
    regression_ok, _ = validate_file(
        "05_regression_suite.json",
        run_dir / "05_regression_suite.json",
        validator_name="regression",
        ctx=ctx,
        refined_suite=refined_data,
    )

    all_ok = placeholder_ok and raw_ok and refined_ok and regression_ok
    if all_ok:
        print(
            f"[OK] Outputs in {run_dir} match schemas/test_case.schema.json "
            "and schemas/regression.schema.json"
        )
        return 0
    return 1


def build_context(run_dir: Path) -> ValidationContext:
    meta_path = run_dir / "run_meta.json"
    allow_incomplete: bool | None = None
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            meta = {}
        domain = str(meta.get("domain") or run_dir.parent.name)
        if "allow_incomplete" in meta:
            allow_incomplete = bool(meta.get("allow_incomplete"))
    else:
        domain = run_dir.parent.name
    return ValidationContext(
        run_dir=run_dir,
        domain=domain,
        testcase_prefix=f"TC-{domain.upper().replace('_', '-')}-",
        allow_incomplete=allow_incomplete,
    )


def validate_prompt_placeholders(ctx: ValidationContext) -> bool:
    if ctx.allow_incomplete is not False:
        return True

    pending_files = []
    for step in range(1, 7):
        prompt_path = ctx.run_dir / f"step_{step:02d}_prompt.txt"
        if prompt_path.exists() and contains_pending_marker(prompt_path):
            pending_files.append(prompt_path.name)
        kb_path = ctx.run_dir / f"kb_context_step{step:02d}.txt"
        if kb_path.exists() and contains_pending_marker(kb_path):
            pending_files.append(kb_path.name)

    if not pending_files:
        return True

    print("[FAIL] prompt_context")
    print("  - Pending-input markers are present even though allow_incomplete=false.")
    print(f"  - Affected files: {', '.join(pending_files)}")
    return False


def contains_pending_marker(path: Path) -> bool:
    return path.read_text(encoding="utf-8", errors="replace").lstrip().startswith(PENDING_INPUT_PREFIX)


def validate_file(
    label: str,
    path: Path,
    *,
    validator_name: str,
    ctx: ValidationContext,
    refined_suite: Any | None = None,
) -> tuple[bool, Any | None]:
    if not path.exists():
        print(f"[FAIL] {label}")
        print(f"  - Missing file: {path}")
        return False, None

    raw_text = path.read_text(encoding="utf-8", errors="replace")
    if raw_text.lstrip().startswith(PLACEHOLDER_MARKER):
        print(f"[FAIL] {label}")
        print("  - File still contains the manual placeholder text.")
        print("  - Replace it with the model output and rerun the validator.")
        return False, None

    payload_text = strip_fenced_block(raw_text)
    try:
        data = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        print(f"[FAIL] {label}")
        print(f"  - Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}")
        return False, None

    if validator_name == "test_case":
        issues = validate_testcase_suite(data, ctx)
    elif validator_name == "regression":
        issues = validate_regression_suite(data, refined_suite, ctx)
    else:
        raise ValueError(f"Unknown validator_name: {validator_name}")

    if issues:
        print(f"[FAIL] {label}")
        for issue in issues:
            print(f"  - {issue.path}: {issue.message}")
        return False, None

    print(f"[OK] {label}")
    return True, data


def validate_testcase_suite(data: Any, ctx: ValidationContext) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    if not isinstance(data, dict):
        return [ValidationIssue("$", "Expected a JSON object at the root.")]

    check_required_and_extra_keys(data, ROOT_KEYS, "$", issues)
    feature = data.get("feature")
    if feature is None:
        issues.append(ValidationIssue("$.feature", "Missing required field."))
    elif not isinstance(feature, dict):
        issues.append(ValidationIssue("$.feature", "Expected an object."))
    else:
        check_required_and_extra_keys(feature, FEATURE_KEYS, "$.feature", issues)
        check_non_empty_string(feature.get("name"), "$.feature.name", issues)
        check_non_empty_string(feature.get("scope"), "$.feature.scope", issues)

    testcases = data.get("testcases")
    if testcases is None:
        issues.append(ValidationIssue("$.testcases", "Missing required field."))
        return issues
    if not isinstance(testcases, list):
        issues.append(ValidationIssue("$.testcases", "Expected an array."))
        return issues
    if not testcases:
        issues.append(ValidationIssue("$.testcases", "Expected at least 1 testcase."))
        return issues

    seen_ids = set()
    for index, testcase in enumerate(testcases):
        case_path = f"$.testcases[{index}]"
        if not isinstance(testcase, dict):
            issues.append(ValidationIssue(case_path, "Expected an object."))
            continue
        check_required_and_extra_keys(testcase, TESTCASE_KEYS, case_path, issues)
        testcase_id = testcase.get("id")
        check_non_empty_string(testcase_id, f"{case_path}.id", issues)
        if isinstance(testcase_id, str):
            if not GENERIC_TESTCASE_ID_PATTERN.match(testcase_id):
                issues.append(
                    ValidationIssue(
                        f"{case_path}.id",
                        "Expected format TC-<DOMAIN>-001.",
                    )
                )
            elif not testcase_id.startswith(ctx.testcase_prefix):
                issues.append(
                    ValidationIssue(
                        f"{case_path}.id",
                        f"Expected prefix {ctx.testcase_prefix} for domain '{ctx.domain}'.",
                    )
                )
            elif testcase_id in seen_ids:
                issues.append(ValidationIssue(f"{case_path}.id", "Duplicate testcase id."))
            else:
                seen_ids.add(testcase_id)

        check_non_empty_string(testcase.get("title"), f"{case_path}.title", issues)
        check_string_array(testcase.get("preconditions"), f"{case_path}.preconditions", issues, min_items=0)
        check_string_array(testcase.get("steps"), f"{case_path}.steps", issues, min_items=3, max_items=8)
        check_string_array(testcase.get("expected"), f"{case_path}.expected", issues, min_items=1, max_items=4)
        check_enum(testcase.get("priority"), f"{case_path}.priority", PRIORITIES, issues)
        check_enum(testcase.get("type"), f"{case_path}.type", TEST_TYPES, issues)
        check_string_array(testcase.get("tags"), f"{case_path}.tags", issues, min_items=1)
        notes = testcase.get("notes")
        if notes is None:
            issues.append(ValidationIssue(f"{case_path}.notes", "Missing required field."))
        elif not isinstance(notes, str):
            issues.append(ValidationIssue(f"{case_path}.notes", "Expected a string."))

    return issues


def validate_regression_suite(
    data: Any,
    refined_suite: Any | None,
    ctx: ValidationContext,
) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    if not isinstance(data, dict):
        return [ValidationIssue("$", "Expected a JSON object at the root.")]

    check_required_and_extra_keys(data, REGRESSION_ROOT_KEYS, "$", issues)
    feature = data.get("feature")
    if feature is None:
        issues.append(ValidationIssue("$.feature", "Missing required field."))
    elif not isinstance(feature, dict):
        issues.append(ValidationIssue("$.feature", "Expected an object."))
    else:
        check_required_and_extra_keys(feature, REGRESSION_FEATURE_KEYS, "$.feature", issues)
        check_non_empty_string(feature.get("name"), "$.feature.name", issues)

    regression_ids = data.get("regression_ids")
    selected_ids: list[str] = []
    if regression_ids is None:
        issues.append(ValidationIssue("$.regression_ids", "Missing required field."))
    elif not isinstance(regression_ids, list):
        issues.append(ValidationIssue("$.regression_ids", "Expected an array."))
    elif not regression_ids:
        issues.append(ValidationIssue("$.regression_ids", "Expected at least 1 testcase id."))
    else:
        seen_ids = set()
        for index, testcase_id in enumerate(regression_ids):
            path = f"$.regression_ids[{index}]"
            if not isinstance(testcase_id, str):
                issues.append(ValidationIssue(path, "Expected a string."))
                continue
            if not GENERIC_TESTCASE_ID_PATTERN.match(testcase_id):
                issues.append(ValidationIssue(path, "Expected format TC-<DOMAIN>-001."))
                continue
            if not testcase_id.startswith(ctx.testcase_prefix):
                issues.append(
                    ValidationIssue(path, f"Expected prefix {ctx.testcase_prefix} for domain '{ctx.domain}'.")
                )
                continue
            if testcase_id in seen_ids:
                issues.append(ValidationIssue(path, "Duplicate testcase id."))
                continue
            seen_ids.add(testcase_id)
            selected_ids.append(testcase_id)

    notes = data.get("notes")
    check_non_empty_string(notes, "$.notes", issues)

    if refined_suite is None:
        issues.append(
            ValidationIssue(
                "$.regression_ids",
                "Cannot validate regression ids without a valid 04_testcases_refined.json file.",
            )
        )
        return issues

    refined_cases = refined_suite.get("testcases")
    if not isinstance(refined_cases, list):
        issues.append(
            ValidationIssue(
                "$.regression_ids",
                "04_testcases_refined.json does not contain a valid testcase list.",
            )
        )
        return issues

    refined_ids = {case["id"] for case in refined_cases if isinstance(case, dict) and "id" in case}
    p0_ids = {
        case["id"]
        for case in refined_cases
        if isinstance(case, dict) and case.get("priority") == "P0" and isinstance(case.get("id"), str)
    }
    unknown_ids = [testcase_id for testcase_id in selected_ids if testcase_id not in refined_ids]
    if unknown_ids:
        issues.append(
            ValidationIssue(
                "$.regression_ids",
                f"Regression ids must be a subset of refined testcase ids. Unknown ids: {', '.join(unknown_ids)}.",
            )
        )

    missing_p0 = sorted(p0_ids - set(selected_ids))
    if missing_p0:
        issues.append(
            ValidationIssue(
                "$.regression_ids",
                f"Regression suite must include all P0 testcases. Missing: {', '.join(missing_p0)}.",
            )
        )

    total_tests = len(refined_cases)
    selected_count = len(selected_ids)
    if total_tests == 0:
        issues.append(ValidationIssue("$.regression_ids", "04_testcases_refined.json contains zero testcases."))
        return issues

    ratio = selected_count / total_tests
    p0_ratio = len(p0_ids) / total_tests
    if ratio < 0.25:
        issues.append(
            ValidationIssue(
                "$.regression_ids",
                f"Regression suite selects {selected_count}/{total_tests} tests ({ratio:.1%}), below the 25% minimum.",
            )
        )
    if ratio > 0.40 and p0_ratio <= 0.40:
        issues.append(
            ValidationIssue(
                "$.regression_ids",
                f"Regression suite selects {selected_count}/{total_tests} tests ({ratio:.1%}), above the 40% maximum without a P0 override.",
            )
        )
    if p0_ratio > 0.40 and isinstance(notes, str):
        notes_lower = notes.lower()
        mentions_override = "override" in notes_lower or "exceed" in notes_lower or "40%" in notes_lower
        mentions_p0 = "p0" in notes_lower
        if not (mentions_override and mentions_p0):
            issues.append(
                ValidationIssue(
                    "$.notes",
                    "Notes must explain the ratio override when P0 tests alone exceed 40% of total tests.",
                )
            )

    return issues


def check_required_and_extra_keys(
    data: dict[str, Any],
    expected_keys: set[str],
    path: str,
    issues: List[ValidationIssue],
) -> None:
    missing_keys = sorted(expected_keys - set(data.keys()))
    extra_keys = sorted(set(data.keys()) - expected_keys)
    for key in missing_keys:
        issues.append(ValidationIssue(f"{path}.{key}", "Missing required field."))
    for key in extra_keys:
        issues.append(ValidationIssue(f"{path}.{key}", "Unexpected field."))


def check_non_empty_string(value: Any, path: str, issues: List[ValidationIssue]) -> None:
    if value is None:
        issues.append(ValidationIssue(path, "Missing required field."))
        return
    if not isinstance(value, str):
        issues.append(ValidationIssue(path, "Expected a string."))
        return
    if not value.strip():
        issues.append(ValidationIssue(path, "String must not be empty."))


def check_enum(
    value: Any,
    path: str,
    allowed_values: Iterable[str],
    issues: List[ValidationIssue],
) -> None:
    if value is None:
        issues.append(ValidationIssue(path, "Missing required field."))
        return
    if not isinstance(value, str):
        issues.append(ValidationIssue(path, "Expected a string."))
        return
    if value not in allowed_values:
        issues.append(ValidationIssue(path, f"Expected one of: {', '.join(sorted(allowed_values))}."))


def check_string_array(
    value: Any,
    path: str,
    issues: List[ValidationIssue],
    min_items: int,
    max_items: int | None = None,
) -> None:
    if value is None:
        issues.append(ValidationIssue(path, "Missing required field."))
        return
    if not isinstance(value, list):
        issues.append(ValidationIssue(path, "Expected an array."))
        return
    if len(value) < min_items:
        issues.append(ValidationIssue(path, f"Expected at least {min_items} item(s)."))
    if max_items is not None and len(value) > max_items:
        issues.append(ValidationIssue(path, f"Expected at most {max_items} item(s)."))
    for index, item in enumerate(value):
        if not isinstance(item, str):
            issues.append(ValidationIssue(f"{path}[{index}]", "Expected a string."))
        elif not item.strip():
            issues.append(ValidationIssue(f"{path}[{index}]", "String must not be empty."))


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
