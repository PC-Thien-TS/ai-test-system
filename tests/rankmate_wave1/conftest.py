"""Pytest fixtures and hooks for RankMate Wave 1 API automation."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest
import requests

from .helpers.admin_helper import AdminHelper
from .helpers.api_client import RankmateApiClient
from .helpers.auth_helper import AuthHelper
from .helpers.assertion_helper import assert_status, assert_success_envelope, response_json
from .helpers.config import Wave1Config, load_wave1_config
from .helpers.idempotency import IdempotencyRegistry
from .helpers.merchant_helper import MerchantHelper, MerchantSession
from .helpers.order_helper import OrderHelper
from .helpers.payment_helper import PaymentHelper
from .helpers.search_helper import SearchHelper
from .helpers.store_helper import StoreHelper
from .helpers.result_tags import attach_case_metadata_to_node


@pytest.fixture(scope="session")
def wave1_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def wave1_config(wave1_repo_root: Path) -> Wave1Config:
    return load_wave1_config(wave1_repo_root)


@pytest.fixture(scope="session", autouse=True)
def ensure_wave1_enabled(wave1_config: Wave1Config):
    if not wave1_config.enabled:
        pytest.skip(
            "RankMate Wave 1 API suite is disabled. Set RANKMATE_WAVE1_ENABLED=1 to execute.",
            allow_module_level=True,
        )
    if not wave1_config.base_url:
        pytest.skip(
            "Missing API_BASE_URL for Wave 1 suite. Set API_BASE_URL and rerun.",
            allow_module_level=True,
        )


@pytest.fixture(scope="session", autouse=True)
def ensure_wave1_backend_reachable(wave1_config: Wave1Config):
    if not wave1_config.enabled:
        return
    if not wave1_config.base_url:
        return

    probe_url = f"{wave1_config.normalized_base_url}/"
    try:
        response = requests.get(
            probe_url,
            timeout=wave1_config.timeout_sec,
            verify=wave1_config.verify_ssl,
        )
    except requests.RequestException as exc:
        pytest.skip(
            f"Wave 1 backend is unreachable at {wave1_config.normalized_base_url} "
            f"(check API_BASE_URL/network/VPN). Probe error: {exc}",
            allow_module_level=True,
        )
        return

    if wave1_config.debug:
        print(f"[Wave1API] Backend preflight GET {probe_url} -> {response.status_code}")


@pytest.fixture(autouse=True)
def attach_case_metadata(request):
    attach_case_metadata_to_node(request)


@pytest.fixture(scope="session")
def api_client(wave1_config: Wave1Config) -> RankmateApiClient:
    return RankmateApiClient(
        base_url=wave1_config.normalized_base_url,
        api_prefix=wave1_config.normalized_api_prefix,
        timeout_sec=wave1_config.timeout_sec,
        verify_ssl=wave1_config.verify_ssl,
        debug=wave1_config.debug,
    )


@pytest.fixture(scope="session")
def require_config(wave1_config: Wave1Config) -> Callable[[str, str], None]:
    def _require(case_id: str, *fields: str) -> None:
        missing = wave1_config.missing_fields(fields)
        if missing:
            env_names = ", ".join(wave1_config.env_name_for_field(field) for field in missing)
            pytest.skip(f"[{case_id}] Missing required environment values: {env_names}")

    return _require


@pytest.fixture(scope="session")
def auth_helper(api_client: RankmateApiClient, wave1_config: Wave1Config) -> AuthHelper:
    return AuthHelper(
        api_client,
        phone_number=wave1_config.phone_number or "string",
        campaign=wave1_config.campaign or "string",
        device_id=wave1_config.device_id or "string",
    )


@pytest.fixture(scope="session")
def order_helper(api_client: RankmateApiClient) -> OrderHelper:
    return OrderHelper(api_client)


@pytest.fixture(scope="session")
def payment_helper(api_client: RankmateApiClient) -> PaymentHelper:
    return PaymentHelper(api_client)


@pytest.fixture(scope="session")
def search_helper(api_client: RankmateApiClient) -> SearchHelper:
    return SearchHelper(api_client)


@pytest.fixture(scope="session")
def store_helper(api_client: RankmateApiClient) -> StoreHelper:
    return StoreHelper(api_client)


@pytest.fixture(scope="session")
def merchant_helper(api_client: RankmateApiClient) -> MerchantHelper:
    return MerchantHelper(api_client)


@pytest.fixture(scope="session")
def admin_helper(api_client: RankmateApiClient) -> AdminHelper:
    return AdminHelper(api_client)


@pytest.fixture(scope="session")
def idempotency_registry() -> IdempotencyRegistry:
    return IdempotencyRegistry()


@pytest.fixture(scope="session")
def user_session(wave1_config: Wave1Config, require_config, auth_helper: AuthHelper):
    require_config("AUTH-API-001", "user_email", "user_password")
    response = auth_helper.login(email=wave1_config.user_email or "", password=wave1_config.user_password or "")
    assert_status(response, 200, assertion_id="API-A01", case_id="AUTH-API-001")
    payload = assert_success_envelope(response, assertion_id="API-A01", case_id="AUTH-API-001")
    return auth_helper.extract_session(payload)


@pytest.fixture(scope="session")
def merchant_user_session(wave1_config: Wave1Config, require_config, auth_helper: AuthHelper):
    require_config("AUTH-API-003", "merchant_email", "merchant_password")
    response = auth_helper.login(
        email=wave1_config.merchant_email or "",
        password=wave1_config.merchant_password or "",
    )
    assert_status(response, 200, assertion_id="API-A01", case_id="AUTH-API-003")
    payload = assert_success_envelope(response, assertion_id="API-A01", case_id="AUTH-API-003")
    return auth_helper.extract_session(payload)


@pytest.fixture(scope="session")
def merchant_store_session(
    wave1_config: Wave1Config,
    merchant_user_session,
    merchant_helper: MerchantHelper,
):
    verify_response = merchant_helper.get_verify_stores(token=merchant_user_session.token)
    assert_status(verify_response, 200, assertion_id="API-A01", case_id="AUTH-API-004")
    verify_payload = assert_success_envelope(verify_response, assertion_id="API-A01", case_id="AUTH-API-004")

    store_id, profile_id = merchant_helper.extract_store_candidate(
        verify_payload,
        preferred_store_id=wave1_config.merchant_store_id,
    )

    switch_response = merchant_helper.switch_profile(
        token=merchant_user_session.token,
        store_id=store_id,
        profile_id=profile_id,
    )
    assert_status(switch_response, 200, assertion_id="API-A01", case_id="AUTH-API-005")
    switch_payload = assert_success_envelope(switch_response, assertion_id="API-A01", case_id="AUTH-API-005")

    switch_session = AuthHelper(merchant_helper.client).extract_session(switch_payload)

    return MerchantSession(
        user_token=merchant_user_session.token,
        store_token=switch_session.token,
        store_id=store_id,
        profile_id=profile_id,
    )


@pytest.fixture(scope="session")
def admin_session(wave1_config: Wave1Config, require_config, auth_helper: AuthHelper):
    require_config("AUTH-API-006", "admin_email", "admin_password")
    response = auth_helper.login(
        email=wave1_config.admin_email or "",
        password=wave1_config.admin_password or "",
    )
    assert_status(response, 200, assertion_id="API-A01", case_id="AUTH-API-006")
    payload = assert_success_envelope(response, assertion_id="API-A01", case_id="AUTH-API-006")
    return auth_helper.extract_session(payload)


@pytest.fixture
def parse_payload() -> Callable:
    return response_json


@pytest.fixture
def case_skip() -> Callable[[str, str], None]:
    def _skip(case_id: str, reason: str) -> None:
        pytest.skip(f"[{case_id}] {reason}")

    return _skip
