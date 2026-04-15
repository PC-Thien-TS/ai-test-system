"""Wave 1 ORD-API-* automated tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from .helpers.assertion_helper import (
    assert_same_order_id,
    assert_status,
    assert_success_envelope,
    assert_order_status,
    extract_id,
    response_json,
)
from .helpers.idempotency import generate_idempotency_key
from .helpers.result_tags import wave1_case


def _default_store_id(cfg) -> int:
    store_id = cfg.order_store_id or cfg.store_id
    if not isinstance(store_id, int):
        raise AssertionError("Missing integer order/store id in configuration")
    return store_id


def _default_sku_id(cfg) -> int:
    if not isinstance(cfg.order_sku_id, int):
        raise AssertionError("Missing integer API_ORDER_SKU_ID in configuration")
    return cfg.order_sku_id


@wave1_case(
    case_id="ORD-API-001",
    assertion_ids=["API-A05"],
    domain="order",
    priority="P0",
    risk="high",
)
def test_ord_api_001_pricing_preview_success(wave1_config, require_config, user_session, order_helper):
    require_config("ORD-API-001", "order_store_id", "order_sku_id")
    store_id = _default_store_id(wave1_config)
    sku_id = _default_sku_id(wave1_config)

    resp = order_helper.preview_pricing(
        token=user_session.token,
        store_id=store_id,
        items=order_helper.build_items(sku_id, quantity=1),
        order_type=20,
    )

    assert_status(resp, 200, assertion_id="API-A05", case_id="ORD-API-001")
    payload = assert_success_envelope(resp, assertion_id="API-A05", case_id="ORD-API-001")
    data = payload.get("data", {})
    assert isinstance(data.get("totalAmount"), (int, float))
    assert isinstance(data.get("totalDueNowAmount"), (int, float))


@wave1_case(
    case_id="ORD-API-002",
    assertion_ids=["API-A05"],
    domain="order",
    priority="P0",
    risk="critical",
)
def test_ord_api_002_create_order_success(wave1_config, require_config, user_session, order_helper):
    require_config("ORD-API-002", "order_store_id", "order_sku_id")
    store_id = _default_store_id(wave1_config)
    sku_id = _default_sku_id(wave1_config)

    idempotency_key = generate_idempotency_key("ORD-API-002")
    resp = order_helper.create_order(
        token=user_session.token,
        store_id=store_id,
        items=order_helper.build_items(sku_id, quantity=1),
        idempotency_key=idempotency_key,
    )

    assert_status(resp, 200, assertion_id="API-A05", case_id="ORD-API-002")
    payload = assert_success_envelope(resp, assertion_id="API-A05", case_id="ORD-API-002")
    assert_order_status(payload, {10}, assertion_id="API-A05", case_id="ORD-API-002")


@wave1_case(
    case_id="ORD-API-003",
    assertion_ids=["API-A04"],
    domain="order",
    priority="P0",
    risk="critical",
)
def test_ord_api_003_missing_idempotency_key_rejected(wave1_config, require_config, user_session, order_helper):
    require_config("ORD-API-003", "order_store_id", "order_sku_id")
    store_id = _default_store_id(wave1_config)
    sku_id = _default_sku_id(wave1_config)

    resp = order_helper.create_order_without_idempotency(
        token=user_session.token,
        store_id=store_id,
        items=order_helper.build_items(sku_id, quantity=1),
    )

    assert_status(resp, 400, assertion_id="API-A04", case_id="ORD-API-003")


@wave1_case(
    case_id="ORD-API-004",
    assertion_ids=["API-A06"],
    domain="order",
    priority="P0",
    risk="high",
)
def test_ord_api_004_invalid_payload_empty_items_rejected(wave1_config, require_config, user_session, order_helper):
    require_config("ORD-API-004", "order_store_id")
    store_id = _default_store_id(wave1_config)

    resp = order_helper.create_order(
        token=user_session.token,
        store_id=store_id,
        items=[],
        idempotency_key=generate_idempotency_key("ORD-API-004"),
    )

    assert_status(resp, 400, assertion_id="API-A06", case_id="ORD-API-004")


@wave1_case(
    case_id="ORD-API-005",
    assertion_ids=["API-A06"],
    domain="order",
    priority="P0",
    risk="high",
)
def test_ord_api_005_unavailable_sku_rejected_or_controlled(
    wave1_config,
    user_session,
    order_helper,
    case_skip,
):
    sku_id = wave1_config.disabled_sku_id or wave1_config.out_of_stock_sku_id
    store_id = wave1_config.order_store_id or wave1_config.store_id
    if not isinstance(store_id, int) or not isinstance(sku_id, int):
        case_skip("ORD-API-005", "Need API_ORDER_STORE_ID and API_DISABLED_SKU_ID/API_OUT_OF_STOCK_SKU_ID")

    resp = order_helper.create_order(
        token=user_session.token,
        store_id=store_id,
        items=order_helper.build_items(sku_id, quantity=1),
        idempotency_key=generate_idempotency_key("ORD-API-005"),
    )

    assert resp.status_code in {400, 404, 409}, (
        f"[ORD-API-005/API-A06] Expected unavailable SKU rejection, got {resp.status_code} {resp.text[:800]}"
    )


@wave1_case(
    case_id="ORD-API-006",
    assertion_ids=["API-A07"],
    domain="idempotency",
    priority="P0",
    risk="critical",
)
def test_ord_api_006_same_idempotency_key_replays_same_order(wave1_config, require_config, user_session, order_helper):
    require_config("ORD-API-006", "order_store_id", "order_sku_id")
    store_id = _default_store_id(wave1_config)
    sku_id = _default_sku_id(wave1_config)

    key = generate_idempotency_key("ORD-API-006")
    body_items = order_helper.build_items(sku_id, quantity=1)

    first = order_helper.create_order(
        token=user_session.token,
        store_id=store_id,
        items=body_items,
        idempotency_key=key,
    )
    second = order_helper.create_order(
        token=user_session.token,
        store_id=store_id,
        items=body_items,
        idempotency_key=key,
    )

    assert_status(first, 200, assertion_id="API-A07", case_id="ORD-API-006")
    assert_status(second, 200, assertion_id="API-A07", case_id="ORD-API-006")

    first_payload = assert_success_envelope(first, assertion_id="API-A07", case_id="ORD-API-006")
    second_payload = assert_success_envelope(second, assertion_id="API-A07", case_id="ORD-API-006")
    assert_same_order_id(first_payload, second_payload, assertion_id="API-A07", case_id="ORD-API-006")


@wave1_case(
    case_id="ORD-API-007",
    assertion_ids=["API-A08"],
    domain="idempotency",
    priority="P0",
    risk="critical",
)
def test_ord_api_007_same_key_different_payload_rejected(wave1_config, require_config, user_session, order_helper):
    require_config("ORD-API-007", "order_store_id", "order_sku_id")
    store_id = _default_store_id(wave1_config)
    sku_id = _default_sku_id(wave1_config)

    key = generate_idempotency_key("ORD-API-007")
    first = order_helper.create_order(
        token=user_session.token,
        store_id=store_id,
        items=order_helper.build_items(sku_id, quantity=1),
        idempotency_key=key,
    )
    assert_status(first, 200, assertion_id="API-A08", case_id="ORD-API-007")

    second = order_helper.create_order(
        token=user_session.token,
        store_id=store_id,
        items=order_helper.build_items(sku_id, quantity=2),
        idempotency_key=key,
    )
    assert second.status_code in {400, 409}, (
        f"[ORD-API-007/API-A08] Expected replay mismatch rejection, got {second.status_code} {second.text[:900]}"
    )


@wave1_case(
    case_id="ORD-API-008",
    assertion_ids=["API-A07"],
    domain="idempotency",
    priority="P1",
    risk="high",
)
def test_ord_api_008_different_keys_allow_distinct_submissions(
    wave1_config,
    require_config,
    user_session,
    order_helper,
):
    require_config("ORD-API-008", "order_store_id", "order_sku_id")
    store_id = _default_store_id(wave1_config)
    sku_id = _default_sku_id(wave1_config)

    payload_items = order_helper.build_items(sku_id, quantity=1)
    first = order_helper.create_order(
        token=user_session.token,
        store_id=store_id,
        items=payload_items,
        idempotency_key=generate_idempotency_key("ORD-API-008-A"),
    )
    second = order_helper.create_order(
        token=user_session.token,
        store_id=store_id,
        items=payload_items,
        idempotency_key=generate_idempotency_key("ORD-API-008-B"),
    )

    assert_status(first, 200, assertion_id="API-A07", case_id="ORD-API-008")
    assert_status(second, 200, assertion_id="API-A07", case_id="ORD-API-008")
    first_payload = assert_success_envelope(first, assertion_id="API-A07", case_id="ORD-API-008")
    second_payload = assert_success_envelope(second, assertion_id="API-A07", case_id="ORD-API-008")

    first_id = extract_id(first_payload)
    second_id = extract_id(second_payload)
    assert first_id != second_id, (
        f"[ORD-API-008/API-A07] Expected distinct orders for different idempotency keys. "
        f"first_id={first_id}, second_id={second_id}"
    )


@wave1_case(
    case_id="ORD-API-009",
    assertion_ids=["API-A05"],
    domain="order",
    priority="P1",
    risk="high",
)
def test_ord_api_009_reservation_order_flow(wave1_config, require_config, user_session, order_helper):
    require_config("ORD-API-009", "order_store_id", "order_sku_id")
    store_id = _default_store_id(wave1_config)
    sku_id = _default_sku_id(wave1_config)

    arrival_time = (datetime.now(tz=timezone.utc) + timedelta(days=1)).isoformat()
    resp = order_helper.create_order(
        token=user_session.token,
        store_id=store_id,
        items=order_helper.build_items(sku_id, quantity=1),
        idempotency_key=generate_idempotency_key("ORD-API-009"),
        order_type=10,
        arrival_time=arrival_time,
        pax=2,
    )

    assert_status(resp, {200, 400}, assertion_id="API-A05", case_id="ORD-API-009")
    if resp.status_code == 200:
        payload = assert_success_envelope(resp, assertion_id="API-A05", case_id="ORD-API-009")
        assert_order_status(payload, {10}, assertion_id="API-A05", case_id="ORD-API-009")


@wave1_case(
    case_id="ORD-API-010",
    assertion_ids=["API-A09"],
    domain="order",
    priority="P1",
    risk="high",
)
def test_ord_api_010_retry_payment_pending_reuses_same_order(wave1_config, require_config, user_session, order_helper):
    require_config("ORD-API-010", "order_store_id", "order_sku_id")
    store_id = _default_store_id(wave1_config)
    sku_id = _default_sku_id(wave1_config)

    create_resp = order_helper.create_order(
        token=user_session.token,
        store_id=store_id,
        items=order_helper.build_items(sku_id),
        idempotency_key=generate_idempotency_key("ORD-API-010-create"),
    )
    assert_status(create_resp, 200, assertion_id="API-A09", case_id="ORD-API-010")
    create_payload = assert_success_envelope(create_resp, assertion_id="API-A09", case_id="ORD-API-010")
    source_order_id = extract_id(create_payload)

    retry_resp = order_helper.retry_payment(
        token=user_session.token,
        order_id=source_order_id,
        idempotency_key=generate_idempotency_key("ORD-API-010-retry"),
    )
    assert_status(retry_resp, 200, assertion_id="API-A09", case_id="ORD-API-010")

    retry_payload = assert_success_envelope(retry_resp, assertion_id="API-A09", case_id="ORD-API-010")
    data = retry_payload.get("data", {})
    assert data.get("sourceOrderId") == source_order_id
    assert data.get("targetOrderId") == source_order_id
    assert data.get("reusedExistingPendingOrder") is True


@wave1_case(
    case_id="ORD-API-011",
    assertion_ids=["API-A09"],
    domain="order",
    priority="P1",
    risk="high",
)
def test_ord_api_011_retry_payment_terminal_replacement(wave1_config, user_session, order_helper, case_skip):
    if not isinstance(wave1_config.cancelled_order_id, int):
        case_skip("ORD-API-011", "Need API_CANCELLED_ORDER_ID seeded for terminal retry replacement test")

    retry_resp = order_helper.retry_payment(
        token=user_session.token,
        order_id=wave1_config.cancelled_order_id,
        idempotency_key=generate_idempotency_key("ORD-API-011-retry"),
    )
    assert_status(retry_resp, 200, assertion_id="API-A09", case_id="ORD-API-011")
    payload = assert_success_envelope(retry_resp, assertion_id="API-A09", case_id="ORD-API-011")

    data = payload.get("data", {})
    assert data.get("sourceOrderId") == wave1_config.cancelled_order_id
    assert data.get("targetOrderId") != wave1_config.cancelled_order_id
    assert data.get("reusedExistingPendingOrder") is False
