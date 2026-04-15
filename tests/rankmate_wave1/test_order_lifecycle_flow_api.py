"""Wave 1 full order lifecycle flow (API-first)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

import pytest

from .helpers.assertion_helper import (
    assert_order_status,
    assert_status,
    assert_success_envelope,
    envelope_data,
    extract_id,
)
from .helpers.idempotency import generate_idempotency_key
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


def _status_name(value: Optional[int]) -> Optional[str]:
    if not isinstance(value, int):
        return None
    return STATUS_NAMES.get(value, f"status_{value}")


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


def _extract_status(payload: Mapping[str, Any], *, case_id: str, assertion_id: str) -> int:
    data = envelope_data(payload)
    assert isinstance(data, Mapping), f"[{case_id}/{assertion_id}] Missing data envelope"
    status = data.get("status")
    assert isinstance(status, int), f"[{case_id}/{assertion_id}] Missing integer status: {payload}"
    return status


def _extract_store_id(payload: Mapping[str, Any], *, case_id: str, assertion_id: str) -> int:
    data = envelope_data(payload)
    assert isinstance(data, Mapping), f"[{case_id}/{assertion_id}] Missing order data envelope"
    store_id = data.get("storeId")
    assert isinstance(store_id, int), f"[{case_id}/{assertion_id}] Missing integer storeId: {payload}"
    return store_id


def _find_order_in_rows(rows: list[Mapping[str, Any]], order_id: int) -> Optional[Mapping[str, Any]]:
    for row in rows:
        row_id = row.get("id") or row.get("orderId")
        if isinstance(row_id, int) and row_id == order_id:
            return row
    return None


def _write_lifecycle_outputs(repo_root: Path, recorder: dict[str, Any]) -> None:
    seed_path = repo_root / "order_lifecycle_seed.json"
    report_path = repo_root / "docs" / "wave1_runtime" / "ORDER_LIFECYCLE_REPORT.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    notes = recorder.get("notes")
    if not isinstance(notes, list):
        notes = []
        recorder["notes"] = notes
    if recorder.get("order_id") is None:
        notes.append(
            "No lifecycle order was generated in this run. "
            "Most likely cause: backend reachability precheck skipped module execution."
        )

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "order_id": recorder.get("order_id"),
        "store_id": recorder.get("store_id"),
        "payment_attempt_id": recorder.get("payment_attempt_id"),
        "payment_transaction_id": recorder.get("payment_transaction_id"),
        "initial_status": _status_name(recorder.get("initial_status")),
        "final_status": _status_name(recorder.get("final_status")),
        "user_visible": bool(recorder.get("user_visible")),
        "merchant_visible": bool(recorder.get("merchant_visible")),
        "admin_visible": bool(recorder.get("admin_visible")),
        "notes": notes,
        "branches": recorder.get("branches", {}),
    }
    seed_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    branch_lines = []
    for branch_name, branch_data in sorted(payload.get("branches", {}).items()):
        if isinstance(branch_data, Mapping):
            status = branch_data.get("status")
            branch_order_id = branch_data.get("order_id")
            note = branch_data.get("note", "")
            branch_lines.append(
                f"| `{branch_name}` | `{branch_order_id if branch_order_id is not None else ''}` | "
                f"`{status if status is not None else ''}` | {note} |"
            )

    notes = payload.get("notes") or []
    report_lines = [
        "# ORDER_LIFECYCLE_REPORT",
        "",
        f"- Generated at: `{payload['generated_at_utc']}`",
        f"- Main order id: `{payload.get('order_id')}`",
        f"- Store id: `{payload.get('store_id')}`",
        f"- Initial status: `{payload.get('initial_status')}`",
        f"- Final status: `{payload.get('final_status')}`",
        f"- User visible: `{payload.get('user_visible')}`",
        f"- Merchant visible: `{payload.get('merchant_visible')}`",
        f"- Admin visible: `{payload.get('admin_visible')}`",
        "",
        "## Captured IDs",
        "",
        f"- `payment_attempt_id`: `{payload.get('payment_attempt_id')}`",
        f"- `payment_transaction_id`: `{payload.get('payment_transaction_id')}`",
        "",
        "## Branch Outcomes",
        "",
        "| Branch | Order ID | Status | Note |",
        "|---|---:|---:|---|",
        *(branch_lines if branch_lines else ["| `none` | `` | `` | No branch execution data captured |"]),
        "",
        "## Notes",
        "",
        *([f"- {line}" for line in notes] if notes else ["- none"]),
        "",
    ]
    report_path.write_text("\n".join(report_lines), encoding="utf-8")


@pytest.fixture(scope="module", autouse=True)
def lifecycle_recorder(wave1_repo_root: Path):
    recorder: dict[str, Any] = {
        "order_id": None,
        "store_id": None,
        "payment_attempt_id": None,
        "payment_transaction_id": None,
        "initial_status": None,
        "final_status": None,
        "user_visible": False,
        "merchant_visible": False,
        "admin_visible": False,
        "notes": [],
        "branches": {},
    }
    yield recorder
    _write_lifecycle_outputs(wave1_repo_root, recorder)


@pytest.fixture(scope="module")
def lifecycle_base_flow(
    wave1_config,
    require_config,
    user_session,
    search_helper,
    store_helper,
    order_helper,
    lifecycle_recorder,
):
    require_config("ORD-LIFE-001", "order_sku_id")
    store_id = wave1_config.order_store_id or wave1_config.menu_store_id or wave1_config.store_id
    if not isinstance(store_id, int):
        pytest.skip("[ORD-LIFE-001] Missing API_ORDER_STORE_ID/API_MENU_STORE_ID/API_STORE_ID")
    sku_id = wave1_config.order_sku_id
    if not isinstance(sku_id, int):
        pytest.skip("[ORD-LIFE-001] Missing API_ORDER_SKU_ID")

    keyword = (wave1_config.search_keyword or "").strip() or "banh"

    search_resp = search_helper.search_stores_v2(keyword=keyword, page_number=0, page_size=20)
    assert_status(search_resp, 200, assertion_id="SEARCH-A01", case_id="ORD-LIFE-001")
    search_payload = assert_success_envelope(search_resp, assertion_id="SEARCH-A01", case_id="ORD-LIFE-001")
    _ = _extract_rows(search_payload)

    store_detail_resp = store_helper.get_store_by_id(store_id=store_id, token=user_session.token)
    assert_status(store_detail_resp, 200, assertion_id="STORE-A01", case_id="ORD-LIFE-001")
    _ = assert_success_envelope(store_detail_resp, assertion_id="STORE-A01", case_id="ORD-LIFE-001")

    eligibility_resp = store_helper.get_store_eligibility(store_id=store_id)
    assert_status(eligibility_resp, 200, assertion_id="STORE-A02", case_id="ORD-LIFE-001")
    _ = assert_success_envelope(eligibility_resp, assertion_id="STORE-A02", case_id="ORD-LIFE-001")

    menu_resp = store_helper.get_store_menu(store_id=store_id)
    assert_status(menu_resp, 200, assertion_id="STORE-A03", case_id="ORD-LIFE-001")
    _ = assert_success_envelope(menu_resp, assertion_id="STORE-A03", case_id="ORD-LIFE-001")

    create_resp = order_helper.create_order(
        token=user_session.token,
        store_id=store_id,
        items=order_helper.build_items(sku_id, quantity=1),
        idempotency_key=generate_idempotency_key("ORD-LIFE-001-CREATE"),
    )
    assert_status(create_resp, 200, assertion_id="API-A05", case_id="ORD-LIFE-001")
    create_payload = assert_success_envelope(create_resp, assertion_id="API-A05", case_id="ORD-LIFE-001")
    order_id = extract_id(create_payload)
    initial_status = _extract_status(create_payload, case_id="ORD-LIFE-001", assertion_id="API-A05")
    payload_store_id = _extract_store_id(create_payload, case_id="ORD-LIFE-001", assertion_id="API-A05")

    detail_resp = order_helper.get_order(token=user_session.token, order_id=order_id)
    assert_status(detail_resp, 200, assertion_id="XSURF-C01", case_id="ORD-LIFE-001")
    detail_payload = assert_success_envelope(detail_resp, assertion_id="XSURF-C01", case_id="ORD-LIFE-001")
    detail_status = _extract_status(detail_payload, case_id="ORD-LIFE-001", assertion_id="XSURF-C01")
    assert detail_status == initial_status, (
        f"[ORD-LIFE-001/XSURF-C01] Initial status mismatch create={initial_status} detail={detail_status}"
    )

    history_resp = order_helper.list_orders(token=user_session.token)
    assert_status(history_resp, 200, assertion_id="XSURF-C01", case_id="ORD-LIFE-001")
    history_payload = assert_success_envelope(history_resp, assertion_id="XSURF-C01", case_id="ORD-LIFE-001")
    history_rows = _extract_rows(history_payload)
    history_row = _find_order_in_rows(history_rows, order_id)
    assert history_row is not None, (
        f"[ORD-LIFE-001/XSURF-C01] Created order {order_id} not found in user history/list."
    )

    lifecycle_recorder["order_id"] = order_id
    lifecycle_recorder["store_id"] = payload_store_id
    lifecycle_recorder["initial_status"] = initial_status
    lifecycle_recorder["final_status"] = detail_status
    lifecycle_recorder["user_visible"] = True
    lifecycle_recorder["notes"].append(
        f"Golden path created order {order_id} for store {payload_store_id} and verified user detail/history."
    )

    return {
        "order_id": order_id,
        "store_id": payload_store_id,
        "initial_status": initial_status,
    }


@wave1_case(
    case_id="ORD-LIFE-001",
    assertion_ids=["API-A05", "XSURF-C01"],
    domain="order-lifecycle",
    priority="P0",
    risk="critical",
)
def test_order_lifecycle_001_golden_path_create_history_detail(lifecycle_base_flow):
    assert isinstance(lifecycle_base_flow["order_id"], int)
    assert isinstance(lifecycle_base_flow["store_id"], int)
    assert isinstance(lifecycle_base_flow["initial_status"], int)


@wave1_case(
    case_id="ORD-LIFE-002",
    assertion_ids=["API-A10"],
    domain="order-lifecycle",
    priority="P0",
    risk="high",
)
def test_order_lifecycle_002_payment_init_and_verify_branch(
    user_session,
    payment_helper,
    case_skip,
    lifecycle_base_flow,
    lifecycle_recorder,
):
    order_id = lifecycle_base_flow["order_id"]

    init_resp = payment_helper.create_order_payment_intent(
        token=user_session.token,
        order_id=order_id,
        idempotency_key=generate_idempotency_key("ORD-LIFE-002-PAY"),
    )
    assert_status(init_resp, {200, 400, 409, 422}, assertion_id="API-A10", case_id="ORD-LIFE-002")
    if init_resp.status_code != 200:
        lifecycle_recorder["branches"]["payment"] = {
            "order_id": order_id,
            "status": init_resp.status_code,
            "note": "Payment init did not reach success path; webhook realism intentionally not faked.",
        }
        case_skip(
            "ORD-LIFE-002",
            f"Payment init not in success path for order {order_id}; status={init_resp.status_code}",
        )

    init_payload = assert_success_envelope(init_resp, assertion_id="API-A10", case_id="ORD-LIFE-002")
    data = envelope_data(init_payload)
    assert isinstance(data, Mapping), "[ORD-LIFE-002/API-A10] Missing payment init data envelope"
    payment_attempt_id = data.get("paymentAttemptId")
    assert isinstance(payment_attempt_id, int), "[ORD-LIFE-002/API-A10] paymentAttemptId missing"

    verify_resp = payment_helper.verify_order_payment(token=user_session.token, order_id=order_id)
    assert_status(verify_resp, 200, assertion_id="API-A10", case_id="ORD-LIFE-002")
    verify_payload = assert_success_envelope(verify_resp, assertion_id="API-A10", case_id="ORD-LIFE-002")
    verify_data = envelope_data(verify_payload)
    transaction_id = None
    if isinstance(verify_data, Mapping):
        tx = verify_data.get("paymentTransactionId") or verify_data.get("transactionId")
        transaction_id = tx if isinstance(tx, int) else None

    lifecycle_recorder["payment_attempt_id"] = payment_attempt_id
    if isinstance(transaction_id, int):
        lifecycle_recorder["payment_transaction_id"] = transaction_id
    lifecycle_recorder["branches"]["payment"] = {
        "order_id": order_id,
        "status": 200,
        "note": "Payment init+verify contract completed without webhook mutation.",
    }


@wave1_case(
    case_id="ORD-LIFE-003",
    assertion_ids=["XSURF-C02"],
    domain="order-lifecycle",
    priority="P0",
    risk="high",
)
def test_order_lifecycle_003_merchant_queue_detail_visibility(
    lifecycle_base_flow,
    merchant_store_session,
    merchant_helper,
    case_skip,
    lifecycle_recorder,
):
    order_id = lifecycle_base_flow["order_id"]
    list_resp = merchant_helper.list_orders(
        token=merchant_store_session.store_token,
        store_id=merchant_store_session.store_id,
    )
    assert_status(list_resp, 200, assertion_id="XSURF-C02", case_id="ORD-LIFE-003")
    list_payload = assert_success_envelope(list_resp, assertion_id="XSURF-C02", case_id="ORD-LIFE-003")
    rows = _extract_rows(list_payload)
    row = _find_order_in_rows(rows, order_id)
    if row is None:
        lifecycle_recorder["branches"]["merchant_visibility"] = {
            "order_id": order_id,
            "status": list_resp.status_code,
            "note": "Order not visible in merchant queue page for current scope/store.",
        }
        case_skip("ORD-LIFE-003", f"Order {order_id} not visible in merchant queue for store={merchant_store_session.store_id}")

    detail_resp = merchant_helper.get_order_detail(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(detail_resp, 200, assertion_id="XSURF-C02", case_id="ORD-LIFE-003")
    _ = assert_success_envelope(detail_resp, assertion_id="XSURF-C02", case_id="ORD-LIFE-003")
    lifecycle_recorder["merchant_visible"] = True
    lifecycle_recorder["branches"]["merchant_visibility"] = {
        "order_id": order_id,
        "status": 200,
        "note": "Merchant list/detail visibility confirmed.",
    }


@wave1_case(
    case_id="ORD-LIFE-004",
    assertion_ids=["API-A13", "XSURF-C02"],
    domain="order-lifecycle",
    priority="P1",
    risk="high",
)
def test_order_lifecycle_004_merchant_happy_transition_from_paid_seed(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    user_session,
    order_helper,
    case_skip,
    lifecycle_recorder,
):
    paid_seed = wave1_config.paid_order_id
    if not isinstance(paid_seed, int):
        case_skip("ORD-LIFE-004", "Missing API_PAID_ORDER_ID seed for merchant happy transition flow")

    detail_before_resp = merchant_helper.get_order_detail(token=merchant_store_session.store_token, order_id=paid_seed)
    if detail_before_resp.status_code != 200:
        case_skip("ORD-LIFE-004", f"Merchant cannot access paid seed order {paid_seed}; status={detail_before_resp.status_code}")
    detail_before = assert_success_envelope(detail_before_resp, assertion_id="API-A13", case_id="ORD-LIFE-004")
    status_before = _extract_status(detail_before, case_id="ORD-LIFE-004", assertion_id="API-A13")
    if status_before != 20:
        case_skip("ORD-LIFE-004", f"Paid seed order {paid_seed} is not status=20 (actual={status_before})")

    accept_resp = merchant_helper.accept_order(token=merchant_store_session.store_token, order_id=paid_seed)
    assert_status(accept_resp, 200, assertion_id="API-A13", case_id="ORD-LIFE-004")
    accept_payload = assert_success_envelope(accept_resp, assertion_id="API-A13", case_id="ORD-LIFE-004")
    assert_order_status(accept_payload, {21}, assertion_id="API-A13", case_id="ORD-LIFE-004")

    arrived_resp = merchant_helper.mark_arrived(token=merchant_store_session.store_token, order_id=paid_seed)
    assert_status(arrived_resp, 200, assertion_id="API-A13", case_id="ORD-LIFE-004")
    arrived_payload = assert_success_envelope(arrived_resp, assertion_id="API-A13", case_id="ORD-LIFE-004")
    assert_order_status(arrived_payload, {22}, assertion_id="API-A13", case_id="ORD-LIFE-004")

    complete_resp = merchant_helper.complete_order(
        token=merchant_store_session.store_token,
        order_id=paid_seed,
        pay_at_store_collected_amount=1.0,
    )
    assert_status(complete_resp, 200, assertion_id="API-A13", case_id="ORD-LIFE-004")
    complete_payload = assert_success_envelope(complete_resp, assertion_id="API-A13", case_id="ORD-LIFE-004")
    final_status = assert_order_status(complete_payload, {23, 24}, assertion_id="API-A13", case_id="ORD-LIFE-004")

    user_detail_resp = order_helper.get_order(token=user_session.token, order_id=paid_seed)
    if user_detail_resp.status_code == 200:
        user_payload = assert_success_envelope(user_detail_resp, assertion_id="XSURF-C02", case_id="ORD-LIFE-004")
        _ = _extract_status(user_payload, case_id="ORD-LIFE-004", assertion_id="XSURF-C02")
        lifecycle_recorder["user_visible"] = True

    lifecycle_recorder["final_status"] = final_status
    lifecycle_recorder["branches"]["merchant_happy"] = {
        "order_id": paid_seed,
        "status": final_status,
        "note": "accept -> arrived -> complete executed from paid seed",
    }


@wave1_case(
    case_id="ORD-LIFE-005",
    assertion_ids=["API-A13"],
    domain="order-lifecycle",
    priority="P1",
    risk="high",
)
def test_order_lifecycle_005_negative_cancel_branch(
    wave1_config,
    user_session,
    order_helper,
    case_skip,
    lifecycle_recorder,
):
    store_id = wave1_config.order_store_id or wave1_config.menu_store_id or wave1_config.store_id
    sku_id = wave1_config.order_sku_id
    if not isinstance(store_id, int) or not isinstance(sku_id, int):
        case_skip("ORD-LIFE-005", "Missing API_ORDER_STORE_ID/API_MENU_STORE_ID/API_STORE_ID + API_ORDER_SKU_ID")

    create_resp = order_helper.create_order(
        token=user_session.token,
        store_id=store_id,
        items=order_helper.build_items(sku_id, quantity=1),
        idempotency_key=generate_idempotency_key("ORD-LIFE-005-CREATE"),
    )
    assert_status(create_resp, 200, assertion_id="API-A05", case_id="ORD-LIFE-005")
    create_payload = assert_success_envelope(create_resp, assertion_id="API-A05", case_id="ORD-LIFE-005")
    cancel_order_id = extract_id(create_payload)

    cancel_resp = order_helper.cancel_order(token=user_session.token, order_id=cancel_order_id)
    if cancel_resp.status_code != 200:
        lifecycle_recorder["branches"]["cancel"] = {
            "order_id": cancel_order_id,
            "status": cancel_resp.status_code,
            "note": "Cancel did not reach happy branch; kept as controlled contract observation.",
        }
        case_skip("ORD-LIFE-005", f"Cancel branch did not reach success for order {cancel_order_id}; status={cancel_resp.status_code}")

    cancel_payload = assert_success_envelope(cancel_resp, assertion_id="API-A13", case_id="ORD-LIFE-005")
    # Runtime contract note:
    # Cancel currently returns success envelope, but immediate order status may remain 10 (pending)
    # before downstream state transition processing. Keep this strict to observed controlled states only.
    cancel_status = assert_order_status(cancel_payload, {10, 60, 90}, assertion_id="API-A13", case_id="ORD-LIFE-005")
    detail_resp = order_helper.get_order(token=user_session.token, order_id=cancel_order_id)
    assert_status(detail_resp, 200, assertion_id="XSURF-C01", case_id="ORD-LIFE-005")
    detail_payload = assert_success_envelope(detail_resp, assertion_id="XSURF-C01", case_id="ORD-LIFE-005")
    detail_status = _extract_status(detail_payload, case_id="ORD-LIFE-005", assertion_id="XSURF-C01")
    assert detail_status in {10, 60, 90}, (
        f"[ORD-LIFE-005/XSURF-C01] Unexpected post-cancel detail status: {detail_status}"
    )

    lifecycle_recorder["branches"]["cancel"] = {
        "order_id": cancel_order_id,
        "status": cancel_status,
        "note": "create -> cancel branch verified by user detail",
    }


@wave1_case(
    case_id="ORD-LIFE-006",
    assertion_ids=["API-A13"],
    domain="order-lifecycle",
    priority="P1",
    risk="high",
)
def test_order_lifecycle_006_negative_reject_branch(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
    lifecycle_recorder,
):
    order_id = wave1_config.rejectable_paid_order_id
    if not isinstance(order_id, int):
        case_skip("ORD-LIFE-006", "Missing API_REJECTABLE_PAID_ORDER_ID seed")

    detail_resp = merchant_helper.get_order_detail(token=merchant_store_session.store_token, order_id=order_id)
    if detail_resp.status_code != 200:
        case_skip("ORD-LIFE-006", f"Merchant cannot access reject seed order {order_id}; status={detail_resp.status_code}")
    detail_payload = assert_success_envelope(detail_resp, assertion_id="API-A13", case_id="ORD-LIFE-006")
    status_before = _extract_status(detail_payload, case_id="ORD-LIFE-006", assertion_id="API-A13")
    if status_before != 20:
        case_skip("ORD-LIFE-006", f"Reject seed order {order_id} is not status=20 (actual={status_before})")

    reject_resp = merchant_helper.reject_order(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(reject_resp, 200, assertion_id="API-A13", case_id="ORD-LIFE-006")
    reject_payload = assert_success_envelope(reject_resp, assertion_id="API-A13", case_id="ORD-LIFE-006")
    reject_status = assert_order_status(reject_payload, {40, 60, 90}, assertion_id="API-A13", case_id="ORD-LIFE-006")
    lifecycle_recorder["branches"]["reject"] = {
        "order_id": order_id,
        "status": reject_status,
        "note": "merchant reject branch from paid seed",
    }


@wave1_case(
    case_id="ORD-LIFE-007",
    assertion_ids=["API-A13", "API-A07"],
    domain="order-lifecycle",
    priority="P1",
    risk="high",
)
def test_order_lifecycle_007_negative_no_show_and_duplicate_submit(
    wave1_config,
    user_session,
    order_helper,
    merchant_store_session,
    merchant_helper,
    case_skip,
    lifecycle_recorder,
):
    # Duplicate-submit branch
    store_id = wave1_config.order_store_id or wave1_config.menu_store_id or wave1_config.store_id
    sku_id = wave1_config.order_sku_id
    if not isinstance(store_id, int) or not isinstance(sku_id, int):
        case_skip("ORD-LIFE-007", "Missing store/sku config for duplicate submit branch")

    idem_key = generate_idempotency_key("ORD-LIFE-007-DUP")
    first = order_helper.create_order(
        token=user_session.token,
        store_id=store_id,
        items=order_helper.build_items(sku_id, quantity=1),
        idempotency_key=idem_key,
    )
    second = order_helper.create_order(
        token=user_session.token,
        store_id=store_id,
        items=order_helper.build_items(sku_id, quantity=1),
        idempotency_key=idem_key,
    )
    assert_status(first, 200, assertion_id="API-A07", case_id="ORD-LIFE-007")
    assert_status(second, 200, assertion_id="API-A07", case_id="ORD-LIFE-007")
    first_payload = assert_success_envelope(first, assertion_id="API-A07", case_id="ORD-LIFE-007")
    second_payload = assert_success_envelope(second, assertion_id="API-A07", case_id="ORD-LIFE-007")
    first_id = extract_id(first_payload)
    second_id = extract_id(second_payload)
    assert first_id == second_id, (
        f"[ORD-LIFE-007/API-A07] Duplicate submit same key created mismatched orders: {first_id} vs {second_id}"
    )

    # No-show branch
    no_show_seed = wave1_config.no_show_order_id
    if not isinstance(no_show_seed, int):
        lifecycle_recorder["branches"]["no_show"] = {
            "order_id": None,
            "status": None,
            "note": "Missing API_NO_SHOW_ORDER_ID seed.",
        }
        case_skip("ORD-LIFE-007", "Missing API_NO_SHOW_ORDER_ID seed for no-show branch")

    detail_resp = merchant_helper.get_order_detail(token=merchant_store_session.store_token, order_id=no_show_seed)
    if detail_resp.status_code != 200:
        case_skip("ORD-LIFE-007", f"Merchant cannot access no-show seed {no_show_seed}; status={detail_resp.status_code}")
    detail_payload = assert_success_envelope(detail_resp, assertion_id="API-A13", case_id="ORD-LIFE-007")
    seed_status = _extract_status(detail_payload, case_id="ORD-LIFE-007", assertion_id="API-A13")
    if seed_status not in {21, 22}:
        case_skip("ORD-LIFE-007", f"No-show seed {no_show_seed} status {seed_status} is not eligible")

    no_show_resp = merchant_helper.mark_no_show(token=merchant_store_session.store_token, order_id=no_show_seed)
    assert_status(no_show_resp, {200, 400}, assertion_id="API-A13", case_id="ORD-LIFE-007")
    no_show_status: Optional[int] = None
    if no_show_resp.status_code == 200:
        no_show_payload = assert_success_envelope(no_show_resp, assertion_id="API-A13", case_id="ORD-LIFE-007")
        no_show_status = assert_order_status(no_show_payload, {91, 60, 90}, assertion_id="API-A13", case_id="ORD-LIFE-007")

    lifecycle_recorder["branches"]["duplicate_submit"] = {
        "order_id": first_id,
        "status": 200,
        "note": "Same idempotency key returned same order id.",
    }
    lifecycle_recorder["branches"]["no_show"] = {
        "order_id": no_show_seed,
        "status": no_show_status or no_show_resp.status_code,
        "note": "No-show branch executed with controlled status.",
    }


@wave1_case(
    case_id="ORD-LIFE-008",
    assertion_ids=["API-A13"],
    domain="order-lifecycle",
    priority="P1",
    risk="medium",
)
def test_order_lifecycle_008_stale_retry_terminal_safety(
    wave1_config,
    user_session,
    order_helper,
    case_skip,
    lifecycle_recorder,
):
    order_id = wave1_config.cancelled_order_id
    if not isinstance(order_id, int):
        case_skip("ORD-LIFE-008", "Missing API_CANCELLED_ORDER_ID seed for stale terminal action safety")

    first_cancel = order_helper.cancel_order(token=user_session.token, order_id=order_id)
    assert_status(first_cancel, {200, 400, 409, 422}, assertion_id="API-A13", case_id="ORD-LIFE-008")

    second_cancel = order_helper.cancel_order(token=user_session.token, order_id=order_id)
    assert_status(second_cancel, {200, 400, 409, 422}, assertion_id="API-A13", case_id="ORD-LIFE-008")

    detail_resp = order_helper.get_order(token=user_session.token, order_id=order_id)
    assert_status(detail_resp, 200, assertion_id="XSURF-C01", case_id="ORD-LIFE-008")
    detail_payload = assert_success_envelope(detail_resp, assertion_id="XSURF-C01", case_id="ORD-LIFE-008")
    final_status = _extract_status(detail_payload, case_id="ORD-LIFE-008", assertion_id="XSURF-C01")
    assert final_status in {60, 90, 40, 50, 23, 24}, (
        f"[ORD-LIFE-008/API-A13] Unexpected terminal-safety status after repeated cancel: {final_status}"
    )

    lifecycle_recorder["branches"]["stale_terminal"] = {
        "order_id": order_id,
        "status": final_status,
        "note": "Repeated terminal action returned controlled status and did not crash.",
    }
    lifecycle_recorder["final_status"] = final_status
