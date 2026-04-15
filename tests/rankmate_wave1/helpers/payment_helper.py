"""Payment helpers for Wave 1 API tests."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from .api_client import RankmateApiClient
from .webhook_signer import (
    build_momo_signature,
    build_stripe_payment_succeeded_event,
    build_stripe_signature,
    normalize_json_payload,
)


class PaymentHelper:
    def __init__(self, client: RankmateApiClient):
        self.client = client

    def create_order_payment_intent(self, *, token: str, order_id: int, idempotency_key: str):
        return self.client.post(
            f"/orders/{order_id}/payments",
            token=token,
            idempotency_key=idempotency_key,
        )

    def create_order_wallet_payment(self, *, token: str, order_id: int, idempotency_key: str):
        return self.client.post(
            f"/orders/{order_id}/payments/wallet",
            token=token,
            idempotency_key=idempotency_key,
        )

    def retry_order_payment(self, *, token: str, order_id: int, idempotency_key: str):
        return self.client.post(
            f"/orders/{order_id}/retry-payment",
            token=token,
            idempotency_key=idempotency_key,
        )

    def create_stripe_payment_intent_raw(self, *, token: str, payload: dict[str, Any]):
        return self.client.post(
            "/stripe-payment/create-payment-intent",
            token=token,
            json_body=payload,
        )

    def confirm_stripe_payment(self, *, token: str, payload: dict[str, Any]):
        return self.client.post(
            "/payments/stripe",
            token=token,
            json_body=payload,
        )

    def create_momo_payment(self, *, token: str, payload: dict[str, Any]):
        return self.client.post(
            "/payments/momo",
            token=token,
            json_body=payload,
        )

    def verify_transaction(self, *, token: str, transaction_id: int):
        return self.client.get(f"/payments/transactions/{transaction_id}/verify", token=token)

    def verify_order_payment(self, *, token: str, order_id: int):
        return self.client.get(f"/orders/{order_id}/payments/verify", token=token)

    def extract_payment_attempt_and_intent(self, payment_payload: dict[str, Any]) -> tuple[int, str]:
        data = payment_payload.get("data") if "data" in payment_payload else payment_payload.get("Data")
        if not isinstance(data, dict):
            raise AssertionError(f"Invalid payment payload envelope: {payment_payload}")

        attempt_id = data.get("paymentAttemptId")
        client_secret = data.get("stripeClientSecret")
        if not isinstance(attempt_id, int):
            raise AssertionError(f"Missing paymentAttemptId in payload: {payment_payload}")
        if not isinstance(client_secret, str) or "_secret" not in client_secret:
            raise AssertionError(f"Missing stripeClientSecret in payload: {payment_payload}")

        intent_id = client_secret.split("_secret", 1)[0]
        return attempt_id, intent_id

    def send_stripe_webhook(
        self,
        *,
        payload: dict[str, Any],
        webhook_secret: Optional[str] = None,
        signature: Optional[str] = None,
    ):
        body = normalize_json_payload(payload)
        if signature is None:
            if not webhook_secret:
                raise ValueError("webhook_secret is required when signature is not provided")
            signature = build_stripe_signature(body, webhook_secret)

        return self.client.post(
            "/payments/stripe/webhook",
            headers={"Stripe-Signature": signature, "Content-Type": "application/json"},
            data_body=body,
        )

    def build_stripe_success_payload(
        self,
        *,
        order_id: int,
        attempt_id: int,
        payment_intent_id: str,
        event_id: Optional[str] = None,
    ) -> dict[str, Any]:
        return build_stripe_payment_succeeded_event(
            event_id=event_id or f"evt_{uuid.uuid4().hex[:18]}",
            payment_intent_id=payment_intent_id,
            order_id=order_id,
            attempt_id=attempt_id,
        )

    def build_momo_callback_payload(
        self,
        *,
        order_id: str,
        request_id: str,
        amount: int,
        partner_code: str,
        result_code: int = 0,
        message: str = "Success",
        order_type: str = "momo_wallet",
        pay_type: str = "wallet",
        trans_id: int = 1000001,
        response_time: Optional[int] = None,
        extra_data: str = "",
        order_info: str = "Wave1 callback",
    ) -> dict[str, Any]:
        return {
            "orderType": order_type,
            "amount": amount,
            "partnerCode": partner_code,
            "orderId": order_id,
            "extraData": extra_data,
            "signature": "",
            "transId": trans_id,
            "responseTime": response_time or 1710000000,
            "resultCode": result_code,
            "message": message,
            "payType": pay_type,
            "requestId": request_id,
            "orderInfo": order_info,
        }

    def sign_momo_payload(self, payload: dict[str, Any], *, access_key: str, secret_key: str) -> dict[str, Any]:
        signed = dict(payload)
        signed["signature"] = build_momo_signature(signed, access_key=access_key, secret_key=secret_key)
        return signed

    def send_momo_webhook(self, payload: dict[str, Any]):
        return self.client.post("/payments/momo/webhook", json_body=payload)
