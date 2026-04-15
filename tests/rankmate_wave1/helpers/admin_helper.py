"""Admin API helpers for Wave 1 tests."""

from __future__ import annotations

from typing import Optional

from .api_client import RankmateApiClient


class AdminHelper:
    def __init__(self, client: RankmateApiClient):
        self.client = client

    def list_orders(
        self,
        *,
        token: str,
        status: Optional[int] = None,
        store_id: Optional[int] = None,
        page_number: int = 0,
        page_size: int = 20,
    ):
        params = {
            "pageNumber": page_number,
            "pageSize": page_size,
        }
        if status is not None:
            params["status"] = status
        if store_id is not None:
            params["storeId"] = store_id

        return self.client.get("/admin/orders", token=token, params=params)

    def get_order_detail(self, *, token: str, order_id: int):
        return self.client.get(f"/admin/orders/{order_id}", token=token)
