"""Configuration loader for RankMate Wave 1 API tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
from typing import Iterable, Optional


ENV_FIELD_MAP = {
    "enabled": "RANKMATE_WAVE1_ENABLED",
    "base_url": "API_BASE_URL",
    "api_prefix": "API_PREFIX",
    "timeout_sec": "API_TIMEOUT_SEC",
    "verify_ssl": "RANKMATE_WAVE1_VERIFY_SSL",
    "user_email": "API_USER",
    "user_password": "API_PASS",
    "merchant_email": "API_MERCHANT_USER",
    "merchant_password": "API_MERCHANT_PASS",
    "admin_email": "API_ADMIN_USER",
    "admin_password": "API_ADMIN_PASS",
    "phone_number": "API_PHONE_NUMBER",
    "campaign": "API_CAMPAIGN",
    "device_id": "API_DEVICE_ID",
    "search_keyword": "API_SEARCH_KEYWORD",
    "noresult_keyword": "API_NORESULT_KEYWORD",
    "store_id": "API_STORE_ID",
    "store_unique_id": "API_STORE_UNIQUE_ID",
    "menu_store_id": "API_MENU_STORE_ID",
    "order_store_id": "API_ORDER_STORE_ID",
    "order_sku_id": "API_ORDER_SKU_ID",
    "alt_store_id": "API_ALT_STORE_ID",
    "alt_sku_id": "API_ALT_SKU_ID",
    "merchant_store_id": "API_MERCHANT_STORE_ID",
    "pending_order_id": "API_PENDING_ORDER_ID",
    "paid_order_id": "API_PAID_ORDER_ID",
    "rejectable_paid_order_id": "API_REJECTABLE_PAID_ORDER_ID",
    "accepted_order_id": "API_ACCEPTED_ORDER_ID",
    "arrived_order_id": "API_ARRIVED_ORDER_ID",
    "arrived_order_with_offline_due_id": "API_ARRIVED_ORDER_WITH_OFFLINE_DUE_ID",
    "non_paid_order_id": "API_NON_PAID_ORDER_ID",
    "stale_transition_order_id": "API_STALE_TRANSITION_ORDER_ID",
    "no_show_order_id": "API_NO_SHOW_ORDER_ID",
    "merchant_cancellable_order_id": "API_MERCHANT_CANCELLABLE_ORDER_ID",
    "consistency_order_id": "API_CONSISTENCY_ORDER_ID",
    "cancelled_order_id": "API_CANCELLED_ORDER_ID",
    "completed_order_id": "API_COMPLETED_ORDER_ID",
    "disabled_sku_id": "API_DISABLED_SKU_ID",
    "out_of_stock_sku_id": "API_OUT_OF_STOCK_SKU_ID",
    "stripe_webhook_secret": "API_STRIPE_WEBHOOK_SECRET",
    "momo_access_key": "API_MOMO_ACCESS_KEY",
    "momo_secret_key": "API_MOMO_SECRET_KEY",
    "momo_partner_code": "API_MOMO_PARTNER_CODE",
    "momo_request_id": "API_MOMO_REQUEST_ID",
    "momo_transaction_order_id": "API_MOMO_TRANSACTION_ORDER_ID",
    "momo_transaction_amount": "API_MOMO_TRANSACTION_AMOUNT",
    "payment_transaction_id": "API_PAYMENT_TRANSACTION_ID",
}


@dataclass(frozen=True)
class Wave1Config:
    enabled: bool
    base_url: str
    api_prefix: str
    timeout_sec: float
    verify_ssl: bool
    debug: bool

    user_email: Optional[str]
    user_password: Optional[str]
    merchant_email: Optional[str]
    merchant_password: Optional[str]
    admin_email: Optional[str]
    admin_password: Optional[str]
    phone_number: Optional[str]
    campaign: Optional[str]
    device_id: Optional[str]
    search_keyword: Optional[str]
    noresult_keyword: Optional[str]

    store_id: Optional[int]
    store_unique_id: Optional[str]
    menu_store_id: Optional[int]
    order_store_id: Optional[int]
    order_sku_id: Optional[int]
    alt_store_id: Optional[int]
    alt_sku_id: Optional[int]
    merchant_store_id: Optional[int]

    pending_order_id: Optional[int]
    paid_order_id: Optional[int]
    rejectable_paid_order_id: Optional[int]
    accepted_order_id: Optional[int]
    arrived_order_id: Optional[int]
    arrived_order_with_offline_due_id: Optional[int]
    non_paid_order_id: Optional[int]
    stale_transition_order_id: Optional[int]
    no_show_order_id: Optional[int]
    merchant_cancellable_order_id: Optional[int]
    consistency_order_id: Optional[int]
    cancelled_order_id: Optional[int]
    completed_order_id: Optional[int]

    disabled_sku_id: Optional[int]
    out_of_stock_sku_id: Optional[int]

    stripe_webhook_secret: Optional[str]
    momo_access_key: Optional[str]
    momo_secret_key: Optional[str]
    momo_partner_code: Optional[str]
    momo_request_id: Optional[str]
    momo_transaction_order_id: Optional[str]
    momo_transaction_amount: Optional[int]
    payment_transaction_id: Optional[int]

    @property
    def normalized_base_url(self) -> str:
        return self.base_url.rstrip("/")

    @property
    def normalized_api_prefix(self) -> str:
        prefix = self.api_prefix.strip()
        if not prefix:
            return ""
        if not prefix.startswith("/"):
            prefix = f"/{prefix}"
        return prefix.rstrip("/")

    def maybe_int(self, name: str) -> Optional[int]:
        value = getattr(self, name)
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def missing_fields(self, fields: Iterable[str]) -> list[str]:
        missing: list[str] = []
        for field in fields:
            value = getattr(self, field)
            if value is None:
                missing.append(field)
            elif isinstance(value, str) and not value.strip():
                missing.append(field)
        return missing

    def env_name_for_field(self, field: str) -> str:
        return ENV_FIELD_MAP.get(field, field)


def _load_dotenv_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists() or not path.is_file():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        values[key] = value
    return values


def _get_env(key: str, fallback: Optional[str], dotenv_values: dict[str, str]) -> Optional[str]:
    value = os.getenv(key)
    if value is not None and value.strip() != "":
        return value.strip()
    if key in dotenv_values:
        candidate = dotenv_values[key].strip()
        if candidate:
            return candidate
    return fallback


def _as_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _as_int(value: Optional[str]) -> Optional[int]:
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _normalize_base_and_prefix(base_url: str, api_prefix: str) -> tuple[str, str]:
    normalized_base = base_url.rstrip("/")
    normalized_prefix = api_prefix.strip() or "/api/v1"
    if not normalized_prefix.startswith("/"):
        normalized_prefix = f"/{normalized_prefix}"
    normalized_prefix = normalized_prefix.rstrip("/")

    suffix = normalized_prefix.lstrip("/")
    if normalized_base.lower().endswith(f"/{suffix}".lower()):
        normalized_base = normalized_base[: -(len(suffix) + 1)]

    return normalized_base.rstrip("/"), normalized_prefix


def load_wave1_config(repo_root: Path) -> Wave1Config:
    dotenv_values = _load_dotenv_file(repo_root / ".env")

    enabled = _as_bool(_get_env("RANKMATE_WAVE1_ENABLED", "0", dotenv_values), default=False)
    debug = _as_bool(_get_env("RANKMATE_WAVE1_DEBUG", "0", dotenv_values), default=False)
    verify_ssl = _as_bool(_get_env("RANKMATE_WAVE1_VERIFY_SSL", "0", dotenv_values), default=False)

    raw_base_url = _get_env("API_BASE_URL", "", dotenv_values) or ""
    raw_api_prefix = _get_env("API_PREFIX", "/api/v1", dotenv_values) or "/api/v1"

    base_url, api_prefix = _normalize_base_and_prefix(raw_base_url, raw_api_prefix)

    timeout = _get_env("API_TIMEOUT_SEC", "30", dotenv_values) or "30"
    try:
        timeout_sec = float(timeout)
    except ValueError:
        timeout_sec = 30.0

    return Wave1Config(
        enabled=enabled,
        base_url=base_url,
        api_prefix=api_prefix,
        timeout_sec=timeout_sec,
        verify_ssl=verify_ssl,
        debug=debug,
        user_email=_get_env("API_USER", None, dotenv_values),
        user_password=_get_env("API_PASS", None, dotenv_values),
        merchant_email=_get_env("API_MERCHANT_USER", None, dotenv_values),
        merchant_password=_get_env("API_MERCHANT_PASS", None, dotenv_values),
        admin_email=_get_env("API_ADMIN_USER", None, dotenv_values),
        admin_password=_get_env("API_ADMIN_PASS", None, dotenv_values),
        phone_number=_get_env("API_PHONE_NUMBER", "string", dotenv_values),
        campaign=_get_env("API_CAMPAIGN", "string", dotenv_values),
        device_id=_get_env("API_DEVICE_ID", "string", dotenv_values),
        search_keyword=_get_env("API_SEARCH_KEYWORD", "banh", dotenv_values),
        noresult_keyword=_get_env("API_NORESULT_KEYWORD", "wave1-no-result-keyword-zzzz", dotenv_values),
        store_id=_as_int(_get_env("API_STORE_ID", None, dotenv_values)),
        store_unique_id=_get_env("API_STORE_UNIQUE_ID", None, dotenv_values),
        menu_store_id=_as_int(_get_env("API_MENU_STORE_ID", None, dotenv_values)),
        order_store_id=_as_int(_get_env("API_ORDER_STORE_ID", None, dotenv_values)),
        order_sku_id=_as_int(_get_env("API_ORDER_SKU_ID", None, dotenv_values)),
        alt_store_id=_as_int(_get_env("API_ALT_STORE_ID", None, dotenv_values)),
        alt_sku_id=_as_int(_get_env("API_ALT_SKU_ID", None, dotenv_values)),
        merchant_store_id=_as_int(_get_env("API_MERCHANT_STORE_ID", None, dotenv_values)),
        pending_order_id=_as_int(_get_env("API_PENDING_ORDER_ID", None, dotenv_values)),
        paid_order_id=_as_int(_get_env("API_PAID_ORDER_ID", None, dotenv_values)),
        rejectable_paid_order_id=_as_int(_get_env("API_REJECTABLE_PAID_ORDER_ID", None, dotenv_values)),
        accepted_order_id=_as_int(_get_env("API_ACCEPTED_ORDER_ID", None, dotenv_values)),
        arrived_order_id=_as_int(_get_env("API_ARRIVED_ORDER_ID", None, dotenv_values)),
        arrived_order_with_offline_due_id=_as_int(
            _get_env("API_ARRIVED_ORDER_WITH_OFFLINE_DUE_ID", None, dotenv_values)
        ),
        non_paid_order_id=_as_int(_get_env("API_NON_PAID_ORDER_ID", None, dotenv_values)),
        stale_transition_order_id=_as_int(_get_env("API_STALE_TRANSITION_ORDER_ID", None, dotenv_values)),
        no_show_order_id=_as_int(_get_env("API_NO_SHOW_ORDER_ID", None, dotenv_values)),
        merchant_cancellable_order_id=_as_int(_get_env("API_MERCHANT_CANCELLABLE_ORDER_ID", None, dotenv_values)),
        consistency_order_id=_as_int(_get_env("API_CONSISTENCY_ORDER_ID", None, dotenv_values)),
        cancelled_order_id=_as_int(_get_env("API_CANCELLED_ORDER_ID", None, dotenv_values)),
        completed_order_id=_as_int(_get_env("API_COMPLETED_ORDER_ID", None, dotenv_values)),
        disabled_sku_id=_as_int(_get_env("API_DISABLED_SKU_ID", None, dotenv_values)),
        out_of_stock_sku_id=_as_int(_get_env("API_OUT_OF_STOCK_SKU_ID", None, dotenv_values)),
        stripe_webhook_secret=_get_env("API_STRIPE_WEBHOOK_SECRET", None, dotenv_values),
        momo_access_key=_get_env("API_MOMO_ACCESS_KEY", None, dotenv_values),
        momo_secret_key=_get_env("API_MOMO_SECRET_KEY", None, dotenv_values),
        momo_partner_code=_get_env("API_MOMO_PARTNER_CODE", None, dotenv_values),
        momo_request_id=_get_env("API_MOMO_REQUEST_ID", None, dotenv_values),
        momo_transaction_order_id=_get_env("API_MOMO_TRANSACTION_ORDER_ID", None, dotenv_values),
        momo_transaction_amount=_as_int(_get_env("API_MOMO_TRANSACTION_AMOUNT", None, dotenv_values)),
        payment_transaction_id=_as_int(_get_env("API_PAYMENT_TRANSACTION_ID", None, dotenv_values)),
    )
