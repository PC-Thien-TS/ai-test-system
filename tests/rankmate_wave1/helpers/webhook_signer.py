"""Webhook signing and payload builders for payment callback tests."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Any, Optional


def build_stripe_signature(payload_json: str, webhook_secret: str, timestamp: Optional[int] = None) -> str:
    """Build Stripe-Signature header compatible with Stripe SDK convention."""
    ts = timestamp or int(time.time())
    signed_payload = f"{ts}.{payload_json}".encode("utf-8")
    digest = hmac.new(webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={digest}"


def build_stripe_payment_succeeded_event(
    *,
    event_id: str,
    payment_intent_id: str,
    order_id: int,
    attempt_id: int,
) -> dict[str, Any]:
    return {
        "id": event_id,
        "object": "event",
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": payment_intent_id,
                "object": "payment_intent",
                "metadata": {
                    "order_id": str(order_id),
                    "attempt_id": str(attempt_id),
                },
            }
        },
    }


def build_momo_signature(payload: dict[str, Any], access_key: str, secret_key: str) -> str:
    """Build MoMo signature using backend VerifyCallback raw hash strategy."""
    raw_hash = (
        f"accessKey={access_key}&amount={payload.get('amount')}&extraData={payload.get('extraData')}&"
        f"message={payload.get('message')}&orderId={payload.get('orderId')}&orderInfo={payload.get('orderInfo')}&"
        f"orderType={payload.get('orderType')}&partnerCode={payload.get('partnerCode')}&payType={payload.get('payType')}&"
        f"requestId={payload.get('requestId')}&responseTime={payload.get('responseTime')}&"
        f"resultCode={payload.get('resultCode')}&transId={payload.get('transId')}"
    )
    return hmac.new(secret_key.encode("utf-8"), raw_hash.encode("utf-8"), hashlib.sha256).hexdigest()


def normalize_json_payload(payload: dict[str, Any]) -> str:
    """Compact deterministic json for signature generation and request body."""
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
