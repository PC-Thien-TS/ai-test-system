from __future__ import annotations

import contextlib
import importlib
import inspect
import os
import subprocess
import sys
from dataclasses import is_dataclass
from pathlib import Path
from typing import Any, Iterator

from orchestrator.adapters.base.adapter_contract import ProjectAdapter
from orchestrator.adapters.base.models import BlockerClassification, DefectFamilyDefinition, FlowDefinition
from orchestrator.adapters.base.validation_models import AdapterValidationReport, ValidationCheck


REPO_ROOT = Path(__file__).resolve().parents[2]


def _push_check(target: list[ValidationCheck], name: str, status: str, details: str) -> None:
    target.append(ValidationCheck(name=name, status=status, details=details))


@contextlib.contextmanager
def _adapter_env(adapter_name: str) -> Iterator[None]:
    previous = os.getenv("AI_TESTING_ADAPTER")
    os.environ["AI_TESTING_ADAPTER"] = adapter_name
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("AI_TESTING_ADAPTER", None)
        else:
            os.environ["AI_TESTING_ADAPTER"] = previous


def _reload(module_name: str) -> Any:
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


def _resolve_adapter(adapter_name: str) -> tuple[ProjectAdapter | None, str, str | None]:
    with _adapter_env(adapter_name):
        loader = _reload("orchestrator.adapters.loader")
        resolved_id = loader.get_active_adapter_id()
        try:
            adapter = loader.get_active_adapter()
        except Exception as exc:
            return None, resolved_id, str(exc)
        return adapter, resolved_id, None


def _required_methods() -> list[str]:
    methods = sorted(getattr(ProjectAdapter, "__abstractmethods__", set()))
    return methods


def _validate_contract(report: AdapterValidationReport, adapter: ProjectAdapter) -> None:
    methods = _required_methods()
    missing = [method for method in methods if not callable(getattr(adapter, method, None))]
    if missing:
        _push_check(
            report.contract_checks,
            "required_methods",
            "fail",
            f"Missing callable adapter methods: {', '.join(missing)}",
        )
        report.errors.append(f"Missing required adapter methods: {', '.join(missing)}")
    else:
        _push_check(
            report.contract_checks,
            "required_methods",
            "pass",
            f"All required adapter methods are callable ({len(methods)} methods).",
        )

    try:
        product_name = adapter.get_product_name()
        if isinstance(product_name, str) and product_name.strip():
            _push_check(report.contract_checks, "product_name", "pass", f"Product name: {product_name}")
        else:
            raise ValueError("product name is empty")
    except Exception as exc:
        _push_check(report.contract_checks, "product_name", "fail", f"get_product_name failed: {exc}")
        report.errors.append(f"get_product_name failed: {exc}")

    try:
        flow_registry = adapter.get_flow_registry()
        if not isinstance(flow_registry, dict) or not flow_registry:
            raise ValueError("flow registry is empty or non-dict")
        invalid = [k for k, v in flow_registry.items() if not isinstance(k, str) or not isinstance(v, FlowDefinition)]
        if invalid:
            raise ValueError(f"invalid flow entries: {invalid}")
        _push_check(
            report.contract_checks,
            "flow_registry_contract",
            "pass",
            f"Flow registry has {len(flow_registry)} flow definitions.",
        )
    except Exception as exc:
        _push_check(report.contract_checks, "flow_registry_contract", "fail", f"Flow registry invalid: {exc}")
        report.errors.append(f"Flow registry invalid: {exc}")

    try:
        suite_registry = adapter.get_suite_catalog()
        if not isinstance(suite_registry, dict) or not suite_registry:
            raise ValueError("suite registry is empty or non-dict")
        for key, value in suite_registry.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                raise ValueError(f"suite entry invalid: {key}")
            for field in ("suite", "priority", "blast_radius"):
                if not isinstance(value.get(field), str) or not value.get(field):
                    raise ValueError(f"suite '{key}' missing required field '{field}'")
        _push_check(
            report.contract_checks,
            "suite_registry_contract",
            "pass",
            f"Suite registry has {len(suite_registry)} entries.",
        )
    except Exception as exc:
        _push_check(report.contract_checks, "suite_registry_contract", "fail", f"Suite registry invalid: {exc}")
        report.errors.append(f"Suite registry invalid: {exc}")

    try:
        families = adapter.get_defect_families()
        if not isinstance(families, list):
            raise ValueError("defect family registry is not a list")
        malformed = 0
        for row in families:
            if isinstance(row, DefectFamilyDefinition):
                continue
            if is_dataclass(row):
                continue
            if isinstance(row, dict) and {"family_id", "title", "type"}.issubset(set(row.keys())):
                continue
            malformed += 1
        if malformed:
            raise ValueError(f"{malformed} malformed defect family entries")
        _push_check(
            report.contract_checks,
            "defect_registry_contract",
            "pass",
            f"Defect family registry is structurally valid ({len(families)} entries).",
        )
    except Exception as exc:
        _push_check(report.contract_checks, "defect_registry_contract", "fail", f"Defect registry invalid: {exc}")
        report.errors.append(f"Defect registry invalid: {exc}")

    try:
        blocker = adapter.classify_blocker({"message": "seed missing"})
        if not isinstance(blocker, BlockerClassification):
            raise ValueError("classify_blocker must return BlockerClassification")
        _push_check(
            report.contract_checks,
            "blocker_classification_contract",
            "pass",
            f"Blocker classification returns type '{blocker.blocker_type}'.",
        )
    except Exception as exc:
        _push_check(
            report.contract_checks,
            "blocker_classification_contract",
            "fail",
            f"classify_blocker invalid: {exc}",
        )
        report.errors.append(f"classify_blocker invalid: {exc}")

    try:
        risk_rules = adapter.get_risk_rules()
        scoring = adapter.get_release_scoring_rules()
        if not isinstance(risk_rules, dict):
            raise ValueError("risk rules must be dict")
        if not isinstance(scoring, dict):
            raise ValueError("release scoring rules must be dict")
        _push_check(
            report.contract_checks,
            "risk_rules_contract",
            "pass",
            "Risk and release scoring rules are available.",
        )
    except Exception as exc:
        _push_check(report.contract_checks, "risk_rules_contract", "fail", f"Risk rule contract invalid: {exc}")
        report.errors.append(f"Risk rule contract invalid: {exc}")


def _validate_structure(report: AdapterValidationReport, adapter: ProjectAdapter) -> None:
    flow_registry = adapter.get_flow_registry()
    flow_ids = list(flow_registry.keys())
    flow_order = adapter.get_flow_order()
    release_critical = adapter.get_release_critical_flows()
    core_anchors = adapter.get_core_anchor_flows()
    intent_flow_base = adapter.get_intent_flow_base()
    suite_registry = adapter.get_suite_catalog()
    defect_families = adapter.get_defect_families()

    if not flow_ids:
        _push_check(report.structure_checks, "flow_registry_non_empty", "fail", "Flow registry is empty.")
        report.errors.append("Flow registry must not be empty.")
    else:
        _push_check(
            report.structure_checks,
            "flow_registry_non_empty",
            "pass",
            f"Flow registry contains {len(flow_ids)} flows.",
        )

    if not isinstance(flow_order, tuple) or not flow_order:
        _push_check(report.structure_checks, "flow_order_non_empty", "fail", "Flow order is missing.")
        report.errors.append("Flow order must be non-empty tuple.")
    elif not set(flow_order).issubset(set(flow_ids)):
        _push_check(
            report.structure_checks,
            "flow_order_consistency",
            "fail",
            "Flow order contains IDs not present in flow registry.",
        )
        report.errors.append("Flow order contains unknown flow IDs.")
    else:
        _push_check(
            report.structure_checks,
            "flow_order_consistency",
            "pass",
            f"Flow order covers {len(flow_order)} known flow IDs.",
        )

    if not isinstance(release_critical, tuple) or not release_critical:
        _push_check(
            report.structure_checks,
            "release_critical_flow_presence",
            "fail",
            "No release-critical flows declared.",
        )
        report.errors.append("At least one release-critical flow is required.")
    elif not set(release_critical).issubset(set(flow_ids)):
        _push_check(
            report.structure_checks,
            "release_critical_flow_consistency",
            "fail",
            "Release-critical flow list contains unknown flow IDs.",
        )
        report.errors.append("Release-critical flows include unknown IDs.")
    else:
        _push_check(
            report.structure_checks,
            "release_critical_flow_consistency",
            "pass",
            f"Release-critical flows: {', '.join(release_critical)}",
        )

    if not isinstance(core_anchors, tuple) or not core_anchors:
        _push_check(report.structure_checks, "core_anchor_presence", "warn", "Core anchor flow list is empty.")
        report.warnings.append("Core anchor flow list is empty; orchestrator baselines may be weak.")
    elif not set(core_anchors).issubset(set(flow_ids)):
        _push_check(
            report.structure_checks,
            "core_anchor_consistency",
            "fail",
            "Core anchor flow list contains unknown IDs.",
        )
        report.errors.append("Core anchor flow list contains unknown IDs.")
    else:
        _push_check(
            report.structure_checks,
            "core_anchor_consistency",
            "pass",
            f"Core anchors: {', '.join(core_anchors)}",
        )

    for intent, mapped in intent_flow_base.items():
        if not isinstance(mapped, tuple):
            report.errors.append(f"Intent flow base for '{intent}' must be tuple.")
            _push_check(
                report.structure_checks,
                "intent_flow_mapping_shape",
                "fail",
                f"Intent '{intent}' mapping is not tuple.",
            )
            break
        if not set(mapped).issubset(set(flow_ids)):
            report.errors.append(f"Intent '{intent}' references unknown flow IDs.")
            _push_check(
                report.structure_checks,
                "intent_flow_mapping_consistency",
                "fail",
                f"Intent '{intent}' references unknown flow IDs.",
            )
            break
    else:
        _push_check(
            report.structure_checks,
            "intent_flow_mapping_consistency",
            "pass",
            f"Intent mappings validated ({len(intent_flow_base)} intents).",
        )

    if not suite_registry:
        _push_check(report.structure_checks, "suite_registry_non_empty", "fail", "Suite registry is empty.")
        report.errors.append("Suite registry must not be empty.")
    else:
        _push_check(
            report.structure_checks,
            "suite_registry_non_empty",
            "pass",
            f"Suite registry contains {len(suite_registry)} entries.",
        )

    missing_suite_paths = []
    for row in suite_registry.values():
        suite_path = row.get("suite", "")
        if isinstance(suite_path, str) and suite_path:
            if not (REPO_ROOT / suite_path).exists():
                missing_suite_paths.append(suite_path)
    if missing_suite_paths:
        _push_check(
            report.structure_checks,
            "suite_path_existence",
            "warn",
            f"{len(missing_suite_paths)} suite paths do not exist locally.",
        )
        report.warnings.append(
            "Some suite paths are placeholders or not yet implemented: "
            + ", ".join(sorted(set(missing_suite_paths))[:5])
        )
    else:
        _push_check(report.structure_checks, "suite_path_existence", "pass", "All suite paths exist locally.")

    if not defect_families:
        _push_check(
            report.structure_checks,
            "defect_family_presence",
            "warn",
            "Defect family registry is empty. This is structurally valid but low onboarding readiness.",
        )
        report.warnings.append("Defect family registry is empty; add project-specific families before production onboarding.")
    else:
        _push_check(
            report.structure_checks,
            "defect_family_presence",
            "pass",
            f"Defect family registry has {len(defect_families)} entries.",
        )

    sample_family_detected = False
    for family in defect_families:
        family_id = ""
        title = ""
        if isinstance(family, DefectFamilyDefinition):
            family_id = family.family_id
            title = family.title
        elif isinstance(family, dict):
            family_id = str(family.get("family_id", ""))
            title = str(family.get("title", ""))
        if "SAMPLE" in family_id.upper() or "sample" in title.lower():
            sample_family_detected = True
            break
    if sample_family_detected:
        _push_check(
            report.structure_checks,
            "placeholder_defect_family_detection",
            "warn",
            "Sample/template defect family content detected.",
        )
        report.warnings.append("Sample defect families detected; replace with real project defect families.")
    else:
        _push_check(
            report.structure_checks,
            "placeholder_defect_family_detection",
            "pass",
            "No sample/template defect families detected.",
        )

    sample_files = [
        "auth/login_service.py",
        "order/checkout_service.py",
        "merchant/order_transition_service.py",
        "search/store_query_handler.py",
        "payment/webhook_handler.py",
    ]
    mapped = adapter.map_changed_files_to_flows(sample_files)
    if not isinstance(mapped, dict):
        _push_check(
            report.structure_checks,
            "change_mapping_shape",
            "fail",
            "map_changed_files_to_flows must return dict.",
        )
        report.errors.append("map_changed_files_to_flows must return dict.")
    elif not mapped:
        _push_check(
            report.structure_checks,
            "change_mapping_signal",
            "warn",
            "Change mapping returns empty for sample inputs.",
        )
        report.warnings.append("Change mapping produced no sample matches; extend keyword mapping.")
    else:
        _push_check(
            report.structure_checks,
            "change_mapping_signal",
            "pass",
            f"Change mapping produced {len(mapped)} flow matches for sample inputs.",
        )

    try:
        built_families = adapter.build_defect_families(
            release_data={},
            rerun_data={},
            lastfailed_case_ids=[],
            merchant_missing_slots=[],
        )
        if isinstance(built_families, list):
            if not built_families:
                _push_check(
                    report.structure_checks,
                    "build_defect_families_readiness",
                    "warn",
                    "build_defect_families returns empty list on baseline input.",
                )
                report.warnings.append("build_defect_families currently returns no families; implement project-specific clustering.")
            else:
                _push_check(
                    report.structure_checks,
                    "build_defect_families_readiness",
                    "pass",
                    f"build_defect_families returns {len(built_families)} family entries.",
                )
        else:
            raise ValueError("must return list")
    except Exception as exc:
        _push_check(
            report.structure_checks,
            "build_defect_families_readiness",
            "fail",
            f"build_defect_families contract failed: {exc}",
        )
        report.errors.append(f"build_defect_families contract failed: {exc}")


def _smoke_check_modules(report: AdapterValidationReport, adapter_name: str) -> None:
    with _adapter_env(adapter_name):
        try:
            orchestrator_mod = _reload("ai_regression_orchestrator")
            adapter = orchestrator_mod.ADAPTER
            plan = orchestrator_mod._build_plan(adapter.get_default_intent(), adapter.get_default_mode())
            if isinstance(plan, dict) and "selected_suites" in plan:
                _push_check(
                    report.core_smoke_checks,
                    "regression_orchestrator_smoke",
                    "pass",
                    "Regression orchestrator built plan successfully.",
                )
            else:
                raise ValueError("unexpected plan payload shape")
        except Exception as exc:
            _push_check(
                report.core_smoke_checks,
                "regression_orchestrator_smoke",
                "fail",
                f"Regression orchestrator smoke failed: {exc}",
            )
            report.errors.append(f"Regression orchestrator smoke failed: {exc}")

        try:
            release_gate_mod = _reload("release_decision_gate")
            payload = release_gate_mod._build_payload()
            if isinstance(payload, dict) and payload.get("decision"):
                _push_check(
                    report.core_smoke_checks,
                    "release_gate_compatibility_smoke",
                    "pass",
                    "Release gate compatibility payload built successfully.",
                )
            else:
                raise ValueError("unexpected release gate payload shape")
        except Exception as exc:
            _push_check(
                report.core_smoke_checks,
                "release_gate_compatibility_smoke",
                "fail",
                f"Release gate compatibility smoke failed: {exc}",
            )
            report.errors.append(f"Release gate compatibility smoke failed: {exc}")

    env = os.environ.copy()
    env["AI_TESTING_ADAPTER"] = adapter_name
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "ai_change_aware_regression_trigger.py",
                "--files",
                "auth/login_service.py,order/checkout_service.py",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        if completed.returncode == 0:
            _push_check(
                report.core_smoke_checks,
                "change_aware_trigger_smoke",
                "pass",
                "Change-aware trigger executed successfully.",
            )
        else:
            details = (completed.stderr or completed.stdout or "").strip()
            _push_check(
                report.core_smoke_checks,
                "change_aware_trigger_smoke",
                "fail",
                f"Change-aware trigger failed (rc={completed.returncode}): {details[:220]}",
            )
            report.errors.append("Change-aware trigger smoke failed.")
    except Exception as exc:
        _push_check(
            report.core_smoke_checks,
            "change_aware_trigger_smoke",
            "fail",
            f"Change-aware trigger execution exception: {exc}",
        )
        report.errors.append(f"Change-aware trigger execution exception: {exc}")


def _finalize_status(report: AdapterValidationReport) -> None:
    if report.strict_mode and report.warnings:
        report.errors.append("Strict mode escalation: warnings must be resolved.")

    if report.errors:
        report.status = "fail"
    elif report.warnings:
        report.status = "pass_with_warnings"
    else:
        report.status = "pass"

    if report.status == "fail":
        report.recommendations.append("Fix contract/compatibility errors before onboarding this adapter.")
    if report.warnings:
        report.recommendations.append(
            "Resolve warning items (placeholder suites/families/mappings) before production onboarding."
        )
    if not report.warnings and not report.errors:
        report.recommendations.append("Adapter is structurally ready for onboarding workflows.")


def validate_adapter(
    adapter_name: str,
    *,
    strict: bool = False,
    ci: bool = False,
    verbose: bool = False,
) -> AdapterValidationReport:
    report = AdapterValidationReport(adapter_name=adapter_name, strict_mode=strict, ci_mode=ci)
    adapter, resolved_id, resolve_error = _resolve_adapter(adapter_name)

    if resolve_error is not None:
        _push_check(
            report.loader_checks,
            "loader_resolution",
            "fail",
            f"Loader failed to instantiate adapter '{adapter_name}': {resolve_error}",
        )
        report.errors.append(f"Loader failed for adapter '{adapter_name}': {resolve_error}")
        _finalize_status(report)
        return report

    if adapter is None:
        _push_check(
            report.loader_checks,
            "loader_resolution",
            "fail",
            f"Adapter '{adapter_name}' could not be resolved.",
        )
        report.errors.append(f"Adapter '{adapter_name}' could not be resolved.")
        _finalize_status(report)
        return report

    if resolved_id != adapter_name:
        _push_check(
            report.loader_checks,
            "loader_resolution",
            "fail",
            f"Loader resolved '{resolved_id}' instead of requested '{adapter_name}'.",
        )
        report.errors.append(
            f"Loader resolved '{resolved_id}' instead of requested '{adapter_name}'."
        )
        _finalize_status(report)
        return report

    adapter_id = adapter.get_adapter_id()
    if adapter_id != adapter_name:
        _push_check(
            report.loader_checks,
            "loader_adapter_identity",
            "fail",
            f"Adapter instance id mismatch: '{adapter_id}' != '{adapter_name}'.",
        )
        report.errors.append("Adapter instance id mismatch.")
        _finalize_status(report)
        return report

    _push_check(
        report.loader_checks,
        "loader_resolution",
        "pass",
        f"Loader resolved adapter '{adapter_name}' successfully.",
    )

    _validate_contract(report, adapter)
    if ci and any(item.status == "fail" for item in report.contract_checks):
        report.recommendations.append("CI mode fail-fast: contract violations detected.")
        _finalize_status(report)
        return report

    _validate_structure(report, adapter)
    if ci and any(item.status == "fail" for item in report.structure_checks):
        report.recommendations.append("CI mode fail-fast: structural violations detected.")
        _finalize_status(report)
        return report

    _smoke_check_modules(report, adapter_name)
    _finalize_status(report)

    if verbose:
        for check in report.all_checks():
            print(f"[{check.status}] {check.name}: {check.details}")
    return report

