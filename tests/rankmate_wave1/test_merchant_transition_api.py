"""Wave 1 Merchant seeded-transition API automation (Phase E)."""

from __future__ import annotations

from typing import Any, Mapping, Optional

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
        for key in ("data", "items", "rows", "records"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return [row for row in candidate if isinstance(row, Mapping)]
    if isinstance(data, list):
        return [row for row in data if isinstance(row, Mapping)]
    return []


def _seed_or_skip(case_id: str, value: Optional[int], env_name: str, case_skip) -> int:
    if isinstance(value, int):
        return value
    case_skip(case_id, f"Missing required seeded order id: {env_name}")
    raise AssertionError("unreachable")


def _load_merchant_detail(*, case_id: str, token: str, order_id: int, merchant_helper, case_skip):
    response = merchant_helper.get_order_detail(token=token, order_id=order_id)
    if response.status_code != 200:
        case_skip(case_id, f"Merchant detail precheck failed for order {order_id}: status={response.status_code}")
    return assert_success_envelope(response, assertion_id="API-A13", case_id=case_id)


@wave1_case(
    case_id="MER-API-011",
    assertion_ids=["XSURF-C02"],
    domain="merchant",
    priority="P0",
    risk="high",
)
def test_mer_api_011_queue_list_controlled_success(
    merchant_store_session,
    merchant_helper,
):
    response = merchant_helper.list_orders(
        token=merchant_store_session.store_token,
        store_id=merchant_store_session.store_id,
        status=20,
    )
    assert_status(response, 200, assertion_id="XSURF-C02", case_id="MER-API-011")
    payload = assert_success_envelope(response, assertion_id="XSURF-C02", case_id="MER-API-011")
    _ = _extract_rows(payload)


@wave1_case(
    case_id="MER-API-012",
    assertion_ids=["XSURF-C02"],
    domain="merchant",
    priority="P0",
    risk="high",
)
def test_mer_api_012_detail_controlled_success_for_seeded_order(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    seeded_order_id = (
        wave1_config.paid_order_id
        or wave1_config.accepted_order_id
        or wave1_config.arrived_order_id
        or wave1_config.cancelled_order_id
        or wave1_config.completed_order_id
    )
    order_id = _seed_or_skip(
        "MER-API-012",
        seeded_order_id,
        "API_PAID_ORDER_ID/API_ACCEPTED_ORDER_ID/API_ARRIVED_ORDER_ID/API_CANCELLED_ORDER_ID/API_COMPLETED_ORDER_ID",
        case_skip,
    )

    response = merchant_helper.get_order_detail(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(response, 200, assertion_id="XSURF-C02", case_id="MER-API-012")
    payload = assert_success_envelope(response, assertion_id="XSURF-C02", case_id="MER-API-012")
    data = envelope_data(payload)
    assert isinstance(data, Mapping), (
        f"[MER-API-012/XSURF-C02] Expected merchant detail mapping payload, got {type(data).__name__}"
    )


@wave1_case(
    case_id="MER-API-013",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P0",
    risk="critical",
)
def test_mer_api_013_accept_valid_paid_order(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = _seed_or_skip("MER-API-013", wave1_config.paid_order_id, "API_PAID_ORDER_ID", case_skip)
    before_payload = _load_merchant_detail(
        case_id="MER-API-013",
        token=merchant_store_session.store_token,
        order_id=order_id,
        merchant_helper=merchant_helper,
        case_skip=case_skip,
    )
    if before_payload.get("data", {}).get("status") != 20:
        case_skip("MER-API-013", f"Precondition failed: order {order_id} is not Paid(status=20)")

    response = merchant_helper.accept_order(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(response, 200, assertion_id="API-A13", case_id="MER-API-013")
    payload = assert_success_envelope(response, assertion_id="API-A13", case_id="MER-API-013")
    assert_order_status(payload, {21}, assertion_id="API-A13", case_id="MER-API-013")


@wave1_case(
    case_id="MER-API-014",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P0",
    risk="critical",
)
def test_mer_api_014_reject_valid_paid_order(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = _seed_or_skip(
        "MER-API-014",
        wave1_config.rejectable_paid_order_id,
        "API_REJECTABLE_PAID_ORDER_ID",
        case_skip,
    )
    before_payload = _load_merchant_detail(
        case_id="MER-API-014",
        token=merchant_store_session.store_token,
        order_id=order_id,
        merchant_helper=merchant_helper,
        case_skip=case_skip,
    )
    if before_payload.get("data", {}).get("status") != 20:
        case_skip("MER-API-014", f"Precondition failed: order {order_id} is not Paid(status=20)")

    response = merchant_helper.reject_order(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(response, 200, assertion_id="API-A13", case_id="MER-API-014")
    payload = assert_success_envelope(response, assertion_id="API-A13", case_id="MER-API-014")
    assert_order_status(payload, {40, 60, 90}, assertion_id="API-A13", case_id="MER-API-014")


@wave1_case(
    case_id="MER-API-015",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P0",
    risk="critical",
)
def test_mer_api_015_mark_arrived_valid_accepted_order(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = _seed_or_skip("MER-API-015", wave1_config.accepted_order_id, "API_ACCEPTED_ORDER_ID", case_skip)
    before_payload = _load_merchant_detail(
        case_id="MER-API-015",
        token=merchant_store_session.store_token,
        order_id=order_id,
        merchant_helper=merchant_helper,
        case_skip=case_skip,
    )
    if before_payload.get("data", {}).get("status") != 21:
        case_skip("MER-API-015", f"Precondition failed: order {order_id} is not Accepted(status=21)")

    response = merchant_helper.mark_arrived(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(response, 200, assertion_id="API-A13", case_id="MER-API-015")
    payload = assert_success_envelope(response, assertion_id="API-A13", case_id="MER-API-015")
    assert_order_status(payload, {22}, assertion_id="API-A13", case_id="MER-API-015")


@wave1_case(
    case_id="MER-API-016",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P0",
    risk="critical",
)
def test_mer_api_016_complete_valid_arrived_order(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = _seed_or_skip("MER-API-016", wave1_config.arrived_order_id, "API_ARRIVED_ORDER_ID", case_skip)
    before_payload = _load_merchant_detail(
        case_id="MER-API-016",
        token=merchant_store_session.store_token,
        order_id=order_id,
        merchant_helper=merchant_helper,
        case_skip=case_skip,
    )
    if before_payload.get("data", {}).get("status") != 22:
        case_skip("MER-API-016", f"Precondition failed: order {order_id} is not Arrived(status=22)")

    response = merchant_helper.complete_order(
        token=merchant_store_session.store_token,
        order_id=order_id,
        pay_at_store_collected_amount=1.0,
    )
    assert_status(response, 200, assertion_id="API-A13", case_id="MER-API-016")
    payload = assert_success_envelope(response, assertion_id="API-A13", case_id="MER-API-016")
    assert_order_status(payload, {23, 24}, assertion_id="API-A13", case_id="MER-API-016")


@wave1_case(
    case_id="MER-API-017",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P1",
    risk="high",
)
def test_mer_api_017_cancel_valid_order(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = _seed_or_skip(
        "MER-API-017",
        wave1_config.merchant_cancellable_order_id or wave1_config.pending_order_id,
        "API_MERCHANT_CANCELLABLE_ORDER_ID/API_PENDING_ORDER_ID",
        case_skip,
    )
    response = merchant_helper.cancel_order(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(response, 200, assertion_id="API-A13", case_id="MER-API-017")
    payload = assert_success_envelope(response, assertion_id="API-A13", case_id="MER-API-017")
    assert_order_status(payload, {60, 90}, assertion_id="API-A13", case_id="MER-API-017")


@wave1_case(
    case_id="MER-API-018",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P1",
    risk="medium",
)
def test_mer_api_018_mark_no_show_valid_or_controlled(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = _seed_or_skip(
        "MER-API-018",
        wave1_config.no_show_order_id or wave1_config.arrived_order_id,
        "API_NO_SHOW_ORDER_ID/API_ARRIVED_ORDER_ID",
        case_skip,
    )
    response = merchant_helper.mark_no_show(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(response, {200, 400}, assertion_id="API-A13", case_id="MER-API-018")
    if response.status_code == 200:
        payload = assert_success_envelope(response, assertion_id="API-A13", case_id="MER-API-018")
        assert_order_status(payload, {91, 60, 90}, assertion_id="API-A13", case_id="MER-API-018")


@wave1_case(
    case_id="MER-API-019",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P0",
    risk="high",
)
def test_mer_api_019_accept_invalid_state_rejected(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = _seed_or_skip(
        "MER-API-019",
        wave1_config.non_paid_order_id or wave1_config.cancelled_order_id or wave1_config.completed_order_id,
        "API_NON_PAID_ORDER_ID/API_CANCELLED_ORDER_ID/API_COMPLETED_ORDER_ID",
        case_skip,
    )
    response = merchant_helper.accept_order(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(response, 400, assertion_id="API-A13", case_id="MER-API-019")


@wave1_case(
    case_id="MER-API-020",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P0",
    risk="high",
)
def test_mer_api_020_reject_invalid_state_rejected(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = _seed_or_skip(
        "MER-API-020",
        wave1_config.accepted_order_id or wave1_config.completed_order_id or wave1_config.cancelled_order_id,
        "API_ACCEPTED_ORDER_ID/API_COMPLETED_ORDER_ID/API_CANCELLED_ORDER_ID",
        case_skip,
    )
    response = merchant_helper.reject_order(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(response, 400, assertion_id="API-A13", case_id="MER-API-020")


@wave1_case(
    case_id="MER-API-021",
    assertion_ids=["API-A13"],
    domain="merchant",
    priority="P1",
    risk="high",
)
def test_mer_api_021_stale_double_action_safety(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    order_id = _seed_or_skip(
        "MER-API-021",
        wave1_config.stale_transition_order_id or wave1_config.completed_order_id or wave1_config.cancelled_order_id,
        "API_STALE_TRANSITION_ORDER_ID/API_COMPLETED_ORDER_ID/API_CANCELLED_ORDER_ID",
        case_skip,
    )
    arrived_response = merchant_helper.mark_arrived(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(arrived_response, 400, assertion_id="API-A13", case_id="MER-API-021")

    complete_response = merchant_helper.complete_order(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(complete_response, 400, assertion_id="API-A13", case_id="MER-API-021")


@wave1_case(
    case_id="MER-API-022",
    assertion_ids=["XSURF-C02"],
    domain="merchant",
    priority="P1",
    risk="medium",
)
def test_mer_api_022_queue_detail_consistency_for_seeded_order(
    wave1_config,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    target_order_id = _seed_or_skip(
        "MER-API-022",
        wave1_config.consistency_order_id or wave1_config.paid_order_id,
        "API_CONSISTENCY_ORDER_ID/API_PAID_ORDER_ID",
        case_skip,
    )

    list_response = merchant_helper.list_orders(
        token=merchant_store_session.store_token,
        store_id=merchant_store_session.store_id,
    )
    assert_status(list_response, 200, assertion_id="XSURF-C02", case_id="MER-API-022")
    list_payload = assert_success_envelope(list_response, assertion_id="XSURF-C02", case_id="MER-API-022")
    rows = _extract_rows(list_payload)
    in_queue = any(row.get("id") == target_order_id for row in rows)
    if not in_queue:
        case_skip("MER-API-022", f"Target order {target_order_id} not present in current merchant queue page")

    detail_response = merchant_helper.get_order_detail(
        token=merchant_store_session.store_token,
        order_id=target_order_id,
    )
    assert_status(detail_response, 200, assertion_id="XSURF-C02", case_id="MER-API-022")
    detail_payload = assert_success_envelope(detail_response, assertion_id="XSURF-C02", case_id="MER-API-022")
    detail_data = envelope_data(detail_payload)
    assert isinstance(detail_data, Mapping), (
        f"[MER-API-022/XSURF-C02] Expected merchant detail mapping payload, got {type(detail_data).__name__}"
    )
