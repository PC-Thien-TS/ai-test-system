"""Wave 1 MER-API-* automated tests."""

from __future__ import annotations

from typing import Any, Mapping

from .helpers.assertion_helper import (
    assert_order_status,
    assert_status,
    assert_success_envelope,
    envelope_data,
)
from .helpers.result_tags import wave1_case


def _extract_rows(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    data = envelope_data(payload)
    if isinstance(data, Mapping):
        candidates = data.get("data") or data.get("items") or data.get("rows")
        if isinstance(candidates, list):
            return [row for row in candidates if isinstance(row, Mapping)]
    if isinstance(data, list):
        return [row for row in data if isinstance(row, Mapping)]
    return []


def _order_id_or_skip(case_id: str, value: int | None, case_skip, env_name: str) -> int:
    if not isinstance(value, int):
        case_skip(case_id, f"Missing required seeded order id: {env_name}")
    return value


@wave1_case(
    case_id="MER-API-001",
    assertion_ids=["XSURF-C02"],
    domain="merchant",
    priority="P0",
    risk="high",
)
def test_mer_api_001_merchant_queue_contains_paid_order(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    target_order_id = _order_id_or_skip(
        "MER-API-001",
        wave1_config.paid_order_id,
        case_skip,
        "API_PAID_ORDER_ID",
    )

    response = merchant_helper.list_orders(
        token=merchant_store_session.store_token,
        store_id=merchant_store_session.store_id,
        status=20,
    )
    assert_status(response, 200, assertion_id="XSURF-C02", case_id="MER-API-001")
    payload = assert_success_envelope(response, assertion_id="XSURF-C02", case_id="MER-API-001")
    rows = _extract_rows(payload)
    order_ids = {row.get("id") for row in rows}
    assert target_order_id in order_ids, (
        f"[MER-API-001/XSURF-C02] Expected paid order {target_order_id} in merchant queue. "
        f"returned_ids={sorted(v for v in order_ids if isinstance(v, int))}"
    )


@wave1_case(
    case_id="MER-API-002",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P0",
    risk="critical",
)
def test_mer_api_002_merchant_accept_success(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = _order_id_or_skip("MER-API-002", wave1_config.paid_order_id, case_skip, "API_PAID_ORDER_ID")

    detail_before = merchant_helper.get_order_detail(token=merchant_store_session.store_token, order_id=order_id)
    if detail_before.status_code != 200:
        case_skip(
            "MER-API-002",
            f"Precheck failed for order {order_id}: expected 200 detail, got {detail_before.status_code}",
        )
    before_payload = assert_success_envelope(detail_before, assertion_id="API-A13", case_id="MER-API-002")
    if before_payload.get("data", {}).get("status") != 20:
        case_skip("MER-API-002", f"Precondition failed: order {order_id} is not Paid(status=20)")

    accept_response = merchant_helper.accept_order(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(accept_response, 200, assertion_id="API-A13", case_id="MER-API-002")
    accept_payload = assert_success_envelope(accept_response, assertion_id="API-A13", case_id="MER-API-002")
    assert_order_status(accept_payload, {21}, assertion_id="API-A13", case_id="MER-API-002")


@wave1_case(
    case_id="MER-API-003",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P0",
    risk="critical",
)
def test_mer_api_003_merchant_reject_success(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = _order_id_or_skip(
        "MER-API-003",
        wave1_config.rejectable_paid_order_id,
        case_skip,
        "API_REJECTABLE_PAID_ORDER_ID",
    )

    detail_before = merchant_helper.get_order_detail(token=merchant_store_session.store_token, order_id=order_id)
    if detail_before.status_code != 200:
        case_skip(
            "MER-API-003",
            f"Precheck failed for order {order_id}: expected 200 detail, got {detail_before.status_code}",
        )
    before_payload = assert_success_envelope(detail_before, assertion_id="API-A13", case_id="MER-API-003")
    if before_payload.get("data", {}).get("status") != 20:
        case_skip("MER-API-003", f"Precondition failed: order {order_id} is not Paid(status=20)")

    reject_response = merchant_helper.reject_order(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(reject_response, 200, assertion_id="API-A13", case_id="MER-API-003")
    reject_payload = assert_success_envelope(reject_response, assertion_id="API-A13", case_id="MER-API-003")
    assert_order_status(reject_payload, {40, 60, 90}, assertion_id="API-A13", case_id="MER-API-003")


@wave1_case(
    case_id="MER-API-004",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P0",
    risk="critical",
)
def test_mer_api_004_mark_arrived_success(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = _order_id_or_skip(
        "MER-API-004",
        wave1_config.accepted_order_id,
        case_skip,
        "API_ACCEPTED_ORDER_ID",
    )

    detail_before = merchant_helper.get_order_detail(token=merchant_store_session.store_token, order_id=order_id)
    if detail_before.status_code != 200:
        case_skip(
            "MER-API-004",
            f"Precheck failed for order {order_id}: expected 200 detail, got {detail_before.status_code}",
        )
    before_payload = assert_success_envelope(detail_before, assertion_id="API-A13", case_id="MER-API-004")
    if before_payload.get("data", {}).get("status") != 21:
        case_skip("MER-API-004", f"Precondition failed: order {order_id} is not Accepted(status=21)")

    arrived_response = merchant_helper.mark_arrived(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(arrived_response, 200, assertion_id="API-A13", case_id="MER-API-004")
    arrived_payload = assert_success_envelope(arrived_response, assertion_id="API-A13", case_id="MER-API-004")
    assert_order_status(arrived_payload, {22}, assertion_id="API-A13", case_id="MER-API-004")


@wave1_case(
    case_id="MER-API-005",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P0",
    risk="critical",
)
def test_mer_api_005_complete_success(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = _order_id_or_skip("MER-API-005", wave1_config.arrived_order_id, case_skip, "API_ARRIVED_ORDER_ID")

    detail_before = merchant_helper.get_order_detail(token=merchant_store_session.store_token, order_id=order_id)
    if detail_before.status_code != 200:
        case_skip(
            "MER-API-005",
            f"Precheck failed for order {order_id}: expected 200 detail, got {detail_before.status_code}",
        )
    before_payload = assert_success_envelope(detail_before, assertion_id="API-A13", case_id="MER-API-005")
    if before_payload.get("data", {}).get("status") != 22:
        case_skip("MER-API-005", f"Precondition failed: order {order_id} is not Arrived(status=22)")

    complete_response = merchant_helper.complete_order(
        token=merchant_store_session.store_token,
        order_id=order_id,
        pay_at_store_collected_amount=1.0,
    )
    assert_status(complete_response, 200, assertion_id="API-A13", case_id="MER-API-005")
    complete_payload = assert_success_envelope(complete_response, assertion_id="API-A13", case_id="MER-API-005")
    assert_order_status(complete_payload, {23, 24}, assertion_id="API-A13", case_id="MER-API-005")


@wave1_case(
    case_id="MER-API-006",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P0",
    risk="high",
)
def test_mer_api_006_complete_without_required_collected_amount_rejected(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = _order_id_or_skip(
        "MER-API-006",
        wave1_config.arrived_order_with_offline_due_id,
        case_skip,
        "API_ARRIVED_ORDER_WITH_OFFLINE_DUE_ID",
    )
    response = merchant_helper.complete_order(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(response, 400, assertion_id="API-A13", case_id="MER-API-006")


@wave1_case(
    case_id="MER-API-007",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P0",
    risk="high",
)
def test_mer_api_007_accept_invalid_state_rejected(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = wave1_config.non_paid_order_id or wave1_config.cancelled_order_id or wave1_config.completed_order_id
    order_id = _order_id_or_skip(
        "MER-API-007",
        order_id,
        case_skip,
        "API_NON_PAID_ORDER_ID/API_CANCELLED_ORDER_ID/API_COMPLETED_ORDER_ID",
    )
    response = merchant_helper.accept_order(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(response, 400, assertion_id="API-A13", case_id="MER-API-007")


@wave1_case(
    case_id="MER-API-008",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P1",
    risk="high",
)
def test_mer_api_008_mark_arrived_on_stale_state_rejected(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = wave1_config.stale_transition_order_id or wave1_config.completed_order_id or wave1_config.cancelled_order_id
    order_id = _order_id_or_skip(
        "MER-API-008",
        order_id,
        case_skip,
        "API_STALE_TRANSITION_ORDER_ID/API_COMPLETED_ORDER_ID/API_CANCELLED_ORDER_ID",
    )
    response = merchant_helper.mark_arrived(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(response, 400, assertion_id="API-A13", case_id="MER-API-008")


@wave1_case(
    case_id="MER-API-009",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P1",
    risk="medium",
)
def test_mer_api_009_no_show_path_behaves_safely(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = wave1_config.no_show_order_id or wave1_config.arrived_order_id
    order_id = _order_id_or_skip(
        "MER-API-009",
        order_id,
        case_skip,
        "API_NO_SHOW_ORDER_ID/API_ARRIVED_ORDER_ID",
    )

    response = merchant_helper.mark_no_show(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(response, {200, 400}, assertion_id="API-A13", case_id="MER-API-009")
    if response.status_code == 200:
        _ = assert_success_envelope(response, assertion_id="API-A13", case_id="MER-API-009")


@wave1_case(
    case_id="MER-API-010",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P1",
    risk="high",
)
def test_mer_api_010_merchant_cancel_behaves_safely(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = wave1_config.merchant_cancellable_order_id or wave1_config.pending_order_id
    order_id = _order_id_or_skip(
        "MER-API-010",
        order_id,
        case_skip,
        "API_MERCHANT_CANCELLABLE_ORDER_ID/API_PENDING_ORDER_ID",
    )

    response = merchant_helper.cancel_order(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(response, 200, assertion_id="API-A13", case_id="MER-API-010")
    payload = assert_success_envelope(response, assertion_id="API-A13", case_id="MER-API-010")
    assert_order_status(payload, {60, 90}, assertion_id="API-A13", case_id="MER-API-010")

