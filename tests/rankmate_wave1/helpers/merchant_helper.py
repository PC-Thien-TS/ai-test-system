"""Merchant API helpers for Wave 1 tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .api_client import RankmateApiClient
from .assertion_helper import envelope_data


@dataclass(frozen=True)
class MerchantSession:
    user_token: str
    store_token: str
    store_id: int
    profile_id: int


class MerchantHelper:
    def __init__(self, client: RankmateApiClient):
        self.client = client

    def get_verify_stores(self, *, token: str):
        return self.client.get(
            "/store/verify",
            token=token,
            params={"forSelf": True, "isverify": True, "pageNumber": 0, "pageSize": 1000},
        )

    def switch_profile(self, *, token: str, store_id: int, profile_id: int):
        return self.client.put(
            "/authors/switch",
            token=token,
            json_body={"storeId": store_id, "profileId": profile_id},
        )

    def list_orders(self, *, token: str, store_id: Optional[int] = None, status: Optional[int] = None):
        params: dict[str, Any] = {"pageNumber": 0, "pageSize": 20}
        if store_id is not None:
            params["storeId"] = store_id
        if status is not None:
            params["status"] = status
        return self.client.get("/merchant/orders", token=token, params=params)

    def get_order_detail(self, *, token: str, order_id: int):
        return self.client.get(f"/merchant/orders/{order_id}", token=token)

    def accept_order(self, *, token: str, order_id: int):
        return self.client.post(f"/merchant/orders/{order_id}/accept", token=token)

    def reject_order(self, *, token: str, order_id: int, reason: str = "Wave1 reject"):
        return self.client.post(
            f"/merchant/orders/{order_id}/reject",
            token=token,
            json_body={"reason": reason},
        )

    def mark_arrived(self, *, token: str, order_id: int):
        return self.client.post(f"/merchant/orders/{order_id}/mark-arrived", token=token)

    def complete_order(self, *, token: str, order_id: int, pay_at_store_collected_amount: Optional[float] = None):
        body: dict[str, Any] = {}
        if pay_at_store_collected_amount is not None:
            body["payAtStoreCollectedAmount"] = pay_at_store_collected_amount
        return self.client.post(
            f"/merchant/orders/{order_id}/complete",
            token=token,
            json_body=body,
        )

    def mark_no_show(self, *, token: str, order_id: int):
        return self.client.post(f"/merchant/orders/{order_id}/mark-no-show", token=token)

    def cancel_order(self, *, token: str, order_id: int):
        return self.client.post(f"/merchant/orders/{order_id}/cancel", token=token)

    def extract_store_candidate(self, verify_payload: Mapping[str, Any], preferred_store_id: Optional[int]) -> tuple[int, int]:
        data = envelope_data(verify_payload)
        if not isinstance(data, Mapping):
            raise AssertionError(f"Verify-store payload missing data envelope: {verify_payload}")

        records = data.get("data")
        if not isinstance(records, list) or not records:
            raise AssertionError(f"No merchant stores available in verify payload: {verify_payload}")

        selected: Optional[Mapping[str, Any]] = None
        if preferred_store_id is not None:
            for row in records:
                if isinstance(row, Mapping) and int(row.get("storeId", -1)) == preferred_store_id:
                    selected = row
                    break

        if selected is None:
            candidate = records[0]
            if not isinstance(candidate, Mapping):
                raise AssertionError(f"Invalid merchant store candidate payload: {candidate}")
            selected = candidate

        store_id = selected.get("storeId")
        profile_id = selected.get("authorId")
        if not isinstance(store_id, int) or not isinstance(profile_id, int):
            raise AssertionError(f"Verify-store payload missing storeId/authorId: {selected}")

        return store_id, profile_id
