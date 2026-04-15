"""Reusable HTTP client for RankMate Wave 1 API tests."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping, Optional

import requests


@dataclass
class RequestTrace:
    method: str
    url: str
    status_code: int
    request_headers: dict[str, Any]
    response_text: str


class RankmateApiClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_prefix: str,
        timeout_sec: float,
        verify_ssl: bool,
        debug: bool = False,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_prefix = api_prefix.rstrip("/")
        self.timeout_sec = timeout_sec
        self.verify_ssl = verify_ssl
        self.debug = debug
        self.session = requests.Session()
        self.last_trace: Optional[RequestTrace] = None

    def build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        path = path.strip()
        if not path.startswith("/"):
            path = f"/{path}"
        if self.api_prefix and not path.startswith(self.api_prefix):
            path = f"{self.api_prefix}{path}"
        return f"{self.base_url}{path}"

    def request(
        self,
        method: str,
        path: str,
        *,
        token: Optional[str] = None,
        headers: Optional[Mapping[str, str]] = None,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Any] = None,
        data_body: Optional[Any] = None,
        idempotency_key: Optional[str] = None,
        timeout_sec: Optional[float] = None,
    ) -> requests.Response:
        url = self.build_url(path)
        outgoing_headers: dict[str, str] = {"Accept": "application/json"}
        if headers:
            outgoing_headers.update({k: str(v) for k, v in headers.items()})
        if token:
            outgoing_headers["Authorization"] = f"Bearer {token}"
        if idempotency_key:
            outgoing_headers["Idempotency-Key"] = idempotency_key

        if json_body is not None and data_body is not None:
            raise ValueError("Provide only one of json_body or data_body")

        response = self.session.request(
            method=method.upper(),
            url=url,
            headers=outgoing_headers,
            params=params,
            json=json_body,
            data=data_body,
            timeout=timeout_sec or self.timeout_sec,
            verify=self.verify_ssl,
        )

        response_text = response.text or ""
        self.last_trace = RequestTrace(
            method=method.upper(),
            url=url,
            status_code=response.status_code,
            request_headers=dict(outgoing_headers),
            response_text=response_text[:5000],
        )

        if self.debug:
            print(
                f"[Wave1API] {method.upper()} {url} -> {response.status_code} | "
                f"idempotency={outgoing_headers.get('Idempotency-Key', '-')}")

        return response

    def get(self, path: str, **kwargs) -> requests.Response:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return self.request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return self.request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return self.request("DELETE", path, **kwargs)

    @staticmethod
    def parse_json(response: requests.Response) -> dict[str, Any]:
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise AssertionError(
                f"Response is not JSON. status={response.status_code} body={response.text[:1000]}"
            ) from exc
