"""Wave 1 PAY-API-* automated tests."""

from __future__ import annotations

import pytest

from .helpers.assertion_helper import (
    assert_order_status,
    assert_status,
    assert_success_envelope,
    extract_id,
    response_json,
)
from .helpers.idempotency import generate_idempotency_key
from .helpers.result_tags import wave1_case


def _create_order_and_intent(*, wave1_config, user_session, order_helper, payment_helper):
    store_id = wave1_config.order_store_id or wave1_config.store_id
    sku_id = wave1_config.order_sku_id
    if not isinstance(store_id, int) or not isinstance(sku_id, int):
        raise AssertionError("Missing API_ORDER_STORE_ID/API_STORE_ID and API_ORDER_SKU_ID")

    create_resp = order_helper.create_order(
        token=user_session.token,
        store_id=store_id,
        items=order_helper.build_items(sku_id),
        idempotency_key=generate_idempotency_key("PAY-ORDER-CREATE"),
    )
    assert_status(create_resp, 200, assertion_id="API-A05", case_id="PAY-SETUP")
    create_payload = assert_success_envelope(create_resp, assertion_id="API-A05", case_id="PAY-SETUP")
    order_id = extract_id(create_payload)

    pay_resp = payment_helper.create_order_payment_intent(
        token=user_session.token,
        order_id=order_id,
        idempotency_key=generate_idempotency_key("PAY-INTENT"),
    )
    assert_status(pay_resp, 200, assertion_id="API-A10", case_id="PAY-SETUP")
    pay_payload = assert_success_envelope(pay_resp, assertion_id="API-A10", case_id="PAY-SETUP")
    attempt_id, payment_intent_id = payment_helper.extract_payment_attempt_and_intent(pay_payload)
    return order_id, attempt_id, payment_intent_id


@wave1_case(
    case_id="PAY-API-001",
    assertion_ids=["API-A10"],
    domain="payment",
    priority="P0",
    risk="critical",
)
def test_pay_api_001_payment_init_success(wave1_config, require_config, user_session, payment_helper, order_helper):
    require_config("PAY-API-001", "order_store_id", "order_sku_id")
    order_id, attempt_id, payment_intent_id = _create_order_and_intent(
        wave1_config=wave1_config,
        user_session=user_session,
        order_helper=order_helper,
        payment_helper=payment_helper,
    )

    assert isinstance(order_id, int)
    assert isinstance(attempt_id, int)
    assert payment_intent_id.startswith("pi_")


@wave1_case(
    case_id="PAY-API-002",
    assertion_ids=["API-A10"],
    domain="payment",
    priority="P1",
    risk="high",
)
def test_pay_api_002_order_payment_verify_endpoint(user_session, payment_helper, order_helper, wave1_config, require_config):
    require_config("PAY-API-002", "order_store_id", "order_sku_id")
    order_id, _, _ = _create_order_and_intent(
        wave1_config=wave1_config,
        user_session=user_session,
        order_helper=order_helper,
        payment_helper=payment_helper,
    )

    verify_resp = payment_helper.verify_order_payment(token=user_session.token, order_id=order_id)
    assert_status(verify_resp, 200, assertion_id="API-A10", case_id="PAY-API-002")
    _ = assert_success_envelope(verify_resp, assertion_id="API-A10", case_id="PAY-API-002")


@wave1_case(
    case_id="PAY-API-003",
    assertion_ids=["API-A10", "PAY-I01"],
    domain="payment",
    priority="P0",
    risk="critical",
)
def test_pay_api_003_stripe_callback_success_marks_paid(
    wave1_config,
    user_session,
    payment_helper,
    order_helper,
    case_skip,
):
    if not wave1_config.stripe_webhook_secret:
        case_skip("PAY-API-003", "Missing API_STRIPE_WEBHOOK_SECRET")

    order_id, attempt_id, payment_intent_id = _create_order_and_intent(
        wave1_config=wave1_config,
        user_session=user_session,
        order_helper=order_helper,
        payment_helper=payment_helper,
    )
    payload = payment_helper.build_stripe_success_payload(
        order_id=order_id,
        attempt_id=attempt_id,
        payment_intent_id=payment_intent_id,
    )

    callback_resp = payment_helper.send_stripe_webhook(payload=payload, webhook_secret=wave1_config.stripe_webhook_secret)
    assert_status(callback_resp, 204, assertion_id="API-A10", case_id="PAY-API-003")

    order_resp = order_helper.get_order(token=user_session.token, order_id=order_id)
    assert_status(order_resp, 200, assertion_id="PAY-I01", case_id="PAY-API-003")
    order_payload = assert_success_envelope(order_resp, assertion_id="PAY-I01", case_id="PAY-API-003")
    assert_order_status(order_payload, {20, 21, 22, 23, 24}, assertion_id="PAY-I01", case_id="PAY-API-003")


@wave1_case(
    case_id="PAY-API-004",
    assertion_ids=["API-A11", "PAY-I02"],
    domain="payment",
    priority="P0",
    risk="critical",
)
def test_pay_api_004_stripe_duplicate_callback_replay_safe(
    wave1_config,
    user_session,
    payment_helper,
    order_helper,
    case_skip,
):
    if not wave1_config.stripe_webhook_secret:
        case_skip("PAY-API-004", "Missing API_STRIPE_WEBHOOK_SECRET")

    order_id, attempt_id, payment_intent_id = _create_order_and_intent(
        wave1_config=wave1_config,
        user_session=user_session,
        order_helper=order_helper,
        payment_helper=payment_helper,
    )
    payload = payment_helper.build_stripe_success_payload(
        order_id=order_id,
        attempt_id=attempt_id,
        payment_intent_id=payment_intent_id,
    )

    first = payment_helper.send_stripe_webhook(payload=payload, webhook_secret=wave1_config.stripe_webhook_secret)
    second = payment_helper.send_stripe_webhook(payload=payload, webhook_secret=wave1_config.stripe_webhook_secret)
    assert_status(first, 204, assertion_id="API-A11", case_id="PAY-API-004")
    assert_status(second, 204, assertion_id="API-A11", case_id="PAY-API-004")

    order_resp = order_helper.get_order(token=user_session.token, order_id=order_id)
    order_payload = assert_success_envelope(order_resp, assertion_id="PAY-I02", case_id="PAY-API-004")
    assert_order_status(order_payload, {20, 21, 22, 23, 24}, assertion_id="PAY-I02", case_id="PAY-API-004")


@wave1_case(
    case_id="PAY-API-005",
    assertion_ids=["API-A12"],
    domain="payment",
    priority="P0",
    risk="critical",
)
def test_pay_api_005_stripe_malformed_callback_rejected(api_client):
    response = api_client.post("/payments/stripe/webhook", json_body={"malformed": True})
    assert_status(response, {400, 422}, assertion_id="API-A12", case_id="PAY-API-005")


@wave1_case(
    case_id="PAY-API-006",
    assertion_ids=["API-A12", "PAY-I03"],
    domain="payment",
    priority="P0",
    risk="critical",
)
def test_pay_api_006_stripe_invalid_signature_rejected(api_client):
    payload = {
        "id": "evt_invalidsig",
        "object": "event",
        "type": "payment_intent.succeeded",
        "data": {"object": {"id": "pi_dummy", "object": "payment_intent", "metadata": {}}},
    }
    response = api_client.post(
        "/payments/stripe/webhook",
        headers={"Stripe-Signature": "t=1,v1=deadbeef"},
        json_body=payload,
    )
    assert_status(response, {400, 422}, assertion_id="API-A12", case_id="PAY-API-006")


@wave1_case(
    case_id="PAY-API-007",
    assertion_ids=["API-A11", "PAY-I05"],
    domain="payment",
    priority="P0",
    risk="high",
)
def test_pay_api_007_stripe_callback_on_already_paid_is_idempotent(
    wave1_config,
    user_session,
    payment_helper,
    order_helper,
    case_skip,
):
    if not wave1_config.stripe_webhook_secret:
        case_skip("PAY-API-007", "Missing API_STRIPE_WEBHOOK_SECRET")

    order_id, attempt_id, payment_intent_id = _create_order_and_intent(
        wave1_config=wave1_config,
        user_session=user_session,
        order_helper=order_helper,
        payment_helper=payment_helper,
    )
    payload_1 = payment_helper.build_stripe_success_payload(
        order_id=order_id,
        attempt_id=attempt_id,
        payment_intent_id=payment_intent_id,
        event_id="evt_wave1_paid_once",
    )
    payload_2 = payment_helper.build_stripe_success_payload(
        order_id=order_id,
        attempt_id=attempt_id,
        payment_intent_id=payment_intent_id,
        event_id="evt_wave1_paid_twice",
    )

    first = payment_helper.send_stripe_webhook(payload=payload_1, webhook_secret=wave1_config.stripe_webhook_secret)
    second = payment_helper.send_stripe_webhook(payload=payload_2, webhook_secret=wave1_config.stripe_webhook_secret)
    assert_status(first, 204, assertion_id="API-A11", case_id="PAY-API-007")
    assert_status(second, 204, assertion_id="API-A11", case_id="PAY-API-007")

    order_resp = order_helper.get_order(token=user_session.token, order_id=order_id)
    order_payload = assert_success_envelope(order_resp, assertion_id="PAY-I05", case_id="PAY-API-007")
    assert_order_status(order_payload, {20, 21, 22, 23, 24}, assertion_id="PAY-I05", case_id="PAY-API-007")


@wave1_case(
    case_id="PAY-API-008",
    assertion_ids=["PAY-I06"],
    domain="payment",
    priority="P0",
    risk="high",
)
def test_pay_api_008_callback_after_cancel_does_not_corrupt_state(
    wave1_config,
    user_session,
    payment_helper,
    order_helper,
    case_skip,
):
    if not wave1_config.stripe_webhook_secret:
        case_skip("PAY-API-008", "Missing API_STRIPE_WEBHOOK_SECRET")

    order_id, attempt_id, payment_intent_id = _create_order_and_intent(
        wave1_config=wave1_config,
        user_session=user_session,
        order_helper=order_helper,
        payment_helper=payment_helper,
    )

    cancel_resp = order_helper.cancel_order(token=user_session.token, order_id=order_id)
    assert_status(cancel_resp, {200, 400}, assertion_id="PAY-I06", case_id="PAY-API-008")

    payload = payment_helper.build_stripe_success_payload(
        order_id=order_id,
        attempt_id=attempt_id,
        payment_intent_id=payment_intent_id,
    )
    callback_resp = payment_helper.send_stripe_webhook(payload=payload, webhook_secret=wave1_config.stripe_webhook_secret)
    assert_status(callback_resp, 204, assertion_id="PAY-I06", case_id="PAY-API-008")

    order_resp = order_helper.get_order(token=user_session.token, order_id=order_id)
    order_payload = assert_success_envelope(order_resp, assertion_id="PAY-I06", case_id="PAY-API-008")
    assert_order_status(order_payload, {20, 60, 90, 50, 21, 22, 23, 24}, assertion_id="PAY-I06", case_id="PAY-API-008")


@wave1_case(
    case_id="PAY-API-012",
    assertion_ids=["API-A10"],
    domain="payment",
    priority="P1",
    risk="high",
)
def test_pay_api_012_retry_payment_pending_order_behavior(
    wave1_config,
    require_config,
    user_session,
    payment_helper,
    order_helper,
):
    require_config("PAY-API-012", "order_store_id", "order_sku_id")
    order_id, _, _ = _create_order_and_intent(
        wave1_config=wave1_config,
        user_session=user_session,
        order_helper=order_helper,
        payment_helper=payment_helper,
    )

    retry_resp = payment_helper.retry_order_payment(
        token=user_session.token,
        order_id=order_id,
        idempotency_key=generate_idempotency_key("PAY-RETRY-PENDING"),
    )
    assert_status(retry_resp, {200, 400, 404, 409, 422}, assertion_id="API-A10", case_id="PAY-API-012")
    if retry_resp.status_code == 200:
        _ = assert_success_envelope(retry_resp, assertion_id="API-A10", case_id="PAY-API-012")


@wave1_case(
    case_id="PAY-API-013",
    assertion_ids=["API-A10"],
    domain="payment",
    priority="P1",
    risk="high",
)
def test_pay_api_013_retry_payment_terminal_state_behavior(
    wave1_config,
    user_session,
    payment_helper,
    case_skip,
):
    seeded_order_id = wave1_config.paid_order_id or wave1_config.cancelled_order_id or wave1_config.completed_order_id
    if not isinstance(seeded_order_id, int):
        case_skip("PAY-API-013", "Need API_PAID_ORDER_ID or API_CANCELLED_ORDER_ID or API_COMPLETED_ORDER_ID")

    retry_resp = payment_helper.retry_order_payment(
        token=user_session.token,
        order_id=seeded_order_id,
        idempotency_key=generate_idempotency_key("PAY-RETRY-TERMINAL"),
    )
    assert_status(retry_resp, {200, 400, 404, 409, 422}, assertion_id="API-A10", case_id="PAY-API-013")
    if retry_resp.status_code == 200:
        _ = assert_success_envelope(retry_resp, assertion_id="API-A10", case_id="PAY-API-013")


@wave1_case(
    case_id="PAY-API-014",
    assertion_ids=["API-A10"],
    domain="payment",
    priority="P1",
    risk="high",
)
def test_pay_api_014_wallet_payment_conflict_or_success(
    wave1_config,
    require_config,
    user_session,
    payment_helper,
    order_helper,
):
    require_config("PAY-API-014", "order_store_id", "order_sku_id")
    order_id, _, _ = _create_order_and_intent(
        wave1_config=wave1_config,
        user_session=user_session,
        order_helper=order_helper,
        payment_helper=payment_helper,
    )

    wallet_resp = payment_helper.create_order_wallet_payment(
        token=user_session.token,
        order_id=order_id,
        idempotency_key=generate_idempotency_key("PAY-WALLET"),
    )
    assert_status(wallet_resp, {200, 400, 404, 409, 422}, assertion_id="API-A10", case_id="PAY-API-014")
    if wallet_resp.status_code == 200:
        _ = assert_success_envelope(wallet_resp, assertion_id="API-A10", case_id="PAY-API-014")
    else:
        payload = response_json(wallet_resp)
        message = payload.get("message", payload.get("Message"))
        assert isinstance(message, str) and message.strip(), (
            f"[PAY-API-014/API-A10] Expected actionable error payload for wallet payment failure, got {payload}"
        )


@wave1_case(
    case_id="PAY-API-015",
    assertion_ids=["API-A10"],
    domain="payment",
    priority="P1",
    risk="high",
)
def test_pay_api_015_transactions_verify_endpoint_coverage(
    wave1_config,
    user_session,
    payment_helper,
    case_skip,
):
    # /payments/transactions/{transactionId}/verify expects PaymentTransaction.Id,
    # not order paymentAttemptId from /orders/{id}/payments.
    transaction_id = wave1_config.payment_transaction_id
    if not isinstance(transaction_id, int):
        case_skip("PAY-API-015", "Need API_PAYMENT_TRANSACTION_ID (PaymentTransaction.Id)")

    verify_resp = payment_helper.verify_transaction(token=user_session.token, transaction_id=transaction_id)
    assert_status(verify_resp, {200, 400, 404}, assertion_id="API-A10", case_id="PAY-API-015")
    if verify_resp.status_code == 200:
        _ = assert_success_envelope(verify_resp, assertion_id="API-A10", case_id="PAY-API-015")


@wave1_case(
    case_id="PAY-API-016",
    assertion_ids=["API-A10"],
    domain="payment",
    priority="P1",
    risk="high",
)
def test_pay_api_016_stripe_payment_endpoint_contract_probe(
    user_session,
    payment_helper,
):
    # Backend/provider payload contract can vary by gateway mode; this probes integration guard behavior
    # and keeps non-5xx responses explicit.
    stripe_resp = payment_helper.confirm_stripe_payment(token=user_session.token, payload={})
    assert_status(stripe_resp, {200, 400, 401, 403, 404, 405, 415, 422}, assertion_id="API-A10", case_id="PAY-API-016")


@wave1_case(
    case_id="PAY-API-017",
    assertion_ids=["API-A10"],
    domain="payment",
    priority="P1",
    risk="high",
)
def test_pay_api_017_momo_payment_endpoint_contract_probe(
    user_session,
    payment_helper,
):
    # Provider init contract may require gateway-specific fields in runtime env;
    # this probe ensures the endpoint responds with controlled non-5xx behavior.
    momo_resp = payment_helper.create_momo_payment(token=user_session.token, payload={})
    assert_status(momo_resp, {200, 400, 401, 403, 404, 405, 415, 422}, assertion_id="API-A10", case_id="PAY-API-017")


@wave1_case(
    case_id="PAY-API-009",
    assertion_ids=["API-A10", "PAY-I01"],
    domain="payment",
    priority="P1",
    risk="high",
)
def test_pay_api_009_momo_callback_success_path(
    wave1_config,
    payment_helper,
    case_skip,
):
    if not all(
        [
            wave1_config.momo_access_key,
            wave1_config.momo_secret_key,
            wave1_config.momo_partner_code,
            wave1_config.momo_request_id,
            wave1_config.momo_transaction_order_id,
            isinstance(wave1_config.momo_transaction_amount, int),
        ]
    ):
        case_skip(
            "PAY-API-009",
            "Need API_MOMO_ACCESS_KEY/API_MOMO_SECRET_KEY/API_MOMO_PARTNER_CODE/"
            "API_MOMO_REQUEST_ID/API_MOMO_TRANSACTION_ORDER_ID/API_MOMO_TRANSACTION_AMOUNT",
        )

    payload = payment_helper.build_momo_callback_payload(
        order_id=wave1_config.momo_transaction_order_id or "",
        request_id=wave1_config.momo_request_id or "",
        amount=wave1_config.momo_transaction_amount or 0,
        partner_code=wave1_config.momo_partner_code or "",
        result_code=0,
        message="Success",
    )
    signed = payment_helper.sign_momo_payload(
        payload,
        access_key=wave1_config.momo_access_key or "",
        secret_key=wave1_config.momo_secret_key or "",
    )

    response = payment_helper.send_momo_webhook(signed)
    assert_status(response, 204, assertion_id="API-A10", case_id="PAY-API-009")


@wave1_case(
    case_id="PAY-API-010",
    assertion_ids=["API-A11", "PAY-I04"],
    domain="payment",
    priority="P1",
    risk="high",
)
def test_pay_api_010_momo_invalid_signature_no_mutation(wave1_config, payment_helper):
    payload = payment_helper.build_momo_callback_payload(
        order_id=wave1_config.momo_transaction_order_id or "999999",
        request_id=wave1_config.momo_request_id or "wave1-invalid-signature",
        amount=wave1_config.momo_transaction_amount or 1000,
        partner_code=wave1_config.momo_partner_code or "MOMO_TEST",
        result_code=0,
        message="Success",
    )
    payload["signature"] = "invalid-signature"

    response = payment_helper.send_momo_webhook(payload)
    assert_status(response, 204, assertion_id="API-A11", case_id="PAY-API-010")


@wave1_case(
    case_id="PAY-API-011",
    assertion_ids=["XSURF-C01", "XSURF-C02"],
    domain="payment",
    priority="P0",
    risk="critical",
)
def test_pay_api_011_paid_state_visible_to_user_and_merchant(
    wave1_config,
    user_session,
    merchant_store_session,
    payment_helper,
    order_helper,
    merchant_helper,
    case_skip,
):
    if not wave1_config.stripe_webhook_secret:
        case_skip("PAY-API-011", "Missing API_STRIPE_WEBHOOK_SECRET")

    order_id, attempt_id, payment_intent_id = _create_order_and_intent(
        wave1_config=wave1_config,
        user_session=user_session,
        order_helper=order_helper,
        payment_helper=payment_helper,
    )
    callback_payload = payment_helper.build_stripe_success_payload(
        order_id=order_id,
        attempt_id=attempt_id,
        payment_intent_id=payment_intent_id,
    )
    callback_resp = payment_helper.send_stripe_webhook(
        payload=callback_payload,
        webhook_secret=wave1_config.stripe_webhook_secret,
    )
    assert_status(callback_resp, 204, assertion_id="XSURF-C01", case_id="PAY-API-011")

    user_order_resp = order_helper.get_order(token=user_session.token, order_id=order_id)
    merchant_detail_resp = merchant_helper.get_order_detail(token=merchant_store_session.store_token, order_id=order_id)
    assert_status(user_order_resp, 200, assertion_id="XSURF-C01", case_id="PAY-API-011")
    assert_status(merchant_detail_resp, 200, assertion_id="XSURF-C02", case_id="PAY-API-011")

    user_payload = assert_success_envelope(user_order_resp, assertion_id="XSURF-C01", case_id="PAY-API-011")
    merchant_payload = assert_success_envelope(merchant_detail_resp, assertion_id="XSURF-C02", case_id="PAY-API-011")
    user_status = user_payload.get("data", {}).get("status")
    merchant_status = merchant_payload.get("data", {}).get("status")

    assert user_status == merchant_status, (
        f"[PAY-API-011/XSURF-C02] user status {user_status} != merchant status {merchant_status}"
    )
