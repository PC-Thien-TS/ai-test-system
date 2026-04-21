"""Wave 1 SEARCH-API-* and STORE-API-* automated tests."""

from __future__ import annotations

from typing import Any, Mapping, Optional

from .helpers.assertion_helper import (
    assert_status,
    assert_success_envelope,
    envelope_data,
)
from .helpers.result_tags import wave1_case


def _active_store_id(cfg) -> Optional[int]:
    for candidate in (cfg.menu_store_id, cfg.order_store_id, cfg.store_id):
        if isinstance(candidate, int):
            return candidate
    return None


def _extract_rows(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    data = envelope_data(payload)
    if isinstance(data, list):
        return [row for row in data if isinstance(row, Mapping)]
    if isinstance(data, Mapping):
        for key in ("data", "items", "rows", "stores", "records"):
            candidate = data.get(key)
            if isinstance(candidate, list):
                return [row for row in candidate if isinstance(row, Mapping)]
    return []


def _extract_store_id(row: Mapping[str, Any]) -> Optional[int]:
    for key in ("storeId", "id", "storeID"):
        value = row.get(key)
        if isinstance(value, int):
            return value
    return None


def _extract_menu_categories(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    data = envelope_data(payload)
    if not isinstance(data, Mapping):
        return []
    categories = data.get("categories")
    if isinstance(categories, list):
        return [cat for cat in categories if isinstance(cat, Mapping)]
    return []


def _iter_menu_skus(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    skus: list[Mapping[str, Any]] = []
    for category in _extract_menu_categories(payload):
        items = category.get("items")
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, Mapping):
                continue
            sku_rows = item.get("skus")
            if not isinstance(sku_rows, list):
                continue
            for sku in sku_rows:
                if isinstance(sku, Mapping):
                    skus.append(sku)
    return skus


def _is_unavailable_sku(sku: Mapping[str, Any]) -> bool:
    is_active = sku.get("isActive")
    if isinstance(is_active, bool) and not is_active:
        return True

    is_available = sku.get("isAvailable")
    if isinstance(is_available, bool) and not is_available:
        return True

    availability_status = sku.get("availabilityStatus")
    if isinstance(availability_status, int) and availability_status != 0:
        return True

    return False


@wave1_case(
    case_id="SEARCH-API-001",
    assertion_ids=["SEARCH-A01"],
    domain="search",
    priority="P0",
    risk="high",
)
def test_search_api_001_search_stores_keyword_contract(wave1_config, search_helper):
    keyword = (wave1_config.search_keyword or "").strip() or "banh"
    response = search_helper.search_stores(keyword=keyword, page_number=0, page_size=20)
    assert_status(response, 200, assertion_id="SEARCH-A01", case_id="SEARCH-API-001")
    payload = assert_success_envelope(response, assertion_id="SEARCH-A01", case_id="SEARCH-API-001")
    rows = _extract_rows(payload)
    assert isinstance(rows, list)


@wave1_case(
    case_id="SEARCH-API-002",
    assertion_ids=["SEARCH-A01"],
    domain="search",
    priority="P0",
    risk="high",
)
def test_search_api_002_search_stores_v2_contract(wave1_config, search_helper):
    keyword = (wave1_config.search_keyword or "").strip() or "banh"
    response = search_helper.search_stores_v2(keyword=keyword, page_number=0, page_size=20)
    assert_status(response, 200, assertion_id="SEARCH-A01", case_id="SEARCH-API-002")
    payload = assert_success_envelope(response, assertion_id="SEARCH-A01", case_id="SEARCH-API-002")
    rows = _extract_rows(payload)
    assert isinstance(rows, list)


@wave1_case(
    case_id="SEARCH-API-003",
    assertion_ids=["SEARCH-A02"],
    domain="search",
    priority="P1",
    risk="medium",
)
def test_search_api_003_search_menu_contract(wave1_config, search_helper):
    keyword = (wave1_config.search_keyword or "").strip() or "banh"
    store_id = _active_store_id(wave1_config)
    response = search_helper.search_menu(keyword=keyword, store_id=store_id, page_number=0, page_size=20)
    assert_status(response, 200, assertion_id="SEARCH-A02", case_id="SEARCH-API-003")
    payload = assert_success_envelope(response, assertion_id="SEARCH-A02", case_id="SEARCH-API-003")
    rows = _extract_rows(payload)
    assert isinstance(rows, list)


@wave1_case(
    case_id="SEARCH-API-004",
    assertion_ids=["SEARCH-A03"],
    domain="search",
    priority="P1",
    risk="medium",
)
def test_search_api_004_autocomplete_structured_response(wave1_config, search_helper):
    keyword = (wave1_config.search_keyword or "").strip() or "banh"
    response = search_helper.autocomplete(keyword=keyword)
    assert_status(response, 200, assertion_id="SEARCH-A03", case_id="SEARCH-API-004")
    payload = assert_success_envelope(response, assertion_id="SEARCH-A03", case_id="SEARCH-API-004")
    data = envelope_data(payload)
    assert isinstance(data, list), (
        f"[SEARCH-API-004/SEARCH-A03] Expected autocomplete data list, got {type(data).__name__}"
    )


@wave1_case(
    case_id="SEARCH-API-005",
    assertion_ids=["SEARCH-A03"],
    domain="search",
    priority="P1",
    risk="medium",
)
def test_search_api_005_suggestions_no_result_keyword_well_formed(wave1_config, search_helper):
    keyword = (wave1_config.noresult_keyword or "").strip() or "wave1-no-result-keyword-zzzz"
    suggestions = search_helper.suggestions(keyword=keyword)
    assert_status(suggestions, 200, assertion_id="SEARCH-A03", case_id="SEARCH-API-005")
    suggestions_payload = assert_success_envelope(
        suggestions, assertion_id="SEARCH-A03", case_id="SEARCH-API-005"
    )
    suggestions_data = envelope_data(suggestions_payload)
    assert isinstance(suggestions_data, list), (
        f"[SEARCH-API-005/SEARCH-A03] Expected suggestions data list, got {type(suggestions_data).__name__}"
    )

    autocomplete = search_helper.autocomplete(keyword=keyword)
    assert_status(autocomplete, 200, assertion_id="SEARCH-A03", case_id="SEARCH-API-005")
    autocomplete_payload = assert_success_envelope(
        autocomplete, assertion_id="SEARCH-A03", case_id="SEARCH-API-005"
    )
    autocomplete_data = envelope_data(autocomplete_payload)
    assert isinstance(autocomplete_data, list), (
        f"[SEARCH-API-005/SEARCH-A03] Expected autocomplete data list, got {type(autocomplete_data).__name__}"
    )


@wave1_case(
    case_id="SEARCH-API-006",
    assertion_ids=["SEARCH-A04"],
    domain="search",
    priority="P1",
    risk="medium",
)
def test_search_api_006_filters_endpoint_contract(search_helper):
    response = search_helper.filters()
    assert_status(response, 200, assertion_id="SEARCH-A04", case_id="SEARCH-API-006")
    payload = assert_success_envelope(response, assertion_id="SEARCH-A04", case_id="SEARCH-API-006")
    data = envelope_data(payload)
    assert isinstance(data, (list, dict)), (
        f"[SEARCH-API-006/SEARCH-A04] Expected filters payload list/dict, got {type(data).__name__}"
    )


@wave1_case(
    case_id="SEARCH-API-007",
    assertion_ids=["SEARCH-A04"],
    domain="search",
    priority="P1",
    risk="medium",
)
def test_search_api_007_hot_keywords_contract(search_helper):
    response = search_helper.hot_keywords()
    assert_status(response, 200, assertion_id="SEARCH-A04", case_id="SEARCH-API-007")
    payload = assert_success_envelope(response, assertion_id="SEARCH-A04", case_id="SEARCH-API-007")
    data = envelope_data(payload)
    assert isinstance(data, list), (
        f"[SEARCH-API-007/SEARCH-A04] Expected hot-keywords list, got {type(data).__name__}"
    )


@wave1_case(
    case_id="STORE-API-001",
    assertion_ids=["STORE-A01"],
    domain="store",
    priority="P0",
    risk="high",
)
def test_store_api_001_get_store_by_id_contract(wave1_config, user_session, store_helper, case_skip):
    store_id = _active_store_id(wave1_config)
    if not isinstance(store_id, int):
        case_skip("STORE-API-001", "Missing API_MENU_STORE_ID/API_ORDER_STORE_ID/API_STORE_ID")

    response = store_helper.get_store_by_id(store_id=store_id, token=user_session.token)
    assert_status(response, 200, assertion_id="STORE-A01", case_id="STORE-API-001")
    payload = assert_success_envelope(response, assertion_id="STORE-A01", case_id="STORE-API-001")
    data = envelope_data(payload)
    assert isinstance(data, Mapping), (
        f"[STORE-API-001/STORE-A01] Expected store detail map, got {type(data).__name__}"
    )


@wave1_case(
    case_id="STORE-API-002",
    assertion_ids=["STORE-A02"],
    domain="store",
    priority="P0",
    risk="high",
)
def test_store_api_002_store_eligibility_well_formed(wave1_config, store_helper, case_skip):
    store_id = _active_store_id(wave1_config)
    if not isinstance(store_id, int):
        case_skip("STORE-API-002", "Missing API_MENU_STORE_ID/API_ORDER_STORE_ID/API_STORE_ID")

    response = store_helper.get_store_eligibility(store_id=store_id)
    assert_status(response, 200, assertion_id="STORE-A02", case_id="STORE-API-002")
    payload = assert_success_envelope(response, assertion_id="STORE-A02", case_id="STORE-API-002")
    data = envelope_data(payload)
    assert isinstance(data, (bool, Mapping)), (
        f"[STORE-API-002/STORE-A02] Expected eligibility bool/map, got {type(data).__name__}"
    )


@wave1_case(
    case_id="STORE-API-003",
    assertion_ids=["STORE-A03"],
    domain="store",
    priority="P0",
    risk="high",
)
def test_store_api_003_store_menu_contract(wave1_config, store_helper, case_skip):
    store_id = _active_store_id(wave1_config)
    if not isinstance(store_id, int):
        case_skip("STORE-API-003", "Missing API_MENU_STORE_ID/API_ORDER_STORE_ID/API_STORE_ID")

    response = store_helper.get_store_menu(store_id=store_id)
    assert_status(response, 200, assertion_id="STORE-A03", case_id="STORE-API-003")
    payload = assert_success_envelope(response, assertion_id="STORE-A03", case_id="STORE-API-003")
    categories = _extract_menu_categories(payload)
    assert isinstance(categories, list)


@wave1_case(
    case_id="STORE-API-004",
    assertion_ids=["STORE-A04"],
    domain="store",
    priority="P0",
    risk="critical",
)
def test_store_api_004_invalid_store_id_returns_controlled_failure(user_session, store_helper):
    response = store_helper.get_store_by_id(store_id=999999999, token=user_session.token)
    assert_status(response, {400, 404}, assertion_id="STORE-A04", case_id="STORE-API-004")


@wave1_case(
    case_id="STORE-API-005",
    assertion_ids=["STORE-A04"],
    domain="store",
    priority="P0",
    risk="critical",
)
def test_store_api_005_invalid_store_unique_id_returns_controlled_failure(store_helper):
    response = store_helper.get_store_by_unique_id(unique_id="UNKNOWN-UNIQUE-ID-QA")
    assert_status(response, {400, 404}, assertion_id="STORE-A04", case_id="STORE-API-005")


@wave1_case(
    case_id="STORE-API-006",
    assertion_ids=["STORE-A01"],
    domain="store",
    priority="P1",
    risk="medium",
)
def test_store_api_006_get_store_by_unique_id_contract(wave1_config, user_session, store_helper, case_skip):
    unique_id = (wave1_config.store_unique_id or "").strip()
    if not unique_id:
        case_skip("STORE-API-006", "Missing API_STORE_UNIQUE_ID deterministic seed")

    response = store_helper.get_store_by_unique_id(unique_id=unique_id, token=user_session.token)
    assert_status(response, 200, assertion_id="STORE-A01", case_id="STORE-API-006")
    payload = assert_success_envelope(response, assertion_id="STORE-A01", case_id="STORE-API-006")
    data = envelope_data(payload)
    assert isinstance(data, Mapping), (
        f"[STORE-API-006/STORE-A01] Expected store detail map, got {type(data).__name__}"
    )


@wave1_case(
    case_id="STORE-API-007",
    assertion_ids=["STORE-A05"],
    domain="store",
    priority="P0",
    risk="high",
)
def test_store_api_007_search_to_store_funnel_consistency(
    wave1_config,
    user_session,
    search_helper,
    store_helper,
    case_skip,
):
    keyword = (wave1_config.search_keyword or "").strip() or "banh"
    search_response = search_helper.search_stores_v2(keyword=keyword, page_number=0, page_size=20)
    assert_status(search_response, 200, assertion_id="STORE-A05", case_id="STORE-API-007")
    search_payload = assert_success_envelope(search_response, assertion_id="STORE-A05", case_id="STORE-API-007")
    rows = _extract_rows(search_payload)
    if not rows:
        case_skip("STORE-API-007", f"No stores returned for keyword='{keyword}'")

    selected_store_id: Optional[int] = None
    for row in rows:
        selected_store_id = _extract_store_id(row)
        if isinstance(selected_store_id, int):
            break
    if not isinstance(selected_store_id, int):
        case_skip("STORE-API-007", "Search rows did not expose integer store id")

    detail_response = store_helper.get_store_by_id(store_id=selected_store_id, token=user_session.token)
    assert_status(detail_response, 200, assertion_id="STORE-A05", case_id="STORE-API-007")
    _ = assert_success_envelope(detail_response, assertion_id="STORE-A05", case_id="STORE-API-007")

    eligibility_response = store_helper.get_store_eligibility(store_id=selected_store_id)
    assert_status(eligibility_response, 200, assertion_id="STORE-A05", case_id="STORE-API-007")
    _ = assert_success_envelope(eligibility_response, assertion_id="STORE-A05", case_id="STORE-API-007")

    menu_response = store_helper.get_store_menu(store_id=selected_store_id)
    assert_status(menu_response, 200, assertion_id="STORE-A05", case_id="STORE-API-007")
    _ = assert_success_envelope(menu_response, assertion_id="STORE-A05", case_id="STORE-API-007")


@wave1_case(
    case_id="STORE-API-008",
    assertion_ids=["STORE-A03"],
    domain="store",
    priority="P1",
    risk="medium",
)
def test_store_api_008_unavailable_sku_visibility_seed_aware(wave1_config, store_helper, case_skip):
    store_id = _active_store_id(wave1_config)
    if not isinstance(store_id, int):
        case_skip("STORE-API-008", "Missing API_MENU_STORE_ID/API_ORDER_STORE_ID/API_STORE_ID")

    response = store_helper.get_store_menu(store_id=store_id)
    assert_status(response, 200, assertion_id="STORE-A03", case_id="STORE-API-008")
    payload = assert_success_envelope(response, assertion_id="STORE-A03", case_id="STORE-API-008")
    skus = _iter_menu_skus(payload)
    if not skus:
        case_skip("STORE-API-008", "Menu has no SKU rows to validate unavailable SKU visibility")

    expected_seed_sku = wave1_config.disabled_sku_id or wave1_config.out_of_stock_sku_id
    if isinstance(expected_seed_sku, int):
        target = next((row for row in skus if row.get("id") == expected_seed_sku), None)
        if target is None:
            case_skip(
                "STORE-API-008",
                f"Configured unavailable SKU {expected_seed_sku} not found in store {store_id} menu",
            )
    else:
        target = next((row for row in skus if _is_unavailable_sku(row)), None)
        if target is None:
            case_skip(
                "STORE-API-008",
                "No unavailable SKU found and API_DISABLED_SKU_ID/API_OUT_OF_STOCK_SKU_ID not configured",
            )

    assert _is_unavailable_sku(target), (
        f"[STORE-API-008/STORE-A03] Expected unavailable SKU marker, got sku={target}"
    )
