"""Assertion helpers mapped to Wave 1 assertion IDs."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

import requests


def response_json(response: requests.Response) -> dict[str, Any]:
    try:
        return response.json()
    except Exception as exc:  # pragma: no cover - assertion helper
        raise AssertionError(
            f"Expected JSON response. status={response.status_code} body={response.text[:1000]}"
        ) from exc


def envelope_data(payload: Mapping[str, Any]) -> Any:
    if "data" in payload:
        return payload.get("data")
    if "Data" in payload:
        return payload.get("Data")
    return None


def assert_status(
    response: requests.Response,
    expected: int | Iterable[int],
    *,
    assertion_id: str,
    case_id: str,
) -> None:
    expected_values = {expected} if isinstance(expected, int) else set(expected)
    assert response.status_code in expected_values, (
        f"[{case_id}/{assertion_id}] Unexpected status {response.status_code}, "
        f"expected {sorted(expected_values)} body={response.text[:1200]}"
    )


def assert_success_envelope(
    response: requests.Response,
    *,
    assertion_id: str,
    case_id: str,
) -> dict[str, Any]:
    payload = response_json(response)
    result = payload.get("result", payload.get("Result"))
    assert result == 20, (
        f"[{case_id}/{assertion_id}] Expected result=20 success envelope, "
        f"got result={result} payload={payload}"
    )
    return payload


def assert_access_denied(
    response: requests.Response,
    *,
    assertion_id: str,
    case_id: str,
) -> None:
    assert response.status_code in {400, 401, 403}, (
        f"[{case_id}/{assertion_id}] Expected access denied status 400/401/403, "
        f"got {response.status_code} body={response.text[:1000]}"
    )


def assert_has_tokens(payload: Mapping[str, Any], *, assertion_id: str, case_id: str) -> None:
    data = envelope_data(payload)
    assert isinstance(data, Mapping), f"[{case_id}/{assertion_id}] Missing auth data envelope: {payload}"
    token = data.get("token")
    refresh_token = data.get("refreshToken")
    assert isinstance(token, str) and token.strip(), f"[{case_id}/{assertion_id}] Missing token"
    assert isinstance(refresh_token, str) and refresh_token.strip(), (
        f"[{case_id}/{assertion_id}] Missing refreshToken"
    )


def assert_order_status(
    payload: Mapping[str, Any],
    expected_statuses: Iterable[int],
    *,
    assertion_id: str,
    case_id: str,
) -> int:
    data = envelope_data(payload)
    assert isinstance(data, Mapping), f"[{case_id}/{assertion_id}] Missing order data envelope"
    status = data.get("status")
    expected = set(expected_statuses)
    assert isinstance(status, int), f"[{case_id}/{assertion_id}] Order status missing or not int: {status}"
    assert status in expected, (
        f"[{case_id}/{assertion_id}] Expected order status in {sorted(expected)} got {status}"
    )
    return status


def assert_same_order_id(
    first_payload: Mapping[str, Any],
    second_payload: Mapping[str, Any],
    *,
    assertion_id: str,
    case_id: str,
) -> None:
    first = envelope_data(first_payload)
    second = envelope_data(second_payload)
    assert isinstance(first, Mapping) and isinstance(second, Mapping), (
        f"[{case_id}/{assertion_id}] Missing envelope data in replay response"
    )
    assert first.get("id") == second.get("id"), (
        f"[{case_id}/{assertion_id}] Expected idempotent replay to return same order id. "
        f"first={first.get('id')} second={second.get('id')}"
    )


def extract_id(payload: Mapping[str, Any], *, key: str = "id") -> int:
    data = envelope_data(payload)
    if not isinstance(data, Mapping):
        raise AssertionError(f"Missing data envelope for id extraction: {payload}")
    value = data.get(key)
    if not isinstance(value, int):
        raise AssertionError(f"Missing integer '{key}' in payload: {payload}")
    return value
