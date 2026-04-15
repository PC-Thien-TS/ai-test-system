"""Wave 1 CONS-API-* automated tests."""

from __future__ import annotations

import time
from typing import Any, Mapping

import pytest

from .helpers.assertion_helper import (
    assert_access_denied,
    assert_status,
    assert_success_envelope,
    envelope_data,
    extract_id,
)
from .helpers.idempotency import generate_idempotency_key
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


def _extract_status(payload: Mapping[str, Any], *, case_id: str, assertion_id: str) -> int:
    data = envelope_data(payload)
    assert isinstance(data, Mapping), f"[{case_id}/{assertion_id}] Missing data envelope: {payload}"
    status = data.get("status")
    assert isinstance(status, int), f"[{case_id}/{assertion_id}] Missing integer status in payload: {payload}"
    return status


@pytest.fixture(scope="module")
def consistency_order_id(
    wave1_config,
    user_session,
    merchant_store_session,
    order_helper,
):
    if isinstance(wave1_config.consistency_order_id, int):
        return wave1_config.consistency_order_id

    store_id = wave1_config.order_store_id or wave1_config.store_id
    sku_id = wave1_config.order_sku_id

    if not isinstance(store_id, int) or not isinstance(sku_id, int):
        pytest.skip("Need API_CONSISTENCY_ORDER_ID or API_ORDER_STORE_ID/API_STORE_ID + API_ORDER_SKU_ID")

    if wave1_config.merchant_store_id and wave1_config.merchant_store_id != store_id:
        pytest.skip("API_ORDER_STORE_ID must align with merchant store context for cross-surface checks")

    create_response = order_helper.create_order(
        token=user_session.token,
        store_id=store_id,
        items=order_helper.build_items(sku_id, quantity=1),
        idempotency_key=generate_idempotency_key("CONS-SETUP"),
    )
    assert_status(create_response, 200, assertion_id="API-A05", case_id="CONS-SETUP")
    payload = assert_success_envelope(create_response, assertion_id="API-A05", case_id="CONS-SETUP")
    return extract_id(payload)


@wave1_case(
    case_id="CONS-API-001",
    assertion_ids=["API-A14", "XSURF-C03"],
    domain="consistency",
    priority="P0",
    risk="critical",
)
def test_cons_api_001_admin_list_contains_target_order_by_status(
    consistency_order_id,
    admin_session,
    admin_helper,
):
    detail_response = admin_helper.get_order_detail(token=admin_session.token, order_id=consistency_order_id)
    assert_status(detail_response, 200, assertion_id="API-A14", case_id="CONS-API-001")
    detail_payload = assert_success_envelope(detail_response, assertion_id="API-A14", case_id="CONS-API-001")
    expected_status = _extract_status(detail_payload, case_id="CONS-API-001", assertion_id="API-A14")

    list_response = admin_helper.list_orders(
        token=admin_session.token,
        status=expected_status,
        page_size=200,
    )
    assert_status(list_response, 200, assertion_id="API-A14", case_id="CONS-API-001")
    list_payload = assert_success_envelope(list_response, assertion_id="API-A14", case_id="CONS-API-001")
    rows = _extract_rows(list_payload)

    order_ids = set()
    for row in rows:
        row_status = row.get("status")
        if isinstance(row_status, int):
            assert row_status == expected_status, (
                f"[CONS-API-001/API-A14] Filtered status mismatch: expected={expected_status}, row={row}"
            )
        row_id = row.get("id")
        if isinstance(row_id, int):
            order_ids.add(row_id)

    assert consistency_order_id in order_ids, (
        f"[CONS-API-001/XSURF-C03] Order {consistency_order_id} missing from admin list for status={expected_status}. "
        f"visible_ids={sorted(order_ids)}"
    )


@wave1_case(
    case_id="CONS-API-002",
    assertion_ids=["API-A14"],
    domain="consistency",
    priority="P0",
    risk="critical",
)
def test_cons_api_002_admin_detail_contract_and_timeline_shape(consistency_order_id, admin_session, admin_helper):
    response = admin_helper.get_order_detail(token=admin_session.token, order_id=consistency_order_id)
    assert_status(response, 200, assertion_id="API-A14", case_id="CONS-API-002")
    payload = assert_success_envelope(response, assertion_id="API-A14", case_id="CONS-API-002")
    _ = _extract_status(payload, case_id="CONS-API-002", assertion_id="API-A14")

    data = envelope_data(payload)
    assert isinstance(data, Mapping), "[CONS-API-002/API-A14] Missing detail payload data envelope"
    timeline = data.get("timeline") or data.get("events") or data.get("statusLogs")
    if isinstance(timeline, list) and len(timeline) > 1:
        stamps: list[str] = []
        for item in timeline:
            if not isinstance(item, Mapping):
                continue
            stamp = item.get("createdDate") or item.get("createdAt") or item.get("timestamp")
            if isinstance(stamp, str):
                stamps.append(stamp)
        if len(stamps) > 1:
            assert stamps == sorted(stamps), (
                f"[CONS-API-002/API-A14] Timeline stamps are not monotonic: {stamps}"
            )


@wave1_case(
    case_id="CONS-API-003",
    assertion_ids=["XSURF-C01"],
    domain="consistency",
    priority="P0",
    risk="critical",
)
def test_cons_api_003_user_detail_returns_canonical_state(consistency_order_id, user_session, order_helper):
    response = order_helper.get_order(token=user_session.token, order_id=consistency_order_id)
    assert_status(response, 200, assertion_id="XSURF-C01", case_id="CONS-API-003")
    payload = assert_success_envelope(response, assertion_id="XSURF-C01", case_id="CONS-API-003")
    _ = _extract_status(payload, case_id="CONS-API-003", assertion_id="XSURF-C01")


@wave1_case(
    case_id="CONS-API-004",
    assertion_ids=["XSURF-C02", "XSURF-C04"],
    domain="consistency",
    priority="P0",
    risk="critical",
)
def test_cons_api_004_merchant_detail_matches_admin_status(
    consistency_order_id,
    admin_session,
    admin_helper,
    merchant_store_session,
    merchant_helper,
    case_skip,
):
    admin_detail_response = admin_helper.get_order_detail(token=admin_session.token, order_id=consistency_order_id)
    assert_status(admin_detail_response, 200, assertion_id="XSURF-C04", case_id="CONS-API-004")
    admin_payload = assert_success_envelope(
        admin_detail_response,
        assertion_id="XSURF-C04",
        case_id="CONS-API-004",
    )
    admin_status = _extract_status(admin_payload, case_id="CONS-API-004", assertion_id="XSURF-C04")

    merchant_detail_response = merchant_helper.get_order_detail(
        token=merchant_store_session.store_token,
        order_id=consistency_order_id,
    )
    if merchant_detail_response.status_code in {400, 403, 404}:
        case_skip(
            "CONS-API-004",
            f"Merchant cannot access order {consistency_order_id}; check user-store-merchant mapping in fixtures",
        )
    assert_status(merchant_detail_response, 200, assertion_id="XSURF-C02", case_id="CONS-API-004")
    merchant_payload = assert_success_envelope(
        merchant_detail_response,
        assertion_id="XSURF-C02",
        case_id="CONS-API-004",
    )
    merchant_status = _extract_status(merchant_payload, case_id="CONS-API-004", assertion_id="XSURF-C02")
    assert merchant_status == admin_status, (
        f"[CONS-API-004/XSURF-C04] admin status={admin_status} merchant status={merchant_status}"
    )


@wave1_case(
    case_id="CONS-API-005",
    assertion_ids=["API-A03"],
    domain="permission",
    priority="P0",
    risk="high",
)
def test_cons_api_005_non_admin_cannot_access_admin_detail(consistency_order_id, user_session, admin_helper):
    response = admin_helper.get_order_detail(token=user_session.token, order_id=consistency_order_id)
    assert_access_denied(response, assertion_id="API-A03", case_id="CONS-API-005")


@wave1_case(
    case_id="CONS-API-006",
    assertion_ids=["API-A14"],
    domain="consistency",
    priority="P1",
    risk="high",
)
def test_cons_api_006_admin_status_filter_correctness(admin_session, admin_helper):
    for status in (10, 20, 30, 50):
        response = admin_helper.list_orders(token=admin_session.token, status=status, page_size=200)
        assert_status(response, 200, assertion_id="API-A14", case_id="CONS-API-006")
        payload = assert_success_envelope(response, assertion_id="API-A14", case_id="CONS-API-006")
        rows = _extract_rows(payload)
        for row in rows:
            row_status = row.get("status")
            if isinstance(row_status, int):
                assert row_status == status, (
                    f"[CONS-API-006/API-A14] Filter mismatch for status={status}: row={row}"
                )


@wave1_case(
    case_id="CONS-API-007",
    assertion_ids=["XSURF-C06"],
    domain="consistency",
    priority="P0",
    risk="high",
)
def test_cons_api_007_eventual_convergence_user_merchant_admin(
    consistency_order_id,
    user_session,
    merchant_store_session,
    admin_session,
    order_helper,
    merchant_helper,
    admin_helper,
    case_skip,
):
    last = {}
    for _ in range(6):
        user_response = order_helper.get_order(token=user_session.token, order_id=consistency_order_id)
        admin_response = admin_helper.get_order_detail(token=admin_session.token, order_id=consistency_order_id)
        merchant_response = merchant_helper.get_order_detail(
            token=merchant_store_session.store_token,
            order_id=consistency_order_id,
        )

        if merchant_response.status_code in {400, 403, 404}:
            case_skip(
                "CONS-API-007",
                f"Merchant cannot access order {consistency_order_id}; check fixture ownership/store mapping",
            )

        assert_status(user_response, 200, assertion_id="XSURF-C06", case_id="CONS-API-007")
        assert_status(admin_response, 200, assertion_id="XSURF-C06", case_id="CONS-API-007")
        assert_status(merchant_response, 200, assertion_id="XSURF-C06", case_id="CONS-API-007")

        user_payload = assert_success_envelope(user_response, assertion_id="XSURF-C06", case_id="CONS-API-007")
        admin_payload = assert_success_envelope(admin_response, assertion_id="XSURF-C06", case_id="CONS-API-007")
        merchant_payload = assert_success_envelope(merchant_response, assertion_id="XSURF-C06", case_id="CONS-API-007")

        user_status = _extract_status(user_payload, case_id="CONS-API-007", assertion_id="XSURF-C06")
        admin_status = _extract_status(admin_payload, case_id="CONS-API-007", assertion_id="XSURF-C06")
        merchant_status = _extract_status(merchant_payload, case_id="CONS-API-007", assertion_id="XSURF-C06")

        last = {"user": user_status, "admin": admin_status, "merchant": merchant_status}
        if len({user_status, admin_status, merchant_status}) == 1:
            return
        time.sleep(1.0)

    raise AssertionError(f"[CONS-API-007/XSURF-C06] No convergence after retries: {last}")
