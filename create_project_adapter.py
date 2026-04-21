"""Project Adapter SDK bootstrap generator v1.

Usage:
  python create_project_adapter.py --name ecommerce_alpha --profile ecommerce
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = REPO_ROOT / "orchestrator" / "adapters" / "templates"
ADAPTERS_DIR = REPO_ROOT / "orchestrator" / "adapters"


@dataclass(frozen=True)
class FlowSeed:
    flow_id: str
    title: str
    description: str
    keywords: tuple[str, ...]


PROFILE_FLOWS: dict[str, list[FlowSeed]] = {
    "generic": [
        FlowSeed("auth_foundation", "Auth Foundation", "Authentication and token baseline.", ("auth", "login", "token")),
        FlowSeed("core_business", "Core Business", "Primary product business flow.", ("core", "business", "flow")),
        FlowSeed("payment_integrity", "Payment Integrity", "Payment init/verify/retry integrity.", ("payment", "billing", "transaction")),
        FlowSeed("admin_ops", "Admin Operations", "Admin visibility and control flow.", ("admin", "ops", "management")),
    ],
    "ecommerce": [
        FlowSeed("auth_foundation", "Auth Foundation", "Authentication and token baseline.", ("auth", "login", "token")),
        FlowSeed("catalog_discovery", "Catalog Discovery", "Catalog/search/listing funnel.", ("catalog", "search", "discovery", "product")),
        FlowSeed("cart_checkout", "Cart & Checkout", "Cart management and checkout path.", ("cart", "checkout", "order")),
        FlowSeed("order_management", "Order Management", "Order status and fulfillment lifecycle.", ("order", "fulfillment", "shipment")),
        FlowSeed("payment_integrity", "Payment Integrity", "Payment initiation and callback integrity.", ("payment", "billing", "transaction", "webhook")),
        FlowSeed("admin_ops", "Admin Operations", "Admin operational consistency and controls.", ("admin", "ops", "console")),
    ],
    "saas": [
        FlowSeed("auth_foundation", "Auth Foundation", "Authentication and identity baseline.", ("auth", "login", "identity")),
        FlowSeed("workspace_access", "Workspace Access", "Tenant/workspace authorization flow.", ("workspace", "tenant", "organization")),
        FlowSeed("subscription_billing", "Subscription Billing", "Plan and billing lifecycle.", ("subscription", "billing", "invoice", "payment")),
        FlowSeed("settings_profile", "Settings & Profile", "User settings and account management.", ("settings", "profile", "preferences")),
        FlowSeed("admin_ops", "Admin Operations", "Admin controls and organization operations.", ("admin", "ops", "management")),
    ],
    "booking": [
        FlowSeed("auth_foundation", "Auth Foundation", "Authentication and access baseline.", ("auth", "login", "token")),
        FlowSeed("search_discovery", "Search & Discovery", "Search and discovery funnel.", ("search", "discovery", "listing")),
        FlowSeed("reservation_core", "Reservation Core", "Reservation creation and core contract checks.", ("reservation", "booking", "order")),
        FlowSeed("payment_integrity", "Payment Integrity", "Payment and verification integrity.", ("payment", "billing", "transaction")),
        FlowSeed("operator_handling", "Operator Handling", "Operator-side workflow transitions.", ("operator", "merchant", "handling")),
        FlowSeed("admin_consistency", "Admin Consistency", "Cross-surface admin consistency checks.", ("admin", "consistency", "tracking")),
    ],
}

TEMPLATE_MAP: dict[str, str] = {
    "__init__.py": "__init__.py.tpl",
    "adapter.py": "adapter.py.tpl",
    "flow_registry.py": "flow_registry.py.tpl",
    "suite_registry.py": "suite_registry.py.tpl",
    "defect_registry.py": "defect_registry.py.tpl",
    "change_mapping.py": "change_mapping.py.tpl",
    "risk_rules.py": "risk_rules.py.tpl",
    "blocker_rules.py": "blocker_rules.py.tpl",
    "README.md": "README.md.tpl",
}


def _to_camel_case(value: str) -> str:
    return "".join(token.capitalize() for token in value.split("_") if token)


def _tuple_lines(values: list[str], indent: int = 4) -> str:
    spaces = " " * indent
    if not values:
        return f'{spaces}"",'
    return "\n".join(f'{spaces}"{value}",' for value in values)


def _tuple_literal(values: list[str]) -> str:
    if not values:
        return "()"
    if len(values) == 1:
        return f'("{values[0]}",)'
    joined = ", ".join(f'"{value}"' for value in values)
    return f"({joined})"


def _pick_first(flows: list[str], candidates: list[str]) -> str:
    for candidate in candidates:
        if candidate in flows:
            return candidate
    return flows[0]


def _build_core_anchors(flows: list[str]) -> list[str]:
    anchors: list[str] = []
    for token in ("auth_foundation", "order_core", "order_management", "reservation_core", "cart_checkout"):
        if token in flows and token not in anchors:
            anchors.append(token)
            break
    for token in ("admin_consistency", "admin_ops"):
        if token in flows and token not in anchors:
            anchors.append(token)
            break
    for flow_id in flows:
        if flow_id not in anchors:
            anchors.append(flow_id)
        if len(anchors) >= 3:
            break
    return anchors


def _build_flow_registry_entries(flows: list[FlowSeed]) -> str:
    rows: list[str] = []
    for flow in flows:
        rows.append(
            f'    "{flow.flow_id}": FlowDefinition(\n'
            f'        flow_id="{flow.flow_id}",\n'
            f'        title="{flow.title}",\n'
            f'        description="{flow.description}",\n'
            f'        suites=("tests/{{ADAPTER_NAME}}/test_{flow.flow_id}_api.py",),\n'
            f"        release_critical=True,\n"
            f"    ),"
        )
    return "\n".join(rows)


def _build_suite_catalog_entries(flows: list[FlowSeed]) -> str:
    entries: list[str] = []
    for flow in flows:
        priority = "P0" if any(token in flow.flow_id for token in ("auth", "order", "reservation", "checkout", "admin")) else "P1"
        entries.append(
            f'    "{flow.flow_id}": {{\n'
            f'        "suite": "tests/{{ADAPTER_NAME}}/test_{flow.flow_id}_api.py",\n'
            f'        "priority": "{priority}",\n'
            f'        "blast_radius": "release-critical",\n'
            f"    }},"
        )

    flow_ids = [flow.flow_id for flow in flows]
    alias_targets = {
        "auth": _pick_first(flow_ids, ["auth_foundation"]),
        "order_core": _pick_first(flow_ids, ["order_core", "order_management", "reservation_core", "cart_checkout"]),
        "search_store": _pick_first(flow_ids, ["search_discovery", "catalog_discovery", "workspace_access"]),
        "lifecycle": _pick_first(flow_ids, ["order_management", "reservation_core", "cart_checkout", "order_core"]),
        "admin_consistency": _pick_first(flow_ids, ["admin_consistency", "admin_ops"]),
        "merchant_depth": _pick_first(flow_ids, ["merchant_handling", "operator_handling", "order_management"]),
        "payment_realism": _pick_first(flow_ids, ["payment_integrity", "subscription_billing"]),
    }
    for alias, target in alias_targets.items():
        if alias in flow_ids:
            continue
        entries.append(
            f'    "{alias}": {{\n'
            f'        "suite": "tests/{{ADAPTER_NAME}}/test_{target}_api.py",\n'
            f'        "priority": "P1",\n'
            f'        "blast_radius": "partial-surface",\n'
            f"    }},"
        )
    return "\n".join(entries)


def _build_defect_family_entries(flows: list[FlowSeed], profile: str) -> str:
    primary_flow = flows[1].flow_id if len(flows) > 1 else flows[0].flow_id
    payment_flow = _pick_first([f.flow_id for f in flows], ["payment_integrity", "subscription_billing", primary_flow])
    return (
        "    DefectFamilyDefinition(\n"
        '        family_id="DF-SAMPLE-PRODUCT-DEFECT",\n'
        '        title="Sample active-path product defect family",\n'
        '        family_type="product_defect",\n'
        '        severity="P1",\n'
        '        release_impact="release-critical",\n'
        '        member_cases=("SAMPLE-001",),\n'
        '        recommended_next_action="Replace with real project defect family mappings.",\n'
        "    ),\n"
        "    DefectFamilyDefinition(\n"
        '        family_id="DF-SAMPLE-ENV-BLOCKER",\n'
        '        title="Sample environment blocker family",\n'
        '        family_type="env_blocker",\n'
        '        severity="BLOCKER",\n'
        '        release_impact="partial-surface",\n'
        '        member_cases=("SAMPLE-BLK-001",),\n'
        '        recommended_next_action="Replace with real env/runtime blocker families.",\n'
        "    ),\n"
        "    DefectFamilyDefinition(\n"
        '        family_id="DF-SAMPLE-COVERAGE-GAP",\n'
        f'        title="Sample coverage gap for {profile} flow depth",\n'
        '        family_type="coverage_gap",\n'
        '        severity="GAP",\n'
        '        release_impact="partial-surface",\n'
        f'        member_cases=("{primary_flow}", "{payment_flow}"),\n'
        '        recommended_next_action="Replace with real seed/data/coverage gap families.",\n'
        "    ),"
    )


def _build_file_flow_rules(flows: list[FlowSeed]) -> str:
    rows: list[str] = []
    seen: set[tuple[str, str]] = set()
    for flow in flows:
        tokens = set(flow.keywords) | set(flow.flow_id.split("_"))
        for token in sorted(tokens):
            key = (token, flow.flow_id)
            if key in seen:
                continue
            seen.add(key)
            rows.append(f'    ("{token}", "{flow.flow_id}"),')
    return "\n".join(rows)


def _build_risk_text_ifs(flows: list[FlowSeed]) -> str:
    lines: list[str] = []
    for flow in flows:
        tokens = ", ".join(f'"{token}"' for token in flow.keywords[:4])
        lines.append(f"    if any(token in value for token in ({tokens},)):")
        lines.append(f'        return "{flow.flow_id}"')
    return "\n".join(lines)


def _build_defect_flow_ifs(flows: list[FlowSeed]) -> str:
    lines: list[str] = []
    for flow in flows:
        tokens = sorted(set(flow.keywords[:3]) | set(flow.flow_id.split("_")[:2]))
        token_expr = ", ".join(f'"{token}"' for token in tokens)
        lines.append(f"    if any(token in text for token in ({token_expr},)):")
        lines.append(f'        flows.append("{flow.flow_id}")')
    return "\n".join(lines)


def _build_intent_flow_base(flows: list[FlowSeed], core_anchors: list[str]) -> str:
    flow_ids = [flow.flow_id for flow in flows]
    mapping = {
        "full_app_fast_regression": [],
        "order_flow_regression": [_pick_first(flow_ids, ["order_core", "order_management", "reservation_core", "cart_checkout"])],
        "merchant_flow_regression": [_pick_first(flow_ids, ["merchant_handling", "operator_handling", "order_management"])],
        "search_store_regression": [_pick_first(flow_ids, ["search_discovery", "catalog_discovery", "workspace_access"])],
        "payment_regression": [_pick_first(flow_ids, ["payment_integrity", "subscription_billing"])],
        "release_gate_regression": core_anchors,
    }
    lines: list[str] = []
    for key, values in mapping.items():
        lines.append(f'    "{key}": {_tuple_literal(values)},')
    return "\n".join(lines)


def _render_template(template_path: Path, context: dict[str, str]) -> str:
    content = template_path.read_text(encoding="utf-8")
    for key, value in context.items():
        content = content.replace(f"{{{{{key}}}}}", value)
    unresolved = re.findall(r"\{\{[A-Z0-9_]+\}\}", content)
    if unresolved:
        unresolved_text = ", ".join(sorted(set(unresolved)))
        raise ValueError(f"Unresolved placeholders in {template_path.name}: {unresolved_text}")
    return content


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create project adapter scaffold.")
    parser.add_argument("--name", required=True, help="Adapter name (snake_case).")
    parser.add_argument(
        "--profile",
        default="generic",
        choices=sorted(PROFILE_FLOWS.keys()),
        help="Starter profile.",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing adapter files.")
    parser.add_argument("--dry-run", action="store_true", help="Show planned outputs without writing files.")
    return parser.parse_args()


def _validate_name(name: str) -> None:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise ValueError("Adapter name must match [a-z][a-z0-9_]*")


def main() -> None:
    args = _parse_args()
    adapter_name = args.name.strip().lower()
    profile = args.profile.strip().lower()
    _validate_name(adapter_name)

    if profile not in PROFILE_FLOWS:
        raise ValueError(f"Unsupported profile: {profile}")

    target_dir = ADAPTERS_DIR / adapter_name
    exists = target_dir.exists()
    if exists and not args.force:
        raise SystemExit(
            f"[adapter-bootstrap] target '{target_dir}' already exists. Use --force to overwrite scaffold files."
        )

    flows = PROFILE_FLOWS[profile]
    flow_ids = [flow.flow_id for flow in flows]
    core_anchors = _build_core_anchors(flow_ids)
    release_critical = flow_ids
    class_name = f"{_to_camel_case(adapter_name)}Adapter"
    product_name = _to_camel_case(adapter_name).replace("_", " ")

    context = {
        "ADAPTER_NAME": adapter_name,
        "CLASS_NAME": class_name,
        "PRODUCT_NAME": product_name,
        "PROFILE_NAME": profile,
        "FLOW_REGISTRY_ENTRIES": _build_flow_registry_entries(flows).replace("{ADAPTER_NAME}", adapter_name),
        "FLOW_ORDER_ENTRIES": _tuple_lines(flow_ids, indent=4),
        "CORE_ANCHOR_ENTRIES": _tuple_lines(core_anchors, indent=4),
        "RELEASE_CRITICAL_ENTRIES": _tuple_lines(release_critical, indent=4),
        "SUITE_CATALOG_ENTRIES": _build_suite_catalog_entries(flows).replace("{ADAPTER_NAME}", adapter_name),
        "DEFECT_FAMILY_ENTRIES": _build_defect_family_entries(flows, profile),
        "FILE_FLOW_RULES": _build_file_flow_rules(flows),
        "INTENT_FLOW_BASE_ENTRIES": _build_intent_flow_base(flows, core_anchors),
        "RISK_TEXT_FLOW_IFS": _build_risk_text_ifs(flows),
        "DEFECT_FLOW_IFS": _build_defect_flow_ifs(flows),
        "FLOW_README_LIST": "\n".join(f"- `{flow.flow_id}`: {flow.title}" for flow in flows),
    }

    planned_files = [target_dir / rel_path for rel_path in TEMPLATE_MAP]
    if args.dry_run:
        print(f"[adapter-bootstrap] dry-run adapter={adapter_name} profile={profile}")
        for path in planned_files:
            print(f"  - {path}")
        return

    target_dir.mkdir(parents=True, exist_ok=True)
    created: list[str] = []
    overwritten: list[str] = []

    for output_name, template_name in TEMPLATE_MAP.items():
        output_path = target_dir / output_name
        template_path = TEMPLATE_DIR / template_name
        rendered = _render_template(template_path, context)
        existed_before = output_path.exists()
        output_path.write_text(rendered, encoding="utf-8")
        if existed_before:
            overwritten.append(str(output_path))
        else:
            created.append(str(output_path))

    print(
        f"[adapter-bootstrap] adapter={adapter_name} profile={profile} "
        f"created={len(created)} overwritten={len(overwritten)}"
    )
    for path in created:
        print(f"  + {path}")
    for path in overwritten:
        print(f"  ~ {path}")
    print(f"[adapter-bootstrap] next: set AI_TESTING_ADAPTER={adapter_name} and customize scaffold mappings.")


if __name__ == "__main__":
    main()

