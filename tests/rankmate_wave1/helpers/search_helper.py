"""Search API helpers for Wave 1 tests."""

from __future__ import annotations

from typing import Any, Optional

from .api_client import RankmateApiClient


class SearchHelper:
    def __init__(self, client: RankmateApiClient):
        self.client = client

    def search_stores(
        self,
        *,
        keyword: Optional[str] = None,
        page_number: int = 0,
        page_size: int = 20,
    ):
        params: dict[str, Any] = {
            "pageNumber": page_number,
            "pageSize": page_size,
        }
        if keyword is not None:
            params["keyword"] = keyword
        return self.client.get("/searches/stores", params=params)

    def search_stores_v2(
        self,
        *,
        keyword: Optional[str] = None,
        page_number: int = 0,
        page_size: int = 20,
    ):
        params: dict[str, Any] = {
            "pageNumber": page_number,
            "pageSize": page_size,
        }
        if keyword is not None:
            params["keyword"] = keyword
        return self.client.get("/searches/storesV2", params=params)

    def search_menu(
        self,
        *,
        keyword: str,
        store_id: Optional[int] = None,
        page_number: int = 0,
        page_size: int = 20,
    ):
        params: dict[str, Any] = {
            "keyword": keyword,
            "pageNumber": page_number,
            "pageSize": page_size,
        }
        if store_id is not None:
            params["storeId"] = store_id
        return self.client.get("/searches/menu", params=params)

    def autocomplete(self, *, keyword: str):
        return self.client.get(f"/searches/autocomplete/{keyword}")

    def suggestions(self, *, keyword: str):
        return self.client.get(f"/searches/suggestions/{keyword}")

    def filters(self):
        return self.client.get("/searches/filters")

    def hot_keywords(self):
        return self.client.get("/searches/hot-keywords")
