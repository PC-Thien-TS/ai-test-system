"""Store API helpers for Wave 1 tests."""

from __future__ import annotations

from typing import Optional

from .api_client import RankmateApiClient


class StoreHelper:
    def __init__(self, client: RankmateApiClient):
        self.client = client

    def get_store_by_unique_id(self, *, unique_id: str, token: Optional[str] = None):
        return self.client.get(f"/store/{unique_id}", token=token)

    def get_store_by_id(self, *, store_id: int, token: Optional[str] = None):
        return self.client.get(f"/store/{store_id}", token=token)

    def get_store_eligibility(self, *, store_id: int):
        return self.client.get(f"/store/{store_id}/eligibility")

    def get_store_menu(self, *, store_id: int):
        return self.client.get(f"/stores/{store_id}/menu")
