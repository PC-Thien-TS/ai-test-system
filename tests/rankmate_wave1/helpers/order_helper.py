"""Order domain API helpers for Wave 1 tests."""

from __future__ import annotations

from typing import Any, Iterable, Optional

from .api_client import RankmateApiClient


class OrderHelper:
    def __init__(self, client: RankmateApiClient):
        self.client = client

    @staticmethod
    def build_items(sku_id: int, quantity: int = 1, note: Optional[str] = None) -> list[dict[str, Any]]:
        payload = {"skuId": sku_id, "quantity": quantity}
        if note is not None:
            payload["note"] = note
        return [payload]

    def preview_pricing(
        self,
        *,
        token: str,
        store_id: int,
        items: list[dict[str, Any]],
        order_type: int = 20,
        arrival_time: Optional[str] = None,
        pax: Optional[int] = None,
    ):
        body: dict[str, Any] = {
            "storeId": store_id,
            "orderType": order_type,
            "items": items,
        }
        if arrival_time is not None:
            body["arrivalTime"] = arrival_time
        if pax is not None:
            body["pax"] = pax
        return self.client.post("/orders/pricing-preview", token=token, json_body=body)

    def create_order(
        self,
        *,
        token: str,
        store_id: int,
        items: list[dict[str, Any]],
        idempotency_key: str,
        order_type: int = 20,
        arrival_time: Optional[str] = None,
        pax: Optional[int] = None,
    ):
        body: dict[str, Any] = {
            "storeId": store_id,
            "orderType": order_type,
            "items": items,
        }
        if arrival_time is not None:
            body["arrivalTime"] = arrival_time
        if pax is not None:
            body["pax"] = pax

        return self.client.post(
            "/orders",
            token=token,
            json_body=body,
            idempotency_key=idempotency_key,
        )

    def create_order_without_idempotency(
        self,
        *,
        token: str,
        store_id: int,
        items: list[dict[str, Any]],
        order_type: int = 20,
    ):
        body = {"storeId": store_id, "orderType": order_type, "items": items}
        return self.client.post("/orders", token=token, json_body=body)

    def get_order(self, *, token: str, order_id: int):
        return self.client.get(f"/orders/{order_id}", token=token)

    def list_orders(self, *, token: str, status: Optional[int] = None):
        params: dict[str, Any] = {"pageNumber": 0, "pageSize": 20}
        if status is not None:
            params["status"] = status
        return self.client.get("/orders", token=token, params=params)

    def retry_payment(self, *, token: str, order_id: int, idempotency_key: str):
        return self.client.post(
            f"/orders/{order_id}/retry-payment",
            token=token,
            idempotency_key=idempotency_key,
        )

    def cancel_order(self, *, token: str, order_id: int):
        return self.client.post(f"/orders/{order_id}/cancel", token=token)

    def verify_order_payment(self, *, token: str, order_id: int):
        return self.client.get(f"/orders/{order_id}/payments/verify", token=token)

    def create_payment_intent(self, *, token: str, order_id: int, idempotency_key: str):
        return self.client.post(
            f"/orders/{order_id}/payments",
            token=token,
            idempotency_key=idempotency_key,
        )

    def pay_with_wallet(self, *, token: str, order_id: int, idempotency_key: str):
        return self.client.post(
            f"/orders/{order_id}/payments/wallet",
            token=token,
            idempotency_key=idempotency_key,
        )

    def assert_status_in(self, order_payload: dict[str, Any], statuses: Iterable[int]) -> None:
        data = order_payload.get("data") if "data" in order_payload else order_payload.get("Data")
        if not isinstance(data, dict):
            raise AssertionError(f"Invalid order payload shape: {order_payload}")
        current_status = data.get("status")
        if current_status not in set(statuses):
            raise AssertionError(
                f"Expected order status in {sorted(set(statuses))}, got {current_status} payload={order_payload}"
            )
