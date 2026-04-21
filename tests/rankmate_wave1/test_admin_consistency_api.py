"""Wave 1 ADMIN-CONS-* cross-surface order consistency tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

import pytest

from .helpers.assertion_helper import (
    assert_status,
    assert_success_envelope,
    envelope_data,
)
from .helpers.result_tags import wave1_case


STATUS_NAMES = {
    10: "pending",
    20: "paid",
    21: "accepted",
    22: "arrived",
    23: "completed",
    24: "waiting_customer_confirmation",
    30: "failed",
    40: "refunded",
    50: "expired",
    60: "cancelled",
    90: "rejected",
    91: "no_show",
}

STATUS_ALIASES = {
    "pending": "pending",
    "paid": "paid",
    "accepted": "accepted",
    "arrived": "arrived",
    "complete": "completed",
    "completed": "completed",
    "waitingcustomerconfirmation": "waiting_customer_confirmation",
    "waiting_customer_confirmation": "waiting_customer_confirmation",
    "cancelled": "cancelled",
    "canceled": "cancelled",
    "rejected": "rejected",
    "noshow": "no_show",
    "no_show": "no_show",
    "refunded": "refunded",
    "expired": "expired",
    "failed": "failed",
}

TERMINAL_STATUSES = {"completed", "cancelled", "rejected", "no_show", "expired", "refunded", "failed"}


def _normalize_text(value: str) -> str:
    return "".join(ch for ch in value.lower().strip().replace("-", "_") if ch.isalnum() or ch == "_")


def _status_semantic(value: Any) -> Optional[str]:
    if isinstance(value, int):
        return STATUS_NAMES.get(value, f"status_{value}")
    if isinstance(value, str) and value.strip():
        key = _normalize_text(value)
        return STATUS_ALIASES.get(key, key)
    return None


def _status_phase(semantic: Optional[str]) -> Optional[str]:
    if semantic is None:
        return None
    if semantic in TERMINAL_STATUSES:
        return "terminal"
    return "active"


def _extract_rows(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    data = envelope_data(payload)
    if isinstance(data, Mapping):
        for key in ("data", "items", "rows", "records"):
            rows = data.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, Mapping)]
    if isinstance(data, list):
        return [row for row in data if isinstance(row, Mapping)]
    return []


def _extract_data(payload: Mapping[str, Any], *, case_id: str, assertion_id: str) -> Mapping[str, Any]:
    data = envelope_data(payload)
    assert isinstance(data, Mapping), f"[{case_id}/{assertion_id}] Missing data envelope: {payload}"
    return data


def _nested_mapping(value: Any) -> Optional[Mapping[str, Any]]:
    return value if isinstance(value, Mapping) else None


def _candidate_order_nodes(data: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    candidates: list[Mapping[str, Any]] = [data]
    order_node = _nested_mapping(data.get("order"))
    if order_node is not None:
        candidates.append(order_node)
    return candidates


def _extract_order_id(data: Mapping[str, Any], *, case_id: str, assertion_id: str) -> int:
    for candidate in _candidate_order_nodes(data):
        order_id = candidate.get("id") or candidate.get("orderId")
        if isinstance(order_id, int):
            return order_id
    raise AssertionError(f"[{case_id}/{assertion_id}] Missing integer order id in payload: {data}")


def _extract_status(data: Mapping[str, Any], *, case_id: str, assertion_id: str) -> tuple[Any, Optional[str]]:
    for candidate in _candidate_order_nodes(data):
        if "status" in candidate:
            raw = candidate.get("status")
        else:
            raw = candidate.get("orderStatus")
        semantic = _status_semantic(raw)
        if semantic is not None:
            return raw, semantic
    raise AssertionError(f"[{case_id}/{assertion_id}] Missing status/orderStatus in payload: {data}")


def _extract_store_identity(data: Mapping[str, Any]) -> tuple[Optional[int], Optional[str]]:
    store_id: Optional[int] = None
    store_unique: Optional[str] = None

    for candidate in _candidate_order_nodes(data):
        if store_id is None:
            candidate_store_id = candidate.get("storeId")
            if isinstance(candidate_store_id, int):
                store_id = candidate_store_id
            else:
                candidate_store = _nested_mapping(candidate.get("store"))
                if candidate_store is not None:
                    nested_id = candidate_store.get("id") or candidate_store.get("storeId")
                    if isinstance(nested_id, int):
                        store_id = nested_id

        if store_unique is None:
            for key in ("storeUniqueId", "uniqueId", "storeCode"):
                value = candidate.get(key)
                if isinstance(value, str) and value.strip():
                    store_unique = value.strip()
                    break
            if store_unique is None:
                candidate_store = _nested_mapping(candidate.get("store"))
                if candidate_store is not None:
                    for key in ("storeUniqueId", "uniqueId", "storeCode"):
                        value = candidate_store.get(key)
                        if isinstance(value, str) and value.strip():
                            store_unique = value.strip()
                            break

    return store_id, store_unique


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _extract_amount_currency(data: Mapping[str, Any]) -> tuple[Optional[float], Optional[str], Optional[int]]:
    total = None
    for key in ("totalAmount", "total", "amount", "grandTotal", "finalTotal"):
        total = _as_float(data.get(key))
        if total is not None:
            break
    currency = None
    for key in ("currency", "currencyCode"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            currency = value.strip().upper()
            break
    item_count = None
    for key in ("items", "orderItems", "details"):
        items = data.get(key)
        if isinstance(items, list):
            item_count = len(items)
            break
    return total, currency, item_count


def _load_lifecycle_seed(repo_root: Path) -> Optional[dict[str, Any]]:
    seed_path = repo_root / "order_lifecycle_seed.json"
    if not seed_path.exists() or not seed_path.is_file():
        return None
    try:
        raw = json.loads(seed_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return raw if isinstance(raw, dict) else None


def _fetch_order_surfaces(
    *,
    case_id: str,
    assertion_id: str,
    order_id: int,
    user_session,
    merchant_store_session,
    admin_session,
    order_helper,
    merchant_helper,
    admin_helper,
) -> dict[str, Mapping[str, Any]]:
    user_resp = order_helper.get_order(token=user_session.token, order_id=order_id)
    assert_status(user_resp, 200, assertion_id=assertion_id, case_id=case_id)
    user_payload = assert_success_envelope(user_resp, assertion_id=assertion_id, case_id=case_id)
    user_data = _extract_data(user_payload, case_id=case_id, assertion_id=assertion_id)

    merchant_resp = merchant_helper.get_order_detail(token=merchant_store_session.store_token, order_id=order_id)
    if merchant_resp.status_code in {400, 403, 404}:
        pytest.skip(
            f"[{case_id}] Merchant cannot access consistency order {order_id}; "
            "verify lifecycle seed ownership and merchant store mapping."
        )
    assert_status(merchant_resp, 200, assertion_id=assertion_id, case_id=case_id)
    merchant_payload = assert_success_envelope(merchant_resp, assertion_id=assertion_id, case_id=case_id)
    merchant_data = _extract_data(merchant_payload, case_id=case_id, assertion_id=assertion_id)

    admin_resp = admin_helper.get_order_detail(token=admin_session.token, order_id=order_id)
    assert_status(admin_resp, 200, assertion_id=assertion_id, case_id=case_id)
    admin_payload = assert_success_envelope(admin_resp, assertion_id=assertion_id, case_id=case_id)
    admin_data = _extract_data(admin_payload, case_id=case_id, assertion_id=assertion_id)

    return {
        "user": user_data,
        "merchant": merchant_data,
        "admin": admin_data,
    }


def _write_admin_consistency_report(repo_root: Path, report: dict[str, Any]) -> None:
    report_path = repo_root / "docs" / "wave1_runtime" / "ADMIN_CONSISTENCY_REPORT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    status = report.get("status_matrix", {})
    amount = report.get("amount_matrix", {})
    inconsistencies = report.get("inconsistencies", [])

    lines = [
        "# ADMIN_CONSISTENCY_REPORT",
        "",
        f"- Generated at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Order ID: `{report.get('order_id')}`",
        f"- Seed source: `{report.get('seed_source')}`",
        f"- Lifecycle artifact used: `{report.get('lifecycle_artifact_used')}`",
        "",
        "## Status Comparison Matrix",
        "",
        "| Surface | Raw | Semantic |",
        "|---|---|---|",
        f"| seed | `{status.get('seed_raw')}` | `{status.get('seed_semantic')}` |",
        f"| user | `{status.get('user_raw')}` | `{status.get('user_semantic')}` |",
        f"| merchant | `{status.get('merchant_raw')}` | `{status.get('merchant_semantic')}` |",
        f"| admin | `{status.get('admin_raw')}` | `{status.get('admin_semantic')}` |",
        "",
        "## Amount Comparison Matrix",
        "",
        "| Surface | Total | Currency | Item Count |",
        "|---|---:|---|---:|",
        f"| user | `{amount.get('user_total')}` | `{amount.get('user_currency')}` | `{amount.get('user_item_count')}` |",
        f"| merchant | `{amount.get('merchant_total')}` | `{amount.get('merchant_currency')}` | `{amount.get('merchant_item_count')}` |",
        f"| admin | `{amount.get('admin_total')}` | `{amount.get('admin_currency')}` | `{amount.get('admin_item_count')}` |",
        "",
        "## Inconsistencies",
        "",
    ]
    if inconsistencies:
        lines.extend([f"- {issue}" for issue in inconsistencies])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Confidence Note",
            "",
            report.get("confidence_note", "Insufficient evidence captured."),
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")


@pytest.fixture(scope="module")
def lifecycle_seed_payload(wave1_repo_root: Path):
    return _load_lifecycle_seed(wave1_repo_root)


@pytest.fixture(scope="module")
def consistency_seed_context(lifecycle_seed_payload, wave1_config):
    lifecycle_order_id = lifecycle_seed_payload.get("order_id") if isinstance(lifecycle_seed_payload, Mapping) else None
    if isinstance(lifecycle_order_id, int):
        return {
            "order_id": lifecycle_order_id,
            "source": "order_lifecycle_seed.json",
            "lifecycle_artifact_used": True,
            "seed": lifecycle_seed_payload,
        }

    for source, value in (
        ("API_CONSISTENCY_ORDER_ID", wave1_config.consistency_order_id),
        ("API_COMPLETED_ORDER_ID", wave1_config.completed_order_id),
        ("API_CANCELLED_ORDER_ID", wave1_config.cancelled_order_id),
    ):
        if isinstance(value, int):
            return {
                "order_id": value,
                "source": source,
                "lifecycle_artifact_used": False,
                "seed": lifecycle_seed_payload if isinstance(lifecycle_seed_payload, Mapping) else {},
            }

    pytest.skip(
        "[ADMIN-CONS] Missing lifecycle seed order id and fallback env IDs. "
        "Run order lifecycle suite or set API_CONSISTENCY_ORDER_ID/API_COMPLETED_ORDER_ID/API_CANCELLED_ORDER_ID."
    )


@pytest.fixture(scope="module")
def terminal_seed_context(consistency_seed_context, wave1_config):
    seed = consistency_seed_context.get("seed", {})
    seed_final = seed.get("final_status") if isinstance(seed, Mapping) else None
    if isinstance(seed_final, str) and _status_semantic(seed_final) in TERMINAL_STATUSES:
        return consistency_seed_context

    for source, value in (
        ("API_COMPLETED_ORDER_ID", wave1_config.completed_order_id),
        ("API_CANCELLED_ORDER_ID", wave1_config.cancelled_order_id),
    ):
        if isinstance(value, int):
            return {
                "order_id": value,
                "source": source,
                "lifecycle_artifact_used": False,
                "seed": seed if isinstance(seed, Mapping) else {},
            }

    pytest.skip(
        "[ADMIN-CONS-005] Missing terminal order seed. "
        "Provide completed/cancelled seed via lifecycle artifact or API_COMPLETED_ORDER_ID/API_CANCELLED_ORDER_ID."
    )


@pytest.fixture(scope="module", autouse=True)
def admin_consistency_report(wave1_repo_root: Path, consistency_seed_context):
    report: dict[str, Any] = {
        "order_id": consistency_seed_context.get("order_id"),
        "seed_source": consistency_seed_context.get("source"),
        "lifecycle_artifact_used": consistency_seed_context.get("lifecycle_artifact_used"),
        "status_matrix": {},
        "amount_matrix": {},
        "inconsistencies": [],
        "confidence_note": "Consistency evidence partially captured.",
    }
    yield report
    if not report["inconsistencies"] and report["status_matrix"]:
        report["confidence_note"] = (
            "Cross-surface consistency checks completed without detected contradictions for the selected order."
        )
    _write_admin_consistency_report(wave1_repo_root, report)


@wave1_case(
    case_id="ADMIN-CONS-001",
    assertion_ids=["XSURF-C11"],
    domain="admin-consistency",
    priority="P0",
    risk="critical",
)
def test_admin_cons_001_cross_surface_order_id_continuity(
    consistency_seed_context,
    user_session,
    merchant_store_session,
    admin_session,
    order_helper,
    merchant_helper,
    admin_helper,
    admin_consistency_report,
):
    order_id = consistency_seed_context["order_id"]
    surfaces = _fetch_order_surfaces(
        case_id="ADMIN-CONS-001",
        assertion_id="XSURF-C11",
        order_id=order_id,
        user_session=user_session,
        merchant_store_session=merchant_store_session,
        admin_session=admin_session,
        order_helper=order_helper,
        merchant_helper=merchant_helper,
        admin_helper=admin_helper,
    )

    user_id = _extract_order_id(surfaces["user"], case_id="ADMIN-CONS-001", assertion_id="XSURF-C11")
    merchant_id = _extract_order_id(surfaces["merchant"], case_id="ADMIN-CONS-001", assertion_id="XSURF-C11")
    admin_id = _extract_order_id(surfaces["admin"], case_id="ADMIN-CONS-001", assertion_id="XSURF-C11")

    assert user_id == order_id == merchant_id == admin_id, (
        f"[ADMIN-CONS-001/XSURF-C11] Order id mismatch across surfaces: "
        f"seed={order_id} user={user_id} merchant={merchant_id} admin={admin_id}"
    )
    admin_consistency_report["order_id"] = order_id


@wave1_case(
    case_id="ADMIN-CONS-002",
    assertion_ids=["XSURF-C12"],
    domain="admin-consistency",
    priority="P0",
    risk="critical",
)
def test_admin_cons_002_semantic_status_continuity(
    consistency_seed_context,
    user_session,
    merchant_store_session,
    admin_session,
    order_helper,
    merchant_helper,
    admin_helper,
    admin_consistency_report,
):
    order_id = consistency_seed_context["order_id"]
    surfaces = _fetch_order_surfaces(
        case_id="ADMIN-CONS-002",
        assertion_id="XSURF-C12",
        order_id=order_id,
        user_session=user_session,
        merchant_store_session=merchant_store_session,
        admin_session=admin_session,
        order_helper=order_helper,
        merchant_helper=merchant_helper,
        admin_helper=admin_helper,
    )

    user_raw, user_semantic = _extract_status(surfaces["user"], case_id="ADMIN-CONS-002", assertion_id="XSURF-C12")
    merchant_raw, merchant_semantic = _extract_status(
        surfaces["merchant"], case_id="ADMIN-CONS-002", assertion_id="XSURF-C12"
    )
    admin_raw, admin_semantic = _extract_status(surfaces["admin"], case_id="ADMIN-CONS-002", assertion_id="XSURF-C12")

    seed = consistency_seed_context.get("seed", {})
    seed_raw = seed.get("final_status") if isinstance(seed, Mapping) else None
    seed_semantic = _status_semantic(seed_raw) if seed_raw is not None else None

    sem_set = {user_semantic, merchant_semantic, admin_semantic}
    if len(sem_set) != 1:
        phase_set = {_status_phase(value) for value in sem_set}
        assert len(phase_set) == 1, (
            f"[ADMIN-CONS-002/XSURF-C12] Contradictory status phase across surfaces: "
            f"user={user_semantic} merchant={merchant_semantic} admin={admin_semantic}"
        )
        if "terminal" in phase_set:
            assert len(sem_set) == 1, (
                f"[ADMIN-CONS-002/XSURF-C12] Terminal status mismatch across surfaces: "
                f"user={user_semantic} merchant={merchant_semantic} admin={admin_semantic}"
            )

    if seed_semantic is not None:
        assert _status_phase(seed_semantic) == _status_phase(user_semantic), (
            f"[ADMIN-CONS-002/XSURF-C12] Seed final status phase mismatch: "
            f"seed={seed_semantic} user={user_semantic}"
        )

    admin_consistency_report["status_matrix"] = {
        "seed_raw": seed_raw,
        "seed_semantic": seed_semantic,
        "user_raw": user_raw,
        "user_semantic": user_semantic,
        "merchant_raw": merchant_raw,
        "merchant_semantic": merchant_semantic,
        "admin_raw": admin_raw,
        "admin_semantic": admin_semantic,
    }


@wave1_case(
    case_id="ADMIN-CONS-003",
    assertion_ids=["XSURF-C13"],
    domain="admin-consistency",
    priority="P0",
    risk="high",
)
def test_admin_cons_003_store_identity_continuity(
    consistency_seed_context,
    user_session,
    merchant_store_session,
    admin_session,
    order_helper,
    merchant_helper,
    admin_helper,
):
    order_id = consistency_seed_context["order_id"]
    surfaces = _fetch_order_surfaces(
        case_id="ADMIN-CONS-003",
        assertion_id="XSURF-C13",
        order_id=order_id,
        user_session=user_session,
        merchant_store_session=merchant_store_session,
        admin_session=admin_session,
        order_helper=order_helper,
        merchant_helper=merchant_helper,
        admin_helper=admin_helper,
    )
    user_store_id, user_store_unique = _extract_store_identity(surfaces["user"])
    merchant_store_id, merchant_store_unique = _extract_store_identity(surfaces["merchant"])
    admin_store_id, admin_store_unique = _extract_store_identity(surfaces["admin"])

    assert isinstance(user_store_id, int), "[ADMIN-CONS-003/XSURF-C13] Missing user store id"
    assert user_store_id == merchant_store_id == admin_store_id, (
        f"[ADMIN-CONS-003/XSURF-C13] Store id mismatch: "
        f"user={user_store_id} merchant={merchant_store_id} admin={admin_store_id}"
    )

    seed = consistency_seed_context.get("seed", {})
    seed_store_id = seed.get("store_id") if isinstance(seed, Mapping) else None
    if isinstance(seed_store_id, int):
        assert seed_store_id == user_store_id, (
            f"[ADMIN-CONS-003/XSURF-C13] Seed store mismatch seed={seed_store_id} user={user_store_id}"
        )

    unique_values = {
        value for value in (user_store_unique, merchant_store_unique, admin_store_unique) if isinstance(value, str) and value
    }
    if len(unique_values) > 1:
        raise AssertionError(
            "[ADMIN-CONS-003/XSURF-C13] Store unique identity mismatch across surfaces: "
            f"{sorted(unique_values)}"
        )


@wave1_case(
    case_id="ADMIN-CONS-004",
    assertion_ids=["XSURF-C14"],
    domain="admin-consistency",
    priority="P0",
    risk="high",
)
def test_admin_cons_004_amount_currency_item_continuity(
    consistency_seed_context,
    user_session,
    merchant_store_session,
    admin_session,
    order_helper,
    merchant_helper,
    admin_helper,
    admin_consistency_report,
):
    order_id = consistency_seed_context["order_id"]
    surfaces = _fetch_order_surfaces(
        case_id="ADMIN-CONS-004",
        assertion_id="XSURF-C14",
        order_id=order_id,
        user_session=user_session,
        merchant_store_session=merchant_store_session,
        admin_session=admin_session,
        order_helper=order_helper,
        merchant_helper=merchant_helper,
        admin_helper=admin_helper,
    )

    user_total, user_currency, user_count = _extract_amount_currency(surfaces["user"])
    merchant_total, merchant_currency, merchant_count = _extract_amount_currency(surfaces["merchant"])
    admin_total, admin_currency, admin_count = _extract_amount_currency(surfaces["admin"])

    totals = [value for value in (user_total, merchant_total, admin_total) if isinstance(value, float)]
    if len(totals) < 2:
        pytest.skip("[ADMIN-CONS-004] Amount fields are not observable on enough surfaces for continuity check.")
    baseline = totals[0]
    for value in totals[1:]:
        assert abs(value - baseline) <= 0.01, (
            f"[ADMIN-CONS-004/XSURF-C14] Total mismatch across surfaces: "
            f"user={user_total} merchant={merchant_total} admin={admin_total}"
        )

    currencies = [value for value in (user_currency, merchant_currency, admin_currency) if isinstance(value, str)]
    if len(currencies) >= 2:
        assert len(set(currencies)) == 1, (
            f"[ADMIN-CONS-004/XSURF-C14] Currency mismatch across surfaces: "
            f"user={user_currency} merchant={merchant_currency} admin={admin_currency}"
        )

    item_counts = [value for value in (user_count, merchant_count, admin_count) if isinstance(value, int)]
    if len(item_counts) >= 2:
        assert len(set(item_counts)) == 1, (
            f"[ADMIN-CONS-004/XSURF-C14] Item-count mismatch across surfaces: "
            f"user={user_count} merchant={merchant_count} admin={admin_count}"
        )

    admin_consistency_report["amount_matrix"] = {
        "user_total": user_total,
        "user_currency": user_currency,
        "user_item_count": user_count,
        "merchant_total": merchant_total,
        "merchant_currency": merchant_currency,
        "merchant_item_count": merchant_count,
        "admin_total": admin_total,
        "admin_currency": admin_currency,
        "admin_item_count": admin_count,
    }


@wave1_case(
    case_id="ADMIN-CONS-005",
    assertion_ids=["XSURF-C15"],
    domain="admin-consistency",
    priority="P0",
    risk="high",
)
def test_admin_cons_005_terminal_visibility_and_mutation_safety(
    terminal_seed_context,
    user_session,
    merchant_store_session,
    admin_session,
    order_helper,
    merchant_helper,
    admin_helper,
):
    order_id = terminal_seed_context["order_id"]
    surfaces = _fetch_order_surfaces(
        case_id="ADMIN-CONS-005",
        assertion_id="XSURF-C15",
        order_id=order_id,
        user_session=user_session,
        merchant_store_session=merchant_store_session,
        admin_session=admin_session,
        order_helper=order_helper,
        merchant_helper=merchant_helper,
        admin_helper=admin_helper,
    )
    _, user_semantic = _extract_status(surfaces["user"], case_id="ADMIN-CONS-005", assertion_id="XSURF-C15")
    _, merchant_semantic = _extract_status(surfaces["merchant"], case_id="ADMIN-CONS-005", assertion_id="XSURF-C15")
    _, admin_semantic = _extract_status(surfaces["admin"], case_id="ADMIN-CONS-005", assertion_id="XSURF-C15")
    for surface, semantic in (
        ("user", user_semantic),
        ("merchant", merchant_semantic),
        ("admin", admin_semantic),
    ):
        assert semantic in TERMINAL_STATUSES, (
            f"[ADMIN-CONS-005/XSURF-C15] {surface} surface is not terminal for terminal seed order {order_id}: {semantic}"
        )

    for action, response in (
        ("accept", merchant_helper.accept_order(token=merchant_store_session.store_token, order_id=order_id)),
        ("cancel", merchant_helper.cancel_order(token=merchant_store_session.store_token, order_id=order_id)),
    ):
        assert response.status_code in {200, 400, 401, 403, 404, 409, 422}, (
            f"[ADMIN-CONS-005/XSURF-C15] Unexpected status on terminal {action}: "
            f"{response.status_code} body={response.text[:1000]}"
        )
        if response.status_code == 200:
            payload = assert_success_envelope(response, assertion_id="XSURF-C15", case_id="ADMIN-CONS-005")
            data = _extract_data(payload, case_id="ADMIN-CONS-005", assertion_id="XSURF-C15")
            _, semantic = _extract_status(data, case_id="ADMIN-CONS-005", assertion_id="XSURF-C15")
            assert semantic in TERMINAL_STATUSES, (
                f"[ADMIN-CONS-005/XSURF-C15] Terminal mutation changed order into active state via {action}: {semantic}"
            )

    refreshed = _fetch_order_surfaces(
        case_id="ADMIN-CONS-005",
        assertion_id="XSURF-C15",
        order_id=order_id,
        user_session=user_session,
        merchant_store_session=merchant_store_session,
        admin_session=admin_session,
        order_helper=order_helper,
        merchant_helper=merchant_helper,
        admin_helper=admin_helper,
    )
    for surface_name, data in refreshed.items():
        _, semantic = _extract_status(data, case_id="ADMIN-CONS-005", assertion_id="XSURF-C15")
        assert semantic in TERMINAL_STATUSES, (
            f"[ADMIN-CONS-005/XSURF-C15] {surface_name} left terminal state after mutation attempt: {semantic}"
        )


@wave1_case(
    case_id="ADMIN-CONS-006",
    assertion_ids=["XSURF-C16"],
    domain="admin-consistency",
    priority="P1",
    risk="medium",
)
def test_admin_cons_006_lifecycle_seed_availability_guard(lifecycle_seed_payload):
    if not isinstance(lifecycle_seed_payload, Mapping) or not isinstance(lifecycle_seed_payload.get("order_id"), int):
        pytest.skip(
            "[ADMIN-CONS-006] order_lifecycle_seed.json is missing usable order_id. "
            "Run `test_order_lifecycle_flow_api.py` to generate deterministic lifecycle seed."
        )
    assert isinstance(lifecycle_seed_payload.get("order_id"), int)
